"""Read-only, real-Meta trace adapter. Never synthesizes model responses."""
import json
from pathlib import Path

def normalize(data):
    if not isinstance(data,dict) or data.get('mode') not in ('LIVE_META','LIVE_META_CONTINUATION') or data.get('error'):
        return None
    pilot=data.get('pilot')
    if pilot not in ('BOKE','AGRO','FLOOD'):
        return None
    if pilot=='BOKE':
        if not isinstance(data.get('steps'),list) or not data['steps'] or not isinstance(data.get('decision'),dict) or data.get('status')!='PROVISIONAL_HUMAN_REVIEW':return None
        steps=data['steps']; consults=data.get('consultations') or []; decision=data['decision']
    elif pilot=='AGRO':
        if not isinstance(data.get('new_interventions'),list) or not data['new_interventions'] or not isinstance(data.get('decision'),dict) or data.get('status')!='PROVISIONAL_HUMAN_REVIEW':return None
        # Preserve original findings and final live continuation as distinct stages
        orig=data.get('original_findings') or []
        steps=[{'model':'muse-spark-1.3','action':{'action':'record_finding','summary':str(x.get('summary') or x.get('finding') or '')}} for x in orig if isinstance(x,dict)] + data['new_interventions']
        consults=data.get('consultations') or [];decision=data['decision']
    else:
        result=data.get('result') or {};steps=result.get('steps') or [];consults=result.get('consultations') or [];decision=result.get('decision')
        if not steps or not decision:return None
    if any((not isinstance(s,dict)) for s in steps):return None
    return {'pilot':pilot,'mode':data['mode'],'status':data.get('status'),'result':{'steps':steps,'consultations':consults,'decision':decision},'scientific_scope':'PROVISIONAL_HUMAN_REVIEW','api_attempts':data.get('api_attempts'),'original_trace_timestamp':data.get('timestamp_utc')}

def discover(folder):
    folder=Path(folder)
    patterns={'BOKE':['DEMO-040-BOKE-LIVE-*.json'], 'AGRO':['DEMO-035-AGRO-CONTINUATION-*.json'], 'FLOOD':['SCIENCE-024-LIVE-*.json']}
    found={}
    for pilot,globs in patterns.items():
        for pat in globs:
            for path in sorted(folder.glob(pat),key=lambda p:p.stat().st_mtime,reverse=True):
                try:
                    data=json.loads(path.read_text(encoding='utf-8-sig'));norm=normalize(data)
                    # Flood older envelopes may lack top-level pilot.
                    if pilot=='FLOOD' and not norm and data.get('mode')=='LIVE_META' and isinstance((data.get('result') or {}).get('steps'),list):
                        data=dict(data,pilot='FLOOD');norm=normalize(data)
                    if norm and norm['pilot']==pilot:
                        found[pilot]=norm;break
                except (OSError,ValueError,TypeError):pass
            if pilot in found:break
    return found
