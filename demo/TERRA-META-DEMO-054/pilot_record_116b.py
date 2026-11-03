"""RELEASE 116B: strictly trace- and evidence-bound authentic pilot recordings.

record: 3 actual Meta calls using unchanged live_091.execute protocol, explicit charge opt-in.
synthesize: optionally uses existing auto_113 backend, explicit charge opt-in.
publish: binds authenticated generated MP3s to pilot/language without new API calls.
All operations one pilot/language at a time; never automatically retry paid operations.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, re, shutil, sys
from datetime import datetime, timezone
from urllib.parse import quote

KEYS=('BOKE','FLOOD','AGRO'); LANGS=('fr','en')
TRACE_RE=re.compile(r'^FINAL-092-QUESTION-LIVE-[0-9-]+\.json$')
DATA=Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write_atomic(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(path)
def check_inputs(root,pilot,lang):
    if pilot not in KEYS or lang not in LANGS:raise ValueError('Invalid pilot/language')
    work=load_json(root/'pilot_workorders_116'/f'{pilot}-{lang}.json')
    if work.get('pilot_id')!=pilot or work.get('language')!=lang or work.get('recording_status')!='NOT_RUN':raise ValueError('Work order mismatch')
    expected=work.pop('workorder_sha256')
    content=json.dumps(work,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')
    if hashlib.sha256(content).hexdigest()!=expected:raise ValueError('Work order fingerprint mismatch')
    work['workorder_sha256']=expected
    if work.get('local_verified_evidence_newly_admitted')!=0 or work.get('protocol')!=['spark_initial','wonder_critique','spark_revision']:
        raise ValueError('Unexpected evidence admission/protocol')
    return work

def load_trace(root,pilot,lang,trace_name):
    work=check_inputs(root,pilot,lang)
    if not TRACE_RE.fullmatch(trace_name):raise ValueError('Unsafe trace name')
    path=DATA/trace_name
    if not path.is_file():raise ValueError('No recorded Meta trace: '+trace_name)
    obj=load_json(path);result=obj.get('meta_result',{});case=obj.get('evidence_case',{})
    stages=result.get('phases',[])
    if [p.get('phase') for p in stages]!=work['protocol']:raise ValueError('Not a complete 3-stage Live Meta deliberation')
    if not all(isinstance(p.get('text'),str) and p['text'].strip() and str(p.get('model','')).startswith('muse-') for p in stages):
        raise ValueError('Missing genuine Meta model output stages')
    if result.get('status','').startswith('INCOMPLETE') or result.get('language')!=lang or case.get('language')!=lang:
        raise ValueError('Language or completion status mismatch')
    if result.get('question')!=work['question'] or case.get('question')!=work['question']:
        raise ValueError('Trace question does not match the selected Demo pilot')
    if result.get('scientific_evidence_admitted')!=0 or case.get('scientific_admission')!='NOT_PERFORMED':
        raise ValueError('Scientific evidence status requires review')
    meta=obj.get('pilot_record_116b')
    if not isinstance(meta,dict) or meta.get('pilot_id')!=pilot or meta.get('language')!=lang or meta.get('workorder_sha256')!=work['workorder_sha256']:
        raise ValueError('Not a RELEASE-116B authentic pilot recording')
    return work,path,obj,sha(path)

def record(root,pilot,lang,authorize=False,caller=None):
    work=check_inputs(root,pilot,lang)
    if not authorize:raise PermissionError('Explicit --authorize-meta required; no API requests attempted')
    key=os.environ.get('META_API_KEY')
    if not key and caller is None:raise ValueError('META_API_KEY missing')
    engine=root/'live_091.py'
    if not engine.is_file():raise ValueError('Existing Live Meta engine live_091.py unavailable')
    spec=importlib.util.spec_from_file_location('terra_live091_for116b',engine)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    if caller is None:
        # Same Meta implementation used in FINAL-092 Live. No alternate/fake model.
        repo=root.parents[2]
        src=repo/'src'
        if not (src/'council.py').is_file():raise ValueError('Existing repo/src/council.py unavailable')
        sys.path.insert(0,str(src));from council import meta_call
        caller=meta_call
    context={'workorder_sha256':work['workorder_sha256'],
       'context_from_editorial_brief_not_field_verified':work['pilot_context_from_existing_editorial_brief'],
       'unverified_candidate_sources_not_admitted':work['unverified_candidate_sources'],
       'missing_local_evidence':work['missing_local_evidence'],
       'stage_research_guide_not_evidence':work['stage_instructions']}
    def grounded_caller(model,instruction,payload,api_key):
        enriched={**payload,'pilot_research_context':context}
        return caller(model,instruction+'\nResearch guide is NOT observational evidence. Never claim it proves local facts.',enriched,api_key)
    case={'schema':'terra-universal-live-evidence/1.0','question':work['question'],
          'language':lang,'scientific_admission':'NOT_PERFORMED','indexed_files':0,'candidates':[],
          'pilot_context_status':'CANDIDATE_ONLY'}
    result=mod.execute(case,grounded_caller,key or 'TEST_ONLY',consent=True,max_calls=3)
    obj={'evidence_case':case,'meta_result':result,'pilot_record_116b':{
        'pilot_id':pilot,'language':lang,'workorder_sha256':work['workorder_sha256'],
        'recorded_utc':datetime.now(timezone.utc).isoformat(),
        'research_context_attached_to_each_actual_Meta_call':True,'field_validated':False}}
    DATA.mkdir(parents=True,exist_ok=True)
    name='FINAL-092-QUESTION-LIVE-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.json'
    path=DATA/name
    with path.open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
    index=root/'pilot_record_index_116b.json'
    old=load_json(index) if index.is_file() else {}
    if result.get('status','').startswith('INCOMPLETE'):
        print('INCOMPLETE:',path,'— saved; no automatic retry; may already have incurred costs')
        raise ValueError('One or more Meta calls failed; trace saved, do not retry blindly')
    load_trace(root,pilot,lang,name)
    old[f'{pilot}-{lang}']={'trace':name,'sha256':sha(path),'workorder_sha256':work['workorder_sha256']}
    write_atomic(index,old)
    print('AUTHENTIC META RECORDING SAVED:',name,'SHA:',sha(path))
    return name

def verify_index(root,pilot,lang):
    idx=root/'pilot_record_index_116b.json'
    if not idx.is_file():raise ValueError('Record this pilot via 116B first')
    rec=load_json(idx).get(f'{pilot}-{lang}')
    if not isinstance(rec,dict):raise ValueError('No authentic recording for pilot/language')
    work,path,obj,hashval=load_trace(root,pilot,lang,rec['trace'])
    if hashval!=rec.get('sha256'):raise ValueError('Recorded trace has changed')
    return rec,work,path,obj

def synthesize(root,pilot,lang,allow_meta=False,allow_eleven=False):
    rec,work,path,obj=verify_index(root,pilot,lang)
    if not allow_meta or not allow_eleven:
        raise PermissionError('Both --authorize-meta-editorial and --authorize-eleven are required; no automatic retries')
    # Existing RELEASE-113 editor and ElevenLabs engine, exact immutable source trace.
    sys.path.insert(0,str(root))
    import deliverables_112 as core
    import auto_113
    ctx=core.context(rec['trace'],lang)
    if ctx['sha']!=rec['sha256']:raise ValueError('Trace changed before audio')
    # RELEASE-119: quality-gated scientific moderation, scoped to Demo only.
    from pilot_editor_119 import synthesize as synthesize_119
    return synthesize_119(root,pilot,lang,allow_meta,allow_eleven)
    if not answer.get('audio_ready'):raise ValueError('Audio not verified; no automatic retry')
    print('REAL AUDIO VERIFIED:',len(answer['audio']),'segment(s) for',pilot,lang)
    return answer

def publish(root,pilot,lang):
    rec,work,path,obj=verify_index(root,pilot,lang)
    sys.path.insert(0,str(root));import deliverables_112 as core;import auto_113
    ctx=core.context(rec['trace'],lang)
    if ctx['sha']!=rec['sha256']:raise ValueError('Scientific trace fingerprint mismatch')
    turns=auto_113.load_script(ctx)
    if not turns:raise ValueError('No verified editorial dialogue for this exact trace')
    found=core.current_audio(ctx,turns)
    if not found:raise ValueError('No verified ElevenLabs MP3 files for this exact trace; no demo audio published')
    media=root/'council_sessions';media.mkdir(exist_ok=True)
    # RELEASE-119: new dialogue versions receive unique audio filenames.
    import hashlib as _hashlib
    _script_hash=_hashlib.sha256(json.dumps(turns,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')).hexdigest()[:8]
    published=[];prefix='TC116B-'+pilot+'-'+lang+'-'+rec['sha256'][:12]+'-'+_script_hash
    for i,source in enumerate(found,1):
        if source.stat().st_size<1000:raise ValueError('Audio file empty')
        target=media/(prefix+'-'+f'{i:02d}'+'.mp3')
        if target.exists() and sha(target)!=sha(source):raise ValueError('Existing published audio mismatch: refused overwrite')
        if not target.exists():shutil.copy2(source,target)
        published.append({'filename':target.name,'sha256':sha(target),'sequence':i,'role':'council'})
    manifest={'schema':'terra-pilot-audio-116b/1.0','status':'COMPLETE','pilot_id':pilot,'language':lang,
      'question':work['question'],'workorder_sha256':work['workorder_sha256'],
      'source_trace':rec['trace'],'source_trace_sha256':rec['sha256'],
      'dialogue_status':'automatically_checked_not_field_validated','segments':published}
    destination=root/'pilot_audio_116b'/f'{pilot}-{lang}.json';write_atomic(destination,manifest)
    print('PUBLISHED DEMO PILOT AUDIO:',pilot,lang,'segments:',len(published))
    return destination

def main(argv=None):
    p=argparse.ArgumentParser(description='116B genuine pilot recording: explicit costs; one pilot/language at a time')
    p.add_argument('action',choices=['preflight','record','synthesize','publish'])
    p.add_argument('--root',required=True);p.add_argument('--pilot',choices=KEYS,required=True);p.add_argument('--lang',choices=LANGS,required=True)
    p.add_argument('--authorize-meta',action='store_true');p.add_argument('--authorize-meta-editorial',action='store_true')
    p.add_argument('--authorize-eleven',action='store_true')
    a=p.parse_args(argv);root=Path(a.root).resolve()
    if a.action=='preflight':
        o=check_inputs(root,a.pilot,a.lang);print('READY — candidate-only',o['pilot_id'],o['language'],'fingerprint',o['workorder_sha256']);return
    if a.action=='record':record(root,a.pilot,a.lang,authorize=a.authorize_meta);return
    if a.action=='synthesize':synthesize(root,a.pilot,a.lang,a.authorize_meta_editorial,a.authorize_eleven);return
    publish(root,a.pilot,a.lang)
if __name__=='__main__':main()
