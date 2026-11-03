"""Generate a genuine-source-grounded narrated council session with ElevenLabs.
Editorial moderator, faithfully condensed scientific interventions; source always retained.
"""
import argparse,json,hashlib,os,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).parent
TRACE_DIR=Path.home()/"Documents"/"TerraCouncil-Scientific-Inputs"
SPEAKERS=['moderator','spark','wonder','spark','moderator']
FIELDS=['','position','critique','revised_position','']
def source(path):
 raw=Path(path).read_bytes();x=json.loads(raw.decode('utf-8-sig'))
 if x.get('mode')!='LIVE_META_PEER_REVIEW' or x.get('pilot')!='FLOOD' or x.get('status') not in ('PROVISIONAL_HUMAN_REVIEW','ABSTAIN_INSUFFICIENT_EVIDENCE'):
  raise ValueError('Requires authentic DEMO-048 FLOOD peer review')
 steps=x.get('steps') or []
 if [(s.get('stage'),s.get('model'),s.get('authentic')) for s in steps]!=[
  ('spark_initial','muse-spark-1.3',True),('wonder_review','muse-wonder-1.0',True),('spark_revision','muse-spark-1.3',True)]:
  raise ValueError('Three authentic Spark-Wonder-Spark stages required')
 return x,hashlib.sha256(raw).hexdigest()

# Scientifically faithful authored oral adaptation anchored to actual statement fields.
# Validates named source assertions before use; does NOT impersonate extra model calls.
SCRIPTS={
 'fr':[
 ('moderator',"Bienvenue à cette séance de TerraCouncil consacrée aux inondations à Gaoual et à Kankan, en Guinée. Notre conseil examine deux indicateurs scientifiques partiels et cherche à déterminer quelles solutions méritent une étude approfondie. Écoutons d'abord Spark, puis la revue critique indépendante de Wonder."),
 ('spark',"Les données disponibles donnent, pour Gaoual, environ cinq cent quatre-vingt-cinq personnes-équivalentes par an, et pour Kankan, environ mille cinq cent trente-neuf, dans une mesure partielle de l'exposition attendue aux crues de périodes de retour de dix à cinq cents ans. Ces chiffres ne représentent ni le total des personnes exposées, ni des victimes, ni des dommages. Ils n'ont pas été recalculés localement. Nous devons donc étudier, sans les classer ni promettre leur efficacité, les alertes précoces, l'aménagement du territoire, les ouvrages de drainage, les solutions fondées sur la nature et la protection des bâtiments."),
 ('wonder',"L'interprétation prudente de Spark est justifiée, mais les options restent trop générales. Nous ignorons quels types de crues touchent les populations, leur profondeur et leur durée. Les événements plus fréquents que ceux du périmètre étudié n'y figurent pas. Il faut aussi examiner les coûts, l'entretien, l'accès aux alertes pour les groupes vulnérables, les risques de déplacement et les effets transférés vers d'autres communautés. Pour chaque solution, je recommande un protocole d'évaluation local et des critères explicites avant tout projet pilote."),
 ('spark',"Je retiens ces remarques. Mon analyse initiale ne suffit pas à recommander des investissements. Nous devons vérifier la modélisation des aléas, la population exposée, les limites géographiques, les incertitudes et les crues hors de la plage étudiée. Les cinq familles de solutions demeurent des pistes de recherche, sans classement entre Gaoual et Kankan. Leur pertinence exigera des analyses de faisabilité, d'équité, de maintenance et de suivi des effets."),
 ('moderator',"La séance montre comment une revue critique peut renforcer le raisonnement scientifique. Spark a formulé des pistes, Wonder en a identifié les limites, puis Spark a révisé sa position. Aucune solution n'est déclarée efficace ou prête à déployer. Le conseil recommande une vérification locale et une revue humaine avant toute décision. Merci d'avoir suivi TerraCouncil.")
 ],
 'en':[
 ('moderator',"Welcome to TerraCouncil's scientific session on flooding in Gaoual and Kankan, Guinea. The council will examine two partial scientific exposure indicators and discuss which resilience strategies deserve further investigation. Spark will first present an assessment, Wonder will review it independently, and Spark will respond."),
 ('spark',"The documented figures are approximately five hundred and eighty-five person-equivalents per year for Gaoual and fifteen hundred and thirty-nine for Kankan, within a partial expected flood-exposure measure covering return periods from ten to five hundred years. These are not total exposure, casualties, or damages, and they have not been recomputed locally. We should investigate early warning, land-use planning, drainage, nature-based retention and building resilience. We cannot rank the locations or claim these approaches would work here."),
 ('wonder',"Spark's cautious interpretation is sound, but the proposed options remain too generic. We lack information about flood mechanisms, depth, duration and frequent events outside the partial indicator's range. We also need to investigate maintenance, cost, equitable warning access, possible displacement and risk transferred to other communities. Each candidate intervention needs locally appropriate evidence, evaluation criteria and a defensible study design before any pilot."),
 ('spark',"I accept Wonder's qualification. The current evidence is insufficient to recommend investments or rank Gaoual against Kankan. We first need to validate hazard modelling, exposed populations, geographic boundaries, uncertainty and events outside the measured range. The five strategy families remain research options, not validated local solutions. Feasibility, equity, maintenance and monitoring must be assessed before advancing."),
 ('moderator',"The council has demonstrated a real scientific review: Spark proposed an interpretation, Wonder tested its limitations, and Spark revised its position. No intervention has been shown to be locally effective or ready for deployment. Local validation and human review remain essential. Thank you for joining TerraCouncil.")
 ]}
