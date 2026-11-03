"""HACK-016: question-specific Spark/Wonder council with independent FSDC gates."""
from council import SPARK, WONDER, meta_call
from verification import verify_submission

SCHEMA = ("Return strict JSON with observations as exact source evidence_id/finding pairs, "
          "hypotheses, investigations, abstentions as string arrays. "
          "Never invent measures. Address the current question and missing data.")

def run_dynamic(plan, api_key, caller=meta_call):
    if not plan["status"].startswith("READY_") or not plan["evidence"]:
        raise ValueError("No question-relevant FSDC evidence; abstain")
    if not api_key:
        raise ValueError("Missing API key")
    base={"question":plan["question"],"geography":plan["geography"],
          "sector":plan["sector"],"topics":plan["topics"],
          "missing_topics":plan["missing_topics"],"evidence":plan["evidence"],
          "evidence_sha256":plan["evidence_sha256"]}
    result={"status":"RUNNING","question":plan["question"],
            "evidence_sha256":plan["evidence_sha256"],
            "missing_topics":plan["missing_topics"],
            "agents":plan["proposers"],"steps":[]}
    perspectives=[]
    def one(role,model,payload):
        raw=caller(model,SCHEMA+" Role: "+role,payload,api_key)
        check=verify_submission(raw,plan["evidence"],plan["evidence_sha256"])
        result["steps"].append({"role":role,"model":model,
                                "status":check["status"],
                                "checked_publication":check.get("publication")})
        if not check["verified"]:
            raise ValueError("Source verification failed: "+role)
        return check["publication"]
    try:
        for role in plan["proposers"]:
            view=one(role,SPARK,base)
            perspectives.append({"role":role,"publication":view})
        criticism=one("scientific_critic",WONDER,
                      dict(base,verified_positions=perspectives))
        summary=one("final_synthesis",SPARK,
                    dict(base,verified_positions=perspectives,
                         verified_critique=criticism))
        result["decision_support"]=summary
        result["status"]="STRUCTURAL_CHECKS_PASSED_HUMAN_REVIEW_REQUIRED"
    except (ValueError,RuntimeError,TypeError) as error:
        result["status"]="STOPPED_DO_NOT_RETRY_BLINDLY"
        result["error_type"]=type(error).__name__
    result["calls_attempted"]=len(result["steps"])
    return result
