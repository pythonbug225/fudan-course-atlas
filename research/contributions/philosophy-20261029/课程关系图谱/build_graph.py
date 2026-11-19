from pathlib import Path
import collections,csv,hashlib,io,json,re

ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent
DEST=ROOT
DEST.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(data.encode('utf-8'))
def dump(p,data):write(p,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
courses=load(SRC/'summaries/courses.json')
planned=load(SRC/'official/programme-courses.json')
BASE_SHA='9c6ec994af187adfd8bc022e06010121e788d9bf'
PDF='https://philosophy.fudan.edu.cn/_upload/article/files/98/2a/cd8af1f746e3ac12a137bbcfaffe/43d2a51a-eb21-4991-925c-26bb8fde30f4.pdf'
topics={
 'foundation':('哲学基础与研究方法','PHIL10002','哲学|学术|论文|实践|外语|英语|书籍装帧'),
 'chinese':('中国哲学与经学','PHIL20014','先秦|汉晋|宋元|近现代哲学|中国哲学|国学|小学|论语|大学|中庸|礼记|公羊|荀子|孟子|庄子|四书|老庄|儒|经学|心学|理学|阳明|传习录|二程|诗.*书'),
 'western':('西方哲学与形而上学','PHIL10001','西方哲学|古希腊哲学|中世纪哲学|德国|康德|黑格尔|笛卡尔|沉思集|查拉图斯特拉|形而上学|启蒙|欧陆|法国|福柯|现象学|精神现象学|谈谈方法'),
 'logic':('逻辑与数学基础','PHIL20013','逻辑|集合论|模型论|概率论|批判性思维'),
 'knowledge':('知识、语言与心智','PHIL30054','知识论|认识论|语言哲学|心灵|心智|心理学哲学|维特根斯坦|分析哲学|英美哲学'),
 'science':('科学、技术与人工智能','PHIL20004','科学哲学|技术哲学|人工智能|智能哲学|超级智能|科学精神|科学解释|科学与社会|自然辨证法|生态哲学'),
 'ethics':('伦理与应用伦理','PHIL20012','伦理|功利主义'),
 'politics':('政治、社会与PPE','PHIL30024','政治|社会批判|批判理论|民族|人类学|论法|利维坦|卢梭|法哲学|经济哲学|PPE|上海|不平等|现代性社会'),
 'marx':('马克思主义与批判理论','PHIL20003','马克思|资本论|意识形态|法兰克福|否定辩证法|社会主义|强国之路'),
 'religion':('宗教、比较与经典','PHIL10004','宗教|基督|佛教|天主|伊斯兰|古兰|希伯来|圣经|法华|道教|灵修|印度哲学'),
 'art':('美学与艺术','PHIL30052','美学|艺术|图像|观看|悲剧'),
 'languages':('古典语言与文本工具','PHIL40019','梵语|藏语|古希腊语'),
}
nodes=[]
for c in courses:
 name=c['course_names'][0].strip()
 tags=[key for key,(_,_,pattern) in topics.items() if re.search(pattern,name)]
 if c['course_code'] in ['PHIL70095','PHIL70001']:tags=['chinese','western']
 if c['course_code']=='PHIL30007':tags=['western','politics']
 # Generic "哲学" is only a fallback, not a claim that every course is foundational.
 if len(tags)>1 and 'foundation' in tags:tags.remove('foundation')
 if not tags:tags=['foundation']
 # Keep formal logic in its own primary track rather than a broad western label.
 for preferred in ['languages','art','religion','marx','ethics','logic','chinese','knowledge','science','politics','western']:
  if preferred in tags:tags=[preferred]+[x for x in tags if x!=preferred];break
 nodes.append({'id':c['course_code'],'name':name,'original_names':c['course_names'],
  'teachers':c['teachers'],'levels':c['levels'],'terms':c['terms'],'topics':tags,
  'topic_basis':'按正式课名和培养方案模块作导航分类；不是已核对的逐周授课大纲',
  'offering_ids':[o['offering_id'] for o in c['offerings']],
  'programme_ids':sorted({str(p['方案编号']) for p in c['program_matches']}),
  'formal_prerequisite_status':'not_established_from_available_sources',
  'source_ref':f'../summaries/courses.json#course_code={c["course_code"]}'})
byid={n['id']:n for n in nodes}
edges=[]
def edge(a,b,kind,rationale,source='catalogue',**extra):
 assert a in byid and b in byid and a!=b,(a,b)
 if kind in ('content_related','parallel_variant','same_title') and a>b:a,b=b,a
 if any((e['source'],e['target'],e['kind'])==(a,b,kind) for e in edges):return
 ev=[{'source_id':'catalogue','locator':f'course_code={a}'},{'source_id':'catalogue','locator':f'course_code={b}'}]
 if source!='catalogue':ev.append({'source_id':source,'locator':'PDF第18页（从1开始）；2026哲学专业修读说明'})
 edges.append({'id':f'E{len(edges)+1:04d}','source':a,'target':b,'kind':kind,
  'directed':kind in ('official_sequence','recommended_preparation','official_credit_waiver','formal_prerequisite'),
  'is_formal_prerequisite':False,'authority':'official' if source=='handbook-2026' else 'editorial_inference',
  'rationale':rationale,'evidence':ev,**extra})

edge('PHIL10003','PHIL20013','official_sequence','2026哲学专业普通路线安排逻辑学在大一上、数理逻辑在大一下；这是培养修读顺序，不等于已验证的选课拦截条件。','handbook-2026',scope='2026哲学专业一般修读路线；其他专业与年级核对相应方案')
for target in ['PHIL10003','PHIL20013']:
 edge('PHIL20013h',target,'official_credit_waiver','2026哲学专业数学基础较好学生可选大一上数理逻辑（H），同时免修普通路线的逻辑学和数理逻辑；不是先修箭头。','handbook-2026',scope='2026哲学专业可选修读路线',waiver_group='logic-h-alternative',group_semantics='one_h_course_waives_both_ordinary_courses')

# Every recommended edge below is a transparent learning suggestion, not an official prerequisite.
chains=[
 ('中国哲学史的时间脉络',['PHIL20014','PHIL20015','PHIL20016','PHIL20017']),
 ('逻辑训练的学习阶梯',['PHIL10003','PHIL20013','PHIL30087']),
 ('模型论的工具准备',['PHIL20013','PHIL30101','PHIL50038']),
 ('集合论的进阶准备',['PHIL20013','PHIL30106','PHIL50040']),
 ('梵语连续学习',['PHIL40019','PHIL40020','PHIL40021','PHIL40022']),
 ('梵语连续学习（GESF代码）',['GESF40004','GESF40005']),
 ('西方艺术史的时间脉络',['PHIL30136','PHIL30137']),
 ('中国艺术史的时间脉络',['PHIL30138','PHIL30139','PHIL30140']),
 ('西方哲学概览到德国古典专题',['PHIL10001','PHIL20011','PHIL30008','PHIL40031']),
 ('德国古典哲学到黑格尔文本',['PHIL20011','PHIL30064','PHIL60064']),
 ('欧陆哲学到现象学专题',['PHIL30050','PHIL30067','PHIL70025']),
 ('分析哲学到原著研究',['PHIL30049','PHIL30066','PHIL70049']),
 ('伦理学基础到规范与应用',['PHIL20012','PHIL40028','PHIL60060','PHIL60047']),
 ('中国古典文本的阅读工具',['PHIL20007','PHIL30023','PHIL70103']),
 ('儒家典籍的递进阅读',['PHIL20014','PHIL20008','PHIL40035']),
 ('宋明哲学到理学原著',['PHIL20016','PHIL60077','PHIL60014']),
 ('宋明哲学到阳明原著',['PHIL20016','PHIL70094']),
 ('宗教学概览到比较研究',['PHIL10004','PHIL30043','PHIL60081']),
 ('佛教思想到经典与历史',['GEEC10346','PHIL30011','PHIL30149']),
 ('基督教概览到经典研究',['PHIL30009','PHIL30154','PHIL70009']),
 ('科学哲学到原著与专题',['PHIL20004','PHIL40033','PHIL60074','PHIL50029']),
 ('美学基础到原著与批评',['PHIL30052','PHIL30074','PHIL30151','PHIL40002']),
 ('马克思主义基础到原著',['PHIL20003','PHIL30099','PHIL60005','PHIL40029']),
 ('西方马克思主义到批判理论',['PHIL30051','PHIL30057','PHIL30058','PHIL60090','PHIL70118']),
 ('写作训练到论文实践',['PHIL20018','PHIL40036','PHIL30004','PHIL40008']),
 ('研究生论文训练',['PHIL40036','PHIL70088','PHIL70127']),
 ('中级古希腊语的连续文本训练',['PHIL70074','PHIL70077']),
]
for why,chain in chains:
 for a,b in zip(chain,chain[1:]):
  # The official ordinary-logic order is already represented with its own scope.
  if (a,b)==('PHIL10003','PHIL20013'):continue
  edge(a,b,'recommended_preparation',why+'：可先准备前一门涉及的基础，再进入后一门；由课名/知识结构整理，未核对各教学班先修限制。',learning_path=why)

preparations=[
 ('PHIL20013','PHIL30116','先熟悉命题和一阶逻辑，再比较非经典逻辑系统'),
 ('PHIL20013','PHIL40034','一阶逻辑专题可先准备形式语言与证明方法；两门内容可能重叠'),
 ('PHIL20013','PHIL20005','逻辑技术有助于理解有效性、真与逻辑哲学问题'),
 ('PHIL30054','PHIL50051','知识论问题与形式化方法结合'),
 ('PHIL30111','PHIL50051','概率与形式知识论的方法联系'),
 ('PHIL30054','PHIL70117','先掌握知识论基础问题，再读当代经典'),
 ('PHIL30022','PHIL30114','先了解心身问题与心灵概念，再进入心理学哲学'),
 ('PHIL30022','PHIL70089','心灵哲学为当代心智专题提供问题背景'),
 ('PHIL30025','PHIL30069','语言、意义与维特根斯坦专题的准备关系'),
 ('PHIL20004','PHIL30047','科学说明与方法问题可帮助讨论人工智能哲学'),
 ('PHIL30047','AIB310001','人工智能哲学可为智能系统伦理问题提供概念背景'),
 ('PHIL20012','AIB310001','规范评价与伦理论证用于人工智能议题'),
 ('PHIL20012','PHIL30115','伦理学的规范论证为神经伦理提供准备'),
 ('PHIL20012','PHIL70071','伦理学基础为生命伦理议题提供准备'),
 ('PHIL30024','PHIL70028','政治哲学基本概念到专题研究'),
 ('PHIL30052','PHIL30117','美学问题与艺术史解释方法的联系'),
 ('PHIL20003','PHIL40025','马克思主义基础有助于阅读资本论专题'),
 ('PHIL40025','PHIL70119','资本论文本到当代哲学研究'),
 ('PHIL30019','PHIL70045','宗教的社会研究视角可帮助理解民间宗教专题'),
]
unresolved=[]
for a,b,why in preparations:
 if a not in byid or b not in byid:
  unresolved.append({'source':a,'target':b,'reason':'不存在于本批267个课程代码，未写入关系；不生成或纠正一个未核对的课程代码。'});continue
 edge(a,b,'recommended_preparation',why+'；这是学习建议，尚无相应教学班正式先修要求的证据。')

# A topic-star is intentionally used instead of an unhelpful all-to-all similarity graph.
for n in nodes:
 for tag in n['topics']:
  label,anchor,_=topics[tag]
  if anchor!=n['id']:
   edge(anchor,n['id'],'content_related',f'按正式课名归入“{label}”导航主题；共享主题不表示课程等价、知识点全部相同或存在先修要求。',topic=tag,method='title_and_curriculum_topic_index')

bridges=[
 ('PHIL20004','PHIL30054','科学解释与知识正当性的交叉问题'),
 ('PHIL30022','PHIL30115','心智/神经研究与伦理评价的交叉'),
 ('PHIL30024','PHIL20012','正义、权利与规范理由的交叉'),
 ('PHIL30011','PHIL30147','佛教与印度哲学的思想语境'),
 ('PHIL30009','PHIL30065','基督教哲学与中世纪哲学文本'),
 ('PHIL20011','PHIL30051','德国哲学与西方马克思主义的思想背景'),
 ('PHIL30052','PHIL60089','美学与康德判断力问题的专题联系'),
 ('PHIL30024','GECC20041','政治哲学与霍布斯经典文本'),
 ('PHIL30024','GECC20037','政治哲学与卢梭不平等问题'),
 ('PHIL30024','GECC20014','政治哲学与法、政体的经典问题'),
 ('PHIL20012','GECC20043','伦理学与功利主义经典文本'),
 ('PHIL20014','GECC20012','先秦哲学与荀子经典文本'),
 ('PHIL30028','GESF40004','梵语是印度佛教文献研究的一种语言工具；不表示本课必须掌握梵语'),
 ('PHIL30023','PHIL70035','史料研读与经学历史研究的工具联系'),
 ('PHIL30013','PHIL60058','技术议题与科技伦理评价的联系'),
]
for a,b,why in bridges:edge(a,b,'content_related',why+'；内容结构层面的推断，需以当期大纲细化。',method='manual_cross_topic_bridge')

for n in nodes:
 if n['id'].endswith('h') and n['id'][:-1] in byid:
  edge(n['id'][:-1],n['id'],'parallel_variant','相同主体代码的普通/H命名变体；两者教学班和要求分别保留。除明确列出的逻辑H替代规则外，不推断学分互认。')
names=collections.defaultdict(list)
for n in nodes:names[n['name']].append(n['id'])
for name,ids in names.items():
 for a,b in zip(sorted(ids),sorted(ids)[1:]):
  edge(a,b,'same_title','同名但代码或层次不同，作为检索关联；不据此认定内容完全一致、合班或可替代。')

sources=[
 {'id':'catalogue','title':'哲学学院2025秋/2026春267代码与384教学班','path':'../summaries/courses.json','sha256':hashlib.sha256((SRC/'summaries/courses.json').read_bytes()).hexdigest(),'scope':'提供课程名、代码、层次、教学班和培养方案匹配；未提供正式先修字段'},
 {'id':'programmes','title':'2026级18份培养方案课程索引','path':'../official/programme-courses.json','sha256':hashlib.sha256((SRC/'official/programme-courses.json').read_bytes()).hexdigest(),'scope':'3327个方案课程条目；建议学期字段均空或null，不能由其生成先修边'},
 {'id':'handbook-2026','title':'复旦大学哲学学院本科生课程学习手册（2026版）','url':PDF,'sha256':'7bfb9ef2eafc04e888d3026e3348bd138ed4614ccd749b63fb2e8de9d8af77e1','pages':235,'accessed':'2026-11-19','scope':'第18页普通逻辑修读路线及H替代；第181、183、186、189、192页是微专业整体先修不作要求，不等于每门课无先修'}
]
counts=dict(collections.Counter(e['kind'] for e in edges))
graph={'schema_version':'1.0','department':'哲学学院（哲学系）','generated_on':'2026-11-19','base_commit':BASE_SHA,
 'scope':'节点完整覆盖2025秋、2026春哲学学院267个开课代码；2026培养方案和2026版手册用于补充关联与限定规则，不代表全历史开课目录。',
 'relation_types':{
  'formal_prerequisite':{'label':'正式先修','directed':True,'count':0,'meaning':'仅在正式课程条目明确要求先修时建立；本批尚未取得逐班证据，不能当作没有先修。'},
  'official_sequence':{'label':'官方修读顺序','directed':True},
  'recommended_preparation':{'label':'建议先学','directed':True},
  'content_related':{'label':'内容联系','directed':False},
  'parallel_variant':{'label':'普通/H关联','directed':False},
  'same_title':{'label':'同名异码关联','directed':False},
  'official_credit_waiver':{'label':'官方免修方向','directed':True}},
 'topics':[{'id':k,'label':v[0],'anchor':v[1]} for k,v in topics.items()],
 'sources':sources,'nodes':nodes,'edges':edges,'statistics':{'nodes':len(nodes),'edges':len(edges),'edge_counts':counts,'formal_prerequisites_verified':0},
 'audit':{'programme_entries':len(planned),'programme_nonempty_suggested_terms':sum(bool(x.get('建议学期')) for x in planned),'unresolved_candidates':unresolved,
 'limitations':['未按课程编号大小、开课学期或培养方案建议学期自动生成先修关系。','内容关联和建议先学以课名/知识结构为主，未完整核对267课逐班大纲。','所有关系均保留来源和关系类型；教师差异、选课资格及替代条件应再查当期教务说明。','培养方案同模块关系只作为节点元数据，未把同模块所有课互相连线。']}}
dump(DEST/'graph.json',graph)
dump(DEST/'sources.json',sources)
dump(DEST/'audit.json',graph['audit'])
def csvfile(name,fields,rows):
 out=io.StringIO(newline='');w=csv.DictWriter(out,fields,lineterminator='\n');w.writeheader();w.writerows(rows);write(DEST/name,out.getvalue())
csvfile('nodes.csv',['course_code','course_name','levels','terms','topics','formal_prerequisite_status'],[{'course_code':n['id'],'course_name':n['name'],'levels':'|'.join(n['levels']),'terms':'|'.join(n['terms']),'topics':'|'.join(n['topics']),'formal_prerequisite_status':n['formal_prerequisite_status']} for n in nodes])
csvfile('edges.csv',['id','source','target','kind','directed','is_formal_prerequisite','authority','rationale','evidence'],[{k:json.dumps(e[k],ensure_ascii=False) if k=='evidence' else e[k] for k in ['id','source','target','kind','directed','is_formal_prerequisite','authority','rationale','evidence']} for e in edges])

md=['# 哲学系课程关系图谱','',graph['scope'],'',
 '覆盖全部267个课程代码（253个去重名称），按12个主题导航。每条关系都有类型、解释和来源定位。**目前确认的正式先修边为0条，表示逐班正式要求尚未核实，不表示这些课程没有先修。**','',
 '- [离线交互图谱](index.html)：下载本目录，打开index.html，可搜索名称/代码/教师、按主题和关系类型筛选，点击课程查看相邻关系。HTML内嵌完整数据，不需联网。GitHub会显示HTML源码，可下载后打开。',
 '- [完整图数据](graph.json)、[节点表](nodes.csv)、[关系表](edges.csv)、[来源索引](sources.json)、[审计记录](audit.json)。','',
 '## 关系怎么读','',
 '| 类型 | 箭头含义 | 依据与适用边界 |','| --- | --- | --- |',
 '| 正式先修 | 先修课程 → 后续课程 | 本批未确认，不自动生成 |',
 '| 官方修读顺序 | 官方安排先读 → 后读 | 2026手册第18页，限相应年级和方案；不是选课拦截条件 |',
 '| 建议先学 | 有帮助的基础 → 专题/进阶 | 编辑根据课名及知识结构整理，需当期大纲复核 |',
 '| 内容联系 | 无方向 | 共用主题、经典文本、方法或交叉问题；不是学分互认 |',
 '| 普通/H、同名异码 | 无方向 | 作为检索关联，课程代码、层次和教师分别保留 |',
 '| 官方免修方向 | 已修替代课 → 被免修课 | 2026哲学专业H逻辑路线的特定规则 |','',
 '## 官方逻辑修读路线','',
 '2026版手册第18页明确普通路线与可选H路线：普通路线先逻辑学，再数理逻辑；数学基础较好者可在大一上选数理逻辑（H），并免修前两门普通课程。适用2026哲学专业相关方案；不倒推2025级规则。','',
 '```mermaid','flowchart LR','  L["PHIL10003 逻辑学"] -->|"官方普通修读顺序"| M["PHIL20013 数理逻辑"]','  H["PHIL20013h 数理逻辑（H）"] -.->|"可选路线：免修"| L','  H -.->|"可选路线：免修"| M','```','',
 '## 建议学习路径','',
 '以下图中虚线箭头是**学习建议**，不表示已取得正式先修证据；逻辑学到数理逻辑的实线单独标为官方普通路线。正文路径保留具体代码，普通/H与本科/研究生课程不会自动合并。','']
for title,chain in chains:
 md+=['### '+title,'','```mermaid','flowchart LR']
 for code in chain:md.append(f'  {code}["{code} {byid[code]["name"]}"]')
 for a,b in zip(chain,chain[1:]):md.append(f'  {a} -->|"官方普通路线"| {b}' if (a,b)==('PHIL10003','PHIL20013') else f'  {a} -.->|"建议先学"| {b}')
 md+=['```','']
md+=['## 跨主题内容桥梁','','| 课程A | 课程B | 联系 |','| --- | --- | --- |']
for a,b,why in bridges:md.append(f'| {byid[a]["name"]}（{a}） | {byid[b]["name"]}（{b}） | {why} |')
md+=['','## 数据、来源与更新','',
 f'- [学院2026版课程学习手册]({PDF})：PDF共235页，页码从1开始。来源于[学院培养栏目](https://philosophy.fudan.edu.cn/py/list.htm)的2026-09-23条目，2026-11-19核对。只记录所用规则及来源，不复制完整手册。',
 '- [本批267代码与教学班记录](../summaries/courses.json)、[18份培养方案课程索引](../official/programme-courses.json)。培养方案索引3327条的建议学期均为空或null；不据此编造修读先后。',
 '- 内容主题星形索引使用正式课名进行导航匹配，完整保留推断标记。主题连线不意味着任意两门课程内容等价；未核对的逐周内容和先修字段保留待查。',
 '- 手册第181、183、186、189、192页的“先修课程不作要求”针对微专业整体准入，不当作267门课均无先修的证据。',
 '- 后续接入检索时以课程代码为主键；按kind和authority过滤。需要严格先修查询时仅允许kind=formal_prerequisite；本批该查询应返回“待核实”，不能用建议边替代。',
 '- 新增硬性先修要求必须带具体教学班/学期、官方大纲或教务规则、页码/字段路径及确认日期。H班替代条款需要完整保留适用专业和年级。',
 '- 生成命令：在本院系目录执行 `python 课程关系图谱/build_graph.py`（标准库；维护源数据见脚本说明）。','',
 '## 当前数量','',f'- 节点：{len(nodes)}；关系：{len(edges)}；主题：{len(topics)}。']
for k,count in counts.items():md.append(f'- {graph["relation_types"][k]["label"]}：{count}。')
write(DEST/'README.md','\n'.join(md)+'\n')
if (DEST/'viewer.template.html').exists():
 compact=json.dumps(graph,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
 template=(DEST/'viewer.template.html').read_text('utf-8')
 viewer=(DEST/'viewer.js').read_text('utf-8')
 write(DEST/'index.html',template.replace('__GRAPH_DATA__',compact).replace('__VIEWER_JS__',viewer))
print(json.dumps(graph['statistics'],ensure_ascii=False))
