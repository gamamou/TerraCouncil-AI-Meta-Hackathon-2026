"""TERRA-DATA-002E: verify recovered Boké point context, not admission.

Offline, standard library only. The recovered reference point is OUTSIDE the
old exploratory pilot rectangle. No model calls or source recomputation.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"data"/"boke_nasa_power_context_candidate_002e.json"

def inspect_context(path=SOURCE):
    raw=Path(path).read_bytes()
    item=json.loads(raw.decode("utf-8-sig"))
    if item.get("schema_version")!="TERRA_BOKE_CONTEXT_CANDIDATE_002E":
        raise ValueError("Invalid scientific candidate contract")
    if item.get("scientific_tier")!="CONTEXT_CANDIDATE_NOT_AOI_ADMITTED" or item.get("council_admission") is not False:
        raise ValueError("Unapproved scientific admission")
    point=item.get("indicator_location",{})
    bbox=item.get("pilot_aoi_bbox_epsg4326")
    lon=point.get("reference_lon");lat=point.get("reference_lat")
    if not all(isinstance(n,(int,float)) and not isinstance(n,bool) for n in [lon,lat,*bbox]):
        raise ValueError("Invalid coordinate types")
    inside=(bbox[0]<=lon<=bbox[2] and bbox[1]<=lat<=bbox[3])
    if inside!=item.get("point_inside_pilot_rectangle"):
        raise ValueError("Source AOI location mismatch")
    if not item.get("source_reference",{}).get("response_sha256"):
        raise ValueError("Missing historic response hash")
    if not item.get("scientific_limits"):
        raise ValueError("Missing science limitations")
    return {
        "schema_version":"TERRA_CONTEXT_GUARD_RESULT_002E",
        "candidate_sha256":hashlib.sha256(raw).hexdigest(),
        "source_system":"FAITH FSMI, pre-existing calculation",
        "prefectural_reference_point":[lon,lat],
        "inside_exploratory_rectangle":inside,
        "measurement_period":item["period"],
        "source_scientific_status":item["source_status"],
        "values_observed_in_existing_faith_snapshot":item["indicators"],
        "context_status":"REFERENCE_POINT_OUTSIDE_PILOT_AOI" if not inside else "POINT_WITHIN_RECTANGLE_NOT_AREAL_MEAN",
        "council_evidence":[],
        "council_admission":"BLOCKED_PENDING_AOI_AND_LICENSE",
        "model_calls":0,"network_calls":0,
        "statement":"Source is a pre-existing modeled point climatology, not mining-site or prefecture average evidence."
    }

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",default=str(SOURCE))
    args=parser.parse_args()
    print(json.dumps(inspect_context(args.source),ensure_ascii=False,indent=2))
