"""TERRA-VOICE-AUTO-001: conservative automatic oral plan for completed councils.

No AI paraphrase and no network access. Exact source-backed utterances are
pronunciation-normalized only. Fail closed on unclear English, digits, unsafe
symbols, source audit failure, or excessive size. This module never consents
to paid speech and never approves source claims scientifically.
"""
from dynamic_voice_plan import prepare_voice

def automatic_oral_plan(trace, spark_voice, wonder_voice):
    plan = prepare_voice(trace, spark_voice, wonder_voice)
    audit = plan["pronunciation_audit"]
    if len(audit) != len(plan["turns"]):
        raise ValueError("Narration stage mismatch")
    if any(x["source_text"] != plan["turns"][i]["text_to_review"]
           for i, x in enumerate(audit)):
        raise ValueError("Narration no longer matches original council")
    if not 3 <= len(audit) <= 6:
        raise ValueError("Unexpected council size")
    return {
        **plan,
        "mode": "AUTOMATIC_SOURCE_BOUND_PRONUNCIATION",
        "approval": "NO_EDITORIAL_HUMAN_APPROVAL_REQUIRED",
        "source_validation": "STRUCTURAL_ONLY_NOT_FIELD_VALIDATED",
        "semantic_paraphrase": False,
        "approval_required_on_failure": True,
        "requires_fresh_paid_consent": True,
        "requires_fresh_sharing_consent": True,
        "automatic_provider_dispatch": False,
    }

def automatic_oral_status(trace, spark_voice, wonder_voice):
    """No script or voice IDs disclosed to web UI; reveal only readiness."""
    try:
        plan = automatic_oral_plan(trace, spark_voice, wonder_voice)
    except (ValueError, KeyError, TypeError) as error:
        return {"state": "NEEDS_REVIEW_OR_SOURCE_REPAIR",
                "reason": type(error).__name__,
                "automatically_sendable": False, "provider_calls": 0}
    return {"state": "READY_FOR_SEPARATELY_CONSENTED_VOICE",
            "turn_count": len(plan["turns"]),
            "mode": plan["mode"],
            "automatically_sendable": False,
            "provider_calls": 0,
            "script_sha256": plan["script_sha256"]}
