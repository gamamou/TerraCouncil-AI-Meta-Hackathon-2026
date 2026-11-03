"""HACK-003: independent FSDC evidence and decision verification.

Pure Python, no models, no network and no agent-controlled bypass.
This verifier checks identity, provenance metadata and exact quoted findings.
It cannot independently establish that a source's scientific conclusion is true.
"""
import hashlib
import json

REQUIRED = (
    "evidence_id", "dataset", "source", "observed_at", "geography",
    "method", "license", "validation_status", "provenance", "finding",
)
EXPLORATORY = {"SCREENED_NOT_FIELD_VALIDATED", "NOT_FIELD_VALIDATED"}
ACCEPTED = EXPLORATORY | {"ADMISSIBLE"}
RESPONSE_KEYS = {"observations", "hypotheses", "investigations", "abstentions"}
MAX_RECORDS = 50

def _canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def evidence_hash(records):
    return hashlib.sha256(_canonical(records).encode("utf-8")).hexdigest()

def gate_evidence(records, sector, geography):
    """Return immutable-input copy of usable observations; never upgrade scientific status."""
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError("Evidence must be a JSON list with at most 50 records")
    seen, approved, rejected = set(), [], []
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("Evidence record must be an object")
        if any(not isinstance(record.get(k), str) or not record[k].strip() for k in REQUIRED):
            raise ValueError("Incomplete evidence at index " + str(idx))
        eid = record["evidence_id"]
        if eid in seen:
            raise ValueError("Duplicate evidence_id")
        seen.add(eid)
        status = record["validation_status"]
        if status not in ACCEPTED:
            rejected.append({"evidence_id": eid, "reason": "unsupported_status"})
            continue
        if sector not in record.get("sectors", []):
            rejected.append({"evidence_id": eid, "reason": "sector_mismatch"})
            continue
        # Strict pilot geography contract; no fuzzy/geocoding or assumed overlap.
        if record["geography"] != geography:
            rejected.append({"evidence_id": eid, "reason": "geography_mismatch"})
            continue
        # Preserve the source's exact asserted finding and status.
        clean = {k: record[k] for k in REQUIRED}
        clean["sectors"] = list(record["sectors"])
        clean["usage"] = "exploratory_only" if status in EXPLORATORY else "source_documented"
        approved.append(clean)
    return {
        "status": "EVIDENCE_READY_EXPLORATORY" if approved and any(x["usage"] == "exploratory_only" for x in approved)
                  else ("EVIDENCE_READY" if approved else "ABSTAIN_NO_USABLE_EVIDENCE"),
        "evidence": approved, "rejected": rejected, "evidence_sha256": evidence_hash(approved),
        "limits": ["Metadata checks do not establish source authenticity or scientific correctness.",
                   "Exploratory records must not be used to claim confirmed impact or causality."]
    }

def _parse_response(raw):
    """Reject non-JSON and unexpected fields rather than 'repairing' assertions."""
    if isinstance(raw, dict):
        obj = raw
    elif isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            raise ValueError("Response is not strict JSON") from None
    else:
        raise ValueError("Response must be JSON object or JSON string")
    if not isinstance(obj, dict) or set(obj) != RESPONSE_KEYS:
        raise ValueError("Response schema mismatch")
    for key in RESPONSE_KEYS:
        if not isinstance(obj[key], list) or len(obj[key]) > 30:
            raise ValueError("Response list invalid: " + key)
    return obj

def verify_submission(raw, evidence, expected_hash):
    """Fail closed. Only exact known findings may be published as factual observations.

    Free-form text (hypotheses/investigations) remains unverified and is clearly labeled.
    All evidence metadata must be checked outside the AI invocation.
    """
    if evidence_hash(evidence) != expected_hash:
        return {"status": "BLOCKED_EVIDENCE_CHANGED", "verified": False, "issues": ["evidence_sha256_mismatch"]}
    by_id = {x["evidence_id"]: x for x in evidence}
    if len(by_id) != len(evidence):
        return {"status": "BLOCKED", "verified": False, "issues": ["duplicate_evidence_id"]}
    try:
        obj = _parse_response(raw)
    except ValueError as exc:
        return {"status": "BLOCKED", "verified": False, "issues": [str(exc)]}
    issues = []
    published = {"observations": [], "hypotheses": [], "investigations": [], "abstentions": []}
    for i, item in enumerate(obj["observations"]):
        if not isinstance(item, dict) or set(item) != {"evidence_id", "finding"}:
            issues.append("observation_schema:" + str(i)); continue
        e = by_id.get(item["evidence_id"])
        if e is None:
            issues.append("unknown_evidence:" + str(i)); continue
        # Exact match makes paraphrased, model-invented or amplified factual findings fail.
        if item["finding"] != e["finding"]:
            issues.append("finding_not_exact:" + str(i)); continue
        published["observations"].append({
            "evidence_id": item["evidence_id"], "finding": e["finding"],
            "validation_status": e["validation_status"], "usage": e["usage"]
        })
    for key in ("hypotheses", "investigations", "abstentions"):
        for i, item in enumerate(obj[key]):
            if not isinstance(item, str) or not item.strip() or len(item) > 1000:
                issues.append(key + "_invalid:" + str(i)); continue
            published[key].append({"text": item.strip(), "label":
                "UNVERIFIED_HYPOTHESIS" if key == "hypotheses" else
                "PROPOSED_INVESTIGATION_NOT_ESTABLISHED" if key == "investigations" else
                "ABSTENTION"})
    if issues:
        return {"status": "BLOCKED", "verified": False, "issues": issues}
    if not published["observations"]:
        return {"status": "ABSTAIN_NO_SUPPORTED_OBSERVATIONS", "verified": False,
                "issues": ["no_exact_supported_observation"]}
    return {"status": "PASSED_STRUCTURAL_CHECKS_HUMAN_REVIEW_REQUIRED", "verified": True,
            "issues": [], "publication": published,
            "disclaimer": "Citation/finding identity checked only. No field validation, causal proof, legal approval, or human sign-off."}
