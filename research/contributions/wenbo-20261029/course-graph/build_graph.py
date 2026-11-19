import argparse,collections,gzip,hashlib,html,json,re,shutil
from pathlib import Path
from curation import GROUPS,PREPARATION,CONTENT,PATHS

W=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--handbook',type=Path,help='官方2024手册PDF的本地路径')
parser.add_argument('--cache-dir',type=Path,help='仅在本地保存的PDF文字提取缓存')
args=parser.parse_args()
in_repository=(W.parent/'official/courses.json').exists()
BASE=W.parent if in_repository else W.parent/'wenbo-publish/research/contributions/wenbo-20261029'
CACHE=args.cache_dir or (W/'.build-cache' if in_repository else W)
CACHE.mkdir(exist_ok=True,parents=True)
PDF=args.handbook or CACHE/'official-handbook.pdf'
if not (CACHE/'handbook-pages.json').exists():
 from pypdf import PdfReader
 pages=[page.extract_text() or '' for page in PdfReader(PDF).pages]
 (CACHE/'handbook-pages.json').write_text(json.dumps(pages,ensure_ascii=False),'utf-8')
if not (CACHE/'handbook-sections.json').exists():
 pages=json.loads((CACHE/'handbook-pages.json').read_text('utf-8'));ss=[]
 for i,text in enumerate(pages):
  match=re.search(r'《([^》\n]+)》[\s\S]{0,100}?一、基本信息',text[:450])
  if match:
   code=re.search(r'课程代码\s*([A-Z]+\d+)',text[:700])
   ss.append(dict(name=match.group(1).strip(),start_page=i+1,legacy_code=code.group(1) if code else None))
 for i,section in enumerate(ss):
  section['end_page']=ss[i+1]['start_page']-1 if i+1<len(ss) else len(pages)
  section['text']='\n'.join(pages[section['start_page']-1:section['end_page']])
 (CACHE/'handbook-sections.json').write_text(json.dumps(ss,ensure_ascii=False),'utf-8')
OUT=BASE/'course-graph';OUT.mkdir(exist_ok=True)
COMMIT='c86c5d3eaa692022ee9b8a6439c21c35ffde4244'
REPO='https://github.com/pythonbug225/fudan-course-atlas'
PREFIX='research/contributions/wenbo-20261029/'
BOOK='https://jwc.fudan.edu.cn/_upload/article/files/d4/56/707002a8413b8a3cc690244c1118/62a17cae-2a02-4686-b167-07cd85099113.pdf'
def read(p):return json.loads(Path(p).read_text('utf-8'))
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8',newline='\n')
def esc(x):return html.escape(str(x))
def sourceurl(p):return REPO+'/blob/'+COMMIT+'/'+PREFIX+p

catalog=read(BASE/'official/courses.json');plans=read(BASE/'official/programme-courses.json')
sections=read(CACHE/'handbook-sections.json');page_texts=read(CACHE/'handbook-pages.json')
groups={code:gid for gid,_,codes in GROUPS for code in codes.split()}
all_codes={c['课程代码'] for c in catalog}
assert all_codes==set(groups),(all_codes-set(groups),set(groups)-all_codes)
nodes={}
for c in catalog:
 code=c['课程代码']
 n=nodes.setdefault(code,dict(id=code,name=c['课程名称'],group=groups[code],offerings=[],programmes=[],historical_handbook=[],current_prerequisite_status='not_verified',source_refs=[sourceurl('official/courses.json')]))
 n['offerings'].append({k:c[k] for k in ['学期','教师','开课业务类型','课程类别','教学班数']})
for code,n in nodes.items():
 n['business_types']=sorted({x['开课业务类型'] for x in n['offerings']})
 n['teachers']=sorted({t for c in n['offerings'] for t in c['教师'].split('、') if t})
 n['programmes']=sorted({r['方案编号'] for r in plans if r['课程代码']==code})
 n['is_honors_variant']=code.endswith('h')
namecodes=collections.defaultdict(list)
for c,n in nodes.items():namecodes[n['name']].append(c)

