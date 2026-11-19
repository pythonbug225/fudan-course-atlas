"""Build the History graph offline from the pinned department research snapshot."""
from pathlib import Path
import collections
import csv
import hashlib
import html
import json
import re
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OFF = HERE.parent/'2026-10-30/report/history-research/official'
GROUPS = [
    ('foundation','史学入门与通史','#987243'),('ancient_china','中国古代史','#aa6751'),
    ('modern_china','中国近现代史','#aa5874'),('ancient_world','古代中古世界','#658554'),
    ('modern_world','近现代世界与全球史','#3d7c9a'),('asia','亚洲与中外交流','#765d98'),
    ('sources','史料、文献与方法','#557c73'),('society','社会、经济与环境','#7a843c'),
    ('culture','思想、文化与宗教','#a47734'),('language','语言与原典工具','#8b6388'),
    ('digital','数字与人工智能史学','#4b7ca1'),('general','通识及待核专题','#85817a')]

def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n','utf-8',newline='\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def group(name,code):
    if code in {'AIT631013','HIST40001'}:return 'digital'
    if code.startswith('GESP') or name=='认识地球':return 'general'
    if re.search('拉丁语|古希腊语|古希腊文|叙利亚语|梵文|葡萄牙语|专业外语|专业英语|专业日语|法语历史',name):return 'language'
    if re.search('史学入门|史学原典|史学导论|世界文明史通论|中国古代史（|中国近现代史（|15世纪以前|20世纪的世界|^世界近代史$',name):return 'foundation'
    if re.search('人工智能|智能体',name):return 'digital'
    if re.search('性别|妇女|医学|医疗|身体|社会史|社会经济|经济史|财政|金融|货币|企业|环境|地理|城市',name):return 'society'
    if re.search('宗教|佛|基督|思想|思潮|经学|文化史|传统文化|十三经|遗产|篆刻|艺术|考古',name):return 'culture'
    if re.search('古希腊|希腊悲剧|古希腊文学|罗马|拜占庭|中世纪|古代西亚|埃及|上古中古|古典|古代晚期|近东',name):return 'ancient_world'
    if re.search('日本|韩国|东亚|亚洲|北方民族|蒙古|契丹|中外|中西|西方人在中国|欧美汉学|海外|西方中国|周边国家|丝绸之路|边疆|留学生',name):return 'asia'
    if re.search('秦汉|先秦|魏晋|南北朝|隋唐|汉唐|宋|明清|明史|清代|蒙元|古代|中古|江南',name):return 'ancient_china'
    if re.search('中国近|中国现代|近代中国|当代中国|共和国|中国革命|20世纪的中国|晚清|毛泽东|中国与德国',name):return 'modern_china'
    if re.search('欧洲|西欧|美国|英国|法国|俄罗斯|非洲|冷战|大西洋|全球|世界|帝国|文艺复兴',name):return 'modern_world'
    return 'sources'

