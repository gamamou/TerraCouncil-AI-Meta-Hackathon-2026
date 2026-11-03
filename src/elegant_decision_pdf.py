"""HACK-010: elegant French committee-ready brief from verified HACK-008 data.

Editorial executive summary is a conservative template, NOT an AI approval.
Original Meta statements stay in an audit appendix. No network or Meta calls.
"""
from pathlib import Path
import re
from xml.sax.saxutils import escape

def export_elegant_pdf(data, output):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.units import mm

    output=Path(output)
    if output.exists(): raise ValueError("PDF already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    dark=HexColor("#18344D"); teal=HexColor("#147A87")
    gray=HexColor("#566678"); cream=HexColor("#F2F6F7"); amber=HexColor("#8B5A19")
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TCTitle", fontName="Helvetica-Bold",fontSize=23,leading=29,
                              textColor=dark,spaceAfter=10))
    styles.add(ParagraphStyle(name="TCLead",fontName="Helvetica",fontSize=11,leading=17,
                              textColor=gray,spaceAfter=12))
    styles.add(ParagraphStyle(name="TCHead",fontName="Helvetica-Bold",fontSize=14,leading=19,
                              textColor=dark,spaceBefore=16,spaceAfter=10,keepWithNext=True))
    styles.add(ParagraphStyle(name="TCSubHead",fontName="Helvetica-Bold",fontSize=10,leading=14,
                              textColor=teal,spaceBefore=10,spaceAfter=5,keepWithNext=True))
    styles.add(ParagraphStyle(name="TCBodyClean",fontName="Helvetica",fontSize=9.6,leading=15,
                              textColor=dark,spaceAfter=8))
    styles.add(ParagraphStyle(name="TCFine",fontName="Helvetica",fontSize=7.6,leading=11,
                              textColor=gray,spaceAfter=5,wordWrap="CJK"))
    styles.add(ParagraphStyle(name="TCKicker",fontName="Helvetica-Bold",fontSize=9,leading=13,
                              textColor=teal,spaceAfter=11,tracking=1))
    styles.add(ParagraphStyle(name="TCWarning",fontName="Helvetica-Bold",fontSize=9,leading=14,
                              textColor=amber,spaceAfter=7))
    P=lambda txt,sty="TCBodyClean":Paragraph(escape(str(txt)).replace("\n","<br/>"),styles[sty])
    flow=[]
    def section(title):flow.append(P(title,"TCHead"))
    def para(txt,style="TCBodyClean"):flow.append(P(txt,style))
    def pill(title,body):
        t=Table([[P(title,"TCSubHead")],[P(body)]],colWidths=[168*mm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),cream),
                               ("BOX",(0,0),(-1,-1),0.3,HexColor("#D1DEE2")),
                               ("LEFTPADDING",(0,0),(-1,-1),13),
                               ("RIGHTPADDING",(0,0),(-1,-1),13),
                               ("TOPPADDING",(0,0),(-1,-1),8),
                               ("BOTTOMPADDING",(0,0),(-1,-1),9)]))
        flow.append(t);flow.append(Spacer(1,5*mm))
    src={e["evidence_id"]:e for e in data["evidence"]}
    pop=next((e for e in data["evidence"] if "WorldPop" in e["dataset"]),None)
    cover=next((e for e in data["evidence"] if "WorldCover" in e["dataset"]),None)
    final=data["steps"][-1]["checked_publication"]
    critique=data["steps"][-2]["checked_publication"]
    # This is explicitly a conservative editorial interpretation of the displayed verified facts.
    flow.append(P("SUSTAINAFRICA  /  FAITH  /  FSDC","TCKicker"))
    flow.append(P("TerraCouncil","TCTitle"))
    flow.append(P("Note de délibération scientifique  |  Périmètre pilote de Boké","TCLead"))
    flow.append(P("DOSSIER EXPLORATOIRE — REVUE HUMAINE REQUISE","TCWarning"))
    para("Objet de la délibération","TCSubHead")
    para(data["question"])
    section("Synthèse exécutive")
    pill("Orientation préliminaire",
         "Les informations examinées permettent de proposer des investigations complémentaires. "
         "Elles ne suffisent pas à établir les impacts du projet ni à soutenir une décision d'investissement. "
         "Le Conseil recommande de renforcer les données de référence et leur vérification.")
    section("Ce qui est documenté")
    if pop:
        para("Population : une estimation spatialisée de WorldPop 2026 est disponible pour le périmètre d'étude. "
             "Elle ne constitue ni un recensement ni une mesure du nombre de personnes potentiellement affectées.")
    if cover:
        para("Occupation du sol : une photographie de référence ESA WorldCover 2021 décrit certaines classes de couverture "
             "du territoire. Elle ne démontre pas les changements survenus depuis 2021 ni une responsabilité minière.")
    section("Investigations à engager en priorité")
    priorities=[
        ("1 · Délimitation et représentativité",
         "Vérifier que le périmètre rectangulaire choisi correspond bien aux sites et aux enjeux de la décision."),
        ("2 · Population et communautés",
         "Recouper les estimations raster avec des données démographiques actualisées et des enquêtes de terrain."),
        ("3 · Territoires et milieux naturels",
         "Actualiser l'état initial de l'occupation du sol, des cultures, des mangroves et de la biodiversité."),
        ("4 · Eau et climat",
         "Réaliser des études hydrologiques et climatiques spécifiques avant de qualifier les risques."),
        ("5 · Qualité des preuves",
         "Vérifier les dates, les méthodes, les limites des classifications satellitaires et les résultats sur le terrain.")
    ]
    for name,description in priorities:
        para(name,"TCSubHead");para(description)
    section("Enseignements de la confrontation")
    para("La première analyse a proposé des investigations démographiques et environnementales. "
         "La critique de Muse Wonder a souligné l'écart temporel des données, les limites du périmètre rectangulaire "
         "et l'absence de validation de terrain. La synthèse finale a maintenu ces réserves. "
         "Ces constats sont issus d'une lecture éditoriale des interventions structurées, non d'une approbation humaine.")
    section("Décisions à différer")
    para("Ne pas conclure, sur la base de ces deux jeux de données seuls, à une population exposée, "
         "à des impacts écologiques ou climatiques, à un changement d'occupation du sol en 2026, "
         "à une causalité minière ou à une autorisation d'investir.")
    section("Sources et degré de confiance")
    if pop:para("WorldPop 2026 · estimation raster · statut : données préliminaires non validées sur le terrain.","TCFine")
    if cover:para("ESA WorldCover 2021 · répartition des classes de couverture · statut : données préliminaires non validées sur le terrain.","TCFine")
    para("Les contrôles FSDC vérifient la concordance des références et des observations reprises par les modèles. "
         "Ils ne démontrent pas à eux seuls la justesse scientifique des sources ou des interprétations.","TCFine")
    flow.append(PageBreak())
    para("ANNEXE · TRAÇABILITÉ DES INTERVENTIONS","TCKicker")
    para("Les textes ci-dessous conservent les interventions originales pour audit. Leur rédaction anglaise et leur "
         "vocabulaire technique ne sont pas destinés à être lus comme script audio.","TCFine")
    names=["Muse Spark — perspective minière","Muse Spark — perspective environnementale",
           "Muse Wonder — critique scientifique","Muse Spark — synthèse révisée"]
    for name,step in zip(names,data["steps"]):
        section(name)
        pub=step["checked_publication"]
        for key,title in (("hypotheses","Hypothèses"),("investigations","Investigations"),
                          ("abstentions","Abstentions")):
            para(title,"TCSubHead")
            for item in pub.get(key,[]):
                para("— "+item["text"],"TCFine")
    section("Références techniques")
    for e in data["evidence"]:
        para(e["evidence_id"]+" · "+e["dataset"],"TCSubHead")
        para(e["finding"],"TCFine")
        para("Source : "+e["source"]+" · Statut : "+e["validation_status"],"TCFine")
    para("Session : "+str(data["run_id"])+"  |  SHA-256 : "+data["sha256"],"TCFine")
    doc=SimpleDocTemplate(str(output),pagesize=(210*mm,297*mm),topMargin=20*mm,bottomMargin=20*mm,
                          leftMargin=21*mm,rightMargin=21*mm,
                          title="TerraCouncil — Note de délibération scientifique",
                          author="SustainAfrica / TerraCouncil")
    def footer(canvas,document):
        canvas.saveState();w,h=document.pagesize
        canvas.setStrokeColor(HexColor("#C5D4DC"));canvas.line(21*mm,17*mm,w-21*mm,17*mm)
        canvas.setFont("Helvetica",8);canvas.setFillColor(gray)
        canvas.drawString(21*mm,12*mm,"TerraCouncil  ·  Analyse exploratoire  ·  Revue scientifique requise")
        canvas.drawRightString(w-21*mm,12*mm,str(document.page))
        canvas.restoreState()
    doc.build(flow,onFirstPage=footer,onLaterPages=footer)
    return output
