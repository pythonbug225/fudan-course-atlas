import pathlib,json,collections,re,csv,hashlib,html,shutil,zipfile,importlib.util
from curation import FIGURE_LINKS,PREPARATION,CONTENT_CHAINS,CONTENT_PAIRS
R=pathlib.Path(__file__).resolve().parent;S=R/'sources';O=R if R.name=='course-graph' else R/'course-graph';O.mkdir(exist_ok=True)
SNAPSHOT='802ace3b97a20c334818673331c5f4728773156b'
BASE='https://github.com/pythonbug225/fudan-course-atlas/blob/'+SNAPSHOT+'/research/contributions/journalism/'
def load(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
catalog=load(S/'course_catalog.json');program_index=load(S/'program-course-index.json')
groups=[('规范与伦理','法规|伦理|规制|法律|版权|责任|经济法'),('语言与表达','语言|英语|外语|口语|经典阅读'),('研究与方法','研究方法|研究设计|论文|文献|数据科学|量化|质化|计算|数据分析|数据挖掘|舆论分析方法'),('广告与战略传播','广告|品牌|营销|消费|商业|公共关系|企业|战略|公共外交|说服|洞察与创新|公共事务'),('国际与跨文化','跨文化|国际|全球|对外|全球化|China’s International|Reporting'),('视听与艺术','视听|影|纪录|音频|剧本|电视|动漫|播客|无人机|娱乐|音乐|镜前|New Chinese Cinema|美术'),('数字与智能媒介','新媒体|新媒介|媒介产品|平台|数字|智能|融合|信息互动|交互|用户体验|用户行为|网络数据|Emerging Media'),('采访编辑与报道','采访|报道|编辑|新闻评论|新闻实务|新闻叙事|新闻作品|非虚构|核查|内容生产|新闻生产'),('传播与社会','舆论|人际|组织传播|健康传播|政治传播|受众|认知|心理|城市传播|传播学|传播研究|传播理论|媒介与社会|媒介批评|传媒与文化|媒介政治经济|Communication'),('新闻史与思想','新闻史|新闻传播史|新闻思想|工作理论|新闻学|文化思想|中外新闻|新闻业|学说史|经典著作'),('媒介经营与财经','经营|管理|媒介经济|金融|财经|经济学|财务|产业|经济与社会'),('实践与毕业训练','实习|毕业|实践|工作坊|工作室|发展与生涯')]
def group(name):return next((g for g,pat in groups if re.search(pat,name,re.I)),'公共与跨学科')
by=collections.defaultdict(list)
for r in catalog:by[r['course_code']].append(r)
nodes=[];memberships=[]
for code in sorted(set(by)|set(program_index)):
 rows=by.get(code,[]);prs=program_index.get(code,[])
 name=rows[0]['course_name'] if rows else prs[0]['name']
 variants=sorted({x['course_name'] for x in rows}|{x['name'] for x in prs})
 seen=set();ms=[]
 for p in prs:
  key=(p['program'],p['name'],p['terms_text'],p['compulsory'])
  if key in seen:continue
  seen.add(key);entry={k:p[k] for k in ['program','program_name','code','name','terms','terms_text','compulsory','path']};ms.append({k:entry[k] for k in ['program','name','terms_text','compulsory']});memberships.append(entry)
 nodes.append({'id':code,'name':name,'name_variants':variants,'group':group(name),'scope':'offering_2025_2026' if rows else 'program_2026_only','levels':sorted({r['course_level'] for r in rows}) or ['方案列课（层次未按课号推断）'],'teachers':sorted({t for r in rows for t in r['teachers']}),'terms':sorted({r['term'] for r in rows}),'program_ids':sorted({p['program'] for p in prs}),'program_memberships':ms,'prerequisite_status':'not_verified','syllabus_content_status':'not_available_in_this_snapshot','source_ids':(['catalog'] if rows else [])+['plan:'+x for x in sorted({p['program'] for p in prs})]})
N={n['id']:n for n in nodes};edges=[];seen=set()
def add(a,b,kind,why,evidence,**extra):
 assert a in N and b in N,(a,b)
 directed=kind in ['official_curriculum_link','suggested_preparation']
 if not directed:a,b=sorted([a,b])
 key=(a,b,kind)
 if a==b or key in seen:return
 seen.add(key);edges.append({'id':f'e{len(edges)+1:03}','source':a,'target':b,'type':kind,'directed':directed,'reason':why,'evidence':evidence,'is_enrollment_prerequisite':False,**extra})
for pid,a,b,loc in FIGURE_LINKS:
 assert all(any(p['program']==pid for p in N[c]['program_memberships']) for c in [a,b])
 add(a,b,'official_curriculum_link','2026培养方案配图中的有向课程联系；表示培养设计，不等于系统先修条件。',[{'source_id':'figure:'+pid,'locator':loc,'figure':'source-figures/'+pid+'.png','program':pid}],confidence='direct_figure',program_scope=pid)
for a,b,why in PREPARATION:
 add(a,b,'suggested_preparation',why,[{'source_id':'catalog','locator':a+' / '+b,'basis':'课程题名与一般学科训练逻辑，未核对逐班大纲。'}],confidence='inferred')
for theme,chain,why in CONTENT_CHAINS:
 for a,b in zip(chain.split(),chain.split()[1:]):
  if N[a]['name']==N[b]['name']:continue
  add(a,b,'content_related',why,[{'source_id':'catalog_and_program_index','locator':a+' / '+b,'basis':'题名及学科主题关联，属于整理者解释；不是大纲内容逐项比对。'}],confidence='inferred',theme=theme)
for a,b,why in CONTENT_PAIRS:
 add(a,b,'content_related',why,[{'source_id':'catalog_and_program_index','locator':a+' / '+b,'basis':'题名与学科场景解释，未核对逐班大纲。'}],confidence='inferred')
byname=collections.defaultdict(list)
for n in nodes:
 for name in n['name_variants']:byname[name].append(n['id'])
for name,codes in byname.items():
 codes=sorted(set(codes))
 for i,a in enumerate(codes):
  for b in codes[i+1:]:add(a,b,'same_name_distinct_code','同名“'+name+'”但课号不同；保留为不同节点，不认定互认、替代、同一班或同一层次。',[{'source_id':'catalog_and_program_index','locator':name}],confidence='exact_name_only')
figures=load(S/'figure-index.json');(O/'source-figures').mkdir(exist_ok=True)
for pid in ['153731','153733','153736','153741']:shutil.copy2(S/'figures'/f'{pid}-0.png',O/'source-figures'/f'{pid}.png')
programs=[]
for p in sorted((S/'official/program-responses').glob('*.json')):
 d=load(p);programs.append({'id':p.stem,'name':d['model']['nameZh'],'json_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'curriculum_section':d['programContent']['paragraphs'][6]['titleZh'],'source':BASE+'official/official-originals.zip'})
audit={'date':'2026-11-19','snapshot_commit':SNAPSHOT,'catalog_sections':352,'catalog_course_codes':207,'catalog_unique_names':203,'programs_checked':27,'program_only_additional_codes':len(N)-207,'graph_nodes':len(N),'all_hard_prerequisite_fields_status':'未发现具名先修条款；不等于没有先修要求。','textual_prerequisite_hits':0,'curriculum_figures_extracted':len(figures),'unique_figure_hashes':len({f['sha256'] for f in figures}),'figures_visually_read':['153731','153733','153736','153741'],'confirmed_enrollment_prerequisite_edges':0,'scope_limits':['2025秋—2026春开课快照与2026级培养方案分别标记；本图不声称当前学期已开出全部方案列课。','未取得逐班教学大纲；内容联系与建议知识准备主要以课程题名和通用学科逻辑整理。','没有按课号大小、难度等级、秋春开课先后推断强制先修；也没有生成所有较早/较晚课程之间的边。','同名异号、本研课程、方案名称变化不自动合并，内容联系不表示学分互认。','四张官方课程体系配图中的15条清晰课程箭头被编码；未把其余活动、未清楚判读箭头及整张图都宣称为已结构化。'],'programs':programs}
source_links={'catalog':{'title':'2025秋—2026春官方352班目录','url':BASE+'official/course_catalog.json','sha256':hashlib.sha256((S/'course_catalog.json').read_bytes()).hexdigest()},'catalog_and_program_index':{'title':'官方课名与2026方案列课索引','path':'program-memberships.json'}}
for p in programs:source_links['plan:'+p['id']]={'title':p['name'],'url':p['source']}
for pid in ['153731','153733','153736','153741']:source_links['figure:'+pid]={'title':next(p['name'] for p in programs if p['id']==pid)+'：课程体系与科研训练体系','path':'source-figures/'+pid+'.png','url':BASE+'official/official-originals.zip'}
graph={'schema':'fudan-journalism-course-graph/1','generated_date':'2026-11-19','title':'新闻学院课程关系图谱','relation_types':{'official_curriculum_link':'方案配图联系（有向）','suggested_preparation':'建议知识准备（有向）','content_related':'内容联系（无向）','same_name_distinct_code':'同名异号（无向）'},'nodes':nodes,'edges':edges,'sources':source_links,'audit':{k:v for k,v in audit.items() if k!='programs'}}
save(O/'graph.json',graph);save(O/'program-memberships.json',memberships);save(O/'source-audit.json',audit)
for filename,rows in [('nodes.csv',[{k:n[k] for k in ['id','name','name_variants','group','scope','levels','terms','teachers','program_ids','prerequisite_status']} for n in nodes]),('edges.csv',edges)]:
 with (O/filename).open('w',encoding='utf-8-sig',newline='') as f:
  keys=list(dict.fromkeys(k for row in rows for k in row));cw=csv.DictWriter(f,fieldnames=keys);cw.writeheader();cw.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
# Portable graph viewer: no network requests or third-party libraries.
template=(R/'viewer-template.html').read_text(encoding='utf8');(O/'课程关系图谱.html').write_text(template.replace('__GRAPH_DATA__',json.dumps(graph,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')),encoding='utf8')
def svg():
 esc=lambda v:html.escape(str(v));w=1540;rh=130;h=145+5*rh
 tracks=[('新闻采编：建议准备','JCM10002 JCM20012 JCM20027 JCM30018'),('传播研究：建议准备','JCM10003 JCM20013 JCM30024 JCM50096 JCM40003'),('视听：2026方案配图','JCM20007 JCM20008 JCM20030'),('广告：2026方案配图','JCM10003 JCM20002 JCM20003 JCM20005 JCM30022'),('财经报道：建议准备','MJC60022 MJC70021 MJC70014')]
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">新闻学院课程关系主线</title><desc id="desc">绿色实线为2026官方方案配图中的课程联系；橙色虚线为建议知识准备。所有箭头均不表示强制先修。完整{len(nodes)}节点见交互图谱。</desc><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="context-stroke"/></marker></defs><rect width="100%" height="100%" fill="#f5f8fb"/><g font-family="Microsoft YaHei,Noto Sans CJK SC,sans-serif"><text x="32" y="42" font-size="26" fill="#193647">新闻学院 · 课程关系主线</text><text x="32" y="75" font-size="15" fill="#4c6474">方案配图联系 ≠ 强制先修；虚线为整理者建议。按课号保留同名及不同版本，原始依据见交互图谱。</text>']
 for i,(title,codes) in enumerate(tracks):
  y=105+i*rh;s.append(f'<text x="32" y="{y+40}" font-size="15" fill="#314e5d">{esc(title)}</text>');cs=codes.split()
  for j,c in enumerate(cs):
   x=245+j*252
   if j:
    color='#187f72' if '方案' in title else '#a66c26';dash='' if '方案' in title else ' stroke-dasharray="6 4"'
    s.append(f'<line x1="{x-35}" y1="{y+32}" x2="{x-5}" y2="{y+32}" stroke="{color}" stroke-width="2"{dash} marker-end="url(#arrow)"/>')
   label=N[c]['name'];s.append(f'<rect x="{x}" y="{y}" width="218" height="70" rx="8" fill="white" stroke="#b8ced8"/><text x="{x+10}" y="{y+20}" font-size="11" fill="#617d8e">{c}</text>')
   for k in range(0,len(label),14):s.append(f'<text x="{x+10}" y="{y+42+(k//14)*17}" font-size="14" fill="#203f52">{esc(label[k:k+14])}</text>')
 s.append('</g></svg>');return ''.join(s)
(O/'课程关系主线.svg').write_text(svg(),encoding='utf8')
readme=['# 新闻学院课程关系图谱','','覆盖原官方课表207个课程代码，并补入2026级培养方案中74个新闻学院方案列课代码，共281个节点。按课号建图；原203课名查询单保持原样。','','- [交互图谱](课程关系图谱.html)：下载course-graph目录后双击打开；搜索、方向/层次筛选、邻接图、关系证据、SVG导出均可离线使用。','- [课程主线图](课程关系主线.svg)：GitHub可直接预览。','- [图谱JSON](graph.json) · [节点CSV](nodes.csv) · [关系CSV](edges.csv)。','- [方案列课定位](program-memberships.json) · [来源审计](source-audit.json) · [校验结果](validation.json)。','','## 四种关系','','| 类型 | 方向 | 含义 |','|---|---|---|','| 方案配图联系 | 有向 | 2026官方课程体系图中的清晰课程箭头；保留方案和配图位置，不称为选课先修。 |','| 建议知识准备 | 有向 | 根据题名和学科训练逻辑给出的学习准备；逐条写出技能联系，尚无逐班大纲证明。 |','| 内容联系 | 无向 | 课程主题、方法、材料或实践场景存在联系；未认定内容完全重合。 |','| 同名异号 | 无向 | 标出名字相同而课号不同的课程，便于核查；不表示课程替代或学分互认。 |','','目前在27份保存的官方培养方案中未找到具名的“必须先修”条款，也未取得逐班教学大纲。因此**图谱没有已确认的强制先修边**；这不等于学校、专业或具体教学班没有先修要求。四张体系图已直接核读；其中15条明确课程箭头录入。其他配图和实践活动没有被冒充为已经完整结构化。','','## 怎样使用','','先在课程列表中选课，看左侧入边、右侧出边和下方相关课程。点击任意关系可看理由、证据位置和方案适用范围。方向图展示同一主题的课程；“总览”用于切换主题，避免把281门课挤成不可读的连线。方案新增74课默认隐藏，可开启“含2026方案列课”查看。','','本科与研究生分层显示；同名课程保留独立代码。方案列课节点不声称已在2025秋或2026春开课，也不按JCM/MJC或数字大小推断层次。培养方案中的学期和难度等级没有被转换为强制先修关系。','','## 原件与复现','','所有资料来自此分支已有快照，未进行新的课评抓取。原件为[官方原始材料ZIP](../official/official-originals.zip)和[官方课程目录](../official/course_catalog.json)；源快照固定到 `'+SNAPSHOT+'`。','','- [新闻学方案体系图](source-figures/153741.png)','- [传播学方案体系图](source-figures/153731.png)','- [广播电视学方案体系图](source-figures/153733.png)','- [广告学方案体系图](source-figures/153736.png)','','`curation.py`保留每条人工关系的理由。`build_graph.py`配合原件提取的sources目录可重新生成；`validate_graph.py`可在本目录离线核查节点、边、引用和有向环。图谱文件中的官方源定位可在原始ZIP对应JSON的JSON路径和Word“课程体系与科研训练体系”中复核。','','节点数：'+str(len(nodes))+'；关系数：'+str(len(edges))+'。分类：'+json.dumps(dict(collections.Counter(e['type'] for e in edges)),ensure_ascii=False)+'。']
readme=[x.replace('74个',str(len(nodes)-207)+'个').replace('281',str(len(nodes))).replace('74课',str(len(nodes)-207)+'课') for x in readme]
readme=[x.replace('`build_graph.py`配合原件提取的sources目录可重新生成；','下载本院系完整目录后，依次运行 `python prepare_sources.py`、`python extract_program_index.py`、`python build_graph.py` 可重建；') for x in readme]
(O/'README.md').write_text('\n'.join(readme)+'\n',encoding='utf8')
if R!=O:
 for filename in ['curation.py','viewer-template.html','build_graph.py','extract_program_index.py','prepare_sources.py']:shutil.copy2(R/filename,O/filename)
print(json.dumps({'nodes':len(nodes),'edges':len(edges),'types':dict(collections.Counter(e['type'] for e in edges)),'offering_codes':len(by),'program_only':len(nodes)-len(by)},ensure_ascii=False))
