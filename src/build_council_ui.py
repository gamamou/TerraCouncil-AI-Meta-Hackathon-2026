"""HACK-007 — offline interactive replay of the actual Meta Boké debate.

No Meta API calls. Produces ONE standalone HTML file using locally saved traces.
Before rendering, rechecks all published findings with the independent verifier.
Raw model text and API credentials are never embedded.
"""
import argparse
import datetime as dt
import html
import json
from pathlib import Path
import sys
from verified_council import prepare
from verification import verify_submission

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def reconstruct(p):
    if not isinstance(p, dict):
        raise ValueError("Missing checked publication")
    return {
        "observations": [
            {"evidence_id": v["evidence_id"], "finding": v["finding"]}
            for v in p["observations"]
        ],
        "hypotheses": [v["text"] for v in p["hypotheses"]],
        "investigations": [v["text"] for v in p["investigations"]],
        "abstentions": [v["text"] for v in p["abstentions"]],
    }

def assemble(evidence, spark, wonder, revision):
    if spark.get("status") != "FIRST_META_RESPONSE_PASSED_STRUCTURAL_GATES":
        raise ValueError("First Spark response not structurally accepted")
    for name, trace, stage, model in (
        ("Wonder", wonder, "critique", "muse-wonder-1.0"),
        ("Spark revision", revision, "revision", "muse-spark-1.3"),
    ):
        if trace.get("status") != "PASSED_STRUCTURAL_GATES" or trace.get("stage") != stage or trace.get("model") != model:
            raise ValueError(name + " trace is incomplete or unverified")
    if spark.get("model") != "muse-spark-1.3":
        raise ValueError("Unexpected initial Spark model")
    q = spark.get("question")
    if not isinstance(q, str) or not q.strip():
        raise ValueError("Missing original question")
    job = prepare(q, evidence)
    gate = job["gate"]
    if gate["status"] not in ("EVIDENCE_READY_EXPLORATORY", "EVIDENCE_READY"):
        raise ValueError("No usable evidence")
    fingerprint = gate["evidence_sha256"]
    for label, trace in (("Spark", spark), ("Wonder", wonder), ("Revision", revision)):
        if trace.get("evidence_sha256") != fingerprint or trace.get("question") != q:
            raise ValueError(label + " source fingerprint or question mismatch")
        verified = verify_submission(reconstruct(trace.get("checked_publication")),
                                     gate["evidence"], fingerprint)
        if not verified["verified"]:
            raise ValueError(label + " fails independent re-verification: " + repr(verified["issues"]))
    # No invented stakeholder participation: one Spark perspective, Wonder critic, Spark revision.
    sessions = [
        {"name": "Muse Spark", "role": "Position initiale : " + str(spark.get("agent_id", "perspective analytique")),
         "model": "muse-spark-1.3", "verified": "Structural checks passed",
         "content": spark["checked_publication"]},
        {"name": "Muse Wonder", "role": "Critique contradictoire", "model": "muse-wonder-1.0",
         "verified": "Structural checks passed", "content": wonder["checked_publication"]},
        {"name": "Muse Spark", "role": "Synthèse révisée", "model": "muse-spark-1.3",
         "verified": "Structural checks passed", "content": revision["checked_publication"]},
    ]
    evidence_public = [{k: e[k] for k in ("evidence_id", "dataset", "source", "observed_at",
                         "geography", "method", "license", "validation_status", "finding", "usage")}
                       for e in gate["evidence"]]
    return {
        "title": "TerraCouncil — Boké Scientific Council", "question": q,
        "geography": job["geography"],
        "status": gate["status"], "evidence_sha256": fingerprint,
        "evidence": evidence_public, "sessions": sessions,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "disclaimer": "Scientific screening only — NOT_FIELD_VALIDATED. Structural checks do not prove scientific correctness or causality. Human scientific review required.",
        "model_calls_in_replay": 0
    }

