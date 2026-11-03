"""TerraCouncil RELEASE-112: trace-bound deliverables; no surprise API calls.

GET status is read-only. POST pdf is local-only. POST audio requires an already
reviewed/approved dialogue plus explicit audio authorization; no automatic Meta
editorial calls or auto-approval. Checks exact trace hash and voice-bound cache.
"""
from pathlib import Path
from urllib.parse import parse_qs, urlparse, quote, unquote
import hashlib, json, os, re, sys, threading

ROOT=Path(__file__).resolve().parent
DATA=Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs'
LOCK=threading.Lock()
FR_STORE=DATA/'TERRA-RELEASE-101'
NAME=re.compile(r'^FINAL-092-QUESTION-LIVE-[0-9-]+\.json$')
MP3=re.compile(r'^dialogue_\d{2}\.mp3$')
VOICES={'moderator':'ELEVENLABS_MODERATOR_VOICE_ID','spark':'ELEVENLABS_SPARK_VOICE_ID','wonder':'ELEVENLABS_WONDER_VOICE_ID'}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def json_read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def context(name, lang):
    if not isinstance(name,str) or not NAME.fullmatch(name):raise ValueError('Invalid trace identifier')
    if lang not in ('fr','en'):raise ValueError('Choose French or English')
    path=DATA/name
    if not path.is_file():raise ValueError('Trace not found')
    data=json_read(path);result=data.get('meta_result') or {}
    phases=result.get('phases') or []
    if [p.get('phase') for p in phases]!=['spark_initial','wonder_critique','spark_revision']:
        raise ValueError('Incomplete scientific deliberation')
    if not all(isinstance(p.get('text'),str) and p['text'].strip() and str(p.get('model','')).startswith('muse-') for p in phases):
        raise ValueError('Unverified Meta phases')
    actual=(result.get('language') or data.get('evidence_case',{}).get('language') or '').lower()
    if actual not in ('fr','en'):
        # Legacy trace without language marker: reject rather than mislabel.
        raise ValueError('Source trace language unknown; cannot publish a native-language output')
    if actual!=lang:raise ValueError('Trace language does not match selected language')
    # An EN routing flag alone cannot guarantee that Meta answered in English.
    # Fail closed only for clearly French replies; never silently relabel or translate.
    if lang=='en':
        joined=' '.join(str(p.get('text','')) for p in phases).lower()
        french_cues=['votre question', 'aucune preuve', 'dans ce dossier', 'je ne peux',
                     'les références', 'les activit', 'je m’abstiens', "je m'abstiens"]
        if sum(cue in joined for cue in french_cues)>=2:
            raise ValueError('English session contains French Meta responses. Native English deliverables require a genuinely English deliberation; existing French scientific trace is preserved.')
    q=result.get('question') or data.get('evidence_case',{}).get('question')
    if not isinstance(q,str) or len(q.strip())<5:raise ValueError('Trace question unavailable')
    sha=digest(path)
    if lang=='fr':dest=FR_STORE/sha[:18]
    else:
        import native_107
        # Existing native EN trace validator handles evidence status too.
        native_107.read_trace(name)
        dest=native_107.folder(sha)
    return {'trace':name,'lang':lang,'path':path,'root':data,'result':result,'question':q,'sha':sha,'dest':dest}

def approved(ctx):
    dest=ctx['dest'];sha=ctx['sha'];lang=ctx['lang']
    if lang=='fr':
        source=dest/'approved_dialogue_fr.json'
        if not source.is_file():return None
        script=json_read(source)
        sys.path.insert(0,str(ROOT/'release_101_modules'))
        import universal_debate_100 as engine
        engine.verify_reviewed(script,sha,ctx['root'])
        if script.get('review_status')!='approved':raise ValueError('French human approval missing')
        import integrity_105 as guard
        guard.checked_fr(script,sha,ctx['root'],engine)
        turns=script['turns']
    else:
        source=dest/'approved_en.json'
        if not source.is_file():return None
        script=json_read(source)
        import native_107
        native_107.validate_script(script,sha)
        if script.get('review_status')!='approved' or script.get('approved_turns_sha256')!=native_107.digest_turns(script['turns']):
            raise ValueError('English human approval fingerprint mismatch')
        turns=script['turns']
    return turns

