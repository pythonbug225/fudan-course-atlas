"""Build sourced Journalism cohort graphs offline; never infer enrollment rules."""
from pathlib import Path
import collections,csv,gzip,hashlib,html,itertools,json,re,shutil
W=Path(__file__).resolve().parent
ROOT=W.parent if W.name=='scripts' else W/'package'
S=ROOT/'cohorts' if W.name=='scripts' else W/'sources'
OUT=ROOT/'cohorts'; OUT.mkdir(parents=True,exist_ok=True)
REL=ROOT/'relations' if W.name=='scripts' else W/'relations'
DATE='2026-11-26'
TYPES={'verified_prerequisite':'官方明确先修','official_curriculum_link':'官方方案图联系','suggested_preparation':'建议先学','content_related':'内容联系','same_name_distinct_code':'同名异号'}
def load(p):
    if p.is_file():return json.loads(p.read_text('utf-8-sig'))
    return json.loads(gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def csvout(p,rows,fields):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fields,extrasaction='ignore');writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
def classify(name):
    for group,pattern in [('规范与伦理','法规|伦理|规制|法律|版权'),('研究与方法','方法|研究设计|论文|文献|统计|计算|数据分析|数据挖掘|可视化'),('广告与战略传播','广告|品牌|营销|消费|商业|公共关系|企业|战略|说服'),('国际与跨文化','跨文化|国际|全球|对外'),('视听与艺术','视听|影|纪录|音频|剧本|电视|动漫|播客|娱乐|音乐|镜前|美术'),('数字与智能媒介','新媒体|新媒介|媒介产品|平台|数字|智能|融合|交互|用户体验|网络'),('采访编辑与报道','采访|报道|编辑|新闻评论|新闻实务|新闻叙事|新闻作品|非虚构|核查'),('传播与社会','舆论|传播|媒介|心理|社会'),('新闻史与思想','新闻史|新闻思想|新闻学|新闻业'),('实践与毕业','实习|毕业|实践|工作坊|工作室'),('语言与表达','语言|英语|外语|口语')]:
        if re.search(pattern,name):return group
    return '公共与跨学科'
def mname(m):return m.get('nameZh') or (m.get('type') or {}).get('nameZh') or '未命名模块'

def extract(data,pid):
    rows={};modules=[]
    def walk(x,path,ancestors):
        if isinstance(x,dict):
            if any(k in x for k in ['planCourses','realPlanCourses','courseModuleHide']):
                ancestors=ancestors+[mname(x)]
                modules.append({'program_id':pid,'path':path,'name':mname(x),'module_path':' / '.join(ancestors),'requireInfo':x.get('requireInfo'),'remark':x.get('remark'),'reference':x.get('reference'),'showCourse':x.get('showCourse')})
            course=x.get('course')
            if isinstance(course,dict) and course.get('code') and 'terms' in x:
                key=(str(x.get('id')),course['code'],course.get('nameZh'))
                if key not in rows:
                    rows[key]={'program_id':pid,'code':course['code'],'name':course.get('nameZh') or course['code'],'plan_course_id':x.get('id'),'course_id':course.get('id'),'module':' / '.join(ancestors),'terms':x.get('termsText') or x.get('terms'),'suggested_terms':x.get('suggestTermsText') or x.get('suggestTerms'),'credits':course.get('credits'),'compulsory':x.get('compulsory'),'remark':x.get('remark'),'requiredCourse':x.get('requiredCourse'),'department':(x.get('openDepartment') or {}).get('nameZh'),'department_id':(x.get('openDepartment') or {}).get('id'),'source_path':path,'all_source_paths':[path]}
                elif path not in rows[key]['all_source_paths']:rows[key]['all_source_paths'].append(path)
            for k,v in x.items():walk(v,path+'.'+k,ancestors)
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,path+f'[{i}]',ancestors)
    walk(data.get('courseModules',[]),'$.courseModules',[])
    return list(rows.values()),modules

