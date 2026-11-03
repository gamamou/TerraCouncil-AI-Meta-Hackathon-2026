"""HACK-010 — optional reviewed session-specific ElevenLabs v4 dialogue.

No background calls, no automatic retries. No TTS unless all explicit flags,
private key, and source review are provided. Uses ElevenLabs timestamps to
enable speaker visualization. This is editorial reconstruction, NOT verbatim.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error

from natural_french_dialogue import oral_storyboard, write_review_files
from approve_oral_script import reviewed_manifest

ENDPOINT = "https://api.elevenlabs.io/v1/text-to-dialogue/with-timestamps?output_format=mp3_44100_128"
MAX_CHARACTERS = 2000

def build_payload(manifest, spark_voice, wonder_voice):
    if not spark_voice or not wonder_voice or spark_voice == wonder_voice:
        raise ValueError("Two distinct voice IDs are needed for Spark and Wonder")
    if (manifest["recording_status"] != "NOT_GENERATED"
        or not manifest["human_review_required"]
        or manifest.get("human_review_complete") is not True
        or manifest.get("approval_type") != "USER_REVIEWED_EDITORIAL_RECONSTRUCTION"):
        raise ValueError("A session-bound approved oral script is required before ElevenLabs")
    turns = manifest["turns"]
    if len(turns) != 4:
        raise ValueError("Exactly four reviewed interventions expected")
    inputs = []
    for t in turns:
        txt = t["text_to_review"]
        if any(ch.isdigit() for ch in txt) or any(s in txt for s in ("<",">","{","}","_","#","@","\\","|","*")):
            raise ValueError("Speech script includes raw technical symbols or digits")
        inputs.append({"text":txt,"voice_id":wonder_voice if t["source_model"]=="muse-wonder-1.0" else spark_voice})
    total = sum(len(x["text"]) for x in inputs)
    if total > MAX_CHARACTERS:
        raise ValueError("Dialogue exceeds safe 2000-character single-call limit; shorten or split after human review")
    return {"inputs":inputs,"model_id":"eleven_v4","language_code":"fr"}

def render_one(manifest, out_dir, spark_voice, wonder_voice, key, *,
               i_reviewed_script=False, approve_cost_and_sharing=False, caller=None):
    if not i_reviewed_script or not approve_cost_and_sharing:
        raise ValueError("Explicit human script review and ElevenLabs sharing/cost approval required")
    if not key:
        raise ValueError("ELEVENLABS_API_KEY must be set locally")
    payload=build_payload(manifest,spark_voice,wonder_voice)
    directory=Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    base_name="TerraCouncil-"+manifest["session_id"]+"-natural-debate"
    audio_path=directory/(base_name+".mp3")
    timing_path=directory/(base_name+".timing.json")
    if audio_path.exists() or timing_path.exists():
        raise ValueError("Output exists; never overwrite or blindly retry a paid dialogue call")
    if caller is None:
        def caller(request_payload, api_key):
            request=urllib.request.Request(
                ENDPOINT,
                data=json.dumps(request_payload,ensure_ascii=False).encode("utf-8"),
                method="POST",
                headers={"xi-api-key":api_key,"Content-Type":"application/json"}
            )
            with urllib.request.urlopen(request,timeout=180) as response:
                return json.load(response)
    # One external call at most. Failures may have been billed: caller must not retry.
    result=caller(payload,key)
    if not isinstance(result,dict) or not isinstance(result.get("audio_base64"),str):
        raise ValueError("ElevenLabs returned no complete audio; check billing/history before retry")
    sound=base64.b64decode(result["audio_base64"],validate=True)
    if len(sound)<1000:
        raise ValueError("Audio response too short; check before retrying")
    segments=result.get("voice_segments",[])
    if not isinstance(segments,list) or not segments:
        raise ValueError("Missing voice timestamps; check before retrying")
    timeline=[]
    for segment in segments:
        index=segment.get("dialogue_input_index")
        start=segment.get("start_time_seconds")
        end=segment.get("end_time_seconds")
        if not isinstance(index,int) or not 0<=index<len(manifest["turns"]):
            raise ValueError("Invalid timeline turn index")
        if not all(isinstance(v,(float,int)) for v in (start,end)) or end<start:
            raise ValueError("Invalid timeline timestamps")
        timeline.append({"turn":index+1,"speaker":manifest["turns"][index]["speaker"],
                         "start_seconds":float(start),"end_seconds":float(end)})
    timeline.sort(key=lambda t:t["start_seconds"])
    meta={
        "session_id":manifest["session_id"], "editorial_type":manifest["type"],
        "scientific_validation":manifest["scientific_validation"],
        "script_sha256":manifest["script_sha256"],
        "model":"eleven_v4","generation":"HUMAN_REVIEW_CONFIRMED",
        "audio_sha256":hashlib.sha256(sound).hexdigest(),
        "audio_filename":audio_path.name,
        "timeline":timeline,
        "disclaimer":"Audio reconstruit éditorialement, non transcription verbatim. Conserver les textes scientifiques originaux pour audit."
    }
    audio_path.write_bytes(sound)
    timing_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return audio_path,timing_path

def main():
    p=argparse.ArgumentParser(description="TTS naturel français TerraCouncil")
    p.add_argument("--session",required=True)
    p.add_argument("--evidence",required=True)
    p.add_argument("--out-dir",required=True)
    p.add_argument("--approved-manifest",help="Approved script JSON from approve_oral_script.py")
    p.add_argument("--send-to-elevenlabs",action="store_true")
    p.add_argument("--i-reviewed-script",action="store_true")
    p.add_argument("--i-approve-cost-and-sharing",action="store_true")
    args=p.parse_args()
    session=json.loads(Path(args.session).read_text(encoding="utf-8"))
    evidence=json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    manifest=oral_storyboard(session,evidence)
    if not args.send_to_elevenlabs:
        files=write_review_files(manifest,args.out_dir)
        print("STATUS: HUMAN_REVIEW_REQUIRED, NO_TTS_CALL")
        print("REVIEW_TEXT:",files[1]);print("REVIEW_MANIFEST:",files[0]);return
    if not args.approved_manifest:
        raise ValueError("Provide --approved-manifest from source-bound human review")
    edited=json.loads(Path(args.approved_manifest).read_text(encoding="utf-8"))
    manifest=reviewed_manifest(edited,session,evidence)
    if manifest["script_sha256"] != edited.get("script_sha256"):
        raise ValueError("Reviewed manifest digest changed. Approve edited version again.")
    spark_voice=os.environ.get("TERRA_VOICE_SPARK","")
    wonder_voice=os.environ.get("TERRA_VOICE_WONDER","")
    sound,timing=render_one(
        manifest,args.out_dir,spark_voice,wonder_voice,
        os.environ.get("ELEVENLABS_API_KEY",""),
        i_reviewed_script=args.i_reviewed_script,
        approve_cost_and_sharing=args.i_approve_cost_and_sharing)
    print("STATUS: SESSION_AUDIO_GENERATED_EDITORIAL")
    print("AUDIO:",sound);print("TIMING:",timing)
    print("REMINDER: Not a verbatim scientific transcript.")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,urllib.error.URLError) as exc:
        print("STOP:",str(exc)[:220],file=sys.stderr);sys.exit(2)
