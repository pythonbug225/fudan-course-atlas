import json,pathlib,hashlib,zipfile,xml.etree.ElementTree as ET,collections,re,gzip
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
R=pathlib.Path(__file__).resolve().parent
OUT=R
def read(p):return json.loads(p.read_text('utf-8-sig'))
issues=[];checks={}
for p in OUT.rglob('*.json'):
    try:read(p)
    except Exception as e:issues.append('JSON invalid: '+str(p.relative_to(OUT)))
courses=read(OUT/'逐课程汇总.json');evidence=read(OUT/'已核读课评摘要.json')
codes={x['courseCode'] for x in courses};teachers={t['name'] for x in courses for t in x['teachers']}
checks.update(courses=len(courses),unique_codes=len(codes),teachers=len(teachers),classes=sum(len(c['sections']) for c in courses),evidence=len(evidence))
if (len(codes),len(teachers),checks['classes'])!=(167,63,229):issues.append('Official scope count mismatch')
for c in courses:
    if read(OUT/'课程'/(c['courseCode']+'.json'))!=c:issues.append('Course record mismatch '+c['courseCode'])
ids=[e['evidence_id'] for e in evidence]
if len(set(ids))!=len(ids):issues.append('duplicate evidence IDs')
for e in evidence:
    if not set(e['course_codes'])<=codes:issues.append('Evidence uses unknown code '+e['evidence_id'])
    if not e.get('boundary') or not e.get('source_urls'):issues.append('Evidence missing source/boundary '+e['evidence_id'])
correct={2517:'GECS10001',2518:'GESP10001',2525:'ICLE10006',4608:'ICLE10006',4997:'ICLE20030',5781:'GESP10001',5996:'GECS10003',6127:'GEEC20013',6784:'ICLE20028',6798:'GESP20001',6800:'GESP20001'}
for e in evidence:
    if e['evidence_id'].startswith('DANKE-') and e['course_codes']!=[correct[int(e['evidence_id'][6:])]]:issues.append('Danke attribution mismatch '+e['evidence_id'])
plans=read(OUT/'官方资料/official-acquisition-summary.json')['plans'];plan_checks=[]
for p in plans:
    f=OUT/'官方资料/方案原件'/p['docxFile'];b=f.read_bytes();h=hashlib.sha256(b).hexdigest().upper()
    if len(b)!=p['bytes'] or h!=p['sha256'].upper():issues.append('Original DOCX byte/hash mismatch '+p['docxFile'])
    with zipfile.ZipFile(f) as z:
        if z.testzip():issues.append('DOCX ZIP corruption')
        root=ET.fromstring(z.read('word/document.xml'));text=''.join(root.itertext())
        if '2026' not in text or '汉语言' not in text:issues.append('Unexpected DOCX title')
    plan_checks.append({'file':p['docxFile'],'bytes':len(b),'sha256':h})
checks['official_originals']=plan_checks
class Parser(HTMLParser):
    links=[];cards=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and 'href'in a:self.links.append(a['href'])
        if tag=='details' and a.get('class')=='course':self.cards+=1
parser=Parser();parser.feed((OUT/'课程研究报告.html').read_text('utf8'))
for u in parser.links:
    z=urlsplit(u)
    if z.scheme or z.netloc or not z.path:continue
    if not (OUT/unquote(z.path)).exists():issues.append('Broken local link '+u)
checks['html_course_cards']=parser.cards
if parser.cards!=167:issues.append('HTML course card mismatch')
with zipfile.ZipFile(OUT/'培养方案与课程表.xlsx') as z:
    if z.testzip():issues.append('Workbook ZIP corruption')
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    wb=ET.fromstring(z.read('xl/workbook.xml'));checks['workbook_sheets']=[s.attrib['name'] for s in wb.findall('.//s:sheet',ns)]
    checks['workbook_cell_ranges']={n:[c.attrib.get('r') for c in ET.fromstring(z.read(n)).findall('.//s:c',ns)][::max(1,len(ET.fromstring(z.read(n)).findall('.//s:c',ns))-1)] for n in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+.xml',n)}
coverage=read(OUT/'检索执行台账.json');checks['query_statuses']={p:dict(collections.Counter(x['status'] for x in coverage if x['platform']==p)) for p in {x['platform'] for x in coverage}}
checks['scope_note']='检索执行不等于所有候选全文核读；外部平台覆盖另见各检索记录。'
report={'checks':checks,'issues':issues,'status':'passed' if not issues else 'failed'}
manifest=read(OUT/'文件校验清单.json')
for item in manifest['files']:
    p=OUT/item['path']
    if not p.is_file() or p.stat().st_size!=item['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:issues.append('Manifest mismatch '+item['path'])
for p in OUT.rglob('*'):
    if p.suffix in {'.json','.csv','.html','.txt','.md','.py'}:
        text=p.read_text('utf-8-sig')
        if re.search(r'"(?:password|access_token|refresh_token|authorization|cookie)"\s*:|[?&](?:xsec_token|access_token|auth)=|[A-Z]:[\\/]+Users[\\/]',text,re.I):issues.append('Non-public credential field or local path '+str(p.relative_to(OUT)))
raw_manifest=read(OUT/'raw/manifest.json')
raw_values={}
for row in raw_manifest['files']:
    packed=(OUT/'raw'/row['stored_path']).read_bytes()
    if hashlib.sha256(packed).hexdigest()!=row['stored_sha256']:issues.append('Raw compressed hash '+row['source_path'])
    data=gzip.decompress(packed)
    if hashlib.sha256(data).hexdigest()!=row['restored_sha256']:issues.append('Raw restored hash '+row['source_path'])
    value=json.loads(data);raw_values[row['source_path']]=value
    if re.search(r'"(?:password|access_token|refresh_token|authorization|cookie)"\s*:|[?&](?:xsec_token|access_token|auth)=|\b\d{11}@m\.fudan',data.decode('utf8'),re.I):issues.append('Raw private field '+row['source_path'])
if len(raw_values['live/forum_search_results.json']['items'])!=19632:issues.append('Raw forum count')
if len(raw_values['live/forum_context_results.json']['floors'])!=502:issues.append('Raw context count')
details=raw_values['live/danke_details_results.json']
if (len(details['groups']),len(details['courses']),len(details['reviews']))!=(369,776,11):issues.append('Raw Danke counts')
checks['raw_files']=len(raw_manifest['files'])
report['status']='passed' if not issues else 'failed'
checks['manifest_files']=len(manifest['files'])
print(json.dumps(report,ensure_ascii=False))
if issues:raise SystemExit(1)
