"""Validate coverage, references, relationship semantics, acyclicity and embedded data."""
import collections,csv,gzip,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent;P=R.parent
g=json.loads((R/'graph.json').read_text('utf-8'));nodes={n['id']:n for n in g['nodes']}
assert len(nodes)==len(g['nodes'])==681
offered={p.stem for p in (P/'courses').glob('*.json')}
assert len(offered)==296 and offered=={n['id'] for n in nodes.values() if n['scope']!='plan_only'}
plan_rows=list(csv.DictReader((P/'official/program-courses.csv').open(encoding='utf-8-sig')))
assert {r['课程代码'] for r in plan_rows}|offered==set(nodes)
assert len({e['id'] for e in g['edges']})==len(g['edges'])
assert len({(e['source'],e['target'],e['type']) for e in g['edges']})==len(g['edges'])
adj=collections.defaultdict(list)
for e in g['edges']:
    assert e['source'] in nodes and e['target'] in nodes and e['source']!=e['target']
    assert e['type'] in g['relation_types'] and e['mandatory'] is False
    assert e['directed']==(e['type']!='content_link')
    if e['directed']:adj[e['source']].append(e['target'])
    for ref in e['evidence']:
        source=g['sources'][ref['source']];p=R/source['path'];assert p.exists()
        if ref.get('pointer'):
            v=json.loads(gzip.decompress(p.read_bytes()))
            for part in ref['pointer'].strip('/').split('/'):v=v[int(part)] if isinstance(v,list) else v[part]
            assert v==ref['quote']
    if e['type']=='official_recommendation':
        assert (e['source'],e['target'])==('SWK30011','SWK40006') and len(e['evidence'])==3
    if e['type']=='curriculum_sequence':assert e['basis']=='official_figure_arrow'
state={}
def visit(n):
    assert state.get(n)!=1,'Directed cycle at '+n
    if state.get(n)==2:return
    state[n]=1
    for dest in adj[n]:visit(dest)
    state[n]=2
for n in nodes:visit(n)
for p in g['pathways']:assert all(c in nodes for c in p['course_ids'])
audit=json.loads((R/'source-audit.json').read_text('utf-8'))
assert len(audit['plans_scanned'])==15 and all(r['empty'] for r in audit['prerequisite_fields'])
for p in (R/'source-figures').glob('*.json'):
    m=json.loads(p.read_text('utf-8'));assert hashlib.sha256((p.parent/m['image_file']).read_bytes()).hexdigest()==m['image_sha256']
text=(R/'index.html').read_text('utf-8')
embedded=re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',text,re.S).group(1)
assert json.loads(embedded)==g and '__GRAPH__' not in text
ET.fromstring((R/'专业主线.svg').read_text('utf-8'))
for p in [R/'README.md',R/'index.html']:
    links=re.findall(r'\]\(([^)]+)\)',p.read_text('utf-8')) if p.suffix=='.md' else re.findall(r'(?:href|src)="([^"#]+)"',p.read_text('utf-8').split('<script id=')[0])
    for link in links:
        if not link.startswith(('http:','https:','#')):assert (R/link).exists() or link=='validation.json',link
report={'passed':True,'nodes':len(nodes),'edges':len(g['edges']),'types':dict(collections.Counter(e['type'] for e in g['edges'])),'offering_codes':len(offered),'directed_cycle_count':0,'official_text_pointers_verified':3,'plans_scanned':15,'empty_prerequisite_field_instances':len(audit['prerequisite_fields']),'unmapped_offering_codes':[n['id'] for n in nodes.values() if n['scope']!='plan_only' and n['relationship_status']=='needs_syllabus']}
(R/'validation.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(report))