def cache_dir(ctx,turns):
    """Do not expose unrelated/stale audio. Voice setting changes create a new cache."""
    vals={role:os.environ.get(env,'') for role,env in VOICES.items()}
    if not all(re.fullmatch(r'[A-Za-z0-9]{20}',v or '') for v in vals.values()):return None
    if ctx['lang']=='fr':
        spec={'turns':turns,'voices':vals,'model':'eleven_v4','source':ctx['sha']}
    else:
        spec={'turns':turns,'voices':vals,'source':ctx['sha'],'model':'eleven_v4','lang':'en'}
    signature=hashlib.sha256(json.dumps(spec,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    prefix='natural-fr-' if ctx['lang']=='fr' else 'natural-en-'
    return ctx['dest']/'audio'/(prefix+signature[:12])

def current_audio(ctx,turns):
    folder=cache_dir(ctx,turns)
    if folder is None or not folder.is_dir():return []
    manifest=folder/'audio_manifest.json'
    if not manifest.is_file():return []
    try:
        obj=json_read(manifest)
        if obj.get('source_trace_sha256')!=ctx['sha'] or obj.get('language')!=ctx['lang']:return []
        chunks=obj.get('chunks',[])
        if not isinstance(chunks,list) or not chunks:return []
        found=[]
        for item in chunks:
            name=item.get('file');checksum=item.get('sha256')
            if not isinstance(name,str) or not MP3.fullmatch(name):return []
            file=folder/name
            if not file.is_file() or file.stat().st_size<1000 or digest(file)!=checksum:return []
            found.append(file)
        return found
    except (ValueError,TypeError,KeyError,OSError,UnicodeError,json.JSONDecodeError):return []

def pdf_files(ctx):
    dest=ctx['dest']/'pdf'
    if ctx['lang']=='fr':return sorted([p for p in dest.glob('*-BRANDED-FR.pdf') if p.is_file() and p.stat().st_size>1000])
    files=sorted(p for p in dest.glob('*-BRANDED-EN.pdf') if p.is_file() and p.stat().st_size>1000)
    return files

def file_url(ctx,kind,file):
    return '/api/release112/file/'+quote(ctx['lang'])+'/'+quote(ctx['trace'])+'/'+quote(kind)+'/'+quote(file.name)

def status(ctx):
    problem=None
    try:turns=approved(ctx)
    except (ValueError,KeyError,TypeError) as exc:turns=None;problem=str(exc)[:160]
    audio=current_audio(ctx,turns) if turns else []
    pdf=pdf_files(ctx)
    return {'trace':ctx['trace'],'language':ctx['lang'],'question':ctx['question'],
            'trace_sha256':ctx['sha'],'approved_dialogue':bool(turns),
            'dialogue_review_required':not bool(turns),
            'approval_issue':problem,
            'pdf':[{'name':p.name,'url':file_url(ctx,'pdf',p)} for p in pdf],
            'audio':[{'name':p.name,'url':file_url(ctx,'audio',p)} for p in audio],
            'audio_ready':bool(audio),'pdf_ready':bool(pdf)}

def generate_pdf(ctx):
    if pdf_files(ctx):return status(ctx)
    dest=ctx['dest']/'pdf';dest.mkdir(parents=True,exist_ok=True)
    if ctx['lang']=='fr':
        sys.path.insert(0,str(ROOT/'release_101_modules'))
        import branded_live_094
        branded_live_094.generate(ctx['path'],dest,'fr',logo=ROOT/'release_101_modules'/'sustainafrica_logo.jpg')
    else:
        import branded_en_114
        branded_en_114.generate(ctx,dest)
    result=status(ctx)
    if not result['pdf_ready']:raise ValueError('PDF could not be verified after creation')
    return result

def generate_audio(ctx,authorized=False):
    # Always inspect the exact approved content and its voice-bound cache first.
    turns=approved(ctx)
    if turns is None:raise ValueError('A scientifically reviewed dialogue must be approved before audio synthesis')
    prior=current_audio(ctx,turns)
    if prior:return status(ctx)
    if not authorized:raise PermissionError('Explicit ElevenLabs authorization required for uncached audio')
    if ctx['lang']=='fr':
        sys.path.insert(0,str(ROOT/'release_101_modules'))
        import universal_debate_100 as engine
        script=json_read(ctx['dest']/'approved_dialogue_fr.json')
        plan=engine.build_plan(ctx['path'],script)
        from integrity_105 import assert_safe_before_audio
        assert_safe_before_audio(plan['turns'])
        engine.render(plan,ctx['dest']/'audio')
    else:
        import native_107
        native_107.validate_turns(turns)
        sys.path.insert(0,str(ROOT/'release_101_modules'))
        import bilingual_102
        bilingual_102.render_audio_en({'turns_en':turns,'source_trace_sha256':ctx['sha']},ctx['dest']/'audio')
    result=status(ctx)
    if not result['audio_ready']:raise ValueError('Audio did not pass manifest and content verification')
    return result

def run(payload):
    ctx=context(payload.get('trace'),payload.get('language'))
    op=payload.get('action')
    if op=='status':return status(ctx)
    if op not in ('pdf','audio'):raise ValueError('Unsupported operation')
    if not LOCK.acquire(False):raise ValueError('Another deliverable generation is in progress')
    try:
        if op=='pdf':return generate_pdf(ctx)
        return generate_audio(ctx,payload.get('authorize_eleven_charge') is True)
    finally:LOCK.release()

def respond(h,code,data):
    raw=json.dumps(data,ensure_ascii=False).encode('utf8')
    h.send_response(code);h.send_header('Content-Type','application/json; charset=utf-8');h.send_header('Cache-Control','no-store');h.send_header('Content-Length',str(len(raw)));h.end_headers();h.wfile.write(raw)

def handle_post(h):
    try:
        n=int(h.headers.get('Content-Length','0'))
        if not 0<n<=16000:raise ValueError('Invalid request size')
        result=run(json.loads(h.rfile.read(n)))
        respond(h,200,result)
    except PermissionError as e:respond(h,403,{'error':str(e)})
    except (ValueError,KeyError,TypeError,UnicodeError) as e:respond(h,409,{'error':str(e)[:220]})
    except Exception as e:
        print('RELEASE-112 operation failed:',type(e).__name__,flush=True)
        respond(h,500,{'error':'Operation failed. Inspect server log before retrying; no automatic paid retry.'})

def stream(h,file,kind):
    """HTTP Range support for reliable <audio> playback and duration discovery."""
    size=file.stat().st_size
    if size<1:return h.send_error(404)
    start,end=0,size-1;code=200
    ranges=h.headers.get('Range','')
    if ranges:
        found=re.fullmatch(r'bytes=(\d*)-(\d*)',ranges)
        if not found or (not found[1] and not found[2]):return h.send_error(416)
        if not found[1]:
            n=int(found[2]);start=max(0,size-n)
        else:
            start=int(found[1]);end=int(found[2]) if found[2] else size-1
        end=min(end,size-1)
        if start> end or start>=size:return h.send_error(416)
        code=206
    h.send_response(code)
    h.send_header('Content-Type','audio/mpeg' if kind=='audio' else 'application/pdf')
    h.send_header('Accept-Ranges','bytes')
    h.send_header('Content-Length',str(end-start+1))
    h.send_header('Cache-Control','no-store')
    if code==206:h.send_header('Content-Range',f'bytes {start}-{end}/{size}')
    h.end_headers()
    if h.command=='HEAD':return
    with file.open('rb') as src:
        src.seek(start);remaining=end-start+1
        while remaining:
            chunk=src.read(min(65536,remaining))
            if not chunk:break
            h.wfile.write(chunk);remaining-=len(chunk)

def handle_get(h):
    parts=urlparse(h.path)
    if parts.path=='/api/release112/status':
        try:
            params=parse_qs(parts.query);ctx=context(params.get('trace',[''])[0],params.get('language',[''])[0]);return respond(h,200,status(ctx))
        except (ValueError,KeyError,TypeError) as e:return respond(h,409,{'error':str(e)[:200]})
    if parts.path.startswith('/api/release112/file/'):
        segments=[unquote(x) for x in parts.path[len('/api/release112/file/'):].split('/')]
        if len(segments)!=4:return h.send_error(404)
        lang,trace,kind,filename=segments
        try:
            if kind not in ('pdf','audio') or filename!=Path(filename).name:return h.send_error(404)
            ctx=context(trace,lang);state=status(ctx)
            item=next((x for x in state[kind] if x['name']==filename),None)
            if not item:return h.send_error(404)
            if kind=='pdf':file=next(x for x in pdf_files(ctx) if x.name==filename)
            else:file=next(x for x in current_audio(ctx,approved(ctx)) if x.name==filename)
            return stream(h,file,kind)
        except (ValueError,KeyError,TypeError,StopIteration,OSError):return h.send_error(404)
    return h.send_error(404)
