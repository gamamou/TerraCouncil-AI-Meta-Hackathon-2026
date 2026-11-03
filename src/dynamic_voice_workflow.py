"""HACK-016F: one-attempt, consent-gated voice synthesis for dynamic sessions.

No automatic retries. Model tokens never sent to the browser. The approved
voice plan is source-extractive only; paid provider action is separate.
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from dynamic_voice_plan import prepare_voice
from render_session_audio import ENDPOINT

IDENTIFIER=re.compile(r"HACK016-[A-Za-z0-9_-]{10,80}\Z")

def local_paths(root,session_id):
    if not isinstance(session_id,str) or not IDENTIFIER.fullmatch(session_id):
        raise ValueError("Invalid HACK016 session")
    base=Path(root)/"Dynamic-Voice"/session_id
    stem="TerraCouncil-"+session_id+"-dynamic-dialogue"
    return {"base":base,"claim":base/"attempt.json",
            "audio":base/(stem+".mp3"),"timing":base/(stem+".timing.json")}

def get_status(root,session_id):
    paths=local_paths(root,session_id)
    if not paths["claim"].is_file():
        return {"state":"NOT_REQUESTED","session_id":session_id}
    try:
        saved=json.loads(paths["claim"].read_text(encoding="utf-8"))
    except (ValueError,OSError):
        return {"state":"INDETERMINATE_DO_NOT_RETRY","session_id":session_id}
    state=saved.get("state","INDETERMINATE_DO_NOT_RETRY")
    if state=="READY" and (not paths["audio"].is_file() or not paths["timing"].is_file()):
        state="INDETERMINATE_DO_NOT_RETRY"
    return {"state":state,"session_id":session_id,
            "script_sha256":saved.get("script_sha256")}

def synthesis(root,trace,voice_spark,voice_wonder,key,consent=False,caller=None,approved_plan=None):
    if consent is not True:
        raise ValueError("Explicit ElevenLabs cost and sharing consent is required")
    if not key:
        raise ValueError("Missing ElevenLabs credentials")
    if approved_plan is None:
        plan=prepare_voice(trace,voice_spark,voice_wonder)
    else:
        from terra_voice_storage_002b import load_verified_approval
        plan=load_verified_approval(root,trace,voice_spark,voice_wonder)
        if plan != approved_plan:
            raise ValueError("Approved script changed before dispatch")
        plan={**plan,
              "payload":{"inputs":plan["inputs"],"model_id":plan["model_id"],"language_code":plan["language_code"]},
              "turns":[{"speaker":step["role"]} for step in trace["steps"]],
              "script_sha256":plan["approval_sha256"],
              "editorial_type":"HUMAN_APPROVED_EDITORIAL_RECONSTRUCTION",
              "scientific_validation":"STRUCTURAL_ONLY_NOT_FIELD_VALIDATED"}
    paths=local_paths(root,plan["session_id"])
    paths["base"].mkdir(parents=True,exist_ok=True)
    # Exclusive claim across browser clicks and process restarts.
    with paths["claim"].open("x",encoding="utf-8") as stream:
        json.dump({"state":"ATTEMPT_STARTED_DO_NOT_RETRY",
                   "session_id":plan["session_id"],
                   "script_sha256":plan["script_sha256"]},stream)
    try:
        if caller is None:
            def caller(payload,secret):
                req=urllib.request.Request(ENDPOINT,method="POST",
                    data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
                    headers={"xi-api-key":secret,"Content-Type":"application/json"})
                with urllib.request.urlopen(req,timeout=180) as resp:
                    return json.load(resp)
        answer=caller(plan["payload"],key)
        if not isinstance(answer,dict) or not isinstance(answer.get("audio_base64"),str):
            raise ValueError("Missing audio in provider response")
        audio=base64.b64decode(answer["audio_base64"],validate=True)
        if len(audio)<1000:raise ValueError("Audio too short")
        segments=answer.get("voice_segments")
        if not isinstance(segments,list) or not segments:
            raise ValueError("Missing provider voice timing")
        timeline=[]
        for segment in segments:
            i=segment.get("dialogue_input_index")
            start=segment.get("start_time_seconds")
            end=segment.get("end_time_seconds")
            if not isinstance(i,int) or not 0<=i<len(plan["turns"]):
                raise ValueError("Unrecognized voice segment")
            if not isinstance(start,(int,float)) or not isinstance(end,(int,float)) or start<0 or end<start:
                raise ValueError("Invalid voice timestamps")
            timeline.append({"turn":i+1,"speaker":plan["turns"][i]["speaker"],
                             "start_seconds":float(start),"end_seconds":float(end)})
        timeline.sort(key=lambda x:x["start_seconds"])
        manifest={"session_id":plan["session_id"],"script_sha256":plan["script_sha256"],
             "evidence_sha256":plan["evidence_sha256"],"editorial_type":plan["editorial_type"],
             "scientific_validation":plan["scientific_validation"],
             "audio_sha256":hashlib.sha256(audio).hexdigest(),
             "audio_filename":paths["audio"].name,"timeline":timeline,
             "generation":"HUMAN_APPROVED_SEPARATELY_AUTHORIZED" if approved_plan is not None else "SOURCE_EXTRACTIVE_SEPARATELY_AUTHORIZED",
             "model":"eleven_v4"}
        paths["audio"].write_bytes(audio)
        paths["timing"].write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        paths["claim"].write_text(json.dumps({"state":"READY","session_id":plan["session_id"],
               "script_sha256":plan["script_sha256"]},indent=2),encoding="utf-8")
    except Exception as error:
        paths["claim"].write_text(json.dumps({"state":"FAILED_OR_INDETERMINATE_DO_NOT_RETRY",
           "session_id":plan["session_id"],"error_type":type(error).__name__,
           "note":"Inspect billing and output before any manually approved new attempt."},
           indent=2),encoding="utf-8")
    return get_status(root,plan["session_id"])

def read_asset(root,session_id,kind):
    if get_status(root,session_id)["state"]!="READY":
        raise ValueError("Audio unavailable")
    paths=local_paths(root,session_id)
    if kind not in ("audio","timing"):
        raise ValueError("Unknown asset")
    return paths[kind].read_bytes()
