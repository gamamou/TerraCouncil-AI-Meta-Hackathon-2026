import argparse
import json
import os
from pathlib import Path
from dynamic_council import plan_question
from dynamic_debate import run_dynamic

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--question",required=True)
    p.add_argument("--evidence",required=True)
    p.add_argument("--geography",default="Boké, Guinea")
    p.add_argument("--sector")
    p.add_argument("--execute",action="store_true")
    p.add_argument("--out")
    p.add_argument("--approve-cost-and-sharing",action="store_true")
    a=p.parse_args()
    records=json.loads(Path(a.evidence).read_text(encoding="utf-8"))
    plan=plan_question(a.question,records,a.geography,a.sector)
    if not a.execute:
        print(json.dumps({"mode":"PREVIEW_NO_MODEL_CALLS","plan":plan},
              indent=2,ensure_ascii=False))
        return
    if not a.approve_cost_and_sharing:
        raise ValueError("Paid Meta execution requires explicit approval")
    if not plan["status"].startswith("READY_"):
        print(json.dumps({"status":plan["status"],"calls_attempted":0}))
        return
    if not a.out: raise ValueError("--out required for paid run")
    key=os.environ.get("MODEL_API_KEY","")
    if not key: raise ValueError("MODEL_API_KEY missing")
    target=Path(a.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as f:
        json.dump({"status":"ATTEMPT_STARTED","question":a.question},f)
    try: result=run_dynamic(plan,key)
    except Exception as error:
        result={"status":"FAILED_DO_NOT_RETRY","error_type":type(error).__name__}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("RESULT:",target)
    print("STATUS:",result["status"])
if __name__=="__main__":
    main()
