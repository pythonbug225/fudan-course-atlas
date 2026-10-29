# 法学院：2026级培养方案与2025秋／2026春课程研究

本批提供法学院官方范围、来源摘要和核读台账，供复核后合入复旦选课地图。已有课程网站数据尚未导入本批贡献。

- 官方资料：2026级培养方案8份，含临时版、普通本科、涉外本科／本硕融通、法学经济学双学位、法学人工智能双学位、留学生及港澳台侨生版本。原件8/8核验通过。
- 官方开课：2025秋174班、2026春195班，共369教学班、260课程代码、124教师；本科136班、研究生216班、本研融通17班。
- 检索：树洞1772个查询完成、3个宽泛词触及分页上限；课评区1775个查询完成。课程／教师全名、拼音、首字母与已观察称呼保留在查询表中。
- 全文范围：6779个去重树洞楼层的可见文字、71篇去重课评正文，包含排除项；不是有效课评数或独立学生人数。
- 中央摘要：223条关联材料。`course_codes`仅是查找候选，`confirmed_section_keys`均为空；未确认源班层次或教师的材料不能当成当前班评价。

## 阅读入口

- [课程名称清单](course-list.md)；[逐课贡献文件](courses/)（260个文件，参照仓库单课模板扩展为多学期／多教学班）。
- [官方369班](official/sections.json)；[完整课程表CSV](official/timetable.csv)；[8份培养方案索引](official/programs.json)；[原件核验](official/program-verification.json)。
- [中央证据摘要](summaries/evidence.json)；[范围统计](summaries/statistics.json)；[全文核读ID](ledgers/fulltext-reading-ids.json)；[采用／排除说明](ledgers/exclusions.json)。
- [3550条检索执行记录](ledgers/search-queries.json)；[课程与教师检索变体](ledgers/search-variants.json)。
- [完整离线报告与官方资料包](https://github.com/pythonbug225/fudan-course-atlas/releases/download/law-research-20261029/law-research-20261029.zip)：解压后打开index.html，可按课程、教师、层次与学期筛选；同时含官方原件和公开原始接口响应。
- [8份官方Word原件](https://github.com/pythonbug225/fudan-course-atlas/releases/download/law-research-20261029/law-programs-2026-originals.zip)；[Release与SHA-256索引](release-assets.json)。大体积原件及完整离线包放资料Release，Git只存贡献与索引。

## 使用边界

小红书、知乎、微信公众号的登录态站内检索因Edge页面控制失败而尚未完成，不能称为全平台全部讨论。树洞`qq`、`d`、`🐟哥`各触及100页／10000条上限，词义过宽，不用于认定教师。

历史评价、异师、同名跨本科／研究生、未确定标准班／H班等情况逐条注明。API原始year／semester和正文自述修读期分开保存；不从发布日期自动推定学期。课程卡中的关联材料不是已经确认适用的班级评价；没有关联摘要也不等于没有评价。

长洞有的只读命中楼层及直接上下文，精确已读ID另列；图片未OCR，删除或隐藏原文无法复原。宪法学前沿组5859显示1条评价，但可见接口正文为空，保留可见性差异。

仅发布必要匿名摘要、公开官方资料、规范链接和来源编号；不提交账号、凭据、浏览器数据、私密群聊、无关树洞全文或未获转载许可的外部文章全文。第三方来源许可未核实处不补造开放许可。

## 校验

在本目录运行 `python validate.py`。校验260课程／369班／8方案、官方教学班联合键、摘要引用、查询状态、6779／71个全文ID及逐文件SHA-256。本站应用运行数据、计算工具与部署文件均不在这批变更范围中。
