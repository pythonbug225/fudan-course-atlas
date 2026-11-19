import pathlib,json
R=pathlib.Path(__file__).resolve().parent;S=R/'sources'
codes={r['course_code'] for r in json.loads((S/'course_catalog.json').read_text(encoding='utf8'))};index={}
for f in sorted((S/'official/program-responses').glob('*.json')):
 d=json.loads(f.read_text(encoding='utf8'));seen=set()
 def walk(x,path):
  if isinstance(x,dict):
   c=x.get('course');dept=x.get('openDepartment') or {}
   if isinstance(c,dict) and c.get('code') and 'terms' in x:
    code=c['code'];key=(code,c['nameZh'],str(x.get('terms')),x.get('compulsory'))
    if key not in seen and (code in codes or dept.get('id')==2621 or code.startswith(('JCM','MJC'))):
     seen.add(key);index.setdefault(code,[]).append({'program':f.stem,'program_name':d['model']['nameZh'],'code':code,'name':c['nameZh'],'department':dept.get('nameZh'),'terms':x.get('terms'),'terms_text':x.get('termsText'),'compulsory':x.get('compulsory'),'path':path})
   for k,v in x.items():walk(v,path+'.'+k)
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,path+f'[{i}]')
 walk(d['courseModules'],'$.courseModules')
(S/'program-course-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('program codes',len(index),'program-only',len(set(index)-codes),'memberships',sum(map(len,index.values())))
