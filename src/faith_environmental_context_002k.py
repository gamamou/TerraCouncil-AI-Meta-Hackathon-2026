"""TERRA-DATA-002K: attach recovered FAITH environmental science as LIMITED context.

National source aggregates are NEVER local Boké AOI observations. The
documentary/context lane already exists in HACK-016B Spark/Wonder runtime.
Model transfer still requires explicit separate user consent in the existing UI.
"""
import hashlib
import json
from pathlib import Path
from dynamic_council import classify, plan_fingerprint
from faith_dust_context_002l1 import attach_dust_context

SNAPSHOT=Path(__file__).resolve().parents[1]/"data"/"faith_fsmI_environmental_snapshot_002k.json"
EXPECTED_IDS={
  "FAITH-MAUS-HANSEN-640","FAITH-CHENG-HISTORICAL-707",
  "FAITH-CPDM-FOOTPRINT-REFS-1012","FAITH-CHENG-CPDM-CHAIN",
  "FAITH-CHENG-REGIONAL-PROXIMITY"
}
EXPECTED_STATUS={
  "FAITH-MAUS-HANSEN-640":"EXISTING_FAITH_SCIENCE_NOT_SITE_ADMITTED",
  "FAITH-CHENG-HISTORICAL-707":"CHENG_HISTORICAL_CLASSIFICATION_COUNTS_ONLY",
  "FAITH-CPDM-FOOTPRINT-REFS-1012":"OBSERVED_FOOTPRINT_SCREENING_ONLY_NOT_FIELD_VERIFIED",
  "FAITH-CHENG-CPDM-CHAIN":"PARTY_CONTEXT_ONLY_NOT_CHENG_VERIFIED",
  "FAITH-CHENG-REGIONAL-PROXIMITY":"PUBLIC_HISTORICAL_OBSERVATIONS_REGIONAL_BUFFER_SCREENING_ONLY"
}
TOPIC_MATCHES={
 "FAITH-MAUS-HANSEN-640":{"mining","land","climate"},
 "FAITH-CHENG-HISTORICAL-707":{"mining","land"},
 "FAITH-CPDM-FOOTPRINT-REFS-1012":{"mining","governance"},
 "FAITH-CHENG-CPDM-CHAIN":{"mining","governance"},
 "FAITH-CHENG-REGIONAL-PROXIMITY":{"mining","land"},
}
def _canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"))

def read_snapshot(path=SNAPSHOT):
    obj=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if obj.get("schema_version")!="TERRA_DATA_002K_ENVIRONMENTAL_SNAPSHOT":
        raise ValueError("Unrecognized FAITH scientific snapshot")
    if obj.get("scope")!="GUINEA_NATIONAL_OR_NONCANONICAL_SCREENING_NOT_BOKE_AOI" or obj.get("metadata_only") is not True:
        raise ValueError("Invalid source geographical scope")
    entries=obj.get("source_entries")
    if not isinstance(entries,list) or {x["id"] for x in entries}!=EXPECTED_IDS or len(entries)!=5:
        raise ValueError("FAITH snapshot entry identities changed")
    for entry in entries:
        if entry.get("status")!=EXPECTED_STATUS[entry["id"]]:
            raise ValueError("Source status changed")
        if not isinstance(entry.get("caveats"),list) or not entry["caveats"]:
            raise ValueError("Missing source scientific limitations")
    if (entries[0]["source_fids"],entries[0]["zone_rows"],entries[1]["observations"],
        entries[2]["reference_records"],entries[3]["verified_cheng_to_permit_count"])!=(128,640,707,1012,0):
        raise ValueError("Source population identity changed")
    return obj

def attach_environmental_context(plan, snapshot_path=SNAPSHOT):
    snapshot=read_snapshot(snapshot_path)
    question=plan.get("question","")
    topics=set(classify(question,plan.get("sector"))["topics"])
    result=dict(plan)
    base=list(plan.get("regional_context",[]))
    if not ("bok" in question.casefold() and plan.get("geography")=="Boké, Guinea"):
        result["environmental_context_count"]=0
        return result
    additions=[]
    for entry in snapshot["source_entries"]:
        if not topics.intersection(TOPIC_MATCHES[entry["id"]]):
            continue
        numbers={k:v for k,v in entry.items() if k in (
           "source_fids","zone_rows","hansen_qa","numeric_populated_rows",
           "observations","source_sites","reference_records","geometry_in_payload",
           "screened_shape_count","party_link_shapes","verified_cheng_to_permit_count",
           "screening_points","buffer_radii_km","source_features_examined")}
        additions.append({
            "evidence_id":entry["id"],"source_type":"FAITH_HISTORICAL_NATIONAL_SCIENTIFIC_CONTEXT",
            "source_path":entry["source_path"],"source_period":entry.get("period",entry.get("snapshot_id","historical")),
            "claim":entry["title"]+"; original archived metrics and source population recorded as historical, not local AOI results.",
            "metrics":numbers,
            "scope":"Guinea national or approximate regional screening, not validated Boké pilot",
            "coverage_relation":"NON_AOI_CONTEXT_NOT_GEOGRAPHICALLY_ADMITTED",
            "validation_status":entry["status"],
            "limitations":entry["caveats"],
            "scientific_publication_status":"CONTEXT_ONLY_NOT_AOI_FACT",
        })
    result["regional_context"]=base+additions
    result["environmental_context_count"]=len(additions)
    result["regional_context_sha256"]=hashlib.sha256(
        _canonical(result["regional_context"]).encode("utf-8")).hexdigest()
    result["plan_sha256"]=plan_fingerprint(result)
    return attach_dust_context(result)
