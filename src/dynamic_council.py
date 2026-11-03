"""HACK-016 — Deterministic, inspectable question-based FAITH council planner.

Strictly local, zero model calls. Never invent or download evidence.
A production FSDC connector can later supply richer verified records.
"""
import hashlib
import json
import re
from pathlib import Path

from registry import load_registry
from verification import gate_evidence, evidence_hash
import hashlib

# Bilingual keywords are discovery hints, NOT scientific assertions.
TOPICS={
  "dust":("poussièr","poussiere","pm10","pm2.5","qualité de l'air","qualite de l'air","dust","air quality","aermod"),
  "water":("eau","hydrolog","inond","water","flood","bassin","rivière","riviere"),
  "population":("population","communaut","village","habitant","école","ecole","community","school","people"),
  "land":("occupation du sol","terres","forêt","foret","culture","sols","agricol","mangrove","land cover","forest","cropland"),
  "mining":("mine","minier","minerai","bauxite","extraction","simandou","mining","graphite","red mud"),
  "logistics":("transport","rail","corridor","route","logisti","road","truck","camion","port"),
  "energy":("énergie","energie","électri","electri","renewable","energy","smr","power"),
  "finance":("coût","cout","financ","investiss","économ","econom","cost","revenue","profit","budget"),
  "governance":("permis","réglement","reglement","gouvernance","conform","permit","compliance","policy"),
  "climate":("climat","températ","temperat","pluie","sécher","secher","climate","rainfall","drought"),
}
AGENT_TOPIC={
 "mining_industry":("mining","logistics"),
 "environment_climate":("dust","water","land","climate"),
 "agriculture_land":("land","water"),
 "energy_infrastructure":("energy","logistics"),
 "communities":("population","dust","water","land"),
 "economics_finance":("finance",),
 "governance_compliance":("governance",),
}
SECTOR_TOPIC={
 "mining":("mining","dust","logistics"),
 "agriculture":("land","water"),
 "environment":("dust","water","climate"),
 "energy":("energy",),
 "simandou":("logistics","mining"),
 "critical_minerals":("mining",),
 "digital_twins":(),
}
# Grounded source keywords only. They cannot establish that a scientific measure exists.
DATA_HINTS={
 "dust":("dust","aermod","pm10","pm2.5","particulate","air quality","poussi"),
 "water":("water","hydrolog","flood","eau"),
 "population":("worldpop","population","demograph"),
 "land":("worldcover","land cover","cover shares","cropland","mangrove","forest"),
 "mining":("mine","mining","permit","bauxite"),
 "logistics":("transport","rail","road","route","traffic"),
 "energy":("energy","power","énergie"),
 "finance":("cost","finance","revenue","economic"),
 "governance":("permit","compliance","regulation","governance"),
 "climate":("climate","era5","chirps","rainfall","wind","vent"),
}

def _matched(text,words):
    return any(w in text for w in words)

def classify(question,sector=None):
    if not isinstance(question,str) or not question.strip() or len(question)>1800:
        raise ValueError("Question must have between 1 and 1800 characters")
    norm=question.casefold()
    topics=[k for k,words in TOPICS.items() if _matched(norm,words)]
    registry=load_registry()
    sectors={x["id"] for x in registry["sectors"]}
    if sector is not None and sector not in sectors:
        raise ValueError("Unknown FAITH sector")
    if sector is None:
        # Stable, transparent classification; never claim AI comprehension.
        values={s:sum(k in topics for k in linked) for s,linked in SECTOR_TOPIC.items()}
        best=max(values.values())
        sector=next((s for s in ("mining","agriculture","environment","energy","simandou","critical_minerals","digital_twins")
                     if values[s]==best and best>0),None)
    return {"sector":sector,"topics":topics,
            "classification":"RULE_BASED_PRELIMINARY"}

def plan_fingerprint(plan):
    fields={key:plan.get(key) for key in ("question","geography","sector","topics","proposers","evidence_sha256","missing_topics","regional_context_sha256","scientific_protocol_sha256")}
    return hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()

def plan_question(question,records,geography="Boké, Guinea",sector=None,max_proposers=4):
    if not isinstance(geography,str) or not geography.strip():
        raise ValueError("Explicit FSDC geography is required")
    if not isinstance(max_proposers,int) or not 1<=max_proposers<=4:
        raise ValueError("At most four proposing agents")
    decision=classify(question,sector)
    if decision["sector"] is None:
        return {"status":"ABSTAIN_UNRESOLVED_DOMAIN","question":question,
                "geography":geography,"topics":decision["topics"],"proposers":[],
                "evidence":[],"missing_topics":[],"model_calls_planned":0}
    registry=load_registry()
    sector=decision["sector"]
    if not decision["topics"]:
        return {"schema_version":"HACK016.1","status":"ABSTAIN_UNRECOGNIZED_QUESTION_TOPICS",
                "question":question,"geography":geography,"sector":sector,
                "topics":[],"proposers":[],"evidence":[],
                "evidence_sha256":evidence_hash([]),"missing_topics":[],
                "model_calls_planned":0,"rejected":[],"limitations":[
                "Question topic was not recognized; no unrelated evidence will be substituted."]}
    gate=gate_evidence(records,sector,geography)
    # For this strictly bounded PoC, zero evidence => ABSTAIN; no API call.
    available=[]
    for e in gate["evidence"]:
        corpus=(" ".join([e["dataset"],e["finding"],e["method"]])).casefold()
        supported=[topic for topic in decision["topics"] if _matched(corpus,DATA_HINTS[topic])]
        if supported:
            available.append(e)
    # Where topics are recognized but the local registry lacks matching source
    # data, do not silently substitute unrelated evidence.
    supported_topics={topic for e in available for topic in decision["topics"]
       if _matched((" ".join([e["dataset"],e["finding"],e["method"]])).casefold(),DATA_HINTS[topic])}
    missing=[topic for topic in decision["topics"] if topic not in supported_topics]
    # Filter agent registry by topical relevance first and then original registry ordering.
    candidates=[a for a in registry["agents"] if a["id"]!="scientific_critic" and sector in a["sectors"]]
    ranked=sorted(candidates,key=lambda a:(-sum(t in decision["topics"] for t in AGENT_TOPIC.get(a["id"],())),registry["agents"].index(a)))
    proposers=[x["id"] for x in ranked[:max_proposers]]
    digest=evidence_hash(available)
    status=("READY_EXPLORATORY_MISSING_TOPICS" if available and missing else
            "READY_EXPLORATORY" if available else "ABSTAIN_NO_QUESTION_RELEVANT_EVIDENCE")
    result={"schema_version":"HACK016.1","status":status,"question":question,
            "geography":geography,"sector":sector,"topics":decision["topics"],
            "classification":decision["classification"],
            "proposers":proposers,"critic":"scientific_critic",
            "evidence":available,"evidence_sha256":digest,
            "missing_topics":missing,"rejected":gate["rejected"],
            "model_calls_planned":len(proposers)+2 if available else 0,
            "limitations":["Selection is keyword-based, not a complete semantic search.",
               "Available records are only from supplied local FSDC data; no external retrieval.",
               "Missing domains/measurements are not inferred from related sources.",
               "Screened evidence is not field-validated."]}
    result["plan_sha256"]=plan_fingerprint(result)
    return result
