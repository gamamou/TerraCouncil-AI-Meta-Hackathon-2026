"""Additive release routes; no key exposure, no external calls unless explicitly authorized."""
import json, os, sys, hashlib, subprocess, threading, mimetypes
from pathlib import Path
from urllib.parse import urlparse, unquote
ROOT=Path(__file__).resolve().parent
DATA=Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs'
OUT=DATA/'TERRA-RELEASE-101'; OUT.mkdir(parents=True,exist_ok=True)
LOCK=threading.Lock()
BASE=ROOT.parents[0]
PKG=ROOT/'release_101_modules'
sys.path.insert(0,str(PKG))
import universal_debate_100 as engine
import integrity_105 as guard # INTEGRITY_105_ACTIVE

def reply(h,code,body):
    b=json.dumps(body,ensure_ascii=False).encode('utf-8');h.send_response(code);h.send_header('Content-Type','application/json; charset=utf-8');h.send_header('Cache-Control','no-store');h.send_header('Content-Length',str(len(b)));h.end_headers();h.wfile.write(b)
def trace_path(name):
    if not isinstance(name,str) or not name.startswith('FINAL-092-QUESTION-LIVE-') or name!=Path(name).name or not name.endswith('.json'):raise ValueError('Invalid trace name')
    p=DATA/name
    if not p.is_file():raise ValueError('Trace not found')
    return p

def selected(name):
    p=trace_path(name); root,digest,q=engine.read_trace(p); return p,root,digest,q,OUT/digest[:18]
def state(name):
    p,root,digest,q,dest=selected(name); approved=dest/'approved_dialogue_fr.json';draft=dest/'editorial_draft_fr.json'
    return {'trace':name,'question':q,'sha256':digest,'draft_available':draft.is_file(),'approved':approved.is_file(),'pdf_fr':bool(list((dest/'pdf').glob('*-BRANDED-FR.pdf'))) if (dest/'pdf').exists() else False,'audio_available':len(list((dest/'audio').glob('natural-fr-*/dialogue_*.mp3'))) if (dest/'audio').exists() else 0}
def get(h):
    path=urlparse(h.path).path
    if path=='/api/release/traces':
        names=sorted((p.name for p in DATA.glob('FINAL-092-QUESTION-LIVE-*.json') if p.is_file()),reverse=True)[:30]
        return reply(h,200,{'traces':names})
    if path.startswith('/api/release/file/'):
        parts=[unquote(x) for x in path[len('/api/release/file/'):].split('/')]
        if len(parts)!=3:return h.send_error(404)
        trace,kind,filename=parts
        try:
            _,_,_,_,dest=selected(trace)
            if kind=='pdf' and filename.endswith('.pdf'):file=dest/'pdf'/filename
            elif kind=='audio' and filename.endswith('.mp3'):file=next((p for p in (dest/'audio').glob('natural-fr-*/'+filename) if p.is_file()),None)
            else:file=None
            if not file or not file.is_file():return h.send_error(404)
            raw=file.read_bytes();h.send_response(200);h.send_header('Content-Type','application/pdf' if kind=='pdf' else 'audio/mpeg');h.send_header('Content-Length',str(len(raw)));h.send_header('Cache-Control','no-store');h.end_headers();h.wfile.write(raw)
        except (ValueError,OSError):h.send_error(404)
        return
    return h.send_error(404)

