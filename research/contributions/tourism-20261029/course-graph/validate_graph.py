"""Validate source order, semantic types, coverage, and export consistency."""
import collections,csv,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent
def read(name):return json.loads((R/name).read_text('utf-8-sig'))
g=read('graph.json');nodes={n['id']:n for n in g['nodes']};edges=g['edges'];rows=read('plan-fields.json')
assert len(nodes)==len(g['nodes'])==132
assert sum(n['scope']=='offered_2025_2026' for n in nodes.values())==85
assert sum(n['scope']=='plan_only' for n in nodes.values())==47
assert sum(n['node_type']=='course' for n in nodes.values())==131
assert nodes['102']['node_type']=='research_activity'
assert sum(o['sections'] for n in nodes.values() for o in n['offerings'])==123
assert nodes['BA30064']['name']==nodes['BA30103']['name'] and nodes['BA30064']['scope']!=nodes['BA30103']['scope']
assert nodes['BA30090']['business_types']==['本科'] and nodes['TOUR60007']['business_types']==['研究生']
assert g['statistics']['current_mandatory_prerequisites_verified']==0
keys=set();degree=collections.Counter();dag=collections.defaultdict(list)
for e in edges:
 a,b=e['source'],e['target'];assert a in nodes and b in nodes and a!=b
 assert e['type'] in g['relation_types'] and e['directed']==(e['type'] in ['planned_before','recommended_preparation'])
 assert not e['mandatory'] and not e['credit_equivalence'] and e['reason'] and e['evidence']
 key=(a,b,e['type']);assert key not in keys;keys.add(key)
 if not e['directed']:assert a<b
 for ref in e['evidence']:assert ref['source'] in g['sources'] and ref['locator']
 if e['type']=='planned_before':
  for pid in {r['plan_id'] for r in e['evidence']}:
   left=[r for r in e['evidence'] if r['course']==a and r['plan_id']==pid];right=[r for r in e['evidence'] if r['course']==b and r['plan_id']==pid]
   assert left and right and max(left[0]['terms'])<min(right[0]['terms'])
   for side in left+right:
    placement=next(p for p in nodes[side['course']]['plan_placements'] if p['plan_id']==pid)
    assert side['terms']==placement['numbered_terms'] and side['locator']==placement['locator']
    if side['source'].startswith('PLAN-'):
     actual=next(p for p in rows if p['plan_id']==pid and p['locator']==side['locator']);assert actual['numbered_terms']==side['terms']
    else:assert side['source'].startswith('FIGURE-') and placement['term_source']=='reviewed_curriculum_figure'
  dag[a].append(b)
 degree.update([a,b])
visiting=set();done=set()
def visit(x):
 assert x not in visiting,'Cycle in plan ordering: '+x
 if x in done:return
 visiting.add(x)
 for y in dag[x]:visit(y)
 visiting.remove(x);done.add(x)
for x in nodes:visit(x)
assert all(degree[n] for n in nodes)
for path in g['learning_paths']:
 for a,b in zip(path['course_ids'],path['course_ids'][1:]):
  assert any((e['source']==a and e['target']==b) or (not e['directed'] and {e['source'],e['target']}=={a,b}) for e in edges)
for s in g['sources'].values():
 if s['path'].startswith('source-figures/'):
  p=R/s['path'];assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256']
ET.parse(R/'overview.svg')
page=(R/'index.html').read_text('utf-8');assert '__GRAPH_DATA__' not in page and 'fetch(' not in page
data=page.split('<script id="graph-data" type="application/json">')[1].split('</script>')[0];assert json.loads(data)==g
for file,count in [('nodes.csv',132),('edges.csv',len(edges))]:
 with (R/file).open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==count
for p in R.rglob('*.md'):
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text('utf-8')):
  if '://' not in link and not link.startswith('../') and link!='validation.json':assert (p.parent/link.split('#')[0]).exists(),link
result={'status':'passed','date':'2026-11-19','course_nodes':131,'activity_nodes':1,'offered_course_codes':85,'plan_only_nodes':47,'edges':len(edges),'edge_types':dict(collections.Counter(e['type'] for e in edges)),'hard_prerequisites_verified':0,'checks':['Source-backed same-plan term order and DAG','Distinct codes, activity type, and education levels','Complete 85-code offering coverage, 123 sections, and 47 additional plan entries','All nodes have an explicit relation; all learning paths use existing edges','Figure hashes, parseable SVG/CSV, embedded graph identity, and relative links'],'browser_ui_validation':{'status':'not_completed','reason':'Browser security policy rejected the local file URL; no workaround attempted.'}}
(R/'validation.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'));print(json.dumps(result,ensure_ascii=False))
