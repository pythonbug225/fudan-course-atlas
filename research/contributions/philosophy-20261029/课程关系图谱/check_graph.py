"""Validate graph coverage, provenance and prerequisite semantics using stdlib only."""
import collections,json,re
from pathlib import Path

D=Path(__file__).resolve().parent
g=json.loads((D/'graph.json').read_text('utf-8'))
nodes={n['id']:n for n in g['nodes']}
assert len(nodes)==len(g['nodes'])==267
assert len({n['name'] for n in nodes.values()})==253
assert set(n['formal_prerequisite_status'] for n in nodes.values())=={'not_established_from_available_sources'}
source_ids={s['id'] for s in g['sources']}
keys=set();adj=collections.defaultdict(list)
for e in g['edges']:
    assert e['source'] in nodes and e['target'] in nodes and e['source']!=e['target']
    key=(e['source'],e['target'],e['kind']);assert key not in keys;keys.add(key)
    assert e['kind'] in g['relation_types']
    assert all(x['source_id'] in source_ids and x['locator'] for x in e['evidence'])
    assert e['rationale'] and not e['is_formal_prerequisite']
    assert e['directed']==g['relation_types'][e['kind']]['directed']
    if e['kind'] in ['official_sequence','official_credit_waiver']:
        assert e['authority']=='official' and e['scope']
        assert any(s['source_id']=='handbook-2026' for s in e['evidence'])
    else:assert e['authority']=='editorial_inference'
    if e['kind'] in ['official_sequence','recommended_preparation']:adj[e['source']].append(e['target'])
assert not any(e['kind']=='formal_prerequisite' for e in g['edges'])
assert {(e['source'],e['target']) for e in g['edges'] if e['kind']=='official_credit_waiver'}=={('PHIL20013h','PHIL10003'),('PHIL20013h','PHIL20013')}
visiting=set();done=set()
def visit(n):
    assert n not in visiting,'Learning-order cycle: '+n
    if n in done:return
    visiting.add(n)
    for to in adj[n]:visit(to)
    visiting.remove(n);done.add(n)
for n in nodes:visit(n)
assert set(n for e in g['edges'] for n in [e['source'],e['target']])==set(nodes),'Every course must be navigable.'
html=(D/'index.html').read_text('utf-8')
embedded=re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',html,re.S).group(1)
assert json.loads(embedded)==g
assert not re.search(r'<script[^>]+src=|https?://[^"\s]+\.(js|css)["\s]',html)
assert '__GRAPH_DATA__' not in html and '__VIEWER_JS__' not in html
assert g['audit']['programme_nonempty_suggested_terms']==0
assert not g['audit']['unresolved_candidates']
base=D.parent
if (base/'summaries/courses.json').exists():
    src=json.loads((base/'summaries/courses.json').read_text('utf-8'))
    assert {c['course_code'] for c in src}==set(nodes)
print(json.dumps({'status':'passed','nodes':len(nodes),'edges':len(g['edges']),'all_courses_navigable':True,'learning_order_acyclic':True,'formal_prerequisites_verified':0},ensure_ascii=False))
