"""Offline validation of source coverage, graph evidence, exports and viewer payloads."""
from pathlib import Path
import collections,csv,functools,gzip,hashlib,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1]

@functools.lru_cache(None)
def load(path):
    path=Path(path);return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pointer(obj,path):
    for key in path.split('/')[1:]:
        key=key.replace('~1','/').replace('~0','~');obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj
def payload(path):
    match=re.search(r'<script type="application/json" id="payload">(.*?)</script>',path.read_text('utf-8'),re.S)
    assert match,path
    return json.loads(match[1])
def csvrows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    summaries=[];combined=payload(ROOT/'index.html');assert set(combined['graphs'])=={'2023','2024','2025'}
    for year,count in [(2023,5),(2024,14),(2025,23)]:
        target=ROOT/'cohorts'/str(year);official=target/'official';plans=load(official/'programmes.json')
        assert len(plans)==count
        graph=load(target/'course-graph/graph.json');rows=load(target/'data/program-course-index.json')
        by={n['id']:n for n in graph['nodes']};assert len(by)==len(graph['nodes'])
        catalog={p['id']:p for p in graph['programs']};assert len(catalog)==len(graph['programs'])
        assert all(n.get('program_ids') and set(n['program_ids'])<=catalog.keys() for n in graph['nodes'])
        assert {n['id'] for n in graph['nodes'] if n['kind']=='course'}=={r['node_id'] for r in rows}
        member=collections.defaultdict(set)
        for row in rows:
            member[row['program_id']].add(row['node_id'])
            obj=pointer(load(target/row['source_path']),row['json_pointer']);course=obj.get('course',obj)
            assert str(course.get('code'))==str(row['course_code']),(year,row['node_id'])
            assert course.get('nameZh',course.get('name'))==row['course_name']
        for plan in plans:
            pid=plan['plan_id'];raw=official/plan['raw_path'];word=official/plan['word_path']
            assert sha(raw)==plan['raw_sha256'];assert sha(word)==plan['word_sha256']
            assert hashlib.sha256(gzip.decompress(raw.read_bytes())).hexdigest()==plan['response_sha256']
            with zipfile.ZipFile(word) as z:assert z.testzip() is None
            original=load(raw);expected=set()
            for module in original['courseModules']:
                for key in ('planCourses','realPlanCourses'):
                    for course in module.get(key) or []:
                        item=course.get('course') or {}
                        if item.get('code') and item.get('nameZh'):expected.add(str(item['code']))
            assert member[pid]==expected,(year,pid,member[pid]^expected)
            for im in plan['images']:assert sha(official/im['path'])==im['sha256']
        if (official/'supplemental-programmes.json').exists():
            for plan in load(official/'supplemental-programmes.json'):
                expected={str(c['code']) for m in plan['modules'] for c in m['courses'] if c.get('code')}
                assert member[plan['plan_id']]==expected
                assert (target/plan['source_path']).exists()
        keys=[];evidence_checks=0
        for edge in graph['edges']:
            assert edge['source'] in by and edge['target'] in by and edge['source']!=edge['target']
            assert edge['basis'] and edge['source_url'].startswith('https://') and edge['evidence']
            keys.append((edge['source'],edge['target'],edge['type']))
            if edge['type']=='suggested_sequence':
                assert edge['program_ids']
                for pid in edge['program_ids']:assert {edge['source'],edge['target']}<=member[pid]
                assert '推断' in edge['basis']
            if edge['type'].startswith('official_'):
                assert all(e.get('quote') and e.get('source_locator') for e in edge['evidence'])
            for ev in edge['evidence']:
                assert ev['program_id'] in catalog
                assert (target/ev['source_path']).is_file()
                if ev.get('json_pointer'):pointer(load(target/ev['source_path']),ev['json_pointer'])
                if ev.get('document_path'):assert (target/ev['document_path']).is_file()
                evidence_checks+=1
        assert len(keys)==len(set(keys))
        exported=csvrows(target/'course-graph/edges.csv')
        for row in exported:
            row['program_ids']=json.loads(row['program_ids']);row['evidence']=json.loads(row['evidence'])
        assert exported==graph['edges']
        assert {r['id'] for r in csvrows(target/'course-graph/nodes.csv')}==set(by)
        assert len(csvrows(target/'data/program-course-index.csv'))==len(rows)
        assert payload(target/'course-graph/index.html')['graphs']=={str(year):graph}
        assert combined['graphs'][str(year)]==graph
        for p in catalog.values():
            for key in ('word_path','document_path','source_path'):
                if p.get(key):assert (target/p[key]).is_file(),p[key]
        summaries.append({'cohort':year,**graph['statistics'],'evidence_pointers_checked':evidence_checks})
    manifest=ROOT/'file-manifest.json'
    if manifest.exists():
        for entry in load(manifest)['files']:assert sha(ROOT/entry['path'])==entry['sha256'],entry['path']
    report={'status':'passed','checked_on':'2026-11-26','checks':['42 source JSON/DOCX files and embedded image hashes','all original plan course codes covered','all PDF normalized course codes covered','all evidence JSON pointers resolve','suggested edges share an applicable plan','CSV and graph equivalence','4 HTML embedded payloads equal graph data','local source links exist'],'cohorts':summaries}
    (ROOT/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
