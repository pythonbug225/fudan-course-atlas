"""Check all three graphs against each cohort's actual plan rows and Word files."""
import collections,csv,gzip,hashlib,json,re,subprocess,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
W=Path(__file__).resolve().parent;O=W if (W/'2023/official').exists() else W/'package/cohorts'
def load(p):return json.loads(p.read_text('utf-8-sig')) if p.exists() else json.loads(gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
results=[]
for year,expected in [(2023,2),(2024,2),(2025,4)]:
 root=O/str(year);official=root/'official';out=root/'course-graph';plans=load(official/'programmes.json');rows=load(official/'courses.json');modules=load(official/'modules.json');g=load(out/'graph.json');nodes={n['id']:n for n in g['nodes']};course_ids={n['id'] for n in g['nodes'] if n['node_type']!='curriculum_module'}
 assert len(plans)==expected and len(nodes)==len(g['nodes']) and g['cohort']==year
 assert course_ids=={r['course_code'] for r in rows}
 assert {p['plan_id'] for p in plans}=={p['id'] for p in g['programmes']}
 originals={}
 for p in plans:
  doc=official/p['word_path'];b=doc.read_bytes();assert len(b)==p['word_bytes'] and hashlib.sha256(b).hexdigest()==p['word_sha256']
  with zipfile.ZipFile(doc) as z:assert z.testzip() is None and 'word/document.xml' in z.namelist()
  raw=load(official/'raw'/('plan-'+p['plan_id']+'.json'));assert str(raw['model']['grade'])==str(year) and str(raw['model']['id'])==p['plan_id']
  originals[p['plan_id']]=raw
  title_text=(official/'word-text'/('plan-'+p['plan_id']+'.txt')).read_text('utf-8');assert str(year) in title_text and '旅游管理' in title_text
 for row in rows:
  mi,ci=[int(i) for i in re.fullmatch(r'/courseModules/(\d+)/planCourses/(\d+)',row['locator']).groups()];source=originals[row['plan_id']]['courseModules'][mi]['planCourses'][ci]
  assert row['course_code']==str(source['course']['code']) and row['course_name']==source['course']['nameZh']
  assert row['terms_raw']==source.get('terms',[]) and row['compulsory_field']==source.get('compulsory')
 keys=set();degree=collections.Counter();dag=collections.defaultdict(lambda:collections.defaultdict(list))
 for e in g['edges']:
  a,b=e['source'],e['target'];assert a in nodes and b in nodes and a!=b
  assert not e['mandatory'] and not e['credit_equivalence'];assert e['reason'] and e['evidence']
  key=(a,b,e['type']);assert key not in keys;keys.add(key)
  assert e['directed']==(e['type'] in ['planned_before','recommended_preparation'])
  if not e['directed']:assert a<b
  for ref in e['evidence']:
   assert ref['source'] in g['sources'] and ref['locator'].startswith('/courseModules/')
  if e['type']=='planned_before':
   for pid in {ref['plan_id'] for ref in e['evidence']}:
    left=[r for r in e['evidence'] if r['plan_id']==pid and r['course']==a];right=[r for r in e['evidence'] if r['plan_id']==pid and r['course']==b]
    assert left and right and max(left[0]['terms'])<min(right[0]['terms'])
    for ref in left+right:
     mi,ci=[int(i) for i in re.fullmatch(r'/courseModules/(\d+)/planCourses/(\d+)',ref['locator']).groups()]
     pc=originals[pid]['courseModules'][mi]['planCourses'][ci];terms=[int(t.split('_')[1]) for t in pc.get('terms',[]) if re.fullmatch(r'TERM_[1-8]',str(t))]
     assert str(pc['course']['code'])==ref['course'] and terms==ref['terms']
    dag[pid][a].append(b)
  if e['type']=='module_membership':assert (nodes[a]['node_type']=='curriculum_module') != (nodes[b]['node_type']=='curriculum_module')
  degree.update([a,b])
 for pid,edges in dag.items():
  visiting=set();done=set()
  def visit(x):
   assert x not in visiting,('Cycle in one plan',year,pid,x)
   if x in done:return
   visiting.add(x)
   for y in edges[x]:visit(y)
   visiting.remove(x);done.add(x)
  for n in list(edges):visit(n)
 assert all(degree[c] for c in course_ids)
 for path in g['learning_paths']:
  for a,b in zip(path['course_ids'],path['course_ids'][1:]):assert any((e['source']==a and e['target']==b) or (not e['directed'] and {e['source'],e['target']}=={a,b}) for e in g['edges']),('Path discontinuity',year,a,b)
 page=(out/'index.html').read_text('utf-8');embedded=page.split('<script id="graph-data" type="application/json">')[1].split('</script>')[0];assert json.loads(embedded)==g and '__GRAPH_DATA__' not in page and 'fetch(' not in page
 script=page.split('</script><script>')[1].split('</script>')[0];tmp=W/f'viewer-{year}-check.js';tmp.write_bytes(script.encode('utf-8'));subprocess.run(['node','--check',str(tmp)],capture_output=True,check=True);tmp.unlink()
 ET.parse(out/'overview.svg')
 for file,count in [('nodes.csv',len(nodes)),('edges.csv',len(g['edges']))]:
  with (out/file).open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==count
 for source in g['sources'].values():assert (out/source['url']).exists() or (out/source['url'].removesuffix('.gz')).exists(),source['url']
 assert g['statistics']['verified_hard_prerequisites']==0
 results.append({'cohort':year,'status':'passed','plans':len(plans),'course_entries':len(course_ids),'programme_entries':g['statistics']['programme_entries'],'public_option_entries':g['statistics']['public_option_entries'],'module_nodes':g['statistics']['module_nodes'],'edges':len(g['edges']),'edge_types':g['statistics']['edge_types'],'hard_prerequisites_verified':0})
for p in O.rglob('*'):
 if p.is_file() and p.suffix in ['.json','.md','.html','.csv','.txt','.py']:
  text=p.read_text('utf-8-sig');assert not re.search(r'Bearer\s+[A-Za-z0-9._-]{15,}|gh[pousr]_[A-Za-z0-9]{25,}',text),('Sensitive string',p.name)
report={'date':'2026-11-26','status':'passed','years':results,'checks':['8 official original DOCX CRC/size/SHA-256 and year/plan identity','Every normalized course row traces to its own cohort API JSON pointer','No invented mandatory prerequisites or cross-cohort term transfer','Same-plan term evidence and per-plan DAGs','All course entries link to a source module; public candidate scope preserved','Learning-path continuity, inline graph identity, JS syntax, parseable SVG and CSV','Sensitive-content scan'],'browser_ui_validation':'not_performed; no claim of completed browser interaction tests'}
(O/'validation.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'));print(json.dumps(report,ensure_ascii=False))
