"""HACK-016D — report constructed from an actual dynamic council session.

No fixed Boké conclusions. No external model call. Verified session only.
"""
from pathlib import Path
from xml.sax.saxutils import escape
from verification import evidence_hash,verify_submission

def brief_data(trace):
    if trace.get("status")!="COMPLETED_STRUCTURALLY_CHECKED_HUMAN_REVIEW_REQUIRED":
        raise ValueError("Incomplete dynamic session")
    evidence=trace["evidence_snapshot"]
    if evidence_hash(evidence)!=trace["evidence_sha256"]:
        raise ValueError("Source snapshot changed")
    steps=trace["steps"]
    if len(steps)<3 or steps[-2]["role"]!="scientific_critic":
        raise ValueError("No independent critique")
    if trace["decision_support"]!=steps[-1]["checked_publication"]:
        raise ValueError("Final decision does not match source step")
    for step in steps:
        if step["status"]!="ACCEPTED_STRUCTURAL_ONLY":
            raise ValueError("Unverified intervention")
        p=step["checked_publication"]
        back={"observations":[{"evidence_id":x["evidence_id"],"finding":x["finding"]} for x in p["observations"]],
              "hypotheses":[x["text"] for x in p["hypotheses"]],
              "investigations":[x["text"] for x in p["investigations"]],
              "abstentions":[x["text"] for x in p["abstentions"]]}
        if not verify_submission(back,evidence,trace["evidence_sha256"])["verified"]:
            raise ValueError("Publication fails independent source gate")
    return {"session_id":trace["run_id"],"question":trace["question"],
            "sector":trace["sector"],"geography":trace["geography"],
            "evidence_sha256":trace["evidence_sha256"],
            "sources":evidence,"regional_context":trace.get("regional_context",[]),"steps":steps,
            "final":trace["decision_support"],
            "missing_topics":trace.get("missing_topics",[])}

