"""Build per-cohort plan inventories and sourced course graphs, offline."""
import collections,csv,gzip,hashlib,html,importlib.util,itertools,json,re,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;O=W if (W/'2023/official').exists() else W/'package/cohorts'
CURATION=json.loads((W/'curation.json').read_text('utf-8'))
HANDBOOK=json.loads((O/'sources/handbook-course-requirements.json').read_text('utf-8'))
group_titles={'analysis':'分析与方程','algebra':'代数与数论','geometry':'几何与拓扑','probability':'概率统计与金融','computation':'计算与优化','ai':'计算机与人工智能','physics':'物理与力学','practice':'论文与研究实践','foundation':'其他基础与跨学科','public_options':'公共候选目录','curriculum':'方案模块'}

def load(p):
 if p.exists():return json.loads(p.read_text('utf-8-sig'))
 return json.loads(gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def esc(s):return html.escape(str(s or ''))
def sourceurl(pid):return 'https://fdjwgl.fudan.edu.cn/manager/bizType/2/major-program-search/info/'+str(pid)+'?skipAuth=1'
def module_name(m):return m.get('nameZh') or (m.get('type') or {}).get('nameZh') or '未命名模块'
def norm(name):
 import unicodedata
 return re.sub(r'\s+','',unicodedata.normalize('NFKC',name)).upper()
def writecsv(p,rows,fields):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fields,extrasaction='ignore');writer.writeheader()
  for row in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items() if k in fields})
