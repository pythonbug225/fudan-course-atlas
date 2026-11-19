"""Rebuild the SSDPP graph offline from versioned official records and explicit proposals."""
import collections,csv,gzip,hashlib,html,io,json,re,unicodedata
from pathlib import Path
R=Path(__file__).resolve().parent;P=R.parent
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,s):p.write_bytes(s.encode('utf-8'))
def save(p,v):write(p,json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def norm(s):return unicodedata.normalize('NFKC',s).strip()
courses=[read(p) for p in sorted((P/'courses').glob('*.json'))]
rows=list(csv.DictReader((P/'official/program-courses.csv').open(encoding='utf-8-sig')))
plans=read(P/'official/programs.json')
sources={'offerings':{'title':'2025秋、2026春官方教学班','path':'../official/sections.json'},'plan_rows':{'title':'2026级培养方案列课','path':'../official/program-courses.csv'}}
nodes={c['course_code']:{'id':c['course_code'],'name':c['course_name'],'aliases':c['official_name_variants'],'offered_terms':c['target_terms'],'level':sorted({s['course_level'] for s in c['official_sections']}),'teachers':c['teachers'],'scope':'offering','programs':[],'search_keys':{},'prerequisite_status':'未核定强制先修'} for c in courses}
for i,row in enumerate(rows):
    code=row['课程代码'];name=norm(row['课程名称'])
    if code not in nodes:nodes[code]={'id':code,'name':name,'aliases':[],'offered_terms':[],'level':['本科方案列课'],'teachers':[],'scope':'plan_only','programs':[],'search_keys':{},'prerequisite_status':'未核定强制先修'}
    n=nodes[code]
    n['aliases']=sorted(set(n['aliases']+[row['课程名称']]))
    n['programs'].append({'plan_id':row['方案编号'],'plan_name':row['方案名称'],'module':row['模块'],'terms_text':row['开设季节'],'suggest_terms_text':row['建议学期'],'remark':row['备注'],'department':row['开课院系'],'record_index':i})
    if n['scope']=='offering':n['scope']='offering_and_plan'
for p in plans:sources['plan'+p['方案编号']]={'title':p['方案名称'],'path':'../raw/official/plans/2026-plan-'+p['方案编号']+'-detail.json.gz','url':p['详情接口'],'word_sha256':p['SHA256']}
topics={'psych':'心理学与认知','social':'社会学与人类学','work':'社会工作与实务','policy':'政策、人口与老龄','data':'统计、计算与方法','general':'公共基础与跨院系选修','unresolved':'题名不足以判断'}
for n in nodes.values():
    code=n['id'];name=n['name']
    t='psych' if code.startswith(('PSYC','APSY','GEMH')) else 'work' if code.startswith('SWK') else 'social' if code.startswith('SOCI') else 'policy' if code.startswith(('MANA','MSP','MAA','ECON5','ECON6')) else 'data' if code.startswith(('AI','CS','MATH')) else 'general'
    if any(w in name for w in ['统计','数据','计算社会','机器学习','社会计算']):t='data'
    if code=='000.000.6':t='unresolved'
    n['topic']=t;n['topic_label']=topics[t]
edges=[];seen={};pathways=[]
def add(a,b,kind,reason,evidence=None,context=''):
    assert a in nodes and b in nodes,(a,b)
    assert a!=b
    if kind=='content_link':a,b=sorted([a,b])
    key=(a,b,kind)
    if key in seen:return seen[key]
    if evidence is None:
        evidence=[{'source':'offerings' if nodes[c]['scope']!='plan_only' else 'plan_rows','locator':c,'observed_title':nodes[c]['name']} for c in (a,b)]
    e={'id':'E'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:12],'source':a,'target':b,'type':kind,'directed':kind!='content_link','mandatory':False,'basis':'official_explicit_recommendation' if kind=='official_recommendation' else 'title_and_discipline_inference','confidence':'high' if kind=='official_recommendation' else 'provisional','reason':reason,'evidence':evidence,'context':context or '知识准备／内容关联为整理者推断，需按当期大纲与教师要求复核；不表示选课门槛或课程互认。','credit_equivalence':False}
    edges.append(e);seen[key]=e;return e