def build(year):
    source=S/str(year)/'official'
    target=OUT/str(year)/'official'
    if source.resolve()!=target.resolve():
        shutil.copytree(source,target,dirs_exist_ok=True)
        for raw in (target/'raw').glob('plan-*.json'):
            content=raw.read_bytes();compressed=gzip.compress(content,mtime=0)
            assert gzip.decompress(compressed)==content
            raw.with_suffix('.json.gz').write_bytes(compressed);raw.unlink()
        metas=load(target/'programmes.json')
        for meta in metas:
            original=meta['raw_path'];meta['original_raw_path']=original;meta['raw_path']=original+'.gz';meta['raw_compression']='gzip; raw_sha256 refers to the exact decompressed original response'
            mf=target/'metadata'/f'plan-{meta["plan_id"]}.json'
            if mf.exists():put(mf,meta)
        put(target/'programmes.json',metas)
    out=OUT/str(year)/'course-graph';out.mkdir(parents=True,exist_ok=True)
    plans=load(target/'programmes.json');records=[];modules=[];programs=[]
    for meta in plans:
        pid=str(meta['plan_id']);p=target/'raw'/f'plan-{pid}.json';data=load(p)
        assert str(data['model'].get('grade'))==str(year),(year,pid,'wrong_cohort')
        assert str(data['model']['id'])==pid
        rows,ms=extract(data,pid)
        for row in rows:
            row['source_locator']=row['source_path'];row['source_path']=f'{year}/official/raw/plan-{pid}.json.gz';row['all_source_locators']=row.pop('all_source_paths')
        records.extend(rows);modules.extend(ms)
        programs.append({'id':pid,'title':meta['title'],'department':meta.get('department'),'word_path':f'{year}/official/'+meta['word_path'],'json_path':f'{year}/official/raw/plan-{pid}.json.gz','official_url':meta['detail_url'],'course_occurrences':len(rows),'unique_courses':len({(r['code'],r['name']) for r in rows})})
    by=collections.defaultdict(list);names_by_code=collections.defaultdict(set)
    for row in records:by[row['code'],row['name']].append(row);names_by_code[row['code']].add(row['name'])
    nodes=[];lookup={}
    for (code,name),rows in sorted(by.items()):
        nid=code if len(names_by_code[code])==1 else code+'@'+hashlib.sha256(name.encode()).hexdigest()[:8]
        lookup[code,name]=nid
        nodes.append({'id':nid,'code':code,'name':name,'group':classify(name),'is_department_course':any(r['department_id']==2621 for r in rows) or code.startswith(('JCM','MJC')),'program_ids':sorted({r['program_id'] for r in rows}),'memberships':rows,'prerequisite_status':'unverified','source_scope':'explicitly_listed_in_cohort_plan'})
    byid={n['id']:n for n in nodes};edges={};rejected=[]
    rel=load(REL/f'{year}.json')
    for r in rel['relations']:
        a=lookup.get((r['source_code'],r['source_name']));b=lookup.get((r['target_code'],r['target_name']))
        if not a or not b:rejected.append({'reason':'endpoint_not_exactly_matched','relation':r});continue
        common=set(byid[a]['program_ids'])&set(byid[b]['program_ids']);scope=sorted(set(map(str,r['program_ids']))&common)
        if not scope:rejected.append({'reason':'no_common_plan','relation':r});continue
        kind=r['type'];assert kind in TYPES
        directed=kind in ['verified_prerequisite','official_curriculum_link','suggested_preparation']
        if not directed:a,b=sorted([a,b])
        evidence=[]
        for e in r['evidence']:
            item=dict(e);path=item.get('path','').replace('\\','/')
            if path.startswith('sources/'):path=path[8:]
            if not path.startswith(str(year)+'/'):path=f'{year}/'+path
            if not (OUT/path).is_file() and (OUT/(path+'.gz')).is_file():path+='.gz'
            assert (OUT/path).is_file(),('missing_evidence',path)
            item['path']=path;evidence.append(item)
        key=(a,b,kind)
        if key not in edges:edges[key]={'source':a,'target':b,'type':kind,'directed':directed,'reason':r['reason'],'evidence':evidence,'program_ids':scope,'is_enrollment_prerequisite':kind=='verified_prerequisite','confidence':'inferred' if kind in ['suggested_preparation','content_related'] else 'official_source'}
        else:
            edges[key]['program_ids']=sorted(set(edges[key]['program_ids'])|set(scope))
            for e in evidence:
                if e not in edges[key]['evidence']:edges[key]['evidence'].append(e)
    assert not rejected,('relations_need_review',year,rejected[:2])
    byname=collections.defaultdict(list)
    for n in nodes:byname[n['name']].append(n)
    for name,ns in byname.items():
        for left,right in itertools.combinations(ns,2):
            common=sorted(set(left['program_ids'])&set(right['program_ids']))
            if not common:continue
            a,b=sorted([left['id'],right['id']]);pid=common[0]
            edges[a,b,'same_name_distinct_code']={'source':a,'target':b,'type':'same_name_distinct_code','directed':False,'reason':f'同名“{name}”但课号不同，保留独立节点；不表示课程替代或学分互认。','evidence':[{'path':f'{year}/official/raw/plan-{pid}.json.gz','locator':'$.courseModules（按两端课号定位）','kind':'exact_name_match'}],'program_ids':common,'is_enrollment_prerequisite':False,'confidence':'exact_name_only'}
    edge_list=[]
    for i,(key,e) in enumerate(sorted(edges.items())):
        e={'id':f'{year}-e{i+1:04}',**e,'inferred':e['type'] in ['suggested_preparation','content_related']};edge_list.append(e)
    audit={**rel['audit'],'cohort':year,'plans':len(plans),'nodes':len(nodes),'course_codes':len(names_by_code),'course_occurrences':len(records),'department_nodes':sum(n['is_department_course'] for n in nodes),'edges':len(edge_list),'relation_types':dict(collections.Counter(e['type'] for e in edge_list)),'confirmed_hard_prerequisites':sum(e['is_enrollment_prerequisite'] for e in edge_list),'isolated_nodes':len(set(byid)-{e[k] for e in edge_list for k in ['source','target']}),'same_code_multiple_names':{c:sorted(ns) for c,ns in names_by_code.items() if len(ns)>1},'scope_notes':['图谱包含本年级所有方案明确列出的课程，通识候选课与专业课均保留；列出不代表全部必修。','学期字段保留原文。春/秋开课季节、建议学期和方案图箭头均不自动转成选课先修。','同码异名分为不同节点；不跨年套用2026课号或方案箭头。','内容联系与建议先学为整理者推断，未取得逐班教学大纲。']}
    graph={'schema':'fudan-journalism-cohort-graph/1','cohort':year,'generated_date':DATE,'relation_types':TYPES,'nodes':nodes,'edges':edge_list,'programs':programs,'audit':audit}
    put(out/'graph.json',graph);put(out/'source-audit.json',audit);put(out/'program-course-memberships.json',records);put(out/'modules.json',modules)
    csvout(out/'nodes.csv',nodes,['id','code','name','group','is_department_course','program_ids','prerequisite_status'])
    csvout(out/'edges.csv',edge_list,['id','source','target','type','directed','reason','program_ids','evidence','inferred','is_enrollment_prerequisite'])
    csvout(out/'program-course-memberships.csv',records,['program_id','code','name','module','terms','suggested_terms','credits','compulsory','department','source_path','source_locator'])
    (OUT/str(year)/'新闻学院课程名单.txt').write_text('\n'.join(sorted({n['name'] for n in nodes if n['is_department_course']}))+'\n',encoding='utf8')
    return graph

def main():
    graphs={str(y):build(y) for y in [2023,2024,2025]}
    data={'metadata':{'date':DATE,'title':'新闻学院 2023—2025 级课程关系图谱','scope':'各年级官方培养方案快照，非当期开课表','relation_types':TYPES},'cohorts':graphs}
    put(OUT/'graphs.json',data)
    template=(W/'viewer-template.html').read_text('utf8')
    (OUT/'课程关系图谱.html').write_text(template.replace('__GRAPH_DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')),encoding='utf8')
    print(json.dumps({y:{k:g['audit'][k] for k in ['plans','nodes','department_nodes','edges','confirmed_hard_prerequisites']} for y,g in graphs.items()},ensure_ascii=False))
if __name__=='__main__':main()
