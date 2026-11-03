"""English-native Meta live workflow. This is not a translation pathway."""
from pathlib import Path
from urllib.parse import urlparse,unquote
import json,hashlib,os,re,sys,threading,urllib.request,datetime

ROOT=Path(__file__).resolve().parent
DATA=Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs'
STORE=DATA/'TERRA-RELEASE-107-NATIVE-EN'
LOCK=threading.Lock()

def send(h,code,item):
    raw=json.dumps(item,ensure_ascii=False).encode('utf8')
    h.send_response(code);h.send_header('Content-Type','application/json; charset=utf-8');h.send_header('Cache-Control','no-store');h.send_header('Content-Length',str(len(raw)));h.end_headers();h.wfile.write(raw)

def read_trace(name):
    if not isinstance(name,str) or not re.fullmatch(r'FINAL-092-QUESTION-LIVE-[0-9-]+\.json',name):raise ValueError('Invalid trace identifier')
    p=DATA/name
    if not p.is_file():raise ValueError('Trace unavailable')
    raw=p.read_bytes();obj=json.loads(raw);r=obj.get('meta_result',{})
    if obj.get('evidence_case',{}).get('language')!='en' or r.get('language')!='en':raise ValueError('Not an English-native source trace')
    phases=r.get('phases',[])
    if r.get('status','').startswith('INCOMPLETE') or [x.get('phase') for x in phases]!=['spark_initial','wonder_critique','spark_revision']:
        raise ValueError('Incomplete scientific deliberation')
    if r.get('scientific_evidence_admitted')!=0:raise ValueError('Unsupported evidence status; manual assessment required')
    q=r.get('question','')
    if not isinstance(q,str) or len(q.strip())<20:raise ValueError('Invalid question')
    return p,obj,r,hashlib.sha256(raw).hexdigest(),q

def folder(digest):return STORE/digest[:18]

