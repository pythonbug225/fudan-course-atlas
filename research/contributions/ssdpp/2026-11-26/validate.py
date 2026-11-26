"""Validate cohort/source boundaries, evidence pointers, graph cycles and files."""
import collections,gzip,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
report={'passed':True,'cohorts':[],'checks':['directory_total_and_department_match','all_plan_ids_and_cohorts','all_node_course_coverage','all_edge_evidence_pointers','directed_edges_same_plan','directed_acyclic','html_embedded_data','svg_xml','source_image_sha256','annual_pdf_full_code_coverage','annual_pdf_excerpt_sha256','sensitive_fields_redacted']}
for year in [2023,2024,2025]:
    root=R/str(year);official=root/'official';out=root/'course-graph';g=load(out/'graph.json');nodes={n['id']:n for n in g['nodes']};plans=load(official/'programmes.json');rows=load(official/'courses.json')
    allrows=[r for page in load(official/'raw/directory-all.json.gz') for r in page['response']['data']];dept=[r for page in load(official/'raw/directory-department-2567.json.gz') for r in page['response']['data']]
    assert {str(r['ID']) for r in dept}=={str(r['ID']) for r in allrows if r['DEPART_IDS']==2567}=={p['plan_id'] for p in plans}
    for typ,count in [('all',len(allrows)),('department-2567',len(dept))]:
        for page in load(official/f'raw/directory-{typ}.json.gz'):
            total=page['response'].get('_page_',{}).get('totalRows')
            if total is not None:assert count==int(total)
    for p in plans:
        d=load(official/p['detail_path']);assert str(d['model']['grade'])==str(year) and str(d['model']['id'])==p['plan_id']
        def privacy(v):
            if isinstance(v,dict):
                for k,z in v.items():
                    if re.fullmatch(r'telephone|phone|mobile|email|emailAddress|password|passwd|token|accessToken|refreshToken|cookie|authorization|idCard|idCardNo|studentNo|loginName',k,re.I):assert z is None
                    privacy(z)
            elif isinstance(v,list):
                for z in v:privacy(z)
        privacy(d)
        for im in p['images']:assert hashlib.sha256((official/im['path']).read_bytes()).hexdigest()==im['sha256']
    assert len(nodes)==len(g['nodes']) and set(nodes)=={r['course_code'] for r in rows}
    assert all(n['cohort']==year for n in nodes.values())
    assert len({e['id'] for e in g['edges']})==len(g['edges'])
    assert len({(e['source'],e['target'],e['type']) for e in g['edges']})==len(g['edges'])
    adj=collections.defaultdict(set)
    for e in g['edges']:
        a,b=e['source'],e['target'];assert a in nodes and b in nodes and a!=b
        assert e['mandatory'] is False and e['directed']==(e['type']!='content_link')
        common={p['plan_id'] for p in nodes[a]['programs']}&{p['plan_id'] for p in nodes[b]['programs']}
        assert set(e['applicable_plan_ids'])<=common
        if e['directed']:assert e['applicable_plan_ids'];adj[a].add(b)
        for ev in e['evidence']:
            source=g['sources'][ev['source']];f=out/source['path'];assert f.exists()
            if 'pointer' in ev:
                v=load(f)
                for part in ev['pointer'].strip('/').split('/'):v=v[int(part)] if isinstance(v,list) else v[part]
                assert v==ev['observed_title']
        if e['type']=='curriculum_sequence':assert year==2025 and e['applicable_plan_ids']==['97235'] and e['basis']=='official_figure_arrow'
        else:assert e['basis']=='title_and_discipline_inference'
    state={}
    def visit(n):
        assert state.get(n)!=1,'cycle at '+n
        if state.get(n)==2:return
        state[n]=1
        for dest in adj[n]:visit(dest)
        state[n]=2
    for n in nodes:visit(n)
    for p in g['pathways']:
        assert all(c in nodes for c in p['course_ids'])
        assert all(b in adj[a] for a,b in zip(p['course_ids'],p['course_ids'][1:]))
    html=(out/'index.html').read_text('utf8');assert '__GRAPH__' not in html and '__YEAR__' not in html
    embedded=re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',html,re.S).group(1);assert json.loads(embedded)==g
    ET.fromstring((out/'专业主线.svg').read_text('utf8'))
    if year==2024:
        annual=load(official/'annual/metadata.json');arows=load(official/'annual/courses.json');pages=load(official/'annual/pages.json')
        textcodes=set(re.findall(r'[A-Z]{2,}\d{5,}[hH]?',str(pages)));assert textcodes=={r['course_code'] for r in arows}
        assert not annual['extraction_issues']
        for sec in annual['sections']:assert hashlib.sha256((official/'annual'/sec['excerpt_path']).read_bytes()).hexdigest()==sec['excerpt_sha256']
        for r in arows:assert r['course_code'] in pages[str(r['pdf_page'])]['text']
    report['cohorts'].append({'cohort':year,'portal_plans':len(plans),'nodes':len(nodes),'edges':len(g['edges']),'evidence_refs':sum(len(e['evidence']) for e in g['edges']),'directed_cycles':0})
for f in R.rglob('*.md'):
    for link in re.findall(r'\]\(([^)]+)\)',f.read_text('utf8')):
        if not link.startswith(('http:','https:','#')):assert (f.parent/link).exists() or (f.parent/link).resolve() in [R/'manifest.json',R/'validation.json',R/'release-assets.json'],(f,link)
(R/'validation.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(report,ensure_ascii=False))