def chain(title,codes,reason,topic):
    codes=codes.split();pathways.append({'title':title,'course_ids':codes,'topic':topic,'status':'inferred_learning_path'})
    for a,b in zip(codes,codes[1:]):add(a,b,'recommended_preparation',reason)

# Explicit official recommendation: resolve the ambiguous title within each same plan.
audit={'plans_scanned':[],'prerequisite_fields':[],'explicit_recommendations':[],'hard_prerequisite_edges_verified':0}
for p in plans:
    pid=p['方案编号'];raw=P/sources['plan'+pid]['path'].removeprefix('../');v=json.loads(gzip.decompress(raw.read_bytes()))
    audit['plans_scanned'].append({'plan_id':pid,'path':sources['plan'+pid]['path'],'sha256':hashlib.sha256(raw.read_bytes()).hexdigest()})
    def walk(x,path=''):
        if isinstance(x,dict):
            for k,z in x.items():
                if k in ['defaultPreCourses','defaultPreCourseList']:audit['prerequisite_fields'].append({'plan_id':pid,'pointer':path+'/'+k,'empty':not bool(z)})
                walk(z,path+'/'+k)
        elif isinstance(x,list):
            for j,z in enumerate(x):walk(z,path+'/'+str(j))
    walk(v)
    for mi,m in enumerate(v['courseModules']):
        for ci,c in enumerate(m.get('planCourses',[])):
            remark=c.get('remark') or ''
            if '建议先修读变态心理学，再修读精神健康社会工作' in remark:
                candidates={r['课程代码'] for r in rows if r['方案编号']==pid and r['课程名称']=='变态心理学'}
                assert candidates=={'SWK30011'}
                target=c['course']['code'];assert target=='SWK40006'
                ev={'source':'plan'+pid,'pointer':f'/courseModules/{mi}/planCourses/{ci}/remark','locator':'专业进阶模块I／精神健康社会工作／备注','quote':remark}
                audit['explicit_recommendations'].append(ev)
                edge=add('SWK30011',target,'official_recommendation','培养方案明确建议先修变态心理学，再修精神健康社会工作。',[ev],'仅对应社会工作普通、留学生、港澳台侨生方案中的建议；不是系统强制先修。不能替换成心理学系同名课PSYC30023。')
                if ev not in edge['evidence']:edge['evidence'].append(ev)
assert len(audit['explicit_recommendations'])==3

# These arrows were read directly in the original curriculum figures.
for pid,a,b in [('153495','SOCI30020','SOCI30021')]:
    sid='figure'+pid
    sources[sid]={'title':next(p['方案名称'] for p in plans if p['方案编号']==pid)+'／课程体系图','path':'source-figures/'+pid+'-curriculum.png','basis':'official_figure_arrow','word_media_metadata':'source-figures/'+pid+'.json'}
    e=add(a,b,'curriculum_sequence','原方案课程体系图用箭头连接这两门课程，作为培养递进关系；图中未说明强制选课拦截。',[{'source':sid,'locator':nodes[a]['name']+' → '+nodes[b]['name']}],'只适用所引方案的课程体系；不能把培养顺序视为逐课硬性先修。')
    e['basis']='official_figure_arrow';e['confidence']='high'

