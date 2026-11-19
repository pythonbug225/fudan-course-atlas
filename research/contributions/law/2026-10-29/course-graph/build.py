"""Build the Law course graph from pinned local sources; standard library, offline."""
import collections
import csv
import gzip
import hashlib
import html
import io
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
GROUPS = [
    ('theory','理论与法律史','#9f5a38'), ('civil','民事与家事','#377d78'),
    ('business','商事与经济','#a27829'), ('public','宪法、行政与监察','#547aaf'),
    ('criminal','刑法与犯罪研究','#ad5964'), ('procedure','诉讼与争议解决','#7a65a7'),
    ('international','国际与涉外','#438494'), ('digital','知识产权与数字法','#64804c'),
    ('environment','环境与资源','#55856b'), ('methods','研究与法律实践','#6b7185'),
    ('language','语言与专业外语','#87678b'), ('general','通识与其他','#8c8275'),
]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group(name, code):
    if re.search('英语|外语|汉语|外国语',name):return 'language'
    if code.startswith(('GESP','GEIP')) or name in ['文艺复兴史','思辨与创新']:return 'general'
    if re.search('知识产权|人工智能|Python|科技',name):return 'digital'
    if re.search('环境|自然资源',name):return 'environment'
    if re.search('刑|犯罪|检察',name):return 'criminal'
    if re.search('宪法|行政|监察|党内|人权|立法',name):return 'public'
    if re.search('诉讼|仲裁|证据|纠纷|调解',name):return 'procedure'
    if re.search('国际|涉外|海商|海事|欧盟|对外|全球化|外商',name):return 'international'
    if re.search('民法|物权|债法|合同|侵权|婚姻|家事|房地产',name):return 'civil'
    if re.search('商|公司|金融|证券|银行|财税|税法|票据|破产|企业|市场|投融|劳动|经济法|保险',name):return 'business'
    if re.search('法理|法律史|法制史|思想史|法律文化|法治与文化|比较法|欧陆|英美法|法学思想|法治思想|法律体系',name):return 'theory'
    if code.startswith('GE'):return 'general'
    return 'methods'


