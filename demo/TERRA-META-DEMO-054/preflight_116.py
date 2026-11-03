"""Build offline, non-fabricated inputs for the existing Meta Live 3-stage protocol.

This module NEVER executes Meta or ElevenLabs calls. It prepares an explicit evidence
candidate work-order for a subsequent operator-controlled recording run.
"""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent

def compile_workorder(root,pilot,lang):
    root=Path(root)
    data=json.loads((root/'scientific_116.json').read_text(encoding='utf8'))
    briefs=json.loads((root/'pilots_115.json').read_text(encoding='utf8'))
    if pilot not in ('BOKE','FLOOD','AGRO') or lang not in ('fr','en'):
        raise ValueError('Unknown pilot/language')
    a=data['pilots'][pilot]
    item=briefs[pilot][lang]
    payload={
      'schema':'terra-pilot-116-workorder/1.0',
      'pilot_id':pilot,'language':lang,'question':item['question'],
      'protocol':data['scientific_policy']['protocol'],
      'pilot_context_from_existing_editorial_brief':a['context_already_in_demo115'],
      'unverified_candidate_sources':a['candidate_sources'],
      'missing_local_evidence':a['evidence_gaps'],
      'stage_instructions':{k:a[k] for k in ('spark_initial','wonder_critique','spark_revision')},
      'local_verified_evidence_newly_admitted':0,
      'guardrails':['Use actual Meta calls in a separate authorized operator run before labeling as a real Meta deliberation.',
       'Never turn a discovery candidate into admitted evidence without provenance, licensing, time/space coverage and QA.',
       'No fabricated numbers, source-derived local findings, or fake debate/audio recordings.',
       'Audio transcripts must remain tied to this question, pilot, language and later source-trace SHA-256.'],
      'recording_status':'NOT_RUN'
    }
    canonical=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')
    payload['workorder_sha256']=hashlib.sha256(canonical).hexdigest()
    return payload

def write_all(root):
    root=Path(root);out=root/'pilot_workorders_116';out.mkdir(exist_ok=True)
    for p in ('BOKE','FLOOD','AGRO'):
        for l in ('fr','en'):
            obj=compile_workorder(root,p,l)
            (out/f'{p}-{l}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
    return out
if __name__=='__main__':
    base=Path(sys.argv[1]) if len(sys.argv)>1 else HERE
    print('Six non-paid, candidate-only scientific work orders:',write_all(base))