chain('心理统计与数据分析','PSYC30017 PSYC30018 PSYC40006','统计基础可支持后续推断与高级分析；题名序号支持递进建议，具体知识边界须核对大纲。','psych')
chain('实验研究训练','PSYC30001 PSYC30002 PSYC30012 PSYC40004','由实验基础到实验设计与独立研究方案，是建议的能力准备路线。','psych')
chain('认知与神经科学','PSYC20001 PSYC30004 PSYC30025 PSYC60001','心理学概念、认知过程与神经机制之间存在逐步深入的知识准备联系。','psych')
chain('临床与咨询','PSYC20001 PSYC30023 PSYC30010 PSYC30019','导论及异常心理知识可为临床与咨询学习提供背景；此顺序仅为建议，不代表临床执业资格。','psych')
chain('心理测量','PSYC30017 PSYC30008 APSY60016','统计基础支持测量概念与工具评价；本科与专业硕士课并非同一培养路径。','psych')
chain('应用心理研究','APSY70009 APSY70010 APSY70002','应用统计、研究方法和实验专题可形成研究能力准备；跨学期要求待大纲确认。','psych')
chain('高级实验技术','PSYC30027 PSYC30028','依据题名序号提出技术训练的连续修读建议。','psych')
chain('心理专业实践','PSYC40002 PSYC40003','同一课号系列的实践一、二按序号提供学习顺序参考；不与2026方案新代码自动互认。','psych')
chain('社会学理论','SOCI20001 SOCI30020 SOCI30021 SOCI70001','导论提供概念，古典与当代理论可支持高级理论研读；跨培养层次的连接是知识准备。','social')
chain('社会研究方法','SOCI10003 SOCI20002 SOCI30034 SOCI40009','从方法基础、研究设计到调查与高级方法整理建议路线。','social')
chain('社会统计','SOCI20003 SOCI30006 SOCI50017 SOCI70009','统计基础和中级分析有助于进一步理解因果分析；具体模型依赖尚未获大纲确认。','social')
chain('质性与人类学','SOCI30002 SOCI30035 SOCI30039 SOCI60002','人类学视角与质性方法为田野研究和高级方法提供准备。','social')
chain('调查与论文','SOCI30034 SOCI40004 SOCI40005 SOCI40003 SOCI40006','建议先练习调查设计与调查实践，再形成论文；不是从开课学期机械推断的硬性链。','social')
chain('人口研究','SOCI30008 SOCI30018 SOCI50019','人口理论背景与人口分析可衔接统计与分析技术。','policy')
chain('社会工作个案实务','SWK20002 SWK30001 SWK40004 SWK40002 SWK40003','导论、个案方法与技巧训练可为专业实习做准备；须按具体方案确认实践准入。','work')
chain('社会工作政策与评估','SWK30006 SWK30014 SWK30015','政策与福利制度背景可支持服务评价；建议补充研究方法，不能仅以本链代替先修清单。','work')
chain('社会工作研究与写作','SWK30017 SWK30020 SWK40001','质性研究与实务研究可支持毕业论文的问题设计与资料分析。','work')
chain('社区项目设计','SOCI30049 SOCI30052 SWK30015','社区工作与项目设计可衔接项目及服务评估；跨代码方案不表示学分替代。','work')
chain('公共政策研究','MANA50013 MANA50011 MANA50020','公共管理背景、政策分析与政策研究构成建议的概念到分析路线。','policy')
chain('政策建模','MANA50011 MANA50015 MANA60073','政策分析可为系统动力学、政策模拟与实验提供问题框架。','policy')
chain('老龄服务','SOCI50059 SOCI50055 MAA70002','老年学与健康老龄化议题可为老年社会工作实务提供背景。','policy')
chain('统计软件应用','SOCI30006 SOCI30029 SOCI50020','社会统计知识可支撑软件操作与统计计算；软件课可能并行修读。','data')
chain('计算社会科学','AIB110002 AIE310007 SOCI30046 AIS631008','编程、数据结构及机器学习可为计算社会科学提供工具准备；不是强制选课链。','data')
chain('人工智能工具','AIE310009 AIE410001 AIE410002','数学基础、机器学习和语言模型之间存在方法准备联系，具体先修依赖须补充AI课程大纲。','data')
chain('空间分析','MSP60001 SOCI40011','GIS工具知识有助于空间数据分析与应用。','data')
for a,b,reason in [
('PSYC30017','PSYC30012','统计知识支持实验设计中的变量控制、数据分析与结果解释。'),('PSYC30026','PSYC40001','质性研究方法可支持采用访谈、观察等设计的论文。'),('PSYC30024','PSYC40001','研究技术和数据处理可为实证论文提供工具准备。'),('PSYC30008','APSY60006','测量知识可帮助理解评估工具的适用范围与测量质量。'),('APSY60008','APSY70004','访谈技巧可为个体咨询案例训练提供实践准备。'),('SOCI30035','SOCI50044','质性方法基础可衔接高级质性方法。'),('SOCI30032','SOCI40003','论文写作练习可支持学年论文。'),('SWK30007','SWK40002','专业伦理为实习中的服务边界与专业判断提供准备。'),('SWK30005','SWK30001','理解个体与环境的关系有助于个案问题评估。'),('SWK30002','SWK40004','小组方法可以作为技巧训练的一类实务基础。'),('SWK30011','SWK30012','异常心理背景可为家庭治疗相关问题理解提供知识准备。'),('MATH10031','AIE410001','线性代数为机器学习中的向量与矩阵方法提供基础；A/B课程不得自动替代。'),('MATH10029','PSYC30017','数学基础有助于统计概念理解；是否要求特定数学课须按心理学方案确认。'),('SOCI30006','SOCI30037','统计知识可支持统计软件应用；与SOCI30029同名但不自动合并。')]:add(a,b,'recommended_preparation',reason)

