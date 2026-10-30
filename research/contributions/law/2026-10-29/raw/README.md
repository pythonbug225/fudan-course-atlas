# 法学院原始采集数据（脱敏快照）

本目录补充2026-10-29法学院研究实际保存的接口响应与查询计划，不是模型生成的摘要。58份源文件以 `.json.gz` 存储；解压后仍是原接口／采集器的JSON结构，保留查询关联、结果ID、分页、时间和课程／教师元数据。身份字段、账号状态及受限正文经过下述处理，因此不是未处理的逐字节原件。

## 文件入口

| 路径 | 数据 |
| --- | --- |
| [树洞搜索响应](live/forum_search_results.json.gz) | 88,781个搜索候选；含已废弃分词查询的命中，不等于有效课评。 |
| [树洞查询台账](live/forum_search_ledger.json.gz) | 1,775个现行精确／称呼查询，加96个已废弃查询；含分页、状态、结果编号、URL。 |
| [树洞上下文响应](live/forum_context_results.json.gz) | 232个洞、11,460个楼层的采集快照与关联编号。 |
| [树洞上下文台账](live/forum_context_ledger.json.gz) | 每洞抓取状态、页码、命中楼层和停止位置。 |
| [课评搜索响应](live/danke_search_results.json.gz) | 1,133个课程组候选。 |
| [课评搜索台账](live/danke_search_ledger.json.gz) | 1,775个查询的执行结果。 |
| [课评详情响应](live/danke_details_results.json.gz) | 153个课程组、997个历史教学班及其课评关联；采集器详情中只有36篇评价，额外原文另见独立课程组快照。 |
| [课评详情台账](live/danke_details_ledger.json.gz) | 课程组／班级拉取与评价ID记录。 |
| `live/danke-group-*.json.gz` | 31份独立课程组响应，保留内嵌课评及year／semester原字段。 |
| `live/*probe.json.gz`、`live/danke-constitutional-frontier-reviews.json.gz` | 实际接口试读与宪法学前沿“有评计数但无可见正文”的响应。 |
| [现行查询计划](query-plans/) | 课程／教师全名、拼音、首字母、称呼、课号与关联候选；另留废弃初始分词查询及别名出处。 |
| [官方培养方案响应](official/programs/) | 2026级目录1份、8份培养方案详情响应。 |
| [官方课表响应](official/timetables/) | 2025秋174班、2026春195班的完整分页响应。 |
| [逐文件校验清单](manifest.json) | 采集文件、压缩文件、还原文件三组字节数／SHA-256及各文件处理计数。 |
| [摘要到来源编号对应](evidence-source-links.json) | 将既有223条证据记录关联到原始洞／楼／评价ID；当前教学班归属仍未确认。 |

不同响应可能含同一帖子或不同版本，合并共有99,329个楼层ID、116个课评ID。不能把候选数、对象数、快照数或已读数当作独立学生人数。

## 正文与署名

- 树洞正文仅公开既有核读证据明确引用的477个楼层ID中的469个；另8个命中敏感／受限标记，仅保留元数据和来源链接。其余候选正文以原因占位，未作为课程原文公开。上下文抓取成功不表示所有楼层已读或均与课程有关。
- 课评原文保留实际全文核读的71个评价ID（含排除项、异师和重复经历）；另45个未核读候选仅留元数据。逐篇 `public_body_status` 标明处理结果。71篇不是71篇目标学期、目标教师的有效评价。
- 保留原响应已有的匿名署名和来源URL；采集时未提供的署名不补造。`history`／旧修订正文、用户档案、提及账号、投票者状态、联系方式、凭据和分享口令等已移除或脱敏。同一ID的任一已存版本出现删除、折叠、敏感或禁止转载标记时，所有已存版本均不公开正文。
- 正文处理依据[旦挞社区服务使用协议](https://danxi.fduhole.com/doc/community-user-agreement)的内容版权条款：原创文本在无特别声明时按CC BY 4.0授权，作者特别声明优先。原文权利归原作者；官方资料及外部材料不因此自动改用该许可。保留来源并标示脱敏修改，缺失署名需回原站核查。
- 小红书、知乎和微信公众号站内检索仍未完成；本包没有这些平台的文章全文或截图，也不含浏览器诊断数据。图片未采集为可公开原文，未做OCR。

8份官方Word原件已在[原件资料包](https://github.com/pythonbug225/fudan-course-atlas/releases/download/law-research-20261029/law-programs-2026-originals.zip)保留，校验值见[原件索引](../official/programs.json)。原始响应和后续研究结论分别保存；查询命中不自动确认课程、教师、层次或学期对应。

## 校验与还原

从仓库根目录运行，只用Python标准库，无需登录或联网：

```shell
python research/contributions/law/2026-10-29/restore_raw.py
python research/contributions/law/2026-10-29/restore_raw.py --output data/source-snapshots/law-20261029
```

第一条只校验所有58份压缩／还原响应，第二条将脱敏JSON还原到指定目录。已有同名文件内容不同时会停止，不覆盖研究者原档。使用 `gzip.open(..., 'rt', encoding='utf-8')` 也可直接载入单个响应。

`manifest.json` 中 `captured_sha256` 对应本地采集文件，`restored_sha256` 对应公开脱敏JSON，`stored_sha256` 对应GitHub存储的gzip文件，三者用途不同。gzip采用固定mtime便于复现；不声称采集文件哈希就是网络响应字节哈希。

拥有原始采集工作区的维护者可运行 `export_raw.py --workspace <工作区>` 重建本目录。导出器使用仓库已有的脱敏函数，不发起任何新抓取。核读范围继续以[已读ID台账](../ledgers/fulltext-reading-ids.json)和[证据归属／排除](../ledgers/exclusions.json)为准。
