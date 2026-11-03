"""Isolated, no-Meta-call three-pilot jury experience.

Data is a verbatim-preserving extraction of the DEMO-054 editorial briefs.
The PDF is an EXPLORATORY EDITORIAL BRIEF, never labelled as new Meta analysis.
Only authenticated, prerecorded local audio is served. No external calls.
"""
from pathlib import Path
from urllib.parse import urlparse,parse_qs,quote
from http import HTTPStatus
import json,re

ROOT=Path(__file__).resolve().parent
DATA_FILE=ROOT/'pilots_115.json'
KEYS=('BOKE','FLOOD','AGRO')
LANGS=('fr','en')

def pilots():
    data=json.loads(DATA_FILE.read_text(encoding='utf-8'))
    if set(data)!=set(KEYS):raise ValueError('Exactly three fixed demo pilots required')
    for p in KEYS:
        if set(data[p])!=set(LANGS):raise ValueError('Missing pilot language')
    return data

def select(pilot,lang):
    if pilot not in KEYS or lang not in LANGS:raise ValueError('Invalid pilot or language')
    return pilots()[pilot][lang]

def audio_segments(pilot,lang,root=ROOT):
    # RELEASE-116B VERIFIED AUDIO: strict three-pilot, per-language, exact-recording manifest.
    from hashlib import sha256
    key=pilot+'-'+lang
    manifest=Path(root)/'pilot_audio_116b'/(key+'.json')
    try:
        item=json.loads(manifest.read_text(encoding='utf8'))
        if item.get('schema')!='terra-pilot-audio-116b/1.0' or item.get('status')!='COMPLETE':return []
        if item.get('pilot_id')!=pilot or item.get('language')!=lang:return []
        from pilot_editor_119 import published_audio_allowed
        if not published_audio_allowed(root,pilot,lang,item):return []
        reg=json.loads((Path(root)/'pilots_115.json').read_text(encoding='utf8'))
        if item.get('question')!=reg[pilot][lang]['question']:return []
        path=Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs'/item.get('source_trace','')
        if not path.is_file() or sha256(path.read_bytes()).hexdigest()!=item.get('source_trace_sha256'):return []
        trace=json.loads(path.read_text(encoding='utf8'))
        phases=trace.get('meta_result',{}).get('phases',[])
        if [p.get('phase') for p in phases]!=['spark_initial','wonder_critique','spark_revision']:return []
        if trace.get('meta_result',{}).get('language')!=lang:return []
        if trace.get('meta_result',{}).get('question')!=item['question']:return []
        entries=item.get('segments',[])
        if not isinstance(entries,list) or not 1<=len(entries)<=10:return []
        out=[]
        for i,seg in enumerate(entries,1):
            filename=seg.get('filename','')
            if not re.fullmatch(r'TC116B-[A-Z]+-(?:fr|en)-[a-f0-9]{12}(?:-[a-f0-9]{8})?-[0-9]{2}\.mp3',filename):return []
            if seg.get('sequence')!=i:return []
            file=Path(root)/'council_sessions'/filename
            if not file.is_file() or file.stat().st_size<1000 or sha256(file.read_bytes()).hexdigest()!=seg.get('sha256'):return []
            out.append({'url':'/council_sessions/'+quote(filename),'role':'council','sequence':i})
        return out
    except (OSError,ValueError,KeyError,TypeError,UnicodeError):return []
    if pilot!='FLOOD':return []  # Only FLOOD has a documented 5-segment recorded Council session.
    folder=Path(root)/'council_sessions'
    manifest=folder/(lang+'_flood_council_manifest.json')
    try:
        data=json.loads(manifest.read_text(encoding='utf8'))
        items=data['segments']
        if data.get('status')!='COMPLETE' or len(items)!=5:return []
        links=[]
        for i,seg in enumerate(items):
            name=seg.get('filename','')
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.mp3',name) or name.startswith('.'):
                return []
            path=folder/name
            if not path.is_file() or path.stat().st_size<1000:return []
            links.append({'url':'/council_sessions/'+quote(name),'role':seg.get('role','speaker'),'sequence':i+1})
        return links
    except (OSError,ValueError,KeyError,TypeError):return []

