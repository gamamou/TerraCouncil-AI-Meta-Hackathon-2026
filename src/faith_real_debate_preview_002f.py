"""TERRA-DATA-002F: preview a real HACK016 evidence plan without paid calls."""
import argparse
import json
from pathlib import Path
from dynamic_council import plan_question
from faith_boke_context_guard_002e import inspect_context

QUESTIONS = {
 "land": "Quelle occupation du sol est documentee et quelles analyses manquent pour les mines de Boke ?",
 "multidomain": "Comment concilier extraction miniere, poussiere, foret, eau et communautes a Boke ?",
 "climate": "Quelles preuves de climat et pluie sont disponibles pour Boke ?",
}

def preview(records, scenario="multidomain"):
    if scenario not in QUESTIONS:
        raise ValueError("Unknown scenario")
    if not isinstance(records,list):
        raise ValueError("Evidence must be list")
    plan=plan_question(QUESTIONS[scenario],records,geography="Boké, Guinea")
    context=inspect_context()
    if context["inside_exploratory_rectangle"] or context["council_evidence"]:
        raise ValueError("Unapproved climate context admission")
    return {
      "schema_version":"TERRA_DATA_002F",
      "scenario":scenario,
      "question":QUESTIONS[scenario],
      "plan":plan,
      "evidence_count":len(plan.get("evidence",[])),
      "climate_context":{"source":"existing FAITH NASA POWER point",
        "point":context["prefectural_reference_point"],
        "outside_pilot":True,"not_citable_for_pilot":True},
      "unadmitted":["FSMI_HANSEN_640","FSMI_CHENG_CLASSES","FSMI_CAMS_REGIONAL","FSMI_WORLDPOP_OSM"],
      "model_calls_executed":0,"external_requests_executed":0
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",required=True)
    p.add_argument("--scenario",choices=sorted(QUESTIONS),default="multidomain")
    args=p.parse_args()
    source=Path(args.evidence)
    if not source.is_file() or source.stat().st_size>4000000:
        raise ValueError("Invalid local evidence file")
    records=json.loads(source.read_text(encoding="utf-8-sig"))
    result=preview(records,args.scenario)
    print(json.dumps({"scenario":result["scenario"],
      "plan_status":result["plan"]["status"],
      "evidence_count":result["evidence_count"],
      "missing_topics":result["plan"].get("missing_topics",[]),
      "climate_context":"POINT_OUTSIDE_PILOT_NOT_ADMITTED",
      "model_calls_executed":0},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
