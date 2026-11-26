"""Check source coverage, raw locators, edge meaning and original-file integrity."""
import collections,csv,gzip,hashlib,json,re,sys,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
W=Path(__file__).resolve().parent;O=W if (W/'2023/official').exists() else W/'package/cohorts'
def load(p):
 return json.loads(p.read_text('utf-8-sig')) if p.exists() else json.loads(gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
def pointer(d,p):
 for k in p.strip('/').split('/'):
  k=k.replace('~1','/').replace('~0','~');d=d[int(k)] if isinstance(d,list) else d[k]
 return d
reports=[]
for year,expected in [(2023,7),(2024,11),(2025,18)]:
 root=O/str(year);official=root/'official';plans=load(official/'programmes.json');graph=load(root/'course-graph/graph.json');rows=load(official/'courses.json');modules=load(official/'modules.json');coverage=load(official/'coverage.json')
 assert len(plans)==expected==coverage['downloaded_originals']==coverage['department_plans']
 departments=load(official/'raw/directory-department-2581.json');directory={str(r['ID']) for page in departments for r in page['response']['data']};assert directory=={p['plan_id'] for p in plans}
 full=load(official/'raw/directory-all.json');assert directory=={str(r['ID']) for page in full for r in page['response']['data'] if r.get('DEPART_IDS')==2581}
 assert sum(len(p['response']['data']) for p in full)==coverage['directory_total']
 raw={p['plan_id']:load(official/'raw'/f'plan-{p["plan_id"]}.json') for p in plans}
 nodes={n['id']:n for n in graph['nodes']};assert len(nodes)==len(graph['nodes']);courses={k:n for k,n in nodes.items() if n['scope']!='module'};byplacement=collections.defaultdict(list)
 assert len(courses)==graph['statistics']['course_entries'];assert set(courses)=={r['course_code'] for r in rows}
 assert sum(n['scope']=='programme' for n in courses.values())==graph['statistics']['programme_entries']
 assert len([n for n in nodes.values() if n['scope']=='module'])==graph['statistics']['module_nodes']
 for p in plans:
  pid=p['plan_id'];d=raw[pid];assert str(d['model']['grade'])==str(year) and str(d['model']['id'])==pid and d['model']['department']['id']==2581
  word=official/p['word_path'];assert word.stat().st_size==p['word_bytes'];assert hashlib.sha256(word.read_bytes()).hexdigest()==p['word_sha256']
  with zipfile.ZipFile(word) as z:
   assert z.testzip() is None
   xml=ET.fromstring(z.read('word/document.xml'));text=''.join(t.text or '' for t in xml.iter() if t.tag.endswith('}t'))
   assert str(year) in text and '数学' in text;assert (official/'word-text'/f'plan-{pid}.txt').read_text('utf-8')==text
   for image in p['images']:assert z.read(image['member'])==(official/image['path']).read_bytes() and hashlib.sha256(z.read(image['member'])).hexdigest()==image['sha256']
  expectedrows=sum(1 for m in d['courseModules'] for pc in m.get('planCourses',[]) if pc.get('course',{}).get('code') and pc.get('course',{}).get('nameZh'))
  assert sum(r['plan_id']==pid for r in rows)==expectedrows
 for r in rows:
  pc=pointer(raw[r['plan_id']],r['locator']);assert pc['course']['code']==r['course_code'] and pc['course']['nameZh']==r['course_name'];assert pc.get('terms',[])==r['terms_raw']
  n=nodes[r['course_code']];assert r['course_name'] in n['name_variants'];assert r['plan_id'] in n['programmes'];assert nodes[r['module_id']]['node_type']=='curriculum_module'
  byplacement[(r['course_code'],r['plan_id'])].append(r)
 assert len({e['id'] for e in graph['edges']})==len(graph['edges']);assert graph['statistics']['edge_types']==dict(collections.Counter(e['type'] for e in graph['edges']))
 for e in graph['edges']:
  a,b=e['source'],e['target'];assert a in nodes and b in nodes and a!=b;assert not e['mandatory'] and not e['credit_equivalence'];assert e['evidence'] and e['type'] in graph['relation_types']
  assert set(e['shared_plan_ids'])<=set(nodes[a]['programmes'])&set(nodes[b]['programmes'])
  for ref in e['evidence']:
   assert ref['source'] in graph['sources']
   if ref['source'].startswith('PLAN-'):pointer(raw[ref['source'].split('-')[1]],ref['locator'])
   else:assert ref['source']=='HANDBOOK-2024' and ref.get('pdf_pages') and all(1<=p<=217 for p in ref['pdf_pages'])
  if e['type']=='planned_before':
   for pid in e['shared_plan_ids']:
    left=[t for r in byplacement[a,pid] for t in r['numbered_terms']];right=[t for r in byplacement[b,pid] for t in r['numbered_terms']];assert left and right and max(left)<min(right)
  if e['type']=='historical_preparation':assert any(r['source']=='HANDBOOK-2024' for r in e['evidence'])
  if e['type']=='module_membership':assert nodes[a]['scope']=='module' or nodes[b]['scope']=='module'
 # Each exact source membership must have an edge and its raw locator.
 membership={(e['source'],e['target']) if nodes[e['target']]['scope']=='module' else (e['target'],e['source']) for e in graph['edges'] if e['type']=='module_membership'}
 assert membership=={(r['course_code'],r['module_id']) for r in rows}
 for path in graph['learning_paths']:
  pid=path['plan_id'];assert all(pid in nodes[c]['programmes'] for c in path['course_ids'])
  for a,b in zip(path['course_ids'],path['course_ids'][1:]):assert any((e['source']==a and e['target']==b or not e['directed'] and {e['source'],e['target']}=={a,b}) and pid in e['shared_plan_ids'] for e in graph['edges'])
 for name,count in [('nodes',len(nodes)),('edges',len(graph['edges']))]:
  with (root/f'course-graph/{name}.csv').open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==count
 ET.parse(root/'course-graph/overview.svg')
 viewer=(root/'course-graph/index.html').read_text('utf-8');embedded=re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',viewer,re.S).group(1);assert json.loads(embedded)==graph
 for p in root.rglob('*.html'):
  for target in re.findall(r'(?:href|src)="([^"]+)"',p.read_text('utf-8')):
   if '${' in target or target.startswith(('http:','https:','#','data:')) or not target:continue
   assert (p.parent/target.split('#')[0]).exists(),(p,target)
 reports.append({'cohort':year,'plans':len(plans),'word_originals_verified':len(plans),'raw_course_rows_verified':len(rows),'module_records':len(modules),'nodes':len(nodes),'edges':len(graph['edges']),'learning_paths':len(graph['learning_paths']),'passed':True})
handbook=load(O/'sources/handbook-course-requirements.json');assert len(handbook['courses'])==68;assert hashlib.sha256((O/'sources/math-handbook-2024.pdf').read_bytes()).hexdigest()==handbook['sha256']
for p in O.rglob('*'):
 if p.is_file():assert p.suffix not in ['.har','.pem','.key','.pyc'] and '__pycache__' not in p.parts
manifest=O/'manifest.json'
if '--check' in sys.argv:
 m=load(manifest);assert {r['path'] for r in m['records']}=={p.relative_to(O).as_posix() for p in O.rglob('*') if p.is_file() and p.name!='manifest.json'}
 for r in m['records']:
  b=(O/r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
result={'passed':True,'cohorts':reports,'checks':['official department directory equals downloaded plan IDs','cohort/model/department identity','Word ZIP CRC and SHA-256','Word media byte equality','raw JSON course pointers and complete row coverage','module membership completeness','plan-specific numeric term ordering','relation provenance and nonmandatory labels','learning path continuity','CSV row counts','SVG XML','embedded graph JSON equality','relative HTML links','68 syllabus index and handbook SHA-256'],'browser_interaction_verified':False,'hard_prerequisite_enforcement_verified':False}
if '--check' not in sys.argv:(O/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(result,ensure_ascii=False))
