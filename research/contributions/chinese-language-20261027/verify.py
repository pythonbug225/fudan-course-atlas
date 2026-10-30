"""Verify this downloaded contribution offline using only Python's standard library."""
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def lines(path):return [json.loads(line) for line in (ROOT/path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]
def check(ok,message):
    if not ok:raise ValueError(message)

try:
    manifest=load('file-manifest.json')
    for item in manifest['files']:
        path=ROOT/item['path']
        check(path.resolve().is_relative_to(ROOT),'Unsafe manifest path')
        data=path.read_bytes()
        check(len(data)==item['bytes'],'File size mismatch: '+item['path'])
        check(hashlib.sha256(data).hexdigest()==item['sha256'],'SHA-256 mismatch: '+item['path'])
    courses=[json.loads(p.read_text('utf8')) for p in sorted((ROOT/'courses').glob('*.json'))]
    check(len(courses)==163,'Expected 163 course files')
    check(sum(len(c.get('offerings',[])) for c in courses)==297,'Expected 297 target offerings')
    for c in courses:
        ids=[s['source_id'] for s in c['sources']]
        check(len(set(ids))==len(ids),'Duplicate source IDs within a course')
        for s in c['sources']:
            ptr=s.get('raw_filename')
            if ptr:check((ROOT/ptr).exists(),'Missing source file: '+ptr)
    danke=lines('raw/danke.jsonl');forum=lines('raw/forum.jsonl');external=load('raw/external-sources.json')
    raw=danke+forum+external
    check((len(danke),len(forum),len(external))==(246,355,13),'Unexpected raw record counts')
    def source_id(r):
        if r.get('platform')=='danke':return 'DANKE-'+str(r['source_review_id'])
        if r.get('platform')=='forum':return 'FORUM-'+str(r['floor_id'])
        return str(r['id'])
    raw_ids={source_id(r) for r in raw}
    check(len(raw_ids)==len(raw),'Duplicate raw record IDs')
    source_tables={'raw/danke.jsonl':danke,'raw/forum.jsonl':forum,'raw/external-sources.json':external}
    for c in courses:
        for source in c['sources']:
            ptr=source.get('raw_filename');rid=source.get('raw_record_id')
            if not ptr or rid is None:continue
            if ptr not in source_tables:
                data=load(ptr)
                if isinstance(data,list):source_tables[ptr]=data
            if ptr in source_tables:
                possible={str(r[k]) for r in source_tables[ptr] for k in ['id','source_review_id','floor_id','lesson_id'] if k in r}
                check(str(rid) in possible,'Source record ID missing in '+ptr+': '+str(rid))
    curated=load('reports/新增课评与树洞归纳.json')['records']
    check(len(curated)==535,'Expected 535 curated records')
    check(not {r['id'] for r in curated}-raw_ids,'Curated record missing a raw record or external index')
    for path in ROOT.rglob('*.json'):
        json.loads(path.read_text(encoding='utf-8-sig'))
    print(json.dumps({'passed':True,'verified_files':len(manifest['files']),'course_codes':len(courses),'target_offerings':297,'curated_records':len(curated),'raw_danke':len(danke),'raw_forum':len(forum),'external_indexes':len(external)}))
except Exception as exc:
    print(json.dumps({'passed':False,'error':str(exc)},ensure_ascii=False));sys.exit(1)
