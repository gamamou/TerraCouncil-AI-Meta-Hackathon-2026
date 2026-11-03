"""TERRA-DATA-002D: source discovery for the existing HACK-016 planner.

Shows actual FAITH source pointers by topic, with geographic exclusions.
This is NOT an evidence importer and must never call Meta, Base44 or APIs.
"""
import argparse
import json
from pathlib import Path

from dynamic_council import classify, plan_question
from verification import evidence_hash

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config" / "faith_fsmi_existing_sources_002.json"
SOURCE_LABEL = "CATALOG_POINTER_NOT_GEOSPATIAL_OBSERVATION"

def geography_scope(entry, geography):
    scope = str(entry.get("scope", "")).casefold()
    if "kankan only" in scope:
        return "EXCLUDE_OTHER_REGION"
    if "us epa" in scope:
        return "EXCLUDE_OTHER_COUNTRY"
    if entry["id"] == "FSMI_AERMOD_REFERENCE":
        return "METHOD_BENCHMARK_ONLY_NOT_LOCAL_DATA"
    if entry["id"] == "MAUS_LEGACY_572":
        return "LEGACY_UNIVERSE_GEOGRAPHY_UNRESOLVED"
    return "NATIONAL_OR_APPROXIMATE_LOCATION_NOT_AOI_VERIFIED"

def source_readiness(question, geography="Boké, Guinea", catalog_path=CATALOG):
    decision = classify(question)
    if not isinstance(geography, str) or not geography.strip():
        raise ValueError("Explicit geography required")
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8-sig"))
    if catalog.get("schema_version") != "TERRA_FAITH_SOURCE_CATALOG_002":
        raise ValueError("Unknown FAITH catalog")
    topics = set(decision["topics"])
    matched = []
    for src in catalog["sources"]:
        overlap = sorted(topics.intersection(src.get("role_topics", [])))
        if overlap:
            matched.append({
                "source_id": src["id"],
                "base44_or_local_pointer": src["path"],
                "matching_topics": overlap,
                "location_gate": geography_scope(src, geography),
                "scientific_limitation": src["scientific_limit"],
                "status": SOURCE_LABEL
            })
    # Exercise the real existing council planner with no evidence.
    # A source pointer does not become factual evidence by being relevant.
    council = plan_question(question, [], geography=geography)
    return {
        "schema_version": "TERRA_FAITH_READINESS_002D",
        "question": question,
        "geography": geography,
        "question_topics": decision["topics"],
        "recognized_sector": decision["sector"],
        "source_candidates": matched,
        "matched_candidate_sources": len(matched),
        "missing_source_topics": sorted(topics-set(t for e in matched for t in e["matching_topics"])),
        "council_status": council["status"],
        "council_evidence_count": len(council["evidence"]),
        "council_evidence_sha256": evidence_hash([]),
        "model_calls_executed": 0,
        "external_requests_executed": 0,
        "scientific_admission": "NONE",
        "next_gate": "Existing local/approved source bytes + exact AOI and licenses + reviewed findings"
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question",required=True)
    parser.add_argument("--geography",default="Boké, Guinea")
    parser.add_argument("--out",help="Optional new private JSON report; existing files never overwritten")
    args=parser.parse_args()
    result=source_readiness(args.question,args.geography)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.out:
        dest=Path(args.out).expanduser()
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("x",encoding="utf-8") as f:
            json.dump(result,f,ensure_ascii=False,indent=2)

if __name__=="__main__":
    main()
