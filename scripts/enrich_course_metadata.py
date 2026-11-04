"""Add current offering departments and curriculum-defined English levels."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,json,re,unicodedata
import pdfplumber
from catalog_io import read_catalog,write_catalog

parser=argparse.ArgumentParser();parser.add_argument('--sources',required=True);parser.add_argument('--audit',required=True);args=parser.parse_args()
P=Path(args.sources);D=Path(__file__).resolve().parents[1]/'public/data'
def read(p):return read_catalog(p)
def clean(s):return re.sub(r'\s+','',unicodedata.normalize('NFKC',s or '')).translate(str.maketrans({'⻢':'马','⻩':'黄','⻜':'飞','⻘':'青','⻓':'长','⻔':'门','⺠':'民','⻄':'西','⻅':'见','⻛':'风'}))
cat=read(D/'catalog.json');rows=read(P/'catalog_expanded.json');plan=read(P/'sources/plan_courses.json')
source_rows={(r['term'],r['code']):r for r in rows};departments={};audit=[];pages=defaultdict(list)
for r in rows:
    key=(r['term'],r['code'])
    if r.get('department'):departments[key]=(clean(r['department']),'开课变更表：开课院系')
    elif r.get('source_pdf') and r.get('pdf_page'):pages[(r['source_pdf'],r['pdf_page'])].append(r)
known={clean(r.get('department')) for r in rows if r.get('department')}
for f in (P/'danke/groups').glob('*.json'):
    dep=read(f).get('department')
    if dep:known.add(clean(dep))
known.update(['附属青浦区中心医院','附属静安区中心医院','附属肿瘤医院'])
tasks=[]
for file in dict.fromkeys(file for file,_ in pages):
    tasks.extend((file,i) for i in range(1,max(page for f,page in pages if f==file)+1))
docs={};current_owner={};current_title={}
for n,(file,page_no) in enumerate(tasks,1):
    if file not in docs:docs[file]=pdfplumber.open(file)
    page=docs[file].pages[page_no-1];words=page.extract_words(x_tolerance=1,y_tolerance=2)
    rs=pages.get((file,page_no),[])
    title=next((clean(w['text']) for w in words if w['top']<40 and w['x0']>180 and w['x1']<700 and ('课程' in w['text'] or '专业' in w['text'])),'')
    if title and title!=current_title.get(file):current_owner[file]=None;current_title[file]=title
    owners=[w for w in words if clean(w['text']) in known and 240<w['x0'] and w['x1']<620]
    intro=''.join(w['text'] for w in words if w['top']<min([w['top'] for w in words if w['text']=='选课序号'] or [140]))
    intro_owners=[d for d in known if d and d+'联系电话' in clean(intro)]
    if len(intro_owners)==1:current_owner[file]=intro_owners[0]
    header=next((w for w in words if clean(w['text'])=='开课院系'),None)
    if header:
        left=header['x0']-16;right=min(page.width,header['x1']+16)
        lines=sorted({e['top'] for e in page.edges if e.get('orientation')=='h' and e['x0']<110 and e['x1']>header['x1']-2})
        for r in rs:
            code=next((w for w in words if clean(w['text'])==r['code']),None)
            if not code:continue
            mid=(code['top']+code['bottom'])/2
            above=[y for y in lines if y<mid];below=[y for y in lines if y>mid]
            if not above or not below:continue
            top=max(above);bottom=min(below)
            bits=[w for w in words if w['x0']>=left-1 and w['x1']<=right+1 and w['top']>=top-.5 and w['bottom']<=bottom+.5]
            dep=clean(''.join(w['text'] for w in sorted(bits,key=lambda w:(round(w['top']/3),w['x0']))))
            if dep in known:
                departments[(r['term'],r['code'])]=(dep,'开课PDF：开课院系列')
    for r in rs:
        key=(r['term'],r['code'])
        if key in departments:continue
        code=next((w for w in words if clean(w['text'])==r['code']),None)
        if not code:continue
        prior=[w for w in owners if w['top']<code['top']]
        owner=clean(max(prior,key=lambda w:w['top'])['text']) if prior else current_owner.get(file)
        if owner:departments[key]=(owner,'开课PDF：院系分节标题/该节联系单位')
    if owners:current_owner[file]=clean(max(owners,key=lambda w:w['top'])['text'])
    page.close()
    if n%100==0:print('DEPARTMENT_PAGES',n,'/',len(tasks),flush=True)
for doc in docs.values():doc.close()
english=defaultdict(set);plan_credits=defaultdict(set)
for r in plan:
    cells=r['cells'];idx=next((i for i,s in enumerate(cells) if s==r['code']),None)
    if idx is not None and idx+1<len(cells):
        try:plan_credits[r['code']].add(float(cells[idx+1]))
        except (TypeError,ValueError):pass
    if r['plan_title']=='2026级 公共方案' and r['code'].startswith('GEEF'):
        matches=re.findall(r'大学英语(基础|进阶|高阶)课程',r['section'])
        if matches:english[r['code']].add({'基础':'综合英语','进阶':'进阶','高阶':'高阶'}[matches[-1]])
for g in cat['scope']:
    for o in g['offerings']:
        o.pop('department',None);o.pop('department_source',None)
        found=departments.get((o['term'],o['code']))
        if found:o['department'],o['department_source']=found
        else:audit.append({'course_id':g['id'],'term':o['term'],'section_code':o['code'],'status':'未从原表院系列确认'})
    g['departments']=sorted({o['department'] for o in g['offerings'] if o.get('department')})
    if len(english.get(g['code'],[]))==1:
        g['english_level']=next(iter(english[g['code']]))
        g['english_level_source']='2026级公共方案：大学外语课程清单'
    if g.get('history_only') and len(plan_credits.get(g['code'],[]))==1:
        g['plan_credits']=next(iter(plan_credits[g['code']]));g['credits_source']='培养方案课程行'
cat['metadata_sources']={'credits':'按当前筛选范围内开课教学班学分展示；历史课程取明确方案课程行。','departments':'用户提供开课PDF的开课院系列与开课变更表；未用限选学生院系或教师任职单位推断。','english_levels':'2026级公共方案按明确课程代码列出的综合英语、进阶、高阶；未纳入三类清单的课程不按名称或代码猜分级。'}
write_catalog(D/'catalog.json',cat)
report={'offers':sum(len(g['offerings']) for g in cat['scope']),'departments_confirmed':len(departments),'missing_offerings':audit,'department_names':dict(Counter(v[0] for v in departments.values())),'english_levels':{g['code']:g['english_level'] for g in cat['scope'] if g.get('english_level')},'english_conflicts':{k:sorted(v) for k,v in english.items() if len(v)>1}}
Path(args.audit).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k in ['offers','departments_confirmed','english_levels','english_conflicts']},ensure_ascii=False),flush=True)
