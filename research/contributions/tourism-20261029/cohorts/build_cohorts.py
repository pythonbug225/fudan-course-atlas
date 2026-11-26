"""Build per-cohort plan inventories and sourced course graphs, offline."""
import collections,csv,gzip,hashlib,html,importlib.util,itertools,json,re,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;O=W if (W/'2023/official').exists() else W/'package/cohorts';PREVIOUS=W.parent/'tourism-graph/package/course-graph'
recipe_file=W/'semantic-recipes.py' if (W/'semantic-recipes.py').exists() else PREVIOUS/'curation.py'
spec=importlib.util.spec_from_file_location('prior_curation',recipe_file);curation=importlib.util.module_from_spec(spec);spec.loader.exec_module(curation)
prior=json.loads((W/'semantic-seed.json' if (W/'semantic-seed.json').exists() else PREVIOUS/'graph.json').read_text('utf-8'));prior_nodes={n['id']:n for n in prior['nodes']}
prior_names={n['name']:n['group'] for n in prior['nodes']};group_titles={g['id']:g['name'] for g in prior['groups']}
group_titles.update({'public_options':'公共选修候选目录','curriculum':'方案模块'})
EXTRA=[
 ('数学分析BⅠ','数学分析BⅡ','数学分析B系列上、下阶段可按基础到延伸的顺序学习。'),
 ('高等数学A(上）','高等数学A(下）','同一数学系列的上、下部分按阶段学习。'),
 ('高等数学B(上）','高等数学B(下）','同一数学系列的上、下部分按阶段学习。'),
 ('高等数学C(上）','高等数学C(下）','同一数学系列的上、下部分按阶段学习；与A/B路线分别保留。'),
 ('线性代数','统计学','向量和矩阵的认识可为定量分析作准备；不是选课硬门槛。'),
 ('统计学','旅游市场研究','统计方法可帮助组织和分析市场调查资料。'),
 ('社会研究方法B','旅游研究方法','一般社会研究的提问和证据意识可用于旅游研究。'),
 ('旅游研究方法','学年论文','研究设计和资料组织可为学年论文作准备。'),
 ('管理学导论','旅游人力资源管理','组织与管理的基础认识可用于人力资源问题。'),
 ('旅游发展规划','旅游项目管理','发展规划的整体认识可为具体项目组织作准备。'),
 ('旅游资源学','旅游景观考察','资源的基本认识可为实地观察和考察作准备。'),
 ('旅游学原理','导游学','旅游系统与游客活动的认识可支持导游主题学习。'),
 ('社会研究方法B','口述历史','资料获取方法可为口述资料研究作准备；具体访谈要求需另核。'),
 ('文化遗产管理','展览内容策划','遗产管理与展览策划可在文化阐释场景中联系。'),
 ('展览内容策划','展览形式设计','先明确叙事内容再选择展示形式是一种可迭代的工作顺序。'),
 ('旅游接待业','商务旅行管理','接待业与商务旅行可从细分服务场景联系。'),
 ('旅游信息系统','大数据与旅游管理创新','信息系统与数据驱动创新存在技术应用主题联系。'),
 ('旅游法规','经济法','行业规范与经济活动中的法律问题可相互参照。'),
 ('旅游景观考察','教学实习','考察与实习可积累观察材料和实践问题。'),
 ('旅游社会学','中国古代乡村社会','旅游社会现象与乡村社会史可以在社会结构视角下比较。'),
 ('教学实习','旅游实践与社会服务','两课均涉及实践活动；不据此认定学分互认。'),
 ('旅游消费者行为','旅游营销管理','消费者认识可支持营销决策。'),
 ('会计学','财务管理','先理解会计信息，再学习财务决策是可行的准备顺序。'),
 ('旅游文献阅读','学年论文','文献阅读可支持论文的问题形成与论证。'),
 ('学年论文','毕业论文','前期论文训练可为毕业研究作准备。'),
]
EXTRA_CONTENT=[
 ('旅游收益管理','旅游财务管理','收益、收入与财务决策可以从不同管理尺度比较。'),
 ('国际旅游服务贸易','旅游与跨文化沟通','跨境旅游服务与跨文化沟通共享国际服务场景。'),
 ('中国古代城市史','旅游发展规划','城市发展史与旅游规划可围绕空间变迁和文化背景比较。'),
 ('中国文学经典','文化遗产理论与方法','文学材料可为文化遗产的解释提供一种文化背景，不推断两课具体章节。'),
 ('哲学导论','旅游伦理学','哲学中的价值思考可与旅游实践中的伦理问题联系。'),
 ('逻辑学','社会研究方法','逻辑与论证能力可支持研究设计和证据解释。'),
 ('旅游英语','旅游与文化遗产文献阅读','语言能力可辅助文献阅读；不据此推断文献课具体语种或入课要求。'),
 ('中国古代礼制研究','文化遗产活化利用案例研究','礼制的历史语境可为遗产解释和案例分析提供背景。'),
 ('中国古代社会生活史','文化遗产与城市旅游','城市文化与社会生活的历史联系可用于遗产旅游问题的比较。'),
 ('明清文化史','旅游文化学','历史文化材料与旅游文化主题可以相互参照。'),
 ('旅游文化学','旅游与文化遗产文献阅读','文化主题与相关文献利用存在研究对象层面的联系。'),
 ('旅游人力资源管理','旅游接待业','接待业的人员组织与培训可与人力资源管理主题联系。'),
 ('商务旅行管理','旅行社经营管理','商务旅行服务与旅行社经营共享行程、客户和服务链场景。'),
 ('旅游项目管理','会展管理','项目组织与会展运营可在时间、资源和参与者协调方面比较。'),
 ('导游学','旅游与跨文化沟通','导游服务与跨文化沟通可围绕游客交流场景联系。'),
 ('旅游景观考察','旅游资源学','资源识别与景观观察具有相互支持的内容联系。'),
 ('大数据与旅游管理创新','旅游信息系统','两课可从数据组织与管理应用的角度相互参照，未核实具体软件。'),
 ('旅游实践与社会服务','教学实习','两者都是实践性培养条目，课程资格和学分互认需另查。'),
 ('口述历史','社会研究方法B','口述资料与社会研究可围绕资料获取和解释方法联系。'),
 ('展览内容策划','文化遗产管理','遗产阐释与展览叙事共享文化表达问题。'),
 ('展览形式设计','旅游策划学','展览表达与旅游策划可从体验设计的应用场景比较。'),
 ('中国古代乡村社会','旅游社会学','乡村社会史与旅游社会学可从社区、社会关系和变迁比较。'),
 ('统计学','旅游研究方法','统计分析可作为研究方法体系中的一类方法，不能替代全部研究设计。'),
 ('线性代数','旅游信息系统','数量表达与信息组织存在能力层面的联系，具体技术要求待核。'),
 ('经济法','旅游法规','一般经济规范与旅游行业法规可以互相参照。'),
 ('政治经济学','旅游经济学','不同经济学视角可共同分析旅游经济活动。'),
 ('旅游文化学','中国民俗旅游','文化观念与民俗旅游可从文化表达及历史背景联系。'),
 ('旅游资源学','文化遗产管理','资源利用与遗产保护在对象和决策目标上存在交集。'),
 ('旅游发展规划','旅游目的地管理','规划选择与目的地治理可以从长期发展和日常管理两个角度比较。'),
 ('旅游研究方法','旅游市场研究','一般研究设计与市场研究在证据和资料分析方面相交。'),
]
def load(p):
 if p.exists():return json.loads(p.read_text('utf-8-sig'))
 return json.loads(gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def esc(s):return html.escape(str(s or ''))
def sourceurl(pid):return 'https://fdjwgl.fudan.edu.cn/manager/bizType/2/major-program-search/info/'+str(pid)+'?skipAuth=1'
def module_name(m):return m.get('nameZh') or (m.get('type') or {}).get('nameZh') or '未命名模块'
def norm(name):return name.replace('（','(').replace('）',')').replace(' ','').replace('\u3000','')
def writecsv(p,rows,fields):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fields,extrasaction='ignore');writer.writeheader()
  for row in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items() if k in fields})