TYPE_LABELS={
 'historical_prerequisite':'2024手册预修要求',
 'historical_recommended':'2024手册建议预修',
 'historical_followup':'2024手册后续课程',
 'recommended_preparation':'内容推断：建议先学',
 'content_related':'内容联系',
 'parallel_variant':'普通／H同主题班型',
 'same_name_distinct_code':'同名异号，分别保留',
}
edges=[];tables=[];unmapped=[];audits=[]
def add(a,b,kind,reason,source_refs=None,confidence='中',**extra):
 assert a in nodes and b in nodes and a!=b,(a,b)
 directed=kind not in ['content_related','parallel_variant','same_name_distinct_code']
 if not directed and a>b:a,b=b,a
 e=next((e for e in edges if (e['source'],e['target'],e['type'])==(a,b,kind)),None)
 if e:
  for r in source_refs or []:
   if r not in e['source_refs']:e['source_refs'].append(r)
  return e
 e=dict(id=f'E{len(edges)+1:03}',source=a,target=b,type=kind,label=TYPE_LABELS[kind],directed=directed,confidence=confidence,reason=reason,source_refs=source_refs or [sourceurl('official/courses.json')],current_enrollment_rule=False,assertion_scope='historical_2024_undergraduate' if kind.startswith('historical') else 'editorial_content_inference',**extra)
 edges.append(e);return e
def tokens(text):
 text=re.sub(r'\s+','',text)
 quoted=re.findall('《([^》]+)》',text)
 return quoted if quoted else [x for x in re.split('[、，,；;]',text.replace('建议预修','')) if x not in ('','无')]

for section in sections:
 name=section['name']
 if name not in namecodes:continue
 candidates=[c for c in namecodes[name] if nodes[c]['business_types']==['本科'] and not c.endswith('h')]
 match=re.search(r'预修课程\s*(.*?)\s*后续课程\s*(.*?)\s*教学方式',section['text'],re.S)
 if not match:continue
 pre=' '.join(match.group(1).split());post=' '.join(match.group(2).split())
 record=dict(course_name=name,legacy_course_code=section['legacy_code'],pdf_page=section['start_page'],printed_page=section['start_page']-5,preparation_field=pre,followup_field=post,mapping_status='unique_same_title_undergraduate' if len(candidates)==1 else 'ambiguous_or_out_of_scope',candidate_current_codes=candidates,source_url=BOOK+'#page='+str(section['start_page']),note='按同名本科课程对应历史内容，不构成官方课号沿革证明或当期约束。')
 tables.append(record)
 if len(candidates)!=1:
  if pre not in ('','无') or post not in ('','无'):unmapped.append(dict(record,reason='同名当前课程不唯一，不把历史要求自动挂到任何一个课号。'))
  continue
 current=candidates[0];nodes[current]['historical_handbook'].append(record)
 for token in tokens(pre):
  targets=[c for c in namecodes.get(token,[]) if nodes[c]['business_types']==['本科'] and not c.endswith('h')]
  if len(targets)==1:
   kind='historical_recommended' if '建议' in pre else 'historical_prerequisite'
   add(targets[0],current,kind,'2024手册对本课的'+('建议预修' if '建议' in pre else '预修')+'字段列出该课程；本次未核验当前学年的执行要求。',[record['source_url']],confidence='高（历史字段事实）',legacy_target_code=record['legacy_course_code'],field=pre)
  else:unmapped.append(dict(course_code=current,course_name=name,requirement_name=token,pdf_page=record['pdf_page'],reason='不在133课程清单内或名称不能唯一对应；不替换成近似课程名。',source_url=record['source_url']))
 for token in tokens(post):
  targets=[c for c in namecodes.get(token,[]) if nodes[c]['business_types']==['本科'] and not c.endswith('h')]
  if len(targets)==1:
   a,b=current,targets[0]
   existing=next((e for e in edges if e['source']==a and e['target']==b and e['type']=='historical_prerequisite'),None)
   if existing:existing['source_refs'].append(record['source_url'])
   else:add(a,b,'historical_followup','2024手册的后续课程字段列出该课；后续关系本身不等于强制先修。',[record['source_url']],confidence='高（历史字段事实）')
  elif token not in ('等',):unmapped.append(dict(course_code=current,course_name=name,requirement_name=token,pdf_page=record['pdf_page'],reason='后续课程名称不在当前清单或不能唯一匹配。',source_url=record['source_url']))

# Consolidate corroborating historical follow-up descriptions into explicit prerequisite edges.
for e in list(edges):
 if e['type']=='historical_followup':
  stronger=next((x for x in edges if x['type']=='historical_prerequisite' and x['source']==e['source'] and x['target']==e['target']),None)
  if stronger:
   stronger['source_refs']=sorted(set(stronger['source_refs']+e['source_refs']));edges.remove(e)
