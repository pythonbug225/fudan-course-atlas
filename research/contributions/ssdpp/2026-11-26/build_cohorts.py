"""Offline, cohort-scoped normalization and relationship graph construction."""
import collections, csv, gzip, hashlib, html, io, json, re, unicodedata
from pathlib import Path
R=Path(__file__).resolve().parent
def load(p):
    b=p.read_bytes()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(s.encode('utf-8'))
def save(p,v):write(p,json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def csvout(p,rows,fields):
    s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader()
    for row in rows:w.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(list,dict)) else row.get(k) for k in fields})
    write(p,'\ufeff'+s.getvalue())
def norm(s):return re.sub(r'[\s()（）,，、]','',unicodedata.normalize('NFKC',s or '')).lower()
def flatten(v,path=''):
    if isinstance(v,dict):
        for k,z in v.items():yield from flatten(z,path+'/'+k)
    elif isinstance(v,list):
        for i,z in enumerate(v):yield from flatten(z,path+'/'+str(i))
    else:yield path,v
TOPICS={'psych':'心理学与认知','social':'社会学与人类学','work':'社会工作与实务','data':'统计、计算与方法','general':'公共基础与跨学科','activity':'培养环节'}
TYPES={'curriculum_sequence':{'label':'官方课程体系图顺序','directed':True,'mandatory':False},'recommended_preparation':{'label':'建议知识准备（推断）','directed':True,'mandatory':False},'content_link':{'label':'内容联系（推断，无方向）','directed':False,'mandatory':False}}

