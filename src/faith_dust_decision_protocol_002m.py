"""TERRA-DATA-002M — Deterministic dust decision questions for real HACK-016.

Produces actionable INVESTIGATION QUESTIONS, not conclusions, PM exposure,
regulatory compliance judgments, or invented modeled impacts.
"""
from dynamic_council import plan_fingerprint

PROTOCOL=(
 {"id":"DUST-001","domain":"source_identity","question":"Quelles activites produisent les emissions PM10 et PM2.5 et quels inventaires quantifies existent par installation, piste et saison ?",
  "missing_input":"Inventaire local des emissions par source, activite et periode",
  "method":"Recueillir et auditer les flux de transport, chargement, concassage et emissions diffuses",
  "decision_test":"Choisir les sources a instrumenter et evaluer les mesures de reduction"},
 {"id":"DUST-002","domain":"baseline_and_receptors","question":"Quelles concentrations ambiantes PM10 et PM2.5 sont observees aux recepteurs communautaires et dans une zone de reference ?",
  "missing_input":"Mesures locales, metadata capteurs et coordonnees de recepteurs consenties",
  "method":"Campagne de surveillance multi-saison et controle qualite avec fond regional",
  "decision_test":"Distinguer fond atmospherique regional et differents gradients locaux"},
 {"id":"DUST-003","domain":"meteorology_and_dispersion","question":"Quelles trajectoires meteorologiques et emissions de sites sont compatibles avec un modele de dispersion valide ?",
  "missing_input":"Meteorologie representant le site, relief, hauteurs, tailles des sources et emission",
  "method":"Preparer donnees meteo et sources pour AERMOD avec incertitudes et validation des hypotheses",
  "decision_test":"Evaluer l'exposition modelisee et les hypotheses de contribution sans attribuer CAMS aux mines"},
 {"id":"DUST-004","domain":"mitigation","question":"Quelles mesures reduisent effectivement les concentrations sans deplacer les impacts sur l'eau ou les communautes ?",
  "missing_input":"Situation initiale, essais comparables et suivi des mesures de reduction",
  "method":"Comparer arrosage raisonne, stabilisation de pistes, confinement et filtration avec controle des effets secondaires",
  "decision_test":"Prioriser des interventions apres validation du suivi, des couts et de la faisabilite"}
)

def attach_protocol(plan):
    p=dict(plan)
    if "dust" not in p.get("topics",[]) or p.get("geography")!="Boké, Guinea":
        p["dust_protocol"]=[]
        return p
    if p.get("dust_context_count")!=3 or p.get("dust_aoi_concentration_admitted") is not False:
        raise ValueError("Dust context must remain modeled and not admitted as site concentration")
    p["dust_protocol"]=[dict(x) for x in PROTOCOL]
    # Rebinding the fingerprint is essential: consent covers exact investigation brief.
    import hashlib,json
    existing=p.get("regional_context",[])
    base=p.get("regional_context_sha256")
    payload={"regional_context_sha256":base,"dust_protocol":p["dust_protocol"]}
    p["scientific_protocol_sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")).hexdigest()
    return p
