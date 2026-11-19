import csv,json,re,unicodedata,pathlib,collections,base64,gzip,html
P=pathlib.Path(__file__).parent.parent/'data';O=pathlib.Path(__file__).parent;O.mkdir(exist_ok=True)
def readcsv(n):
 with (P/n).open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
rows=readcsv('program-course-index.csv');classes=json.loads((P/'official-classes.json').read_text('utf-8-sig'));nodes={};modules={};edges={}
program_codes={r['课程代码'].strip()for r in rows if r['课程代码'].strip()};class_codes={r['课程代码']for r in classes if r.get('课程代码')}
module_frequency=collections.Counter((r['方案编号'],r['模块'])for r in readcsv('program-module-requirements.csv'))
BASE='https://github.com/pythonbug225/fudan-course-atlas/blob/foreign-languages-2026-plans-2025fall-2026spring-reviews/research/contributions/foreign-languages-20261028/'
for r in rows:
 code=r['课程代码'].strip();name=r['课程名称'].strip()
 if not code or not name:continue
 n=nodes.setdefault(code,{'id':code,'name':name,'kind':'course','names':[],'departments':[],'programs':[],'terms':[],'class_levels':[]})
 if name not in n['names']:n['names'].append(name)
 if r['开课院系']and r['开课院系']not in n['departments']:n['departments'].append(r['开课院系'])
 if r['方案名称']and r['方案名称']not in n['programs']:n['programs'].append(r['方案名称'])
 group=(r['方案编号'],r['方案名称'],r['模块'])
 if all(group):modules.setdefault(group,set()).add(code)
for r in classes:
 code=r.get('课程代码');name=r.get('课程名称')
 if not code or not name:continue
 n=nodes.setdefault(code,{'id':code,'name':name,'kind':'course','names':[],'departments':[],'programs':[],'terms':[],'class_levels':[]})
 if name not in n['names']:n['names'].append(name)
 for k,f in [('departments','开课院系'),('terms','学期'),('class_levels','课程层次')]:
  if r.get(f)and r[f]not in n[k]:n[k].append(r[f])
def add(a,b,t,label,reason,source):
 if a==b:return
 key=(a,b,t,label)
 if key not in edges:edges[key]={'source':a,'target':b,'type':t,'label':label,'basis':reason,'source_url':source}
csvurl=BASE+'data/program-course-index.csv';classurl=BASE+'data/official-classes.json'
# A course-module connection states only co-membership in one official program.
for (pid,plan,module),codes in sorted(modules.items()):
 if len(codes)<2 or module_frequency[(pid,module)]!=1:continue
 mid='module:'+pid+':'+module
 nodes[mid]={'id':mid,'name':module,'kind':'module','program':plan,'program_id':pid,'course_count':len(codes)}
 for code in sorted(codes):add(code,mid,'program_module','同一培养方案模块',f'{plan}：{module}；同属模块不表示课程先修。',csvurl)
# Recognize explicit I/II/III/IV and 上/下 suffixes from titles, as suggestions only.
families=collections.defaultdict(list)
def series(name):
 s=unicodedata.normalize('NFKC',name).replace(' ','').replace('（','(').replace('）',')')
 part=0;m=re.search(r'\(?([上下])\)?$',s)
 if m:part=1 if m.group(1)=='上'else 2;s=s[:m.start()]
 level=0;m=re.search(r'\(?(IV|III|II|I|[1-4])\)?$',s)
 if m:level={'I':1,'II':2,'III':3,'IV':4,'1':1,'2':2,'3':3,'4':4}[m.group(1)];s=s[:m.start()]
 if not part and not level:return None
 if not re.search(r'[\u4e00-\u9fff]',s)or len(s)<3:return None
 return s.rstrip('()'),(level,part)
for code,n in list(nodes.items()):
 if n['kind']!='course':continue
 for name in n['names']:
  v=series(name)
  if v:families[v[0]].append((v[1],code,name))