CSS = r"""
:root{color-scheme:dark;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;background:#0b1220;color:#e7eef8}
*{box-sizing:border-box}body{margin:0}header{padding:18px 32px;border-bottom:1px solid #263548;background:#0e192b}
h1{font-size:23px;margin:6px 0}h2{font-size:18px;margin:0 0 12px}h3{font-size:15px;margin:18px 0 8px}
p{line-height:1.6}small,.muted{color:#a8b6c9}.flag{background:#2f2418;color:#ffd59a;border-radius:8px;padding:6px 9px;display:inline-block;font-size:12px}
main{max-width:1380px;margin:auto;padding:24px;display:grid;grid-template-columns:320px minmax(0,1fr);gap:18px}
section,.panel{background:#121f31;border:1px solid #29394e;border-radius:15px;padding:20px;min-width:0}
aside{display:flex;flex-direction:column;gap:16px}.panel{padding:15px}.brand{letter-spacing:.13em;font-size:11px;font-weight:800;color:#a6cadb}
.rows{display:flex;flex-wrap:wrap;gap:9px}.pill{display:inline-block;border:1px solid #416079;padding:7px 10px;border-radius:99px;font-size:12px;color:#d4e5f2}
button{border:1px solid #3d5873;color:#eaf3fa;background:#1c304a;padding:10px 14px;border-radius:9px;cursor:pointer;font:inherit;text-align:left}
button:hover,button.active{background:#24516b;border-color:#77afc2}button:focus-visible{outline:2px solid #a0e3f1;outline-offset:2px}
.nav{width:100%;display:block;margin:8px 0}.card{padding:12px 14px;border:1px solid #35465b;border-radius:9px;margin:9px 0;background:#18283c;line-height:1.55;overflow-wrap:anywhere}
.tag{font-size:11px;text-transform:uppercase;color:#a8c5d9;letter-spacing:.07em;margin-bottom:5px}
.sources{font-size:12px;color:#adc4d8}.columns{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
.gridHeading{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
input,textarea{width:100%;padding:12px;background:#091523;color:#f5faff;border:1px solid #465c75;border-radius:9px;font:inherit}
textarea{min-height:90px}.notice{border-left:3px solid #d7a54c;padding:10px 12px;background:#2c271d;color:#f5dca9;border-radius:6px;font-size:13px}
.hidden{display:none}.divider{height:1px;background:#35465b;margin:16px 0}.sourceTitle{font-weight:700}
@media(max-width:850px){main{grid-template-columns:1fr;padding:12px}header{padding:16px}aside{order:2}}
@media print{body{background:white;color:black}header{background:white;color:black}main{display:block}.panel,section{background:white;color:black;border-color:#999}button,textarea{display:none}.hidden{display:block}.card{background:#fff;color:#000}}
"""
JS = r"""
(function(){
 const data = JSON.parse(document.getElementById("terracouncil-data").textContent);
 const select = id => document.getElementById(id);
 function add(tag, cls, txt, parent){
   const n=document.createElement(tag);
   if(cls)n.className=cls;
   if(txt !== undefined && txt !== null)n.textContent=String(txt);
   parent.appendChild(n);return n;
 }
 function cards(node, items, category){
   const h=add("h3","",category,node);
   if(!items.length) add("p","muted","Aucun élément fourni pour cette catégorie.",node);
   for(const item of items){
     const x=add("div","card",null,node);
     if(typeof item==="string")add("p","",item,x);
     else {
       if(item.label) add("div","tag",item.label,x);
       add("p","",item.finding||item.text||"",x);
       if(item.evidence_id) add("small","sources","Source : "+item.evidence_id+" · "+item.validation_status+" · "+item.usage,x);
     }
   }
 }
 function show(i){
   const s=data.sessions[i], host=select("stage-content");
   host.replaceChildren();
   add("h2","",s.name+" — "+s.role,host);
   add("small","muted",s.model+" · "+s.verified+" · Replay : aucun appel Meta",host);
   cards(host,s.content.observations,"Observations documentées");
   cards(host,s.content.hypotheses,"Hypothèses non vérifiées");
   cards(host,s.content.investigations,"Investigations proposées");
   cards(host,s.content.abstentions,"Abstentions scientifiques");
   for(let j=0;j<data.sessions.length;j++)select("stage-"+j).classList.toggle("active",i===j);
 }
 data.sessions.forEach((s,i)=>{
   const b=add("button","nav",String(i+1)+". "+s.name+" — "+s.role,select("stages"));
   b.id="stage-"+i;b.onclick=()=>show(i);
 });
 for(const e of data.evidence){
   const c=add("div","card",null,select("evidence"));
   add("div","sourceTitle",e.evidence_id+" · "+e.dataset,c);
   add("p","",e.finding,c);
   add("small","sources",e.validation_status+" · "+e.observed_at+" · "+e.geography,c);
   add("p","muted","Méthode : "+e.method+" | Licence : "+e.license,c);
 }
 select("question").textContent=data.question;
 select("hash").textContent=data.evidence_sha256;
 select("status").textContent=data.status;
 select("ask").addEventListener("click",()=>{
   const q=select("new-question").value.trim(), target=select("ask-result");
   target.replaceChildren();
   if(!q){add("p","muted","Saisissez une question.",target);return;}
   add("div","notice","Nouvelle question non exécutée. Cette page est une archive locale : elle ne lance aucun modèle Meta. Pour répondre, utilisez une nouvelle session vérifiée avec preuves FSDC et autorisation API.",target);
   add("p","muted","Question préparée : "+q,target);
 });
 select("evidence-toggle").onclick=()=>select("evidence-section").classList.toggle("hidden");
 show(0);
})();
"""
def make_html(data):
    # JSON script block cannot be broken out of by finding </script> in untrusted text.
    safe = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TerraCouncil — Scientific Council</title><style>{CSS}</style></head>
