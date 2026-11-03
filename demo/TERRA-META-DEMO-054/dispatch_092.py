"""FINAL-092 explicit-cost live Meta dispatch. Local only. No PDF/audio claims."""
import json, os, sys, importlib.util
from pathlib import Path
from datetime import datetime, timezone


def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    if not spec or not spec.loader: raise RuntimeError('Module missing')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dispatch(payload,server_path,call=None,case_maker=None):
    if not isinstance(payload,dict):raise ValueError('Invalid payload')
    if set(payload)-{'question','language','confirm_meta_charges'}:raise ValueError('Unexpected fields')
    q=payload.get('question');lang=payload.get('language')
    if not isinstance(q,str) or not 20<=len(q.strip())<=1200 or lang not in ('fr','en'):raise ValueError('Invalid question')
    if payload.get('confirm_meta_charges') is not True:raise PermissionError('Explicit consent required')
    key=os.environ.get('META_API_KEY')
    if not key and call is None:raise RuntimeError('META_API_KEY missing')
    server=Path(server_path).resolve()
    repo=server.parents[3]
    if case_maker is None:
        maker=load(server.parent/'universal_live_089.py','terra_089_092')
        case_maker=lambda question,language:maker.make_case(question,language,maker.roots_for_server(server))
    case=case_maker(q.strip(),lang)
    engine=load(server.parent/'live_091.py','terra_091_092')
    if call is None:
        sys.path.insert(0,str(repo/'src'))
        from council import meta_call
        call=meta_call
    result=engine.execute(case,call,key or 'TEST_ONLY',consent=True,max_calls=3)
    folder=Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs'
    folder.mkdir(parents=True,exist_ok=True)
    filename='FINAL-092-QUESTION-LIVE-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.json'
    output=folder/filename
    with output.open('x',encoding='utf8') as fh:json.dump({'evidence_case':case,'meta_result':result},fh,ensure_ascii=False,indent=2)
    return {'schema':'terra-live-092/1.0','status':result['status'],'question':q.strip(),'language':lang,
      'scientific_evidence_admitted':result.get('scientific_evidence_admitted',0),
      'phases':result.get('phases',[]),'saved_trace':filename,'pdf_generated':False,'audio_generated':False,
      'human_review_required':True,'warning':'Model responses are not independently verified; no scientific local facts admitted.'}


def route(handler,server_path):
    from free_question_guard_084 import json_reply
    try:
        size=int(handler.headers.get('Content-Length','0'))
        if size<1 or size>8192:return json_reply(handler,400,{'error':'invalid_request_size'})
        payload=json.loads(handler.rfile.read(size))
        result=dispatch(payload,server_path)
        return json_reply(handler,200 if not result['status'].startswith('INCOMPLETE') else 502,result)
    except PermissionError:return json_reply(handler,403,{'error':'explicit_meta_consent_required'})
    except (ValueError,TypeError,json.JSONDecodeError):return json_reply(handler,400,{'error':'invalid_question'})
    except RuntimeError as exc:return json_reply(handler,503,{'error':str(exc)})
    except Exception as exc:return json_reply(handler,500,{'error':'live_session_failed','type':type(exc).__name__,'do_not_retry_automatically':True})