for a,b,reason in PREPARATION:
 if not any(e['source']==a and e['target']==b and e['type'].startswith('historical') for e in edges):add(a,b,'recommended_preparation',reason)
for a,b,reason in CONTENT:
 add(a,b,'content_related',reason,confidence='低' if a in ['AIT531020','GEIN10040'] or '项目未知' in reason else '中')
for code in sorted(nodes):
 if code.endswith('h') and code[:-1] in nodes:
  add(code[:-1],code,'parallel_variant','官方开课名与课号显示普通／H班对应；仅表明同主题班型，不推定互认、替代或相同考核。',confidence='高（名称与课号事实）')
for name,codes in namecodes.items():
 if len(codes)==2 and not any(x.endswith('h') for x in codes):
  a,b=codes
  edges[:]=[e for e in edges if not(e['type']=='content_related' and {e['source'],e['target']}=={a,b})]
  add(a,b,'same_name_distinct_code','官方开课表同名但课号不同，保持独立；不能据名称认定互相替代或先修。',confidence='高（名称与课号事实）')
for i,e in enumerate(edges):
 e['id']=f'E{i+1:03}'
 e['shared_2026_programme_ids']=sorted(set(nodes[e['source']]['programmes'])&set(nodes[e['target']]['programmes']))
 e['note']='共同出现在培养方案中只说明收录范围，不证明先修。' if e['shared_2026_programme_ids'] else '可能跨培养层次或为通识关联；不是选课资格说明。'

# Explicitly audit the available 2026 plan schema rather than treating empty fields as no constraints.
schema=collections.Counter();text_hits=[]
def scan(x,path):
 if isinstance(x,dict):
  if 'defaultPreCourses' in x or 'defaultPreCourseList' in x:
   schema['objects_with_prerequisite_fields']+=1
   if x.get('code') in nodes:schema['target_course_objects_with_prerequisite_fields']+=1
   if x.get('defaultPreCourses') or x.get('defaultPreCourseList'):schema['nonempty_prerequisite_objects']+=1
  for k,v in x.items():scan(v,path+'/'+k)
 elif isinstance(x,list):
  for i,v in enumerate(x):scan(v,path+'/'+str(i))
 elif isinstance(x,str) and re.search('先修|前置|先选|修读顺序|修读本课',x):text_hits.append(path)
for p in (BASE/'raw/official/responses').glob('*.gz'):scan(json.loads(gzip.decompress(p.read_bytes())),p.name)
assert schema['nonempty_prerequisite_objects']==0
historical_semesters={1:['ARCH10001'],3:['ARCH20013','MUSE20001','CULT20002','ARCH20010','ARCH20014','CULT20004'],4:['ARCH30007','MUSE20002','ARCH20009','CULT20005','CULT20006','MUSE20003'],5:['ARCH20008','ARCH30010'],6:['ARCH30008','ARCH30006'],8:['ARCH40004']}
for term,codes in historical_semesters.items():
 for code in codes:nodes[code]['historical_semester_reference']=dict(term=term,version='2024参考安排',source_url=BOOK+'#page=37',note='参考安排，不等于先修，不外推至2026级或研究生。')
degree=collections.Counter(c for e in edges for c in (e['source'],e['target']))
stats=dict(courses=len(nodes),edges=len(edges),edge_types=dict(collections.Counter(e['type'] for e in edges)),groups=len(GROUPS),current_verified_hard_prerequisites=0,historical_handbook_mapped_courses=sum(bool(n['historical_handbook']) for n in nodes.values()),historical_field_records=len(tables),isolated_courses=[c for c in nodes if not degree[c]])
audit=dict(as_of='2026-11-19',base_commit=COMMIT,official_2026_schema=dict(schema),target_plan_rows=len([p for p in plans if p['课程代码'] in nodes]),target_rows_with_nonempty_suggested_term=sum(bool(p['建议学期']) for p in plans if p['课程代码'] in nodes),plan_text_prerequisite_path_matches=text_hits,current_course_outlines_collected=False,conclusion='未取得可用于证明2025秋/2026春当前选课硬条件的依据。空字段不等于无先修。2024手册关系作为历史版本单列。',handbook=dict(title='本科生课程学习手册',department='文物与博物馆学系',year=2024,total_pdf_pages=len(page_texts),url=BOOK,sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),reviewed_scope='读取并核对与本次课程同名的大纲预修/后续字段，以及PDF37—38页修读参考；不宣称355页正文逐字人工读完。',page_number_note='本图所有page均为PDF从1开始的页序；印刷页码通常为PDF页序减5。'))
graph=dict(schema_version=1,title='文物与博物馆学系课程关系图谱',updated_at='2026-11-19',course_scope='2025秋、2026春开课；培养方案与手册分别注明版本',evidence_policy='历史官方要求、编辑建议和内容联系分开。所有边均不作为已核实的当期选课硬规则。',confidence_meaning='置信度针对该类型的陈述；历史字段事实不等于当前制度有效。',statistics=stats,groups=[dict(id=g,name=n) for g,n,_ in GROUPS],relation_types=TYPE_LABELS,nodes=list(nodes.values()),edges=edges,learning_paths=[dict(title=t,course_ids=cs,note=note) for t,cs,note in PATHS])
put(OUT/'graph.json',graph);put(OUT/'source-audit.json',audit);put(OUT/'historical-fields.json',dict(source_url=BOOK,fields=tables,unmapped=unmapped))
if (W/'curation.py').resolve()!=(OUT/'curation.py').resolve():shutil.copy2(W/'curation.py',OUT/'curation.py')
if Path(__file__).resolve()!=(OUT/'build_graph.py').resolve():shutil.copy2(Path(__file__),OUT/'build_graph.py')

