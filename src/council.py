"""HACK-002: FSDC evidence-gated Meta multi-stakeholder council.
Standard library only; remote calls occur exclusively with --execute.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib import request, error

from registry import load_registry, select_agents

SPARK = "muse-spark-1.3"
WONDER = "muse-wonder-1.0"
ENDPOINT = "https://api.meta.ai/v1/chat/completions"
MAX_AGENTS = 4

def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

def validate_evidence(items, sector):
    """Accept only explicitly ADMISSIBLE evidence for this sector; reject malformed records."""
    if not isinstance(items, list):
        raise ValueError("Evidence must be a JSON list")
    required = set(load_registry()["evidence_contract"]["required_fields"])
    out, ids = [], set()
    for e in items:
        if not isinstance(e, dict) or any(not e.get(k) for k in required):
            raise ValueError("Missing required FSDC provenance fields")
        if e["evidence_id"] in ids:
            raise ValueError("Duplicate evidence_id")
        ids.add(e["evidence_id"])
        if e["validation_status"] != "ADMISSIBLE":
            continue
        if sector not in e.get("sectors", []):
            continue
        if not e.get("finding"):
            raise ValueError("Admissible evidence must include finding")
        out.append({k: e[k] for k in sorted(required | {"finding"})})
    return out

def plan(question, sector, evidence, registry=None):
    registry = registry or load_registry()
    if not question.strip() or len(question) > 3000:
        raise ValueError("Question must have between 1 and 3000 characters")
    selected = select_agents(sector, registry)
    # Always include the scientific critic in the plan, outside the proposing agents.
    critics = [a for a in selected if a["id"] == "scientific_critic"]
    proposers = [a for a in selected if a["id"] != "scientific_critic"][:MAX_AGENTS]
    if not critics:
        raise ValueError("Scientific critic not configured for sector")
    admissible = validate_evidence(evidence, sector)
    return {
        "schema_version": "1.0", "status": "READY" if admissible else "ABSTAIN_NO_ADMISSIBLE_EVIDENCE",
        "question": question, "sector": sector,
        "proposers": [a["id"] for a in proposers],
        "critic": critics[0]["id"],
        "admissible_evidence": admissible,
        "evidence_sha256": fingerprint(admissible),
        "model_calls_planned": len(proposers) + 2 if admissible else 0,
        "note": "No stakeholder representation, field verification or decision approval is asserted."
    }

def meta_call(model, instruction, payload, api_key):
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    body = json.dumps({"model": model, "messages": [
        {"role": "developer", "content": instruction},
        {"role": "user", "content": content}
    ]}).encode("utf-8")
    req = request.Request(ENDPOINT, data=body, headers={
        "Authorization": "Bearer " + api_key, "Content-Type": "application/json",
        "Accept": "application/json"
    }, method="POST")
    try:
        with request.urlopen(req, timeout=90) as resp:
            data = json.load(resp)
    except error.HTTPError as exc:
        # Never print headers or credentials; do not blindly retry billed requests.
        raise RuntimeError("Meta API returned HTTP " + str(exc.code)) from None
    except error.URLError as exc:
        raise RuntimeError("Meta API connection failed; inspect network and account") from None
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Meta API response missing expected text") from None

def run_council(job, api_key, caller=meta_call):
    if job["status"] != "READY":
        raise ValueError("ABSTAIN: no admissible evidence; no model request permitted")
    if not api_key:
        raise ValueError("MODEL_API_KEY not set")
    e = job["admissible_evidence"]
    common = {"question": job["question"], "sector": job["sector"],
              "admissible_evidence": e, "evidence_sha256": job["evidence_sha256"]}
    positions = []
    for agent_id in job["proposers"]:
        instruction = (
            "You are a TerraCouncil analytical perspective: " + agent_id +
            ". This is simulated analysis, NOT an endorsement by any stakeholder. "
            "Use only supplied evidence. Every empirical assertion MUST cite an evidence_id. "
            "Separate facts, hypotheticals and missing evidence. NEVER fabricate numbers, "
            "impact, validation, stakeholder testimony or compliance approvals. "
            "Return concise analysis with investigation priorities and uncertainty."
        )
        positions.append({"agent_id": agent_id, "model": SPARK,
                          "text": caller(SPARK, instruction, common, api_key)})
    critique = caller(WONDER,
        "Act as an independent scientific critic. Challenge unsupported claims in each agent position, "
        "check evidence_id references only against provided evidence, enumerate disagreements, "
        "and explicitly call for abstention on unsupported conclusions. Do not invent evidence.",
        {**common, "positions": positions}, api_key)
    revision = caller(SPARK,
        "Synthesize a decision SUPPORT note, not an approval. Preserve explicit disagreement and critique. "
        "Cite only supplied evidence IDs for empirical statements. Label unknowns and investigations. "
        "Never assert human authorization, confirmed impacts, or field validation without evidence.",
        {**common, "positions": positions, "critique": critique}, api_key)
    return {"schema_version": "1.0", "status": "GENERATED_UNVERIFIED",
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "question": job["question"], "sector": job["sector"],
            "evidence_sha256": job["evidence_sha256"],
            "evidence_ids": [x["evidence_id"] for x in e],
            "positions": positions, "critique": {"model": WONDER, "text": critique},
            "revision": {"model": SPARK, "text": revision},
            "warnings": ["Model text is NOT mechanically verified for citation correctness.",
                         "Human scientific review required before external use."]}

def main():
    ap = argparse.ArgumentParser(description="TerraCouncil HACK-002")
    ap.add_argument("--question", required=True)
    ap.add_argument("--sector", default="mining")
    ap.add_argument("--evidence", help="Path to FSDC evidence JSON list (default: empty)")
    ap.add_argument("--out", help="Write prepared plan or runtime trace to JSON")
    ap.add_argument("--execute", action="store_true", help="Allow REAL, potentially billed Meta API calls")
    args = ap.parse_args()
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8")) if args.evidence else []
    job = plan(args.question, args.sector, evidence)
    if args.execute:
        if job["status"] != "READY":
            print("ABSTAIN: no admissible FSDC evidence; 0 API calls")
            result = job
        else:
            result = run_council(job, os.environ.get("MODEL_API_KEY", ""))
    else:
        result = job
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(output + "\n", encoding="utf-8")
        print(str(dest))
    else:
        print(output)

if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        sys.exit(2)
