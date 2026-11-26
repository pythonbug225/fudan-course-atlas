"""Download public foreign-language programme sources, preserving original responses."""
import concurrent.futures,gzip,hashlib,json,time,urllib.parse,urllib.request,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
W=Path(__file__).resolve().parent;O=W.parent
BASE='https://fdjwgl.fudan.edu.cn/manager/bizType/2'
def put(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def request(url,data=None):
 for attempt in range(3):
  try:
   q=urllib.request.Request(url,data=data,headers={'User-Agent':'Fudan-Foreign-Curriculum-Research/1','Content-Type':'application/x-www-form-urlencoded' if data else 'application/json'})
   with urllib.request.urlopen(q,timeout=40) as r:return r.read(),r.headers.get('Content-Type','')
  except Exception:
   if attempt==2:raise
   time.sleep(1)
def directory(year,dept=None):
 rows=[];raw=[];page=1
 while True:
  args={'skipAuth':'1','YEARS':str(year),'queryPage__':f'{page},1000'}
  if dept:args['DEPART_IDS']=str(dept)
  url=BASE+'/page-center/major-program-search-view/search?'+urllib.parse.urlencode(args)
  body,_=request(url);data=json.loads(body);raw.append({'url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'response':data});part=data['data'];rows.extend(part)
  total=data.get('_page_',{}).get('totalRows')
  if total is not None and len(rows)>=int(total):assert len(rows)==int(total);break
  if len(part)<1000:break
  page+=1;assert page<=10
 assert len({r['ID'] for r in rows})==len(rows)
 return rows,raw
def enumerate_year(year):
 root=O/str(year)/'official'
 rows,raw=directory(year);dept,dr=directory(year,2551)
 assert {r['ID'] for r in dept}=={r['ID'] for r in rows if r.get('DEPART_IDS')==2551}
 put(root/'raw/directory-all.json',raw);put(root/'raw/directory-department-2551.json',dr);put(root/'raw/department-rows.json',dept)
 common=[r for r in rows if any(x in r['NAME_ZH'] for x in ['公共培养','通识'])]
 put(root/'raw/common-candidates.json',common)
 print(json.dumps({'year':year,'total':len(rows),'dept':dept,'common':common},ensure_ascii=False),flush=True)
 return year,dept,common
def collect_plan(year,row,scope='department'):
 root=O/str(year)/'official';pid=str(row['ID']);url=BASE+'/major-program-search/info/'+pid+'?skipAuth=1'
 body,ctype=request(url);data=json.loads(body);model=data['model']
 assert str(model['id'])==pid and str(model['grade'])==str(year)
 target=root/'raw'/('plan-'+pid+'.json.gz');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(gzip.compress(body,mtime=0))
 docx,dtype=request(BASE+'/major-program-search/export-word',urllib.parse.urlencode({'ids':pid}).encode())
 wp=root/'word-originals'/('plan-'+pid+'.docx');wp.parent.mkdir(exist_ok=True);wp.write_bytes(docx)
 with zipfile.ZipFile(wp) as z:
  assert z.testzip() is None
  doc=ET.fromstring(z.read('word/document.xml'))
  ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
  text='\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:p',ns))
  assert str(year) in text
  tp=root/'word-text'/('plan-'+pid+'.txt');tp.parent.mkdir(exist_ok=True);tp.write_text(text,encoding='utf-8')
  images=[]
  if 'word/_rels/document.xml.rels' in z.namelist():
   rel=ET.fromstring(z.read('word/_rels/document.xml.rels'));mapping={r.attrib['Id']:r.attrib['Target'] for r in rel}
   for pi,para in enumerate(doc.findall('.//w:p',ns)):
    for im in para.findall('.//a:blip',ns):
     rid=im.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed');member=mapping.get(rid)
     if member:
      b=z.read('word/'+member);relative='source-figures/plan-'+pid+'-'+Path(member).name;p=root/relative;p.parent.mkdir(exist_ok=True);p.write_bytes(b);images.append({'path':relative,'member':'word/'+member,'paragraph':pi,'sha256':hashlib.sha256(b).hexdigest()})
 meta={'plan_id':pid,'cohort':year,'title':row['NAME_ZH'],'department':row.get('DEPART_NAME'),'department_id':row.get('DEPART_IDS'),'major_name':row.get('MAJOR_NAME'),'scope':scope,'directory_row':row,'detail_url':url,'export_url':BASE+'/major-program-search/export-word','export_method':'POST ids='+pid,'raw_path':target.relative_to(root).as_posix(),'raw_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'response_sha256':hashlib.sha256(body).hexdigest(),'word_path':wp.relative_to(root).as_posix(),'word_bytes':len(docx),'word_sha256':hashlib.sha256(docx).hexdigest(),'word_text_path':tp.relative_to(root).as_posix(),'content_type':dtype,'images':images,'retrieved_at':datetime.now(timezone.utc).isoformat()}
 put(root/'metadata'/('plan-'+pid+'.json'),meta)
 print(f'downloaded {year} {pid} {row["NAME_ZH"]}',flush=True)
 return meta
if __name__=='__main__':
 import sys
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  enumerations=list(pool.map(enumerate_year,[2023,2024,2025]))
 if '--enumerate' in sys.argv:raise SystemExit
 for year,dept,common in enumerations:
  selected=[(r,'department')for r in dept]+[(r,'common_reference')for r in common if r['ID']not in {d['ID']for d in dept}]
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:plans=list(pool.map(lambda item:collect_plan(year,*item),selected))
  put(O/str(year)/'official/programmes.json',plans)
  put(O/str(year)/'official/coverage.json',{'cohort':year,'department_id':2551,'department_plans':len(dept),'common_reference_plans':len(plans)-len(dept),'downloaded_originals':len(plans),'retrieved_date':'2026-11-26','scope_note':'外院筛选目录全部方案；当前目录无独立公共方案，完整毕业要求须结合本年公共要求。历史PDF补充另列。'})
