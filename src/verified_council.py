"""HACK-003 runnable evidence-verified multi-perspective council.

Two independent deterministic gates surround every AI step.
Default dry-run uses NO model API and never upgrades evidence status.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys

from council import SPARK, WONDER, meta_call
from registry import load_registry, select_agents
from verification import gate_evidence, verify_submission

GEOGRAPHY = "Boké, Guinea"
MAX_PROPOSERS = 4

PROMPT = """You are an analytical perspective of TerraCouncil, not an actual stakeholder.
Use ONLY the supplied FSDC evidence. Return STRICT JSON object with EXACTLY these keys:
{"observations":[{"evidence_id":"...","finding":"EXACT VERBATIM finding from evidence"}],
 "hypotheses":["unverified hypothesis phrased explicitly as uncertain"],
 "investigations":["suggested investigation, not an empirical fact"],
 "abstentions":["what evidence does not allow you to conclude"]}
Observations MUST copy an actual supplied finding byte-for-byte with correct evidence_id.
NEVER paraphrase evidence findings in observations or add narrative fields.
Never assert causation, impacts, permits, field validation, approvals or stakeholder endorsement.
Hypotheses and investigations are NOT validated scientific claims.
You MUST NOT change, disable, or bypass verification gates.
Return JSON only, no Markdown."""

def prepare(question, evidence, sector="mining", geography=GEOGRAPHY):
    if not isinstance(question, str) or not question.strip() or len(question) > 3000:
        raise ValueError("Invalid question length")
    selected = select_agents(sector)
    proposers = [x["id"] for x in selected if x["id"] != "scientific_critic"][:MAX_PROPOSERS]
    if not any(x["id"] == "scientific_critic" for x in selected):
        raise ValueError("Independent scientific critic is required")
    gate = gate_evidence(evidence, sector, geography)
    return {
        "status": gate["status"], "question": question, "sector": sector,
        "geography": geography, "proposers": proposers, "critic": "scientific_critic",
        "gate": gate, "model_calls_planned": len(proposers) + 2 if gate["evidence"] else 0,
        "mode": "PREPARED_NO_MODEL_CALLS",
        "human_review_required": True
    }

def _step(role, model, payload, gate, key, caller):
    raw = caller(model, PROMPT + "\nRole: " + role, payload, key)
    verified = verify_submission(raw, gate["evidence"], gate["evidence_sha256"])
    return {
        "role": role, "model": model,
        "verification_status": verified["status"],
        "verification_issues": verified["issues"],
        "published": verified.get("publication"),
        "valid": verified["verified"]
    }

def deliberate(job, api_key, caller=meta_call):
    if not job["gate"]["evidence"]:
        return {"status": "ABSTAIN_NO_USABLE_EVIDENCE", "calls_attempted": 0, "steps": []}
    if not api_key:
        raise ValueError("MODEL_API_KEY not set")
    gate = job["gate"]
    common = {"question": job["question"], "sector": job["sector"],
              "geography": job["geography"], "evidence": gate["evidence"],
              "evidence_sha256": gate["evidence_sha256"],
              "validation_note": "Boké is NOT_FIELD_VALIDATED; exploratory evidence is NOT causal proof"}
    steps = []
    for agent in job["proposers"]:
        step = _step(agent, SPARK, common, gate, api_key, caller)
        steps.append(step)
        if not step["valid"]:
            return {"status": "BLOCKED_BY_INDEPENDENT_VERIFIER",
                    "blocked_at": agent, "calls_attempted": len(steps), "steps": steps,
                    "human_review_required": True}
    critique = _step("scientific_critic", WONDER,
                     {**common, "verified_positions": [x["published"] for x in steps]},
                     gate, api_key, caller)
    steps.append(critique)
    if not critique["valid"]:
        return {"status": "BLOCKED_BY_INDEPENDENT_VERIFIER", "blocked_at": "scientific_critic",
                "calls_attempted": len(steps), "steps": steps, "human_review_required": True}
    synthesis = _step("final_synthesis", SPARK,
                      {**common, "verified_positions": [x["published"] for x in steps[:-1]],
                       "verified_critique": critique["published"]},
                      gate, api_key, caller)
    steps.append(synthesis)
    if not synthesis["valid"]:
        return {"status": "BLOCKED_BY_INDEPENDENT_VERIFIER", "blocked_at": "final_synthesis",
                "calls_attempted": len(steps), "steps": steps, "human_review_required": True}
    return {"status": "STRUCTURALLY_VERIFIED_HUMAN_REVIEW_REQUIRED",
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "evidence_sha256": gate["evidence_sha256"],
            "calls_attempted": len(steps), "steps": steps,
            "decision_support": synthesis["published"],
            "human_review_required": True,
            "limitations": "Exact citation/metadata matching only; scientific accuracy and causal inference not independently proven."}

def main():
    p = argparse.ArgumentParser(description="HACK-003 verified FAITH council, no Muse Code")
    p.add_argument("--question", required=True)
    p.add_argument("--sector", default="mining")
    p.add_argument("--geography", default=GEOGRAPHY)
    p.add_argument("--evidence", help="Local JSON evidence array; never upload private data to public GitHub")
    p.add_argument("--execute", action="store_true", help="Make actual potentially billable Meta calls")
    p.add_argument("--out", help="Local result JSON")
    args = p.parse_args()
    records = json.loads(Path(args.evidence).read_text(encoding="utf-8")) if args.evidence else []
    job = prepare(args.question, records, args.sector, args.geography)
    if args.execute:
        result = deliberate(job, os.environ.get("MODEL_API_KEY", ""))
    else:
        result = job
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
        print(str(target))
    else:
        print(text)

if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        sys.exit(2)
