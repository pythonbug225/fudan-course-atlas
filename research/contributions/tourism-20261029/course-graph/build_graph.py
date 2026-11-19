"""Build a sourced offline tourism course graph. Standard-library only."""
import collections,csv,hashlib,html,json,re,shutil
from pathlib import Path
from curation import GROUPS,PLANNED,PREPARATION,CONTENT,PATHS
W=Path(__file__).resolve().parent;S=W/'sources';O=W/'package/course-graph';O.mkdir(parents=True,exist_ok=True)
SHA='262d99e34d453e99fda887773c41137376209be0'
URL='https://github.com/pythonbug225/fudan-course-atlas/blob/'+SHA+'/research/contributions/tourism-20261029/'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def put(name,value):(O/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def esc(v):return html.escape(str(v))
catalog=read(S/'course_catalog.json');plan_index=read(S/'培养方案课程索引.json');stats=read(S/'统计摘要.json')
offered={r['课程代码'] for r in catalog};all_codes=offered|{r['课程代码'] for r in plan_index}
groups={code:g for g,_,codes in GROUPS for code in codes.split()}
assert len(groups)==sum(len(c.split()) for _,_,c in GROUPS),'Duplicate group membership'
assert all_codes==set(groups),(sorted(all_codes-set(groups)),sorted(set(groups)-all_codes))
sources={
 'CAT':{'title':'2025秋／2026春旅游学系实际开课目录','url':URL+'官方资料/course_catalog.json','path':'../官方资料/course_catalog.json','reading_copy_sha256':hashlib.sha256((S/'course_catalog.json').read_bytes()).hexdigest()},
 'INDEX':{'title':'2026两份方案课程索引','url':URL+'官方资料/培养方案课程索引.json','path':'../官方资料/培养方案课程索引.json'},
}
nodes={}
for row in catalog+plan_index:
 code=row['课程代码']
 n=nodes.setdefault(code,{'id':code,'name':row['课程名称'],'name_variants':[],'group':groups[code],'node_type':'research_activity' if code=='102' else 'course','scope':'offered_2025_2026' if code in offered else 'plan_only','offerings':[],'business_types':[],'teachers':[],'programmes':[],'plan_placements':[],'current_prerequisite_status':'not_verified','source_ids':[]})
 if row['课程名称'] not in n['name_variants']:n['name_variants'].append(row['课程名称'])
 if '学期ID' in row:
  n['offerings'].append({'term':row['学期'],'teachers':row['教师'],'sections':row['教学班数']});n['teachers']=sorted(set(n['teachers'])|{x for x in row['教师'].split('、') if x});n['source_ids']=sorted(set(n['source_ids'])|{'CAT'})
 else:
  n['programmes']=sorted(set(n['programmes'])|{str(row['方案编号'])});n['source_ids']=sorted(set(n['source_ids'])|{'INDEX'})
for term in ['2025秋','2026春']:
 source='LESSON-'+term;file=term+'旅游学系教学班.json'
 sources[source]={'title':term+'实际教学班原始响应','url':URL+'官方资料/原始接口/'+file,'path':'../官方资料/原始接口/'+file}
 for row in read(S/file)['data']:
  n=nodes[row['course']['code']];n['business_types']=sorted(set(n['business_types'])|{row.get('lessonCrossBizTypeName') or '未标注'})
for n in nodes.values():
 if not n['business_types']:n['business_types']=['培养方案条目' if n['node_type']=='research_activity' else '本科（仅方案收录）']
 if n['id']=='102':n['note']='原接口代码102、名称“复芏计划(FDUROP)”原样保留；作为科研活动条目，不计常规课程。'
plan_rows=[];audits=[]
figure_extra={'BA10006':1,'MATH10028':1,'MATH10030':2,'BA10003':4}
for pid,image in [('154832','154832-document_image_rId6.png'),('154078','154078-document_image_rId8.png')]:
 source='PLAN-'+pid;fig='FIGURE-'+pid;fn='2026-plan-'+pid+'-detail.json';data=read(S/fn)
 title=next(p['方案名称'] for p in plan_index if p['方案编号']==pid)
 sources[source]={'title':title,'url':URL+'官方资料/原始接口/'+fn,'path':'../官方资料/原始接口/'+fn,'reading_copy_sha256':hashlib.sha256((S/fn).read_bytes()).hexdigest()}
 (O/'source-figures').mkdir(exist_ok=True);shutil.copyfile(S/image,O/'source-figures'/('plan-'+pid+'-curriculum.png'))
 sources[fig]={'title':title+'：课程体系与科研训练体系图','url':'source-figures/plan-'+pid+'-curriculum.png','path':'source-figures/plan-'+pid+'-curriculum.png','original_docx_url':URL+'官方资料/方案原件/2026-plan-'+pid+'.docx','original_member':'word/media/'+image[len(pid)+1:],'sha256':hashlib.sha256((S/image).read_bytes()).hexdigest(),'reviewed':'2026-11-19逐行核对学期、课程框及科研训练箭头；图中没有逐门课程的强制先修连线。'}
 seen=set()
 for mi,module in enumerate(data['courseModules']):
  for ci,pc in enumerate(module.get('planCourses',[])):
   course=pc.get('course',{});code=course.get('code')
   if code not in nodes:continue
   terms=[int(x.split('_')[1]) for x in pc.get('terms',[]) if re.fullmatch('TERM_[1-8]',x)]
   record={'plan_id':pid,'course_code':code,'module':module.get('name') or module.get('nameZh') or '', 'source':source,'locator':f'/courseModules/{mi}/planCourses/{ci}','terms_raw':pc.get('terms',[]),'terms_text':pc.get('termsText'),'suggest_terms_raw':pc.get('suggestTerms',[]),'numbered_terms':terms,'term_source':'api_terms','note':'方案课程安排；原开设季节索引中的数字不能作为秋春季节解释。'}
   plan_rows.append(record)
   if code not in seen:
    placement=dict(record)
    if not terms and code in figure_extra:
     placement['numbered_terms']=[figure_extra[code]];placement['term_source']='reviewed_curriculum_figure';placement['source']=fig;placement['locator']='课程体系表：第'+str(figure_extra[code])+'学期课程框';placement['note']='API季节/建议字段未提供数值学期，本字段单独来自已核对的官方Word内嵌课程体系图。'
    nodes[code]['plan_placements'].append(placement);seen.add(code)
 prefields=[];texts=[]
 def scan(x,path=''):
  if isinstance(x,dict):
   for k,v in x.items():
    if k in ['defaultPreCourses','defaultPreCourseList']:prefields.append({'path':path+'/'+k,'value':v})
    scan(v,path+'/'+k)
  elif isinstance(x,list):
   for i,v in enumerate(x):scan(v,path+'/'+str(i))
  elif isinstance(x,str) and re.search('先修|前置|预修|修读顺序',x):texts.append(path)
 scan(data);audits.append({'plan_id':pid,'prerequisite_fields':prefields,'prerequisite_text_paths':texts,'current_hard_prerequisites_verified':0})
types={'planned_before':'2026方案学期在先（非先修）','recommended_preparation':'建议先学（内容推断）','content_related':'内容联系（无方向）','same_name_distinct_code':'同名异号（不代表互认）'}
edges=[];keys=set()
def add(a,b,kind,reason,evidence=None):
 assert a in nodes and b in nodes and a!=b,(a,b)
 directed=kind in ['planned_before','recommended_preparation']
 if not directed and a>b:a,b=b,a
 key=(a,b,kind)
 if key in keys:return
 keys.add(key)
 edges.append({'id':f'E{len(edges)+1:03}','source':a,'target':b,'type':kind,'directed':directed,'reason':reason,'evidence':evidence or [{'source':'CAT' if a in offered and b in offered else 'INDEX','locator':a+' + '+b,'basis':'课程名称和主题的编辑判断，未据此断言大纲具体章节。'}],'mandatory':False,'credit_equivalence':False,'assertion_scope':'2026_plan_term_order_only' if kind=='planned_before' else 'editorial_title_based_content_inference' if kind!='same_name_distinct_code' else 'official_name_code_identity','confidence':'高（方案学期事实；关联选择为编辑判断）' if kind=='planned_before' else '高（名称代码事实）' if kind=='same_name_distinct_code' else '中（主题层面，待大纲核对）'})
for a,b,reason in PLANNED:
 evidence=[]
 for left in nodes[a]['plan_placements']:
  for right in nodes[b]['plan_placements']:
   if left['plan_id']==right['plan_id'] and left['numbered_terms'] and right['numbered_terms'] and max(left['numbered_terms'])<min(right['numbered_terms']):
    evidence.append({'source':left['source'],'locator':left['locator'],'course':a,'terms':left['numbered_terms'],'plan_id':left['plan_id']});evidence.append({'source':right['source'],'locator':right['locator'],'course':b,'terms':right['numbered_terms'],'plan_id':right['plan_id']})
 assert evidence,('No same-plan term order',a,b)
 add(a,b,'planned_before',reason+' 此边只表达同一方案里的学期安排，方案未把这两课明确写成先修条件。',evidence)
for a,b,reason in PREPARATION:add(a,b,'recommended_preparation',reason)
for a,b,reason in CONTENT:add(a,b,'content_related',reason)
namecodes=collections.defaultdict(list)
for n in nodes.values():namecodes[n['name']].append(n['id'])
for name,codes in namecodes.items():
 for i,a in enumerate(codes):
  for b in codes[i+1:]:add(a,b,'same_name_distinct_code','官方目录中同名“'+name+'”，课号与培养层次/方案分别保留；不据此认定等价、替代、课程沿革或先修。',[{'source':'CAT' if a in offered else 'INDEX','locator':a},{'source':'CAT' if b in offered else 'INDEX','locator':b}])
degree=collections.Counter(x for e in edges for x in [e['source'],e['target']])
statistics={'nodes':len(nodes),'course_nodes':sum(n['node_type']=='course' for n in nodes.values()),'activity_nodes':1,'offered_course_codes':len(offered),'plan_only_nodes':len(nodes)-len(offered),'offering_sections':123,'edges':len(edges),'edge_types':dict(collections.Counter(e['type'] for e in edges)),'current_mandatory_prerequisites_verified':0,'isolated_node_ids':[c for c in nodes if not degree[c]]}
graph={'schema_version':'fudan-course-graph/1','title':'旅游学系课程关系图谱','updated_at':'2026-11-19','base_commit':SHA,'scope':{'offering_terms':['2025秋','2026春'],'program_year':2026,'plan_ids':['154832','154078'],'plan_note':'留学生本科方案与历史学-旅游管理双学士方案分别适用；方案收录不等于两学期已开课。'},'evidence_policy':'学期安排不等于先修；建议和内容联系按题名与学科主题判断，未取得全量课程大纲。','relation_types':types,'groups':[{'id':g,'name':name} for g,name,_ in GROUPS],'sources':sources,'statistics':statistics,'nodes':list(nodes.values()),'edges':edges,'learning_paths':[{'title':name,'course_ids':codes.split(),'note':note} for name,codes,note in PATHS]}
put('graph.json',graph);put('plan-fields.json',plan_rows)
put('source-audit.json',{'date':'2026-11-19','base_commit':SHA,'plans':audits,'images_reviewed':[sources['FIGURE-154832'],sources['FIGURE-154078']],'handbook_access':[{'url':'https://jwc.fudan.edu.cn/0c/d5/c39650a789717/page.htm','status':'2026手册入口转统一认证；未读取正文，不算依据'},{'url':'https://jwc.fudan.edu.cn/81/eb/c39650a688619/page.htm','status':'2024手册入口转统一认证；未取得旅游学系手册；搜索返回的历史学手册未替代采用'}],'limits':['文本接口阅读副本可能按换行规范化；reading_copy_sha256仅校验本次阅读副本，原始源版本由固定Git提交与路径定位。','未取得逐教学班大纲及现行先修规则；空defaultPreCourses/suggestTerms字段不证明没有先修。','学期安排来自2026方案，不能解释成2025秋/2026春教学班的选课硬条件。','本科、研究生、同名异号与科研活动102分别保留；不推断互认。','课程体系图的“社会研究方法基础”与API“社会研究方法”存在标题差异，该节点安排采用同课号API，不单靠近似标题匹配。','数字学期来自terms/课程体系图；未将旧索引的开设季节数字误认作季节或自动连出先修边。']})
with (O/'nodes.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=['id','name','node_type','scope','group','business_types','teachers','programmes'];w=csv.DictWriter(f,fields);w.writeheader()
 for n in graph['nodes']:w.writerow({k:'；'.join(n[k]) if isinstance(n[k],list) else n[k] for k in fields})
with (O/'edges.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=['id','source','target','type','directed','reason','mandatory','credit_equivalence','evidence'];w=csv.DictWriter(f,fields);w.writeheader()
 for e in edges:w.writerow({k:json.dumps(e[k],ensure_ascii=False) if k=='evidence' else e[k] for k in fields})
# Compact representative paths; the interactive graph contains every node.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1740" height="1350" viewBox="0 0 1740 1350"><style>text{font-family:Microsoft YaHei,Noto Sans CJK SC,sans-serif}.title{font-size:30px;font-weight:bold;fill:#203d50}.name{font-size:15px;fill:#163b4e}.sub{font-size:13px;fill:#526c7a}.code{font-size:11px;fill:#557c8a}</style><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="context-stroke"/></marker></defs><rect width="1740" height="1350" fill="#f2f7f8"/><text class="title" x="35" y="50">旅游学系 · 课程关系与学习路径</text><text class="sub" x="35" y="82">2025秋—2026春开课＋2026方案关联课　｜　学期安排、学习建议和内容联系分别标注；不是强制先修链</text>']
for i,(title,codes,note) in enumerate(PATHS):
 y=125+i*142;svg.append(f'<rect x="20" y="{y-15}" width="1700" height="130" rx="12" fill="white"/><text class="name" x="35" y="{y+15}" font-weight="bold">{esc(title)}</text>')
 cs=codes.split()
 for j,code in enumerate(cs):
  x=280+j*280;n=nodes[code];svg.append(f'<rect x="{x}" y="{y}" width="246" height="60" rx="8" fill="#eef6f7" stroke="#bfd6de"/><text class="code" x="{x+10}" y="{y+17}">{code}</text><text class="name" x="{x+10}" y="{y+42}">{esc(n["name"])}</text>')
  if j:
   options=[e for e in edges if (e['source']==cs[j-1] and e['target']==code) or (not e['directed'] and {e['source'],e['target']}=={cs[j-1],code})];assert options,(cs[j-1],code)
   e=options[0];color={'planned_before':'#147e76','recommended_preparation':'#b16b1a','content_related':'#778baa','same_name_distinct_code':'#9877ae'}[e['type']];dash=' stroke-dasharray="5 4"' if e['type']=='recommended_preparation' else '';arrow=' marker-end="url(#arrow)"' if e['directed'] else ''
   svg.append(f'<line x1="{x-34}" x2="{x-7}" y1="{y+30}" y2="{y+30}" stroke="{color}" stroke-width="2.5"{dash}{arrow}/>')
 svg.append(f'<text class="sub" x="280" y="{y+92}">{esc(note)}</text>')
svg.append('<text class="sub" x="35" y="1300">绿色箭头：方案学期在先　　橙色虚线：建议先学　　蓝灰无箭头：内容联系　　完整图谱包含131个课程节点与1个科研活动条目。</text></svg>')
(O/'overview.svg').write_bytes(''.join(svg).encode('utf-8'))
lines=['# 旅游学系课程关系与学习路径','','![课程关系总览](overview.svg)','','## 先修关系如何理解','','目前没有核实到可以作为当期强制先修的关系。绿色边依据同一2026方案中的学期安排；选择哪些课程配对展示由编者依据主题决定。橙色边为建议准备，蓝色边为内容联系，均可按具体目标调整。','','## 学习路径','']
for title,cs,note in PATHS:lines.extend(['### '+title,'',' → '.join(nodes[c]['name']+'（'+c+'）' for c in cs.split()),'',note,''])
lines.extend(['## 全部关系及理由','','| 起点 | 终点 | 类型 | 理由 |','| --- | --- | --- | --- |'])
for e in edges:lines.append('| '+nodes[e['source']]['name']+' '+e['source']+' | '+nodes[e['target']]['name']+' '+e['target']+' | '+types[e['type']]+' | '+e['reason']+' |')
(O/'learning-paths.md').write_bytes(('\n'.join(lines)+'\n').encode('utf-8'))
for name in ['build_graph.py','curation.py']:shutil.copyfile(W/name,O/name)
template=(W/'viewer-template.html').read_text('utf-8');(O/'index.html').write_bytes(template.replace('__GRAPH_DATA__',json.dumps(graph,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')).encode('utf-8'));shutil.copyfile(W/'viewer-template.html',O/'viewer-template.html')
readme=f'''# 旅游学系课程关系图谱

覆盖 **{statistics['course_nodes']}个课程节点＋1个科研活动条目、{len(edges)}条关系**。其中85个代码来自2025秋／2026春实际开课；另47个条目来自两份2026方案，包含跨院系基础课和科研活动，已注明“仅方案收录”。

![代表性路径](overview.svg)

- [交互图谱 index.html](index.html)：下载后直接打开，离线可用。支持课程/课号/教师搜索、主题/层次/开课范围筛选、关系开关和课程邻接图。
- [课程关系与学习路径](learning-paths.md)：GitHub可直接阅读，包含全部关系及理由。
- [graph.json](graph.json)、[课程节点CSV](nodes.csv)、[关系CSV](edges.csv)：用于后续检索与图数据库；每条边包含类型、方向、依据和明确的非强制标记。
- [方案原始学期字段提取](plan-fields.json)、[证据核查与缺口](source-audit.json)、[验证记录](validation.json)。

## 关系类型

| 类型 | 含义 |
| --- | --- |
| 2026方案学期在先 | 同一方案的A课程学期数字早于B。只表明安排先后，**不等于方案明确规定A是B的先修**；关联配对由编者选择 |
| 建议先学 | 依据课程名称与学科主题给出的准备顺序；未取得全量课程大纲，需结合个人基础调整 |
| 内容联系 | 无方向的主题、方法、能力或应用场景联系；不代表先修 |
| 同名异号 | 显示官方同名不同代码，保留层次与方案差异，不表示互认或替代 |

**当前已核实的硬性先修边：0。** 空白先修字段不等于没有要求。2026留学生方案154832和历史学—旅游管理双学士方案154078适用对象不同，不能合成同一人的必修链；2025秋／2026春实际开课也不等于2026级的建议修读学期。

## 官方依据

沿用[本分支官方资料](../官方资料/README.md)，源版本固定为提交`{SHA}`；核对两份方案Word内嵌的课程体系图，保留[留学生方案图](source-figures/plan-154832-curriculum.png)和[双学士方案图](source-figures/plan-154078-curriculum.png)。原件与原始接口未改写，图像SHA-256及提取位置见source-audit.json。

直接读取原始`terms`中的`TERM_1…TERM_8`；会计学等数字学期来自已核对的体系图，另外标明图源。旧课程索引“开设季节”中的数字不是秋春标签；本图不根据空白`suggestTerms`编造顺序。共同属于某模块、教师相同、分数高低、课号大小均未用作先修依据。

同名异号、本科/研究生保持独立。“复芏计划(FDUROP)”及代码102沿用原字段，作为科研活动单列。图谱主题分组、建议和内容边为编辑判断；没有将历史课评中的先修传闻、未读学习手册或个人感受当作正式要求。公开手册入口转统一认证的访问缺口已登记。

## 复核与再生成

`graph.json`是面向检索的完整数据，`plan-fields.json`保存原始方案字段及JSON定位。`build_graph.py`、`curation.py`与`viewer-template.html`提供构建逻辑；在脚本旁的`sources/`放入本分支官方资料对应文件及体系图，运行Python脚本即可重建。内容修改后需运行`validate_graph.py`重新核验节点覆盖、关系证据、学期先后、图数据一致性及循环。

原件与提取图的权利归原权利人，公开来源不额外授予再利用许可。此提交将图谱存于旅游学系研究分支，不自动部署在线网站。
'''
(O/'README.md').write_bytes(readme.encode('utf-8'));print(json.dumps(statistics,ensure_ascii=False))
