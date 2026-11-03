"""TERRA-VOICE-002B — private, atomic approval storage. No network or provider calls."""
import json
import os
from pathlib import Path
import re
import tempfile
from terra_voice_approval_002 import approve, voice_payload

RUN_ID = re.compile(r"^HACK016-[A-Za-z0-9_-]{10,80}$")

def _approved_path(out_dir, run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid session identifier")
    return Path(out_dir) / "Dynamic-HACK016" / "voice-approvals" / (run_id + ".json")

def save_approval(out_dir, trace, submitted, reviewer):
    """Only one approved record per session. Never silently overwrite a review."""
    run_id = trace.get("run_id")
    path = _approved_path(out_dir, run_id)
    record = approve(trace, submitted, reviewer)
    if record["session_id"] != run_id:
        raise ValueError("Approval/session mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents races and overwrites. Restrictive file permissions
    # are applied during creation; no temporary plaintext copy is left behind.
    data = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(str(path), flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return {"session_id": run_id, "approval_sha256": record["approval_sha256"],
            "status": record["status"], "stored": True}

def load_verified_approval(out_dir, trace, voice_spark, voice_wonder):
    """Re-check exact approval, source, stage IDs and edit checksum before TTS preflight."""
    run_id = trace.get("run_id")
    path = _approved_path(out_dir, run_id)
    if not path.is_file() or path.stat().st_size > 25000:
        raise ValueError("Missing or oversized approval")
    record = json.loads(path.read_text(encoding="utf-8"))
    return voice_payload(trace, record, voice_spark, voice_wonder)

def read_approval_status(out_dir, run_id):
    path = _approved_path(out_dir, run_id)
    return {"session_id": run_id, "state":
            "APPROVED_FOR_VOICE_PREPARATION" if path.is_file() else "PENDING_HUMAN_REVIEW",
            "audio_generated": False}
