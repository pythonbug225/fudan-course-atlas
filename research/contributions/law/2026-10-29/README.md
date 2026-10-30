# 法学院：2026级培养方案与2025秋／2026春课程研究

本批提供法学院官方范围、原始采集快照、来源摘要和核读台账，供复核后合入复旦选课地图。已有课程网站数据尚未导入本批贡献。

- 官方资料：2026级培养方案8份，含临时版、普通本科、涉外本科／本硕融通、法学经济学双学位、法学人工智能双学位、留学生及港澳台侨生版本。原件8/8核验通过。
- 官方开课：2025秋174班、2026春195班，共369教学班、260课程代码、124教师；本科136班、研究生216班、本研融通17班。
- 检索：树洞1772个查询完成、3个宽泛词触及分页上限；课评区1775个查询完成。课程／教师全名、拼音、首字母与已观察称呼保留在查询表中。
- 全文范围：6779个去重树洞楼层的可见文字、71篇去重课评正文，包含排除项；不是有效课评数或独立学生人数。
- 中央摘要：223条关联材料。`course_codes`仅是查找候选，`confirmed_section_keys`均为空；未确认源班层次或教师的材料不能当成当前班评价。

## 阅读入口

- [原始采集数据](raw/README.md)（58份脱敏接口响应／查询计划，gzip压缩JSON，保留结果与分页）；[逐文件SHA-256](raw/manifest.json)；[摘要到原始ID对应](raw/evidence-source-links.json)。原始响应与下列整理结果分开保存。
- [下载原始数据包](https://github.com/pythonbug225/fudan-course-atlas/releases/download/law-research-20261029/law-raw-snapshots-20261030.zip)：包含同一套58份响应、校验清单与离线还原脚本；2026-10-30补充。
- [法学院课程名单](法学院课程名单.txt)（仅课程名称，每行一个，按名称去重共244项）；[详细课程目录](course-list.md)；[逐课贡献文件](courses/)（260个文件，参照仓库单课模板扩展为多学期／多教学班）。
- [官方369班](official/sections.json)；[完整课程表CSV](official/timetable.csv)；[8份培养方案索引](official/programs.json)；[原件核验](official/program-verification.json)。
- [中央证据摘要](summaries/evidence.json)；[范围统计](summaries/statistics.json)；[全文核读ID](ledgers/fulltext-reading-ids.json)；[采用／排除说明](ledgers/exclusions.json)。
- [3550条检索执行记录](ledgers/search-queries.json)；[课程与教师检索变体](ledgers/search-variants.json)。
- [完整离线报告与官方资料包](https://github.com/pythonbug225/fudan-course-atlas/releases/download/law-research-20261029/law-research-20261029.zip)：解压后打开index.html，可按课程、教师、层次与学期筛选；同时含官方原件和公开原始接口响应。
- [8份官方Word原件](https://github.com/pythonbug225/fudan-course-atlas/releases/download/law-research-20261029/law-programs-2026-originals.zip)；[Release与SHA-256索引](release-assets.json)。大体积原件及完整离线包放资料Release，Git只存贡献与索引。

## 使用边界

小红书、知乎、微信公众号的登录态站内检索因Edge页面控制失败而尚未完成，不能称为全平台全部讨论。树洞`qq`、`d`、`🐟哥`各触及100页／10000条上限，词义过宽，不用于认定教师。

历史评价、异师、同名跨本科／研究生、未确定标准班／H班等情况逐条注明。API原始year／semester和正文自述修读期分开保存；不从发布日期自动推定学期。课程卡中的关联材料不是已经确认适用的班级评价；没有关联摘要也不等于没有评价。

长洞有的只读命中楼层及直接上下文，精确已读ID另列；图片未OCR，删除或隐藏原文无法复原。宪法学前沿组5859显示1条评价，但可见接口正文为空，保留可见性差异。

原始快照保留477个已核读课程证据楼层中的469个正文、71篇已读课评正文（包含排除项）；敏感／受限楼层及未核读、未选入课程证据的候选正文以原因占位。采集快照不是未处理的逐字节原件；处理规则及来源许可见[原始数据说明](raw/README.md)。不提交账号、凭据、浏览器数据、私密群聊、无关树洞全文或未获转载许可的外部文章全文。

## 校验

在本目录运行 `python validate.py` 和 `python restore_raw.py`。前者校验260课程／369班／8方案、官方教学班联合键、摘要引用、查询状态、6779／71个全文ID及逐文件SHA-256；后者校验58份压缩响应及还原内容。`python test_raw.py` 检查正文边界、字段脱敏、保留原始关联和安全还原。本站应用运行数据、计算工具与部署文件均不在这批变更范围中。
