"""HACK-016G — deterministic scientific-term pronunciation, no LLM paraphrase.

Only exact, reviewable token-level rendering. Never changes scientific numbers,
measurement values, comparisons, temporal facts or source assertions.
An unknown number, formula, English fragment or unsafe symbol fails closed.
"""
import re
from terra_french_numbers_001 import expand_unambiguous_numbers
from terra_identifier_speech_001 import normalize_identifiers

# Spellings are conventional pronunciation expansions, not new measurements.
TOKEN_RULES=(
    (re.compile(r"(?<!\w)PM\s*2[.,]5(?!\w)",re.I),"P M deux virgule cinq","PM2.5"),
    (re.compile(r"(?<!\w)PM\s*10(?!\w)",re.I),"P M dix","PM10"),
    (re.compile(r"(?<!\w)AERMOD(?!\w)",re.I),"A E R M O D","AERMOD"),
    (re.compile(r"(?<!\w)FSDC(?!\w)",re.I),"F S D C","FSDC"),
    (re.compile(r"(?<!\w)ESG(?!\w)",re.I),"E S G","ESG"),
)
UNSAFE=re.compile(r"[<>{}#@\\|*_]|https?://|www\.",re.I)
ENGLISH=re.compile(r"\b(the|should|with|without|evidence|missing|investigate|cannot|further|recommend|survey)\b",re.I)
NUMBER=re.compile(r"\d")
MAX_TURN=1100
MAX_SPOKEN_TURN=2000

def spoken_pronunciation(text):
    if not isinstance(text,str) or not text.strip():
        raise ValueError("Empty narrated text")
    if len(text)>MAX_TURN:
        raise ValueError("Excessive turn size")
    text, identifier_audit = normalize_identifiers(text)
    if UNSAFE.search(text):
        raise ValueError("Unsupported technical symbols")
    if ENGLISH.search(text):
        raise ValueError("Possible English source speech needs independent review")
    current=text
    applied=list(identifier_audit)
    for pattern,replacement,source in TOKEN_RULES:
        current,count=pattern.subn(replacement,current)
        if count:
            applied.append({"original":source,"spoken":replacement,"occurrences":count})
    if NUMBER.search(current):
        current=expand_unambiguous_numbers(current)
        applied.append({"original":"NUMERIC_TOKENS","spoken":"DETERMINISTIC_FRENCH","occurrences":1})
    if NUMBER.search(current):
        raise ValueError("Unresolved scientific numerical token")
    if len(current)>MAX_SPOKEN_TURN:
        raise ValueError("Oral expansion exceeds length limit")
    return {"spoken_text":current,"normalizations":applied,"method":"WHITELISTED_LITERAL_PRONUNCIATION"}

def spoken_storyboard(draft):
    if not isinstance(draft,dict) or not isinstance(draft.get("turns"),list):
        raise ValueError("Malformed source-bound draft")
    items=[]
    for turn in draft["turns"]:
        view=spoken_pronunciation(turn["text_to_review"])
        items.append({"turn":turn["turn"],"speaker":turn["speaker"],
          "source_text":turn["text_to_review"],"spoken_text":view["spoken_text"],
          "normalizations":view["normalizations"]})
    if sum(len(x["spoken_text"]) for x in items)>2000:
        raise ValueError("Dialogue exceeds single-call voice budget")
    return items
