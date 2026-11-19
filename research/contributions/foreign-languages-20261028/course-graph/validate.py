import collections,csv,gzip,json,pathlib,re
here=pathlib.Path(__file__).parent;root=here.parent;graph=json.loads((here/'graph.json').read_text('utf-8'));nodes=graph['nodes'];edges=graph['edges'];ids={x['id']for x in nodes}
assert len(ids)==len(nodes)
assert all(e['source']in ids and e['target']in ids and e['source']!=e['target'] for e in edges)
assert all(e['type']in {'suggested_sequence','program_module','topic'}for e in edges)
assert len({(e['source'],e['target'],e['type'],e['label'])for e in edges})==len(edges)
assert all(e['source_url'].startswith('https://github.com/pythonbug225/fudan-course-atlas/') for e in edges)
with (root/'data/program-course-index.csv').open(encoding='utf-8-sig',newline='')as f:program=list(csv.DictReader(f))
classes=json.loads((root/'data/official-classes.json').read_text('utf-8-sig'))
expected={r['课程代码'].strip()for r in program if r['课程代码'].strip()and r['课程名称'].strip()}|{r['课程代码']for r in classes if r.get('课程代码')and r.get('课程名称')}
actual={n['id']for n in nodes if n['kind']=='course'};assert expected==actual
with (here/'edges.csv').open(encoding='utf-8-sig',newline='')as f:csv_edges=list(csv.DictReader(f))
assert csv_edges==edges
viewer=(here/'index.html').read_text('utf-8');embedded=viewer.split('<script type="application/json" id="data">',1)[1].split('</script>',1)[0];assert json.loads(embedded)==graph
files=list((root/'raw/official-programs').glob('*.json.gz'));files=[p for p in files if '目录'not in p.name];assert len(files)==25
found=[]
def walk(v,path):
 if isinstance(v,dict):
  for k,x in v.items():
   if k in ('defaultPreCourses','defaultPreCourseList')and x not in (None,[],{},''):found.append((path,k))
   walk(x,path+'/'+k)
 elif isinstance(v,list):
  for x in v:walk(x,path+'[]')
 elif isinstance(v,str)and ('先修'in v or '前置课程'in v):found.append((path,'text'))
for p in files:
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:walk(json.load(f),p.name)
assert not found,found[:3]
print(json.dumps({'courses':len(actual),'nodes':len(nodes),'edges':len(edges),'source_programs_checked':len(files),'official_prerequisite_claims_found':len(found),'edge_types':dict(collections.Counter(e['type']for e in edges))}))
