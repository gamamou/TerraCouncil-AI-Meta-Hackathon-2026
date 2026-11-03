"""013C: adaptive Spark/Wonder scientific consultation, preserving 013B runtime.
No fixed debate length or mandatory consultation. All model outputs are provisional.
"""
import json
from council import meta_call,SPARK,WONDER
from terra_meta_013a_agent_loop import CouncilState,execute

CHAIR="""You are the TerraCouncil scientific chair. Choose the NEXT action as one JSON object:
{"tool":"record_finding","summary":"EXACT source finding","evidence_ids":["KNOWN_ID"]}
{"tool":"consult_scientific_agent","domain":"environment","question":"specific question","reason":"why this distinct expertise matters","evidence_ids":["KNOWN_ID"]}
{"tool":"submit_decision","summary":"provisional synthesis","finding_ids":["F1"],"consultation_rationale":"why further expertise is or is not needed"}
{"tool":"query_evidence","id":"KNOWN_ID"}
Use only supplied evidence. Choose expert consultation only if it adds a distinct scientific
perspective necessary for the user question; never consult to create artificial debate.
Never claim population exposure, causation, temporal change or official approval from a
single exploratory raster. Preserve uncertainty. Finish when answer is sufficient. Before finishing, assess if the user question needs
a distinct domain perspective. If not, state the reason in consultation_rationale.
Do not claim a consultation occurred unless it is in the tool history."""
EXPERT="""You are one scientific specialist in an adaptive council.
Return STRICT JSON with keys "observations", "interpretation", "limits", "recommendations".
observations is a list of objects {"evidence_id":"KNOWN_ID","finding":"EXACT SOURCE FINDING"}.
interpretation, limits, recommendations must be lists of short strings.
Do not introduce numerical facts outside exact quoted observations. Recommendations
are proposals, not scientifically validated conclusions."""
DOMAINS={"mining","environment","agriculture","communities","energy","esg","climate"}
def decode(raw):
 obj=json.loads(raw) if isinstance(raw,str) else raw
 if not isinstance(obj,dict):raise ValueError("Expected JSON object")
 return obj
def check_expert(reply,evidence,ids):
 if set(reply)!={"observations","interpretation","limits","recommendations"}:return False
 if any(not isinstance(reply[k],list) for k in reply):return False
 if not reply["observations"]:return False
 for o in reply["observations"]:
  if not isinstance(o,dict) or set(o)!={"evidence_id","finding"}:return False
  if o["evidence_id"] not in ids or o["finding"]!=evidence[o["evidence_id"]].get("finding"):return False
 for k in ("interpretation","limits","recommendations"):
  if any(not isinstance(v,str) or not v.strip() for v in reply[k]):return False
 return True
def run(question,records,key,caller=meta_call,max_steps=8,max_consults=2):
 evidence={r["evidence_id"]:r for r in records}
 state=CouncilState(question,evidence)
 trace=[]; consultations=[]; attempted=0
 if not evidence:return {"status":"ABSTAIN_NO_EVIDENCE","steps":[],"decision":None,"consultations":[]}
 for n in range(max_steps):
  payload={"question":question,"evidence":evidence,"findings":state.findings,
           "consultations":consultations,"recent_steps":trace[-5:]}
  action=decode(caller(SPARK,CHAIR,payload,key))
  name=action.get("tool")
  if name=="consult_scientific_agent":
   ids=action.get("evidence_ids")
   domain=action.get("domain")
   if domain not in DOMAINS or not isinstance(ids,list) or not ids or any(e not in evidence for e in ids) or attempted>=max_consults:
    result={"ok":False,"reason":"INVALID_CONSULTATION_OR_LIMIT"}
   else:
    attempted+=1
    subject=action.get("question","")
    if not isinstance(subject,str) or not subject.strip():
     result={"ok":False,"reason":"EMPTY_EXPERT_QUESTION"}
    else:
     expert_payload={"domain":domain,"question":subject,"evidence":[evidence[e] for e in ids],
                     "chair_reason":action.get("reason","not supplied")}
     response=decode(caller(WONDER,EXPERT,expert_payload,key))
     if check_expert(response,evidence,ids):
      entry={"domain":domain,"question":subject,"reason":action.get("reason","not supplied"),
             "evidence_ids":ids,"response":response,
             "status":"STRUCTURALLY_CHECKED_NOT_SCIENTIFICALLY_VALIDATED"}
      consultations.append(entry)
      result={"ok":True,"consultation":len(consultations)}
     else:result={"ok":False,"reason":"EXPERT_EVIDENCE_CHECK_FAILED"}
  elif name=="record_finding":
   ids=action.get("evidence_ids")
   if not isinstance(ids,list) or len(ids)!=1 or action.get("summary")!=evidence.get(ids[0],{}).get("finding"):
    result={"ok":False,"reason":"FINDING_NOT_EXACT_SOURCE"}
   else:result=execute(state,action)
  elif name=="submit_decision":
   # Independent gate: only existing findings; free-form synthesis is PROVISIONAL.
   result=execute(state,action)
  else:result=execute(state,action)
  trace.append({"step":n+1,"model":SPARK,"action":action,"verification":result})
  if state.decision or (name=="submit_decision" and not result.get("ok")):break
 rationale=next((x["action"].get("consultation_rationale") for x in reversed(trace)
                 if x["action"].get("tool")=="submit_decision"),None)
 return {"schema":"TERRA_META_013C_V1",
         "status":"PROVISIONAL_HUMAN_REVIEW" if state.decision else "INCOMPLETE",
         "steps":trace,"consultations":consultations,"decision":state.decision,
         "consultation_rationale":rationale,
         "consultation_explained":bool(consultations) or bool(rationale),
         "scientific_validation":"STRUCTURAL_ONLY"}
