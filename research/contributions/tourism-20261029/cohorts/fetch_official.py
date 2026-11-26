"""Fetch public Fudan plan directories, plan JSON and original Word files."""
import concurrent.futures,hashlib,json,time,urllib.parse,urllib.request,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
W=Path(__file__).resolve().parent;O=W/'package/cohorts';O.mkdir(parents=True,exist_ok=True)
HOST='https://fdjwgl.fudan.edu.cn';BASE=HOST+'/manager/bizType/2'
def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def request(url,data=None):
 for attempt in range(3):
  try:
   q=urllib.request.Request(url,data=data,headers={'User-Agent':'Fudan-Tourism-Curriculum-Research/1','Content-Type':'application/x-www-form-urlencoded' if data else 'application/json'})
   with urllib.request.urlopen(q,timeout=35) as r:return r.read(),r.headers.get('Content-Type','')
  except Exception:
   if attempt==2:raise
   time.sleep(1)
def directory(year,dept=None):
 rows=[];raw=[];page=1
 while True:
  args={'skipAuth':'1','YEARS':str(year),'queryPage__':f'{page},1000'}
  if dept:args['DEPART_IDS']=str(dept)
  url=BASE+'/page-center/major-program-search-view/search?'+urllib.parse.urlencode(args)
  body,_=request(url);data=json.loads(body);raw.append({'url':url,'response':data});part=data['data'];rows.extend(part)
  meta=data.get('_page_',{});total=meta.get('totalRows')
  if total is not None and len(rows)>=int(total):assert len(rows)==int(total);break
  if len(part)<1000:break
  page+=1;assert page<=10
 assert len({r['ID'] for r in rows})==len(rows)
 return rows,raw
def collect(year):
 root=O/str(year)/'official';root.mkdir(parents=True,exist_ok=True)
 allrows,raw=directory(year);deptrows,depraw=directory(year,2595)
 put(root/'raw/directory-all.json',raw);put(root/'raw/directory-department-2595.json',depraw)
 selected=[r for r in allrows if r.get('DEPART_IDS')==2595 or '旅游' in str(r.get('NAME_ZH',''))+' '+str(r.get('MAJOR_NAME',''))]
 assert {r['ID'] for r in deptrows}=={r['ID'] for r in allrows if r.get('DEPART_IDS')==2595}
 plans=[]
 for row in selected:
  pid=str(row['ID']);url=BASE+'/major-program-search/info/'+pid+'?skipAuth=1';body,_=request(url);data=json.loads(body)
  put(root/'raw'/('plan-'+pid+'.json'),data)
  docx,ctype=request(BASE+'/major-program-search/export-word',urllib.parse.urlencode({'ids':pid}).encode())
  target=root/'word-originals'/('plan-'+pid+'.docx');target.parent.mkdir(exist_ok=True);target.write_bytes(docx)
  with zipfile.ZipFile(target) as z:
   assert z.testzip() is None
   doc=ET.fromstring(z.read('word/document.xml'));text=''.join(t.text or '' for t in doc.iter() if t.tag.endswith('}t'))
   assert str(year) in text and '旅游' in text
   (root/'word-text').mkdir(exist_ok=True);(root/'word-text'/('plan-'+pid+'.txt')).write_bytes(text.encode('utf-8'))
   rel=ET.fromstring(z.read('word/_rels/document.xml.rels'));mapping={r.attrib['Id']:r.attrib['Target'] for r in rel}
   ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'};images=[]
   for pi,para in enumerate(doc.findall('.//w:p',ns)):
    for im in para.findall('.//a:blip',ns):
     rid=im.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed');member=mapping.get(rid)
     if member:
      b=z.read('word/'+member);relative='source-figures/plan-'+pid+'-'+Path(member).name;p=root/relative;p.parent.mkdir(exist_ok=True);p.write_bytes(b);images.append({'path':relative,'member':'word/'+member,'paragraph':pi,'sha256':hashlib.sha256(b).hexdigest()})
  model=data.get('model',{})
  meta={'plan_id':pid,'cohort':year,'title':row['NAME_ZH'],'department':row.get('DEPART_NAME'),'department_id':row.get('DEPART_IDS'),'major_name':row.get('MAJOR_NAME'),'directory_row':row,'scope':'department' if row.get('DEPART_IDS')==2595 else 'related_cross_department','detail_url':url,'export_url':BASE+'/major-program-search/export-word','export_method':'POST ids='+pid,'word_path':str(target.relative_to(root)),'word_bytes':len(docx),'word_sha256':hashlib.sha256(docx).hexdigest(),'content_type':ctype,'images':images,'model_keys':list(model) if isinstance(model,dict) else []}
  if isinstance(model,dict):
   meta['model_scope_fields']={k:model.get(k) for k in ['id','nameZh','grade','stdType','cultivateType','major','department','depart','years','auditState','bizType'] if k in model}
  plans.append(meta)
 put(root/'programmes.json',plans)
 summary={'cohort':year,'directory_total':len(allrows),'department_plans':len(deptrows),'related_tourism_plans':len(selected)-len(deptrows),'downloaded_originals':len(plans),'plans':[{'id':p['plan_id'],'title':p['title'],'department':p['department']} for p in plans],'fetched_date':'2026-11-26'}
 put(root/'coverage.json',summary);return summary
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for summary in pool.map(collect,[2023,2024,2025]):print(json.dumps(summary,ensure_ascii=False),flush=True)
