# 数学科学学院2023—2025级培养方案与课程关系

[打开课程图谱与逐方案修读导读](课程图谱与修读导读.md)

已按教务公开目录的院系ID **2581** 逐项核对，取得 **36份官方Word原件**、方案JSON快照、课程表与每年级独立图谱。采集日：2026-11-26。

| 年级 | 方案原件 | 方案内课程/科研条目（代码去重） | 仅公共候选 | 手册准备参考关系 | 图谱 |
| --- | ---: | ---: | ---: | ---: | --- |
| 2023 | 7 | 212 | 0 | 33 | [原件与说明](2023/README.md) · [交互图谱](2023/course-graph/index.html) · [课程关系](2023/course-graph/learning-paths.md) |
| 2024 | 11 | 246 | 0 | 50 | [原件与说明](2024/README.md) · [交互图谱](2024/course-graph/index.html) · [课程关系](2024/course-graph/learning-paths.md) |
| 2025 | 18 | 261 | 116 | 37 | [原件与说明](2025/README.md) · [交互图谱](2025/course-graph/index.html) · [课程关系](2025/course-graph/learning-paths.md) |

统计按各年级具体模块收录计算：包含课程表明确列出的部分通识课程、专业课程及科研条目，不是狭义数学专业课数，也不是个人必修课数。仅由引用公共目录展开的候选另列。

## 阅读入口

- [数学科学学院课程名单](数学科学学院课程名单.txt)：三个年级方案明确列出的课程与科研条目的去重课程名，文件只含名称。
- [逐年目录对照](cohort-comparison.md)及[机器可读对照](cohort-comparison.json)。
- [2024版学习指导手册原件](sources/math-handbook-2024.pdf)及[68份完整大纲的基本要求摘录](sources/handbook-course-requirements.json)。
- [官方内嵌图定位](sources/figure-audit.json)、[覆盖统计](coverage.json)、[校验结果](validation.json)、[SHA-256清单](manifest.json)。

## 版本和先修含义

本任务覆盖数学与应用数学、信息与计算科学的普通、英才、强基、相辉、留学生、港澳台侨及双学位/贯通版本，以各年实际公开目录为准；没有将各方案的课程拼成单个人的必修清单。公共引用模块若未展开，保留其模块规则及缺口，不从其他年级补造课程。

图谱关系分别记录：同一方案数字学期在先、2024版手册的知识准备参考、编辑建议、内容联系、同名异号、模块收录。所有关系都保留依据。手册明确预修表述与知识背景均可核对页码，但旧代码与当前代码只按题名作参考，不能据此确认代码替代、学分互认或其他年级的强制规则；当前尚未核实到本年级选课系统执行的硬性先修条款。宽泛的“数学分析”“高等代数”“点集拓扑”等未强行展开成当前若干课程的必修链。

2025年部分方案另附官方课程体系、学分结构和科研训练路线图，已从Word字节无改动提取并提供图集；这些图的系列/阶段关系不直接认定为硬性先修。各年级图谱默认显示方案内课程与科研条目，支持方案筛选、关键词搜索、关系类型筛选和SVG导出。HTML需下载后打开；GitHub页面直接阅读README、SVG和关系表。

## 原始数据与复现

`YYYY/official/word-originals/`是官方Word下载字节；`raw/*.json.gz`是公开目录与详情响应的JSON规范化快照。课程行、模块规则、必修字段、terms/suggestTerms以及JSON Pointer均保留。方案为采集日系统当前版本，可能经历后续修订，不能称为入学当年未修订发布版。手册保留版本年份和大纲内部日期。

官方来源：[培养方案公开检索](https://fdjwgl.fudan.edu.cn/manager/bizType/2/page-center/major-program-search-view?skipAuth=1)；[2024版数学手册](https://jwc.fudan.edu.cn/_upload/article/files/d4/56/707002a8413b8a3cc690244c1118/5f39341f-9c23-496e-807b-cc7ae77cd970.pdf)。未使用个人认证或个人教务数据。原件权利归原权利人；公开可访问不等于取得单独再利用许可。

复现（Python 3；重新抽取PDF时需要PyMuPDF）：

```sh
python build_cohorts.py
python finalize_package.py
python validate_cohorts.py
python finalize_package.py --manifest-only
python validate_cohorts.py --check
```

在线重新下载可运行`fetch_official.py`，它会覆盖源快照；无需登录。关系编辑配方见`curation.json`及`curate_handbook.py`。本次已完成原件CRC/哈希、JSON来源定位、方案内学期顺序、路径、离线重建、CSV/SVG/HTML结构和JavaScript语法核验；未完成浏览器交互验收。
