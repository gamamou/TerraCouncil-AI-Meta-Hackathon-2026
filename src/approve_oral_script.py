"""HACK-011 — Reviewable, amendable oral-script manifest with strict source binding.

Save a draft JSON, edit ONLY turns[].text_to_review, then approve via CLI.
Approval binds the exact script, source session fingerprint and original evidence.
Never changes scientific source JSON. Does not send text to any external API.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from natural_french_dialogue import oral_storyboard
from export_decision_pdf import validate_session

BLOCKED = re.compile(r"[<>{}#@\\|*_]|https?://|www\.|[0-9]", re.IGNORECASE)
LIMIT = 2000

def digest(obj):
    payload=json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def reviewed_manifest(edited, session, evidence):
    baseline=oral_storyboard(session,evidence)
    if not isinstance(edited,dict):
        raise ValueError("Review must be a JSON object")
    if edited.get("session_id") != baseline["session_id"]:
        raise ValueError("Review session mismatch")
    if edited.get("evidence_sha256") != baseline["evidence_sha256"]:
        raise ValueError("Scientific evidence fingerprint mismatch")
    if edited.get("type") != "EDITORIAL_RECONSTRUCTION_NOT_VERBATIM":
        raise ValueError("Original editorial label is required")
    turns=edited.get("turns")
    if not isinstance(turns,list) or len(turns)!=4:
        raise ValueError("Exactly four dialogue turns required")
    reviewed=[]
    total=0
    for i,(candidate,original) in enumerate(zip(turns,baseline["turns"])):
        if not isinstance(candidate,dict):
            raise ValueError("Malformed turn")
        for field in ("turn","speaker","source_model","source_evidence_ids","source_stage_index"):
            if candidate.get(field) != original[field]:
                raise ValueError(f"Turn {i+1}: protected source attribution changed: {field}")
        spoken=candidate.get("text_to_review")
        if not isinstance(spoken,str) or not spoken.strip() or len(spoken)>1100:
            raise ValueError(f"Turn {i+1}: empty or excessively long narration")
        if BLOCKED.search(spoken):
            raise ValueError(f"Turn {i+1}: technical characters, numbers or links in TTS narration")
        if not spoken.strip()[-1] in ".!?":
            raise ValueError(f"Turn {i+1}: narration requires final punctuation")
        # Avoid silent utterance switching with changed role or source metadata.
        item={**original,"text_to_review":spoken.strip(),"approved":True}
        reviewed.append(item)
        total+=len(spoken.strip())
    if total>LIMIT:
        raise ValueError(f"Dialogue of {total} characters exceeds safe {LIMIT}-character single-call limit")
    original_data=validate_session(session,evidence)
    source_corpus=" ".join(
        [original_data["question"]] +
        [x["finding"] for x in original_data["evidence"]] +
        [v["text"] for step in original_data["steps"]
         for key in ("hypotheses","investigations","abstentions")
         for v in step["checked_publication"].get(key,[])]
    ).lower()
    # Editorial texts may use varied phrasing; can't machine-verify all semantics.
    # Human approval remains explicitly required. No invented scientific values
    # may enter narration: raw digits are prohibited in text.
    result={**baseline,"turns":reviewed,
            "human_review_complete":True,
            "approval_type":"USER_REVIEWED_EDITORIAL_RECONSTRUCTION",
            "recording_status":"NOT_GENERATED"}
    result["script_sha256"]=digest(reviewed)
    result["source_script_sha256"]=baseline["script_sha256"]
    result["review_note"]="Human editorial approval; NOT scientific field-validation or verbatim transcript."
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--session",required=True)
    parser.add_argument("--evidence",required=True)
    parser.add_argument("--draft",required=True)
    parser.add_argument("--out",required=True)
    parser.add_argument("--i-reviewed-meaning",action="store_true",
                        help="Confirm manual check of each turn against original scientific steps")
    args=parser.parse_args()
    if not args.i_reviewed_meaning:
        raise ValueError("Manual semantic source review confirmation required")
    out=Path(args.out)
    if out.exists():
        raise ValueError("Do not overwrite an existing approval")
    session=json.loads(Path(args.session).read_text(encoding="utf-8"))
    evidence=json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    draft=json.loads(Path(args.draft).read_text(encoding="utf-8"))
    approved=reviewed_manifest(draft,session,evidence)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(approved,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STATUS: EDITORIAL_REVIEW_APPROVED_NOT_SCIENTIFICALLY_VALIDATED")
    print("SESSION:",approved["session_id"])
    print("SCRIPT_SHA256:",approved["script_sha256"])
    print("MODEL_CALLS: 0")
    print("OUTPUT:",out)
if __name__=="__main__":
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as e:
        print("STOP:",str(e),file=sys.stderr)
        sys.exit(2)
