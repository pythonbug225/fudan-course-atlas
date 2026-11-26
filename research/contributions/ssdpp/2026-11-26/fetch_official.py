"""Fetch the public cohort-specific SSDPP programme directory and original exports."""
import concurrent.futures, datetime, gzip, hashlib, json, re, time, urllib.parse, urllib.request, zipfile, xml.etree.ElementTree as ET
from pathlib import Path

W=Path(__file__).resolve().parent
import sys
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else W/'fresh-snapshot'
ORIGINALS=OUT/'word-originals'
BASE='https://fdjwgl.fudan.edu.cn/manager/bizType/2'
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    b=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
    p.write_bytes(gzip.compress(b,mtime=0) if p.suffix=='.gz' else b)
def request(url,data=None):
    for i in range(3):
        try:
            req=urllib.request.Request(url,data=data,headers={'User-Agent':'Fudan-SSDPP-Curriculum-Research/1','Content-Type':'application/x-www-form-urlencoded' if data else 'application/json'})
            with urllib.request.urlopen(req,timeout=40) as r:return r.read(),r.headers.get('Content-Type','')
        except Exception:
            if i==2:raise
            time.sleep(1)
def directory(year,dept=None):
    rows=[];pages=[];page=1
    while True:
        args={'skipAuth':'1','YEARS':str(year),'queryPage__':f'{page},1000'}
        if dept:args['DEPART_IDS']=str(dept)
        url=BASE+'/page-center/major-program-search-view/search?'+urllib.parse.urlencode(args)
        body,_=request(url);data=json.loads(body);pages.append({'url':url,'response':data})
        rows+=data['data'];total=data.get('_page_',{}).get('totalRows')
        if total is not None and len(rows)>=int(total):assert len(rows)==int(total);break
        if len(data['data'])<1000:break
        page+=1;assert page<10
    assert len({r['ID'] for r in rows})==len(rows)
    return rows,pages

# Public course/plan payloads may embed staff contact fields. Retain curriculum
# values and exact array positions, while redacting these fields only.
PRIVATE=re.compile(r'^(?:telephone|phone|mobile|email|emailAddress|password|passwd|token|accessToken|refreshToken|cookie|authorization|idCard|idCardNo|studentNo|loginName)$',re.I)
def redact(v,path='',removed=None):
    if removed is None:removed=[]
    if isinstance(v,dict):
        out={}
        for k,z in v.items():
            if PRIVATE.fullmatch(k):
                out[k]=None
                if z:removed.append(path+'/'+k)
            else:out[k]=redact(z,path+'/'+k,removed)
        return out
    if isinstance(v,list):return [redact(z,path+'/'+str(i),removed) for i,z in enumerate(v)]
    return v
def collect(year):
    root=OUT/str(year)/'official';root.mkdir(parents=True,exist_ok=True)
    rows,raw=directory(year);selected,depraw=directory(year,2567)
    assert {r['ID'] for r in selected}=={r['ID'] for r in rows if r.get('DEPART_IDS')==2567}
    save(root/'raw/directory-all.json.gz',raw);save(root/'raw/directory-department-2567.json.gz',depraw)
    plans=[]
    for row in selected:
        pid=str(row['ID']);url=BASE+'/major-program-search/info/'+pid+'?skipAuth=1'
        body,_=request(url);data=json.loads(body);removed=[];clean=redact(data,removed=removed)
        assert str(data['model']['grade'])==str(year)
        save(root/'raw'/('plan-'+pid+'.json.gz'),clean)
        target=ORIGINALS/str(year)/('plan-'+pid+'.docx');target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():docx=target.read_bytes();ctype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            docx,ctype=request(BASE+'/major-program-search/export-word',urllib.parse.urlencode({'ids':pid}).encode());target.write_bytes(docx)
        images=[]
        with zipfile.ZipFile(target) as z:
            assert z.testzip() is None
            doc=ET.fromstring(z.read('word/document.xml'))
            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
            paragraphs=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:p',ns)]
            text='\n'.join(paragraphs);assert str(year) in text and any(k in text for k in ['心理学','社会学','社会工作'])
            (root/'word-text').mkdir(exist_ok=True);(root/'word-text'/('plan-'+pid+'.txt')).write_bytes(text.encode())
            rel=ET.fromstring(z.read('word/_rels/document.xml.rels'));mapping={r.attrib['Id']:r.attrib['Target'] for r in rel}
            for pi,para in enumerate(doc.findall('.//w:p',ns)):
                for im in para.findall('.//a:blip',ns):
                    member=mapping.get(im.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'))
                    if member:
                        b=z.read('word/'+member);relative='source-figures/plan-'+pid+'-'+Path(member).name
                        p=root/relative;p.parent.mkdir(exist_ok=True);p.write_bytes(b)
                        images.append({'path':relative,'member':'word/'+member,'paragraph_index':pi,'preceding_text':' / '.join(paragraphs[max(0,pi-2):pi]),'sha256':hashlib.sha256(b).hexdigest()})
        plans.append({'plan_id':pid,'cohort':year,'title':row['NAME_ZH'],'department':row.get('DEPART_NAME'),'department_id':row.get('DEPART_IDS'),'major_name':row.get('MAJOR_NAME'),'directory_row':row,'detail_url':url,'detail_path':'raw/plan-'+pid+'.json.gz','export_url':BASE+'/major-program-search/export-word','export_method':'POST ids='+pid,'word_path':str(year)+'/plan-'+pid+'.docx','word_bytes':len(docx),'word_sha256':hashlib.sha256(docx).hexdigest(),'content_type':ctype,'source_json_sha256':hashlib.sha256(body).hexdigest(),'redacted_nonempty_paths':removed,'images':images})
        print(json.dumps({'cohort':year,'plan_id':pid,'title':row['NAME_ZH'],'word_bytes':len(docx)},ensure_ascii=False),flush=True)
    save(root/'programmes.json',plans)
    summary={'cohort':year,'directory_total':len(rows),'department_plans':len(selected),'downloaded_originals':len(plans),'all_directory_department_ids_match':True,'retrieved_date':'2026-11-26','majors':sorted(set(p['major_name'] for p in plans)),'possible_common_plans':[r for r in rows if any(w in r.get('NAME_ZH','') for w in ['通识教育','公共培养','公共基础'])]}
    save(root/'coverage.json',summary);return summary
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for summary in pool.map(collect,[2023,2024,2025]):print(json.dumps(summary,ensure_ascii=False),flush=True)