for family,items in families.items():
 by=collections.defaultdict(dict)
 for order,code,name in items:by[order][code]=name
 orders=sorted(by)
 for a,b in zip(orders,orders[1:]):
  # Missing intermediate numbered levels make the inferred ordering too weak.
  if a[0]and b[0]and b[0]-a[0]>1:continue
  for ca,na in by[a].items():
   for cb,nb in by[b].items():
    if ca==cb or re.match(r'^[A-Z]+',ca).group()!=re.match(r'^[A-Z]+',cb).group():continue
    if nodes[ca]['class_levels'] and nodes[cb]['class_levels'] and set(nodes[ca]['class_levels']).isdisjoint(nodes[cb]['class_levels']):continue
    if (len(by[a])>1 or len(by[b])>1) and not (set(nodes[ca]['programs'])&set(nodes[cb]['programs'])):continue
    if ca in program_codes and cb in program_codes:source=csvurl
    elif ca in class_codes and cb in class_codes:source=classurl
    else:continue
    add(ca,cb,'suggested_sequence','名称显示的建议顺序',f'课程名称“{na}”与“{nb}”具有同一系列及编号/上下标记；仅提示建议顺序，未证明是正式先修要求。',source)
# Title keyword connections describe topical proximity, not verified syllabi.
topics={'英语':['英语','英美','英国','美国','莎士比亚'],'日语':['日语','日本'],'德语':['德语','德国','德奥','日耳曼'],'法语':['法语','法国'],'俄语':['俄语','俄罗斯'],'韩语与韩国语':['韩语','韩国语','韩国','朝鲜'],'西班牙语':['西班牙语','西班牙','拉丁美洲'],'语言学':['语言学','语音','语法','词汇','语义','句法','语料库'],'翻译':['翻译','笔译','口译','英译','对译','译后'],'文学与文本':['文学','小说','诗歌','戏剧','叙事','文本'],'跨文化与区域研究':['跨文化','文化史','国别','区域研究','文化交流'],'表达与写作':['写作','演讲','辩论','会话','修辞'],'数字技术':['人工智能','编程','计算机','数字','机器学习','语料库']}
for label,terms in topics.items():
 members=[code for code,n in nodes.items()if n['kind']=='course'and any(w in ' '.join(n['names'])for w in terms)]
 if len(members)<2:continue
 tid='topic:'+label;nodes[tid]={'id':tid,'kind':'topic','name':label,'course_count':len(members)}
 for code in members:add(code,tid,'topic','名称关键词主题关联',f'课程名称匹配“{label}”主题的关键词；仅为内容线索，不等于已核验大纲。',csvurl if code in program_codes else classurl)
result={'schema':'fudan-course-atlas.graph.v1','department':'外国语言文学学院','scope':'2026级25份培养方案所列课程（含其他院系开课的双学位课程）与2025秋、2026春外院开课课程的并集；未声称全历史全课程。','source_revision':'ed6ceda6599e447721b720ced00542cc6ac88108','official_prerequisite_status':'已检查25份培养方案JSON，defaultPreCourses和defaultPreCourseList均为空；全文未发现“先修”或“前置课程”文字，未发现可验证的正式先修边。','cautions':['建议顺序依据课程名编号/上下推断，须以课程大纲、教务系统及具体方案为准。','模块关联是同一培养方案中的归类；主题关联是课程名关键词线索，均不等于先修要求。','同名不同课号保留为独立节点；课程名变体保留。'],'nodes':list(nodes.values()),'edges':list(edges.values())}
(O/'graph.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8',newline='\n')
with (O/'nodes.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['节点ID','名称','类型','开课院系','学期','培养方案']);
 for n in nodes.values():w.writerow([n['id'],n['name'],n['kind'],'、'.join(n.get('departments',[])),'、'.join(n.get('terms',[])),'、'.join(n.get('programs',[]))or n.get('program','')])
with (O/'edges.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.DictWriter(f,fieldnames=['source','target','type','label','basis','source_url'],lineterminator='\n');w.writeheader();w.writerows(edges.values())
assert len({n['id']for n in result['nodes']})==len(nodes) and all(e['source']in nodes and e['target']in nodes for e in edges.values())
print(json.dumps({'nodes':len(nodes),'courses':sum(n['kind']=='course'for n in nodes.values()),'modules':sum(n['kind']=='module'for n in nodes.values()),'topics':sum(n['kind']=='topic'for n in nodes.values()),'edges':len(edges),'edge_types':dict(collections.Counter(e['type']for e in edges.values()))},ensure_ascii=True))
