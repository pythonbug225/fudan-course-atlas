"""Validate original documents, cohort coverage, graph references and scope."""
from pathlib import Path
import collections,gzip,hashlib,json,re,zipfile,xml.etree.ElementTree as ET
W=Path(__file__).resolve().parent;ROOT=W.parent if W.name=='scripts' else W/'package';O=ROOT/'cohorts'
def load(p):
    if p.is_file():return json.loads(p.read_text('utf-8-sig'))
    return json.loads(gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
def raw_courses(x,result):
    if isinstance(x,dict):
        if isinstance(x.get('course'),dict) and x['course'].get('code') and 'terms' in x:result.add((x['course']['code'],x['course'].get('nameZh') or x['course']['code']))
        for v in x.values():raw_courses(v,result)
    elif isinstance(x,list):
        for v in x:raw_courses(v,result)
def cycles(nodes,edges):
    adj=collections.defaultdict(list)
    for e in edges:
        if e['directed']:adj[e['source']].append(e['target'])
    visited=set();active=set();found=[]
    def visit(n,path):
        if n in active:found.append(path[path.index(n):]+[n]);return
        if n in visited:return
        active.add(n)
        for nxt in adj[n]:visit(nxt,path+[n])
        active.remove(n);visited.add(n)
    for n in nodes:visit(n,[])
    return found
def main():
    combined=load(O/'graphs.json');summary={};total_words=0
    for year in [2023,2024,2025]:
        g=load(O/str(year)/'course-graph/graph.json');assert combined['cohorts'][str(year)]==g
        assert g['audit'].get('status')!='draft_relations_pending','draft_relations_must_not_publish'
        nodes={n['id']:n for n in g['nodes']};assert len(nodes)==len(g['nodes'])
        assert len({e['id'] for e in g['edges']})==len(g['edges'])
        plans=load(O/str(year)/'official/programmes.json');assert {str(p['plan_id']) for p in plans}=={p['id'] for p in g['programs']}
        words_without_printed_cohort=[]
        for meta in plans:
            pid=str(meta['plan_id']);raw=load(O/str(year)/'official/raw'/f'plan-{pid}.json');assert str(raw['model']['grade'])==str(year)
            rawbytes=gzip.decompress((O/str(year)/'official/raw'/f'plan-{pid}.json.gz').read_bytes());assert hashlib.sha256(rawbytes).hexdigest()==meta['raw_sha256']
            pairs=set();raw_courses(raw['courseModules'],pairs)
            actual={(n['code'],n['name']) for n in g['nodes'] if pid in n['program_ids']};assert pairs==actual,(year,pid,'raw_courses_mismatch')
            word=O/str(year)/'official'/meta['word_path']
            with zipfile.ZipFile(word) as z:
                assert z.testzip() is None;doc=ET.fromstring(z.read('word/document.xml'));text=''.join(t.text or '' for t in doc.iter() if t.tag.endswith('}t'))
                assert len(text)>100,(year,pid,'empty_word')
                if str(year) not in text:words_without_printed_cohort.append(pid)
            if meta.get('word_sha256'):assert hashlib.sha256(word.read_bytes()).hexdigest()==meta['word_sha256']
            total_words+=1
        for e in g['edges']:
            assert e['source'] in nodes and e['target'] in nodes and e['source']!=e['target']
            assert e['program_ids'] and set(e['program_ids'])<=set(nodes[e['source']]['program_ids'])&set(nodes[e['target']]['program_ids'])
            assert e['evidence'] and e['reason']
            assert e['is_enrollment_prerequisite']==(e['type']=='verified_prerequisite')
            for v in e['evidence']:
                p=(O/v['path']).resolve();assert p.is_relative_to(O.resolve()) and p.is_file(),v['path'];assert v['locator']
        cyc=cycles(nodes,g['edges']);byplan={}
        for p in g['programs']:
            ns={k:n for k,n in nodes.items() if p['id'] in n['program_ids']}
            found=cycles(ns,[e for e in g['edges'] if p['id'] in e['program_ids']])
            if found:byplan[p['id']]=found
        summary[str(year)]={'plans':len(plans),'nodes':len(nodes),'edges':len(g['edges']),'types':dict(collections.Counter(e['type'] for e in g['edges'])),'directed_cycles_in_combined_view':cyc,'directed_cycles_by_program':byplan,'cycle_interpretation':'不同方案图可有相反方向；混合关系图不是选课先修 DAG。图中所有方向必须结合 relation type 与 program_ids 解读。','official_word_zip_integrity':True,'raw_course_coverage':True,'cohort_scope_integrity':True,'words_without_printed_cohort_but_api_grade_verified':words_without_printed_cohort,'evidence_paths_exist':True}
    page=(O/'课程关系图谱.html').read_text('utf8');match=re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',page,re.S);assert match and json.loads(match.group(1))==combined
    result={'status':'passed','date':'2026-11-26','cohorts':summary,'official_word_documents_verified':total_words,'html_embedded_graph_matches':True}
    (ROOT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
