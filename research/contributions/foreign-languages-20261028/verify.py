import csv,hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads((root/p).read_text('utf-8-sig'))
manifest=read('file-manifest.json')
for r in manifest['files']:
 p=root/r['path'];assert p.is_file()and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['path']
classes=read('data/official-classes.json');assert len(classes)==618 and len({r['教学班编号']for r in classes})==618
evidence=read('data/evidence.json');assert len(evidence)==122 and len({r['id']for r in evidence})==122
by_id={r['id']:r for r in evidence}
files=list((root/'courses').glob('*.json'));assert len(files)==455
codes=set()
for p in files:
 r=json.loads(p.read_text('utf-8'));code=r['course']['code'];assert code==p.stem and code not in codes;codes.add(code)
 for s in r['sources']:assert s['source_id']in by_id and code in by_id[s['source_id']]['course_codes']
synth=read('data/course-synthesis.json')['courses'];assert len(synth)==35
for s in synth:
 assert s['code']in codes
 for sid in s['source_ids']:assert sid in by_id and s['code']in by_id[sid]['course_codes']
with (root/'data/query-ledger.csv').open(encoding='utf-8-sig',newline='')as f:queries=list(csv.DictReader(f))
assert len(queries)==4334 and all(r['状态']=='completed'for r in queries)
assert all(set(e['course_codes'])<=codes for e in evidence)
print(json.dumps(dict(files_verified=len(manifest['files']),courses=455,classes=618,evidence=122,syntheses=35,completed_queries=4334)))
