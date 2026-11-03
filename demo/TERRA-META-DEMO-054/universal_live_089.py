"""Safe evidence-to-session bridge. Never invokes a model; offline preflight for Live."""
import hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone
from importlib.util import spec_from_file_location,module_from_spec

EXCLUDE_RE=re.compile(r'(?:^|[/\\])(?:FINAL-\d|TERRA-META-FINAL-|\.env|__pycache__|FINAL-\d+-BACKUPS)',re.I)
BLOCK_RE=re.compile(r'(?:api[_ -]?calls?|tts|audio|voice|source_turn|spoken_turn|moderator|\btoken\b|\bpassword\b|debug|draft|audit|readme|request|prompt)',re.I)
SCIENCE_HINT=re.compile(r'(?:evidence|source|science|dataset|observation|indicator|metric|geojson|agro|water|flood|boke|mining)',re.I)


def _load_engine(root):
    module_path=Path(__file__).with_name('evidence_085.py')
    spec=spec_from_file_location('terra_evidence_085_089',module_path)
    mod=module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def make_case(question,language,roots,limit=12):
    if not isinstance(question,str) or not 20<=len(question.strip())<=1200:raise ValueError('question length 20..1200')
    if language not in ('fr','en'):raise ValueError('invalid language')
    if not isinstance(roots,(list,tuple)) or not roots:raise ValueError('no roots configured')
    engine=_load_engine(roots)
    records,warnings=engine.inventory(roots)
    lookup={r['id']:r for r in records}
    candidates=[];seen=set();filtered=[]
    # Rank all indexed candidates, then filter out technical artifacts before selection.
    for candidate in engine.find(records,question,limit=min(500,len(records))):
        source=lookup[candidate['id']]
        filename=source['name'];path=source['path']
        if EXCLUDE_RE.search(path) or BLOCK_RE.search(filename):
            filtered.append({'name':filename,'reason':'TECHNICAL_OR_HISTORIC'});continue
        if source['file_sha256'] in seen:continue
        seen.add(source['file_sha256'])
        # Only corpus candidates, never promote lexical matches to verified scientific measurements.
        candidates.append({'name':filename,'sha256':source['file_sha256'],
            'path':path,'matching_terms':candidate['match_terms'],
            'discovery_score':candidate['score'],'evidence_status':'UNVERIFIED_CANDIDATE',
            'admitted_as_scientific_measurement':False})
        if len(candidates)>=limit:break
    # Do not claim absence of relevant evidence based on lexical retrieval alone.
    status='CANDIDATES_UNVERIFIED' if candidates else 'NO_MATCHING_LOCAL_CANDIDATES'
    return {'schema':'terra-universal-live-evidence/1.0','created_at':datetime.now(timezone.utc).isoformat(),
        'question':question.strip(),'question_sha256':hashlib.sha256(question.strip().encode()).hexdigest(),
        'language':language,'searched_roots':[str(Path(r)) for r in roots],
        'indexed_files':len(records),'candidate_count':len(candidates),'candidates':candidates,
        'excluded_technical_matches':filtered[:30], 'warnings':warnings[:30],
        'evidence_status':status,'scientific_admission':'NOT_PERFORMED',
        'reasoning_guardrails':[
            'Use candidate sources only with correct provenance and scope; do not invent missing facts.',
            'If territory-specific proof is absent, state that it was not located in the indexed corpus, not that it does not exist.',
            'Distinguish proposed data-collection priorities from data-supported investment rankings.',
            'Never treat historic agent debate as independent scientific evidence.'
        ],'meta_executed':False,'pdf_generated':False,'audio_generated':False,
        'ready_for_live_execution':False,
        'reason':'Existing Meta model adapter has not yet been verified to support arbitrary questions. Evidence discovery preflight only.'}


def roots_for_server(server):
    server=Path(server).resolve()
    repo=server.parents[3]
    return [Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs',repo/'data'/'science_packages']


def route(handler,traces,server_file):
    from free_question_guard_084 import json_reply
    try:
        size=int(handler.headers.get('Content-Length','0'))
        if size<1 or size>8192:return json_reply(handler,400,{'error':'invalid_size'})
        payload=json.loads(handler.rfile.read(size))
        if not isinstance(payload,dict):return json_reply(handler,400,{'error':'invalid_payload'})
        result=make_case(payload.get('question'),payload.get('language','fr'),roots_for_server(server_file))
        # This route deliberately cannot dispatch paid calls or reuse preset FLOOD evidence.
        return json_reply(handler,200,result)
    except (ValueError,TypeError,json.JSONDecodeError):
        return json_reply(handler,400,{'error':'invalid_question'})
    except Exception as exc:
        return json_reply(handler,503,{'error':'evidence_discovery_unavailable','type':type(exc).__name__})
