"""TERRA-DATA-002I: guarded CHIRPS AOI value extraction from original 010HI/J.

Does not call CHIRPS API or calculate rainfall. Requires a real, explicitly
declared *AOI* measurement in the original water_climate section. A source hash
alone is NOT a numerical measurement, and Kankan is not Boké.
"""
import argparse
import json
from pathlib import Path
from import_boke_010hi import AOI, GEOGRAPHY, STATUS, build, read

MEASUREMENT_FIELDS = ("precip_mm", "rainfall_mm", "rain_mm")
PERIOD_FIELDS = ("reference_period", "period", "observed_at")
SOURCE_FIELDS = ("source_url", "url")
LICENSE_FIELDS = ("license",)

def first_string(obj,keys):
    for key in keys:
        value=obj.get(key)
        if isinstance(value,str) and value.strip():
            return value.strip()
    return None

def check(hi_path,qa_path):
    # This executes original 010HI/J cross-source hash and scientific QA first.
    base=build(hi_path,qa_path)
    hi=read(hi_path)
    w=hi.get("source_evidence",{}).get("water_climate",{})
    if not isinstance(w,dict):
        raise ValueError("water_climate must be object")
    result={"status":"REFERENCED_NOT_QUANTIFIED",
            "source_hash":w.get("evidence_json_sha256"),
            "source_fields":sorted(w.keys()),
            "measurement_fields":sorted(w.get("measurement",{}).keys())
             if isinstance(w.get("measurement"),dict) else [],
            "accepted":[],
            "original_observations":len(base),
            "network_calls":0}
    measure=w.get("measurement")
    if not isinstance(measure,dict):
        return result
    # Require an explicit exact AOI, never infer from filename/region name.
    local_bbox=measure.get("aoi_bbox_epsg4326")
    if local_bbox != AOI:
        result["status"]="ABSTAIN_MEASUREMENT_AOI_UNVERIFIED"
        return result
    # Explicit source and license required, not a guessed default.
    value=next(((key,measure[key]) for key in MEASUREMENT_FIELDS if key in measure),None)
    source=first_string(measure,SOURCE_FIELDS) or first_string(w,SOURCE_FIELDS)
    license_name=first_string(measure,LICENSE_FIELDS) or first_string(w,LICENSE_FIELDS)
    period=first_string(measure,PERIOD_FIELDS) or first_string(w,PERIOD_FIELDS)
    if not value or not source or not license_name or not period:
        result["status"]="ABSTAIN_INCOMPLETE_MEASUREMENT_METADATA"
        return result
    variable,quantity=value
    if isinstance(quantity,bool) or not isinstance(quantity,(int,float)) or not 0<=quantity<=20000:
        result["status"]="ABSTAIN_INVALID_MEASUREMENT"
        return result
    if "chirps" not in json.dumps(w,ensure_ascii=False).casefold():
        result["status"]="ABSTAIN_SOURCE_FAMILY_UNVERIFIED"
        return result
    if not source.startswith("https://"):
        result["status"]="ABSTAIN_SOURCE_URL_NOT_HTTPS"
        return result
    # No status escalation beyond SCREENED_NOT_FIELD_VALIDATED.
    common=base[0]
    finding=(f"CHIRPS precipitation {variable} of {quantity} mm for period {period} "
        f"within exploratory rectangular AOI {AOI}, as recorded in original "
        "010HI/010HJ evidence; not a field gauge, flood risk estimate or mining impact.")
    record={
       "evidence_id":"BOKE-010HI-CHIRPS-RAINFALL",
       "dataset":"CHIRPS source referenced in TerraCouncil 010HI",
       "source":source,"observed_at":period,"geography":GEOGRAPHY,
       "method":"Recorded original CHIRPS AOI precipitation field, no new calculation; source-defined temporal period.",
       "license":license_name,"validation_status":STATUS,
       "provenance":common["provenance"]+"; original CHIRPS SHA256 "+str(w["evidence_json_sha256"]),
       "finding":finding,"sectors":list(common["sectors"]),
    }
    result["status"]="SCREENED_AOI_CHIRPS_MEASUREMENT"
    result["accepted"]=[record]
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--hi",required=True)
    p.add_argument("--qa",required=True)
    p.add_argument("--out",help="New private JSON file for generated records; no overwrite")
    args=p.parse_args()
    result=check(args.hi,args.qa)
    if args.out:
        dest=Path(args.out)
        if dest.exists():
            raise ValueError("Existing output preserved")
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("x",encoding="utf-8") as f:
            json.dump(result["accepted"],f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!="accepted"}|
      {"accepted_count":len(result["accepted"])},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
