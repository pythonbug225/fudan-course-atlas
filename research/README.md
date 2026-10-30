# 原始抓取快照与协作台账

## 新增院系研究

- [法学院：2026级8份培养方案与2025秋／2026春369教学班研究](contributions/law/2026-10-29/README.md)：260课号、223条关联摘要；[原始接口响应与查询计划](contributions/law/2026-10-29/raw/README.md)另存58份可还原脱敏快照。完整离线包、原始快照下载包和Word原件见资料Release。

这里保存来源目录、协作任务、别名和公开数据包索引。它服务于“全校所有专业课评库”的多人整理；目前课程清单仍是既有1273个条目、1269个唯一课程代码，新增学院需要补官方清单。完整方法和所有来源类别见[主README](../README.md#来源总表之前使用及提出过的入口)。

## 本版数据清单

截至2026-10-27，本版公开 14,613 个来源快照，压缩数据约 178.5 MiB，另附源文件索引和校验表。此数量是文件快照数，不是课评篇数或已读数。

| 类别 | 来源快照数 |
| --- | ---: |
| `research-ledgers` | 153 |
| `treehole` | 5,403 |
| `source-documents` | 54 |
| `external-web` | 36 |
| `danke` | 4,848 |
| `official-rules` | 18 |
| `official-outlines` | 3,290 |
| `official-summer` | 92 |
| `official-enrollment` | 7 |
| `official-programs-and-outlines` | 712 |

对象库含491,478个树洞帖子对象版本、6,177个蛋壳对象版本；同楼层的字段或正文不同可形成多个版本，不能当作独立作者或独立评价人数。原档未提供的署名不补造，引用全文时还需核对原站可提供的署名及作者声明。

一份早期 `forum/searches.jsonl` 有5行损坏数据：恢复了其余917行，损坏行只记行号、长度与哈希，不公开无法安全解析的正文。对应源文件索引带 `integrity.status=partial_jsonl_recovery` 说明。

按内容与来源处理而未公开的本地文件：54份私密群聊派生包、159份未获全文转载许可的外部正文／截图；另有27份生成基线因重复而不打包。私密六群原档本就不是爬取快照，不在这个文件数量中。

## 下载与定位

- [原始数据Release：raw-snapshots-20261027](https://github.com/pythonbug225/fudan-course-atlas/releases/tag/raw-snapshots-20261027)
- [分包清单、大小与SHA-256](raw-release-manifest.json)
- [逐个源文件的索引](source-inventory.jsonl)
- [课程任务表](course-tasks.csv)：负责人和复核人初始留空，请在Issue／PR里认领。
- [名称规范化问题](data-quality.json)：4组同代码名称变体，协作任务合并认领，网站原数据未在本次文档更新中改动。
- [教师别名候选表](teacher-aliases.json)：历史候选，不是简称与身份的一对一证明。
- [外部文章及笔记对应](external-sources.json)、[网站与工具登记表](sources.json)
- [单课整理模板](templates/course-review.json)

仅运行Python标准库即可下载，不需要树洞／教务账号：

```shell
python scripts/research/fetch_raw_archive.py
python scripts/research/fetch_raw_archive.py --category treehole --materialize
python scripts/research/fetch_raw_archive.py --verify-only
# 可选：只还原某个相对路径命中的快照
python scripts/research/fetch_raw_archive.py --category treehole --source-match /forum/hole_680017.json --materialize
```

默认下载到仓库中被忽略的 `data/source-snapshots/`。第二条会把树洞的脱敏快照恢复到该目录的 `snapshots/`，保留既往工作区内的相对来源路径；不会覆盖研究者自己的原档。需要其他来源时，多次使用 `--category`；可选类别以发布清单为准。

## 数据包结构

| 类别 | 含义 |
| --- | --- |
| `treehole` | 多轮普通帖搜索响应、整串楼层快照、直接楼层响应及早期数院推免专题的搜索数据；专题数据不自动计入课程评价。 |
| `danke` | 蛋壳课程组搜索、课程组与各教学班课评快照，包括补充署名的版本。 |
| `official-outlines` | 已保存的教务教学班索引和大纲接口响应。 |
| `official-programs-and-outlines` | 计智学院培养方案、公共方案、开课表、大纲及错误／排除记录。 |
| `official-enrollment` | 往期教学班人数与容量的接口汇总；原工作目录虽含 `private` 字样，导出的只是脱敏后的课程／班级汇总，不含个人选课。 |
| `official-summer` | 暑期课程、大纲、认定和开课状态资料。 |
| `official-rules` | 既往取得的教务规则页面与记录；HTML已去脚本和输入框。 |
| `source-documents` | 用户提供培养方案、开课表等材料的结构化或文字提取版本。 |
| `external-web` | 知乎、小红书、公众号、博客等的来源、规范链接和整理台账；不包含未获许可的文章全文／截图。 |
| `research-ledgers` | 查询批次、候选和阅读／采用／排除台账、覆盖与待查位置。标题含“候选”不代表已采用，早期字段也可能不齐。 |

每个 `*-NNN.zip` 中的 `blobs/` 按发布版内容哈希命名。大量搜索命中会重复同一个楼层；为控制体积，树洞与蛋壳的帖子对象存入各自 `*-objects.jsonl.gz`，查询快照只存 `{"$raw_object":"哈希"}` 引用。不同正文／元数据版本保留不同哈希，不把历史版本互相覆盖。下载脚本的 `--materialize` 会还原这些引用，并核对还原后SHA-256。

同一文件的索引字段：

| 字段 | 含义 |
| --- | --- |
| `source_path` | 原工作区内的相对路径，用于对应批次和既往脚本；不是账号路径。 |
| `original_sha256`、`original_bytes` | 本地原始文件的校验值和大小。 |
| `archive`、`member`、`stored_sha256` | Release分包、包内位置和实际存储版校验值。 |
| `sha256`、`bytes` | 还原对象引用后的脱敏抓取响应校验值和大小；这是恢复文件应匹配的值。 |
| `encoding` | `plain`表示直接内容，`object-refs-v1`表示需还原共享帖子对象。 |
| `redactions` | 删除凭证／身份字段、联系方式、分享码、受限正文等处理计数。 |
| `published`、`status` | 是否公开及未公开原因。 |
| `read_status` | 一律提醒“抓取不等于阅读”；真正阅读和采用情况以各批台账及提交记录为准。 |

JSON/JSONL做过格式规范化与必要脱敏，因此不等于逐字节原件。未公开文件在索引中只记相对类别／路径和原因；不把私人原档哈希、聊天身份或凭证塞进清单。外部版权内容的公开记录只能用于追溯来源，不能据此认定全文转载权。

## 已知未完成位置

树洞既有宽泛模糊查询有到达分页上限的情况，未宣称穷尽。续查先看查询快照里的 `coverage.stop`、offset和时间窗口，再按学期或月份细分。计智学院批次中的 `forum_no_teacher_part2_integrated.json` 保留未完成复核状态，不能把空 `records` 当作“没有课评”；part3仍有待补整串上下文的候选。已经抓到但没读完的队列、作者限制转载及接口返回错误都保留原状态。

六个群聊原档、原始上下文包、身份与回复图不公开。经过审核的必要匿名摘要已经在网站 `public/data/review-supplement.json` 中；不为了填满条目而发布无关闲聊。新协作者如自行获得群资料，应先在本地整理、核对授权与脱敏，再提交课程记录。

知乎／小红书／公众号的网页存档和截图可能含未授权全文及浏览器侧个人信息，故只公开来源索引、已经整理的摘要和规范链接。读不到正文的搜索卡片记为线索。既往PDF、数学试卷、手册和培养方案的可公开原件已在[参考资料Release](https://github.com/pythonbug225/fudan-course-atlas/releases)中保留，本次避免重复大文件。

## 新增数据与复核

1. 用单课模板先写归属：课程代码＋学期＋教师＋班型；来源没说教师时保留空，不靠首字母强行匹配。
2. 查询日志记录别名、精确／模糊、时间、页码和停止原因；已读清单记录洞号楼层、课评ID、图文页码。
3. 采用、排除、重复与待确认各有原因。转发同一经历、蛋壳指向树洞同楼层、同作者跨平台复述不重复计作多人经验。
4. 完成大纲、资料、课评与讨论、对比和总结四部分，保留各教师差异。没有学生评价的课明示缺项，不能用大纲／报道冒充评价。
5. 复核人确认事实、来源与匿名处理；维护者合并课程数据并重建检索索引后，再独立发布网站。

维护者可在具有原工作区的本地重新构建快照，脚本只处理本地文件，不发起新爬取：

```shell
python scripts/research/build_raw_archive.py --workspace 本地工作区 --output 本地输出目录
python tests/research-export.test.py
```

只在预先审查过的源目录上使用导出器；通用脱敏规则不能代替人工确认原始数据类型和第三方许可。严禁把工作区整体压缩上传，或将 `.env`、Cookie、统一认证／树洞凭证、私钥、浏览器配置及个人教务信息加入数据包。
