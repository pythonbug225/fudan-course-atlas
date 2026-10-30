import pathlib,json,hashlib,zipfile
p=pathlib.Path(__file__).resolve().parent
m=json.loads((p/'file-manifest.json').read_text(encoding='utf8'))
for r in m['files']:
 f=p/r['path']; b=f.read_bytes()
 assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
 if f.suffix=='.zip':
  with zipfile.ZipFile(f) as z:assert z.testzip() is None
rows=json.loads((p/'official/course_catalog.json').read_text(encoding='utf8'))
names=(p/'新闻学院课程名单.txt').read_text(encoding='utf8').splitlines()
assert len(rows)==352 and len({r['course_code'] for r in rows})==207
assert len(names)==len(set(names))==203 and set(names)=={r['course_name'].strip() for r in rows}
d=[json.loads(x) for x in (p/'raw/danke-reviews.jsonl').read_text(encoding='utf8').splitlines()]
f=[json.loads(x) for x in (p/'raw/forum-read-and-cited-floors.jsonl').read_text(encoding='utf8').splitlines()]
assert len(d)==len({x['source_review_id'] for x in d})==61
assert len(f)==len({x['floor_id'] for x in f})==m['counts']['forum_source_rows']
print('OK: file hashes, ZIP CRC, 203 course names, 61 source reviews, forum IDs')
