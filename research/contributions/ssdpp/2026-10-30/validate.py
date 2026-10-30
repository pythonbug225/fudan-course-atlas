"""Validate the standalone SSDPP contribution with the Python standard library."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs,urlsplit
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
B=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser()
parser.add_argument('--archives-dir',type=Path)
args=parser.parse_args()
manifest=read(B/'manifest.json')
for row in manifest['files']:
    p=B/row['path']
    assert p.resolve().is_relative_to(B.resolve())
    assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
listed={row['path'] for row in manifest['files']}|{'manifest.json'}
actual={p.relative_to(B).as_posix() for p in B.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==listed,'Unlisted or missing files'
courses=[read(p) for p in (B/'courses').glob('*.json')]
codes={c['course_code'] for c in courses}
assert len(courses)==len(codes)==296
sections=read(B/'official/sections.json')
assert len(sections)==len({s['lesson_id'] for s in sections})==391
assert all(s['department']=='社会发展与公共政策学院' and s['course_code'] in codes for s in sections)
plans=read(B/'official/programs.json')
assert len(plans)==len({p['方案编号'] for p in plans})==15
evidence=read(B/'summaries/evidence.json')
key=lambda r:(r['course_code'],r['platform'],str(r['source_id']))
assert len(evidence)==len({key(r) for r in evidence})==518
assert len({r['course_code'] for r in evidence})==73
for r in evidence:
    assert r['course_code'] in codes and r['summary']
    assert r['source_url'].startswith('https://')
    if r.get('browser_recovery_platform'):
        assert r['full_text_read'] is True and (r.get('term_note') or r.get('term_scope'))
        u=urlsplit(r['source_url']);q=parse_qs(u.query)
        if u.hostname=='mp.weixin.qq.com' and u.path=='/s':assert '__biz' in q or 'signature' in q
for c in courses:
    assert all(r['course_code']==c['course_code'] and key(r) in {key(e) for e in evidence} for r in c['evidence'])
    assert all(s['course_code']==c['course_code'] for s in c['official_sections'])
queries=read(B/'ledgers/search-queries.json')
assert len(queries)==4058 and all(q['status']=='completed' for q in queries)
browser=read(B/'ledgers/browser-searches/实际查询记录.json')
assert len(browser)==17 and not any(q.get('method')=='public indexed web search' for q in browser)
with (B/'ledgers/pending-platform-searches.csv').open(encoding='utf-8-sig',newline='') as f:pending=list(csv.DictReader(f))
assert len(pending)==6087 and {q['platform'] for q in pending}=={'小红书','知乎','微信公众号'}
stats=read(B/'summaries/statistics.json')
assert stats['records']==518 and stats['courses_with_records']==73
assert stats['browser_query_coverage_exhausted'] is False
assert len((B/'社会发展与公共政策学院课程名单.txt').read_text('utf-8').splitlines())==278
private=re.compile(r'\b\d{11}@m\.fudan\.edu\.cn\b|"(?:password|access_token|refresh_token|authorization|cookie)"\s*:|[?&](?:xsec_token|access_token|appmsg_token|pass_ticket)=|\bgh[pousr]_[A-Za-z0-9]{30,}\b',re.I)
for p in B.rglob('*'):
    if p.is_file() and p.suffix in {'.json','.csv','.md','.txt'}:
        s=p.read_text('utf-8-sig')
        assert not private.search(s),'Sensitive field in '+p.relative_to(B).as_posix()
        assert chr(65533) not in s,'Encoding replacement character'
for p in B.glob('*.md'):
    for href in re.findall(r'\]\(([^)]+)\)',p.read_text('utf-8')):
        if not href.startswith(('https://','http://','#')):assert (p.parent/href).exists(),href
if args.archives_dir:
    for a in read(B/'release-assets.json')['assets']:
        p=args.archives_dir/a['name']
        assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256'],a['name']
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            if a['name']=='ssdpp-research-20261030.zip':
                prefix='社会发展与公共政策学院_2026培养方案与课程研究/'
                rows=csv.DictReader(z.read(prefix+'文件校验清单.csv').decode('utf-8-sig').splitlines())
                for r in rows:assert hashlib.sha256(z.read(prefix+r['path'])).hexdigest()==r['sha256']
                for plan in plans:
                    data=z.read(prefix+'官方资料/培养方案/方案原件/'+plan['Word原件'])
                    assert hashlib.sha256(data).hexdigest()==plan['SHA256']
print(json.dumps({'result':'passed','files':len(actual),'programs':15,'sections':391,'courses':296,'evidence':518,'courses_with_evidence':73,'browser_queries':17,'archives_checked':args.archives_dir is not None},ensure_ascii=False))
