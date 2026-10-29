"""Validate the Law contribution and its publication manifest with the Python standard library."""
import hashlib,json,re
from collections import Counter
from pathlib import Path

B=Path(__file__).resolve().parent
def read(path):return json.loads((B/path).read_text(encoding='utf-8'))
def key(s):return (s['term'],s['course_code'],s['section_code'],s['course_level'],tuple(sorted(s['teachers'])))
sections=read('official/sections.json');programs=read('official/programs.json');evidence=read('summaries/evidence.json');ids=read('ledgers/fulltext-reading-ids.json')
assert len(sections)==369 and len({key(s) for s in sections})==369
assert Counter(s['term'] for s in sections)=={'2025秋':174,'2026春':195}
assert Counter(s['course_level'] for s in sections)=={'本科':136,'研究生':216,'本研融通':17}
assert len({t for s in sections for t in s['teachers']})==124
assert len(programs)==8 and len({p['方案编号'] for p in programs})==8
assert all(p['年级']=='2026' and p['院系编号']==2565 and re.fullmatch('[a-f0-9]{64}',p['SHA256']) for p in programs)
assert read('official/program-verification.json')['核验通过数']==8
assert len(ids['forum_floor_ids'])==len(set(ids['forum_floor_ids']))==6779
assert len(ids['danke_review_ids'])==len(set(ids['danke_review_ids']))==71
assert 4583713 not in ids['forum_floor_ids'],'partially read floor must not count as full text'
full_floors=set(ids['forum_floor_ids']);full_reviews=set(ids['danke_review_ids'])
assert len(evidence)==223
by_source={e['source_id']:e for e in evidence};assert len(by_source)==223
for e in evidence:
 assert e['confirmed_section_keys']==[]
 assert e['mapping_status']=='candidate_unconfirmed_section'
 assert e['fulltext_permission']=='fulltext_not_published_summary_only'
 if e['reading_status']=='full_visible_floor_text_read':assert set(e['source_floor_ids'])<=full_floors
 if e['reading_status']=='full_review_text_read':assert set(e['source_review_ids'])<=full_reviews
 assert not {'content','raw_body','author_id','username','user_id'}&e.keys()
official={key(s):s for s in sections};seen=[]
files=list((B/'courses').glob('*.json'));assert len(files)==260
for p in files:
 c=json.loads(p.read_text(encoding='utf-8'));course=c['course'];assert p.stem==course['code']
 assert course['program_year'] is None,'cohort-to-course membership must not be inferred'
 assert c['progress']['status']=='partial_external_sources'
 for s in course['sections']:
  assert s==official[key(s)] and s['course_code']==course['code'];seen.append(key(s))
 for src in c['sources']:
  assert src['source_id'] in by_source and course['code'] in by_source[src['source_id']]['course_codes']
  assert src['confirmed_section_keys']==[]
 for m in c['materials']:
  if m.get('path'):assert (p.parent/m['path']).is_file(),m['path']
 assert set(c['comparison_and_summary']['source_ids'])<=by_source.keys()
assert Counter(seen)==Counter(official.keys())
queries=read('ledgers/search-queries.json');assert len(queries)==3550
assert Counter(q['status'] for q in queries if q['service']=='forum')=={'completed':1772,'truncated':3}
assert Counter(q['status'] for q in queries if q['service']=='danke')=={'completed':1775}
for p in B.glob('*.md'):
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  if not link.startswith(('http://','https://','#')):assert (p.parent/link).exists(),(p.name,link)
forbidden={'password','access_token','refresh_token','authorization','cookie','jwt','observed_tabs','browser_events','student_id','browser_profile','session_cookie'}
def check_fields(value,path):
 if isinstance(value,dict):
  for k,v in value.items():
   assert k.lower() not in forbidden,(path,k)
   check_fields(v,path)
 elif isinstance(value,list):
  for v in value:check_fields(v,path)
for p in B.rglob('*.json'):check_fields(json.loads(p.read_text(encoding='utf-8')),str(p.relative_to(B)))
manifest=read('manifest.json');actual={p.relative_to(B).as_posix() for p in B.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts}
assert {f['path'] for f in manifest['files']}==actual
for f in manifest['files']:
 p=B/f['path'];assert p.stat().st_size==f['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256']
print(json.dumps({'status':'passed','programs':len(programs),'courses':len(files),'sections':len(sections),'evidence':len(evidence),'files_hashed':len(manifest['files']),'forum_full_floor_ids':len(full_floors),'danke_full_review_ids':len(full_reviews)},ensure_ascii=False))
