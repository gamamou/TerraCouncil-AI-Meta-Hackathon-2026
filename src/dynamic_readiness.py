"""HACK-016H: offline readiness and clear blocking reasons; never leaks API keys.

Only records explicitly supplied to the server may be used. Does not infer that
other FAITH datasets are available or that a model provider is reachable.
"""
from pathlib import Path
from dynamic_council import plan_question

SUGGESTIONS=(
  "Que permettent de documenter les données d'occupation du sol à Boké ?",
  "Que savons-nous des estimations de population pour la zone étudiée à Boké ?",
  "Quelles preuves de concentrations PM10 sont disponibles pour Boké ?",
)

def inspect_readiness(records,root,meta_key_available=False,voice_key_available=False):
    root=Path(root)
    dynamic=root/"Dynamic-HACK016"
    # Count filenames only; content is read by authenticated session endpoints.
    dynamic_count=sum(1 for p in dynamic.glob("HACK016-*.json") if p.is_file())
    legacy_count=sum(1 for p in root.glob("HACK008-*.json") if p.is_file())
    examples=[]
    for question in SUGGESTIONS:
        plan=plan_question(question,records,"Boké, Guinea","mining")
        examples.append({"question":question,"status":plan["status"],
                         "source_ids":[x["evidence_id"] for x in plan["evidence"]],
                         "missing_topics":plan["missing_topics"],
                         "estimated_max_calls":plan["model_calls_planned"]})
    notices=[]
    if not meta_key_available:
        notices.append("MODEL_API_KEY absent du processus serveur. Prévisualisation disponible; aucun débat Meta réel ne peut démarrer.")
    if not dynamic_count:
        notices.append("Aucune session HACK-016 enregistrée dans le dossier actif. Les anciennes sessions HACK-008 ne sont pas automatiquement des sessions dynamiques.")
    notices.append("La présence d'une clé ne garantit pas l'accès au fournisseur ni la facturation autorisée.")
    notices.append("L'accès aux données est limité aux observations FSDC chargées localement.")
    return {"schema_version":"HACK016H.1",
      "meta_key_available":bool(meta_key_available),
      "voice_key_available":bool(voice_key_available),
      "dynamic_session_count":dynamic_count,"legacy_session_count":legacy_count,
      "session_directory":str(dynamic.resolve()),
      "examples":examples,"notices":notices,
      "external_calls":0}