def csv_output(path, rows, fields):
    with path.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def build():
    rules=read(HERE/'rules.json')
    sections=read(BATCH/'official/sections.json')
    plans=read(BATCH/'official/programs.json')
    plan_index={str(p['方案编号']):p for p in plans}
    inputs=[BATCH/'official/sections.json',BATCH/'official/program-courses.csv',BATCH/'official/programs.json',HERE/'rules.json']
    sources=[{'id':'official-sections','path':'../official/sections.json','description':'2025秋／2026春法学院369个官方教学班；课程身份与层次来源。'},
             {'id':'plan-course-index','path':'../official/program-courses.csv','description':'2026级8份本科培养方案列课；不代表这两学期实际开课。'},
             {'id':'editorial-rules','path':'rules.json','description':rules['basis']}]
    memberships=collections.defaultdict(list)
    with (BATCH/'official/program-courses.csv').open(encoding='utf-8-sig',newline='') as handle:
        plan_rows=list(csv.DictReader(handle))
    for row in plan_rows:
        memberships[row['课程代码']].append({'program_id':row['方案编号'],'program_name':row['方案名称'],'module':row['模块'],
            'compulsory_in_this_module':row['必修字段']=='True','reported_terms':row['开设季节'],'suggested_terms':row['建议学期']})
    plan_terms=collections.defaultdict(lambda:collections.defaultdict(list))
    audit=[]
    for plan_id,plan in sorted(plan_index.items()):
        path=BATCH/'raw/official/programs'/f'{plan_id}.json.gz';inputs.append(path)
        obj=json.loads(gzip.decompress(path.read_bytes()))
        source_id='plan-'+plan_id
        sources.append({'id':source_id,'path':'../raw/official/programs/'+path.name,'url':plan['详情来源'],
            'description':plan['方案名称'],'snapshot_date':'2026-10-29','sha256':sha(path)})
        fields=[];text_hits=[]
        def inspect(value,pointer=''):
            if isinstance(value,dict):
                for key,child in value.items():
                    where=pointer+'/'+str(key)
                    if re.search(r'defaultPre|pre.?req|preCourse|先修',key,re.I):
                        fields.append({'pointer':where,'value':child})
                    inspect(child,where)
            elif isinstance(value,list):
                for i,child in enumerate(value):inspect(child,pointer+'/'+str(i))
            elif isinstance(value,str) and re.search('先修|先行课程|前修课程|修读顺序|后续课程',value):
                text_hits.append({'pointer':pointer,'text':re.sub('<[^>]+>','',value)})
        inspect(obj)
        assert not any(f['value'] for f in fields) and not text_hits, 'New prerequisite evidence requires manual interpretation'
        audit.append({'program_id':plan_id,'source_ref':source_id,'prerequisite_field_occurrences':len(fields),
            'nonempty_prerequisite_fields':0,'fields':fields,'textual_keyword_hits':text_hits,
            'limits':'字段出现次数含重复的planCourses/realPlanCourses。缺失或空字段不表示无先修；内嵌图片未OCR，尚未核对每门课大纲与研究生培养方案。'})
        for mi,module in enumerate(obj['courseModules']):
            for ci,row in enumerate(module.get('planCourses',[])):
                course=row.get('course') or {};code=course.get('code')
                if not code:continue
                record={'program_id':plan_id,'module':module.get('nameZh') or module.get('name'),
                    'raw_terms':row.get('terms') or [],'terms_text':row.get('termsText'),
                    'numeric_terms':sorted({int(m.group(1)) for t in row.get('terms',[]) if (m:=re.fullmatch('TERM_([1-9][0-9]*)',t))}),
                    'pointer':f'/courseModules/{mi}/planCourses/{ci}'}
                plan_terms[code][plan_id].append(record)
    nodes=[]
    for code in sorted({s['course_code'] for s in sections}):
        rows=[s for s in sections if s['course_code']==code]
        names=list(dict.fromkeys(s['course_name'] for s in rows))
        nodes.append({'id':code,'name':names[0],'names':names,'group':group(names[0],code),
            'levels':sorted({r['course_level'] for r in rows}),'terms':sorted({r['term'] for r in rows}),
            'teachers':sorted({t for r in rows for t in r['teachers']}),'honors':code.endswith('h'),
            'section_codes':sorted({r['section_code'] for r in rows}),'plan_memberships':memberships[code],
            'plan_term_evidence':[r for records in plan_terms[code].values() for r in records],
            'source_refs':['official-sections']+(['plan-course-index'] if memberships[code] else []),
            'course_record':'../courses/'+code+'.json'})
    by_id={n['id']:n for n in nodes};edges=[];seen=set()
    def order_support(a,b):
        results=[]
        for pid in sorted(plan_terms[a].keys() & plan_terms[b].keys()):
            for left in plan_terms[a][pid]:
                for right in plan_terms[b][pid]:
                    if left['numeric_terms'] and right['numeric_terms'] and max(left['numeric_terms'])<min(right['numeric_terms']):
                        results.append({'program_id':pid,'source_ref':'plan-'+pid,
                            'source_terms':left['numeric_terms'],'target_terms':right['numeric_terms'],
                            'source_pointer':left['pointer'],'target_pointer':right['pointer'],
                            'interpretation':'方案开设学期在前，仅佐证顺序；不证明先修门槛。'})
        return results
    def add(a,b,kind,reason,topic=None,basis='editorial_knowledge_structure',rule=None):
        assert a in by_id and b in by_id and a!=b,(a,b)
        directed=kind!='content_relation'
        if not directed:a,b=sorted([a,b])
        if (a,b,kind) in seen:return
        seen.add((a,b,kind));support=order_support(a,b) if directed else []
        edges.append({'id':f'E{len(edges)+1:04d}','source':a,'target':b,'type':kind,'directed':directed,
            'label':'建议先学' if directed else '内容联系','topic':topic,'reason':reason,
            'basis':basis,'confidence':'editorial_unverified','review_status':'needs_syllabus_or_teacher_review',
            'is_enrollment_requirement':False,'scope':'知识准备或主题参照；不推定教学班、学分互认、必修关系或选课限制。',
            'source_refs':['official-sections','editorial-rules']+sorted({s['source_ref'] for s in support}),
            'rule_pointer':rule,'plan_order_support':support})
    for i,path in enumerate(rules['learning_paths']):
        for a,b in zip(path['codes'],path['codes'][1:]):
            add(a,b,'recommended_prerequisite',path['reason'],path['title'],rule=f'/learning_paths/{i}')
    for i,(a,b,reason) in enumerate(rules['recommended']):add(a,b,'recommended_prerequisite',reason,rule=f'/recommended/{i}')
    for i,(a,b,reason) in enumerate(rules['content_links']):add(a,b,'content_relation',reason,rule=f'/content_links/{i}')
    for i,family in enumerate(rules['thematic_families']):
        for b in family['members']:add(family['anchor'],b,'content_relation',family['reason'],family['topic'],rule=f'/thematic_families/{i}')
    for node in nodes:
        base=node['id'].removesuffix('h')
        if node['honors'] and base in by_id:
            add(base,node['id'],'content_relation','同一课程主题的普通与H班，组织、深度及选课规则分别核对；不推定等价、互认或同一先修要求。',basis='honors_title_reference',rule='H班课名对应规则')
    names=collections.defaultdict(list)
    for n in nodes:names[n['name']].append(n['id'])
    for name,ids in names.items():
        for other in ids[1:]:add(ids[0],other,'content_relation','同名课程的检索参照；代码、层次和教师可能不同，不能据此确认内容相同或学分互认。',basis='same_name_title_only',rule='同名课名对应规则')
    degree=collections.Counter(x for e in edges for x in [e['source'],e['target']])
    for n in nodes:
        n['relation_count']=degree[n['id']]
        n['relation_status']='editorial_relations_available' if degree[n['id']] else 'unmapped_needs_syllabus'
        n['official_prerequisite_status']='not_confirmed_from_available_snapshots'
    stats={'nodes':len(nodes),'unique_names':len(names),'sections':len(sections),'edges':len(edges),
        'recommended_prerequisites':sum(e['type']=='recommended_prerequisite' for e in edges),'official_prerequisites':0,
        'content_relations':sum(e['type']=='content_relation' for e in edges),
        'ordered_edges_with_plan_support':sum(bool(e['plan_order_support']) for e in edges),
        'nodes_with_relations':sum(bool(n['relation_count']) for n in nodes),
        'unmapped_nodes':[n['id'] for n in nodes if not n['relation_count']]}
    graph={'schema':'fudan-law-course-graph/1','created_at':'2026-11-19','source_snapshot_date':'2026-10-29',
        'title':'法学院课程关系图谱','scope':'法学院2025秋／2026春开课260课号；2026级8份本科培养方案用于身份和开设学期佐证。',
        'interpretation':rules['basis'],
        'limitations':['现有先修字段均为空或缺失；0条已确认官方先修不表示学校没有先修要求。','未读取内嵌图片或获取各课最新大纲；未从课号、年级或同名推定先修。','研究生课程仅以当前课表与知识结构作编辑关联；本科培养方案不能证明其先修要求。','同名、普通与H班仅保留主题参照；不推定互认，也不自动继承学习顺序。','无边节点标记待核，不等于没有课程联系。'],
        'groups':[{'id':key,'name':name,'color':color} for key,name,color in GROUPS],
        'sources':sources,'nodes':nodes,'edges':edges,'paths':rules['learning_paths'],'stats':stats}
    save(HERE/'graph.json',graph)
    save(HERE/'source-audit.json',{'snapshot_date':'2026-10-29','review_date':'2026-11-19','programs':audit,
        'official_prerequisites_confirmed':0,'interpretation':'开设学期不等于先修门槛；字段空值不等于无需先修。',
        'input_files':[{'path':p.relative_to(BATCH).as_posix(),'sha256':sha(p)} for p in inputs]})
    csv_output(HERE/'nodes.csv',[{'code':n['id'],'name':n['name'],'group':n['group'],'levels':'|'.join(n['levels']),
        'honors':n['honors'],'relation_count':n['relation_count'],'relation_status':n['relation_status']} for n in nodes],
        ['code','name','group','levels','honors','relation_count','relation_status'])
    csv_output(HERE/'relations.csv',[{'id':e['id'],'source':e['source'],'source_name':by_id[e['source']]['name'],
        'target':e['target'],'target_name':by_id[e['target']]['name'],'type':e['type'],'directed':e['directed'],
        'reason':e['reason'],'basis':e['basis'],'is_enrollment_requirement':False,
        'plan_order_program_ids':'|'.join(sorted({s['program_id'] for s in e['plan_order_support']})),
        'rule_pointer':e['rule_pointer']} for e in edges],
        ['id','source','source_name','target','target_name','type','directed','reason','basis','is_enrollment_requirement','plan_order_program_ids','rule_pointer'])
    overview(graph,by_id)
    template=(HERE/'viewer.html').read_text('utf8')
    embedded=json.dumps(graph,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (HERE/'index.html').write_text(template.replace('/* GRAPH_DATA */',embedded).replace('/* GRAPH_CORE */',(HERE/'graph-core.js').read_text('utf8')),encoding='utf8',newline='\n')
    print(json.dumps(stats,ensure_ascii=False))
    return graph


def overview(graph,by_id):
    paths=graph['paths'][:7];parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="890" viewBox="0 0 1440 890" role="img" aria-labelledby="title desc">',
        '<title id="title">法学院课程关系：本科与本研融通学习路径</title><desc id="desc">七条编辑建议学习路径，虚线箭头只表示建议先学。完整260课号和内容联系见交互图谱。</desc>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#77716b"/></marker></defs>',
        '<rect width="1440" height="890" fill="#f7f9f9"/><g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
        '<text x="44" y="58" font-size="28" font-weight="700" fill="#173f3b">法学院 · 从基础走向专题</text>',
        '<text x="44" y="92" font-size="17" fill="#566762">建议学习顺序 · 260个课程代码的完整关联见 index.html / graph.json</text>']
    mermaid=['flowchart LR']
    for i,path in enumerate(paths):
        y=130+i*90
        parts.append(f'<text x="44" y="{y+33}" font-size="17" fill="#52665f">{html.escape(path["title"])}</text>')
        for j,code in enumerate(path['codes']):
            x=255+j*280;name=by_id[code]['name'];color=next(c for k,_,c in GROUPS if k==by_id[code]['group'])
            if j:parts.append(f'<path d="M {x-45} {y+31} H {x-9}" stroke="#77716b" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arrow)"/>')
            parts.extend([f'<rect x="{x}" y="{y}" width="235" height="63" rx="10" fill="white" stroke="{color}" stroke-width="1.5"/>',
                f'<text x="{x+14}" y="{y+27}" font-size="18" fill="#203e36">{html.escape(name)}</text>',
                f'<text x="{x+14}" y="{y+49}" font-size="13" fill="#6c7671">{code}</text>'])
            mermaid.append(f'  {code}["{name}"]')
        for a,b in zip(path['codes'],path['codes'][1:]):mermaid.append(f'  {a} -. 建议先学 .-> {b}')
    parts.extend(['<text x="44" y="815" font-size="17" fill="#425d53">箭头均为编辑建议；方案开设学期仅作顺序佐证，不构成官方选课门槛。</text>',
        '<text x="44" y="850" font-size="16" fill="#65746f">资料快照：2026-10-29　整理：2026-11-19　完整图谱另含研究生路径、内容联系、H班和同名课参照。</text></g></svg>'])
    (HERE/'overview.svg').write_text('\n'.join(parts)+'\n',encoding='utf8',newline='\n')
    (HERE/'overview.mmd').write_text('\n'.join(mermaid)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':build()
