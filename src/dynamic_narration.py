"""Dynamic narration directly from recorded HACK-016 scientific interventions."""
import hashlib
import json
from verification import evidence_hash,verify_submission

def build_dynamic_oral(trace):
    if trace.get("status")!="COMPLETED_STRUCTURALLY_CHECKED_HUMAN_REVIEW_REQUIRED":
        raise ValueError("A completed session is required")
    sources=trace.get("evidence_snapshot")
    if not isinstance(sources,list) or not sources:
        raise ValueError("Missing scientific evidence snapshot")
    if evidence_hash(sources)!=trace["evidence_sha256"]:
        raise ValueError("Evidence mismatch")
    steps=trace["steps"]
    if len(steps)<3 or steps[-2]["role"]!="scientific_critic" or steps[-1]["role"]!="final_synthesis":
        raise ValueError("Missing debate critic or synthesis")
    if trace.get("decision_support")!=steps[-1].get("checked_publication"):
        raise ValueError("Decision summary mismatch")
    turns=[]
    problems=[]
    for index,step in enumerate(steps):
        pub=step["checked_publication"]
        original={
           "observations":[{"evidence_id":x["evidence_id"],"finding":x["finding"]} for x in pub["observations"]],
           "hypotheses":[x["text"] for x in pub["hypotheses"]],
           "investigations":[x["text"] for x in pub["investigations"]],
           "abstentions":[x["text"] for x in pub["abstentions"]]
        }
        checked=verify_submission(original,sources,trace["evidence_sha256"])
        if step.get("status")!="ACCEPTED_STRUCTURAL_ONLY" or not checked["verified"]:
            raise ValueError("Original stage has not passed verification")
        investigation=original["investigations"][0] if original["investigations"] else ""
        caution=original["abstentions"][0] if original["abstentions"] else ""
        if not investigation and not caution:raise ValueError("No spoken content")
        spoken=("Je propose une investigation : "+investigation+" " if investigation else "")+(
                 "Je souligne une limite : "+caution if caution else "")
        spoken=spoken.strip()
        if any(char.isdigit() for char in spoken):
            problems.append({"turn":index+1,"reason":"DIGITS_REQUIRE_ORAL_NORMALIZATION"})
        if any(word in (" "+(investigation+" "+caution).lower()+" ") for word in
               (" the "," should "," with "," evidence "," missing "," investigate "," cannot ")) :
            problems.append({"turn":index+1,"reason":"SOURCE_MAY_BE_ENGLISH"})
        turns.append({
            "turn":index+1,"speaker":step["role"],"source_model":step["model"],
            "text_to_review":spoken,"source_stage_index":index,
            "source_investigation":investigation,"source_abstention":caution,
            "source_evidence_ids":[x["evidence_id"] for x in pub["observations"]]
        })
    total=sum(len(x["text_to_review"]) for x in turns)
    if total>2000:problems.append({"reason":"LONG_SCRIPT_REQUIRES_SEGMENTATION"})
    fingerprint=hashlib.sha256(json.dumps(turns,sort_keys=True,ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"schema_version":"HACK016C.1","session_id":trace["run_id"],
       "question":trace["question"],"evidence_sha256":trace["evidence_sha256"],
       "script_sha256":fingerprint,"type":"EDITORIAL_RECONSTRUCTION_NOT_VERBATIM",
       "derivation":"EXTRACTIVE_FROM_ACTUAL_MODEL_STEPS",
       "scientific_validation":"STRUCTURAL_ONLY_NOT_FIELD_VALIDATED",
       "review_required":True,"automatic_tts_allowed":False,
       "review_issues":problems,"turns":turns}
