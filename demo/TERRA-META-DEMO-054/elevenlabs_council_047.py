"""ElevenLabs voice production from authentic TerraCouncil traces only.
Uses existing jury_adapter_041 and editorial oral filter. Audio is TTS of adapted real model text, not recorded model speech.
"""
import argparse,json,os,re,sys,urllib.request,hashlib,time
from pathlib import Path
from jury_adapter_041 import discover
ROOT=Path(__file__).parent
TRACES=Path.home()/"Documents"/"TerraCouncil-Scientific-Inputs"
def oral_filter(action):
    """Preserve semantic content; remove JSON formatting and machine-only tokens. No generative rewriting."""
    if isinstance(action,str):return clean(action)
    if not isinstance(action,dict):return ''
    txt=action.get('summary') or action.get('finding') or action.get('perspective') or action.get('question')
    if not txt and action.get('action')=='conclude':txt=action.get('summary')
    return clean(str(txt)) if txt else ''
def clean(s):
    s=re.sub(r'[_\n\t]+',' ',s)
    s=re.sub(r'\s+',' ',s).strip()
    return s[:4000]
def segments(tr):
    items=[]
    steps=tr.get('result',{}).get('steps') or []
    for i,st in enumerate(steps):
        act=st.get('action') or st.get('response') or {}
        txt=oral_filter(act)
        if txt:items.append({'speaker':'wonder' if 'wonder' in str(st.get('model','')).lower() else 'spark','text':txt,'source_step':i})
    for i,ct in enumerate(tr.get('result',{}).get('consultations') or []):
        if ct.get('status')!='EXECUTED':continue
        txt=oral_filter(ct.get('response') or {})
        if txt:items.append({'speaker':'wonder','text':txt,'source_consultation':i})
    dec=tr.get('result',{}).get('decision') or {}
    dt=oral_filter(dec)
    if dt and (not items or dt!=items[-1]['text']):items.append({'speaker':'spark','text':dt,'source_decision':True})
    return items

def generate(api_key,voice_id,text,model):
    body=json.dumps({'text':text,'model_id':model,'voice_settings':{'stability':0.55,'similarity_boost':0.75}}).encode()
    url='https://api.elevenlabs.io/v1/text-to-speech/'+voice_id+'?output_format=mp3_44100_128'
    req=urllib.request.Request(url,data=body,headers={'xi-api-key':api_key,'Content-Type':'application/json','Accept':'audio/mpeg'},method='POST')
    with urllib.request.urlopen(req,timeout=90) as resp:
        data=resp.read()
    if len(data)<128:raise ValueError('Invalid audio payload')
    return data

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pilot',choices=['BOKE','FLOOD','AGRO','ALL'],default='ALL')
    ap.add_argument('--list',action='store_true',help='Preview exact oral text; no API calls')
    ap.add_argument('--generate',action='store_true',help='Explicitly generate new MP3s using ElevenLabs')
    ap.add_argument('--model',default='eleven_multilingual_v2')
    ap.add_argument('--max-segments',type=int,default=100)
    args=ap.parse_args()
    if args.list==args.generate:ap.error('Choose exactly one of --list or --generate')
    traces=discover(TRACES)
    pilots=['BOKE','FLOOD','AGRO'] if args.pilot=='ALL' else [args.pilot]
    if args.generate:
        key=os.environ.get('ELEVENLABS_API_KEY')
        voices={'spark':os.environ.get('ELEVENLABS_SPARK_VOICE_ID'),'wonder':os.environ.get('ELEVENLABS_WONDER_VOICE_ID')}
        if not key or not voices['spark']:ap.error('ELEVENLABS_API_KEY and ELEVENLABS_SPARK_VOICE_ID required')
    all_manifest={};total=0
    for pilot in pilots:
        tr=traces.get(pilot)
        if not tr:
            print('MISSING_AUTHENTIC_TRACE:',pilot);continue
        items=segments(tr);output=[]
        for i,item in enumerate(items):
            if total>=args.max_segments:break
            speaker=item['speaker'];text=item['text'];name=f'{pilot.lower()}_{i:02d}_{speaker}.mp3'
            print(f'{pilot} [{i}] {speaker.upper()}: {text[:200]}')
            record={'speaker':speaker,'text':text,'source_step':item.get('source_step'),'source_decision':item.get('source_decision',False),'source_consultation':item.get('source_consultation'),'mp3':name,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'adaptation':'deterministic_oral_filter_from_authentic_meta_trace','language':'en'}
            if args.generate:
                if speaker=='wonder' and not voices['wonder']:raise ValueError('Actual Wonder contribution found but no Wonder voice ID configured')
                dst=ROOT/'voice_audio'/name
                if dst.exists():print('SKIP_EXISTING:',name)
                else:
                    data=generate(key,voices[speaker],text,args.model)
                    with dst.open('xb') as f:f.write(data)
                    print('GENERATED:',dst,'bytes:',len(data))
            output.append(record);total+=1
        all_manifest[pilot]=output
    if args.generate:
        manifest=ROOT/'voice_audio'/'manifest.json'
        if manifest.exists():
            old=json.loads(manifest.read_text(encoding='utf-8'))
            old.update(all_manifest);all_manifest=old
        manifest.write_text(json.dumps(all_manifest,ensure_ascii=False,indent=2),encoding='utf8')
        print('AUDIO_MANIFEST:',manifest)
    else:print('PREVIEW_ONLY: NO_API_CALLS')
    print('SEGMENTS:',total)
if __name__=='__main__':main()
