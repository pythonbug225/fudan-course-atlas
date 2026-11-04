import json, pathlib, shutil, hashlib
import ijson
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=pathlib.Path('D:/danxi/outputs/all-school-audit-20261031/scope')
OUT=ROOT/'public/data/plans'; OUT.mkdir(parents=True,exist_ok=True)
def compact(p,public=False):
    mods={}; rows=p.get('courses',p.get('course_rows',[]))
    for r in rows:
        for a in r.get('module_ancestors',[]):
            k=str(a['module_id'])
            if k not in mods:
                mods[k]={'id':k,'parent':str(a['parent_module_id']) if a.get('parent_module_id') is not None else None,'title':a.get('module_title') or '方案总览','type':a.get('type_code'),'rule':a.get('requireInfo') or {},'limit':a.get('limitInfo') or {},'note':'\n'.join(str(a.get(f) or '') for f in ['labelText','commentText']).strip(),'reference':a.get('reference',False),'courses':[]}
        k=str(r['module_id'])
        if k not in mods: continue
        mods[k]['courses'].append({'code':r['course_code'],'name':r['course_name'],'credits':r.get('credits') or 0,'required':bool(r.get('compulsory')),'term':r.get('planned_term'),'rule':r.get('course_requirement_direct',{})})
    return {'id':str(p['id']),'title':p.get('name') or p.get('model_name'),'department':p.get('department'),'public':public,'source':p.get('url') or p.get('source_url'),'sha256':p.get('response_sha256'),'effective':p.get('model_fields',{}).get('effectiveOn'),'fields':{k:p.get('model_fields',{}).get(k) for k in ['credits','duration','termsCount','integrationType','x2Plan','y2Plan','enhancePlan','doublePlan']},'modules':list(mods.values()),'rowCount':len(rows)}
def write(p):
    (OUT/(p['id']+'.json')).write_text(json.dumps(p,ensure_ascii=False,separators=(',',':'),default=float),encoding='utf-8')
    return {k:p[k] for k in ['id','title','department','public','rowCount']}|{'modules':len(p['modules'])}
index=[]
with open(SRC/'fresh-plan-details-with-module-labels.json','rb') as f:
    for key,p in ijson.kvitems(f,'professional_program_details.programs'):
        index.append(write(compact(p)))
        if len(index)%50==0: print('plans',len(index),flush=True)
p=json.load(open(SRC/'fresh-public-plan-466-with-module-labels.json',encoding='utf-8'))
index.append(write(compact(p,True)))
(OUT/'index.json').write_text(json.dumps(index,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(json.dumps({'plans':len(index),'modules':sum(x['modules'] for x in index),'rows':sum(x['rowCount'] for x in index),'bytes':sum(p.stat().st_size for p in OUT.glob('*.json'))}))
