"""HACK-016K: quantitatively describe only metrics literally present in FSDC findings.

Extract, never estimate. Values, labels and dates are source text; do not infer
coverage, trend, causal effect, uncertainty, or population exposure.
"""
import hashlib
import json
import re
from dynamic_brief import brief_data

PERCENT=re.compile(r"(?P<label>[A-Za-z][A-Za-z -]{1,45}?)\s+(?P<value>\d{1,3}(?:\.\d+)?)%")
YEAR=re.compile(r"\b(?:19|20)\d{2}\b")
BANNED_LABELS=("increase","change","trend","difference","growth","impact")

def quantify(trace):
    checked=brief_data(trace)
    metrics=[]
    for record in checked["sources"]:
        finding=record["finding"]
        if not isinstance(finding,str):continue
        for match in PERCENT.finditer(finding):
            label=match.group("label").strip(" ,;:-")
            # Extract most local clause; do not treat an impact statement as data.
            label=re.split(r"[;,]",label)[-1].strip()
            if not label or any(token in label.lower() for token in BANNED_LABELS):
                continue
            value=float(match.group("value"))
            if not 0<=value<=100:continue
            metrics.append({"evidence_id":record["evidence_id"],
                "dataset":record["dataset"],"metric":label,
                "value":value,"unit":"%",
                "verbatim":match.group(0),
                "observed_at":record["observed_at"],
                "validation_status":record["validation_status"],
                "interpretation":"DESCRIPTIVE_ONLY_NOT_CAUSAL_OR_TEMPORAL"})
    digest=hashlib.sha256(json.dumps(metrics,sort_keys=True,ensure_ascii=False,
                              separators=(",",":")).encode("utf-8")).hexdigest()
    return {"schema_version":"HACK016K.1",
       "session_id":checked["session_id"],
       "question":checked["question"],
       "evidence_sha256":checked["evidence_sha256"],
       "metrics":metrics,"metrics_sha256":digest,
       "coverage_note":"Metrics describe only the cited dataset AOI, not all of Boké.",
       "trend_available":False,"causal_impact_established":False,
       "scientific_status":"EXPLORATORY_SOURCE_EXTRACTION"}