# Specific cross-field content connections. No arrows and no equivalence claims.
for a,b,reason in [
('SOCI30006','PSYC30017','共同涉及统计方法，应用问题分别来自社会研究与心理研究。'),('SOCI30035','PSYC30026','共享质性研究的方法主题，学科对象和训练要求可能不同。'),('SOCI30035','SWK30017','共享访谈、观察等质性研究主题；具体方法覆盖待大纲复核。'),('SOCI30006','SWK10001','共享社会统计基础主题，课程层次及方案要求不同。'),('PSYC30006','SOCI70006','社会心理学与其著作研读共享学科主题，不能据此设定本科到博士的强制链。'),('PSYC30003','SWK30005','发展过程与个体—环境关系在分析人的行为时可互相参照。'),('PSYC30023','SWK30011','两课题名均为变态心理学，保留不同代码与专业背景；不推定可替代官方建议先修。'),('PSYC30019','SWK30012','心理咨询治疗与家庭治疗在助人方法及家庭问题上相邻。'),('PSYC30019','APSY60005','共同讨论咨询与治疗；后者是专业硕士专题，目标和深度需分别核对。'),('SOCI30030','APSY60009','婚姻家庭的社会结构与心理过程可形成跨学科视角。'),('SOCI30014','SWK30008','医疗健康的社会解释与医疗社会工作实务相关。'),('SOCI30038','SOCI60003','医学人类学题名一致，代码和培养层次分开保留。'),('SWK30009','MAA70002','共同关注老年社会工作实务，培养层次不同。'),('SWK30006','MSP50005','社会政策主题相邻，不能由同名推断内容与学分等价。'),('MANA50024','GEEC10008','卫生政策与健康管理共享健康治理议题。'),('SOCI30008','GEEC10399','人口社会学与人口学概论共享人口问题背景。'),('SOCI30013','ECON50016','城市社会与人口迁移、城市化存在议题联系。'),('SOCI30011','ECON60021','环境社会学与资源环境经济学从不同学科分析环境问题。'),('SOCI30033','CS60021','互联网与社会研究、社会计算共享数字社会议题。'),('SOCI30031','MANA50023','社会网络与政策网络可共享网络分析视角。'),('SOCI30044','SOCI50040','社会资本与关系研究共享社会关系资源主题。'),('SWK40006','SWK50013','精神健康社会工作与精神卫生机构实务共享服务领域。'),('SWK30004','SWK50005','社会工作行政与服务机构管理存在组织管理联系。'),('SWK30015','SWK50007','社会工作评估与社会服务评估共享评价主题。')]:add(a,b,'content_link',reason)

