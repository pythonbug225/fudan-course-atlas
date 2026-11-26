"""Package source snapshots, name-only lookup lists and cohort comparisons."""
import collections,gzip,hashlib,html,json,shutil,sys
from pathlib import Path
W=Path(__file__).resolve().parent;O=W if (W/'2023/official').exists() else W/'package/cohorts'
def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def read(p):return json.loads(p.read_text('utf-8-sig'))
if '--manifest-only' in sys.argv:
 records=[{'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
 put(O/'manifest.json',{'algorithm':'sha256','retrieved_date':'2026-11-26','records':records})
 print('updated manifest',len(records));sys.exit(0)
if O!=W:
 for name in ['build_cohorts.py','fetch_official.py','validate_cohorts.py','extract_handbook.py','curate_handbook.py','curation.json','viewer-template.html','finalize_package.py']:
  shutil.copyfile(W/name,O/name)
 shutil.copyfile(W/'handbook-index.json',O/'sources/handbook-index.json')
for p in O.glob('*/official/raw/*.json'):
 target=p.with_suffix('.json.gz');target.write_bytes(gzip.compress(p.read_bytes(),mtime=0));p.unlink()
for p in O.glob('*/course-graph/viewer-check.js'):p.unlink()
stats=read(O/'coverage.json');names=set();byyear={};figures=[]
for s in stats:
 y=s['cohort'];r=O/str(y);rows=read(r/'official/courses.json');g=read(r/'course-graph/graph.json');plans=read(r/'official/programmes.json')
 core=sorted({row['course_name'] for row in rows if row['scope']=='programme'});candidates=sorted({row['course_name'] for row in rows});names.update(core)
 (r/f'数学科学学院{y}级课程名单.txt').write_text('\n'.join(core)+'\n','utf-8');(r/f'{y}级全部方案候选课程名单.txt').write_text('\n'.join(candidates)+'\n','utf-8')
 byyear[y]={n['id']:n for n in g['nodes'] if n['scope']=='programme'}
 gallery=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>官方内嵌图原件</title><style>body{font:16px/1.7 system-ui;max-width:1200px;margin:24px auto;padding:16px;color:#234}img{max-width:100%;height:auto}figure{margin:18px 0;border:1px solid #ccd;padding:16px}h2{margin-top:35px}</style>',f'<h1>数学科学学院{y}级：官方方案内嵌图</h1><p>由Word原件直接提取，字节不变。图中的课程系列、阶段安排和科研路径不直接认定为教务强制先修。重复图片保留各自方案归属。</p><a href="../README.md">返回本年级</a>']
 for p in plans:
  images=[im for im in p['images'] if (r/'official'/im['path']).stat().st_size>10000]
  if images:
   gallery.append(f'<h2>{html.escape(p["title"])}</h2><a href="programme-{p["plan_id"]}.html">方案课程表</a> · <a href="{p["word_path"]}">Word原件</a>')
  for im in images:
   gallery.append(f'<figure><img src="{im["path"]}" alt="方案{p["plan_id"]}原件内嵌图"><figcaption>{html.escape(im["path"])}；原Word段落索引{im["paragraph"]}</figcaption></figure>')
   figures.append({'cohort':y,'plan_id':p['plan_id'],**im,'interpretation':'原图展示培养目标、学分结构、课程体系或科研路径；未据箭头判定硬性先修。'})
  f=r/'official'/f'programme-{p["plan_id"]}.html';text=f.read_text('utf-8')
  if 'id="source-figures"' not in text and images:
   text+='<section id="source-figures"><h2>官方方案内嵌图</h2><a href="source-figures.html">本年级原图索引</a>'+''.join(f'<figure><img style="max-width:100%" src="{im["path"]}" alt="官方方案内嵌图"><figcaption>{html.escape(im["path"])}</figcaption></figure>' for im in images)+'</section>'
   f.write_text(text,'utf-8')
 if not any(p['images'] and any((r/'official'/im['path']).stat().st_size>10000 for im in p['images']) for p in plans):gallery.append('<p>这些方案未内嵌可辨识的课程体系图；Word中小型符号图片仍保留于source-figures目录。</p>')
 gallery.append('</html>');(r/'official/source-figures.html').write_text(''.join(gallery),'utf-8')
 for f in [r/'README.md',r/'course-graph/README.md']:
  text=f.read_text('utf-8');extra='\n## 手册与原图\n\n'+('[2024版手册原件](../sources/math-handbook-2024.pdf) · [大纲基本要求摘录](../sources/handbook-course-requirements.json) · [官方内嵌图](official/source-figures.html)\n' if f.parent==r else '[2024版手册原件](../../sources/math-handbook-2024.pdf) · [大纲基本要求摘录](../../sources/handbook-course-requirements.json) · [本年级官方内嵌图](../official/source-figures.html)\n')
  if '## 手册与原图' not in text:text+=extra
  f.write_text(text.rstrip()+'\n','utf-8')
put(O/'sources/figure-audit.json',figures)
(O/'数学科学学院课程名单.txt').write_text('\n'.join(sorted(names))+'\n','utf-8')
comparisons=[];summary_rows=[];details=[];lines=['# 2023—2025级课程目录对照','','按本年级当前方案所收录的方案明确列出的课程与科研条目比较；相同代码保留题名变体。下表的新增或未收录仅表示两组当前快照的集合差异，不能视为开课、停开或替代证明。','','| 年级对照 | 共同代码 | 后一年独有 | 前一年独有 |','| --- | ---: | ---: | ---: |']
for a,b in [(2023,2024),(2024,2025)]:
 common=set(byyear[a])&set(byyear[b]);added=set(byyear[b])-set(byyear[a]);absent=set(byyear[a])-set(byyear[b])
 rec={'from':a,'to':b,'common_code_count':len(common),'later_only':[{'code':c,'name':byyear[b][c]['name']} for c in sorted(added)],'earlier_only':[{'code':c,'name':byyear[a][c]['name']} for c in sorted(absent)],'same_code_name_variants':[{'code':c,'earlier':byyear[a][c]['name_variants'],'later':byyear[b][c]['name_variants']} for c in sorted(common) if byyear[a][c]['name_variants']!=byyear[b][c]['name_variants']]};comparisons.append(rec)
 summary_rows.append(f'| {a} → {b} | {len(common)} | {len(added)} | {len(absent)} |')
 details+=['',f'## {a} → {b}：后一年独有','']+[f'- {c["code"]}：{c["name"]}' for c in rec['later_only']]+['',f'## {a} → {b}：前一年独有','']+[f'- {c["code"]}：{c["name"]}' for c in rec['earlier_only']]
put(O/'cohort-comparison.json',comparisons);(O/'cohort-comparison.md').write_text('\n'.join(lines+summary_rows+details)+'\n','utf-8')
readme=['# 数学科学学院2023—2025级培养方案与课程关系','','已按教务公开目录的院系ID **2581** 逐项核对，取得 **36份官方Word原件**、方案JSON快照、课程表与每年级独立图谱。采集日：2026-11-26。','','| 年级 | 方案原件 | 方案内课程/科研条目（代码去重） | 仅公共候选 | 手册准备参考关系 | 图谱 |','| --- | ---: | ---: | ---: | ---: | --- |']
for s in stats:
 y=s['cohort'];readme.append(f'| {y} | {s["plans"]} | {s["programme_entries"]} | {s["public_option_entries"]} | {s["historical_preparation_edges"]} | [原件与说明]({y}/README.md) · [交互图谱]({y}/course-graph/index.html) · [课程关系]({y}/course-graph/learning-paths.md) |')
readme+=['','统计按各年级具体模块收录计算：包含课程表明确列出的部分通识课程、专业课程及科研条目，不是狭义数学专业课数，也不是个人必修课数。仅由引用公共目录展开的候选另列。','','## 阅读入口','','- [数学科学学院课程名单](数学科学学院课程名单.txt)：三个年级方案明确列出的课程与科研条目的去重课程名，文件只含名称。','- [逐年目录对照](cohort-comparison.md)及[机器可读对照](cohort-comparison.json)。','- [2024版学习指导手册原件](sources/math-handbook-2024.pdf)及[68份完整大纲的基本要求摘录](sources/handbook-course-requirements.json)。','- [官方内嵌图定位](sources/figure-audit.json)、[覆盖统计](coverage.json)、[校验结果](validation.json)、[SHA-256清单](manifest.json)。','','## 版本和先修含义','','本任务覆盖数学与应用数学、信息与计算科学的普通、英才、强基、相辉、留学生、港澳台侨及双学位/贯通版本，以各年实际公开目录为准；没有将各方案的课程拼成单个人的必修清单。公共引用模块若未展开，保留其模块规则及缺口，不从其他年级补造课程。','','图谱关系分别记录：同一方案数字学期在先、2024版手册的知识准备参考、编辑建议、内容联系、同名异号、模块收录。所有关系都保留依据。手册明确预修表述与知识背景均可核对页码，但旧代码与当前代码只按题名作参考，不能据此确认代码替代、学分互认或其他年级的强制规则；当前尚未核实到本年级选课系统执行的硬性先修条款。宽泛的“数学分析”“高等代数”“点集拓扑”等未强行展开成当前若干课程的必修链。','','2025年部分方案另附官方课程体系、学分结构和科研训练路线图，已从Word字节无改动提取并提供图集；这些图的系列/阶段关系不直接认定为硬性先修。各年级图谱默认显示方案内课程与科研条目，支持方案筛选、关键词搜索、关系类型筛选和SVG导出。HTML需下载后打开；GitHub页面直接阅读README、SVG和关系表。','','## 原始数据与复现','','`YYYY/official/word-originals/`是官方Word下载字节；`raw/*.json.gz`是公开目录与详情响应的JSON规范化快照。课程行、模块规则、必修字段、terms/suggestTerms以及JSON Pointer均保留。方案为采集日系统当前版本，可能经历后续修订，不能称为入学当年未修订发布版。手册保留版本年份和大纲内部日期。','','官方来源：[培养方案公开检索](https://fdjwgl.fudan.edu.cn/manager/bizType/2/page-center/major-program-search-view?skipAuth=1)；[2024版数学手册](https://jwc.fudan.edu.cn/_upload/article/files/d4/56/707002a8413b8a3cc690244c1118/5f39341f-9c23-496e-807b-cc7ae77cd970.pdf)。未使用个人认证或个人教务数据。原件权利归原权利人；公开可访问不等于取得单独再利用许可。','','复现（Python 3；重新抽取PDF时需要PyMuPDF）：','','```sh','python build_cohorts.py','python finalize_package.py','python validate_cohorts.py','python finalize_package.py --manifest-only','python validate_cohorts.py --check','```','','在线重新下载可运行`fetch_official.py`，它会覆盖源快照；无需登录。关系编辑配方见`curation.json`及`curate_handbook.py`。本次已完成原件CRC/哈希、JSON来源定位、方案内学期顺序、路径、离线重建、CSV/SVG/HTML结构和JavaScript语法核验；未完成浏览器交互验收。']
(O/'README.md').write_text('\n'.join(readme)+'\n','utf-8')
cards=''.join(f'<article><h2>{s["cohort"]}级</h2><p>{s["plans"]}份方案 · {s["programme_entries"]}个方案内课程与科研条目</p><a href="{s["cohort"]}/course-graph/index.html">打开课程图谱</a> · <a href="{s["cohort"]}/README.md">原件与说明</a> · <a href="{s["cohort"]}/official/source-figures.html">官方内嵌图</a></article>' for s in stats)
(O/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>数学科学学院2023—2025级课程图谱</title><style>body{font:17px/1.8 system-ui;background:#edf3f6;color:#234;margin:40px auto;padding:20px;max-width:1050px}article{padding:18px 26px;background:white;border:1px solid #cdd;margin:18px 0;border-radius:12px}a{color:#17677e}h1{line-height:1.4}</style><h1>数学科学学院<br>2023—2025级培养方案与课程图谱</h1><p>36份官方方案原件。先选择年级，再在图谱中筛选个人适用方案。手册知识准备、方案学期与编辑建议分别显示，不作为强制先修证明。</p>'+cards+'<p><a href="README.md">数据范围与方法</a> · <a href="数学科学学院课程名单.txt">课程名称名单</a> · <a href="cohort-comparison.md">年级对照</a> · <a href="sources/handbook-course-requirements.json">手册准备条件</a></p></html>','utf-8')
(O/'.gitattributes').write_text('* -text\n*.docx binary\n*.pdf binary\n*.gz binary\n*.csv whitespace=cr-at-eol\n*/official/word-text/*.txt -whitespace\n','utf-8')
for p in O.rglob('*.md'):p.write_text(p.read_text('utf-8').rstrip()+'\n','utf-8')
# Normalize generated text only; preserve downloaded Word/PDF and Word text bytes.
for p in O.rglob('*'):
 if p.is_file() and p.name!='manifest.json' and 'word-text' not in p.parts and (p.suffix in ['.py','.json','.csv','.md','.html','.svg','.txt'] or p.name=='.gitattributes'):
  b=p.read_bytes();p.write_bytes(b.replace(b'\r\n',b'\n'))
records=[{'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
put(O/'manifest.json',{'algorithm':'sha256','retrieved_date':'2026-11-26','records':records})
print('packaged',len(records),'files',sum(r['bytes'] for r in records),'bytes')