def visual_kind(a,b):
 es=[e for e in edges if e['source']==a and e['target']==b and e['directed']]
 if es:return es[0]['type']
 return 'content_related'
sv=['<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1080" viewBox="0 0 1800 1080"><style>text{font-family:Microsoft YaHei,Noto Sans CJK SC,sans-serif}.title{font-size:32px;font-weight:700;fill:#173e48}.sub{font-size:16px;fill:#647985}.name{font-size:16px;fill:#173e48;font-weight:600}.code{font-size:12px;fill:#68818a}</style><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="context-stroke"/></marker></defs><rect width="1800" height="1080" fill="#f5f8f8"/><text class="title" x="46" y="58">文物与博物馆学系 · 课程关系总览</text><text class="sub" x="46" y="91">代表性路径；完整133课与逐边依据请打开 index.html 或 graph.json。历史手册 ≠ 当期选课规定。</text>']
for i,(title,cs,note) in enumerate(PATHS):
 y=146+i*140;sv.append(f'<rect x="28" y="{y-25}" width="1744" height="128" rx="14" fill="white"/><text class="name" x="46" y="{y}">{esc(title)}</text>')
 for j,code in enumerate(cs):
  x=270+j*240;name=nodes[code]['name'];sv.append(f'<rect x="{x}" y="{y-8}" width="200" height="58" rx="10" fill="#edf6f6" stroke="#bdd7d9"/><text class="code" x="{x+12}" y="{y+11}">{esc(code)}</text><text class="name" style="font-size:14px" x="{x+12}" y="{y+35}">{esc(name)}</text>')
  if j:
   kind=visual_kind(cs[j-1],code);color='#0b746f' if kind.startswith('historical') else '#b97630' if kind=='recommended_preparation' else '#7593a2';dash=' stroke-dasharray="7 5"' if kind=='recommended_preparation' else '';arrow=' marker-end="url(#arrow)"' if kind!='content_related' else ''
   sv.append(f'<line x1="{x-40}" y1="{y+21}" x2="{x-5}" y2="{y+21}" stroke="{color}" stroke-width="2.6"{dash}{arrow}/>')
 sv.append(f'<text class="sub" x="270" y="{y+80}">{esc(note)}</text>')
sv.append('<text class="sub" x="46" y="1020">绿色实线：2024手册关系　　橙色虚线：内容推断的建议顺序　　蓝灰无箭头：内容联系</text><text class="sub" x="46" y="1051">“专业论文写作→学年论文→毕业论文”等编辑建议，不作为学籍、选课资格或课程互认依据。</text></svg>')
(OUT/'overview.svg').write_text(''.join(sv),'utf-8',newline='\n')

lines=['# 课程学习路径与关系依据','','图谱范围为133个课程代码。箭头类型须结合标签阅读；“历史预修”来自2024手册，不能直接认定为2025秋／2026春硬性条件。','', '![代表性课程路径](overview.svg)','', '## 2024手册中的具名关系','']
for e in edges:
 if e['type'].startswith('historical'):
  lines.append(f"- **{nodes[e['source']]['name']}（{e['source']}）→{nodes[e['target']]['name']}（{e['target']}）**：{e['label']}。[PDF依据]({e['source_refs'][0]})。{e['reason']}")
