"""TERRA-VOICE-001 — conservative, source-bound oral editing worksheet.

This is a local, no-cost editorial aid. It deliberately does NOT authorize TTS:
no algorithm can guarantee that a shortened scientific argument preserves its
meaning. The complete validated model position remains accessible for review.
"""
import hashlib
import json
import re
from dynamic_narration import build_dynamic_oral

TECHNICAL=re.compile(r"(?:\b[A-Z][A-Z0-9_-]{6,}\b|\d|[<>{}#@\\|*_])")

def _digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,
      separators=(",",":")).encode("utf-8")).hexdigest()

def _excerpt(text,budget):
    # Extract an unaltered complete clause/sentence, never summarize or
    # invent scientific content. The full original remains adjacent.
    clauses=re.split(r"(?<=[;.!?])\s+|(?<=;)\s*",text.strip())
    selected=[]
    for clause in clauses:
        clause=clause.strip()
        if not clause:
            continue
        if not selected and len(clause)>budget:
            return ""  # force human rewriting, never truncate mid-claim
        if len(" ".join(selected+[clause]))>budget:
            break
        selected.append(clause)
    return " ".join(selected).strip()

def editorial_worksheet(trace,limit=1800):
    draft=build_dynamic_oral(trace)  # verified evidence/source, unchanged session
    turns=draft["turns"]
    if not 3<=len(turns)<=6:
        raise ValueError("Unexpected dynamic council size")
    per_turn=min(300,max(160,(limit-80)//len(turns)))
    reviewed=[]
    for t in turns:
        proposed=_excerpt(t["text_to_review"],per_turn)
        flags=[]
        if not proposed:
            flags.append("HUMAN_REWRITE_REQUIRED_LONG_CLAUSE")
        elif proposed != t["text_to_review"]:
            flags.append("SOURCE_ARGUMENTS_OMITTED_CHECK_SEMANTIC_FIDELITY")
        if proposed and TECHNICAL.search(proposed):
            flags.append("PRONUNCIATION_AND_NUMBERS_REQUIRE_REVIEW")
        reviewed.append({
          "turn":t["turn"],"speaker":t["speaker"],"source_model":t["source_model"],
          "source_stage_index":t["source_stage_index"],
          "source_evidence_ids":t["source_evidence_ids"],
          "original_full_text":t["text_to_review"],
          "suggested_extract":proposed,
          "editorial_flags":flags,
          "human_review_approved":False})
    return {
      "schema_version":"TERRA_VOICE_001_WORKSHEET",
      "session_id":draft["session_id"],"evidence_sha256":draft["evidence_sha256"],
      "source_script_sha256":draft["script_sha256"],
      "worksheet_sha256":_digest(reviewed),
      "turns":reviewed,"review_required":True,"automatic_tts_allowed":False,
      "source_scientific_validation":"STRUCTURAL_ONLY_NOT_FIELD_VALIDATED",
      "new_model_calls":0,"new_audio_calls":0,
      "editorial_notice":"Source-verifiable excerpts, not complete spoken positions; omitted claims and pronunciation must be reviewed by a human."}
