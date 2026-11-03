"""TERRA-META-013B — Muse-selected actions with independent evidence gate."""
import json
from council import meta_call, SPARK
from terra_meta_013a_agent_loop import CouncilState,execute

RULES = """You are TerraCouncil's scientific action planner. Choose one next action.
Return ONLY a JSON object using these exact shapes:
{"tool":"query_evidence","id":"E1"}
{"tool":"record_finding","summary":"exact source finding","evidence_ids":["E1"]}
{"tool":"challenge_finding","finding_id":"F1"}
{"tool":"submit_decision","summary":"provisional conclusion","finding_ids":["F1"]}
Use only supplied IDs. Never invent evidence or measurements. Don't repeat actions.
Do not submit a decision before recording evidence. Cite uncertainties."""
def run(question,records,key,caller=meta_call,max_steps=8):
 evidence={r["evidence_id"]:r for r in records}
 state=CouncilState(question,evidence)
 trace=[]
 if not evidence:return {"status":"ABSTAIN_NO_EVIDENCE","steps":[],"decision":None}
 for i in range(max_steps):
  view={"question":question,"evidence":evidence,"findings":state.findings,"steps":trace[-4:]}
  raw=caller(SPARK,RULES,view,key)
  action=json.loads(raw) if isinstance(raw,str) else raw
  if not isinstance(action,dict):raise ValueError("Invalid Muse action")
  if action.get("tool")=="record_finding":
   ids=action.get("evidence_ids",[])
   if not isinstance(ids,list) or len(ids)!=1 or action.get("summary")!=evidence.get(ids[0],{}).get("finding"):
    result={"ok":False,"reason":"FINDING_NOT_EXACT_SOURCE"}
   else:result=execute(state,action)
  else:result=execute(state,action)
  trace.append({"step":i+1,"model":SPARK,"action":action,"verification":result})
  if state.decision:break
  if action.get("tool")=="submit_decision" and not result.get("ok"):
   break
 return {"status":"PROVISIONAL_HUMAN_REVIEW" if state.decision else "INCOMPLETE",
         "steps":trace,"decision":state.decision}
