"""TERRA-DATA-002L1: dust science context from existing FSMI source outputs.

Never equate regional CAMS model, 10m winds or EPA SO2 reference benchmark
to observed Boké mine concentrations. No API calls or scientific recomputation.
"""
import hashlib
import json
from pathlib import Path
from dynamic_council import plan_fingerprint
from faith_dust_decision_protocol_002m import attach_protocol

SOURCE=Path(__file__).resolve().parents[1]/"data"/"faith_dust_atmospheric_context_002l1.json"
EXPECTED={
 "FAITH-CAMS-AIR-SEPT2026":"PUBLIC_CAMS_REGIONAL_MODEL_CONTEXT_NOT_GROUND_MONITORING",
 "FAITH-WIND-SEPT2026":"REGIONAL_MODELED_HOURLY_WIND_NOT_ONSITE_NOT_MINING_DISPERSION",
 "FAITH-AERMOD-EPA-REFERENCE":"REAL_EPA_EXECUTION_NUMERICAL_REFERENCE_MATCH"
}
def read_dust(path=SOURCE):
    obj=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if obj.get("schema_version")!="TERRA_DUST_002L1" or obj.get("scope")!="GUINEA_REGIONAL_SCREENING_CONTEXT_NOT_MINE_ATTRIBUTION":
        raise ValueError("Invalid regional dust scope")
    rows=obj.get("sources")
    if not isinstance(rows,list) or len(rows)!=3 or {v["id"] for v in rows}!=set(EXPECTED):
        raise ValueError("Missing or extra regional dust source")
    for x in rows:
        if x.get("status")!=EXPECTED[x["id"]] or not x.get("restrictions"):
            raise ValueError("Dust status or limitations tampered")
    cams,winds,benchmark=rows
    if (cams["ground_sensor_measurements"]!=0 or cams["mine_attribution_verified"] is not False
       or cams["spatial_resolution_approx_km"]!=45 or cams["regional_model_points"]!=10
       or winds["ground_wind_sensors"]!=0 or winds["dispersion_validated"] is not False
       or benchmark["benchmark_pollutant"]!="SO2" or benchmark["validated_guinea_mine_dispersion"] is not False
       or benchmark["field_sensor_calibration_passed"] is not False):
        raise ValueError("Dust ground truth or source claims altered")
    return obj

def attach_dust_context(plan,path=SOURCE):
    if "dust" not in plan.get("topics",[]) or plan.get("geography")!="Boké, Guinea":
        return dict(plan,dust_context_count=0)
    source=read_dust(path)
    additions=[]
    for item in source["sources"]:
        metrics={}
        if item["id"]=="FAITH-CAMS-AIR-SEPT2026":
            metrics={"points":item["regional_model_points"],"model_resolution_km":item["spatial_resolution_approx_km"],
                     "model_point_example":item["example_point"]}
        elif item["id"]=="FAITH-WIND-SEPT2026":
            metrics={"points":item["regional_model_points"],"hourly_records_per_point":item["hourly_samples_each"]}
        else:
            metrics={"reference_pollutant":"SO2","us_ranked_values_matched":item["matched_ranked_concentrations"],
                     "us_peak_values_matched":item["matched_highest_values"]}
        additions.append({
          "evidence_id":item["id"],"source_type":"FSMI_MODELED_REGIONAL_ATMOSPHERIC_CONTEXT",
          "source_path":item["path"],"source_period":item.get("period",item.get("reference_area")),
          "scope":"Guinea regional contextual sample or USA benchmark; NOT observed Boké mine emissions",
          "coverage_relation":"REGIONAL_MODEL_OR_US_BENCHMARK_NOT_LOCAL_SENSOR",
          "claim":"Historic FAITH/FSMI "+item["policy"]+"; atmospheric context only, not mine impact or receptor exposure.",
          "validation_status":item["status"],
          "metrics":metrics,"limitations":item["restrictions"],
          "scientific_publication_status":"CONTEXT_ONLY_NOT_AOI_FACT"})
    result=dict(plan)
    result["regional_context"]=list(plan.get("regional_context",[]))+additions
    result["dust_context_count"]=3
    result["dust_aoi_concentration_admitted"]=False
    result["regional_context_sha256"]=hashlib.sha256(json.dumps(result["regional_context"],sort_keys=True,
                         ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()
    result=attach_protocol(result)
    result["plan_sha256"]=plan_fingerprint(result)
    return result
