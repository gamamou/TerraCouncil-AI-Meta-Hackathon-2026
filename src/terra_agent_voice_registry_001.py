"""Voice identities are attached to scientific roles, never model vendors.

A six-stage debate does not imply six domain experts. Fail closed until every
actual role has an explicitly assigned distinct ElevenLabs voice ID.
"""
import json,os
from pathlib import Path

def voice_map_for_roles(roles, mapping):
    if not isinstance(mapping,dict) or not isinstance(roles,list) or not roles:
        raise ValueError("Invalid role voice mapping")
    required=set(roles)
    if any(not isinstance(r,str) or not r for r in roles):
        raise ValueError("Invalid scientific role")
    if not required.issubset(mapping):
        raise ValueError("Missing voice IDs for roles: "+", ".join(sorted(required-set(mapping))))
    selected={r:mapping[r] for r in required}
    if any(not isinstance(v,str) or not v.strip() for v in selected.values()):
        raise ValueError("Empty voice ID")
    if len(set(selected.values()))!=len(selected):
        raise ValueError("Each distinct role must have a distinct voice")
    return selected

def load_voice_map(path,roles):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    return voice_map_for_roles(roles,data)

def voice_mapping_template(roles):
    return {r:"" for r in dict.fromkeys(roles)}
