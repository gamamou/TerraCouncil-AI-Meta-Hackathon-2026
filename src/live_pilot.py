"""HACK-005 single-call live Meta pilot with a fail-closed independent gate.

DRY RUN by default. Real call requires 2 opt-ins + MODEL_API_KEY.
No retry: a billed request may have completed even if its response was lost.
Store only in a private local file OUTSIDE the public GitHub repository.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys

from council import SPARK, meta_call
from verified_council import PROMPT, prepare
from verification import verify_submission

def pilot(question, records, *, geography="Boké, Guinea",
          execute=False, share_approved=False, api_key="", caller=meta_call):
    job = prepare(question, records, sector="mining", geography=geography)
    record = {
        "hackathon_stage": "HACK-005",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "question": job["question"],
        "geography": job["geography"],
        "evidence_status": job["status"],
        "source_evidence_ids": [r["evidence_id"] for r in job["gate"]["evidence"]],
        "evidence_sha256": job["gate"]["evidence_sha256"],
        "model": SPARK,
        "calls_attempted": 0,
        "human_review_required": True,
        "status": "PREPARED_NO_MODEL_CALLS",
        "privacy_warning": "Review licensing and source-derived findings before sending to Meta."
    }
    if not job["gate"]["evidence"]:
        record["status"] = "ABSTAIN_NO_USABLE_EVIDENCE"
        return record
    if not execute:
        record["status"] = "READY_EXPLORATORY_NO_MODEL_CALL"
        return record
    if not share_approved:
        raise ValueError("Missing explicit --i-reviewed-sharing confirmation")
    if not api_key:
        raise ValueError("MODEL_API_KEY is not set in the local environment")
    first = job["proposers"][0]
    payload = {
        "question": question, "sector": "mining", "geography": geography,
        "agent_id": first, "evidence": job["gate"]["evidence"],
        "evidence_sha256": job["gate"]["evidence_sha256"],
        "limits": "Exploratory only; NOT_FIELD_VALIDATED; no causal or affected-population inference"
    }
    record["calls_attempted"] = 1
    record["agent_id"] = first
    try:
        raw = caller(SPARK, PROMPT + "\nRole: " + first, payload, api_key)
    except Exception as exc:
        record["status"] = "CALL_FAILED_DO_NOT_RETRY_BLINDLY"
        record["error_type"] = type(exc).__name__
        record["error_message"] = str(exc)[:250]
        return record
    record["raw_model_text"] = raw
    checked = verify_submission(raw, job["gate"]["evidence"], job["gate"]["evidence_sha256"])
    record["verification_status"] = checked["status"]
    record["verification_issues"] = checked["issues"]
    record["status"] = ("FIRST_META_RESPONSE_PASSED_STRUCTURAL_GATES"
                        if checked["verified"] else "FIRST_META_RESPONSE_BLOCKED")
    record["checked_publication"] = checked.get("publication")
    record["limitations"] = [
        "Structural verification is not scientific validation.",
        "Model-authored investigations and hypotheses are not factual findings.",
        "No approval or stakeholder endorsement is implied."
    ]
    return record

def main():
    a = argparse.ArgumentParser(description="HACK-005 one-call Meta pilot, no Muse Code")
    a.add_argument("--question", required=True)
    a.add_argument("--evidence", required=True, help="Local/private screened evidence JSON")
    a.add_argument("--out", required=True, help="Private output trace JSON; never commit")
    a.add_argument("--send-to-meta", action="store_true", help="Enable exactly one paid Meta request")
    a.add_argument("--i-reviewed-sharing", action="store_true",
                   help="Confirm you reviewed all evidence text, licenses and permissions for Meta")
    args = a.parse_args()
    source = Path(args.evidence).resolve()
    target = Path(args.out).resolve()
    if source == target:
        raise ValueError("Do not overwrite input evidence")
    if target.exists():
        raise ValueError("Output exists; use a unique path to prevent duplicate runs")
    records = json.loads(source.read_text(encoding="utf-8"))
    outcome = pilot(args.question, records, execute=args.send_to_meta,
                    share_approved=args.i_reviewed_sharing,
                    api_key=os.environ.get("MODEL_API_KEY", ""))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("RESULT_FILE:", target)
    print("STATUS:", outcome["status"])
    print("CALLS_ATTEMPTED:", outcome["calls_attempted"])
    print("MODEL:", outcome["model"])
    if outcome.get("verification_issues"):
        print("VERIFICATION_ISSUES:", outcome["verification_issues"])
    if outcome.get("error_message"):
        print("ERROR:", outcome["error_message"])

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("STOP:", str(exc), file=sys.stderr)
        sys.exit(2)