# Topic navigation is deliberately weaker than knowledge dependencies.
thematic=[('老龄与老年服务','老龄|老年|养老|银发|长寿','SOCI50059'),('人口研究','人口|死亡率|迁移','SOCI30008'),('家庭与婚姻','家庭|婚姻','SOCI30030'),('社会政策','社会政策|社会保障|福利','SWK30006'),('临床与咨询','临床|咨询|治疗|精神分析','PSYC30019'),('文化与人类学','人类学|文化社会学','SOCI30002'),('统计分析','统计','SOCI30006'),('数字社会与AI','人工智能|数据|计算社会|社会计算|互联网|数字|数智','AIS631008')]
for label,pattern,hub in thematic:
    for n in nodes.values():
        if n['id']!=hub and n['scope']!='plan_only' and re.search(pattern,n['name']):
            e=add(hub,n['id'],'content_link','题名显示共同涉及“'+label+'”；作为宽泛主题导航，实际内容重叠须由大纲确认。')
            if e['reason'].startswith('题名显示'):e['confidence']='low';e['basis']='title_theme_only'
for n in list(nodes.values()):
    if n['id'].endswith('h') and n['id'][:-1] in nodes:
        add(n['id'][:-1],n['id'],'content_link','普通与荣誉课程共享题名主题；要求、深度与考核可能不同，不自动继承先修或认定互认。')

clusters=[
('发展与教育','PSYC30003 PSYC30005 APSY60001 PSYC60004'),('社会心理与组织','PSYC30006 APSY60002 PSYC60006 PSYC30009 APSY60022'),('决策与消费','PSYC30021 APSY60013 APSY60019 PSYC30011'),('认知与人因','PSYC30004 APSY60003 APSY60015 AIS731001 PSYC30014'),('健康与心理成长','PSYC70013 APSY60017 GEMH10001 GEMH10008 GEMH10009 GEMH10010 GEMH10013 GEMH10014 GEMH10016 GEMH10017 SWK20001'),('心理辅导与助人','APSY60014 GEMH10018 PSYC30019'),('心理研究技术','PSYC30024 PSYC60005'),('异常心理与精神医学','PSYC30023 APSY60023'),('职业与生涯','PSYC30013 GEEC10388'),
('社会研究方法','SOCI20002 GECC10115 GEEC10383 MAA60004 MSP60003 SOCI70002 SOCI60011 SWK60002 SWK60009'),('调查实践','SOCI40004 MSP50006'),('理论与思想史','SOCI30020 SOCI10004 SOCI30022 SOCI40008 SOCI50057'),('城市与城乡变迁','SOCI30013 GECC10117 SOCI30012 SOCI50006 SOCI30010'),('当代中国社会','SOCI20004 MSP50003 SOCI50004 GEEC10400'),('文化与社会','SOCI30023 GECC10116 SOCI50030 SOCI50039'),('青年研究','SOCI30047 SOCI10001'),('宗教与社会','SOCI30015 SOCI30027 SOCI50021'),('政治与社会','SOCI30005 SOCI50037'),('经济与劳动','SOCI30004 SOCI60014 ECON50018'),('社会分层','SOCI30026 SOCI50025'),('迁移与移民','SOCI30043 SOCI50045'),('社会性别','PSYC30020 GEEC10385'),('健康与文化','SOCI30014 SOCI30042'),('社会关系与情感','SOCI30040 SOCI30030'),('人口与生命','SOCI30008 SOCI50003 SOCI70004'),('公共危机','MANA50012 MANA50022'),('政策与管理','MANA50011 MANA60072'),('地理信息系统','MSP60001 MANA60071'),('统计建模','SOCI50017 ECON60022'),
('社会工作理论','SWK30019 SWK50002 SOCI50041'),('社会工作伦理','SWK30007 SWK50001 SOCI50047 SWK30010'),('社区与宏观工作','SOCI30003 SOCI30049 SWK50003 SOCI50028'),('公益组织与志愿服务','SWK30013 SOCI30001 SWK50019'),('医疗社会工作','SWK30008 SWK50010 SWK60006'),('儿童与发展服务','SWK30021 SOCI20011'),('社会工作督导','SWK50017 SWK40002'),('社会创新','GEIN10049 GEIN10052 GEXZ10027'),('学术写作','SOCI30032 SOCI50056 MAA70001'),('专业语言','SOCI40002 SOCI50002 SWK40005 MAA60005')]
for theme,codes in clusters:
    ids=codes.split()
    for code in ids[1:]:
        e=add(ids[0],code,'content_link','题名与学科视角共同涉及“'+theme+'”；仅标示内容联系，具体覆盖深度与方法需由各课大纲确认。')
        if e['reason'].startswith('题名与'):e['basis']='title_theme_only';e['confidence']='low'
