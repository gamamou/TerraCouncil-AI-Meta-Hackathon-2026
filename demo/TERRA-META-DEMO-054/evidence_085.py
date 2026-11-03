#!/usr/bin/env python3
"""TerraCouncil universal LOCAL evidence inventory/retrieval. Not a truth validator or Meta executor."""
import argparse, hashlib, json, re, unicodedata
from pathlib import Path

ALLOWED={'.json','.jsonl','.geojson','.csv','.md','.txt'}
MAX_BYTES=6_000_000
BANNED=('secret','credential','token','password','api_key','.env','private_key','node_modules','__pycache__','-backups','/backups/','\\backups\\')
STOP={'what','which','where','with','from','pour','dans','avec','quels','quelle','quelles','comment','sont','have','the','and','des','les','une','sur','est','que','qui','par','notre','nous','faut','cette','this','are','can','du','de','la','le','un','en','et','au','aux','a','to','is','of'}
SYN={'flood':{'flood','flooding','inondation','inondations','crue','crues'},'mine':{'mine','mining','mines','minier','miniere','bauxite'},'water':{'water','eau','hydro','hydrologie'},'climate':{'climat','climate','climatique'},'agriculture':{'agriculture','agricole','crop','cultures'},'population':{'population','communautes','communities'}}
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))
def tokens(s):return {w for w in re.findall(r'[a-z0-9]{3,}',norm(s)) if w not in STOP}
def expand(tt):
    result=set(tt)
    for words in SYN.values():
        if tt & words:result |= words
    return result

def safe_file(p,root):
    try:
        rp=p.resolve(strict=True)
        rp.relative_to(root.resolve(strict=True))
        if not rp.is_file() or rp.suffix.lower() not in ALLOWED or rp.stat().st_size>MAX_BYTES:return False
        components=[norm(x) for x in p.parts]
        if any(any(b in x for b in BANNED) for x in components):return False
        return True
    except (OSError,ValueError):return False

def compact_json(obj,limit=7000):
    # only strings and scalar labels, bounded to avoid consuming large geospatial coordinate arrays
    parts=[]
    def walk(x,depth=0):
        if len(' '.join(parts))>limit or depth>5:return
        if isinstance(x,dict):
            for k,v in list(x.items())[:100]:
                if norm(k) in ('coordinates','geometry','features','password','token','api_key','secret'):continue
                parts.append(str(k)[:80]);walk(v,depth+1)
        elif isinstance(x,list):
            for v in x[:20]:walk(v,depth+1)
        elif isinstance(x,(str,int,float,bool)): parts.append(str(x)[:500])
    walk(obj)
    return ' '.join(parts)[:limit]

def inventory(roots):
    records=[];warnings=[];seen=set()
    for root in roots:
        root=Path(root).expanduser()
        if not root.is_dir():warnings.append({'root':str(root),'reason':'missing_root'});continue
        for p in root.rglob('*'):
            if not safe_file(p,root):continue
            try:
                rp=p.resolve()
                if rp in seen:continue
                seen.add(rp)
                raw=rp.read_bytes()
                if b'\x00' in raw[:1000]:continue
                text=raw.decode('utf-8-sig',errors='replace')
                if rp.suffix.lower() in ('.json','.geojson'):
                    try:text=compact_json(json.loads(text))
                    except (ValueError,TypeError):warnings.append({'file':str(rp),'reason':'bad_json'});continue
                else:text=text[:7000]
                # never return file contents to end user by default: small excerpt for human review only
                records.append({'id':hashlib.sha256(str(rp).encode()).hexdigest()[:16],
                    'path':str(rp),'root':str(root.resolve()),'name':rp.name,
                    'file_sha256':hashlib.sha256(raw).hexdigest(), 'bytes':len(raw),
                    'search_text':text[:7000], 'status':'CANDIDATE_UNREVIEWED',
                    'source_type':rp.suffix.lower()})
            except (OSError,UnicodeError) as e:
                warnings.append({'file':str(p),'reason':type(e).__name__})
    return records,warnings

def find(records,question,limit=12):
    q=expand(tokens(question))
    ranked=[]
    for item in records:
        name_tokens=expand(tokens(item['name']))
        body_tokens=tokens(item['search_text'])
        overlap=q & (name_tokens|body_tokens)
        if not overlap:continue
        score=3*len(q&name_tokens)+len(q&body_tokens)
        ranked.append({'id':item['id'],'name':item['name'],'path':item['path'],
            'sha256':item['file_sha256'],'match_terms':sorted(overlap),
            'score':score,'status':'CANDIDATE_UNREVIEWED',
            'warning':'Matching terms do not establish admissibility, geographical coverage, or scientific accuracy.'})
    return sorted(ranked,key=lambda x:(-x['score'],x['path']))[:limit]

def run(roots,question):
    if len(question.strip())<12 or len(question)>3000:raise ValueError('Question must be between 12 and 3000 characters')
    rows,warnings=inventory(roots)
    candidates=find(rows,question)
    return {'schema':'terra-universal-evidence-candidates/1.0','question':question,
        'roots':[str(Path(r).expanduser()) for r in roots],
        'inventory_count':len(rows),'candidate_count':len(candidates),'candidates':candidates,
        'unavailable_roots_or_files':warnings[:100],
        'scientific_gate':'HUMAN_OR_DETERMINISTIC_ADMISSIBILITY_REVIEW_REQUIRED',
        'live_meta_executed':False,'audio_generated':False,'pdf_generated':False,'api_calls':0,
        'ready_for_meta':False,
        'reason':'File retrieval alone is not adequate evidence selection. Validate source, coverage, units, and relevance before agent calls.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',action='append',required=True)
    ap.add_argument('--question',required=True);ap.add_argument('--output',required=True)
    a=ap.parse_args();p=Path(a.output)
    if p.exists():ap.error('Refusing to overwrite output')
    result=run(a.root,a.question)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('FINAL-085 INDEXED',result['inventory_count'],'FILES / CANDIDATES',result['candidate_count'],
          '/ SCIENTIFIC REVIEW REQUIRED / META 0 / TTS 0')
    print('REPORT',p)
if __name__=='__main__':main()