lines+=['','## 建议学习路径','']
for title,cs,note in PATHS:
 lines += ['### '+title,'',' → '.join(nodes[c]['name'] for c in cs),'',note,'']
lines+=['## 尚待核实','', '- 当前学年每个教学班的正式先修、修读资格和教师要求。','- 历史“文物学导论”“文物学概论”“中国工艺美术史”等名称与当前课号的官方沿革，未强行映射。','- 同名“文物保护基础”的两个课号，以及普通／H班的课程互认。','- 研究生专题的实际方法门槛：本图仅建立内容联系，不推断跨层次选课资格。','']
(OUT/'learning-paths.md').write_text('\n'.join(lines),'utf-8',newline='\n')
readme=f'''# 文物与博物馆学系课程关系图谱

覆盖2025秋、2026春的 **{stats['courses']}个课程代码、{stats['edges']}条关系、9个主题方向**。课程和教师沿用本分支官方开课资料，普通/H班、同名异号、本科/研究生保持独立。

![代表性课程关系](overview.svg)

- **[交互图谱 index.html](index.html)**：下载后直接打开，离线可用；搜索课程/课号/教师，筛选关系类型，点击课程查看前后关联及逐边出处。默认显示局部邻接图，避免133课全连线造成拥挤。
- [完整机器可读图谱 graph.json](graph.json)：所有课程节点、关系方向、类型、理由、依据链接和学习路径。
- [历史大纲字段及未映射名称](historical-fields.json)、[证据核查与限制](source-audit.json)、[学习路径与具名关系](learning-paths.md)。

## 怎样理解箭头

| 类型 | 含义 |
| --- | --- |
| 2024手册预修要求 | 历史大纲的预修字段明确列课；不证明当前学年执行相同要求 |
| 2024手册建议预修 | 历史大纲明确使用“建议” |
| 2024手册后续课程 | 历史大纲列出后续学习方向；不等同强制先修 |
| 内容推断：建议先学 | 编辑根据课程主题提出的准备顺序，带理由；属于建议 |
| 内容联系 | 无方向；研究对象、方法、时段或实践问题相关 |
| 普通/H、同名异号 | 仅说明名称和课号关系，不说明互认、替代或相同考核 |

本次未获得可证明当期选课硬条件的来源，因此 `current_verified_hard_prerequisites=0` 表示**未核实到硬条件**，并不表示所有课都没有先修要求。2026培养方案中目标课程的建议学期字段为空；不能用实际开课学期推断学习顺序。

## 官方手册依据

[文博系《本科生课程学习手册》2024]({BOOK})，355页。图谱核对了同名本科课程大纲的“预修课程／后续课程”字段，以及PDF第37—38页的修读参考。所有页面定位均按PDF从1起算，不能与印刷页码混用。手册与当前课号的同名对应只是历史内容定位，并非官方代码沿革证明。历史同名多课号、范围外名称、研究生与本科之间不强行继承要求。原文中的“无”和空栏分别保留。

现有7份2026方案和开课数据固定引用到提交 `{COMMIT}`。手册仅存取证URL、SHA-256和必要字段事实，不把355页全文复制进仓库。每条关系可从 `source_refs` 追溯。学生评价未用于生成正式先修约束。

## 更新与复现

`curation.py` 保存编辑建议和内容联系；`build_graph.py` 构建数据、SVG、说明及HTML。构建需要本分支官方JSON、原始方案详情、从上述URL下载的2024手册PDF，以及Python的pypdf库。运行 `python build_graph.py --handbook 手册.pdf`；文字提取缓存写入被忽略的 `.build-cache/`，不提交手册全文。`viewer-template.html`是无外部依赖的交互模板。修改后应核对课号有效、关系方向、建议边无环、来源页码和统计，并更新上层manifest。
'''
(OUT/'README.md').write_text(readme,'utf-8',newline='\n')
template=(W/'viewer-template.html').read_text('utf-8')
if (W/'viewer-template.html').resolve()!=(OUT/'viewer-template.html').resolve():shutil.copy2(W/'viewer-template.html',OUT/'viewer-template.html')
(OUT/'index.html').write_text(template.replace('__GRAPH_DATA__',json.dumps(graph,ensure_ascii=False).replace('</',r'<\/')),'utf-8',newline='\n')
print(json.dumps(stats,ensure_ascii=False,indent=2))
