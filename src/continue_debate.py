"""HACK-006: sequential Muse Wonder critique and Spark revision of a real Spark pilot.

Use --stage critique or --stage revision in separate explicit executions.
Default: zero Meta calls; no automatic retries or silently promoted findings.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
from council import SPARK, WONDER, meta_call
from verified_council import prepare, PROMPT
from verification import verify_submission

def stage_run(stage, evidence, spark_trace, critique_trace=None,
              *, execute=False, sharing_approved=False, api_key="", caller=meta_call):
    if stage not in ("critique", "revision"):
        raise ValueError("Unknown stage")
    if spark_trace.get("status") != "FIRST_META_RESPONSE_PASSED_STRUCTURAL_GATES":
        raise ValueError("Spark trace did not pass structural verification")
    question = spark_trace.get("question", "")
    if not question:
        raise ValueError("Spark trace missing question")
    job = prepare(question, evidence)
    if not job["gate"]["evidence"] or spark_trace.get("evidence_sha256") != job["gate"]["evidence_sha256"]:
        raise ValueError("Source evidence mismatch or no admissible exploratory data")
    spark = spark_trace.get("checked_publication")
    if not isinstance(spark, dict):
        raise ValueError("Missing checked Spark publication")
    # Reverify the serialized publication as a guard against trace modification.
    def reconstruct(pub):
        return {"observations":[{"evidence_id":o["evidence_id"],"finding":o["finding"]}
                for o in pub.get("observations",[])],
                "hypotheses":[x["text"] for x in pub.get("hypotheses",[])],
                "investigations":[x["text"] for x in pub.get("investigations",[])],
                "abstentions":[x["text"] for x in pub.get("abstentions",[])]}
    if not verify_submission(reconstruct(spark), job["gate"]["evidence"],
                             job["gate"]["evidence_sha256"])["verified"]:
        raise ValueError("Spark publication does not reverify")
    model, role = (WONDER, "independent_scientific_critic") if stage=="critique" else (SPARK, "revised_decision_synthesis")
    prior_critique = None
    if stage=="revision":
        if not critique_trace or critique_trace.get("stage")!="critique" or critique_trace.get("status")!="PASSED_STRUCTURAL_GATES":
            raise ValueError("A structurally verified Wonder critique is required")
        if critique_trace.get("evidence_sha256") != job["gate"]["evidence_sha256"]:
            raise ValueError("Critique evidence mismatch")
        prior_critique=critique_trace.get("checked_publication")
        if not isinstance(prior_critique,dict) or not verify_submission(
                reconstruct(prior_critique),job["gate"]["evidence"],job["gate"]["evidence_sha256"])["verified"]:
            raise ValueError("Wonder critique failed repeat verification")
    payload={"question":question,"geography":job["geography"],"sector":job["sector"],
             "evidence":job["gate"]["evidence"],"evidence_sha256":job["gate"]["evidence_sha256"],
             "spark_checked_position":spark, "wonder_checked_critique":prior_critique,
             "constraints":"Exploratory scientific observations only; no causal inference or approval."}
    instruction = (PROMPT+"\n"+(
        "Role: independent critical reviewer. Challenge Spark assumptions and missing evidence. "
        "Observations must be exact copied findings; critique belongs in hypotheses, investigations "
        "and abstentions. Highlight uncertainty and factual gaps."
        if stage=="critique" else
        "Role: final revised decision support. Account for all critical objections. "
        "Preserve dissent and unknowns. Propose investigations, not approval."
    ))
    record={"stage":stage,"question":question,"model":model,
            "timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "evidence_sha256":job["gate"]["evidence_sha256"],
            "status":"READY_NO_MODEL_CALL","calls_attempted":0,
            "human_review_required":True}
    if not execute: return record
    if not sharing_approved or not api_key:
        raise ValueError("Explicit sharing review and MODEL_API_KEY required")
    record["calls_attempted"]=1
    try:
        raw=caller(model,instruction,payload,api_key)
    except Exception as exc:
        record["status"]="CALL_FAILED_DO_NOT_RETRY_BLINDLY"
        record["error_type"]=type(exc).__name__
        record["error_message"]=str(exc)[:200]
        return record
    record["raw_model_text"]=raw
    verdict=verify_submission(raw,job["gate"]["evidence"],job["gate"]["evidence_sha256"])
    record["status"]="PASSED_STRUCTURAL_GATES" if verdict["verified"] else "BLOCKED_BY_INDEPENDENT_VERIFIER"
    record["verification_status"]=verdict["status"]
    record["verification_issues"]=verdict["issues"]
    record["checked_publication"]=verdict.get("publication")
    record["warning"]="Structural checks only; no scientific or field-validation endorsement."
    return record

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage", choices=["critique","revision"], required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--spark-trace", required=True)
    p.add_argument("--critique-trace")
    p.add_argument("--out", required=True)
    p.add_argument("--send-to-meta", action="store_true")
    p.add_argument("--i-reviewed-sharing", action="store_true")
    a=p.parse_args()
    dest=Path(a.out)
    if dest.exists(): raise ValueError("Output exists; choose a new filename")
    evidence=json.loads(Path(a.evidence).read_text(encoding="utf-8"))
    spark=json.loads(Path(a.spark_trace).read_text(encoding="utf-8"))
    critique=json.loads(Path(a.critique_trace).read_text(encoding="utf-8")) if a.critique_trace else None
    result=stage_run(a.stage,evidence,spark,critique,execute=a.send_to_meta,
                     sharing_approved=a.i_reviewed_sharing,api_key=os.environ.get("MODEL_API_KEY",""))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STATUS:",result["status"])
    print("MODEL:",result["model"])
    print("CALLS_ATTEMPTED:",result["calls_attempted"])
    print("TRACE:",dest)
    if result.get("verification_issues"): print("ISSUES:",result["verification_issues"])
    if result.get("error_message"): print("ERROR:",result["error_message"])

if __name__=="__main__":
    try: main()
    except (ValueError,OSError,KeyError,TypeError) as e:
        print("STOP:",str(e),file=sys.stderr);sys.exit(2)