def classify(name):
 if name in prior_names:return prior_names[name]
 for pattern,group in [('数学|代数|统计|政治经济','economics'),('人力资源|项目管理|商务旅行|导游','operations'),('研究方法|口述|社会服务|景观考察','research'),('大数据','digital'),('展览|乡村社会','heritage'),('经济法','public')]:
  if re.search(pattern,name):return group
 return 'theory'

def build(year):
 root=O/str(year);official=root/'official';out=root/'course-graph';out.mkdir(exist_ok=True)
 plans=load(official/'programmes.json');rows=[];modules=[];audit=[];sources={};courses={};module_nodes=[];rule_map={};hard_evidence=[]
 for meta in plans:
  pid=meta['plan_id'];data=load(official/'raw'/('plan-'+pid+'.json'));model=data['model'];student=(model.get('stdType') or {}).get('nameZh','未明');cult=(model.get('cultivateType') or {}).get('nameZh','未明')
  meta['student_type']=student;meta['cultivation_type']=cult
  assert str(model.get('grade'))==str(year) and int(model.get('id'))==int(pid)
  sid='PLAN-'+pid;sources[sid]={'title':meta['title'],'url':'../official/raw/plan-'+pid+'.json.gz','official_url':meta['detail_url'],'word_url':'../official/'+meta['word_path'],'cohort':year,'student_type':student,'department':meta['department']}
  ms=data.get('courseModules',[]);byid={m['id']:m for m in ms if m['id']>100}
  def ancestors(m):
   result=[m];seen={m['id']}
   while m.get('parentAssoc') in byid:
    m=byid[m['parentAssoc']]
    if m['id'] in seen:break
    seen.add(m['id']);result.append(m)
   return list(reversed(result))
  for mi,m in enumerate(ms):
   chain=ancestors(m);names=[module_name(v) for v in chain if module_name(v)!='未命名模块'];path=' / '.join(names)
   is_programme=not m.get('reference') or any(re.search('专业培养|学科基础|人文基础|社会科学基础|大类基础|专业核心|专业进阶',n) for n in names)
   mid=f'MODULE:{pid}:{mi}';module={'id':mid,'plan_id':pid,'cohort':year,'module_index':mi,'raw_module_id':m['id'],'module_name':module_name(m),'path':path,'scope':'programme' if is_programme else 'public_options','reference':bool(m.get('reference')),'require_info':m.get('requireInfo'),'limit_info':m.get('limitInfo'),'label_text':m.get('labelText'),'comment_text':m.get('commentText'),'remark':m.get('remark'),'locator':f'/courseModules/{mi}','course_row_count':len(m.get('planCourses',[]))};modules.append(module)
   if m.get('planCourses'):
    module_nodes.append({'id':mid,'name':module_name(m),'node_type':'curriculum_module','group':'curriculum','scope':'module','programmes':[pid],'memberships':[],'plan_placements':[],'business_types':['方案模块'],'teachers':[],'name_variants':[module_name(m)],'offerings':[],'module_path':path,'source_id':sid,'locator':module['locator']})
   for ci,pc in enumerate(m.get('planCourses',[])):
    c=pc.get('course') or {};code=str(c.get('code') or '').strip();name=c.get('nameZh') or c.get('name')
    if not code or not name:continue
    nums=[int(t.split('_')[1]) for t in pc.get('terms',[]) if re.fullmatch(r'TERM_[1-8]',str(t))];suggest=[int(t.split('_')[1]) for t in pc.get('suggestTerms',[]) if re.fullmatch(r'TERM_[1-8]',str(t))]
    row={'cohort':year,'plan_id':pid,'plan_title':meta['title'],'student_type':student,'cultivation_type':cult,'course_code':code,'course_name':name,'credits':c.get('credits'),'department':(pc.get('openDepartment') or c.get('department') or {}).get('nameZh'),'module_id':mid,'module_path':path,'scope':module['scope'],'compulsory_field':pc.get('compulsory'),'required_course_field':pc.get('requiredCourse'),'terms_raw':pc.get('terms',[]),'numbered_terms':nums,'suggest_terms_raw':pc.get('suggestTerms',[]),'numbered_suggest_terms':suggest,'remark':pc.get('remark'),'source':sid,'locator':f'/courseModules/{mi}/planCourses/{ci}'};rows.append(row)
    n=courses.setdefault(code,{'id':code,'name':name,'name_variants':[],'node_type':'research_activity' if not re.search('[A-Za-z]',code) else 'course','scope':'public_options','group':'public_options','programmes':[],'business_types':['本科（本年级方案收录）'],'teachers':[],'offerings':[],'plan_placements':[],'memberships':[],'prerequisite_status':'not_verified','cohort':year})
    if name not in n['name_variants']:n['name_variants'].append(name)
    if is_programme:n['scope']='programme';n['group']=classify(name)
    if pid not in n['programmes']:n['programmes'].append(pid)
    n['memberships'].append({'module_id':mid,'source':sid,'locator':row['locator'],'scope':module['scope']})
    n['plan_placements'].append({'plan_id':pid,'source':sid,'locator':row['locator'],'module_id':mid,'numbered_terms':nums,'numbered_suggest_terms':suggest,'terms_raw':row['terms_raw'],'student_type':student,'term_source':'api_terms'})
  hits=[];prefields=[]
  def scan(x,path=''):
   if isinstance(x,dict):
    for k,v in x.items():
     if re.search('precourse|prerequi',k,re.I):prefields.append({'locator':path+'/'+k,'value':v})
     scan(v,path+'/'+k)
   elif isinstance(x,list):
    for i,v in enumerate(x):scan(v,path+'/'+str(i))
   elif isinstance(x,str) and re.search('先修|预修|前置课程|先选|先读|修读顺序',x):hits.append({'locator':path,'text':x})
  scan(data);word=(official/'word-text'/('plan-'+pid+'.txt')).read_text('utf-8');words=[m.group(0) for m in re.finditer('.{0,25}(?:先修|预修|前置课程).{0,40}',word)]
  nonempty=[v for v in prefields if v['value']]
  assert not nonempty and not hits and not words,('Explicit prerequisite evidence needs human curation',pid)
  audit.append({'plan_id':pid,'cohort':year,'prerequisite_fields_found':prefields,'explicit_prerequisite_texts':hits,'word_prerequisite_mentions':words,'unexpanded_referenced_modules':[{'locator':f'/courseModules/{i}','name':module_name(m)} for i,m in enumerate(ms) if m.get('reference') and not m.get('planCourses')],'hard_prerequisites_verified':0,'conclusion':'官方本年级方案未提供可核实的课程对课程硬性先修；缺失字段不是“没有先修”的证明。公共模块未展开时不以其他年级课程补齐。'})
 put(official/'programmes.json',plans);put(official/'courses.json',rows);put(official/'modules.json',modules)
 writecsv(official/'courses.csv',rows,['cohort','plan_id','student_type','course_code','course_name','credits','department','module_path','scope','compulsory_field','terms_raw','numbered_terms','remark','locator'])
 for p in plans:
  prs=[r for r in rows if r['plan_id']==p['plan_id']];core={r['course_code'] for r in prs if r['scope']=='programme'};allids={r['course_code'] for r in prs};p['course_rows']=len(prs);p['unique_course_codes']=len(allids);p['programme_codes']=len(core);p['public_option_only_codes']=len(allids-core)
  parts=[f'<!doctype html><meta charset="utf-8"><title>{esc(p["title"])}</title><style>body{{font:15px/1.8 system-ui,"Microsoft YaHei";max-width:1200px;margin:28px auto;padding:20px;color:#253f50}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #d8e3e9;text-align:left;padding:7px}}.note{{background:#fff5dc;padding:15px}}details{{margin:15px 0}}a{{color:#116f92}}</style>',f'<h1>{esc(p["title"])}</h1><p>{esc(p["department"])} · {esc(p["student_type"])} · {esc(p["cultivation_type"])}</p><p><a href="{esc(p["word_path"])}">官方Word原件</a> · <a href="raw/plan-{p["plan_id"]}.json.gz">原始接口JSON</a> · <a href="{esc(p["detail_url"])}">官方详情</a> · <a href="../course-graph/index.html">本年级交互图谱</a></p><div class="note">本方案含{len(allids)}个去重代码，其中{len(core)}个属于专业/基础/科研培养条目，另{len(allids-core)}个仅见公共候选目录。课程行必修字段与模块选修规则需同时阅读，不代表每门均须修读。数字学期来自terms；春、秋表示季节，不作为数字学期或先修条件。</div>']
  for m in [m for m in modules if m['plan_id']==p['plan_id']]:
   mr=[r for r in prs if r['module_id']==m['id']]
   if not mr and not(m['label_text'] or m['require_info']):continue
   req='；'.join(str(x) for x in [m['label_text'],m['comment_text'],m['remark']] if x)
   parts.append(f'<details {"open" if m["scope"]=="programme" else ""}><summary><b>{esc(m["path"] or m["module_name"])}</b> · {len(mr)}条</summary><p>{esc(req)}</p><pre>{esc(json.dumps(m["require_info"],ensure_ascii=False))}</pre>')
   if mr:
    parts.append('<table><tr><th>代码</th><th>课程</th><th>学分</th><th>terms原字段</th><th>必修字段</th></tr>')
    for r in mr:parts.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in [r['course_code'],r['course_name'],r['credits'],'、'.join(r['terms_raw']),str(r['compulsory_field'])])+'</tr>')
    parts.append('</table>')
   parts.append('</details>')
  parts.append('<p>来源为本年级官方公开方案的2026-11-26快照；不代表入学当年未修订原版。原件权利归原权利人，未取得单独再利用许可声明。</p>');(official/('programme-'+p['plan_id']+'.html')).write_bytes(''.join(parts).encode('utf-8'))
 put(official/'programmes.json',plans)
 edges=[];seen=set()
 all_node_lookup={**courses,**{n['id']:n for n in module_nodes}}
 relation_types={'planned_before':f'{year}方案学期在先（非先修）','recommended_preparation':'建议先学（编辑判断）','content_related':'内容联系（编辑判断）','same_name_distinct_code':'同名异号（不代表互认）','module_membership':'方案模块收录（非先修）'}
 def add(a,b,kind,reason,refs):
  if a==b:return
  directed=kind in ['planned_before','recommended_preparation']
  if not directed and a>b:a,b=b,a
  key=(a,b,kind)
  if key in seen:return
  shared=sorted(set(all_node_lookup[a]['programmes'])&set(all_node_lookup[b]['programmes']))
  seen.add(key);edges.append({'id':f'{year}-E{len(edges)+1:04}','source':a,'target':b,'type':kind,'directed':directed,'mandatory':False,'credit_equivalence':False,'shared_plan_ids':shared,'reason':reason,'evidence':refs,'confidence':'方案字段事实；非先修' if kind in ['planned_before','module_membership'] else '编辑建议；具体大纲待核'})
 def refs(a,b):return [{'source':courses[c]['plan_placements'][0]['source'],'locator':courses[c]['plan_placements'][0]['locator'],'course':c} for c in [a,b]]
 nameindex=collections.defaultdict(list)
 for n in courses.values():
  if n['scope']=='programme':
   for name in n['name_variants']:nameindex[norm(name)].append(n['id'])
 def unique(name):
  codes=set(nameindex.get(norm(name),[]));return next(iter(codes)) if len(codes)==1 else None
 def sameplan(a,b):
  candidates=[]
  for left in courses[a]['plan_placements']:
   for right in courses[b]['plan_placements']:
    if left['plan_id']==right['plan_id'] and left['numbered_terms'] and right['numbered_terms'] and max(left['numbered_terms'])<min(right['numbered_terms']):
     pair=(left['plan_id'],tuple(left['numbered_terms']),tuple(right['numbered_terms']))
     if pair not in {x[0] for x in candidates}:candidates.append((pair,left,right))
  return candidates
 def semantic(a,b,reason,kind):
  ordered=sameplan(a,b)
  if kind=='recommended_preparation' and ordered:
   ev=[]
   for _,left,right in ordered:
    for c,side in [(a,left),(b,right)]:ev.append({'source':side['source'],'locator':side['locator'],'course':c,'plan_id':side['plan_id'],'terms':side['numbered_terms']})
   add(a,b,'planned_before','本年级同一方案中，前者的数字学期早于后者。'+reason+' 这里只表达方案安排，未认定强制先修。',ev)
  else:add(a,b,kind,reason,refs(a,b))
 skipped=[]
 for kind,recipes in [('recommended_preparation',curation.PLANNED+curation.PREPARATION),('content_related',curation.CONTENT)]:
  for ac,bc,reason in recipes:
   an=prior_nodes[ac]['name'];bn=prior_nodes[bc]['name'];a=unique(an);b=unique(bn)
   if not a or not b:
    skipped.append({'titles':[an,bn],'reason':'本年级未收录该题名或同名不唯一；未把2026课号和安排直接套用。'});continue
   if re.search(r'研究生|跨层次|第\d|2026|新版|课程体系图',reason):reason=f'《{an}》与《{bn}》可按相关概念、研究对象或方法建立联系；具体内容及资格要求需核对该年级大纲。'
   semantic(a,b,reason,kind)
 for an,bn,reason in EXTRA:
  a,b=unique(an),unique(bn)
  if a and b:semantic(a,b,reason,'recommended_preparation')
 for an,bn,reason in EXTRA_CONTENT:
  a,b=unique(an),unique(bn)
  if a and b:semantic(a,b,reason,'content_related')
 for n in courses.values():
  for membership in n['memberships']:add(n['id'],membership['module_id'],'module_membership','原方案在此模块列出该代码；仅表示收录与候选范围，不代表课程相互先修或均须修读。',[{'source':membership['source'],'locator':membership['locator']}])
 for title,ids in nameindex.items():
  for a,b in itertools.combinations(sorted(set(ids)),2):add(a,b,'same_name_distinct_code','本年级存在同名但代码不同的条目，分别保留；不认定替代或沿革。',refs(a,b))
 paths=[]
 for title,string,note in curation.PATHS:
  ids=[]
  for code in string.split():
   resolved=unique(prior_nodes[code]['name'])
   if resolved and resolved not in ids:ids.append(resolved)
  segments=[];segment=[]
  for code in ids:
   if not segment:segment=[code]
   elif any((e['source']==segment[-1] and e['target']==code) or (not e['directed'] and {e['source'],e['target']}=={segment[-1],code}) for e in edges):segment.append(code)
   else:
    if len(segment)>=2:segments.append(segment)
    segment=[code]
  if len(segment)>=2:segments.append(segment)
  for segment in segments:paths.append({'title':title,'course_ids':segment,'note':'逐边区分方案数字学期、编辑建议和内容联系；本年级适用对象按方案筛选。'})
 for names in [('统计与研究','统计学','旅游市场研究','旅游营销管理'),('数学分析路线','数学分析BⅠ','数学分析BⅡ'),('项目与实践','旅游发展规划','旅游项目管理'),('论文训练','旅游文献阅读','学年论文','毕业论文')]:
  ids=[unique(n) for n in names[1:]]
  if all(ids) and len(ids)>1:paths.append({'title':names[0],'course_ids':ids,'note':'编辑学习路径，各课程是否必修及何时修读需结合个人适用方案。'})
 core_count=sum(n['scope']=='programme' for n in courses.values());statistics={'course_entries':len(courses),'course_nodes':sum(n['node_type']=='course' for n in courses.values()),'activity_nodes':sum(n['node_type']!='course' for n in courses.values()),'programme_entries':core_count,'public_option_entries':len(courses)-core_count,'module_nodes':len(module_nodes),'edges':len(edges),'edge_types':dict(collections.Counter(e['type'] for e in edges)),'verified_hard_prerequisites':0,'plans':len(plans)}
 graph={'schema_version':'fudan-course-graph/cohort-1','title':f'旅游学系{year}级培养方案课程关系图谱','updated_at':'2026-11-26','cohort':year,'relation_types':relation_types,'groups':[{'id':g,'name':name} for g,name in group_titles.items()],'sources':sources,'programmes':[{'id':p['plan_id'],'name':p['title'],'student_type':p['student_type'],'cultivation_type':p['cultivation_type']} for p in plans],'statistics':statistics,'nodes':list(courses.values())+module_nodes,'edges':edges,'learning_paths':paths,'evidence_policy':'年度内按本方案字段核对；不合并跨年课号，不把学期在先/模块收录/编辑建议变成强制先修。'}
 put(out/'graph.json',graph);put(out/'source-audit.json',{'date':'2026-11-26','cohort':year,'plans':audit,'skipped_cross_year_recipes':skipped,'source_scope':'本年级官方方案公开当前快照，未采集该年级历史课表或逐班大纲；不回写2026图谱。','rule':'公共候选目录不等于全部必修；模块收录边单列；空先修字段不证明没有先修。'})
 writecsv(out/'nodes.csv',list(courses.values())+module_nodes,['id','name','node_type','scope','group','programmes','plan_placements','memberships'])
 writecsv(out/'edges.csv',edges,['id','source','target','type','directed','mandatory','reason','evidence'])
 simple=[e for e in edges if e['type']!='module_membership'];lines=[f'# 旅游学系{year}级课程关系与先修梳理','','正式硬性先修尚无可核实依据；以下将本年级数字学期安排和编辑建议分开。模块候选收录另见graph.json，不当作先修。','','![专业课程学习路径](overview.svg)','','## 逐条课程关系','','| 起点 | 终点 | 类型 | 理由 |','| --- | --- | --- | --- |']
 for e in simple:lines.append('| '+courses[e['source']]['name']+' '+e['source']+' | '+courses[e['target']]['name']+' '+e['target']+' | '+relation_types[e['type']]+' | '+e['reason']+' |')
 (out/'learning-paths.md').write_bytes(('\n'.join(lines)+'\n').encode('utf-8'))
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1660" height="{max(500,150+len(paths[:8])*125)}"><style>text{{font-family:Microsoft YaHei,system-ui,sans-serif}}.t{{font-size:28px;font-weight:bold;fill:#1e4d60}}.n{{font-size:15px;fill:#234b5d}}.s{{font-size:12px;fill:#5b7685}}</style><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="context-stroke"/></marker></defs><rect width="100%" height="100%" fill="#f1f6f8"/><text x="30" y="45" class="t">旅游学系 {year}级 · 课程关系与学习路径</text><text x="30" y="78" class="s">绿：本年级方案学期在先　橙虚线：编辑建议　蓝灰：内容联系　所有箭头均不作为已核实的强制先修</text>']
 for i,path in enumerate(paths[:8]):
  y=115+i*125;svg.append(f'<rect x="20" y="{y-12}" width="1620" height="113" rx="12" fill="white"/><text x="34" y="{y+23}" class="n">{esc(path["title"])}</text>')
  for j,code in enumerate(path['course_ids'][:5]):
   x=235+j*275;name=courses[code]['name'];svg.append(f'<rect x="{x}" y="{y}" width="245" height="62" rx="8" fill="#eaf3f6" stroke="#bdd1da"/><text x="{x+10}" y="{y+19}" class="s">{esc(code)}</text><text x="{x+10}" y="{y+44}" class="n">{esc(name)}</text>')
   if j:
    previous=path['course_ids'][j-1];es=[e for e in simple if (e['source']==previous and e['target']==code) or (not e['directed'] and {e['source'],e['target']}=={previous,code})]
    if es:
     e=es[0];col='#167e78' if e['type']=='planned_before' else '#b47427' if e['type']=='recommended_preparation' else '#7893a5';dash=' stroke-dasharray="6 4"' if e['type']=='recommended_preparation' else '';arrow=' marker-end="url(#a)"' if e['directed'] else '';svg.append(f'<line x1="{x-30}" x2="{x-5}" y1="{y+31}" y2="{y+31}" stroke="{col}" stroke-width="2"{dash}{arrow}/>')
  svg.append(f'<text x="235" y="{y+87}" class="s">{esc(path["note"])}</text>')
 svg.append('</svg>');(out/'overview.svg').write_bytes(''.join(svg).encode('utf-8'))
 template=(W/'viewer-template.html').read_text('utf-8');(out/'index.html').write_bytes(template.replace('__GRAPH_DATA__',json.dumps(graph,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')).encode('utf-8'))
 readme=f'''# 旅游学系{year}级培养方案与课程关系

本年级共取得 **{len(plans)}份方案原件**，去重 **{len(courses)}个课程/科研条目**，其中 **{core_count}个专业、基础或科研培养条目**，另 **{len(courses)-core_count}个仅见于公共候选目录**。图谱另设{len(module_nodes)}个方案模块节点；不能把全目录数量读作个人必修课数。

- [交互图谱](course-graph/index.html)：下载后打开，默认显示专业培养条目，可按方案、主题和公共目录范围筛选。
- [学习路径与课程关系](course-graph/learning-paths.md)、[静态总览](course-graph/overview.svg)
- [完整图谱JSON](course-graph/graph.json)、[节点CSV](course-graph/nodes.csv)、[关系CSV](course-graph/edges.csv)
- [课程逐行清单](official/courses.csv)、[模块与学分规则原字段](official/modules.json)、[来源核查](course-graph/source-audit.json)

## 官方方案原件

| ID | 名称与适用对象 | 原件 | 离线阅读 |
| --- | --- | --- | --- |
'''
 for p in plans:readme+=f'| {p["plan_id"]} | {p["title"]}；{p["student_type"]}；{p["department"]} | [Word](official/{p["word_path"]}) | [阅读页](official/programme-{p["plan_id"]}.html) |\n'
 readme+='''
## 怎样理解先修与版本

本年级方案正文、Word文本及先修字段已检索，**未取得能够确认课程对课程强制先修的条款**。绿色“方案学期在先”只依据同一方案内的数字学期；橙色为编辑建议，蓝灰色为内容联系；“模块收录”只表示原表列出候选课程。字段缺失不等于没有先修，是否执行选课门槛仍需核对该年级正式大纲和教务规则。

本图不复制2026年的学期数。编辑主题关系按本年级唯一同名课程定位；原课号完整保留，未将旧TOUR代码改写成BA代码，也不推断学分互认。数学三选一路线按原模块并列，不能把三条路线都当成必修链。未明确数字学期的春、秋季节不参与先后推导。

原始接口与官方Word均存于official/；目录记录和方案详情为2026-11-26取得的本年级当前公开快照，系统可能后续修订，不能称为入学当年的原始发布版。JSON经格式规范化并gzip压缩，Word保持下载字节不变；哈希见总清单。原件权利归原权利人，未取得单独的再利用许可声明。
'''
 readme=readme.replace('## 官方方案原件','![专业课程关系总览](course-graph/overview.svg)\n\n## 官方方案原件',1)
 (root/'README.md').write_bytes(readme.encode('utf-8'))
 (out/'README.md').write_bytes((f'# 旅游学系{year}级课程关系图谱\n\n![学习路径总览](overview.svg)\n\n[交互HTML](index.html)（下载后打开） · [课程关系与先修梳理](learning-paths.md) · [图谱JSON](graph.json) · [节点CSV](nodes.csv) · [关系CSV](edges.csv) · [原件与适用方案](../README.md)\n\n关系按本年级方案学期在先、建议先学、内容联系和模块收录分类；尚未确认强制先修。图谱含{len(courses)}个课程/科研条目，其中{core_count}个为专业培养条目、{len(courses)-core_count}个仅公共候选；另有{len(module_nodes)}个模块节点。模块收录不代表全部必修，详情与原始定位见[source-audit.json](source-audit.json)。\n').encode('utf-8'))
 return {'cohort':year,**statistics,'programme_ids':[p['plan_id'] for p in plans]}

if __name__=='__main__':
 summaries=[build(y) for y in [2023,2024,2025]];put(O/'coverage.json',summaries)
 for s in summaries:print(json.dumps(s,ensure_ascii=False))
