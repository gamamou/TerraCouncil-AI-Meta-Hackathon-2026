"""Branded, English-native scientific PDF for one verified source trace.

No Meta/ElevenLabs requests. Texts are unmodified from the authenticated local trace.
"""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

NAVY=HexColor('#173449'); TEAL=HexColor('#008F83'); GOLD=HexColor('#DBB663'); MUTE=HexColor('#566977')
W,H=A4

def generate(ctx, outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    target=outdir/('TerraCouncil-'+Path(ctx['trace']).stem+'-BRANDED-EN.pdf')
    root=Path(__file__).resolve().parent
    logo=root/'release_101_modules'/'sustainafrica_logo.jpg'
    if not logo.is_file():raise ValueError('SustainAfrica branding asset missing; PDF not generated')
    font='Helvetica'
    for f in (Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')):
        if f.is_file():
            try:
                pdfmetrics.registerFont(TTFont('Terra114Body',str(f)))
                font='Terra114Body';break
            except Exception:pass
    styles={
        'title':ParagraphStyle('t114',fontName=font,fontSize=14.5,leading=21,textColor=NAVY,spaceAfter=9),
        'small':ParagraphStyle('s114',fontName=font,fontSize=8.1,leading=12.5,textColor=MUTE,spaceAfter=7),
        'section':ParagraphStyle('h114',fontName=font,fontSize=10.7,leading=16,textColor=TEAL,spaceBefore=13,spaceAfter=7),
        'body':ParagraphStyle('b114',fontName=font,fontSize=9,leading=15,textColor=NAVY,spaceAfter=9),
    }
    def p(s,k='body'):return Paragraph(escape(str(s)).replace('\n','<br/>'),styles[k])
    def page(canvas,doc):
        canvas.saveState()
        canvas.setFillColor(NAVY);canvas.rect(0,H-104,W,104,fill=1,stroke=0)
        canvas.setFillColor(TEAL);canvas.rect(0,H-110,W*.74,6,fill=1,stroke=0)
        canvas.setFillColor(GOLD);canvas.rect(W*.74,H-110,W*.26,6,fill=1,stroke=0)
        img=ImageReader(str(logo));iw,ih=img.getSize();scale=min(115/iw,67/ih)
        canvas.drawImage(img,43,H-89,width=iw*scale,height=ih*scale,mask='auto')
        canvas.setFont(font,10);canvas.setFillColor(white);canvas.drawRightString(W-43,H-42,'TERRACOUNCIL')
        canvas.setFont(font,7);canvas.drawRightString(W-43,H-59,'SUSTAINAFRICA  ·  FSDC')
        canvas.setStrokeColor(TEAL);canvas.line(43,40,W-43,40)
        canvas.setFont(font,7);canvas.setFillColor(MUTE)
        canvas.drawString(43,28,'Source-bound Meta deliberation · Not a field-validated finding')
        canvas.drawRightString(W-43,28,str(doc.page))
        canvas.restoreState()
    phases=ctx['result']['phases']
    story=[p('SCIENTIFIC DECISION BRIEF','title'),p('TERRACOUNCIL  /  SUSTAINAFRICA  /  META LIVE','small'),
        p('QUESTION EXAMINED','section'),p(ctx['question']),
        p('COUNCIL POSITION','section'),p(phases[2]['text']),
        p('EVIDENCE STATUS','section'),p('Scientifically admitted local observations in this session: '+str(ctx['result'].get('scientific_evidence_admitted','not recorded'))+'.'),
        p('Unverified candidate source references are not observations. No local conclusion is established without admissible evidence. Absence of admissible evidence in this session does not imply no relevant information exists elsewhere.','small'),
        p('NEXT STEPS AND DECISION BOUNDARY','section'),p('Confirm relevant data requirements, source provenance, geographic and temporal coverage, and independent validation before taking location-specific decisions.'),
        p('Scientific provenance: '+ctx['trace'],'small'),p('Trace SHA-256: '+ctx['sha'],'small'),PageBreak(),
        p('APPENDIX — ORIGINAL META DELIBERATION','title'),p('Original model text preserved without translation or invented measurements.','small')]
    for label,phase in zip(('Spark · initial analysis','Wonder · scientific critique','Spark · revision'),phases):
        story.extend([p(label+'  |  '+str(phase.get('model','')),'section'),p(phase['text'])])
    SimpleDocTemplate(str(target),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=137,bottomMargin=57,title='TerraCouncil — English Scientific Decision Brief').build(story,onFirstPage=page,onLaterPages=page)
    return target
