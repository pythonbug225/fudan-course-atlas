"""Validate course identity, relation semantics and original source pointers."""
from pathlib import Path
import collections
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text('utf-8-sig'))
g=read(HERE/'graph.json');rules=read(HERE/'rules.json');audit=read(HERE/'source-audit.json')
off=read(HERE.parent/'2026-10-30/report/history-research/official/历史学课程清单.json')
nodes={n['id']:n for n in g['nodes']};edges=g['edges'];sources={s['id']:s for s in g['sources']}
assert len(nodes)==249 and set(nodes)=={r['课程代码'] for r in off}
assert len({n['name'] for n in nodes.values()})==247
for code,n in nodes.items():
    rows=[r for r in off if r['课程代码']==code]
    assert set(n['names'])=={r['课程名称'] for r in rows}
    assert set(n['levels'])=={r['课程层次'] for r in rows}
    assert set(n['teachers'])=={t for r in rows for t in r['教师']}
assert len({(e['source'],e['target'],e['type']) for e in edges})==len(edges)
adj=collections.defaultdict(list);degree=collections.Counter()
def pointer(obj,p):
    for part in p.strip('/').split('/'):
        obj=obj[int(part)] if isinstance(obj,list) else obj[part]
    return obj
for e in edges:
    assert e['source'] in nodes and e['target'] in nodes and e['source']!=e['target']
    assert e['directed']==(e['type']=='recommended_prerequisite')
    assert not e['is_enrollment_requirement'] and e['reason'] and e['scope']
    assert set(e['source_refs'])<=sources.keys()
    if e['rule_pointer'].startswith('/'):
        pointer(rules,e['rule_pointer'])
    if e['directed']:adj[e['source']].append(e['target'])
    degree.update([e['source'],e['target']])
    for support in e['plan_order_support']:
        plan=read(HERE/sources[support['source_ref']]['path'])
        left,right=pointer(plan,support['source_pointer']),pointer(plan,support['target_pointer'])
        assert left['course']['code']==e['source'] and right['course']['code']==e['target']
        assert support['source_terms']==sorted(int(t[5:]) for t in left['terms'])
        assert support['target_terms']==sorted(int(t[5:]) for t in right['terms'])
        assert max(support['source_terms'])<min(support['target_terms'])
visiting,done=set(),set()
def visit(code):
    assert code not in visiting,'Recommended order contains a cycle'
    if code in done:return
    visiting.add(code)
    for target in adj[code]:visit(target)
    visiting.remove(code);done.add(code)
for code in nodes:visit(code)
for n in nodes.values():assert n['relation_count']==degree[n['id']]
for p in g['paths']:
    assert all(any(e['source']==a and e['target']==b and e['directed'] for e in edges) for a,b in zip(p['codes'],p['codes'][1:]))
for p in audit['input_files']:
    assert hashlib.sha256((HERE.parent/p['path']).read_bytes()).hexdigest()==p['sha256']
for source in sources.values():assert (HERE/source['path']).is_file()
assert g['stats']['nodes_with_relations']==sum(bool(degree[c]) for c in nodes)
assert not any(e['type']=='official_prerequisite' for e in edges)
assert all(not p['nonempty_prerequisite_fields'] and not p['word_keyword_hits'] for p in audit['programs'])
assert len(list(csv.DictReader((HERE/'nodes.csv').open(encoding='utf-8-sig'))))==249
assert len(list(csv.DictReader((HERE/'relations.csv').open(encoding='utf-8-sig'))))==len(edges)
page=(HERE/'index.html').read_text('utf-8')
embedded=re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',page,re.S).group(1)
assert json.loads(embedded)==g
assert '法学院' not in page and 'LAW10001' not in page
ET.parse(HERE/'overview.svg')
print(json.dumps(dict(verification='passed',nodes=len(nodes),edges=len(edges),recommended_order_acyclic=True,source_hashes_and_pointers_verified=True,embedded_data_matches=True),ensure_ascii=False))
