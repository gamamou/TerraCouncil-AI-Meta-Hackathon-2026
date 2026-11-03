"""HACK-010 — Human-review-gated natural French oral storyboard.

Each intervention is an editorial summary of a verified HACK-008 session,
not verbatim model output. No auto-TTS, no synthetic research data, no API calls.
Source JSON remains unchanged. Output is a reviewable dialogue manifest.
"""
import hashlib
import json
from pathlib import Path
import re

from export_decision_pdf import validate_session

SPEAKERS=(
    ("Analyse minière", "muse-spark-1.3"),
    ("Analyse environnementale", "muse-spark-1.3"),
    ("Critique scientifique", "muse-wonder-1.0"),
    ("Synthèse et délibération", "muse-spark-1.3"),
)

def oral_storyboard(trace, evidence):
    validated=validate_session(trace,evidence)
    dataset_names=" ".join(x["dataset"] for x in validated["evidence"])
    if not ("WorldPop" in dataset_names and "WorldCover" in dataset_names):
        raise ValueError("Oral storyboard not supported for this scientific data combination")
    # Refuse to apply this editorial storyboard to another conversation merely
    # because it reuses the same datasets. Every cited investigation theme must
    # actually be present in the scientific exchange.
    corpus = " ".join(str(v.get("text", "")) for stage in validated["steps"]
                      for key in ("hypotheses", "investigations", "abstentions")
                      for v in stage["checked_publication"].get(key, [])).lower()
    required_themes = (
        ("population", "demograph"),
        ("land-cover", "land cover"),
        ("water", "hydrolog"),
        ("mangrove",),
        ("biodivers",),
        ("climate",),
        ("rectangular",),
    )
    for aliases in required_themes:
        if not any(alias in corpus for alias in aliases):
            raise ValueError("Oral storyboard needs manual source-specific drafting: " + aliases[0])
    # Carefully bounded to facts and scientifically qualified investigations
    # known to appear in this pilot. No figures invented, no investor verdict.
    scripts=[
        ("Pour commencer, nous avons une estimation spatiale de la population "
         "et une description de l'occupation du sol. Ce sont des points de départ. "
         "Ils ne permettent pas de compter les personnes touchées par une mine. "
         "Avant de décider, il faudrait mieux connaître les communautés, "
         "les villages et les conditions observées sur le terrain."),
        ("J'ajoute une réserve environnementale importante. "
         "La description de l'occupation du sol est ancienne. "
         "On ne peut pas en déduire ce qui a changé aujourd'hui. "
         "Il faut compléter nos informations par des observations récentes "
         "et des études sur l'eau, les cultures, les mangroves et la biodiversité."),
        ("Je voudrais questionner nos hypothèses. "
         "Le périmètre examiné est un rectangle d'étude. "
         "Est-il représentatif des sites sur lesquels une décision serait prise ? "
         "Les estimations spatiales doivent être confrontées à des vérifications de terrain. "
         "À ce stade, ni les effets miniers ni les risques pour les populations "
         "ne sont démontrés par ces deux sources."),
        ("La délibération conduit donc à une orientation prudente. "
         "Nous pouvons définir les enquêtes prioritaires, "
         "mais pas approuver un investissement sur la base des seules observations disponibles. "
         "Nous proposons de vérifier le périmètre, d'actualiser les données sur les communautés "
         "et les milieux naturels, puis de réaliser les études sur l'eau et le climat. "
         "Une expertise scientifique humaine devra examiner les résultats avant toute décision.")
    ]
    # Machine-recheckable source connections, with explicitly bounded editorial status.
    source_ids=[x["evidence_id"] for x in validated["evidence"]]
    items=[]
    for i,((name,model),body) in enumerate(zip(SPEAKERS,scripts)):
        if re.search(r"[<>{}_#@\\|*]|[0-9]",body):
            raise ValueError("Oral text contains code/math/symbols or digits")
        if len(body)>1200 or not body.endswith("."):
            raise ValueError("Invalid oral segment")
        items.append({"turn":i+1,"speaker":name,"source_model":model,
                      "text_to_review":body,"source_evidence_ids":source_ids,
                      "source_stage_index":i,"approved":False})
    raw=json.dumps(items,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return {
        "type":"EDITORIAL_RECONSTRUCTION_NOT_VERBATIM",
        "scientific_validation":"SCREENED_NOT_FIELD_VALIDATED",
        "recording_status":"NOT_GENERATED",
        "human_review_required":True,
        "human_review_complete":False,
        "session_id":validated["run_id"],
        "evidence_sha256":validated["sha256"],
        "script_sha256":hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "language":"fr",
        "note":"Aucun fichier audio ne peut être présenté comme une transcription littérale de la délibération.",
        "turns":items
    }

def write_review_files(manifest, directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    stem="TerraCouncil-"+manifest["session_id"]+"-oral-review"
    jsonpath=directory/(stem+".json")
    txtpath=directory/(stem+".txt")
    if jsonpath.exists() or txtpath.exists():raise ValueError("Review files exist; do not overwrite")
    jsonpath.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=[
        "TERRACOUNCIL — SCRIPT ORAL À RELIRE",
        "Reconstruction éditoriale, non verbatim. Données non validées sur le terrain.",
        "Aucune génération vocale autorisée par ce document.",
        "Session : "+manifest["session_id"],
        "",
    ]
    for item in manifest["turns"]:
        lines.extend((item["speaker"].upper(),item["text_to_review"],""))
    lines.extend(("RELECTURE HUMAINE OBLIGATOIRE : contenu, fidélité aux sources, "
                  "statut des données et éventuelle diffusion.",""))
    txtpath.write_text("\n".join(lines),encoding="utf-8")
    return jsonpath,txtpath
