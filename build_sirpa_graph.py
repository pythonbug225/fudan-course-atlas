import json,re,collections,pathlib,html
R=pathlib.Path('research/contributions/sirpa');B=R/'2026-10-27/official';D=R/'course-graph';D.mkdir(exist_ok=True)
rows=json.loads((B/'sections.json').read_text('utf-8'));sy=json.loads((B/'syllabi.json').read_text('utf-8'));nodes={}
for r in rows:
 n=nodes.setdefault(r['course_code'],{'id':r['course_code'],'name':r['course_name'],'sections':[],'topics':[]});n['sections'].append({k:r[k] for k in ['term','section_code','teachers']})
terms=['政治理论','政治哲学','政治思想','比较政治','国际关系','外交','国际法','公共政策','公共行政','公共管理','社会科学','研究设计','定量','定性','统计','因果','博弈','国家治理','数字治理','人工智能','公共财政','政治经济','社会组织','城市治理','全球治理','国际组织','安全','东亚','欧洲','美国','中国政治']
texts=collections.defaultdict(list);evidence=collections.defaultdict(list);edges=[];explicit=[]
for s in sy:
 if s.get('status')!='parsed':continue
 code=s['course_code']
 for p in s.get('paragraphs',[]):
  if p['title'] not in ['课程简介（中文）','教学内容','教学目标']:continue
  texts[code].append(p['text']);evidence[code].append({'lesson_id':s['lesson_id'],'section_code':s['section_code'],'term':s['term'],'source_url':s['source_url'],'field':p['title']})
  for line in re.split('[。；\\n]',p['text']):
   if re.search('先修|先行修读|修读本课前|前置课程',line):explicit.append({'course_code':code,'statement':line,'source_url':s['source_url'],'section_code':s['section_code']})
for code,n in nodes.items():
 body='\n'.join(texts[code]);n['topics']=[t for t in terms if t in body];n['syllabus_evidence']=evidence[code];n['prerequisite_status']='未确认；不表示无先修要求'
for a,n in nodes.items():
 candidates=[]
 for b,m in nodes.items():
  if a>=b or n['name']==m['name']:continue
  shared=sorted(set(n['topics'])&set(m['topics']))
  if len(shared)>=2:candidates.append((len(shared),b,shared))
 for score,b,shared in sorted(candidates,reverse=True)[:3]:edges.append({'source':a,'target':b,'type':'content_link_inferred','directed':False,'basis':'两门课程官方简介/教学内容共同出现至少两个主题词；自动候选，未经逐对专家审核。','shared_topics':shared,'evidence':{'source':evidence[a],'target':evidence[b]}})
for x in explicit:
 for code,n in nodes.items():
  if code!=x['course_code'] and len(n['name'])>=4 and n['name'] in x['statement']:
   edges.append({'source':code,'target':x['course_code'],'type':'prerequisite_text_candidate','directed':True,'evidence':x,'basis':'正文同时出现先修措辞与课程全名，仍须人工确认是否为肯定要求及同名课号。'})
g={'scope':'国务学院2025秋—2026春619班、306课号；本科及融通171份大纲摘要。','nodes':list(nodes.values()),'edges':edges,'explicit_prerequisite_statements':explicit,'limitations':['未保存的大纲不据课名推断先修关系。','相似主题不意味着先修或可替代；有方向的先修文本候选也需复核。','同名不同代码保留节点；课程计划建议学期不是强制先修依据。']}
(D/'graph.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n','utf-8')
page='''<!doctype html><meta charset="utf-8"><title>国务学院课程关系图谱</title><style>body{font:16px system-ui;margin:28px;color:#18364b}button{margin:5px;padding:8px;cursor:pointer}input{padding:10px;width:450px}svg{background:#f3f7fb;width:100%;height:600px}text{font-size:13px}pre{white-space:pre-wrap}#list{max-height:180px;overflow:auto}</style><h1>国务学院课程关系图谱</h1><p>按课号保留306个节点。连线为大纲主题联系候选，不表示先修要求。点击课程查看邻接关系和原始大纲出处。</p><input id="q" placeholder="搜索课程名、课号、教师"><div id="list"></div><svg viewBox="0 0 1000 600" id="view"></svg><div id="info"></div><script>const data=DATA;const byId=Object.fromEntries(data.nodes.map(n=>[n.id,n]));const esc=s=>String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));function list(){let q=document.querySelector('#q').value.toLowerCase();document.querySelector('#list').innerHTML=data.nodes.filter(n=>JSON.stringify(n).toLowerCase().includes(q)).map(n=>`<button onclick="draw('${n.id}')">${esc(n.name)} ${n.id}</button>`).join('')}function draw(id){let n=byId[id],es=data.edges.filter(e=>e.source===id||e.target===id),ids=[...new Set(es.map(e=>e.source===id?e.target:e.source))],pos={[id]:[500,300]};ids.forEach((v,i)=>pos[v]=[500+360*Math.cos(i*2*Math.PI/ids.length),300+235*Math.sin(i*2*Math.PI/ids.length)]);document.querySelector('#view').innerHTML=es.map(e=>`<line x1="${pos[e.source][0]}" y1="${pos[e.source][1]}" x2="${pos[e.target][0]}" y2="${pos[e.target][1]}" stroke="#80a9bc"/>`).join('')+[id,...ids].map(v=>`<g onclick="draw('${v}')" style="cursor:pointer"><circle cx="${pos[v][0]}" cy="${pos[v][1]}" r="13" fill="${v===id?'#ca702d':'#276d92'}"/><text text-anchor="middle" x="${pos[v][0]}" y="${pos[v][1]+30}">${esc(byId[v].name)}</text></g>`).join('');document.querySelector('#info').innerHTML=`<h2>${esc(n.name)} ${id}</h2><p>先修：${esc(n.prerequisite_status)}</p><p>主题：${esc(n.topics.join('、'))||'缺少可提取大纲'}</p>`+es.map(e=>`<p>${esc(byId[e.source].name)} ↔ ${esc(byId[e.target].name)}：${esc((e.shared_topics||[]).join('、'))}（${esc(e.type)}）</p>`).join('')+'<h3>大纲来源</h3>'+n.syllabus_evidence.map(s=>`<p><a href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.term+' '+s.section_code+' '+s.field)}</a></p>`).join('')}document.querySelector('#q').oninput=list;list();draw(data.nodes.find(n=>n.topics.length)?.id||data.nodes[0].id);</script>'''.replace('DATA',json.dumps(g,ensure_ascii=False).replace('<','\\u003c'))
(D/'index.html').write_text(page,'utf-8')
(D/'README.md').write_text('# 国务学院课程关系图谱\n\n下载并用浏览器打开[index.html](index.html)，可按名称、代码、教师检索，点击课程查看内容联系及大纲来源。[graph.json](graph.json)供后续检索程序读取。\n\n覆盖306个课程节点、'+str(len(edges))+'条关系候选。官方摘要未提供独立先修字段，故不凭推荐学期或课程编号推定先修。正文先修措辞及候选关系另存JSON中供复核。内容连线基于官方中文简介、教学目标、教学内容中的共同主题词自动提取，均属推断，未逐对专家核实；无连线表示证据不足，不表示无关联。\n\n有向候选从被提及的基础课程指向后续课程；正文中的否定、建议措辞及同名多课号仍需核查，不能视为选课硬性要求。\n','utf-8')
assert len(nodes)==306 and all(e['source'] in nodes and e['target'] in nodes and e['source']!=e['target'] for e in edges)
print('nodes',len(nodes),'edges',len(edges),'explicit statements',len(explicit))
