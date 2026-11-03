"""TerraCouncil Executive Decision Brief V3 — visually distinct committee edition.

Verified HACK-008 session data only, no network, no model calls.
Editorial interpretations are explicitly preliminary. The original raw steps
remain in the session JSON; this PDF carries a concise audit appendix.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import re

VERSION="EXECUTIVE_BRIEF_V3_2026_10_28"

def export_v3(data, filename):
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, PageBreak, KeepTogether)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    destination=Path(filename)
    if destination.exists():
        raise ValueError("Never overwrite a versioned executive PDF")
    destination.parent.mkdir(parents=True,exist_ok=True)
    NAVY=colors.HexColor("#0D2338")
    TEAL=colors.HexColor("#0D7A83")
    INK=colors.HexColor("#253B4D")
    MUTE=colors.HexColor("#5C7181")
    PALE=colors.HexColor("#EAF3F3")
    GOLD=colors.HexColor("#CA924C")
    WHITE=colors.white
    BG=colors.HexColor("#FAFBFC")
    font="Helvetica"
    bold="Helvetica-Bold"
    # Use a modern Unicode font where available; the PDF still works without it.
    regular_candidates=[
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    bold_candidates=[
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for name,targets in (("TCBodyFont",regular_candidates),("TCBoldFont",bold_candidates)):
        for candidate in targets:
            if Path(candidate).is_file():
                try:pdfmetrics.registerFont(TTFont(name,candidate));break
                except Exception:pass
    if "TCBodyFont" in pdfmetrics.getRegisteredFontNames():font="TCBodyFont"
    if "TCBoldFont" in pdfmetrics.getRegisteredFontNames():bold="TCBoldFont"
    styles={
        "h":ParagraphStyle("TCV3Heading",fontName=bold,fontSize=14,leading=21,textColor=NAVY,spaceBefore=13,spaceAfter=7,keepWithNext=1),
        "sub":ParagraphStyle("TCV3Sub",fontName=bold,fontSize=10,leading=15,textColor=TEAL,spaceBefore=8,spaceAfter=4,keepWithNext=1),
        "body":ParagraphStyle("TCV3Body",fontName=font,fontSize=9.3,leading=15,textColor=INK,spaceAfter=7),
        "small":ParagraphStyle("TCV3Small",fontName=font,fontSize=7.3,leading=11,textColor=MUTE,spaceAfter=5,wordWrap="CJK"),
        "white":ParagraphStyle("TCV3White",fontName=bold,fontSize=10.5,leading=16,textColor=WHITE,spaceAfter=5),
        "whitebody":ParagraphStyle("TCV3WhiteBody",fontName=font,fontSize=9.5,leading=15,textColor=WHITE),
        "number":ParagraphStyle("TCV3Num",fontName=bold,fontSize=15,leading=21,textColor=TEAL),
    }
    def p(text,style="body"):
        return Paragraph(escape(str(text)).replace("\n","<br/>"),styles[style])
    width,height=210*mm,297*mm
    left=22*mm
    content_width=width-2*left
    def draw_page(c, doc):
        page=doc.page
        c.saveState()
        c.setFillColor(BG);c.rect(0,0,width,height,stroke=0,fill=1)
        c.setFillColor(NAVY);c.rect(0,height-14*mm,width,14*mm,stroke=0,fill=1)
        c.setFillColor(WHITE);c.setFont(bold,9)
        c.drawString(left,height-9*mm,"TERRACOUNCIL  /  SUSTAINAFRICA")
        c.setFont(font,7);c.drawRightString(width-left,height-9*mm,"FAITH · FSDC | NOTE V3")
        c.setStrokeColor(colors.HexColor("#D9E3E7"));c.line(left,15*mm,width-left,15*mm)
        c.setFillColor(MUTE);c.setFont(font,7.4)
        c.drawString(left,10*mm,"Exploratoire · Vérification structurelle · Revue humaine requise")
        c.drawRightString(width-left,10*mm,f"{page}")
        c.restoreState()
    def cover(c,doc):
        c.saveState()
        c.setFillColor(NAVY);c.rect(0,0,width,height,stroke=0,fill=1)
        c.setFillColor(TEAL);c.rect(0,height-12*mm,width,12*mm,stroke=0,fill=1)
        c.setFont(bold,12);c.setFillColor(WHITE);c.drawString(left,height-9*mm,"SUSTAINAFRICA")
        c.setStrokeColor(colors.HexColor("#317B8B"))
        for y in (142,149,156):
            c.line(left*1.0,y*mm,width-left,y*mm)
        c.setFillColor(colors.HexColor("#75D0D3"));c.setFont(bold,10)
        c.drawString(left,244*mm,"FAITH  /  FSDC  /  TERRACOUNCIL")
        c.setFillColor(WHITE);c.setFont(bold,27)
        c.drawString(left,211*mm,"INTELLIGENCE")
        c.drawString(left,195*mm,"DÉCISIONNELLE")
        c.setFont(font,14);c.drawString(left,175*mm,"Note de délibération scientifique")
        c.setFillColor(colors.HexColor("#A9D4D9"));c.setFont(bold,15)
        c.drawString(left,120*mm,"BOKÉ  ·  GUINÉE")
        c.setFont(font,11);c.setFillColor(WHITE)
        c.drawString(left,109*mm,"Périmètre pilote d'analyse géospatiale")
        c.setFillColor(colors.HexColor("#D7A567"));c.roundRect(left,80*mm,120*mm,12*mm,4*mm,stroke=0,fill=1)
        c.setFillColor(NAVY);c.setFont(bold,8.6);c.drawString(left+5*mm,84*mm,"EXPLORATOIRE  •  NON VALIDÉ SUR LE TERRAIN")
        c.setFillColor(colors.HexColor("#BDCAD8"));c.setFont(font,8)
        c.drawString(left,25*mm,"Session : "+str(data["run_id"])[:45])
        c.drawString(left,18*mm,VERSION)
        c.restoreState()
    flow=[PageBreak()]
    def head(title):flow.append(p(title,"h"))
    def sub(title):flow.append(p(title,"sub"))
    def para(text):flow.append(p(text))
    def color_panel(label,text):
        inside=[p(label,"white"),p(text,"whitebody")]
        tbl=Table([[inside]],colWidths=[content_width])
        tbl.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),
            ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
            ("TOPPADDING",(0,0),(-1,-1),13),("BOTTOMPADDING",(0,0),(-1,-1),11)]))
        flow.append(tbl)
        flow.append(Spacer(1,6*mm))
    # Second page: concise and decision-focused, visually unlike previous PDF.
    head("L'essentiel pour le décideur")
    para(data["question"])
    color_panel("ORIENTATION PROVISOIRE",
                "Les éléments disponibles servent à définir les vérifications à entreprendre. "
                "Ils ne permettent pas de conclure à des impacts miniers ni d'autoriser un investissement.")
    head("Trois messages clés")
    message=[
        ("01","Population","WorldPop 2026 fournit une estimation spatiale du périmètre étudié, "
         "pas un recensement ni une mesure des habitants exposés."),
        ("02","Territoire","WorldCover 2021 décrit des catégories d'occupation du sol à une date ancienne, "
         "sans démontrer leur évolution actuelle."),
        ("03","Décision","Une étude de terrain et des sources complémentaires sont nécessaires avant toute conclusion.")
    ]
    for num,label,description in message:
        row=Table([[p(num,"number"),[p(label,"sub"),p(description)]]],
                  colWidths=[17*mm,content_width-17*mm])
        row.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),
            ("LINEBELOW",(0,0),(-1,-1),0.6,colors.HexColor("#CEDFDF")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),9)]))
        flow.append(row);flow.append(Spacer(1,2*mm))
    head("Orientation pour le comité")
    para("Mandater les études préalables plutôt que statuer sur la viabilité du projet. "
         "Les positions présentées sont issues d'agents IA : aucune délibération d'un comité humain n'est affirmée.")
    flow.append(PageBreak())
    head("Programme d'investigations prioritaires")
    tasks=[
       ("P1","Délimiter le territoire réellement concerné","Contrôle géographique et pertinence du périmètre."),
       ("P2","Documenter les communautés","Données démographiques et vérification de terrain."),
       ("P3","Actualiser la couverture du sol","Cultures, couvert végétal, mangroves et biodiversité."),
       ("P4","Établir les données initiales eau-climat","Études hydrologiques et climatiques distinctes."),
       ("P5","Auditer la qualité des données","Dates, incertitudes, classification et traçabilité FSDC.")
    ]
    table_rows=[[p("PRIORITÉ","sub"),p("INVESTIGATION","sub"),p("FINALITÉ","sub")]]
    for code,label,detail in tasks:table_rows.append([p(code,"sub"),p(label),p(detail,"small")])
    table=Table(table_rows,colWidths=[22*mm,69*mm,content_width-91*mm],repeatRows=1,hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),PALE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,BG]),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D4E1E5")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),9),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    flow.append(table)
    head("Ce que la confrontation a changé")
    para("La critique Muse Wonder a questionné la représentativité du périmètre rectangulaire, "
         "l'ancienneté de la couverture du sol et l'absence de validation terrain. "
         "La révision Muse Spark conserve ces réserves et propose des enquêtes complémentaires.")
    head("Décisions à différer")
    color_panel("NON ÉTABLI",
                "Impact minier, nombre de personnes affectées, état de la biodiversité, "
                "risques hydrologiques ou climatiques, conformité réglementaire et autorisation d'investissement.")
    flow.append(PageBreak())
    head("Fondation scientifique et limites")
    # Keep real source numeric values only as reported in verified facts, not an inferred chart.
    for e in data["evidence"]:
        sub(e["dataset"])
        para(e["finding"])
        flow.append(p("Statut : "+e["validation_status"]+"  |  Date : "+e["observed_at"],"small"))
    head("Niveau de vérification")
    para("Le mécanisme FSDC a contrôlé la correspondance exacte des observations citées aux données "
         "disponibles et la cohérence des identifiants. Cette opération ne vérifie pas sur le terrain "
         "les phénomènes décrits et ne démontre aucune causalité.")
    para("Le conseil exécuté comporte deux perspectives analytiques Muse Spark, une critique Muse Wonder "
         "et une synthèse révisée Muse Spark. Il ne représente pas des membres officiels des parties prenantes.")
    flow.append(PageBreak())
    head("Annexe — interventions auditées")
    flow.append(p("Traçabilité des quatre étapes. Texte original conservé, non adapté à la lecture audio.","small"))
    labels=[
        "01 · Analyse minière — Muse Spark",
        "02 · Analyse environnementale — Muse Spark",
        "03 · Critique scientifique — Muse Wonder",
        "04 · Synthèse révisée — Muse Spark"
    ]
    for label,step in zip(labels,data["steps"]):
        head(label)
        publication=step["checked_publication"]
        for key,title in (("hypotheses","Hypothèses"),("investigations","Investigations"),
                          ("abstentions","Abstentions")):
            sub(title)
            for item in publication.get(key,[]):
                flow.append(p("• "+item["text"],"small"))
    head("Identifiants de traçabilité")
    for e in data["evidence"]:
        flow.append(p(e["evidence_id"]+" · "+e["dataset"],"small"))
        flow.append(p("Source : "+e["source"],"small"))
    flow.append(p("Session : "+str(data["run_id"]),"small"))
    flow.append(p("Empreinte FSDC SHA256 : "+data["sha256"],"small"))
    flow.append(p("Version export : "+VERSION,"small"))
    class CoverDocTemplate(SimpleDocTemplate):
        def handle_pageBegin(self):
            super().handle_pageBegin()
    doc=SimpleDocTemplate(str(destination),pagesize=(width,height),
        leftMargin=left,rightMargin=left,topMargin=21*mm,bottomMargin=21*mm,
        title="TerraCouncil | Executive Decision Brief V3",
        subject=VERSION,author="SustainAfrica — TerraCouncil",
        pageCompression=1)
    doc.build(flow,onFirstPage=cover,onLaterPages=draw_page)
    return destination
