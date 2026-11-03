"""Question eligibility and source-inventory guard. No external calls."""
import json,hashlib,re
from pathlib import Path

def json_reply(handler,code,data):
    body=json.dumps(data,ensure_ascii=False).encode('utf8')
    handler.send_response(code)
    handler.send_header('Content-Type','application/json; charset=utf-8')
    handler.send_header('Cache-Control','no-store')
    handler.send_header('Content-Length',str(len(body)))
    handler.end_headers();handler.wfile.write(body)

def assess_request(data,traces):
    if not isinstance(data,dict):raise ValueError('Expected object')
    question=data.get('question')
    if not isinstance(question,str):raise ValueError('Missing question')
    question=question.strip()
    if len(question)<20 or len(question)>1200:raise ValueError('Question must be 20-1200 characters')
    if any(ord(c)<32 and c not in '\n\t' for c in question):raise ValueError('Control character')
    lang=data.get('language','fr')
    if lang not in ('fr','en'):raise ValueError('Invalid language')
    folder=Path(traces)
    # Audit only: source existence does not establish admissibility to answer arbitrary question.
    evidence=[]
    if folder.exists():
        for pattern in ('SCIENCE-021-FLOOD-*.json',):
            for p in sorted(folder.glob(pattern))[-10:]:
                evidence.append({'filename':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    return {'status':'QUESTION_RECEIVED__EXECUTION_NOT_READY',
        'question':question,'question_sha256':hashlib.sha256(question.encode('utf8')).hexdigest(),
        'language':lang,'available_candidate_packets':evidence,
        'source_admissibility':'NOT_YET_ASSESSED_FOR_QUESTION',
        'meta_calls':0,'elevenlabs_calls':0,'pdf_generated':False,'audio_generated':False,
        'next_dependency':'Review terra_science_024.py and SCIENCE-021-FLOOD packet structure before implementing new-question execution.'}
