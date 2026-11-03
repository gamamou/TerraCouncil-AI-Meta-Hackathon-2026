"""HACK-004: convert existing TERRA-META-010HI/J screening records into gated FSDC observations.

No synthetic scientific results. Requires exact 010HI/010HJ schemas, cross-file
source hashes and AOI agreement. Source files stay on the user's machine.
"""
import argparse
import hashlib
import json
from pathlib import Path

AOI = [-14.5, 10.5, -14.0, 11.0]
GEOGRAPHY = "Boké, Guinea"
STATUS = "SCREENED_NOT_FIELD_VALIDATED"

def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def records(hi, qa, source_hi="010HI_evidence.json", source_qa="010HJ_spatial_qa.json"):
    if hi.get("schema_version") != "010H-I-1" or qa.get("schema_version") != "010H-J-QA-1":
        raise ValueError("Unknown evidence or QA schema")
    if hi.get("status") != "MULTIDOMAIN_SCREENED_NOT_FIELD_VALIDATED":
        raise ValueError("Source screening status mismatch")
    if qa.get("status") != "READY_FOR_EXPLORATORY_COUNCIL":
        raise ValueError("QA not ready for exploratory use")
    if hi.get("aoi_bbox_epsg4326") != AOI or qa.get("aoi_bbox_epsg4326") != AOI:
        raise ValueError("AOI mismatch; do not assume administrative boundaries")
    if qa.get("errors") or qa.get("scientific_validation") not in (
            "NOT_FIELD_VALIDATED", "SCREENED_NOT_FIELD_VALIDATED"):
        raise ValueError("Unresolved QA errors or status mismatch")
    src = hi.get("source_evidence", {})
    pop = src.get("communities", {})
    cover = src.get("landcover", {})
    hashes = qa.get("input_files_sha256", {})
    if pop.get("sha256") != hashes.get("worldpop") or cover.get("sha256") != hashes.get("worldcover"):
        raise ValueError("Source raster hashes inconsistent between HI and HJ")
    if src.get("water_climate", {}).get("evidence_json_sha256") != hashes.get("chirps"):
        raise ValueError("CHIRPS reference hash inconsistent between HI and HJ")
    if pop.get("assessment") != "ESTIMATED_POPULATION_NOT_EXPOSURE":
        raise ValueError("Population assessment changed")
    if cover.get("assessment") != "LAND_COVER_PROXY_NOT_BIODIVERSITY_SURVEY":
        raise ValueError("Landcover assessment changed")
    if pop.get("measurement", {}).get("not_a_census") is not True:
        raise ValueError("Population estimate's non-census qualifier absent")
    estimated = pop["measurement"]["estimated_people_sum_cells"]
    classes = cover["measurement"]["classes"]
    for key in ("10", "40", "50", "80", "95"):
        if key not in classes:
            raise ValueError("Missing source landcover class " + key)
    source_refs = f"{source_hi} + {source_qa}; WorldPop SHA256 {pop['sha256']}; ESA SHA256 {cover['sha256']}"
    base = {
        "geography": GEOGRAPHY,
        "validation_status": STATUS,
        "provenance": source_refs,
        "sectors": ["mining", "environment", "agriculture", "simandou"],
    }
    def make(id, dataset, source, observed_at, method, license, finding):
        return {**base, "evidence_id": id, "dataset": dataset,
                "source": source, "observed_at": observed_at,
                "method": method, "license": license, "finding": finding}
    items = [
        make("BOKE-010HI-POP-2026",
             pop["dataset"], pop["url"], "2026",
             "Population raster cells summed over rectangular EPSG:4326 AOI; not exposure or census.",
             pop["license"],
             f"WorldPop 2026 estimated population raster cell sum for AOI {AOI}: {estimated}; not census, mine exposure or affected people."),
        make("BOKE-010HI-LC-2021",
             cover["dataset"], cover["url"], "2021",
             "ESA WorldCover classified raster area-weighted shares, rectangular AOI; not biodiversity field survey.",
             cover["license"],
             "ESA WorldCover 2021 AOI area-weighted cover shares: " +
             ", ".join(f"{classes[k]['name']} {classes[k]['area_weighted_share_pct']}%" for k in ("10","40","50","80","95")) +
             "; 2021 snapshot is not a 2026 change or a mining impact.")
    ]
    if len({r["evidence_id"] for r in items}) != len(items):
        raise ValueError("duplicate generated ID")
    return items

def build(hi_path, qa_path):
    return records(read(hi_path), read(qa_path),
                   source_hi=f"{Path(hi_path).name} SHA256 {file_sha(hi_path)}",
                   source_qa=f"{Path(qa_path).name} SHA256 {file_sha(qa_path)}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--hi", required=True)
    p.add_argument("--qa", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    result = build(a.hi, a.qa)
    dest = Path(a.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"EXPLORATORY_FSDC_RECORDS={len(result)}; NO_MODEL_CALLS; OUT={dest}")

if __name__ == "__main__":
    main()
