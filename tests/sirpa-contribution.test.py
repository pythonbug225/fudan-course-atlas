"""Check SIRPA published original records, provenance and target-term boundaries."""
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
B=ROOT/'research/contributions/sirpa/2026-10-27'
def load(p):return json.loads((B/p).read_text('utf-8'))
def lines(p):return [json.loads(s) for s in (B/p).read_text('utf-8').splitlines()]
m=load('manifest.json')
for f in m['files']:
    p=B/f['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],p
courses=list((B/'courses').glob('*.json'));assert len(courses)==306
roster=load('official/sections.json');assert len(roster)==619
codes={r['course_code'] for r in roster}
dr=lines('raw/danke-reviews.jsonl');fr=lines('raw/treehole-cited-floors.jsonl')
assert len(dr)==len({r['review_id'] for r in dr})==111
assert len(fr)==len({r['floor_id'] for r in fr})==581
ds=load('summaries/danke-summaries.json');fs=load('summaries/forum-summaries.json')
assert {s['review_id'] for s in ds['sources']}=={r['review_id'] for r in dr}
assert {int(f) for s in fs['sources'] for f in s['floor_ids']}=={r['floor_id'] for r in fr}
assert ds['statistics']['exact_target_term_count']==7
assert ds['statistics']['exact_target_term_by_api_code_section_teacher_without_reported_conflict_ids']==[5526,5573,5685,5794,5894,5911,6055]
for p in courses:
    d=json.loads(p.read_text('utf-8'));assert d['course']['code'] in codes
    for s in d['sources']:assert set(s.get('course_codes',[]))<=codes
for r in dr+fr:
    assert r['source_url'].startswith('https://') and 'response' in r
    assert not any(k in r['response'] for k in ['user','author','email','password','access','refresh'])
    t=json.dumps(r,ensure_ascii=False)
    for pattern in [r'eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.',r'(?<!\d)2\d{10}(?!\d)',r'(?<!\d)1[3-9]\d{9}(?!\d)',r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}']:
        assert not re.search(pattern,t),r.get('source_url')
print('SIRPA provenance checks passed: 306 courses / 619 sections / 111 reviews / 581 cited floors')
