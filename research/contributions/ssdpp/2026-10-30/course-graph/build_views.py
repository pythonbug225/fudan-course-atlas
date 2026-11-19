"""Render an offline viewer, a shareable SVG roadmap and GitHub documentation."""
import collections,csv,hashlib,html,io,json
from pathlib import Path
R=Path(__file__).resolve().parent;P=R.parent
g=json.loads((R/'graph.json').read_text('utf-8'));N={n['id']:n for n in g['nodes']}
def write(name,s):(R/name).write_bytes(s.encode('utf-8'))
def esc(s):return html.escape(str(s),quote=True)
template=(R/'viewer-template.html').read_text('utf-8')
write('index.html',template.replace('__GRAPH__',json.dumps(g,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')))
paths=[('官方建议先修',['SWK30011','SWK40006'],'official_recommendation'),('官方社会学顺序',['SOCI30020','SOCI30021'],'curriculum_sequence')]
for i in [0,1,2,8,10,12,14,18,22]:
    p=g['pathways'][i];paths.append((p['title'],p['course_ids'],'recommended_preparation'))
width=1450;height=170+len(paths)*125+65
colors={'official_recommendation':'#14725b','curriculum_sequence':'#176a95','recommended_preparation':'#a45b1c'}
s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc"><title id="title">社政学院课程关系主线</title><desc id="desc">绿色为官方建议先修，蓝色为官方培养顺序，橙色虚线为推断的知识准备。都不是强制选课条件。图中仅展示代表性主线。</desc><defs>']
for k,c in colors.items():s.append(f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10Z" fill="{c}"/></marker>')
s.append('</defs><rect width="100%" height="100%" fill="#f2f6f8"/><g font-family="Microsoft YaHei,Noto Sans CJK SC,sans-serif"><text x="35" y="48" font-size="29" fill="#153347">社会发展与公共政策学院 · 课程关系主线</text><text x="35" y="82" font-size="16" fill="#536a7a">2026级方案 × 2025秋—2026春课表 · 整理于2026-11-19 · 课程按代码区分</text><text x="35" y="113" font-size="16" fill="#14725b">绿色：官方建议先修</text><text x="270" y="113" font-size="16" fill="#176a95">蓝色：官方培养顺序</text><text x="510" y="113" font-size="16" fill="#a45b1c">橙色虚线：推断的知识准备（均非强制先修）</text>')
for row,(label,codes,kind) in enumerate(paths):
    y=155+row*125;c=colors[kind]
    s.append(f'<text x="28" y="{y+38}" font-size="16" fill="#153347">{esc(label)}</text>')
    for i,code in enumerate(codes):
        x=224+i*235;name=N[code]['name'];lines=[name[j:j+12] for j in range(0,len(name),12)]
        if i:s.append(f'<line x1="{x-30}" y1="{y+43}" x2="{x-7}" y2="{y+43}" stroke="{c}" stroke-width="2" '+('stroke-dasharray="6 4" ' if kind=='recommended_preparation' else '')+f'marker-end="url(#{kind})"/>')
        s.append(f'<rect x="{x}" y="{y}" width="205" height="90" rx="8" fill="white" stroke="{c}"/><text x="{x+102}" y="{y+20}" text-anchor="middle" font-size="12" fill="#536a7a">{esc(code)}</text>')
        for j,line in enumerate(lines):s.append(f'<text x="{x+102}" y="{y+44+j*18}" text-anchor="middle" font-size="15" fill="#153347">{esc(line)}</text>')
s.append(f'<text x="35" y="{height-35}" font-size="15" fill="#536a7a">主线仅展示部分关系；全部{len(g["nodes"])}个节点、{len(g["edges"])}条关系及来源见交互图谱和graph.json。</text></g></svg>')
write('专业主线.svg',''.join(s))
missing=[n for n in g['nodes'] if n['relationship_status']=='needs_syllabus']
out=io.StringIO(newline='');w=csv.writer(out,lineterminator='\n');w.writerow(['课程代码','课程名称','范围','待补内容'])
for n in missing:w.writerow([n['id'],n['name'],n['scope'],'逐课大纲、先修条款、专题内容；当前不据题名强行连线'])
write('待补关系.csv','\ufeff'+out.getvalue())
counts=collections.Counter(e['type'] for e in g['edges'])
md=f'''# 社会发展与公共政策学院课程关系图谱

覆盖**296个实际开课代码**和15份2026级方案引用的课程，共**681个节点、{len(g['edges'])}条关系**。385个补充节点仅在方案中出现，包含其他院系课程与公共选修，不能据此判断本院开课。

![课程主线](专业主线.svg)

## 查看与下载

- [交互图谱](index.html)：下载本目录后打开`index.html`，可按名称、别名、课号和课程范围检索，点击节点逐层浏览，并筛选关系类型。GitHub文件页不执行HTML；可直接在上方查看SVG。
- [图谱JSON](graph.json)、[课程节点CSV](nodes.csv)、[关系边CSV](edges.csv)，用于后续检索与数据库导入。
- [来源核查记录](source-audit.json)、[验证结果](validation.json)、[待补关系清单](待补关系.csv)。原296个开课代码中，288个已连接，8个保留待补大纲状态。

## 如何理解连线

| 类型 | 数量 | 判定依据 |
| --- | ---: | --- |
| 官方建议先修 | 1 | 社会工作普通、留学生、港澳台侨生方案的明确备注，三份方案支持同一关系 |
| 官方培养顺序 | 1 | 人工核读课程体系原图中的明确箭头；并非系统硬性先修 |
| 建议知识准备 | {counts['recommended_preparation']} | 题名和一般学科知识的整理者推断，待当期大纲复核 |
| 内容联系 | {counts['content_link']} | 无方向的共同内容／方法主题；低置信度主题导航可在交互图中关闭 |
| 已核定强制先修 | 0 | 不能用本图判断选课资格 |

官方文字明确建议 **SWK30011 变态心理学 → SWK40006 精神健康社会工作**。同一方案内的前课代码已核对；不将PSYC30023或其荣誉课自动当作可替代前课。每条关系记录方向、是否强制、依据类型、可信度、理由与来源定位。

```mermaid
flowchart LR
  SWK30011["SWK30011 变态心理学"] -->|官方建议先修| SWK40006["SWK40006 精神健康社会工作"]
  SOCI30020["SOCI30020 古典社会学理论"] -->|官方培养顺序| SOCI30021["SOCI30021 当代社会学理论"]
  PSYC30017["PSYC30017 心理统计学一"] -.建议知识准备.-> PSYC30018["PSYC30018 心理统计学二"]
  PSYC30018 -.建议知识准备.-> PSYC40006["PSYC40006 高级心理统计分析"]
```

## 官方原图与核查范围

- [心理学普通方案原图](source-figures/153443-curriculum.png)、[社会学普通方案原图](source-figures/153495-curriculum.png)、[社会工作普通方案原图](source-figures/154352-curriculum.png)。配套JSON保留原件SHA-256及Word内部图片位置，原图未经重绘。
- 检索15份原始方案JSON，记录了128个`defaultPreCourses`／`defaultPreCourseList`字段实例，均为空；字段为空不能证明没有先修。大量课程对象没有这些字段。
- 已核读普通社会学、社会工作原图的明确连线，仅选取名称和代码可准确对应的一条关系；社工原图中的“社会统计学”与列课代码SWK10001（社会统计学基础）名称不完全相同，不将其直接映射为SOCI30006。心理学原图附供查阅，未将所有原图符号编码为强制先修。
- 来源资料为2026-10-30采集批次，图谱整理日期为2026-11-19；本次没有重新采集新的课表或逐课大纲。
- 课程代码保留普通／荣誉、不同培养层次及新旧版本，不因同名合并；`course_code`关联不表示学分互认。方案学期与实际开课学期分别保存。
- 25条建议学习路线仅供规划，跨本科与研究生的连线表示知识背景，不保证课程对学生开放。

## 复现与维护

在本目录运行 `python build_graph.py`、`python build_views.py`、`python validate_graph.py`。全部离线，仅使用仓库内数据和显式的关系规则。更新关系时必须同步保存来源；强制先修仅在取得明确、可定位的官方条款后新增。父目录`manifest.json`记录全部交付文件哈希。

CSV使用UTF-8 BOM；JSON中的`nodes.id`为课号，`edges.source/target`为节点ID；`content_link`无方向，`mandatory`均为false，`evidence`引用`sources`。未经核实的关系不进入官方先修类别。
'''
write('README.md',md)
parent=(P/'README.md').read_text('utf-8');entry='- [课程关系图谱](course-graph/README.md)：681个课程节点，区分官方建议先修、官方培养顺序、推断知识准备及内容联系，附交互HTML、SVG和可导入JSON/CSV。\n'
if entry not in parent:parent=parent.replace('## 阅读与下载\n','## 阅读与下载\n\n'+entry)
(P/'README.md').write_bytes(parent.encode('utf-8'))
print(json.dumps({'viewer_bytes':(R/'index.html').stat().st_size,'svg_bytes':(R/'专业主线.svg').stat().st_size,'missing_offerings':sum(n['scope']!='plan_only' for n in missing)}))