for a,b in [('SOCI60004','SOCI60005'),('SOCI80002','SOCI80003'),('SOCI80003','SOCI80004')]:
    add(a,b,'content_link','同一系列讨论班；专题可能随学期变化，只标记系列联系，不推断先修顺序。')
connected={x for e in edges for x in (e['source'],e['target'])}
for n in nodes.values():n['relationship_status']='mapped' if n['id'] in connected else 'needs_syllabus';n['notes']='尚无足够材料连接具体课程，保留节点待补充大纲。' if n['id'] not in connected else ''
g={'schema_version':'1.0.0','generated_on':'2026-11-19','title':'社会发展与公共政策学院课程关系图谱','scope':{'offering_terms':['2025秋','2026春'],'program_grade':'2026','offering_course_codes':296,'plan_course_codes':525,'plan_only_course_codes':385,'total_course_codes':len(nodes),'strict_prerequisite_edges_verified':0,'coverage_note':'完整纳入296个开课代码及15份方案列课，共681个代码；含方案引用的公共及跨院系选修，未取得大纲者允许无连线。'},'relation_types':{'official_recommendation':{'label':'官方建议先修','directed':True,'mandatory':False},'recommended_preparation':{'label':'建议知识准备（推断）','directed':True,'mandatory':False},'content_link':{'label':'内容联系（无方向）','directed':False,'mandatory':False}},'limitations':['仅检索到1对明确官方建议先修关系；没有可核验的强制先修边。空的defaultPreCourse字段不代表该课没有先修要求。','2026方案与2025秋—2026春开课是不同时间范围；不按开课先后、代码大小或学期列课机械连边。','建议知识准备与内容联系为题名和一般学科知识推断，尚未逐课取得教学大纲。主题导航尤其不代表内容等同。','荣誉课、跨专业同名课、旧新课程代码均独立保留；跨培养层次的联系是知识背景，不保证课程开放选修或学分互认。','方案原件配图附供复核，本版未把图中版面位置当作逐课强制先修证据。','图中无连线的课程表示资料不足，不表示该课程独立或没有先修。'],'sources':sources,'topics':topics,'nodes':sorted(nodes.values(),key=lambda n:n['id']),'edges':edges,'pathways':pathways}
g['relation_types']['curriculum_sequence']={'label':'官方培养顺序','directed':True,'mandatory':False}
save(R/'graph.json',g);save(R/'source-audit.json',audit)
for filename,fields,values in [('nodes.csv',['id','name','topic_label','scope','level','offered_terms','relationship_status'],g['nodes']),('edges.csv',['id','source','target','type','directed','mandatory','confidence','basis','reason','evidence'],edges)]:
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader()
    for row in values:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items() if k in fields})
    write(R/filename,'\ufeff'+out.getvalue())
print(json.dumps({'nodes':len(nodes),'edges':len(edges),'types':dict(collections.Counter(e['type'] for e in edges)),'connected_offering_codes':sum(n['id'] in connected for n in nodes.values() if n['scope']!='plan_only'),'unmapped_offering_codes':sum(n['id'] not in connected for n in nodes.values() if n['scope']!='plan_only')}))
