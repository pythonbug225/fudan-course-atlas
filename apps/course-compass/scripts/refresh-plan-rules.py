import pathlib,json,urllib.request,hashlib,concurrent.futures,re,time
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'public/data/plans'
index=json.loads((OUT/'index.json').read_text(encoding='utf-8'))
def parse(raw,old,body):
    mods=[];seen=set()
    def walk(m,parent=None):
        title=m.get('nameZh') or (m.get('type') or {}).get('nameZh') or '方案总览'
        base=str(m['id']); identity=(base,title,str(m.get('parentAssoc')),m.get('level'))
        if identity in seen:return
        seen.add(identity)
        key=base if not any(a['id']==base for a in mods) else base+'~'+str(len(mods))
        row={'id':key,'rawId':base,'parent':str(m['parentAssoc']) if m.get('parentAssoc') is not None else parent,'level':m.get('level'),'title':title,'type':(m.get('type') or {}).get('code'),'rule':m.get('requireInfo') or {},'limit':m.get('limitInfo') or {},'note':'\n'.join(str(m.get(f) or '') for f in ['labelText','commentText','remark']).strip(),'reference':m.get('reference',False),'referenceId':str(m['referenceCourseModuleAssoc']) if m.get('referenceCourseModuleAssoc') is not None else None,'courses':[]}
        for c in m.get('planCourses') or m.get('realPlanCourses') or []:
            d=c.get('course') or {}; row['courses'].append({'code':d.get('code',''),'name':d.get('nameZh',''),'credits':d.get('credits',0),'required':bool(c.get('compulsory')),'term':c.get('termsText'),'rule':{k:c.get(k) for k in ['requiredCourse','integrationCompulsory','postGraduateDegreeType']}})
        mods.append(row)
        for ch in m.get('children') or []:walk(ch,key)
    for m in raw['courseModules']:walk(m)
    old.update(modules=mods,completeModules=True,sha256=hashlib.sha256(body).hexdigest(),fetchedAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    old['programNotes']=[{'title':p.get('titleZh'),'text':re.sub('<[^>]+>','',p.get('contentZh') or '')} for p in (raw.get('document') or {}).get('paragraphs',[]) if p.get('contentZh')]
    return old
def fetch(item):
    path=OUT/(item['id']+'.json');old=json.loads(path.read_text(encoding='utf-8'))
    if old.get('completeModules'):return item['id'],'cached'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(old['source'],timeout=35) as r:body=r.read()
            raw=json.loads(body); value=parse(raw,old,body)
            path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
            return item['id'],'ok'
        except Exception as e:
            if attempt==2:return item['id'],type(e).__name__
            time.sleep(1)
report=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for result in pool.map(fetch,sorted(index,key=lambda i:i['id'] not in ['152034','466'])):
        report.append(result)
        if len(report)%20==0:print(len(report),result,flush=True)
(ROOT/'.sites-runtime/plan-refresh.json').write_text(json.dumps(report),encoding='utf-8')
print('Complete',len(report),'failures',[r for r in report if r[1] not in ['ok','cached']],flush=True)