def digest_turns(turns):return hashlib.sha256(json.dumps(turns,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate_turns(turns):
    if not isinstance(turns,list) or not 7<=len(turns)<=13:raise ValueError('English debate must contain 7–13 turns')
    roles=[]
    for t in turns:
        if not isinstance(t,dict) or t.get('role') not in ('moderator','spark','wonder') or not isinstance(t.get('text'),str) or not 15<=len(t['text'].strip())<=850:raise ValueError('Invalid speaker or text in English dialogue')
        roles.append(t['role'])
    if roles[0]!='moderator' or roles[-1]!='moderator' or set(roles)!={'moderator','spark','wonder'}:raise ValueError('Moderator/Spark/Wonder roles missing or misordered')
    return turns

def validate_script(draft,sha):
    if draft.get('source_trace_sha256')!=sha or draft.get('language')!='en':raise ValueError('English script provenance mismatch')
    validate_turns(draft.get('turns'))
    if not draft.get('zero_evidence_acknowledged'):raise ValueError('No-evidence disclaimer not affirmed')
    return draft

def make_draft(r,sha,q,caller):
    instruction=('You are an ENGLISH editorial producer for a scientific discussion, NOT an independent scientific fact finder. '
       'Create a natural, compelling English dialogue between moderator, spark and wonder grounded ONLY in the supplied authentic '
       'English Meta phases. Output ONLY a JSON object {"turns":[{"role":"moderator","text":"..."},...]}. '
       'Use 8–11 turns, moderator first and last, all three roles. Discuss original question, initial assessment, '
       'Wonder critique and Spark revision faithfully. Local scientific evidence admitted is ZERO. Explicitly disclose '
       'that NO locally admitted observations exist IN THIS FILE, not that no data exist anywhere. Do not invent facts, '
       'measurements, geographies, or citations. No French or translation references. Each turn 20–700 chars. '
       'No markdown, no metadata, no secret information.')
    inputs={'question':q,'scientific_evidence_admitted':0,'phases':r['phases'],'language':'en'}
    response=caller('muse-spark-1.3',instruction,inputs)
    # Meta sometimes wraps valid JSON in fenced code blocks; never evaluate content.
    cleaned=response.strip()
    if cleaned.startswith('```'):
        cleaned=re.sub(r'^```(?:json)?\s*|\s*```$','',cleaned).strip()
    obj=json.loads(cleaned)
    turns=validate_turns(obj.get('turns'))
    return {'schema':'terra-native-en-dialogue/1.0','source_trace_sha256':sha,'language':'en','turns':turns,'mode':'meta_editorial_unreviewed','review_status':'pending','zero_evidence_acknowledged':True}

def call_meta(model,instruction,payload):
    key=os.environ.get('META_API_KEY')
    if not key:raise ValueError('META_API_KEY missing')
    request=urllib.request.Request('https://api.meta.ai/v1/chat/completions',data=json.dumps({'model':model,'messages':[{'role':'developer','content':instruction},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]},ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=110) as res:return json.load(res)['choices'][0]['message']['content']

def pdf_native(p,r,q,draft,out):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from xml.sax.saxutils import escape
    from pathlib import Path
    target=out/'TerraCouncil-NATIVE-EN-Scientific-Decision-Brief.pdf';out.mkdir(parents=True,exist_ok=True)
    font='Helvetica'
    for file in ('C:/Windows/Fonts/arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(file).exists():
            try:pdfmetrics.registerFont(TTFont('Terra107',file));font='Terra107';break
            except Exception:pass
    navy=HexColor('#173549');teal=HexColor('#008b7f')
    h=ParagraphStyle('t',fontName=font,fontSize=17,leading=24,textColor=navy,spaceAfter=14)
    sh=ParagraphStyle('s',fontName=font,fontSize=11,leading=16,textColor=teal,spaceBefore=12,spaceAfter=7)
    body=ParagraphStyle('b',fontName=font,fontSize=9,leading=14,spaceAfter=8)
    def para(t,style=body):return Paragraph(escape(str(t)).replace('\n','<br/>'),style)
    parts=[para('TerraCouncil AI | SustainAfrica',h),para('Scientific decision brief — English-native Meta deliberation',sh),para('Question',sh),para(q),para('Council conclusion',sh),para(r['phases'][2]['text']),para('Evidence & limitations',sh),para('There were zero scientifically admitted local observations in this session. This does not imply that evidence does not exist elsewhere. Model output requires independent review.'),para('Meta deliberation',sh)]
    for phase in r['phases']:parts.extend([para(phase['phase'].replace('_',' ').title(),sh),para(phase['text'])])
    parts.append(para('Human-reviewed English oral adaptation',sh))
    for t in draft['turns']:parts.append(para(t['role'].upper()+': '+t['text']))
    parts.extend([para('Provenance',sh),para('Source trace: '+p.name),para('SHA-256: '+draft['source_trace_sha256'])])
    doc=SimpleDocTemplate(str(target),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=48,bottomMargin=48,title='TerraCouncil English native scientific brief');doc.build(parts)
    return target

def action(obj):
    op=obj.get('action');name=obj.get('trace');p,original,r,sha,q=read_trace(name)
    dest=folder(sha);draftfile=dest/'draft_en.json';approved=dest/'approved_en.json'
    if op=='status':
        return {'source':name,'language':'en','draft':draftfile.exists(),'approved':approved.exists(),'pdf':(dest/'pdf'/'TerraCouncil-NATIVE-EN-Scientific-Decision-Brief.pdf').exists(),'audio':bool(list((dest/'audio').glob('natural-en-*/dialogue_*.mp3')))}
    if not LOCK.acquire(blocking=False):raise ValueError('Generation already in progress')
    try:
        if op=='editor':
            if obj.get('authorize_meta_charge') is not True:raise PermissionError('Meta charge authorization required')
            generated=make_draft(r,sha,q,call_meta)
            dest.mkdir(parents=True,exist_ok=True)
            draftfile.write_text(json.dumps(generated,indent=2,ensure_ascii=False),encoding='utf8')
            return {'draft':generated,'human_review_required':True}
        if op=='approve':
            if obj.get('confirm_reviewed') is not True:raise PermissionError('Human review confirmation required')
            if not draftfile.exists():raise ValueError('Create English editorial draft first')
            generated=validate_script(json.loads(draftfile.read_text(encoding='utf8')),sha)
            # Source text is immutable after approval; never silently approve a different draft.
            generated={**generated,'review_status':'approved','approved_turns_sha256':digest_turns(generated['turns'])}
            approved.write_text(json.dumps(generated,indent=2,ensure_ascii=False),encoding='utf8')
            return {'approved':True,'dialogue':generated}
        if not approved.exists():raise ValueError('Approve English dialogue first')
        script=validate_script(json.loads(approved.read_text(encoding='utf8')),sha)
        if script.get('review_status')!='approved' or script.get('approved_turns_sha256')!=digest_turns(script['turns']):raise ValueError('English dialogue approval fingerprint mismatch')
        if op=='pdf':
            output=pdf_native(p,r,q,script,dest/'pdf')
            return {'pdf':output.name}
        if op=='audio':
            if obj.get('authorize_eleven_charge') is not True:raise PermissionError('ElevenLabs charge authorization required')
            sys.path.insert(0,str(ROOT/'release_101_modules'))
            from bilingual_102 import render_audio_en
            manifest=render_audio_en({'turns_en':script['turns'],'source_trace_sha256':sha},dest/'audio')
            return {'audio':[f.name for f in manifest.parent.glob('dialogue_*.mp3')],'manifest':manifest.name}
        raise ValueError('Unsupported action')
    finally:LOCK.release()

def get(h):
    path=urlparse(h.path).path
    if path=='/api/release107/traces':
        # Archived historical trace is hidden, not deleted. Keep all other
        # genuinely English-native sessions, with human-readable metadata.
        import re as _re114
        sessions=[]
        legacy='FINAL-092-QUESTION-LIVE-20261102-075711-098566.json'
        for f in sorted(DATA.glob('FINAL-092-QUESTION-LIVE-*.json'),reverse=True):
            if f.name==legacy:continue
            try:
                _,_,r,_,q=read_trace(f.name)
                whole=' '.join(str(p.get('text','')).lower() for p in r.get('phases',[]))
                if sum(c in whole for c in ('votre question','aucune preuve','dans ce dossier','les références','je ne peux','je m’abstiens'))>=2:continue
                stamp=_re114.search(r'LIVE-(\d{8})-(\d{6})-',f.name)
                date=(stamp.group(1)[0:4]+'-'+stamp.group(1)[4:6]+'-'+stamp.group(1)[6:8]+' '+stamp.group(2)[0:2]+':'+stamp.group(2)[2:4]) if stamp else ''
                sessions.append({'trace':f.name,'date':date,'question':q,'language':'en'})
            except (OSError,ValueError,KeyError,TypeError):pass
        return send(h,200,{'traces':[s['trace'] for s in sessions],'sessions':sessions})
    if path.startswith('/api/release107/file/'):
        parts=[unquote(s) for s in path[len('/api/release107/file/'):].split('/')]
        if len(parts)!=3:return h.send_error(404)
        name,kind,filename=parts
        try:
            _,_,_,sha,_=read_trace(name);d=folder(sha)
            if filename!=Path(filename).name:return h.send_error(404)
            if kind=='pdf' and filename=='TerraCouncil-NATIVE-EN-Scientific-Decision-Brief.pdf':file=d/'pdf'/filename
            elif kind=='audio' and re.fullmatch(r'dialogue_[0-9]{2}.mp3',filename):file=next((x for x in (d/'audio').glob('natural-en-*/'+filename) if x.is_file()),None)
            else:return h.send_error(404)
            if not file or not file.is_file():return h.send_error(404)
            raw=file.read_bytes();h.send_response(200);h.send_header('Content-Type','application/pdf' if kind=='pdf' else 'audio/mpeg');h.send_header('Content-Length',str(len(raw)));h.end_headers();h.wfile.write(raw)
        except (ValueError,KeyError,OSError):h.send_error(404)
        return
    return h.send_error(404)

def post(h):
    try:
        length=int(h.headers.get('Content-Length','0'))
        if not 0<length<=80000:return send(h,400,{'error':'Invalid payload size'})
        payload=json.loads(h.rfile.read(length));data=action(payload);return send(h,200,data)
    except PermissionError as ex:return send(h,403,{'error':str(ex)})
    except (ValueError,KeyError,TypeError,json.JSONDecodeError) as ex:return send(h,409,{'error':str(ex)[:240]})
    except Exception as ex:
        print('RELEASE-107 ERROR TYPE:',type(ex).__name__,flush=True)
        return send(h,500,{'error':'Operation failed; see server terminal. Never automatically retry paid requests.'})

# RELEASE_114_ARCHIVE_PDF