def generate_pdf(pilot,lang,root=ROOT):
    # RELEASE-117: Same brand language as Live report; pure local PDF generation.
    from pilot_branded_117 import report
    return report(pilot,lang,root)
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from xml.sax.saxutils import escape
    entry=select(pilot,lang)
    root=Path(root)
    out=root/'pilot_reports_115'
    out.mkdir(exist_ok=True)
    path=out/f'TerraCouncil-DEMO-{pilot}-{lang.upper()}-SustainAfrica.pdf'
    font='Helvetica'
    for candidate in [Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]:
        if candidate.is_file():
            try:pdfmetrics.registerFont(TTFont('TC115',str(candidate)));font='TC115';break
            except Exception:pass
    css=getSampleStyleSheet()
    css.add(ParagraphStyle(name='TCHeading',fontName=font,fontSize=17,leading=22,textColor=HexColor('#005E64'),spaceAfter=15))
    css.add(ParagraphStyle(name='TCSection',fontName=font,fontSize=12,leading=17,textColor=HexColor('#005E64'),spaceBefore=15,spaceAfter=7))
    css.add(ParagraphStyle(name='TCBody',fontName=font,fontSize=10,leading=15,spaceAfter=9))
    css.add(ParagraphStyle(name='TCNote',fontName=font,fontSize=9,leading=13,textColor=HexColor('#526b63'),spaceAfter=10))
    p=lambda t,style='TCBody':Paragraph(escape(str(t)).replace('\n','<br/>'),css[style])
    flow=[]
    logo=root/'release_101_modules'/'sustainafrica_logo.jpg'
    if logo.is_file():flow.append(Image(str(logo),width=105,height=35,kind='proportional'))
    flow.append(p('SustainAfrica  |  TerraCouncil AI','TCSection'))
    flow.append(p(entry['title']+' — '+entry['region'],'TCHeading'))
    flow.append(p('DÉMONSTRATION PILOTE · SYNTHÈSE ÉDITORIALE EXPLORATOIRE' if lang=='fr' else 'PILOT DEMONSTRATION · EXPLORATORY EDITORIAL BRIEF','TCNote'))
    flow.append(p(entry['question']))
    flow.append(p('Synthèse pour la décision' if lang=='fr' else 'Decision summary','TCSection'))
    flow.append(p(entry['lead']))
    flow.append(p('Pistes à étudier — non classées' if lang=='fr' else 'Options for investigation — not ranked','TCSection'))
    for i,item in enumerate(entry['options'],1):flow.append(p(str(i)+'. '+item))
    flow.append(p('Limites des preuves' if lang=='fr' else 'Evidence limitations','TCSection'))
    flow.append(p(entry['limits']))

    # RELEASE-116 SCIENCE PDF: candidate data, gaps and protocol, no invented validation.
    registry=json.loads((root/'scientific_116.json').read_text(encoding='utf8'))
    sci=registry['pilots'][pilot]
    flow.append(p('Sources candidates à vérifier' if lang=='fr' else 'Candidate scientific data to verify','TCSection'))
    flow.append(p('Sources non encore admises comme preuves locales.' if lang=='fr' else 'These sources are NOT yet admitted as verified local evidence.','TCNote'))
    for candidate in sci['candidate_sources']:
        flow.append(p(candidate['dataset']+' · '+candidate['provider']+': '+candidate['suggested_variable']+' — '+candidate['status']))
    flow.append(p('Lacunes de preuve / validation terrain' if lang=='fr' else 'Evidence gaps / field verification','TCSection'))
    for gap in sci['evidence_gaps']:
        flow.append(p('• '+gap))
    flow.append(p('Protocole du conseil Meta : Spark → Wonder → Spark' if lang=='fr' else 'Meta Council protocol: Spark → Wonder → Spark','TCSection'))
    flow.append(p('Plan de délibération à exécuter sur le moteur Live ; aucune nouvelle inférence Meta dans ce rapport.' if lang=='fr' else 'Deliberation plan for a subsequent Live-engine run; no new Meta inference was executed for this report.','TCNote'))


    # RELEASE-116B AUTHENTIC PHASES: display only a fingerprint-verified recorded session.
    if audio_segments(pilot,lang,root):
        manifest=json.loads((root/'pilot_audio_116b'/(pilot+'-'+lang+'.json')).read_text(encoding='utf8'))
        source=Path.home()/'Documents'/'TerraCouncil-Scientific-Inputs'/manifest['source_trace']
        trace=json.loads(source.read_text(encoding='utf8'))
        flow.append(p('Délibération Meta enregistrée' if lang=='fr' else 'Authentic recorded Meta Council deliberation','TCSection'))
        for stage in trace['meta_result']['phases']:
            flow.append(p(stage['phase'].replace('_',' ').title()+' · '+stage['model'],'TCSection'))
            flow.append(p(stage['text']))
        flow.append(p('Trace scientifique SHA-256 : ' if lang=='fr' else 'Scientific trace SHA-256: ','TCNote'))
        flow.append(p(manifest['source_trace_sha256'],'TCNote'))

    flow.append(Spacer(1,12))
    flow.append(p('Document préparé à partir de la synthèse pilote déjà enregistrée dans DEMO-054. Aucune nouvelle délibération Meta n’a été exécutée. Vérification locale requise avant toute décision.' if lang=='fr' else 'Prepared from the pilot editorial brief previously recorded in DEMO-054. No new Meta deliberation was executed. Local verification is required before a real-world decision.','TCNote'))
    def page(canvas,doc):
        canvas.saveState()
        w,h=A4
        canvas.setFillColor(HexColor('#005E64'));canvas.rect(0,h-9,w,9,fill=1,stroke=0)
        canvas.setStrokeColor(HexColor('#F3C74D'));canvas.line(38,43,w-38,43)
        canvas.setFont('Helvetica',8);canvas.setFillColor(HexColor('#526b63'))
        canvas.drawString(40,31,'TerraCouncil AI · SustainAfrica · Pilot demonstration')
        canvas.drawRightString(w-40,31,str(doc.page))
        canvas.restoreState()
    SimpleDocTemplate(str(path),pagesize=A4,rightMargin=43,leftMargin=43,topMargin=48,bottomMargin=57,title='TerraCouncil Demo · '+entry['title']).build(flow,onFirstPage=page,onLaterPages=page)
    if not path.is_file() or path.stat().st_size<1100:raise ValueError('PDF verification failed')
    return path