def build(year):
    root=R/str(year);official=root/'official';out=root/'course-graph';out.mkdir(exist_ok=True)
    plans=load(official/'programmes.json');rows=[];modules=[];nodes={};audit={'cohort':year,'plan_checks':[],'prerequisite_field_instances':[],'keyword_hits':[],'hard_prerequisites_verified':0,'explicit_recommendations_verified':0,'figure_reviews':[]}
    for p in plans:
        pid=p['plan_id'];d=load(official/p['detail_path']);assert str(d['model']['grade'])==str(year)
        audit['plan_checks'].append({'plan_id':pid,'detail_sha256':hashlib.sha256((official/p['detail_path']).read_bytes()).hexdigest(),'word_sha256':p['word_sha256']})
        # Include absent/empty field evidence without interpreting it as no prerequisites.
        def scan(v,path=''):
            if isinstance(v,dict):
                for k,z in v.items():
                    if 'pre' in k.lower() and 'course' in k.lower():audit['prerequisite_field_instances'].append({'plan_id':pid,'pointer':path+'/'+k,'empty':not bool(z),'value':z})
                    scan(z,path+'/'+k)
            elif isinstance(v,list):
                for i,z in enumerate(v):scan(z,path+'/'+str(i))
            elif isinstance(v,str) and re.search(r'先修|先行课程|前置课程|先修读|prerequisite',v,re.I):audit['keyword_hits'].append({'plan_id':pid,'pointer':path,'quote':v})
        scan(d)
        for mi,m in enumerate(d['courseModules']):
            label=m.get('nameZh') or (m.get('type') or {}).get('nameZh') or m.get('labelText') or '未命名模块'
            modules.append({'plan_id':pid,'module_id':m['id'],'module':label,'level':m.get('level'),'parent_id':m.get('parentAssoc'),'requirements':m.get('requireInfo'),'comment':m.get('commentText'),'remark':m.get('remark'),'pointer':f'/courseModules/{mi}'})
            for ci,c in enumerate(m.get('planCourses',[])):
                cc=c['course'];code=str(cc['code']);name=cc['nameZh'];pointer=f'/courseModules/{mi}/planCourses/{ci}'
                row={'cohort':year,'plan_id':pid,'plan_title':p['title'],'major':p['major_name'],'module':label,'module_level':m.get('level'),'course_code':code,'course_name':name,'credits':cc.get('credits'),'compulsory_field':c.get('compulsory'),'terms_text':c.get('termsText'),'suggest_terms_text':c.get('suggestTermsText'),'remark':c.get('remark'),'department':(cc.get('department') or {}).get('nameZh'),'pointer':pointer}
                rows.append(row)
                topic='activity' if code.isdigit() else 'psych' if code.startswith(('PSYC','APSY')) else 'work' if code.startswith('SWK') else 'social' if code.startswith('SOCI') else 'data' if code.startswith(('MATH','CS','AI')) else 'general'
                if any(w in name for w in ['统计','数据','机器学习','社会计算']):topic='data'
                n=nodes.setdefault(code,{'id':code,'name':name,'aliases':[],'cohort':year,'topic':topic,'topic_label':TOPICS[topic],'kind':'activity' if code.isdigit() else 'course','programs':[],'level':['本科方案列课（含所引研究生课）'],'offered_terms':[],'scope':'plan_only','prerequisite_status':'未核定强制先修'})
                if name not in n['aliases']:n['aliases'].append(name)
                n['programs'].append({'plan_id':pid,'plan_name':p['title'],'module':label,'terms_text':c.get('termsText'),'suggest_terms_text':c.get('suggestTermsText'),'remark':c.get('remark'),'pointer':pointer})
    portal_plans=plans[:]
    if year==2024:
        annual=load(official/'annual/metadata.json');annual_rows=load(official/'annual/courses.json')
        for sec in annual['sections']:
            plans.append({'plan_id':sec['id'],'title':'2024年度汇编／'+sec['major']+'专业（含普通、留学生修读建议）','major_name':sec['major'],'detail_path':'annual/courses.json','detail_url':annual['source_url'],'word_sha256':None,'SHA256':None,'pdf_sha256':annual['source_sha256']})
        for i,r in enumerate(annual_rows):
            row=dict(r,pointer='/'+str(i),credits=None,compulsory_field=None,terms_text=None,suggest_terms_text=None,remark='详见所标PDF页码及原表格单元格，未从合并单元格猜测学分或学期。',source_kind='annual_pdf')
            rows.append(row);code=row['course_code'];name=row['course_name'];pid=row['plan_id']
            topic='psych' if '心理' in name or ('psychology' in pid and code.startswith('SOCI')) else 'work' if 'social-work' in pid and code.startswith('SOCI') else 'social' if code.startswith('SOCI') else 'data' if code.startswith(('MATH','CS','AI')) else 'general'
            if any(w in name for w in ['统计','数据','计算']):topic='data'
            n=nodes.setdefault(code,{'id':code,'name':name,'aliases':[],'cohort':year,'topic':topic,'topic_label':TOPICS[topic],'kind':'course','programs':[],'level':['2024年度汇编列课'],'offered_terms':[],'scope':'plan_only','prerequisite_status':'未核定强制先修'})
            if name not in n['aliases']:n['aliases'].append(name)
            n['programs'].append({'plan_id':pid,'plan_name':row['plan_title'],'module':row['module'],'terms_text':None,'suggest_terms_text':None,'remark':f'年度汇编PDF第{row["pdf_page"]}页／印刷第{row["printed_page"]}页；'+row['population_scope'],'pointer':'/'+str(i)})
        audit['annual_pdf']={'sha256':annual['source_sha256'],'pages_reviewed':[n for sec in annual['sections'] for n in sec['pages']],'keyword_hits':[{'page':k,'text':v['text']} for k,v in load(official/'annual/pages.json').items() if re.search('先修|前置课程|先行课程|prerequisite',v['text'],re.I)],'note':'年度汇编的三专业章节及普通／留学生修读建议单独保留，不与系统现行代码自动互认。'}
    save(official/'courses.json',rows);save(official/'modules.json',modules)
    csvout(official/'courses.csv',rows,list(dict.fromkeys(k for r in rows for k in r)))
    write(root/'社会发展与公共政策学院课程名单.txt','\n'.join(sorted({n['name'] for n in nodes.values() if n['kind']=='course'}))+'\n')
    sources={p['plan_id']:{'title':p['title'],'path':'../official/'+p['detail_path'],'url':p['detail_url'],'word_sha256':p.get('word_sha256'),'pdf_sha256':p.get('pdf_sha256')} for p in plans}
    edges={};pathways=[];rules=load(R/'relationship-proposals.json')
    def applicable(code):return {p['plan_id'] for p in nodes[code]['programs']}
    def ev(code,plan):
        row=next(r for r in rows if r['course_code']==code and r['plan_id']==plan)
        return {'source':plan,'pointer':row['pointer']+('/course_name' if row.get('source_kind')=='annual_pdf' else '/course/nameZh'),'observed_title':row['course_name'],'locator':row['module']+'／'+row['course_name']+(f'／PDF第{row["pdf_page"]}页' if row.get('pdf_page') else '')}
    def add(a,b,kind,reason,planids=None,evidence=None):
        if a not in nodes or b not in nodes or a==b:return
        if kind=='content_link':a,b=sorted([a,b])
        common=applicable(a)&applicable(b)
        if planids is not None:common&=set(planids)
        # Directed learning suggestions must be possible within at least one same plan.
        if kind!='content_link' and not common:return
        key=(a,b,kind)
        if evidence is None:
            evidence=[ev(a,sorted(applicable(a))[0]),ev(b,sorted(applicable(b))[0])]
        if key in edges:
            old=edges[key];old['applicable_plan_ids']=sorted(set(old['applicable_plan_ids'])|common)
            for item in evidence:
                if item not in old['evidence']:old['evidence'].append(item)
            return
        edges[key]={'id':'E'+hashlib.sha256((str(year)+'|'+'|'.join(key)).encode()).hexdigest()[:12],'source':a,'target':b,'type':kind,'directed':kind!='content_link','mandatory':False,'basis':'official_figure_arrow' if kind=='curriculum_sequence' else 'title_and_discipline_inference','confidence':'high' if kind=='curriculum_sequence' else 'provisional','reason':reason,'evidence':evidence,'applicable_plan_ids':sorted(common),'context':'仅适用于所标年级与方案。图中顺序和知识准备均不表示教务选课门槛；内容联系不表示课程等价或学分互认。','credit_equivalence':False}
    for rule in rules['edges']:
        a,b=rule['source'],rule['target']
        if a not in nodes or b not in nodes:continue
        if norm(rule['source_name']) not in {norm(s) for s in nodes[a]['aliases']} or norm(rule['target_name']) not in {norm(s) for s in nodes[b]['aliases']}:continue
        add(a,b,rule['type'],rule['reason'])
    if year==2024:
        # Same-title rule reuse proposes knowledge links only, never code equivalence.
        for sec in annual['sections']:
            pid=sec['id'];title_codes=collections.defaultdict(set)
            for r in annual_rows:
                if r['plan_id']==pid:title_codes[norm(r['course_name'])].add(r['course_code'])
            for rule in rules['edges']:
                aa=title_codes.get(norm(rule['source_name']),set());bb=title_codes.get(norm(rule['target_name']),set())
                if len(aa)==len(bb)==1:
                    a=next(iter(aa));b=next(iter(bb))
                    add(a,b,rule['type'],rule['reason'],[pid],[ev(a,pid),ev(b,pid)])
            for route in rules['pathways']:
                # Route labels are only included when every step resolves unambiguously.
                code_names={e[k]:e[k+'_name'] for e in rules['edges'] for k in ['source','target']}
                ids=[next(iter(title_codes[norm(code_names[c])])) if c in code_names and len(title_codes.get(norm(code_names[c]),set()))==1 else None for c in route['course_ids']]
                if None not in ids and len(ids)>1 and all((a,b,'recommended_preparation') in edges for a,b in zip(ids,ids[1:])):pathways.append({'title':'汇编／'+route['title'],'course_ids':ids,'status':'inferred_learning_path','applicable_plan_ids':[pid]})
    for route in rules['pathways']:
        ids=route['course_ids']
        # Do not bridge missing intermediate courses.
        chunks=[];chunk=[]
        for c in ids+[None]:
            if c in nodes:chunk.append(c)
            else:
                if len(chunk)>1:chunks.append(chunk)
                chunk=[]
        for chunk in chunks:
            if all((a,b,'recommended_preparation') in edges or (b,a,'recommended_preparation') in edges for a,b in zip(chunk,chunk[1:])):pathways.append({'title':route['title'],'course_ids':chunk,'status':'inferred_learning_path'})
    # Same title / H courses remain distinct nodes; these are content links only.
    byname=collections.defaultdict(list)
    for n in nodes.values():
        if n['kind']=='course' and n['name'] not in ['毕业论文','学年论文','前沿讲座']:byname[norm(n['name']).removesuffix('h')].append(n['id'])
    for codes in byname.values():
        for a,b in zip(sorted(codes),sorted(codes)[1:]):add(a,b,'content_link','题名相同或仅有H标记差异，提示核对内容；课程代码、专业背景与学分要求仍分别保留。')
    if year==2025:
        pid='97235';plan=next(p for p in plans if p['plan_id']==pid)
        im=next(x for x in plan['images'] if x['path'].endswith('rId6.png'))
        sid='figure-'+pid;sources[sid]={'title':plan['title']+'／课程体系原图','path':'../official/'+im['path'],'sha256':im['sha256'],'word_sha256':plan['word_sha256'],'word_member':im['member']}
        pairs=[('MATH10004','MATH10005'),('PHYS10003','PHYS10004'),('PSYC30001','PSYC30002'),('PSYC30017','PSYC30018'),('PSYC30002','PSYC30024'),('PSYC30018','PSYC30024'),('PSYC30018','SOCI30029'),('PSYC30024','PSYC30027'),('SOCI30029','PSYC30008'),('PSYC30027','PSYC30028'),('PSYC30029','PSYC30030')]
        for a,b in pairs:
            add(a,b,'curriculum_sequence','2025心理学普通方案课程体系原图以明确箭头连接这两个课程框；仅编码图示培养顺序。',[pid],[{'source':sid,'locator':nodes[a]['name']+' → '+nodes[b]['name']},ev(a,pid),ev(b,pid)])
        audit['figure_reviews'].append({'plan_id':pid,'source':sid,'verified_pairs':pairs,'not_encoded':['科研实践、复芏计划等宽泛环节的汇合箭头','原图中认知科学AI工程没有可直接对应的列课代码'],'review_note':'人工核读原图箭头，并在同一方案列课中逐一对应课程代码；不视为强制先修。'})
        for pid,issue in [('96675','图中“古典社会学理论”“社会统计学”与当前列课“经典社会学理论”“社会统计学基础”不一致，未跨标题替换代码。'),('97173','图中“社会研究方法A”“社会统计学”与列课“社会研究方法基础”“社会统计学基础”不一致，未将旧题名映射成新的官方课程边。')]:audit['figure_reviews'].append({'plan_id':pid,'verified_pairs':[],'review_note':issue})
    audit['word_text_keyword_scan']=[{'plan_id':p['plan_id'],'matches':[{'line':i+1,'text':s} for i,s in enumerate((official/'word-text'/('plan-'+p['plan_id']+'.txt')).read_text('utf8').splitlines()) if re.search('先修|前置课程|先行课程|prerequisite',s,re.I)]} for p in portal_plans]
    es=list(edges.values());connected={c for e in es for c in (e['source'],e['target'])}
    for n in nodes.values():n['relationship_status']='mapped' if n['id'] in connected else 'needs_syllabus'
    g={'schema_version':'2.0.0','generated_on':'2026-11-26','title':f'社会发展与公共政策学院 · {year}级课程关系图谱','cohort':year,'programmes':[{'id':p['plan_id'],'title':p['title'],'major':p['major_name']} for p in plans],'scope':{'department_id':2567,'plans':len(plans),'course_codes':sum(n['kind']=='course' for n in nodes.values()),'activity_codes':sum(n['kind']=='activity' for n in nodes.values()),'strict_prerequisite_edges_verified':0},'relation_types':TYPES,'topics':TOPICS,'sources':sources,'nodes':sorted(nodes.values(),key=lambda n:n['id']),'edges':es,'pathways':pathways,'limitations':['强制先修尚未核定。公开方案文字未检出逐课先修条款；字段缺失或为空均不等于没有先修。','橙色虚线为题名和一般学科知识的整理者推断；内容联系是共同议题，需逐课大纲复核。','每个年级独立建图；不将2026级备注或课程代码替换关系转用于往届。','课程表开课学期和培养方案建议学期不等于先修关系；本图不按学期先后自动连边。','不同方案的同名课和荣誉课分开；普通、留学生、港澳台侨生及双学位方案分别筛选。','没有连线的节点仍保留，表示需补充大纲。数字标识的复芏计划、讲座等作为培养环节，不计为正式课程代码。']}
    if year==2024:g['limitations'].insert(0,'2024级包含3份教务系统方案及年度汇编的社会学、社会工作、心理学3个章节；社会学有版本重叠。保留汇编十位课程代码与系统现行代码，不自动认定同名课学分等价。年度汇编普通及留学生修读建议在模块栏分别标识。')
    save(out/'graph.json',g);save(out/'source-audit.json',audit)
    csvout(out/'nodes.csv',g['nodes'],['id','name','cohort','kind','topic_label','aliases','programs','relationship_status'])
    csvout(out/'edges.csv',es,['id','source','target','type','directed','mandatory','basis','confidence','reason','applicable_plan_ids','evidence'])
    csvout(out/'待补关系.csv',[n for n in g['nodes'] if n['relationship_status']=='needs_syllabus'],['id','name','kind','relationship_status'])
    counts=collections.Counter(e['type'] for e in es)
    summary={'cohort':year,'plans':len(plans),'portal_plans':len(portal_plans),'annual_chapters':len(plans)-len(portal_plans),'nodes':len(nodes),'course_codes':g['scope']['course_codes'],'activity_codes':g['scope']['activity_codes'],'course_rows':len(rows),'relations':dict(counts),'edges':len(es),'connected_nodes':len(connected),'prerequisite_fields':len(audit['prerequisite_field_instances']),'keyword_hits':len(audit['keyword_hits'])}
    save(root/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':
    for y in [2023,2024,2025]:build(y)
