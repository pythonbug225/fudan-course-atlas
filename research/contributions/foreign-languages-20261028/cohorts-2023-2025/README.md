# 外国语言文学学院：2023—2025级培养方案与课程关系图谱

下载本目录后打开 [index.html](index.html)，可离线按入学年级、培养方案、课程名称或课号检索，查看课程顺序、模块归属与内容主题，并打开对应证据。GitHub文件预览不执行HTML，请下载后在浏览器打开。2026级资料仍在父目录原位置。

## 本次覆盖

| 年级 | 接口方案原件 | PDF适用视图 | 课程代码节点 | 其他培养环节 | 推断学习顺序 |
|---|---:|---:|---:|---:|---:|
| [2023 级](cohorts/2023/course-graph/README.md) | 5 | 16 | 506 | 0 | 103 |
| [2024 级](cohorts/2024/course-graph/README.md) | 14 | 24 | 662 | 0 | 135 |
| [2025 级](cohorts/2025/course-graph/README.md) | 23 | 0 | 405 | 10 | 70 |

数量按来源中的课程代码统计，不等于实际开课门数或去重后的课程实体。同名新旧代码独立保留；同一代码的标点和题名变体保留。PDF适用视图是专业方案或留学生修读建议的整理记录，不是新增教务系统方案，也不应与接口方案相加作为不同专业数量。2025的10个非课程培养环节单独标记。

采集日为2026-11-26。42份教务系统方案均保存官方Word、原始JSON gzip、原文文本与内嵌图片；年级全校目录、年级外院目录、外院全历史目录三路校验一致。接口当前仅列2023年5份、2024年14份，故另下载教务处2023/2024整校培养方案PDF，并整理完整外院章节，保留一般与留学生适用范围。2024覆盖8个常规专业、4个复语试验班、4个外语与计算机双学位项目的原版方案。

2023/2024完整官方PDF及外院原页摘录、公共课程参考章节均入库。公共参考章中的全校可选课程没有一概加入外院必修图谱；原表没有具体课号的课程组和学分要求另存。2025覆盖当前公开接口的23份外院方案，未取得需要登录的独立公共培养方案接口，不能将专业方案图谱当成完整毕业资格审核。

## 文件入口

- [2023官方原件及索引](cohorts/2023/official/README.md) · [完整原PDF](cohorts/2023/official/full-curriculum-2023-original.pdf) · [外院章节](cohorts/2023/official/handbook-excerpt.pdf)
- [2024官方原件及索引](cohorts/2024/official/README.md) · [完整原PDF](cohorts/2024/official/full-curriculum-2024-original.pdf) · [外院章节](cohorts/2024/official/handbook-excerpt.pdf) · [学院学习手册](cohorts/2024/official/student-handbook-2024.pdf)
- [2025官方原件及索引](cohorts/2025/official/README.md)
- 各年 `data/program-course-index.json` 与CSV保留方案、模块、学分、修读信息及证据指针；`course-graph/graph.json`、`nodes.csv`、`edges.csv`供后续检索和图数据库使用。
- 各年 `data/course-names.txt` 只含名称；父目录的外院名称清单也已增补本次官方资料中的外院课程。
- [官方目录核查](cohorts/catalogue-evidence/README.md) · [133张原图核查](cohorts/catalogue-evidence/figure-review.md) · [验证报告](validation-report.json)

## 先修与内容联系的证据口径

本批未核实任何具体课程对的官方强制先修或官方建议先修。JSON中缺失或为空的先修字段不证明课程没有先修，逐年字段与文本审计在 `data/prerequisite-audit.json`。所有建议顺序均来自同一方案内明确同系列的编号或上中下名称，只作为学习线索。

42份Word中的133张图片按SHA去重为73种并已视觉核读。原件课程体系图中的47条知识/技能箭头以概念层次记录，不等同课程代码之间的先修。2024学院学习手册第36页有翻译专业先完成核心课程再选进阶课程的模块层级建议，未将它展开成全部课程两两先修；审读记录在 `cohorts/catalogue-evidence/2024-handbook-guidance-review.json`。

官方模块归属表示课程在某一方案中如何归类；主题联系来自课程名称关键词，尚未逐课取得教学大纲。它们都不代表两门课内容完全相同。无连线表示本批未建立证据充分的关系。各年级、普通/留学生、复语与双学位方案分开筛选，不能将不同适用范围混用。

接口数据是采集日仍公开的历史年级版本，课号/要求可能已更新；PDF是当年出版版本。两者并列留存，不凭同名推定等价、学分互认或制度变更。

## 来源与复现

主要来源：[教务系统培养方案查询](https://fdjwgl.fudan.edu.cn/manager/bizType/2/page-center/major-program-search-view?skipAuth=1)、[教务处各年级培养方案原件](https://jwc.fudan.edu.cn/0a/ae/c25336a461486/page.htm)。逐文件来源、检索时间和SHA-256见各年 `official/programmes.json`、`official/metadata/` 及PDF来源审计；`file-manifest.json`覆盖本资料包文件。官方文件权利归原发布方，摘页保留原版页面，整理数据不冒充学校发布的新方案。

在本目录运行（Python 3标准库）：

```sh
python scripts/build_graphs.py
python scripts/build_viewer.py
python scripts/test_graph_rules.py
python scripts/validate.py
```

下载脚本和原件完整性校验位于 `cohorts/scripts/`。验证检查42份原始响应与Word、课程代码全覆盖、证据指针、CSV导出和4个HTML嵌入数据一致性；源码测试覆盖上下/上中下系列、跨方案隔离和重复虚拟模块编号。
