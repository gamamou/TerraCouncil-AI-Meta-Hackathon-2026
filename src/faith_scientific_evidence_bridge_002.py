"""TERRA-DATA-002: read-only FAITH/FSMI evidence bridge for TerraCouncil.

Offline standard-library program. Explicit local source paths only. Scientific
admission is intentionally NOT performed here. The immutable intake report is
not an agent-ready evidence list; no model or network calls occur.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

SCHEMA = "TERRA_FAITH_BRIDGE_002"
MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 50000
SOURCES = {
    "FSMI_HANSEN_640": {
        "kind":"csv","filename":"maus_evidence_640_v101.csv",
        "expected_rows":640,
        "columns":["maus_fid","zone","hansen_valid_fraction","hansen_qa",
                   "hansen_loss_30pct_rate","hansen_loss_50pct_rate"],
        "geography":"Guinea national MAUS 128 fids × five relative zones",
        "status":"EXISTING_FAITH_SCIENCE_NOT_SITE_ADMITTED",
        "note":"Hansen zone/screening only, no causal attribution, no company geofence."},
    "FSMI_CHENG_CLASSES": {
        "kind":"json","filename":"guinea-cheng-landuse-index.json",
        "keys":["status","doi","display_polygons","source_site_count",
                "area_estimate_authorized","company_attribution_verified"],
        "expected":{"status":"CHENG_HISTORICAL_CLASSIFICATION_COUNTS_ONLY",
                    "display_polygons":707,"source_site_count":199,
                    "area_estimate_authorized":False,
                    "company_attribution_verified":False},
        "geography":"Guinea historical Cheng source subset",
        "status":"HISTORICAL_CLASS_COUNTS_NOT_SITE_ATTRIBUTABLE",
        "note":"Source-site categories, not surface areas or verified mines."},
    "FSMI_CAMS_REGIONAL": {
        "kind":"json","filename":"guinea-cams-air-quality-september-2026.json",
        "keys":["policy","status","reference_period","records",
                "sensed_pm_observations","mine_attribution_established",
                "approved_mine_aois"],
        "expected":{"policy":"FSMI_CAMS_AIR_QUALITY_001",
                    "status":"PUBLIC_CAMS_REGIONAL_MODEL_CONTEXT_NOT_GROUND_MONITORING",
                    "reference_period":"2026-09-01/2026-09-30",
                    "sensed_pm_observations":0,"mine_attribution_established":False,
                    "approved_mine_aois":0},
        "expected_records":10,
        "geography":"Guinea ten approximate cadastral screening points",
        "status":"REGIONAL_MODELED_AIR_NOT_ONSITE",
        "note":"CAMS via Open-Meteo, 45-km model; never measured mine PM."},
    "FSMI_WORLDPOP_OSM": {
        "kind":"json","filename":"guinea-worldpop-buildings-buffers.json",
        "keys":["policy","status","records","population_year",
                "population_is_model_estimate","population_is_mine_affected",
                "site_attribution_verified"],
        "expected":{"policy":"FSMI_WORLDPOP_OSM_BUILDINGS_001",
                    "population_year":2020,"population_is_model_estimate":True,
                    "population_is_mine_affected":False,
                    "site_attribution_verified":False},
        "expected_records":10,
        "geography":"Guinea ten screening-point buffers",
        "status":"MODELED_POPULATION_NOT_AFFECTED_PEOPLE",
        "note":"2020 gridded estimated population, 2024 mapped OSM buildings; coverage incomplete."},
    "CPDM_FOOTPRINT_REFS": {
        "kind":"json","filename":"guinea-observed-footprint-screening.json",
        "keys":["status","record_count","geometry_in_payload","records"],
        "expected":{"status":"OBSERVED_FOOTPRINT_SCREENING_ONLY_NOT_FIELD_VERIFIED",
                    "record_count":1012,"geometry_in_payload":False},
        "expected_records":1012,
        "geography":"Guinea historical CPDM 20260716_232803_UTC",
        "status":"HISTORICAL_FOOTPRINT_REFS_NOT_VERIFIED_INTERSECTIONS",
        "note":"1012 Base44 snapshot rows, not distinct validated MAUS-permit spatial joins."},
    "FSMI_WIND_HOURLY": {
        "kind":"json","filename":"guinea-hourly-wind-september-2026.json",
        "keys":["policy","status","records","observed_ground_wind_sensors",
                "model_dispersion_validated","company_emissions_verified"],
        "expected":{"policy":"FSMI_HOURLY_REGIONAL_METEO_091I",
                    "status":"REGIONAL_MODELED_HOURLY_WIND_NOT_ONSITE_NOT_MINING_DISPERSION",
                    "observed_ground_wind_sensors":0,
                    "company_emissions_verified":False,
                    "model_dispersion_validated":False},
        "expected_records":10,
        "geography":"Guinea ten regional model screening points",
        "status":"METEO_REGIONAL_NOT_DISPERSION_INPUT_VALIDATED",
        "note":"Regional model is not site AERMET meteorology or mine plume."},
    "MAUS_LEGACY_572": {
        "kind":"csv","filename":"maus_v2_overlap_by_license.csv",
        "columns":["guidLicense","maus_ov_ha","has_maus"],
        "expected_rows":572,
        "geography":"Guinea legacy 572-row local cadastral workflow",
        "status":"LEGACY_V1_SOURCE_UNIVERSE_NOT_NATIONAL",
        "note":"35 historic Yes rows; independent geographic identity match not established."},
}
def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def inspect(asset_id,path,expected_sha=None):
    if asset_id not in SOURCES:
        raise ValueError("Unrecognized source identifier")
    cfg=SOURCES[asset_id]
    p=Path(path)
    if p.name!=cfg["filename"]:
        raise ValueError("Unexpected source filename")
    if not p.is_file() or p.is_symlink() or p.stat().st_size>MAX_BYTES:
        raise ValueError("Missing, symbolic link or oversized source file")
    raw=p.read_bytes()
    digest=sha256_bytes(raw)
    if expected_sha and expected_sha.lower()!=digest:
        raise ValueError("Source hash differs from declared immutable input")
    result={"asset_id":asset_id,"source_basename":p.name,
            "source_sha256":digest,"source_bytes":len(raw),
            "source_identity": "SHA256_VERIFIED" if expected_sha else "SHA256_CAPTURED_NOT_PRIOR_VERIFIED",
            "source_geography":cfg["geography"],"source_scientific_status":cfg["status"],
            "interpretation_limit":cfg["note"],
            "admission":"QUARANTINED_UNTIL_AOI_AND_LICENSE_REVIEW",
            "council_evidence_generated":False}
    if cfg["kind"]=="json":
        obj=json.loads(raw.decode("utf-8-sig"))
        if not isinstance(obj,dict) or any(k not in obj for k in cfg["keys"]):
            raise ValueError("Missing JSON schema keys")
        for k,v in cfg.get("expected",{}).items():
            if type(obj[k]) is not type(v) or obj[k]!=v:
                raise ValueError("Source scientific contract mismatch: "+k)
        if "expected_records" in cfg:
            if not isinstance(obj["records"],list) or len(obj["records"])!=cfg["expected_records"]:
                raise ValueError("Unexpected record count")
            result["observed_row_count"]=len(obj["records"])
        elif asset_id=="FSMI_CHENG_CLASSES":
            result["historical_polygon_observations"]=obj["display_polygons"]
            result["historical_source_site_count"]=obj["source_site_count"]
    else:
        from io import StringIO
        reader=csv.DictReader(StringIO(raw.decode("utf-8-sig")))
        if reader.fieldnames is None or len(set(reader.fieldnames))!=len(reader.fieldnames):
            raise ValueError("Invalid CSV headers")
        if any(k not in reader.fieldnames for k in cfg["columns"]):
            raise ValueError("Missing CSV scientific columns")
        rows=0
        for row in reader:
            rows+=1
            if rows>MAX_ROWS:raise ValueError("Too many rows")
            if None in row:raise ValueError("Malformed CSV record")
        if rows!=cfg.get("expected_rows"):
            raise ValueError("Unexpected CSV record count")
        result["observed_row_count"]=rows
    return result

def build_report(inputs):
    if not isinstance(inputs,dict):
        raise ValueError("Expected asset-to-file mapping")
    audited=[];used=set()
    for asset_id,options in sorted(inputs.items()):
        if asset_id in used:raise ValueError("Duplicate source")
        used.add(asset_id)
        if not isinstance(options,dict) or "path" not in options:
            raise ValueError("Each source must declare path")
        audited.append(inspect(asset_id,options["path"],options.get("sha256")))
    return {"schema_version":SCHEMA,"status":"RECOVERY_INTAKE_NOT_SCIENCE_ADMISSION",
            "read_only":True,"network_calls":0,"model_calls":0,
            "evidence_record_count":0,"assets":audited,
            "limits":["No file content is included in this report, only hashes and metadata.",
                      "Source contract and hash checks do not establish scientific field validity.",
                      "Boke AOI selection and source-rights review required before Council evidence.",
                      "Do not merge 572 legacy MAUS rows with 1012 national footprint references."]}

def load_input_manifest(path):
    """Accept plain UTF-8 and Windows PowerShell UTF-8 with BOM."""
    data=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data,dict):
        raise ValueError("Input manifest must be a JSON object")
    return data

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest",help="Local JSON map {asset_id:{path,sha256?}}")
    ap.add_argument("--out",help="Local private JSON report path")
    ap.add_argument("--list",action="store_true")
    args=ap.parse_args()
    if args.list:
        for k,v in SOURCES.items():print(k,":",v["filename"],"|",v["status"])
        return
    if not args.manifest or not args.out:ap.error("--manifest and --out required")
    out=Path(args.out).expanduser()
    if out.exists():ap.error("Report exists; overwrite forbidden")
    report=build_report(load_input_manifest(args.manifest))
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print("AUDITED_ASSETS=",len(report["assets"]))
    print("SCIENTIFIC_STATUS=",report["status"])
    print("COUNCIL_EVIDENCE_GENERATED=0")
    print("PRIVATE_REPORT=",out)

if __name__=="__main__":main()
