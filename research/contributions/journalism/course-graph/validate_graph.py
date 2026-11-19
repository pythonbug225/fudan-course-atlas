import pathlib,json,collections,xml.etree.ElementTree as E,re
R=pathlib.Path(__file__).resolve().parent;O=R if R.name=='course-graph' else R/'course-graph'
g=json.loads((O/'graph.json').read_text(encoding='utf8'));N={n['id']:n for n in g['nodes']};assert len(N)==len(g['nodes'])==285
assert sum(n['scope']=='offering_2025_2026' for n in N.values())==207
assert sum(n['scope']=='program_2026_only' for n in N.values())==78
seen=set();adj=collections.defaultdict(list);degree=collections.Counter()
for e in g['edges']:
 assert e['source'] in N and e['target'] in N and e['source']!=e['target']
 key=(e['source'],e['target'],e['type']);assert key not in seen;seen.add(key)
 assert not e['is_enrollment_prerequisite'] and e['reason'] and e['evidence']
 for v in e['evidence']:
  assert v['source_id'] in g['sources']
  if v.get('figure'):assert (O/v['figure']).is_file()
 if e['directed']:adj[e['source']].append(e['target']);degree[e['target']]+=1
ready=[n for n in N if not degree[n]];count=0
while ready:
 n=ready.pop();count+=1
 for b in adj[n]:
  degree[b]-=1
  if not degree[b]:ready.append(b)
assert count==len(N),'Directed relations unexpectedly contain a cycle'
E.parse(O/'课程关系主线.svg')
text=(O/'课程关系图谱.html').read_text(encoding='utf8');embedded=json.loads(re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',text,re.S)[1]);assert embedded==g
result={'passed':True,'nodes':len(N),'edges':len(g['edges']),'types':dict(collections.Counter(e['type'] for e in g['edges'])),'unique_ids':True,'endpoint_integrity':True,'evidence_references':True,'directed_acyclic':True,'embedded_data_matches':True,'confirmed_hard_prerequisites':0,'isolated_nodes_retained':sum(all(n not in [e['source'],e['target']] for e in g['edges']) for n in N)}
(O/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(result,ensure_ascii=False))
if R!=O:
 import shutil
 shutil.copy2(__file__,O/'validate_graph.py')