def send(h,code,obj):
    raw=json.dumps(obj,ensure_ascii=False).encode('utf8')
    h.send_response(code);h.send_header('Content-Type','application/json; charset=utf-8')
    h.send_header('Cache-Control','no-store');h.send_header('Content-Length',str(len(raw)));h.end_headers();h.wfile.write(raw)

def handle_get(h):
    q=urlparse(h.path);params=parse_qs(q.query)
    if q.path not in ('/api/release115/status','/api/release115/pdf','/api/release115/pilots'):
        return send(h,404,{'error':'Not found'})
    if q.path.endswith('/pilots'):
        return send(h,200,pilots())
    pilot=params.get('pilot',[''])[0];lang=params.get('lang',[''])[0]
    try:
        entry=select(pilot,lang)
        if q.path.endswith('status'):
            seg=audio_segments(pilot,lang)
            return send(h,200,{'pilot':pilot,'language':lang,'question':entry['question'],
              'audio':seg,'audio_available':bool(seg),'report_available':True,'offline_demo':True})
        file=generate_pdf(pilot,lang)
        return send(h,200,{'pilot':pilot,'language':lang,'url':'/pilot_reports_115/'+quote(file.name),'offline_demo':True})
    except ValueError as exc:return send(h,400,{'error':str(exc)})
    except Exception:return send(h,500,{'error':'Pilot report unavailable; no original record was modified'})