def check_source(trace):
 blob=json.dumps(trace['steps'],ensure_ascii=False).lower()
 for term in ['585.433','1539.107','rp10','rp500','equity','maintenance']:
  if term not in blob:raise ValueError('Required factual anchor absent from real trace: '+term)
 for s in trace['steps']:
  if not s.get('response'):raise ValueError('Missing authentic model response')
def build(trace_path,language):
 tr,digest=source(trace_path);check_source(tr)
 items=[]
 for i,(speaker,spoken) in enumerate(SCRIPTS[language]):
  step=None if i in (0,4) else i-1
  items.append({'index':i,'speaker':speaker,'role':'EDITORIAL_MODERATOR' if speaker=='moderator' else 'EDITORIALLY_ADAPTED_AUTHENTIC_AGENT',
    'text':spoken,'language':language,'source_stage':None if step is None else tr['steps'][step]['stage'],
    'source_model':None if step is None else tr['steps'][step]['model'],
    'text_sha256':hashlib.sha256(spoken.encode()).hexdigest(),
    'filename':f'{language}_flood_council_{i:02d}_{speaker}.mp3'})
 return {'status':'PENDING_AUDIO','pilot':'FLOOD','language':language,
   'trace_sha256':digest,'trace_filename':Path(trace_path).name,
   'adaptation':'editorial_condensation_not_verbatim','segments':items}
def synthesize(text,voice,key):
 body=json.dumps({'text':text,'model_id':'eleven_multilingual_v2',
   'voice_settings':{'stability':0.42,'similarity_boost':0.78,'style':0.28,'use_speaker_boost':True}}).encode()
 request=urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/'+voice+'?output_format=mp3_44100_128',
   data=body,method='POST',headers={'xi-api-key':key,'Content-Type':'application/json','Accept':'audio/mpeg'})
 with urllib.request.urlopen(request,timeout=120) as response:audio=response.read()
 if len(audio)<1000:raise ValueError('Unexpected ElevenLabs response')
 return audio

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--trace',help='Authentic DEMO-048-FLOOD-LIVE JSON')
 p.add_argument('--language',choices=['fr','en'],default='fr')
 p.add_argument('--preview',action='store_true')
 p.add_argument('--generate',action='store_true')
 args=p.parse_args()
 if args.preview==args.generate:p.error('Choose --preview or --generate')
 sourcepath=Path(args.trace) if args.trace else next(iter(sorted(TRACE_DIR.glob('DEMO-048-FLOOD-LIVE-*.json'),reverse=True)),None)
 if not sourcepath:p.error('Authentic DEMO-048 FLOOD live trace missing')
 manifest=build(sourcepath,args.language)
 folder=ROOT/'council_sessions';folder.mkdir(exist_ok=True)
 if args.generate:
  key=os.environ.get('ELEVENLABS_API_KEY')
  voices={k:os.environ.get('ELEVENLABS_'+k.upper()+'_VOICE_ID') for k in ['moderator','spark','wonder']}
  if not key or any(not v for v in voices.values()):p.error('Set ELEVENLABS_API_KEY and ELEVENLABS_MODERATOR_VOICE_ID / ELEVENLABS_SPARK_VOICE_ID / ELEVENLABS_WONDER_VOICE_ID')
 for segment in manifest['segments']:
  print(f"{segment['index']+1}/5 {segment['speaker'].upper()}: {segment['text']}")
  if args.generate:
   target=folder/segment['filename']
   if target.exists() and target.stat().st_size>1000:print('EXISTS:',target);continue
   data=synthesize(segment['text'],voices[segment['speaker']],key)
   with target.open('xb') as f:f.write(data)
   print('GENERATED:',target,'BYTES:',len(data))
 if args.generate:
  manifest['status']='COMPLETE' if all((folder/x['filename']).exists() for x in manifest['segments']) else 'INCOMPLETE'
  manifest_file=folder/f'{args.language}_flood_council_manifest.json'
  manifest_file.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
  print('SESSION_MANIFEST:',manifest_file)
 else:print('PREVIEW_ONLY: ZERO_ELEVENLABS_CALLS')
if __name__=='__main__':main()
