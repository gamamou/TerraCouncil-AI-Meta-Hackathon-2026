"""FSDC-EXP-001: source-scope-aware comparative discovery, no invented AOI overlap.

This is a DOCUMENTARY contextual lane, not an admissible spatial observation,
and does not mutate or masquerade as a completed Meta debate.
"""
import hashlib
import json
from pathlib import Path
from dynamic_council import classify,plan_question

REGISTRY=Path(__file__).resolve().parents[1]/"data"/"fsdc_contextual_candidates_boke_2026.json"
VALID={"SOURCE_REPORTED_NOT_INDEPENDENTLY_AUDITED",
       "SECONDARY_UNCONFIRMED_NOT_ADMISSIBLE",
       "PEER_REVIEWED_ABSTRACT_NOT_AOI_GEOREFERENCED"}

def load_context_registry(path=REGISTRY):
    payload=json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version")!="FSDC_CONTEXT_001":
        raise ValueError("Unexpected context registry version")
    records=payload.get("records")
    if not isinstance(records,list) or not records:
        raise ValueError("No real documented context records")
    ids=set()
    for record in records:
        if record["evidence_id"] in ids:raise ValueError("Duplicate context evidence")
        ids.add(record["evidence_id"])
        if record["validation_status"] not in VALID:
            raise ValueError("Unsupported documentary validation label")
        if record["coverage_relation"]!="REGIONAL_CONTEXT_NOT_AOI_OVERLAP_ESTABLISHED":
            raise ValueError("Unproven spatial overlap")
        if not record["source_url"].startswith("https://"):
            raise ValueError("Documentation requires actual link")
    return records

def compare_question(question,local_records,sector="mining",geography="Boké, Guinea",
                     context_records=None):
    baseline=plan_question(question,local_records,geography,sector)
    category=classify(question,sector)
    # Explicit region and question relevance; no claim of AOI source overlap.
    if "bok" not in question.casefold():
        eligible=[]
    else:
        candidates=load_context_registry() if context_records is None else context_records
        eligible=[x for x in candidates
          if set(category["topics"]).intersection(x["topics"])]
    accepted=[x for x in eligible
       if x["validation_status"] in ("SOURCE_REPORTED_NOT_INDEPENDENTLY_AUDITED",
                               "PEER_REVIEWED_ABSTRACT_NOT_AOI_GEOREFERENCED")]
    secondary=[x for x in eligible
       if x["validation_status"]=="SECONDARY_UNCONFIRMED_NOT_ADMISSIBLE"]
    result={"schema_version":"FSDC_EXP_001",
       "question":question,"geography":geography,
       "baseline":{"status":baseline["status"],
           "observation_ids":[x["evidence_id"] for x in baseline["evidence"]],
           "missing_topics":baseline.get("missing_topics",[]),
           "evidence_sha256":baseline.get("evidence_sha256")},
       "additional_regional_context":[
           {key:x[key] for key in ("evidence_id","title","claim","value","unit",
                "period","source_type","source_url","scope","coverage_relation",
                "validation_status","limitations")} for x in accepted],
       "unverified_candidates":[
           {"evidence_id":x["evidence_id"],"title":x["title"],
            "status":x["validation_status"],"source_url":x["source_url"]}
           for x in secondary],
       "contextual_sources_added":len(accepted),
       "peer_reviewed_regional_studies_found":sum(x["validation_status"]=="PEER_REVIEWED_ABSTRACT_NOT_AOI_GEOREFERENCED" for x in accepted),
       "aoi_scientific_observations_added":0,
       "debate_rerun_performed":False,
       "model_calls":0,
       "scientific_conclusion_changed":"NOT_EVALUATED_NO_NEW_DEBATE",
       "message":"The regional documentary/scientific evidence does not establish measurements, current outcomes or geospatial overlap on the pilot AOI."}
    result["comparison_sha256"]=hashlib.sha256(json.dumps(result,
      sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()
    return result

def attach_regional_context(plan):
    """Attach published sources only, update fingerprint; keep spatial evidence separate."""
    from dynamic_council import plan_fingerprint
    question=plan.get("question","")
    decision=classify(question,plan.get("sector"))
    context=[]
    if "bok" in question.casefold():
        for record in load_context_registry():
            if record["validation_status"]=="SECONDARY_UNCONFIRMED_NOT_ADMISSIBLE":
                continue
            if not set(decision["topics"]).intersection(record["topics"]):
                continue
            context.append({"evidence_id":record["evidence_id"],
                "claim":record["claim"],"source_url":record["source_url"],
                "source_type":record["source_type"],"period":record["period"],
                "scope":record["scope"],
                "coverage_relation":record["coverage_relation"],
                "validation_status":record["validation_status"],
                "limitations":record["limitations"]})
    plan=dict(plan)
    plan["regional_context"]=context
    plan["regional_context_sha256"]=hashlib.sha256(json.dumps(context,
        sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()
    plan["plan_sha256"]=plan_fingerprint(plan)
    return plan