<body><header><div class="brand">SUSTAINAFRICA / FAITH / FSDC</div>
<h1>TerraCouncil AI · Scientific Council</h1><span class="flag">EXPLORATORY · NOT FIELD VALIDATED</span></header>
<main><aside>
<div class="panel"><div class="brand">CAS PILOTE</div><h2>Boké · Guinée</h2><p class="muted">Relecture des trois interventions réelles sauvegardées. Le débat ne déclenche aucun nouvel appel API.</p><div class="rows"><span class="pill">Mining</span><span class="pill">Environment</span><span class="pill">Agriculture</span><span class="pill">Energy</span></div><p class="muted">Ces perspectives sont configurées ; seules les interventions enregistrées sont affichées comme exécutées.</p></div>
<div class="panel"><h2>Délibération</h2><div id="stages"></div></div>
<div class="panel"><h2>Traçabilité</h2><small id="status"></small><p class="muted">Empreinte des preuves :</p><small id="hash" style="overflow-wrap:anywhere"></small></div>
</aside><div>
<section><div class="brand">QUESTION DÉCISIONNELLE</div><h2 id="question"></h2>
<div class="notice">Ce démonstrateur est une relecture scientifique. Les observations sont préliminaires ; aucune exposition, causalité ou autorisation minière n'est établie.</div></section>
<section style="margin-top:16px"><div class="gridHeading"><h2>Conseil multi-agents · Débat vérifié structurellement</h2><span class="pill">Spark → Wonder → Spark</span></div><div id="stage-content"></div></section>
<section style="margin-top:16px"><div class="gridHeading"><h2>Preuves FSDC</h2><button id="evidence-toggle" type="button">Afficher / masquer</button></div><div id="evidence-section"><div id="evidence"></div></div></section>
<section style="margin-top:16px"><h2>Poser une nouvelle question</h2><p class="muted">Saisie libre disponible ici ; la génération d'une nouvelle réponse nécessite un backend Meta sécurisé et une nouvelle session de preuves. Aucune réponse n'est simulée.</p><textarea id="new-question" aria-label="Nouvelle question" placeholder="Quelle décision souhaitez-vous examiner ?"></textarea>
<p><button type="button" id="ask">Préparer la question</button></p><div id="ask-result" role="status"></div></section>
<section style="margin-top:16px"><h2>Limites et revue humaine</h2><p>Les citations et observations ont été contrôlées par correspondance exacte avec les preuves enregistrées. Ces contrôles ne vérifient pas la vérité scientifique des sources, la causalité ni l'exhaustivité de la délibération.</p><p><strong>Revue scientifique humaine obligatoire avant toute diffusion comme recommandation validée.</strong></p></section>
</div></main>
<script type="application/json" id="terracouncil-data">{safe}</script>
<script>{JS}</script></body></html>"""

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--evidence", required=True)
    a.add_argument("--spark-trace", required=True)
    a.add_argument("--wonder-trace", required=True)
    a.add_argument("--revision-trace", required=True)
    a.add_argument("--out", required=True)
    args=a.parse_args()
    out=Path(args.out)
    if out.exists():
        raise ValueError("Output already exists; use a new filename")
    data=assemble(read(args.evidence), read(args.spark_trace),
                  read(args.wonder_trace), read(args.revision_trace))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(make_html(data), encoding="utf-8")
    print("STATUS: OFFLINE_COUNCIL_READY")
    print("STAGES:",len(data["sessions"]))
    print("EVIDENCE:",len(data["evidence"]))
    print("META_CALLS: 0")
    print("OUTPUT:",out)

if __name__=="__main__":
    try:main()
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        print("STOP:",str(exc),file=sys.stderr)
        sys.exit(2)
