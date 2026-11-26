"""Build portable HTML, SVG roadmaps and reviewable per-cohort documentation."""
import collections,html,json
from pathlib import Path
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text('utf8'))
def write(p,s):p.write_bytes(s.encode())
def esc(s):return html.escape(str(s),quote=True)
RELEASE='https://github.com/pythonbug225/fudan-course-atlas/releases/tag/ssdpp-cohorts-2023-2025-20261126'
summary=[]
for year in [2023,2024,2025]:
    root=R/str(year);out=root/'course-graph';g=load(out/'graph.json');stats=load(root/'summary.json');summary.append(stats)
    plans=load(root/'official/programmes.json');nodes={n['id']:n for n in g['nodes']};audit=load(out/'source-audit.json')
    notice=('本年级含3份系统方案及年度汇编3个专业章节；两版课程代码分别保留，社会学来源有重叠。' if year==2024 else '')+'尚未核定强制先修。蓝色实线表示官方原图的培养顺序，橙色虚线是推断的知识准备，灰色点线是内容联系。'
    figures='<a href="专业主线.svg"><img src="专业主线.svg" alt="'+str(year)+'级建议学习主线"></a>'
    for p in plans:
        for im in p['images']:
            if '课程体系' in im['preceding_text'] or (p['plan_id']=='97235' and im['path'].endswith('rId6.png')):
                figures+='<a href="../official/'+esc(im['path'])+'"><img loading="lazy" src="../official/'+esc(im['path'])+'" alt="'+esc(p['title'])+'原始图"></a>'
    t=(R/'viewer-template.html').read_text('utf8').replace('__YEAR__',str(year)).replace('__NOTICE__',notice).replace('__FIGURES__',figures)
    write(out/'index.html',t.replace('__GRAPH__',json.dumps(g,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')))
    selected=[];seen=set()
    for route in g['pathways']:
        if route['title'] not in seen and len(route['course_ids'])<=5:
            selected.append((route['title'],route['course_ids'],'recommended_preparation'));seen.add(route['title'])
        if len(selected)>=9:break
    if year==2025:
        selected=[('原图：心理统计',['PSYC30017','PSYC30018','SOCI30029','PSYC30008'],'curriculum_sequence'),('原图：实验技术',['PSYC30001','PSYC30002','PSYC30024','PSYC30027','PSYC30028'],'curriculum_sequence')]+selected[:7]
    width=1500;height=200+len(selected)*130
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">社政学院{year}级课程关系主线</title><desc id="desc">实线为官方图示顺序，虚线为建议知识准备。均不表示强制先修。</desc><defs>']
    for typ,color in [('recommended_preparation','#a45b1c'),('curriculum_sequence','#176a95')]:s.append(f'<marker id="{typ}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10Z" fill="{color}"/></marker>')
    s.append(f'</defs><rect width="100%" height="100%" fill="#f2f6f8"/><g font-family="Microsoft YaHei,Noto Sans CJK SC,sans-serif"><text x="35" y="48" font-size="29" fill="#153347">社会发展与公共政策学院 · {year}级课程关系主线</text><text x="35" y="85" font-size="17" fill="#536a7a">{stats["plans"]}项方案／章节来源 · {stats["course_codes"]}个课程代码 · 采集于2026-11-26</text><text x="35" y="115" font-size="16" fill="#a45b1c">蓝色实线：官方图示培养顺序；橙色虚线：建议知识准备（推断）。均非强制选课条件。</text>')
    if year==2024:s.append('<text x="35" y="143" font-size="16" fill="#536a7a">2024年度汇编已补齐心理学、社会工作；汇编旧代码与系统现行代码保留各自来源。</text>')
    for row,(title,codes,typ) in enumerate(selected):
        y=168+130*row;color='#176a95' if typ=='curriculum_sequence' else '#a45b1c'
        s.append(f'<text x="25" y="{y+38}" font-size="15" fill="#153347">{esc(title)}</text>')
        for i,code in enumerate(codes):
            x=235+245*i
            if i:s.append(f'<line x1="{x-25}" y1="{y+42}" x2="{x-5}" y2="{y+42}" stroke="{color}" stroke-width="2" '+('stroke-dasharray="6 4" ' if typ=='recommended_preparation' else '')+f'marker-end="url(#{typ})"/>')
            s.append(f'<rect x="{x}" y="{y}" width="220" height="92" rx="8" fill="white" stroke="{color}"/><text x="{x+110}" y="{y+20}" text-anchor="middle" font-size="12" fill="#536a7a">{esc(code)}</text>')
            name=nodes[code]['name'];lines=[name[j:j+13] for j in range(0,len(name),13)]
            for j,line in enumerate(lines):s.append(f'<text x="{x+110}" y="{y+45+18*j}" text-anchor="middle" font-size="15" fill="#153347">{esc(line)}</text>')
    s.append('</g></svg>');write(out/'专业主线.svg',''.join(s))
    counts=collections.Counter(e['type'] for e in g['edges'])
    md=f'''# {year}级课程关系图谱

覆盖本年级{len(plans)}份系统方案{'及2024年度汇编3个专业章节' if year==2024 else ''}、{stats['course_codes']}个课程代码及{stats['activity_codes']}个培养环节，共{stats['nodes']}个节点、{stats['edges']}条关系。方案列课不等于实际开课，也不保证每门课对所有学生开放。

{('**2024年度汇编补齐社会工作、心理学，并保存社会学章节用于版本对照。汇编十位代码与系统现行代码分别保留，社会学有版本重叠，不能按同名课自动互认。**' if year==2024 else '')}

![课程关系主线](专业主线.svg)

- [交互图谱](index.html)：下载目录后离线打开，可按课程名、代码与具体培养方案筛选、点击课程逐层浏览。GitHub不直接执行HTML。
- [完整图谱JSON](graph.json)、[节点CSV](nodes.csv)、[关系CSV](edges.csv)、[待补关系](待补关系.csv)。
- [来源核查](source-audit.json)、[培养方案及原件目录](../README.md)、[自动验证](../../validation.json)。

| 关系类型 | 数量 | 含义 |
| --- | ---: | --- |
| 官方图示培养顺序 | {counts['curriculum_sequence']} | 同份方案原图中的明确箭头，课程名称与代码逐一对应；不是硬性先修 |
| 建议知识准备 | {counts['recommended_preparation']} | 题名及一般学科知识推断，两端须在至少同一方案列课 |
| 内容联系 | {counts['content_link']} | 无方向的共同议题或方法关联，可能跨专业，需大纲复核 |
| 已核定强制先修 | 0 | 当前资料不足以判定教务选课门槛 |

对{len(plans)}份JSON及Word导出文字检索先修关键词；未发现可编码的逐课强制先修条款或明确建议先修条款。{'2023、2024级接口未出现defaultPreCourse类字段。' if year<2025 else '检得72个先修字段实例（含重复课程对象），全部为空。'}字段缺失、为空或未出现关键词，都不能证明没有先修。

{('另外核读年度汇编PDF第377—391、747—753页（印刷第363—377、733—739页），未见明确逐课先修条款。以课程题名生成的学习建议仍属推断，不属于原书先修关系。汇编按专业章节筛选，普通／留学生差异见模块标注及原页。' if year==2024 else '')}

每条边保留来源定位、适用方案、判断依据、方向及`mandatory:false`。课程号不同就分别保留，不能据同名或H标记自动互认。点击“依据”可核对两端课程列课来源；**推断关系的来源仅证明课程身份，不能作为官方认可此连线的证据**。

{('2025心理学普通方案（97235）的原图核得11条明确课程箭头。社会学原图的“古典社会学理论／社会统计学”、社会工作原图的“社会研究方法A／社会统计学”与本次列课题名存在差异，未将这些旧题名自动替换成新课程代码。详见来源核查记录。' if year==2025 else '本年级Word导出仅包含页眉校名图片，未包含可编码的课程体系箭头；不由课程表先后或建议学期推导官方先修。')}

全部节点保留；{stats['nodes']-stats['connected_nodes']}个节点尚无足够材料连接课程，列在待补关系中。培养环节与正式课程分开统计。2026级的先修备注没有继承到本年级。
'''
    write(out/'README.md',md)
    md=f'# 社会发展与公共政策学院 · {year}级培养方案\n\n'
    if year==2024:md+='**来源补全：系统公开目录仅列3份社会学相关方案；已从教务处《2024年本科教学培养方案》补齐社会工作与心理学，并另存社会学章节。系统方案与年度汇编是不同版本，保留各自课号。**\n\n'
    md+=f'2026-11-26重新查询官方教务系统。按院系编号2567筛选，已下载全部{len(plans)}份目录记录对应的Word原件与详情JSON，并与同年全校目录中的院系记录逐项核对。此处保存的是查询时可导出的版本，不是入学当年冻结的历史快照。\n\n'
    md+='[课程关系图谱](course-graph/README.md) · [课程列课CSV](official/courses.csv) · [列课JSON](official/courses.json) · [模块及修读要求](official/modules.json) · [仅课程名称名单](社会发展与公共政策学院课程名单.txt) · [原件及SHA-256目录](official/programmes.json)\n\n'
    md+='| 方案ID | 官方方案名称 | 原文复核 |\n| --- | --- | --- |\n'
    for p in plans:md+=f'| {p["plan_id"]} | {p["title"]} | [官方接口]({p["detail_url"]}) · [JSON](official/{p["detail_path"]}) · [Word提取文字](official/word-text/plan-{p["plan_id"]}.txt) |\n'
    if year==2024:
        annual=load(root/'official/annual/metadata.json')
        md+='\n## 2024年度汇编补充\n\n[官方PDF原件]('+annual['source_url']+')：1116页，SHA-256 `'+annual['source_sha256']+'`。PDF第15页的查阅指南明确写明2024年，专业章与普通／留学生修读建议连续保存。以下PDF是原书相关页面的摘取件；字节未改动的完整原件在Release。\n\n| 专业章节 | PDF页码／印刷页码 | 复核材料 |\n| --- | --- | --- |\n'
        for sec in annual['sections']:
            a,b=sec['pages'][0],sec['pages'][-1];md+=f'| {sec["major"]}（含普通、留学生修读建议） | {a}—{b}／{a-14}—{b-14} | [原书页面摘取](official/annual/{sec["excerpt_path"]}) |\n'
        md+='\n[原表格单元格](official/annual/tables.json) · [330条提取列课](official/annual/courses.json) · [逐页文字](official/annual/pages.json) · [原件与摘取件元数据](official/annual/metadata.json)。全部143个不同表内课程代码与相关页文本逐项核对，无漏码。单元格的修读要求、学分与学期保留在原表中，不因合并单元格而猜测逐课值。\n'
    md+=f'\nWord字节原件保存在[原始资料Release]({RELEASE})，每份文件的大小和SHA-256见原件目录。Word提取文字用于检索，不代替原版表格；[配图](official/source-figures/)保留原始图片及元数据定位。\n\n'
    md+='[院系查询快照](official/raw/directory-department-2567.json.gz) · [全校同年目录快照](official/raw/directory-all.json.gz) · [覆盖核查](official/coverage.json) · [返回三年总览](../README.md)\n\n'
    md+='系统课程仅遍历接口的`courseModules[].planCourses`，未再次叠加`realPlanCourses`镜像。相同课号在不同模块的记录原样保留；节点按本年级课程代码去重。必修字段、模块学分要求、开设标注和建议学期分开保存；不能仅凭课程的布尔必修字段判断整条培养路径必修。公共通识模块若仅给出学分、不逐课列出，保留模块要求，不补造通识课程。\n'
    write(root/'README.md',md)

md='''# 社会发展与公共政策学院：2023—2025级培养方案与课程关系图谱

2026-11-26采集。新增18份官方Word原件、18份可公开的详情JSON、2024年度培养方案汇编原件及本院3个专业章节，以及三个年级独立的课程关系图谱。沿用社政学院分支，不改写原2026级批次。

**三个年级均已覆盖社会学、社会工作、心理学。2024级系统目录只列社会学相关方案，因此从教务处2024年度汇编补齐另两个专业，并保留社会学章节供版本对照。** 每年系统公开目录中的记录均已完整下载；这不等于证实校内所有内部班型均已公开。

| 年级 | 官方方案来源 | 课程代码 | 培养环节 | 关系数 | 入口 |
| --- | ---: | ---: | ---: | ---: | --- |
'''
for s in summary:md+=f'| {s["cohort"]} | {str(s["portal_plans"])+"份系统方案"+("＋3个汇编章节（有版本重叠）" if s["annual_chapters"] else "")} | {s["course_codes"]} | {s["activity_codes"]} | {s["edges"]} | [方案与原件目录]({s["cohort"]}/README.md) · [图谱]({s["cohort"]}/course-graph/README.md) |\n'
md+=f'''
## 原始资料

- [18份Word、2024完整汇编原件与离线资料包]({RELEASE})；[下载地址与校验值](release-assets.json)。原件保持下载字节，章节摘取件、图谱和提取文本是衍生资料。
- 三个年级分别保存官方全校目录、院系目录、详情JSON、列课CSV/JSON、模块要求、Word提取文字、原图和逐条SHA-256。
- [覆盖与缺项核查](coverage-audit.json)、[数据与图谱验证](validation.json)、[浏览器检查](browser-validation.json)、[文件清单](manifest.json)。
- [2026级既有方案与研究](../2026-10-30/README.md)。本次没有重新采集2025秋—2026春课程表或课评。

## 先修关系的证据边界

2023、2024级现有方案未取得明确的逐课官方先修条款；2025级心理学普通方案有11条可核验的原图培养顺序。**三个年级均尚未核定强制先修边**。官方培养顺序、整理者建议知识准备、无方向内容联系分别编码。

课程号与题名须同时匹配；有向学习建议还要求两端在同一方案列课。图谱可按普通、留学生、港澳台侨生和双学位／融通方案筛选。2025年原图与列课题名不一致处在来源审计中记录，不把旧图名称自动映射为新课号，不继承2026级的先修条款。

公共通识模块与专业课程共同构成完整培养要求。本批保留每份方案中的公共模块要求；未逐课列出的通识目录不伪装成已经抓取的课程。当前公开列表未列独立公共培养方案。

## 数据来源与可复现性

来源：[复旦官方培养方案查询](https://fdjwgl.fudan.edu.cn/manager/bizType/2/page-center/major-program-search-view?skipAuth=1)。年份使用`YEARS`，院系使用`DEPART_IDS=2567`，每年同时核对不加院系筛选的目录与返回总条数。目录与方案截至采集日可见，不能还原当年版本历史。

详情JSON保留培养内容及数组顺序；人员联系方式／认证字段置空，非空脱敏位置逐份登记。它是可公开的原始接口快照，不冒充逐字节未处理的网络响应。没有使用或上传个人教务记录、账号密码、Cookie或认证令牌。

从本目录运行：

```shell
python build_cohorts.py
python build_views.py
python validate.py
```

上述图谱生成仅用Python标准库。年度汇编的表格与章节可用`python extract_annual.py 完整原件.pdf 新输出目录`另行复核，需要`pdfplumber`及`pymupdf`；摘取件重新生成时PDF内部标识和哈希可能变化。

离线生成不依赖网络。[候选关系规则](relationship-proposals.json)是整理者推断的来源，与官方证据分开；[采集脚本](fetch_official.py)用于按需重新下载公开数据，新快照应单独存档并重新审阅。
'''
write(R/'README.md',md)
print('views and documentation built')
