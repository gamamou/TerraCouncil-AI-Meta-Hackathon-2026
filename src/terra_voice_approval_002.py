"""TERRA-VOICE-002: source-bound approval gate. No network calls or secret handling.

An approver must review each edited intervention against the full original.
This record authorizes preparation only; sending audio requires a *separate*
time-of-action sharing and billing confirmation in the server.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from terra_voice_editorial_001 import editorial_worksheet

SCHEMA = "TERRA_VOICE_002_APPROVAL"
MAX_TURN_CHARS = 1800
BLOCKED = re.compile(r"[<>{}#@\\|*_]|https?://|www\.", re.I)
ENGLISH = re.compile(r"\b(the|should|with|without|evidence|missing|investigate|cannot|further|recommend|survey)\b", re.I)

def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def prepare_review(trace):
    ws = editorial_worksheet(trace)
    return {
        "schema": SCHEMA,
        "session_id": ws["session_id"],
        "evidence_sha256": ws["evidence_sha256"],
        "source_script_sha256": ws["source_script_sha256"],
        "worksheet_sha256": ws["worksheet_sha256"],
        "turns": [{
            "turn": t["turn"], "source_model": t["source_model"],
            "source_stage_index": t["source_stage_index"],
            "source_evidence_ids": t["source_evidence_ids"],
            "original_sha256": digest(t["original_full_text"]),
            "suggested_extract": t["suggested_extract"],
            "editorial_flags": t["editorial_flags"],
            "approved_text": "",
            "reviewed_against_original": False,
            "semantic_fidelity_confirmed": False,
            "pronunciation_checked": False
        } for t in ws["turns"]],
        "reviewer": "", "approved_at": "",
        "review_statement": "",
        "approval_sha256": "",
        "status": "PENDING_HUMAN_REVIEW",
        "tts_authorized": False
    }

def approve(trace, submitted, reviewer, *, approved_at=None):
    """Fail closed: all six (or 3–6) turns individually reviewed.

    Never trusts editable source hashes, IDs or self-reported approval status.
    The reviewed payload is copied only after recomputing the original worksheet.
    """
    expected = prepare_review(trace)
    if not isinstance(submitted, dict) or not isinstance(submitted.get("turns"), list):
        raise ValueError("Missing editorial review")
    if any(submitted.get(k) != expected[k] for k in
           ("session_id", "evidence_sha256", "source_script_sha256", "worksheet_sha256")):
        raise ValueError("Source evidence/script identity changed")
    if len(submitted["turns"]) != len(expected["turns"]):
        raise ValueError("Missing or extra interventions")
    if not isinstance(reviewer, str) or len(reviewer.strip()) < 3 or len(reviewer) > 120:
        raise ValueError("Identified human reviewer required")
    approved = []
    for orig, edit in zip(expected["turns"], submitted["turns"]):
        for key in ("turn", "source_model", "source_stage_index",
                    "source_evidence_ids", "original_sha256"):
            if edit.get(key) != orig[key]:
                raise ValueError("Source association or sequence modified")
        phrase = edit.get("approved_text")
        if not isinstance(phrase, str) or not phrase.strip() or phrase != phrase.strip():
            raise ValueError("Empty or unnormalized approved text")
        if len(phrase) > MAX_TURN_CHARS or BLOCKED.search(phrase) or ENGLISH.search(phrase):
            raise ValueError("Script requires pronunciation/language editing")
        if not all(edit.get(k) is True for k in
                   ("reviewed_against_original", "semantic_fidelity_confirmed",
                    "pronunciation_checked")):
            raise ValueError("Every intervention needs three human checks")
        approved.append({**orig, "approved_text": phrase,
                         "reviewed_against_original": True,
                         "semantic_fidelity_confirmed": True,
                         "pronunciation_checked": True})
    if sum(len(t["approved_text"]) for t in approved) > 2000:
        raise ValueError("Voice payload exceeds reviewed 2000-character budget")
    result = {**expected, "turns": approved, "reviewer": reviewer.strip(),
              "approved_at": approved_at or datetime.now(timezone.utc).isoformat(),
              "review_statement": "Editorial semantic review, not field scientific validation",
              "status": "APPROVED_FOR_VOICE_PREPARATION",
              "tts_authorized": False}
    result["approval_sha256"] = digest({k: v for k, v in result.items()
                                       if k != "approval_sha256"})
    return result

def voice_payload(trace, approval, voice_spark, voice_wonder):
    """Prepare six French turns; does not call ElevenLabs."""
    if not isinstance(approval, dict) or approval.get("status") != "APPROVED_FOR_VOICE_PREPARATION":
        raise ValueError("Approved script required")
    if approval.get("tts_authorized") is not False:
        raise ValueError("Approval cannot grant payment/sharing consent")
    expected = prepare_review(trace)
    if any(approval.get(k) != expected[k] for k in
           ("session_id", "evidence_sha256", "source_script_sha256", "worksheet_sha256")):
        raise ValueError("Original session changed")
    if digest({k: v for k, v in approval.items() if k != "approval_sha256"}) != approval.get("approval_sha256"):
        raise ValueError("Approval record was modified")
    if len(approval.get("turns", [])) != len(expected["turns"]):
        raise ValueError("Approval stage count mismatch")
    if not voice_spark or not voice_wonder or voice_spark == voice_wonder:
        raise ValueError("Two distinct configured voice IDs are required")
    inputs = []
    for orig, item in zip(expected["turns"], approval["turns"]):
        if any(item.get(k) != orig[k] for k in
               ("turn", "source_model", "source_stage_index",
                "source_evidence_ids", "original_sha256")):
            raise ValueError("Edited voice payload does not match evidence")
        inputs.append({"text": item["approved_text"],
                       "voice_id": voice_wonder if item["source_model"] == "muse-wonder-1.0"
                       else voice_spark})
    return {"session_id": expected["session_id"], "approval_sha256": approval["approval_sha256"],
            "evidence_sha256": expected["evidence_sha256"],
            "model_id": "eleven_v4", "language_code": "fr",
            "inputs": inputs, "requires_fresh_sharing_consent": True,
            "requires_fresh_paid_consent": True, "may_be_sent": False,
            "new_meta_calls": 0, "new_audio_calls": 0}
