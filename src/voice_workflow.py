"""HACK-015 — One-click, explicitly approved, no-retry ElevenLabs dialogue.

All calls are initiated by /api/voice-start on localhost. API key stays in
the Python process, not in browser state. Persist a claim BEFORE the paid call:
even a connection error is not assumed safe to retry. Only local run IDs.
"""
import json
import os
from pathlib import Path
import re
import threading

from approve_oral_script import reviewed_manifest
from render_session_audio import render_one

ID_RE = re.compile(r"HACK008-[A-Za-z0-9_-]{10,80}\Z")

def paths(root,run_id):
    if not isinstance(run_id,str) or not ID_RE.fullmatch(run_id):
        raise ValueError("Invalid saved session ID")
    root=Path(root)
    base=root/"Audio-V15"/run_id
    return {
        "base":base, "claim":base/"attempt.json",
        "audio":base/("TerraCouncil-"+run_id+"-natural-debate.mp3"),
        "timing":base/("TerraCouncil-"+run_id+"-natural-debate.timing.json")
    }

def verified_approval(root,run_id,trace,evidence):
    candidates=sorted((Path(root)/"Approved-Oral-Reviews").glob(run_id+"-*-approved.json"))
    if len(candidates)!=1:
        raise ValueError("Exactly one reviewed oral manuscript is required for this session")
    draft=json.loads(candidates[0].read_text(encoding="utf-8"))
    reviewed=reviewed_manifest(draft,trace,evidence)
    if draft.get("script_sha256")!=reviewed["script_sha256"]:
        raise ValueError("Approved text digest differs from reviewed manuscript")
    return reviewed

def status(root,run_id):
    p=paths(root,run_id)
    if not p["claim"].exists():
        return {"state":"NOT_REQUESTED","session_id":run_id}
    try:
        state=json.loads(p["claim"].read_text(encoding="utf-8"))
    except (ValueError,OSError):
        return {"state":"INDETERMINATE_DO_NOT_RETRY","session_id":run_id}
    complete=p["audio"].is_file() and p["timing"].is_file()
    return {"state":"READY" if state.get("state")=="READY" and complete else
            state.get("state","INDETERMINATE_DO_NOT_RETRY"),
            "session_id":run_id, "audio_ready":complete}

def attempt(root,run_id,trace,evidence,key,voice_spark,voice_wonder,caller=None):
    # Fail closed, before touching ledger, if consent/approval/credentials are absent.
    approved=verified_approval(root,run_id,trace,evidence)
    if not key or not voice_spark or not voice_wonder:
        raise ValueError("ElevenLabs credentials/voice IDs missing in server PowerShell")
    p=paths(root,run_id)
    p["base"].mkdir(parents=True,exist_ok=True)
    # Exclusive create occurs before the paid API call, across process restarts.
    with p["claim"].open("x",encoding="utf-8") as stream:
        json.dump({"state":"ATTEMPT_STARTED_DO_NOT_RETRY",
                   "session_id":run_id,"script_sha256":approved["script_sha256"]},stream)
    try:
        sound,timing=render_one(approved,p["base"],voice_spark,voice_wonder,key,
                                i_reviewed_script=True,approve_cost_and_sharing=True,caller=caller)
        completed={"state":"READY","session_id":run_id,
                   "script_sha256":approved["script_sha256"],
                   "audio":sound.name,"timing":timing.name}
        p["claim"].write_text(json.dumps(completed,ensure_ascii=False,indent=2),encoding="utf-8")
        return status(root,run_id)
    except Exception as exc:
        # A timeout could still have been billed. Never retry without inspecting ElevenLabs history.
        p["claim"].write_text(json.dumps({
            "state":"FAILED_OR_INDETERMINATE_DO_NOT_RETRY",
            "session_id":run_id, "error_type":type(exc).__name__,
            "note":"Check provider history and output files before considering any next paid action."
        },ensure_ascii=False,indent=2),encoding="utf-8")
        return status(root,run_id)

def read_audio(root,run_id,kind):
    if status(root,run_id)["state"]!="READY":
        raise ValueError("No completed audio for this saved session")
    p=paths(root,run_id)
    target=p["audio"] if kind=="audio" else p["timing"]
    if kind not in ("audio","timing"):
        raise ValueError("Unknown audio asset")
    return target.read_bytes()
