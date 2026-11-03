"""HACK-016J: evidence-linked decision matrix, NOT an AI approval or invented score.

The entries are original, source-verifiable council investigations.
Priority is explicitly NOT_ASSESSED until data for impact, cost and feasibility exist.
"""
import hashlib
import json
from dynamic_brief import brief_data

def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
      separators=(",",":")).encode("utf-8")).hexdigest()

def decision_matrix(trace):
    report=brief_data(trace)
    known={e["evidence_id"]:e for e in report["sources"]}
    rows=[]
    for idx,step in enumerate(report["steps"]):
        if step["role"] in ("scientific_critic","final_synthesis"):
            continue
        pub=step["checked_publication"]
        refs=[obs["evidence_id"] for obs in pub["observations"]]
        if not refs or any(ref not in known for ref in refs):
            raise ValueError("Unbound scientific source")
        for n,proposal in enumerate(pub["investigations"],1):
            rows.append({
              "option_id":"INV-"+str(idx+1)+"-"+str(n),
              "proposing_agent":step["role"],
              "investigation":proposal["text"],
              "evidence_ids":refs,
              "evidence_validation":[known[e]["validation_status"] for e in refs],
              "hypotheses_unverified":[x["text"] for x in pub["hypotheses"]],
              "scientific_limits":[x["text"] for x in pub["abstentions"]],
              "priority":"NOT_ASSESSED",
              "estimated_cost":"NOT_AVAILABLE",
              "expected_impact":"NOT_ESTABLISHED",
              "feasibility":"NOT_ASSESSED",
              "decision_status":"INVESTIGATION_PROPOSED_NOT_APPROVED"
            })
    if not rows:raise ValueError("No documented proposed investigation")
    critic=report["steps"][-2]["checked_publication"]
    final=report["final"]
    matrix={
      "schema_version":"HACK016J.1",
      "session_id":report["session_id"],
      "question":report["question"],
      "evidence_sha256":report["evidence_sha256"],
      "source_ids":list(known),
      "options":rows,
      "scientific_critic_issues":[x["text"] for x in critic["abstentions"]],
      "scientific_critic_investigations":[x["text"] for x in critic["investigations"]],
      "final_investigations":[x["text"] for x in final["investigations"]],
      "final_abstentions":[x["text"] for x in final["abstentions"]],
      "comparative_ranking":"NOT_POSSIBLE_WITH_CURRENT_EVIDENCE",
      "human_review_required":True,
      "note":"Options transcribe agent investigations; no inferred ranking, financial impact, causality or approval."
    }
    matrix["matrix_sha256"]=_digest(matrix)
    return matrix
