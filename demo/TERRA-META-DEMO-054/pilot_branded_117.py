"""Live-style branded Demo report. No network access; legacy briefs remain labelled as such.
A genuine recorded council trace is displayed only after 116B audio/trace verification.
"""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
import json, hashlib

NAVY=HexColor('#173449'); TEAL=HexColor('#008F83'); GOLD=HexColor('#DBB663'); MUTE=HexColor('#566977')
W,H=A4

def _font():
    for name in ('C:/Windows/Fonts/arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        f=Path(name)
        if f.exists():
            try:
                pdfmetrics.registerFont(TTFont('Terra117Body',str(f)))
                return 'Terra117Body'
            except Exception: pass
    return 'Helvetica'

def report(pilot,lang,root):
    import pilot_115
    root=Path(root)
    entry=pilot_115.select(pilot,lang)
    logo=root/'release_101_modules'/'sustainafrica_logo.jpg'
    if not logo.is_file(): raise ValueError('Required SustainAfrica logo absent; refusing unbranded report')
    font=_font()
    styles={
      'title':ParagraphStyle('tc117title',fontName=font,fontSize=16,leading=22,textColor=NAVY,spaceAfter=11),
      'subtitle':ParagraphStyle('tc117subtitle',fontName=font,fontSize=8,leading=12,textColor=MUTE,spaceAfter=7),
      'section':ParagraphStyle('tc117section',fontName=font,fontSize=10.8,leading=15.5,textColor=TEAL,spaceBefore=15,spaceAfter=8),
      'body':ParagraphStyle('tc117body',fontName=font,fontSize=9,leading=14.5,textColor=NAVY,spaceAfter=9),
      'small':ParagraphStyle('tc117small',fontName=font,fontSize=8,leading=12,textColor=MUTE,spaceAfter=8),
    }
    def p(s,style='body'): return Paragraph(escape(str(s)).replace('\n','<br/>'),styles[style])
    def header(canvas,doc):
        canvas.saveState()
        canvas.setFillColor(NAVY); canvas.rect(0,H-104,W,104,fill=1,stroke=0)
        canvas.setFillColor(TEAL); canvas.rect(0,H-110,W*.74,6,fill=1,stroke=0)
        canvas.setFillColor(GOLD); canvas.rect(W*.74,H-110,W*.26,6,fill=1,stroke=0)
        iw,ih=ImageReader(str(logo)).getSize(); scale=min(115/iw,67/ih)
        canvas.drawImage(str(logo),43,H-89,width=iw*scale,height=ih*scale,mask='auto')
        canvas.setFont(font,10);canvas.setFillColor(white);canvas.drawRightString(W-43,H-42,'TERRACOUNCIL')
        canvas.setFont(font,7);canvas.drawRightString(W-43,H-59,'SUSTAINAFRICA  ·  FSDC')
        canvas.setStrokeColor(TEAL);canvas.line(43,40,W-43,40)
        canvas.setFont(font,7);canvas.setFillColor(MUTE)
        canvas.drawString(43,28,'TerraCouncil AI  ·  Scientific pilot demonstration')
        canvas.drawRightString(W-43,28,str(doc.page))
        canvas.restoreState()
    french=lang=='fr'
    story=[p('NOTE SCIENTIFIQUE — DÉMONSTRATION' if french else 'SCIENTIFIC DECISION BRIEF — DEMO','title'),
      p('TERRACOUNCIL  /  SUSTAINAFRICA  /  PILOT '+pilot,'subtitle'),p(entry['title']+' — '+entry['region'],'section'),
      p('QUESTION EXAMINÉE' if french else 'QUESTION EXAMINED','section'),p(entry['question'])]
    manifest=root/'pilot_audio_116b'/f'{pilot}-{lang}.json'
    from pilot_115 import audio_segments
    recorded=bool(audio_segments(pilot,lang,root))
    trace=None; trace_hash=''
    if recorded:
        manifest_data=json.loads(manifest.read_text(encoding='utf8'))
        trace_path=Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs'/manifest_data['source_trace']
        trace_hash=hashlib.sha256(trace_path.read_bytes()).hexdigest()
        if trace_hash!=manifest_data['source_trace_sha256']:raise ValueError('Trace mismatch')
        trace=json.loads(trace_path.read_text(encoding='utf8'))
        result=trace['meta_result'];phases=result['phases']
        story.extend([p('CONCLUSION RÉVISÉE DU CONSEIL META' if french else 'REVISED META COUNCIL POSITION','section'),p(phases[2]['text']),
          p('STATUT DES PREUVES' if french else 'EVIDENCE STATUS','section'),
          p(('Observations locales admises dans cette session : ' if french else 'Admitted local observations in this session: ')+str(result.get('scientific_evidence_admitted','not recorded'))),
          p('Les sources candidates ne constituent pas des observations locales validées.' if french else 'Candidate sources are not field-validated observations.','small')])
    else:
        story.extend([p('SYNTHÈSE ÉDITORIALE — NON ISSUE D’UNE NOUVELLE INFÉRENCE META' if french else 'EDITORIAL SUMMARY — NOT A NEW META INFERENCE','section'),p(entry['lead']),
          p('Un véritable enregistrement Meta n’est pas encore publié pour ce pilote et cette langue.' if french else 'An authenticated Meta council recording has not yet been published for this pilot and language.','small')])
    story.append(p('AXES D’ANALYSE' if french else 'OPTIONS FOR INVESTIGATION','section'))
    for i,opt in enumerate(entry['options'],1):story.append(p(f'{i}. {opt}'))
    story.extend([p('LIMITES SCIENTIFIQUES' if french else 'SCIENTIFIC LIMITATIONS','section'),p(entry['limits'])])
    science=root/'scientific_116.json'
    if science.is_file():
        sci=json.loads(science.read_text(encoding='utf8'))['pilots'][pilot]
        story.append(p('SOURCES CANDIDATES À VÉRIFIER' if french else 'CANDIDATE DATASETS TO VERIFY','section'))
        for ds in sci['candidate_sources']:
            story.append(p(ds['dataset']+' · '+ds['provider']+' — '+ds['suggested_variable'],'small'))
        story.append(p('LACUNES DOCUMENTAIRES' if french else 'EVIDENCE GAPS','section'))
        for gap in sci['evidence_gaps']:story.append(p('• '+gap,'small'))
    story.append(p('PROTOCOLE DU CONSEIL : Spark → Wonder → Spark' if french else 'COUNCIL PROTOCOL: Spark → Wonder → Spark','section'))
    story.append(p('Le dossier distingue données candidates et observations vérifiées ; aucune validation terrain n’est implicite.' if french else 'Candidate sources are not admissible local evidence absent independent validation.','small'))
    if recorded:
        story.extend([PageBreak(),p('ANNEXE — DÉLIBÉRATION META AUTHENTIFIÉE' if french else 'APPENDIX — AUTHENTIC META DELIBERATION','title')])
        for phase in trace['meta_result']['phases']:
            story.extend([p(phase['phase'].replace('_',' ').title()+' · '+str(phase.get('model','')),'section'),p(phase['text'])])
        story.extend([p('Trace: '+manifest_data['source_trace'],'small'),p('SHA-256: '+trace_hash,'small')])
    out=root/'pilot_reports_115';out.mkdir(exist_ok=True)
    filename=f'TerraCouncil-DEMO-{pilot}-{lang.upper()}-SustainAfrica.pdf'
    path=out/filename
    SimpleDocTemplate(str(path),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=137,bottomMargin=57,title='TerraCouncil · '+entry['title']).build(story,onFirstPage=header,onLaterPages=header)
    if path.stat().st_size<2000:raise ValueError('PDF output invalid')
    return path