def build_dynamic_pdf(trace,filename):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    data=brief_data(trace)
    from dynamic_decision_matrix import decision_matrix
    matrix=decision_matrix(trace)
    from dynamic_quantification import quantify
    quant=quantify(trace)
    output=Path(filename)
    if output.exists():raise ValueError("Report exists; do not overwrite")
    output.parent.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TC16Body",parent=styles["BodyText"],
             fontSize=9,leading=14,spaceAfter=7))
    styles.add(ParagraphStyle(name="TC16Note",parent=styles["Normal"],
             fontSize=8,leading=12,textColor=colors.HexColor("#54677B"),spaceAfter=6))
    def par(t,style="TC16Body"):
        return Paragraph(escape(str(t)),styles[style])
    content=[
      par("TERRACOUNCIL — FAITH / FSDC","Heading2"),
      par("DOSSIER DÉCISIONNEL DYNAMIQUE — HACK-016K","Heading1"),
      par("Session "+data["session_id"],"TC16Note"),
      par("Question scientifique","Heading2"),par(data["question"]),
      par("Secteur : "+data["sector"]+" | Zone : "+data["geography"],"TC16Note"),
      par("Analyse exploratoire. Source checking only, NOT field-validated. "
          "No claim of legal approval, demonstrated impact, or expert sign-off.","TC16Note"),
      par("Dimensions sans preuve pertinente","Heading2"),
      par(", ".join(data["missing_topics"]) if data["missing_topics"] else "Aucune absence détectée dans le catalogue local."),
      par("Synthèse des investigations et abstentions","Heading2")]
    for heading,key in (("Investigations prioritaires","investigations"),
                        ("Abstentions scientifiques","abstentions")):
        content.append(par(heading,"Heading3"))
        for item in data["final"][key]:
            content.append(par("• "+item["text"]))
    content.append(PageBreak())
    content.append(par("Indicateurs observés — quantification FSDC","Heading1"))
    content.append(par("Extraction directe des valeurs contenues dans les preuves sauvegardées. "
       "Aucun chiffre supplémentaire, tendance ou effet minier n'a été calculé.","TC16Note"))
    if quant["metrics"]:
        from reportlab.platypus import Table,TableStyle
        cells=[[par("Indicateur","TC16Note"),par("Valeur","TC16Note"),par("Source / année","TC16Note")]]
        for m in quant["metrics"]:
            cells.append([par(m["metric"]),par(str(m["value"])+" %"),
                par(m["evidence_id"]+" / "+m["observed_at"],"TC16Note")])
        t=Table(cells,colWidths=[69*mm,24*mm,77*mm],repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
            ("BOTTOMPADDING",(0,0),(-1,-1),9),
            ("LINEBELOW",(0,0),(-1,0),0.6,colors.HexColor("#aac0d4")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#eef3f8")])]))
        content.append(t)
    else:
        content.append(par("Aucun indicateur numérique admissible identifié dans les constats de cette session."))
    content.append(par("Limites : les valeurs décrivent uniquement l'emprise de l'observation. "
      "Elles ne prouvent aucun changement temporel, impact minier ou exposition des populations.","TC16Note"))
    content.append(par("SHA256 quantification : "+quant["metrics_sha256"],"TC16Note"))
    content.append(PageBreak())
    content.append(par("Matrice des investigations scientifiques","Heading1"))
    content.append(par("Options non classées et non approuvées. Coût, impact et faisabilité : non évalués.","TC16Note"))
    for option in matrix["options"]:
        content.append(par(option["option_id"]+" — "+option["proposing_agent"],"Heading3"))
        content.append(par(option["investigation"]))
        content.append(par("Preuves : "+", ".join(option["evidence_ids"])+
                           " | Priorité : non évaluée | Coût : indisponible","TC16Note"))
        for caution in option["scientific_limits"][:1]:
            content.append(par("Limite : "+caution,"TC16Note"))
    content.append(par("Critique et désaccords — Wonder","Heading2"))
    for issue in matrix["scientific_critic_issues"]:
        content.append(par("• "+issue))
    content.append(par("Classement comparatif : impossible sans données complémentaires.","TC16Note"))
    content.append(par("SHA256 matrice : "+matrix["matrix_sha256"],"TC16Note"))
    content.append(PageBreak())
    content.append(par("Arguments et contre-expertise","Heading1"))
    for i,step in enumerate(data["steps"],1):
        content.append(par(str(i)+". "+step["role"]+" — "+step["model"],"Heading2"))
        p=step["checked_publication"]
        for key,label in (("hypotheses","Hypothèses non vérifiées"),
                          ("investigations","Investigations proposées"),
                          ("abstentions","Limites et abstentions")):
            content.append(par(label,"Heading3"))
            for entry in p[key]:content.append(par("• "+entry["text"]))
    content.append(PageBreak())
    content.append(par("Preuves FSDC et traçabilité","Heading1"))
    for e in data["sources"]:
        content.append(par(e["evidence_id"]+" — "+e["dataset"],"Heading3"))
        content.append(par(e["finding"]))
        content.append(par("Source : "+e["source"]+" | Date : "+e["observed_at"]+
             " | Validation : "+e["validation_status"],"TC16Note"))
    if data["regional_context"]:
        content.append(par("Contexte scientifique régional — distinct de l'AOI","Heading2"))
        for entry in data["regional_context"]:
            content.append(par(entry["evidence_id"]+" — "+entry["source_type"],"Heading3"))
            content.append(par(entry["claim"]))
            content.append(par("Portée : "+entry["scope"]+" | Statut : "+
                  entry["validation_status"],"TC16Note"))
            content.append(par("Lien original : "+entry["source_url"],"TC16Note"))
            for limit in entry["limitations"][:2]:
                content.append(par("Limite : "+limit,"TC16Note"))
        content.append(par("Ces sources régionales ne constituent pas des mesures "
           "sur l'emprise rectangulaire et ne démontrent aucun changement actuel.","TC16Note"))
    content.append(par("Empreinte FSDC SHA-256 : "+data["evidence_sha256"],"TC16Note"))
    content.append(par("Document generated solely from the saved dynamic scientific debate. "
       "Free-form agent proposals remain unvalidated and require independent review.","TC16Note"))
    pdf=SimpleDocTemplate(str(output),pagesize=(210*mm,297*mm),
                          leftMargin=20*mm,rightMargin=20*mm,
                          topMargin=18*mm,bottomMargin=19*mm,
                          title="TerraCouncil Dynamic Decision Brief",
                          author="SustainAfrica — FAITH FSDC")
    pdf.build(content)
    return output
