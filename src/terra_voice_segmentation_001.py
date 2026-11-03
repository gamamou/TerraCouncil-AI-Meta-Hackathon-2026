"""TERRA-VOICE-SEGMENT-001: bounded, source-preserving audio batch plan.

No network calls. Never truncate or paraphrase. Segments are a plan, not permission
to spend. The existing single-attempt provider workflow must NOT be reused for
multiple segments until a separately audited multi-attempt dispatcher exists.
"""
import hashlib
import json

def segment_spoken_turns(turns, max_characters=2000, max_calls=12):
    if not isinstance(turns,list) or not 3<=len(turns)<=6:
        raise ValueError("Expected 3-6 source-verified turns")
    if not 1<=max_characters<=2000 or not 1<=max_calls<=12:
        raise ValueError("Invalid policy bounds")
    batches=[]
    for i,turn in enumerate(turns,1):
        text=turn.get("spoken_text")
        if not isinstance(text,str) or not text.strip() or text!=text.strip():
            raise ValueError("Missing or altered speech text")
        if len(text)>max_characters:
            raise ValueError("Single turn too long: explicit source-safe sentence partition needed")
        if batches and sum(len(t["text"]) for t in batches[-1]["inputs"])+len(text)<=max_characters:
            batches[-1]["inputs"].append({"turn":i,"text":text})
        else:
            batches.append({"batch":len(batches)+1,"inputs":[{"turn":i,"text":text}]})
    if len(batches)>max_calls:
        raise ValueError("Required calls exceed allowed plan")
    order=[t["turn"] for b in batches for t in b["inputs"]]
    if order!=list(range(1,len(turns)+1)):
        raise ValueError("Intervention order corrupted")
    digest=hashlib.sha256(json.dumps(batches,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return {"batches":batches,"batch_count":len(batches),"source_turn_count":len(turns),
            "total_characters":sum(len(t["spoken_text"]) for t in turns),
            "plan_sha256":digest,"tts_authorized":False,
            "requires_explicit_total_call_and_cost_consent":True,"provider_calls":0}