def classify(name):
 for pattern,g in [('论文|实习|专题讨论|独立学习|科研实践|学术前沿','practice'),('概率|随机|统计|金融|精算|寿险|利息|时间序列|布朗|马氏','probability'),('代数|数论|模形式|算术|表示论|同调代数|Schur','algebra'),('几何|拓扑|流形|黎曼|Current|示性类','geometry'),('数值|逼近|优化|规划|运筹|控制|对策|博弈|计算方法|科学计算|有限元|反问题','computation'),('程序|数据结构|算法|机器学习|深度学习|人工智能|计算机|神经网络|模式识别','ai'),('物理|力学|量子|相对论','physics'),('分析|函数|方程|测度|积分|调和|Fourier|算子|遍历|复变|谱理|复分析','analysis')]:
  if re.search(pattern,name):return g
 return 'foundation'

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
    nums=[int(t.split('_')[1]) for t in pc.get('terms',[]) if re.fullmatch(r'TERM_([1-9]|1[0-9]|2[0-4])',str(t))];suggest=[int(t.split('_')[1]) for t in pc.get('suggestTerms',[]) if re.fullmatch(r'TERM_([1-9]|1[0-9]|2[0-4])',str(t))]
    row={'cohort':year,'plan_id':pid,'plan_title':meta['title'],'student_type':student,'cultivation_type':cult,'course_code':code,'course_name':name,'credits':c.get('credits'),'department':(pc.get('openDepartment') or c.get('department') or {}).get('nameZh'),'module_id':mid,'module_path':path,'scope':module['scope'],'compulsory_field':pc.get('compulsory'),'required_course_field':pc.get('requiredCourse'),'terms_raw':pc.get('terms',[]),'numbered_terms':nums,'suggest_terms_raw':pc.get('suggestTerms',[]),'numbered_suggest_terms':suggest,'remark':pc.get('remark'),'source':sid,'locator':f'/courseModules/{mi}/planCourses/{ci}'};rows.append(row)
    n=courses.setdefault(code,{'id':code,'name':name,'name_variants':[],'node_type':'research_activity' if not re.search('[A-Za-z]',code) else 'course','scope':'public_options','group':'public_options','programmes':[],'business_types':['本科及本研融通方案收录；具体阶段见方案'],'teachers':[],'offerings':[],'plan_placements':[],'memberships':[],'prerequisite_status':'not_verified','cohort':year})
    if name not in n['name_variants']:n['name_variants'].append(name)
    if is_programme:n['scope']='programme';n['group']=classify(name)
    if pid not in n['programmes']:n['programmes'].append(pid)
    n['memberships'].append({'module_id':mid,'source':sid,'locator':row['locator'],'scope':module['scope']})
    n['plan_placements'].append({'plan_id':pid,'source':sid,'locator':row['locator'],'module_id':mid,'numbered_terms':nums,'numbered_suggest_terms':suggest,'terms_raw':row['terms_raw'],'student_type':student,'term_source':'api_terms','course_name':name,'scope':module['scope']})
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
  # Preserve any source mentions for review; never turn them into hard gates automatically.
  audit.append({'plan_id':pid,'cohort':year,'prerequisite_fields_found':prefields,'explicit_prerequisite_texts':hits,'word_prerequisite_mentions':words,'unexpanded_referenced_modules':[{'locator':f'/courseModules/{i}','name':module_name(m)} for i,m in enumerate(ms) if m.get('reference') and not m.get('planCourses')],'hard_prerequisites_verified':0,'nonempty_prerequisite_fields':nonempty,'conclusion':'本方案字段与正文的先修相关命中按原文保留；是否构成选课硬门槛需逐条核对。另用2024版手册补充知识准备参考，未展开公共模块不跨年补齐。'})
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
 edges=[];seen={};skipped=[]
 all_node_lookup={**courses,**{n['id']:n for n in module_nodes}}
 sources['HANDBOOK-2024']={'title':'数学科学学院本科生学习指导手册（2024版）','url':'../../sources/math-handbook-2024.pdf','official_url':HANDBOOK['source_url'],'edition':2024,'applicability':'2024版历史大纲与选课指导；当前课号按题名参考，跨年级规则未确认'}
 relation_types={'planned_before':'本方案学期在先（非先修）','historical_preparation':'2024手册知识准备（题名参考）','recommended_preparation':'建议先学（编辑判断）','content_related':'内容联系（编辑判断）','same_name_distinct_code':'同名异号（不代表互认）','module_membership':'方案模块收录（非先修）'}
 def add(a,b,kind,reason,ev):
  if a==b:return
  directed=kind in ['planned_before','recommended_preparation','historical_preparation']
  if not directed and a>b:a,b=b,a
  key=(a,b,kind)
  if key in seen:
   e=seen[key]
   for r in ev:
    if r not in e['evidence']:e['evidence'].append(r)
   e['shared_plan_ids']=sorted(set(e['shared_plan_ids'])|{r['plan_id'] for r in ev if r.get('plan_id')})
   if reason not in e['reason']:e['reason']+=' '+reason
   return
  common=set(all_node_lookup[a]['programmes'])&set(all_node_lookup[b]['programmes'])
  shared=sorted({r['plan_id'] for r in ev if r.get('plan_id')} or common)
  if not shared:return
  e={'id':f'{year}-E{len(edges)+1:05}','source':a,'target':b,'type':kind,'directed':directed,'mandatory':False,'credit_equivalence':False,'shared_plan_ids':shared,'reason':reason,'evidence':ev,'confidence':'官方方案字段事实；不代表先修' if kind in ['planned_before','module_membership'] else '2024版手册原文与当前方案题名对照；课号沿革和当前门槛待核' if kind=='historical_preparation' else '编辑判断；具体大纲待核'}
  seen[key]=e;edges.append(e)
 nameindex=collections.defaultdict(set);planindex=collections.defaultdict(lambda:collections.defaultdict(set))
 for n in courses.values():
  if n['scope']!='programme':continue
  for name in n['name_variants']:nameindex[norm(name)].add(n['id'])
  for row in n['plan_placements']:
   if row['scope']=='programme':
    planindex[row['plan_id']][norm(row['course_name'])].add(n['id'])
 def unique(name,pid=None):
  ids=(planindex[pid] if pid else nameindex).get(norm(name),set())
  return next(iter(ids)) if len(ids)==1 else None
 def refs(a,b,pid):
  return [{'source':p['source'],'locator':p['locator'],'course':c,'plan_id':pid,'terms':p['numbered_terms']} for c in [a,b] for p in courses[c]['plan_placements'] if p['plan_id']==pid]
 def pair(an,bn,kind,reason,extra=None):
  found=False
  for pid in planindex:
   a,b=unique(an,pid),unique(bn,pid)
   if not a or not b:continue
   found=True;ev=refs(a,b,pid)+(extra or []);add(a,b,kind,reason,ev)
   if kind=='recommended_preparation':
    left=[t for p in courses[a]['plan_placements'] if p['plan_id']==pid for t in p['numbered_terms']];right=[t for p in courses[b]['plan_placements'] if p['plan_id']==pid for t in p['numbered_terms']]
    if left and right and max(left)<min(right):add(a,b,'planned_before','同一方案的terms数字学期前者全部早于后者；不将学期差认定为先修。',refs(a,b,pid))
  if not found:skipped.append({'from':an,'to':bn,'type':kind,'reason':'无具体方案同时收录两个唯一题名；未跨方案、跨年补齐或猜测课号。'})
 for a,b,reason in CURATION['preparation']:pair(a,b,'recommended_preparation',reason)
 for a,b,reason in CURATION['content']:pair(a,b,'content_related',reason)
 # Explicit and advice relationships remain historical, even for the 2024 current snapshot.
 for rule in HANDBOOK['curated_preparation']:
  pair(rule['from'],rule['to'],'historical_preparation',rule['interpretation']+' 依据2024版手册，当前课号仅按题名对照，不能据此推定等价或本年级强制门槛。',[{'source':'HANDBOOK-2024','locator':'PDF p.'+','.join(map(str,rule['pdf_pages'])),'pdf_pages':rule['pdf_pages'],'original_wording':rule['wording'],'handbook_target_code':rule.get('target_code'),'mapping':'题名内容对照；非课号替代证明'}])
 for rule in HANDBOOK['guidance_edges']:
  pair(rule['from'],rule['to'],'historical_preparation','2024版手册选课指导将两课联系为知识准备，属于指导建议；当前方案只作题名参考。',[{'source':'HANDBOOK-2024','locator':'PDF p.'+','.join(map(str,rule['pdf_pages'])),'pdf_pages':rule['pdf_pages'],'original_kind':rule['kind'],'mapping':'题名参考，跨年级规则待核'}])
 for n in courses.values():
  for m in n['memberships']:add(n['id'],m['module_id'],'module_membership','原方案在此模块列出该代码，只表达收录范围；模块可含限选规则，不能理解为每门均须修读。',[{'source':m['source'],'locator':m['locator']}])
 for title,ids in nameindex.items():
  for a,b in itertools.combinations(sorted(ids),2):
   common=set(courses[a]['programmes'])&set(courses[b]['programmes'])
   if common:add(a,b,'same_name_distinct_code','同一方案中同名异号分别保留，不确认等价、替代或沿革。',refs(a,b,sorted(common)[0]))
 paths=[];pathkeys=set()
 def related(a,b,pid):return any(((e['source']==a and e['target']==b) or (not e['directed'] and {e['source'],e['target']}=={a,b})) and pid in e['shared_plan_ids'] for e in edges if e['type']!='module_membership')
 for titles in CURATION['paths']:
  for pid in planindex:
   segment=[]
   def save():
    if len(segment)>1:
     key=tuple(segment)
     if key not in pathkeys:
      pathkeys.add(key);paths.append({'title':titles[0],'course_ids':segment.copy(),'plan_id':pid,'note':'按方案'+pid+'定位；逐边区分编辑建议、2024手册参考与本方案学期，不代表必修或学分互认。'})
   for title in titles[1:]:
    c=unique(title,pid)
    if not c:save();segment=[];continue
    if segment and not related(segment[-1],c,pid):save();segment=[]
    segment.append(c)
   save()
 core_count=sum(n['scope']=='programme' for n in courses.values());statistics={'course_entries':len(courses),'course_nodes':sum(n['node_type']=='course' for n in courses.values()),'activity_nodes':sum(n['node_type']!='course' for n in courses.values()),'programme_entries':core_count,'public_option_entries':len(courses)-core_count,'module_nodes':len(module_nodes),'edges':len(edges),'edge_types':dict(collections.Counter(e['type'] for e in edges)),'verified_hard_prerequisites':0,'historical_preparation_edges':sum(e['type']=='historical_preparation' for e in edges),'plans':len(plans)}
 graph={'schema_version':'fudan-course-graph/cohort-1','title':f'数学科学学院{year}级培养方案课程关系图谱','updated_at':'2026-11-26','cohort':year,'relation_types':relation_types,'groups':[{'id':g,'name':name} for g,name in group_titles.items()],'sources':sources,'programmes':[{'id':p['plan_id'],'name':p['title'],'student_type':p['student_type'],'cultivation_type':p['cultivation_type']} for p in plans],'statistics':statistics,'nodes':list(courses.values())+module_nodes,'edges':edges,'learning_paths':paths,'evidence_policy':'年度内按本方案字段核对；不合并跨年课号，不把学期在先/模块收录/编辑建议变成强制先修。'}
 put(out/'graph.json',graph);put(out/'source-audit.json',{'date':'2026-11-26','cohort':year,'plans':audit,'skipped_cross_year_recipes':skipped,'source_scope':'本年级官方方案2026-11-26公开快照，另附2024版手册；未核实2023/2025专属手册或逐教学班先修门槛。','handbook_pdf_sha256':HANDBOOK['sha256'],'rule':'公共候选目录不等于全部必修；模块收录边单列；空先修字段不证明没有先修。'})
 writecsv(out/'nodes.csv',list(courses.values())+module_nodes,['id','name','node_type','scope','group','programmes','plan_placements','memberships'])
 writecsv(out/'edges.csv',edges,['id','source','target','type','directed','mandatory','reason','evidence'])
 simple=[e for e in edges if e['type']!='module_membership'];lines=[f'# 数学科学学院{year}级课程关系与先修梳理','','以下区分本年级数字学期、2024版手册的预修/基础参考与编辑建议；尚未确认本年级选课系统强制门槛。模块候选收录另见graph.json，不当作先修。','','![专业课程学习路径](overview.svg)','','## 逐条课程关系','','| 起点 | 终点 | 类型 | 理由 | 依据 |','| --- | --- | --- | --- | --- |']
 for e in simple:
  bookrefs=[r for r in e['evidence'] if r['source']=='HANDBOOK-2024'];pids=e['shared_plan_ids'];links=[]
  for r in bookrefs:
   for page in r['pdf_pages']:
    link=f'[手册PDF第{page}页](../../sources/math-handbook-2024.pdf#page={page})'
    if link not in links:links.append(link)
  for pid in pids[:2]:links.append(f'[方案{pid}]({sourceurl(pid)})')
  if len(pids)>2:links.append(f'等{len(pids)}个方案，完整范围见JSON')
  lines.append('| '+courses[e['source']]['name']+' '+e['source']+' | '+courses[e['target']]['name']+' '+e['target']+' | '+relation_types[e['type']]+' | '+e['reason']+' | '+'；'.join(links)+' |')
 (out/'learning-paths.md').write_bytes(('\n'.join(lines)+'\n').encode('utf-8'))
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1660" height="{max(500,150+len(paths[:9])*125)}"><style>text{{font-family:Microsoft YaHei,system-ui,sans-serif}}.t{{font-size:28px;font-weight:bold;fill:#1e4d60}}.n{{font-size:15px;fill:#234b5d}}.s{{font-size:12px;fill:#5b7685}}</style><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="context-stroke"/></marker></defs><rect width="100%" height="100%" fill="#f1f6f8"/><text x="30" y="45" class="t">数学科学学院 {year}级 · 课程关系与学习路径</text><text x="30" y="78" class="s">绿：方案学期　紫：2024手册知识准备参考　橙虚线：编辑建议　蓝灰：内容联系；非强制门槛</text>']
 for i,path in enumerate(paths[:9]):
  y=115+i*125;svg.append(f'<rect x="20" y="{y-12}" width="1620" height="113" rx="12" fill="white"/><text x="34" y="{y+23}" class="n">{esc(path["title"])}</text>')
  for j,code in enumerate(path['course_ids'][:5]):
   x=235+j*275;name=courses[code]['name'];svg.append(f'<rect x="{x}" y="{y}" width="245" height="62" rx="8" fill="#eaf3f6" stroke="#bdd1da"/><text x="{x+10}" y="{y+19}" class="s">{esc(code)}</text><text x="{x+10}" y="{y+39}" class="n">{esc(name[:14])}</text><text x="{x+10}" y="{y+56}" class="s">{esc(name[14:])}</text>')
   if j:
    previous=path['course_ids'][j-1];es=[e for e in simple if (e['source']==previous and e['target']==code) or (not e['directed'] and {e['source'],e['target']}=={previous,code})]
    if es:
     e=es[0];col='#167e78' if e['type']=='planned_before' else '#74549e' if e['type']=='historical_preparation' else '#b47427' if e['type']=='recommended_preparation' else '#7893a5';dash=' stroke-dasharray="6 4"' if e['type']=='recommended_preparation' else '';arrow=' marker-end="url(#a)"' if e['directed'] else '';svg.append(f'<line x1="{x-30}" x2="{x-5}" y1="{y+31}" y2="{y+31}" stroke="{col}" stroke-width="2"{dash}{arrow}/>')
  svg.append(f'<text x="235" y="{y+87}" class="s">{esc(path["note"])}</text>')
 svg.append('</svg>');(out/'overview.svg').write_bytes(''.join(svg).encode('utf-8'))
 template=(W/'viewer-template.html').read_text('utf-8');(out/'index.html').write_bytes(template.replace('__GRAPH_DATA__',json.dumps(graph,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')).encode('utf-8'))
 readme=f'''# 数学科学学院{year}级培养方案与课程关系

本年级共取得 **{len(plans)}份方案原件**，去重 **{len(courses)}个课程/科研条目**，其中 **{core_count}个方案内课程与科研条目（含明列通识）**，另 **{len(courses)-core_count}个仅见于公共候选目录**。图谱另设{len(module_nodes)}个方案模块节点；不能把全目录数量读作个人必修课数。

- [交互图谱](course-graph/index.html)：下载后打开，默认显示方案内课程与科研条目，可按方案、主题和公共目录范围筛选。
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

本年级方案正文、Word文本及先修字段已检索，相关命中见来源核查；**尚未确认本年级选课系统执行的课程对课程强制门槛**。另附2024版学习手册68份完整大纲的基本要求摘录与逐页定位。紫色关系为手册中的预修/基础或选课指导，当前课号按题名参考，不能将2024版条款直接视为2023/2025级或新课号规则。绿色为同一方案数字学期安排，橙色为编辑建议，蓝灰为内容联系；模块收录只表示候选范围。

按本年级具体方案内的唯一题名建立关系；同名异号、普通/H、英才/强基/相辉和本硕博贯通版本分别保留。原课号完整保留，未将历史MATH课号自动替代为新号，不推断学分互认。本硕博贯通方案可能列入研究生课程，收录不代表本科阶段全部必修。春、秋只表示季节，不参与数字学期先后推导。手册预修中未能唯一定位为具体课程的宽泛知识基础保留在原文摘录，不强行展开成若干必修课程。

原始接口与官方Word均存于official/；目录记录和方案详情为2026-11-26取得的本年级当前公开快照，系统可能后续修订，不能称为入学当年的原始发布版。JSON经格式规范化并gzip压缩，Word保持下载字节不变；哈希见总清单。原件权利归原权利人，未取得单独的再利用许可声明。
'''
 readme=readme.replace('## 官方方案原件','![专业课程关系总览](course-graph/overview.svg)\n\n## 官方方案原件',1)
 (root/'README.md').write_bytes(readme.encode('utf-8'))
 (out/'README.md').write_bytes((f'# 数学科学学院{year}级课程关系图谱\n\n![学习路径总览](overview.svg)\n\n[交互HTML](index.html)（下载后打开） · [课程关系与先修梳理](learning-paths.md) · [图谱JSON](graph.json) · [节点CSV](nodes.csv) · [关系CSV](edges.csv) · [原件与适用方案](../README.md)\n\n关系区分本年级方案学期、2024版手册知识准备参考、编辑建议和内容联系；尚未确认本年级强制选课门槛。图谱含{len(courses)}个课程/科研条目，其中{core_count}个为方案内课程与科研条目、{len(courses)-core_count}个仅公共候选；另有{len(module_nodes)}个模块节点。模块收录不代表全部必修，详情与原始定位见[source-audit.json](source-audit.json)。\n').encode('utf-8'))
 return {'cohort':year,**statistics,'programme_ids':[p['plan_id'] for p in plans]}

if __name__=='__main__':
 summaries=[build(y) for y in [2023,2024,2025]];put(O/'coverage.json',summaries)
 for s in summaries:print(json.dumps(s,ensure_ascii=False))
