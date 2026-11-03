"""TERRA-DATA-002H: Assemble already existing FSDC evidence for one debate.

No new observations or Meta calls. Data lanes intentionally distinct:
(1) screened AOI observations from 010HI/J, (2) documentary Boké context,
(3) historical FAITH modeled climate reference point outside pilot rectangle.
"""
import argparse
import hashlib
import json
from pathlib import Path

from faith_indicator_expansion_002g import expand
from dynamic_council import plan_question
from fsdc_evidence_expansion import attach_regional_context
from faith_boke_context_guard_002e import inspect_context
from faith_chirps_aoi_guard_002i import check as check_chirps
from faith_environmental_context_002k import attach_environmental_context

QUESTION = "Comment concilier extraction miniere, poussiere, foret, eau et communautes a Boke ?"
CHIRPS_ROLE = "HASHED_IN_ORIGINAL_010HI_J_NOT_YET_EXTRACTED_AS_AOI_FINDING"

def case_file(hi_path, qa_path, question=QUESTION):
    observations=expand(hi_path,qa_path)
    chirps=check_chirps(hi_path,qa_path)
    observations.extend(chirps["accepted"])
    plan=attach_environmental_context(attach_regional_context(
        plan_question(question,observations,geography="Boké, Guinea")))
    climate=inspect_context()
    if climate["inside_exploratory_rectangle"] or climate["council_evidence"]:
        raise ValueError("FAITH climate context erroneously admitted to AOI")
    return {
        "schema_version":"TERRA_DATA_002H_CASE",
        "question":question,
        "plan":plan,
        "evidence_count":len(plan["evidence"]),
        "ao_i_source_families":["WorldPop 2026","ESA WorldCover 2021"] + (["CHIRPS"] if chirps["accepted"] else []),
        "regional_documentary_context_count":len(plan.get("regional_context",[]))-plan.get("environmental_context_count",0),
        "environmental_scientific_context_count":plan.get("environmental_context_count",0),
        "climate_reference":{
            "origin":"Historic FAITH FSMI NASA POWER computation",
            "geography":"Boke approximate prefectural point, NOT pilot rectangle",
            "point_lonlat":climate["prefectural_reference_point"],
            "indicators":climate["values_observed_in_existing_faith_snapshot"],
            "scientific_status":climate["source_scientific_status"],
            "not_an_aoi_observation":True,
            "not_in_meta_input_without_review":True
        },
        "chirps_status":chirps["status"],
        "chirps_accepted_count":len(chirps["accepted"]),
        "independent_aoi_dataset_count":2 + (1 if chirps["accepted"] else 0),
        "dust_local_numeric_concentration_admitted":False,
        "model_calls_executed":0,
        "external_requests_executed":0,
        "publication_gate":"HUMAN_SOURCE_AND_LICENSE_REVIEW_REQUIRED"
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hi",required=True)
    p.add_argument("--qa",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    result=case_file(a.hi,a.qa)
    dest=Path(a.out)
    if dest.exists():
        raise ValueError("Existing output preserved; choose a new name")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
       "status":result["plan"]["status"],
       "aoi_indicators":result["evidence_count"],
       "independent_aoi_datasets":result["independent_aoi_dataset_count"],
       "regional_context_sources":result["regional_documentary_context_count"],
       "historical_environmental_context_sources":result["environmental_scientific_context_count"],
       "missing_topics":result["plan"]["missing_topics"],
       "chirps":result["chirps_status"],
       "chirps_accepted_count":result["chirps_accepted_count"],
       "faith_climate":"CONTEXT_OUTSIDE_AOI",
       "meta_calls":0,
       "out":str(dest)
    },indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
