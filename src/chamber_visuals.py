"""HACK-013: Evidence-linked visual cues for the real four-stage Boké chamber.

No model calls. All material comes from a locally verified HACK-008 run.
Visuals are labels and verified existing values; not inferred impact maps.
"""
from export_decision_pdf import validate_session
import re

ROLES=(
    ("Mining & Industry","Analyse minière"),
    ("Environment & Climate","Analyse environnementale"),
    ("Scientific Critic","Critique méthodologique"),
    ("Final Synthesis","Délibération révisée"),
)
TOPICS=(
    ("Population estimée","WorldPop"),
    ("Occupation du sol","WorldCover"),
)
def visual_cues(trace,evidence):
    verified=validate_session(trace,evidence)
    sources=verified["evidence"]
    pop=next((x for x in sources if "WorldPop" in x["dataset"]),None)
    cover=next((x for x in sources if "WorldCover" in x["dataset"]),None)
    if not pop or not cover:
        raise ValueError("The Boké chamber needs both verified source records")
    # Use only numeric values literally found in original checked FSDC findings.
    pop_match=re.search(r"(?<!\w)(\d{4,}(?:\.\d+)?)\s*;",pop["finding"])
    shares=list(re.finditer(r"(Tree cover|Cropland|Built-up|Permanent water|Mangroves)\s+(\d+(?:\.\d+)?)%",cover["finding"]))
    land_shares=[{"label":x.group(1),"value":float(x.group(2))} for x in shares]
    for v in land_shares:
        if not 0<=v["value"]<=100:
            raise ValueError("Bad land-cover percentage")
    profiles=[
        ("Données de référence","Lire l'estimation spatiale et identifier ce qui nécessite une enquête sur le terrain.",
         ["population","occupation_du_sol"]),
        ("Sensibilité environnementale","Discuter les limites de la couverture du sol et les besoins d'études eau et biodiversité.",
         ["occupation_du_sol","limitations"]),
        ("Contre-expertise","Examiner le périmètre rectangulaire, les dates et les incertitudes, sans présumer un impact.",
         ["limitations","occupation_du_sol"]),
        ("Décision prudente","Présenter les investigations nécessaires et les décisions qui doivent rester ouvertes.",
         ["limitations","population","occupation_du_sol"])
    ]
    cues=[]
    for i,step in enumerate(verified["steps"]):
        heading,focus,kinds=profiles[i]
        publication=step["checked_publication"]
        cues.append({
            "turn":i+1,
            "title":ROLES[i][1],
            "role":step["role"],
            "model":step["model"],
            "heading":heading,
            "visual_summary":focus,
            "focus":kinds,
            "source_ids":[e["evidence_id"] for e in sources],
            "investigations":[x["text"] for x in publication["investigations"][:3]],
            "abstentions":[x["text"] for x in publication["abstentions"][:2]],
            "human_review_required":True
        })
    return {
        "session_id":verified["run_id"],
        "evidence_sha256":verified["sha256"],
        "status":"EXPLORATORY_SOURCE_CHECKED_NOT_FIELD_VALIDATED",
        "population":{
            "value":float(pop_match.group(1)) if pop_match else None,
            "unit":"WorldPop raster cell sum within rectangle, not affected population",
            "source_id":pop["evidence_id"],
        },
        "landcover":{"year":"2021","classes":land_shares,
                     "source_id":cover["evidence_id"],
                     "warning":"Not an estimate of change or mine-caused impact"},
        "cues":cues,
        "model_calls":0
    }
