import json, pathlib, re, collections, hashlib

root=pathlib.Path(__file__).resolve().parent.parent
src=root/'final-report-20261028/官方培养方案/官方大纲结构化摘要.json'
classes=json.loads(src.read_text(encoding='utf8'))
names=json.loads((root/'马院课程名单.json').read_text(encoding='utf8'))
plans=json.loads((root/'final-report-20261028/官方培养方案/培养方案课程索引.json').read_text(encoding='utf8'))
themes={
 '马克思主义哲学':['马克思主义哲学','辩证唯物主义','历史唯物主义','辩证法'],
 '政治经济学':['政治经济学','资本论','剩余价值','生产关系'],
 '科学社会主义':['科学社会主义','社会主义理论','社会主义运动'],
 '马克思主义经典著作':['经典著作','马克思恩格斯','马克思、恩格斯','原著选读'],
 '马克思主义发展史':['马克思主义发展史','马克思主义思想史','马克思主义发展'],
 '中国近现代史':['中国近现代史','近现代中国','近代中国','中国近代史'],
 '中国共产党历史':['中国共产党历史','中国共产党史','中共党史','党的历史','党史'],
 '中华人民共和国史':['中华人民共和国史','新中国史','新中国成立'],
 '改革开放史':['改革开放史','改革开放以来','改革开放的历史'],
 '中国特色社会主义':['中国特色社会主义','马克思主义中国化','中国化时代化'],
 '思想政治教育':['思想政治教育','思想政治工作','思想政治理论课'],
 '伦理与道德':['伦理学','伦理问题','道德教育','道德观'],
 '社会研究方法':['社会调查','社会研究方法','实证研究','社会科学研究方法'],
 '人工智能与技术':['人工智能','智能技术','数字技术','数字时代'],
 '科学技术与社会':['科学技术与社会','科技伦理','科学技术哲学','自然辩证法'],
 '世界政治与国际关系':['国际关系','国际政治','世界政治','全球治理'],
 '法律与法治':['法治','法律制度','宪法','法律基础'],
 '生态与环境':['生态文明','环境伦理','生态环境'],
 '文化与意识形态':['意识形态','文化建设','文化理论'],
}
nodes=[]; edges=[]; grouped=collections.defaultdict(list)
for row in classes: grouped[row['course_name'].strip()].append(row)
for n in names:
 rr=grouped[n]; p=[r for r in plans if r['课程名称'].strip()==n and r['开课院系']=='马克思主义学院']
 codes=sorted({r['course_code'] for r in rr}|{r['课程代码'] for r in p})
 nodes.append({'id':'course:'+n,'type':'course','name':n,'course_codes':codes,'classes':len(rr),'readable_syllabi':sum(r['status']=='parsed' for r in rr),'prerequisite_status':'未核实'})
 candidates=[]
 for theme,terms in themes.items():
  best=None
  for row in rr:
   for paragraph in row['paragraphs']:
    if paragraph['title'] not in ('课程简介（中文）','教学目标','教学内容与进度安排'): continue
    text=paragraph.get('text','')
    for term in terms:
     at=text.find(term)
     if at<0: continue
     score=(term in n)*100+len(term)*2+(paragraph['title']=='课程简介（中文）')*4
     match=(score,row,paragraph,term,at)
     if best is None or score>best[0]:best=match
  if best: candidates.append((best[0],theme,best))
 for _,theme,(_,row,paragraph,term,at) in sorted(candidates,key=lambda x:(-x[0],x[1]))[:5]:
  text=paragraph['text']; excerpt=re.sub(r'\s+',' ',text[max(0,at-35):min(len(text),at+len(term)+50)]).strip()
  edges.append({'source':'course:'+n,'target':'topic:'+theme,'type':'内容关联','matched_term':term,'evidence':{'course_code':row['course_code'],'lesson_id':row['lesson_id'],'term':row['term'],'section':paragraph['title'],'excerpt':excerpt,'url':row['source_url'],'snapshot':'../raw-official/syllabi-20261027/'+str(row['lesson_id'])+'.html.gz'}})
nodes += [{'id':'topic:'+t,'type':'topic','name':t} for t in themes]
graph={'schema':'fudan-course-graph/1','scope':'马院课程名单148个名称；2025秋与2026春教学班大纲、2026级方案','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'notes':['先修要求未核实；空白不等于没有先修要求。','内容关联由课程大纲中的主题词构建，是检索线索，不是先修要求。','各课程最多保留五个匹配主题；未关联不表示无内容联系。','同名课程合并为一个节点，课程代码和教学班证据保留。'], 'nodes':nodes,'edges':edges}
out=root/'课程关系图谱';out.mkdir(exist_ok=True)
(out/'课程关系图谱.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
bytheme=collections.defaultdict(list)
for e in edges:bytheme[e['target'][6:]].append(e)
connected={e['source'][7:] for e in edges}
lines=['# 马院课程关系图谱','', '本图谱以[马院课程名单](../马院课程名单.json)中的148个课程名称为节点，依据2025秋、2026春可读官方大纲的课程简介、教学目标和教学内容匹配主题词。关联表示内容涉及同一主题，**不是先修限制**。每门课最多展示5个主题，证据为某一教学班的大纲，不代表所有班型或未来学期。','','现有大纲摘要没有可靠的结构化先修字段，先修状态统一标为“未核实”，不能据此判断没有先修要求。没有可读大纲或未匹配主题的课程保留在 JSON 中。','',f'覆盖：148个课程名称；{len(connected)}个课程匹配到至少一个主题；{len(edges)}条课程—主题关联。', '', '[机器可读图谱](课程关系图谱.json)（包含节点、关联、原文摘录、课号、教学班、学期和来源），[官方大纲摘要](../final-report-20261028/官方培养方案/官方大纲结构化摘要.json)。','','```mermaid','graph LR']
for i,(topic,ee) in enumerate(bytheme.items()):
 lines.append(f'  T{i}["{topic}"]')
 for j,e in enumerate(ee[:2]):
  name=e['source'][7:].replace('"','＂');lines.append(f'  C{i}_{j}["{name}"] --- T{i}')
lines+=['```','','上图为每个主题最多两个示例；下表列出全部匹配结果。链接指向本分支的大纲快照，解压后可查看。','']
for topic in themes:
 ee=bytheme[topic]
 if not ee:continue
 lines+=['## '+topic,'','| 课程 | 匹配词 | 证据来源 |','| --- | --- | --- |']
 for e in ee:
  ev=e['evidence'];lines.append(f"| {e['source'][7:].replace('|','／')} | {e['matched_term']} | [{ev['term']} · {ev['lesson_id']}]({ev['snapshot']}) |")
 lines.append('')
missing=[n for n in names if n not in connected]
lines+=['## 暂无主题匹配的课程','', '这些课程可能缺少可读大纲，也可能仅因本次主题词未覆盖其内容；应继续核对，不应理解为孤立或没有先修要求。','', '、'.join(missing),'']
(out/'README.md').write_text('\n'.join(lines),encoding='utf8')
assert len(nodes)==148+len(themes) and len(names)==148
assert all(e['evidence']['matched_term'] in e['evidence']['excerpt'] if 'matched_term' in e['evidence'] else e['matched_term'] in e['evidence']['excerpt'] for e in edges)
assert all((out/e['evidence']['snapshot']).is_file() for e in edges)
print(json.dumps({'courses':len(names),'connected':len(connected),'edges':len(edges),'unmatched':len(missing),'topics_used':len(bytheme)},ensure_ascii=False))