def post(h):
    try:
        n=int(h.headers.get('Content-Length','0'))
        if n<1 or n>80000:return reply(h,400,{'error':'Invalid payload size'})
        obj=json.loads(h.rfile.read(n)); op=obj.get('action'); name=obj.get('trace');p,root,digest,q,dest=selected(name)
        if op=='status':return reply(h,200,state(name))
        if op not in ('preview','editorial_paid','approve','audio_paid','pdf'):return reply(h,400,{'error':'Unknown action'})
        if not LOCK.acquire(False):return reply(h,409,{'error':'Another generation is in progress'})
        try:
            dest.mkdir(parents=True,exist_ok=True)
            if op=='preview':
                plan=engine.build_plan(p);return reply(h,200,{'plan':plan,'note':'Extractive preview only; not natural dialogue and not approved for audio.'})
            if op=='editorial_paid':
                if obj.get('authorize_meta_charge') is not True:return reply(h,400,{'error':'Explicit Meta charge authorization required'})
                key=os.environ.get('META_API_KEY');
                if not key:return reply(h,503,{'error':'META_API_KEY missing on server'})
                # Execute original adapter with same API call contract as FINAL-100
                import urllib.request as url,urllib.error as urle
                def call(model,instruction,payload,k):
                    data=json.dumps({'model':model,'messages':[{'role':'developer','content':instruction},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]},ensure_ascii=False).encode()
                    req=url.Request('https://api.meta.ai/v1/chat/completions',data=data,headers={'Authorization':'Bearer '+k,'Content-Type':'application/json'},method='POST')
                    with url.urlopen(req,timeout=100) as res:return json.load(res)['choices'][0]['message']['content']
                draft=engine.meta_editor(root,q,call,key);draft.update({'mode':'meta_editorial_unreviewed','source_trace_sha256':digest,'review_status':'pending'})
                
                try:engine.validate_turns(draft['turns'],q,root)
                except (ValueError,KeyError,TypeError) as exc:return reply(h,422,{'error':'Meta editorial draft invalid; no file overwritten','detail':str(exc)[:220],'action':'Regenerate editorial draft only if you authorize a new Meta charge'})
                issues=engine.audit(root,draft['turns']);dest.joinpath('editorial_draft_fr.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
                return reply(h,200,{'draft':draft,'quality_issues':issues,'review_required':True})
            if op=='approve':
                draftfile=dest/'editorial_draft_fr.json'
                if not draftfile.exists():return reply(h,409,{'error':'No Meta editorial draft for this trace'})
                draft=json.loads(draftfile.read_text(encoding='utf8'));engine.verify_reviewed({**draft,'review_status':'approved'},digest,root)
                if obj.get('confirm_reviewed') is not True:return reply(h,400,{'error':'Human approval required'})
                draft['review_status']='approved';draft['approved_turns_sha256']=guard.fingerprint(draft['turns']);(dest/'approved_dialogue_fr.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
                plan=engine.build_plan(p,draft);(dest/'natural_dialogue_plan_fr.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
                return reply(h,200,{'approved':True,'plan':plan})
            if op=='audio_paid':
                if obj.get('authorize_eleven_charge') is not True:return reply(h,400,{'error':'Explicit ElevenLabs charge authorization required'})
                approved=dest/'approved_dialogue_fr.json'
                if not approved.exists():return reply(h,409,{'error':'Approve Meta editorial draft first'})
                draft=json.loads(approved.read_text(encoding='utf8'));guard.checked_fr(draft,digest,root,engine);plan=engine.build_plan(p,draft);guard.assert_safe_before_audio(plan['turns']); manifest=engine.render(plan,dest/'audio')
                files=[x.name for x in manifest.parent.glob('dialogue_*.mp3')]
                return reply(h,200,{'audio':files,'manifest':str(manifest.name)})
            if op=='pdf':
                # FR only: EN must not present French agent text as translated English.
                import branded_live_094 as pdfmod
                logo=PKG/'sustainafrica_logo.jpg'
                target=dest/'pdf';target.mkdir(parents=True,exist_ok=True)
                pdfmod.generate(p,target,'fr',logo=logo)
                files=[f.name for f in target.glob('*.pdf')]
                return reply(h,200,{'pdf':files,'language':'fr','english_status':'translation_not_yet_validated'})
        finally:LOCK.release()
    except Exception as ex:
        # Never echo API key or request payload in error strings
        return reply(h,500,{'error':type(ex).__name__,'detail':str(ex)[:300] if isinstance(ex,(ValueError,FileNotFoundError)) else 'Review server terminal; do not retry paid action blindly.'})

# RELEASE-102 bilingual extension: invoked through same existing 101 route.
_old_post_101=post
_old_get_101=get

def post(h):
    import bilingual_102 as bx
    try:
        n=int(h.headers.get('Content-Length','0'))
        if n<1 or n>80000:return reply(h,400,{'error':'Invalid payload size'})
        raw=h.rfile.read(n);obj=json.loads(raw);op=obj.get('action')
        if op not in ('translate_en_paid','approve_en','pdf_en','audio_en_paid'):
            # Restore bytes for old POST handler without changing any legacy behavior.
            import io
            h.rfile=io.BytesIO(raw)
            return _old_post_101(h)
        name=obj.get('trace');p,root,digest,q,dest=selected(name)
        enfile=dest/'translation_en.json';approved=dest/'approved_translation_en.json'
        frfile=dest/'approved_dialogue_fr.json'
        if not frfile.is_file():return reply(h,409,{'error':'Approve the French natural dialogue first'})
        fr=json.loads(frfile.read_text(encoding='utf8'));fr_fp=guard.checked_fr(fr,digest,root,engine)
        src={'question_fr':q,'final_answer_fr':root['meta_result']['phases'][2]['text'],
            'phases_fr':[x['text'] for x in root['meta_result']['phases']], 'turns_fr':fr['turns'],
            'scientific_evidence_admitted':root['meta_result'].get('scientific_evidence_admitted',0)}
        if not LOCK.acquire(False):return reply(h,409,{'error':'Another operation in progress'})
        try:
            dest.mkdir(parents=True,exist_ok=True)
            if op=='translate_en_paid':
                if obj.get('authorize_meta_charge') is not True:return reply(h,400,{'error':'Explicit Meta charge authorization required'})
                key=os.environ.get('META_API_KEY')
                if not key:return reply(h,503,{'error':'META_API_KEY missing'})
                def caller(instruction,payload):
                    data=json.dumps({'model':'muse-spark-1.3','messages':[{'role':'developer','content':instruction},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]},ensure_ascii=False).encode()
                    req=__import__('urllib.request',fromlist=['Request']).Request('https://api.meta.ai/v1/chat/completions',data=data,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
                    import urllib.request
                    with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)['choices'][0]['message']['content']
                result=engine.find_json(bx.translate(src,caller));bx.validate(src,result)
                result['source_trace_sha256']=digest;result['review_status']='pending';result['translation_of']='approved_french_meta_dialogue';result['source_french_dialogue_sha256']=fr_fp;enfile.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
                return reply(h,200,{'translation':result,'review_required':True})
            if op=='approve_en':
                if obj.get('confirm_reviewed_en') is not True:return reply(h,400,{'error':'English human review required'})
                if not enfile.is_file():return reply(h,409,{'error':'No translated English draft'})
                result=json.loads(enfile.read_text(encoding='utf8'));bx.validate(src,result)
                if result.get('source_trace_sha256')!=digest:return reply(h,409,{'error':'Translation does not match trace'})
                existing_fp=result.get('source_french_dialogue_sha256')
                if existing_fp and existing_fp!=fr_fp:return reply(h,409,{'error':'This draft belongs to an older French approval; translate the currently approved French dialogue before approving.'})
                result['source_french_dialogue_sha256']=fr_fp;result['approved_turns_sha256']=guard.fingerprint(result['turns_en'])
                result['review_status']='approved';approved.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
                return reply(h,200,{'approved_en':True})
            if not approved.is_file():return reply(h,409,{'error':'Approve the English translation first'})
            result=json.loads(approved.read_text(encoding='utf8'));guard.checked_en(result,src,fr_fp,digest,bx)
            guard.assert_safe_before_audio(result['turns_en'])
            if op=='pdf_en':
                target=bx.pdf_english(p,result,dest/'pdf',PKG/'sustainafrica_logo.jpg')
                return reply(h,200,{'pdf':[target.name],'language':'en'})
            if op=='audio_en_paid':
                if obj.get('authorize_eleven_charge') is not True:return reply(h,400,{'error':'Explicit ElevenLabs cost authorization required'})
                manifest=bx.render_audio_en(result|{'source_trace_sha256':digest},dest/'audio')
                return reply(h,200,{'audio':[x.name for x in manifest.parent.glob('dialogue_*.mp3')],'manifest':manifest.name,'language':'en'})
        finally:LOCK.release()
    except Exception as e:
        return reply(h,500,{'error':type(e).__name__,'detail':str(e)[:250] if isinstance(e,(ValueError,FileNotFoundError)) else 'See server log. Do not retry paid requests blindly.'})

def get(h):
    # File handler in 101 already supports pdf EN; add EN audio directory.
    path=urlparse(h.path).path
    if path.startswith('/api/release/file/') and '/audio/' in path:
        parts=[unquote(x) for x in path[len('/api/release/file/'):].split('/')]
        if len(parts)==3:
            name,kind,filename=parts
            try:
                _,_,_,_,dest=selected(name)
                f=next((p for p in (dest/'audio').glob('natural-en-*/'+filename) if p.is_file()),None)
                if f and filename.startswith('dialogue_') and filename.endswith('.mp3'):
                    b=f.read_bytes();h.send_response(200);h.send_header('Content-Type','audio/mpeg');h.send_header('Content-Length',str(len(b)));h.send_header('Cache-Control','no-store');h.end_headers();h.wfile.write(b);return
            except (ValueError,OSError):pass
    return _old_get_101(h)
