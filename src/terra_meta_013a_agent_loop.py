"""TERRA-META-013A — minimal agentic council contract, offline testable.
The model decides actions; the runtime validates allowable tools and evidence.
No fabricated scientific data or API calls in this module.
"""
from dataclasses import dataclass,field
from typing import Callable
ALLOWED={"query_evidence","record_finding","challenge_finding","submit_decision"}
@dataclass
class CouncilState:
 question:str
 evidence:dict
 findings:list=field(default_factory=list)
 events:list=field(default_factory=list)
 decision:dict|None=None
def execute(state:CouncilState, action:dict):
 name=action.get("tool")
 if name not in ALLOWED: return {"ok":False,"reason":"UNKNOWN_TOOL"}
 if name=="query_evidence":
  source=state.evidence.get(action.get("id"))
  if not source:return {"ok":False,"reason":"UNKNOWN_EVIDENCE"}
  result={"ok":True,"source":source}
 elif name=="record_finding":
  ids=action.get("evidence_ids")
  if not isinstance(ids,list) or not ids or any(i not in state.evidence for i in ids):
   return {"ok":False,"reason":"UNSUPPORTED_FINDING"}
  summary=action.get("summary")
  if not isinstance(summary,str) or not summary.strip():return {"ok":False,"reason":"EMPTY_FINDING"}
  entry={"id":"F"+str(len(state.findings)+1),"summary":summary,"evidence_ids":ids,"challenged":False}
  state.findings.append(entry);result={"ok":True,"finding_id":entry["id"]}
 elif name=="challenge_finding":
  f=next((f for f in state.findings if f["id"]==action.get("finding_id")),None)
  if not f:return {"ok":False,"reason":"UNKNOWN_FINDING"}
  f["challenged"]=True;result={"ok":True,"finding_id":f["id"]}
 else:
  ids=action.get("finding_ids")
  if not isinstance(ids,list) or not ids or any(not any(f["id"]==i for f in state.findings) for i in ids):
   return {"ok":False,"reason":"UNSUPPORTED_DECISION"}
  state.decision={"summary":action.get("summary",""),"finding_ids":ids,
    "status":"PROVISIONAL_REQUIRES_HUMAN_REVIEW"}
  result={"ok":True,"status":state.decision["status"]}
 state.events.append({"action":name,"arguments":action,"result":result})
 return result
def agent_loop(question,evidence,model_next:Callable,limit=12):
 if not question.strip():raise ValueError("Question required")
 state=CouncilState(question,evidence)
 for _ in range(limit):
  action=model_next({"question":question,"evidence_ids":list(evidence),
                     "findings":state.findings,"events":state.events})
  result=execute(state,action)
  if state.decision is not None:break
 return state