def output_csv(name,rows):
    with (HERE/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def build():
    catalog=read(OFF/'历史学课程清单.json');sections=read(OFF/'历史学课程教学班.json')
    plan_rows=read(OFF/'培养方案课程索引.json');plans=read(OFF/'方案下载清单.json');rules=read(HERE/'rules.json')
    inputs=[OFF/'历史学课程清单.json',OFF/'历史学课程教学班.json',OFF/'培养方案课程索引.json',OFF/'方案下载清单.json',HERE/'rules.json']
    sources=[dict(id='official-catalog',path='../2026-10-30/report/history-research/official/历史学课程清单.json',description='两学期官方开课清单：270条记录、249个课号、247个名称。'),
             dict(id='plan-index',path='../2026-10-30/report/history-research/official/培养方案课程索引.json',description='4份2026级本科培养方案列课索引。'),
             dict(id='editorial-rules',path='rules.json',description='编辑关系规则：题名及知识结构判断，待大纲或教师复核。')]
    memberships=collections.defaultdict(list);terms=collections.defaultdict(lambda:collections.defaultdict(list));audit=[]
    for row in plan_rows:
        member=dict(program_id=row['方案编号'],program_name=row['方案名称'],module=row['模块'],compulsory_in_this_module=row['必修字段'],reported_terms=row['开设季节'],suggested_terms=row['建议学期'])
        if member not in memberships[row['课程代码']]:memberships[row['课程代码']].append(member)
    for plan in plans:
        pid=str(plan['方案编号']);p=OFF/'原始接口'/f'{pid}.json';obj=read(p);inputs.append(p)
        sources.append(dict(id='plan-'+pid,path='../2026-10-30/report/history-research/official/原始接口/'+p.name,url=plan['详情来源'],description=plan['方案名称'],snapshot_date='2026-10-28',sha256=sha(p)))
        fields=[];text_hits=[]
        def scan(x,pointer=''):
            if isinstance(x,dict):
                for k,v in x.items():
                    where=pointer+'/'+str(k)
                    if re.search(r'defaultPre|pre.?req|preCourse|先修',k,re.I):fields.append(dict(pointer=where,value=v))
                    scan(v,where)
            elif isinstance(x,list):
                for i,v in enumerate(x):scan(v,pointer+'/'+str(i))
            elif isinstance(x,str) and re.search('先修|先行课程|前修课程|修读顺序|后续课程',x):text_hits.append(dict(pointer=pointer,text=re.sub('<[^>]+>','',x)))
        scan(obj)
        doc=OFF/'方案原件'/plan['Word原件'];inputs.append(doc)
        with zipfile.ZipFile(doc) as z:
            assert z.testzip() is None
            xml=ET.fromstring(z.read('word/document.xml'))
            text='\n'.join(''.join(t.text or '' for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')) for p in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
        word_hits=[text[max(0,m.start()-60):m.end()+100] for m in re.finditer('先修|先行课程|前修课程|修读顺序|后续课程',text)]
        assert not any(f['value'] for f in fields) and not text_hits and not word_hits,'New prerequisite evidence needs human interpretation before rebuilding'
        audit.append(dict(program_id=pid,source_ref='plan-'+pid,fields=fields,nonempty_prerequisite_fields=0,textual_keyword_hits=text_hits,word_xml_chars=len(text),word_keyword_hits=word_hits,
                          conclusion='非空先修记录未确认。字段只在FDUROP占位课程出现且为空；不能把其空值解释为HIST课程无需先修。',limits='JSON可见文本及Word正文XML已检索；未OCR图片，未取得全部课程大纲和研究生培养方案。'))
        for mi,module in enumerate(obj['courseModules']):
            for ci,row in enumerate(module.get('planCourses',[])):
                code=(row.get('course') or {}).get('code')
                if not code:continue
                terms[code][pid].append(dict(program_id=pid,module=module.get('nameZh'),raw_terms=row.get('terms') or [],terms_text=row.get('termsText'),
                    numeric_terms=sorted({int(m.group(1)) for t in row.get('terms') or [] if (m:=re.fullmatch(r'TERM_(\d+)',t))}),pointer=f'/courseModules/{mi}/planCourses/{ci}'))
    nodes=[]
    for code in sorted({r['课程代码'] for r in catalog}):
        rows=[r for r in catalog if r['课程代码']==code];names=list(dict.fromkeys(r['课程名称'] for r in rows))
        nodes.append(dict(id=code,name=names[0],names=names,group=group(names[0],code),levels=sorted({r['课程层次'] for r in rows}),terms=sorted({r['学期'] for r in rows}),
            teachers=sorted({t for r in rows for t in r['教师']}),honors=code.endswith('h'),section_codes=sorted({c for r in rows for c in r['教学班代码']}),
            plan_memberships=memberships[code],plan_term_evidence=[v for vv in terms[code].values() for v in vv],source_refs=['official-catalog']+(['plan-index'] if memberships[code] else []),
            course_record='../2026-10-30/report/history-research/index.html',official_prerequisite_status='not_confirmed_from_available_snapshots'))
    by_id={n['id']:n for n in nodes};edges=[];seen=set()
    def support(a,b):
        result=[]
        for pid in sorted(terms[a].keys() & terms[b].keys()):
            for x in terms[a][pid]:
                for y in terms[b][pid]:
                    if x['numeric_terms'] and y['numeric_terms'] and max(x['numeric_terms'])<min(y['numeric_terms']):
                        result.append(dict(program_id=pid,source_ref='plan-'+pid,source_terms=x['numeric_terms'],target_terms=y['numeric_terms'],source_pointer=x['pointer'],target_pointer=y['pointer'],interpretation='方案开设学期在前，仅佐证顺序；不证明先修门槛。'))
        return result
    def add(a,b,kind,reason,pointer,topic=None,basis='editorial_knowledge_structure'):
        assert a in by_id and b in by_id and a!=b,(a,b,pointer)
        directed=kind=='recommended_prerequisite'
        if not directed:a,b=sorted([a,b])
        if (a,b,kind) in seen:return
        seen.add((a,b,kind));order=support(a,b) if directed else []
        edges.append(dict(id=f'E{len(edges)+1:04d}',source=a,target=b,type=kind,directed=directed,label='建议先学' if directed else '内容联系',topic=topic,reason=reason,
            basis=basis,confidence='editorial_unverified',review_status='needs_syllabus_or_teacher_review',is_enrollment_requirement=False,
            scope='供学习准备和主题参照。未核对完整大纲；不推定选课资格、课程等价或学分互认，跨层次连线不表示升学要求。',
            source_refs=['official-catalog','editorial-rules']+sorted({s['source_ref'] for s in order}),rule_pointer=pointer,plan_order_support=order))
    for i,path in enumerate(rules['learning_paths']):
        for a,b in zip(path['codes'],path['codes'][1:]):add(a,b,'recommended_prerequisite',path['reason'],f'/learning_paths/{i}',path['title'])
    for i,(a,b,reason) in enumerate(rules['recommended']):add(a,b,'recommended_prerequisite',reason,f'/recommended/{i}')
    for i,(a,b,reason) in enumerate(rules['content_links']):add(a,b,'content_relation',reason,f'/content_links/{i}')
    for i,f in enumerate(rules['thematic_families']):
        for j,b in enumerate(f['members']):add(f['anchor'],b,'content_relation',f['reason'],f'/thematic_families/{i}/members/{j}',f['topic'],'title_level_editorial')
    names=collections.defaultdict(list)
    for n in nodes:names[n['name']].append(n['id'])
    for name,codes in names.items():
        for other in codes[1:]:add(codes[0],other,'content_relation','同名课程的检索参照；不同课号及层次不因此具有相同内容或互认资格。','同名题名参照规则',basis='same_name_title_only')
    degree=collections.Counter(code for e in edges for code in (e['source'],e['target']))
    for n in nodes:n.update(relation_count=degree[n['id']],relation_status='editorial_relations_available' if degree[n['id']] else 'unmapped_needs_syllabus')
    stats=dict(nodes=len(nodes),unique_names=len(names),sections=len(sections),edges=len(edges),official_prerequisites=0,recommended_prerequisites=sum(e['directed'] for e in edges),
        content_relations=sum(not e['directed'] for e in edges),ordered_edges_with_plan_support=sum(bool(e['plan_order_support']) for e in edges),
        nodes_with_relations=sum(bool(n['relation_count']) for n in nodes),unmapped_nodes=[n['id'] for n in nodes if not n['relation_count']])
    graph=dict(schema='fudan-history-course-graph/1',created_at='2026-11-19',source_snapshot_date='2026-10-28',source_commit='6fb20ee8a01b4fffff6ff4af59bbe558a99800c8',
        title='历史学系课程关系图谱',scope='2025秋／2026春实际开课249个课号；2026级4份本科培养方案用于身份及学期顺序佐证。',interpretation=rules['basis'],
        limitations=['官方先修未确认，不表示学校未设置先修。','内容联系基于题名和知识结构，尚未验证教学大纲的具体内容重合。','不把历史时段先后当作选课门槛；上下课顺序也须核对实际教学要求。','同名及H班保留独立节点；本科方案不用于证明研究生先修。','仅纳入两学期实际开课；方案中未在两学期开设的课程不补造为开课节点。','无边节点只是当前缺少可解释关系。'],
        groups=[dict(id=k,name=n,color=c) for k,n,c in GROUPS],sources=sources,nodes=nodes,edges=edges,paths=rules['learning_paths'],stats=stats)
    save(HERE/'graph.json',graph)
    save(HERE/'source-audit.json',dict(snapshot_date='2026-10-28',review_date='2026-11-19',programs=audit,official_prerequisites_confirmed=0,
        input_files=[dict(path=p.relative_to(HERE.parent).as_posix(),sha256=sha(p)) for p in inputs]))
    output_csv('nodes.csv',[dict(code=n['id'],name=n['name'],group=n['group'],levels='|'.join(n['levels']),teachers='|'.join(n['teachers']),terms='|'.join(n['terms']),honors=n['honors'],relation_count=n['relation_count'],relation_status=n['relation_status']) for n in nodes])
    output_csv('relations.csv',[dict(id=e['id'],source=e['source'],source_name=by_id[e['source']]['name'],target=e['target'],target_name=by_id[e['target']]['name'],type=e['type'],directed=e['directed'],reason=e['reason'],basis=e['basis'],is_enrollment_requirement=False,plan_order_program_ids='|'.join(sorted({s['program_id'] for s in e['plan_order_support']})),rule_pointer=e['rule_pointer']) for e in edges])
    overview(graph,by_id)
    payload=json.dumps(graph,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    template=(HERE/'viewer.html').read_text('utf-8')
    (HERE/'index.html').write_text(template.replace('/* GRAPH_DATA */',payload).replace('/* GRAPH_CORE */',(HERE/'graph-core.js').read_text('utf-8')),'utf-8',newline='\n')
    print(json.dumps(stats,ensure_ascii=False))
    return graph

def overview(graph,nodes):
    paths=graph['paths'];width=1660;height=220+len(paths)*100
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">历史学系课程关系与学习路径</title><desc id="desc">11条编辑建议路径。全部249个课号及内容联系见交互图谱；所有箭头均非官方先修要求。</desc>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="#92734d"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="#f6f6ef"/><g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
        '<text x="40" y="55" font-size="30" fill="#234b45" font-weight="700">历史学系 · 从通史框架走向问题与史料</text>',
        '<text x="40" y="91" font-size="18" fill="#5c6e65">虚线箭头：建议先学　／　249个课号与内容联系：见 index.html　／　官方先修要求：尚未确认</text>']
    mermaid=['flowchart LR','  %% 所有箭头均为编辑建议，不是官方选课门槛']
    for i,path in enumerate(paths):
        y=125+i*100;parts.append(f'<text x="40" y="{y+35}" font-size="17" fill="#566760">{html.escape(path["title"])}</text>')
        mermaid.append(f'  subgraph p{i}["{path["title"]}"]')
        for j,code in enumerate(path['codes']):
            n=nodes[code];x=260+j*274;name=n['name'];color=next(c for k,_,c in GROUPS if k==n['group'])
            if j:parts.append(f'<path d="M{x-33} {y+33}H{x-8}" stroke="#92734d" fill="none" stroke-width="2" stroke-dasharray="5 4" marker-end="url(#arrow)"/>')
            parts.append(f'<rect x="{x}" y="{y}" width="240" height="70" rx="9" fill="white" stroke="{color}" stroke-width="1.5"/>')
            lines=[name] if len(name)<=12 else [name[:12],name[12:]]
            for li,line in enumerate(lines):parts.append(f'<text x="{x+12}" y="{y+23+li*20}" font-size="16" fill="#253d35">{html.escape(line)}</text>')
            parts.append(f'<text x="{x+12}" y="{y+59}" font-size="12" fill="#6c7972">{code}</text>')
            mermaid.append(f'    p{i}_{j}["{name}<br/>{code}"]')
        for j in range(len(path['codes'])-1):mermaid.append(f'    p{i}_{j} -. 建议先学 .-> p{i}_{j+1}')
        mermaid.append('  end')
    parts.extend([f'<text x="40" y="{height-45}" font-size="17" fill="#4d6259">跨层次路径只表示知识准备；课程准入、语言水平、荣誉课资格另行核对。资料快照 2026-10-28 · 图谱整理 2026-11-19</text>','</g></svg>'])
    (HERE/'overview.svg').write_text('\n'.join(parts)+'\n','utf-8',newline='\n')
    (HERE/'overview.mmd').write_text('\n'.join(mermaid)+'\n','utf-8',newline='\n')

if __name__=='__main__':build()
