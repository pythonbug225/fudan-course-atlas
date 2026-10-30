# 历史学系原始采集数据（脱敏发布版）

本目录与研究报告位于同一历史学系研究分支。数据直接导出自此前保存的采集缓存，没有从课程总结反向生成；2026-10-30为发布日，不是重新抓取日。

| 目录 | 内容 |
| --- | --- |
| `official/responses/` | 7份教务公开接口响应：4份方案详情、1份方案目录、2份学期教学班返回；解压后与采集文件逐字节一致 |
| `official/word-originals/` | 4份2026级培养方案DOCX原件，逐字节保留 |
| `live/` | 树洞及课评区的搜索、详情、上下文对象与执行台账，共8份JSON |
| `query-plans/` | 两个平台各1341项实际查询计划，以及目标课程和教师关联 |
| `reading-ledgers/` | 人工核读、采用、排除、待核、归属冲突及质量复核记录；属于研究台账 |
| `research-intermediates/` | 此前保存的候选队列、映射说明、别名依据及中间统计；不等于最终采用关系 |
| `public-search-observations/` | 小红书、知乎、微信公众号的实际查询／查阅记录、规范链接与摘要；不是原始网页全文 |

共64份压缩JSON，包含37,309个不同树洞搜索楼层、47帖的1,086个已取得上下文楼层、701个课评搜索课程组，以及398组详情中的1,005个课程对象和159篇课评。统计是采集对象数，不是独立修读人数，也不表示所有命中已经人工核读。

## 读取与校验

全部JSON使用标准gzip压缩，数据文件直接纳入本分支，无需下载外部Release。克隆本分支后，在本目录运行：

```shell
python restore_raw.py
python restore_raw.py --output restored
```

第一条逐文件核对压缩内容和解压后内容的字节数、SHA-256及JSON格式；第二条同时还原JSON和Word原件到一个新的目录。也可直接读取单个文件：

```python
import gzip, json
with gzip.open("live/danke_details_results.json.gz", "rt", encoding="utf-8") as f:
    data = json.load(f)
print(len(data["reviews"]))
```

[manifest.json](manifest.json)记录每份采集文件与发布文件的大小及哈希、保存路径、处理计数、Word原件及未发布文件原因。`byte_identical_to_capture=true`表示解压后与采集文件逐字节一致；其他JSON经过脱敏、格式规范化或发布状态标注，不称为未经修改的HTTP响应。

## 原始关联与正文范围

树洞用楼层对象`id`连接搜索命中及上下文，帖子关联用`hole_id`，`query_ids`回查查询计划。课评通过`review.course_ids → courses[id].data`核对真实课程、教师及学期；聚合字段`course_codes`只表示检索候选关联。`year`是学年，`semester=3`为下一日历年的春季，2026春对应2025/3。

全部搜索命中保留对象ID、候选与查询关联。正文仅在已核读且明确涉及课程的话题及其已采集上下文内公开；不确定课程相关性的命中、已删除／折叠／敏感标记及明确限制转载的正文用`public_body_status`或`archive_body_status`标注。未发布正文不代表原站空帖。具体公开楼层ID及对象实例计数见清单；不要把重复快照当作独立评价。

账号密码、会话凭证、个人身份关联和联系方式已移除。来源地址与原先取得的匿名署名保留；未取得的署名不补造。旦挞原创文本的默认许可依据为[社区服务使用协议](https://danxi.fduhole.com/doc/community-user-agreement)中的CC BY 4.0条款，2026-10-30核查；作者另有声明时遵从其声明。第三方引用、官方文件和外部平台内容保留各自权利。未经授权的小红书图片及外部文章全文未发布，未恢复任何被删内容。

重新导出时，可在包含采集缓存的工作区执行 `export_raw.py --source-dir <历史学系采集目录> --report-dir <原报告目录> --repo-dir <本仓库目录> --output-dir <新的输出目录>`。此脚本仅处理指定的本地文件，不访问网络或账号配置。
