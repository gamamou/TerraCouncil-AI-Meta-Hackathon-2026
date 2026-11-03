"""HACK-016E: independent deterministic fidelity audit of dynamic oral turns.

This does NOT prove semantic equivalence, scientific correctness or language.
Only exact source extraction can pass unattended. Never auto-authorizes TTS.
"""
import hashlib
import json
import re
from dynamic_narration import build_dynamic_oral
from scientific_pronunciation import spoken_pronunciation

ENGLISH=re.compile(r"\b(the|should|with|evidence|missing|investigate|cannot|further|recommend|survey)\b",re.I)
TECHNICAL=re.compile(r"[<>{}#@\\|*_]|https?://|www\.",re.I)
LIMIT=2000

def _hash(value):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def verify_oral(trace,proposal=None):
    baseline=build_dynamic_oral(trace)
    proposal=baseline if proposal is None else proposal
    if not isinstance(proposal,dict):
        raise ValueError("Narration must be an object")
    if proposal.get("session_id")!=baseline["session_id"]:
        raise ValueError("Session mismatch")
    if proposal.get("evidence_sha256")!=baseline["evidence_sha256"]:
        raise ValueError("Scientific evidence mismatch")
    if proposal.get("type")!="EDITORIAL_RECONSTRUCTION_NOT_VERBATIM":
        raise ValueError("Editorial provenance changed")
    originals=baseline["turns"]
    current=proposal.get("turns")
    if not isinstance(current,list) or len(current)!=len(originals):
        raise ValueError("One narrated intervention per verified stage is required")
    findings=[]
    for idx,(expected,actual) in enumerate(zip(originals,current),1):
        if not isinstance(actual,dict):
            raise ValueError("Invalid turn")
        for field in ("turn","speaker","source_model","source_stage_index",
                      "source_evidence_ids","source_investigation","source_abstention"):
            if actual.get(field)!=expected.get(field):
                raise ValueError("Protected evidence attribution altered: "+field)
        voice=actual.get("text_to_review")
        if not isinstance(voice,str) or not voice.strip():
            raise ValueError("Empty oral text")
        reasons=[]
        # Only the deterministic exact extraction is mechanically auditable.
        if voice!=expected["text_to_review"]:
            reasons.append("EDITORIAL_CHANGE_NEEDS_SEMANTIC_REVIEW")
        try:
            spoken_pronunciation(voice)
        except ValueError as issue:
            reasons.append("PRONUNCIATION_REVIEW_REQUIRED: "+str(issue))
        if len(voice)>1100:
            reasons.append("SPEAKER_TEXT_TOO_LONG")
        findings.append({"turn":idx,"role":expected["speaker"],
                         "exact_source_extraction":voice==expected["text_to_review"],
                         "issues":reasons,"classification":"REVIEW_REQUIRED" if reasons else "EXTRACTIVE_PASS"})
    if sum(len(t["text_to_review"]) for t in current)>LIMIT:
        findings.append({"issue":"SINGLE_CALL_CHARACTER_LIMIT","classification":"REVIEW_REQUIRED"})
    issues=sum(bool(x.get("issues") or x.get("issue")) for x in findings)
    return {"schema_version":"HACK016E.1","session_id":baseline["session_id"],
            "source_fingerprint":baseline["evidence_sha256"],
            "script_sha256":_hash(current),
            "status":"REVIEW_REQUIRED" if issues else "EXACT_EXTRACTION_CHECK_PASSED",
            "checks":findings,"manual_review_items":issues,
            "tts_authorized":False,"new_ai_calls":0,
            "disclaimer":"Exact source matching is not semantic, field, medical or scientific validation. Paid voice requires separate authorization."}
