"""TERRA-DATA-002G: expand established Terra 010HI/J evidence into source-linked indicators.

Six distinct, fully traceable *indicator statements* derive from TWO existing
source families (WorldPop and ESA WorldCover). Do not call them six datasets,
independent studies, new acquisitions or field-validated site measurements.
"""
import argparse
import json
from pathlib import Path

from import_boke_010hi import build
from dynamic_council import plan_question

CLASSES = ("10","40","50","80","95")
LABELS = {
 "10":"TREE_COVER", "40":"CROPLAND", "50":"BUILT_UP",
 "80":"PERMANENT_WATER", "95":"MANGROVES",
}

def expand(hi_path,qa_path):
    original = build(hi_path,qa_path)  # reuses original strict schema, AOI and hash checks
    if len(original)!=2:
        raise ValueError("Unexpected original Terra 010HI/J findings")
    population, cover = original
    if population["evidence_id"]!="BOKE-010HI-POP-2026" or cover["evidence_id"]!="BOKE-010HI-LC-2021":
        raise ValueError("Unexpected original source identity")
    hi=json.loads(Path(hi_path).read_text(encoding="utf-8-sig"))
    classes=hi["source_evidence"]["landcover"]["measurement"]["classes"]
    result=[population]
    for code in CLASSES:
        entry=classes[code]
        share=entry["area_weighted_share_pct"]
        if isinstance(share,bool) or not isinstance(share,(int,float)) or not 0<=share<=100:
            raise ValueError("Invalid area weighted class share")
        if not isinstance(entry["name"],str) or not entry["name"].strip():
            raise ValueError("Missing original class label")
        finding=(f"ESA WorldCover 2021 land cover class {code} ({entry['name']}) "
             f"area-weighted share in rectangular AOI [-14.5, 10.5, -14.0, 11.0]: "
             f"{share}%; classification snapshot, not a 2026 land-cover trend, "
             "site biodiversity survey or mine-caused disturbance.")
        record=dict(cover)
        record["evidence_id"]="BOKE-010HI-LC-2021-"+LABELS[code]
        record["finding"]=finding
        record["method"]=cover["method"]+" Individual class indicator derived from original grouped finding."
        result.append(record)
    if len({r["evidence_id"] for r in result})!=len(result):
        raise ValueError("Duplicate indicator id")
    return result

def summary(records):
    plan=plan_question("Comment concilier extraction miniere, poussiere, foret, eau et communautes a Boke ?",records,
        geography="Boké, Guinea")
    return {
        "schema_version":"TERRA_DATA_002G_INDICATORS",
        "indicators":len(records),
        "independent_scientific_source_families":2,
        "source_families":["WorldPop 2026","ESA WorldCover 2021"],
        "hacked_or_synthetic_values":False,
        "h016_selected_evidence":len(plan["evidence"]),
        "planner_status":plan["status"],
        "missing_topics":plan["missing_topics"],
        "model_calls_executed":0,
        "note":"More individually cited indicators, not new independent source studies."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--hi",required=True)
    p.add_argument("--qa",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    dest=Path(args.out)
    if dest.exists():
        raise ValueError("Output already exists: source snapshot preserved")
    records=expand(args.hi,args.qa)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("x",encoding="utf-8") as f:
        json.dump(records,f,ensure_ascii=False,indent=2)
    print(json.dumps(summary(records),ensure_ascii=False,indent=2))
    print("CREATED="+str(dest))

if __name__=="__main__":
    main()
