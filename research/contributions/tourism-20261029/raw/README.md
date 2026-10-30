# 旅游学系采集原始数据（脱敏发布版）

这是2026-10-29研究时保存的接口对象与执行台账，2026-10-30补充发布；正文直接来自采集缓存，没有从总结反向生成。

| 文件 | 内容 |
| --- | --- |
| `forum_search_results.json.gz` | 530条有效树洞查询合并后的12,235个楼层对象，保留ID、原始字段和查询关联；正文公开范围见下文 |
| `forum_context_results.json.gz` | 已取得的59洞、2,393楼上下文对象与关系；公开正文边界同上 |
| `forum_search_ledger.json.gz` / `forum_context_ledger.json.gz` | 查询词、课程候选、来源地址、页数、返回ID、停止/错误状态 |
| `danke_search_results.json.gz` | 课评区检索返回的327个课程组对象 |
| `danke_details_results.json.gz` | 155课程组、282教学课程元数据及5篇匹配目标课程和教师的完整原评正文 |
| `danke_search_ledger.json.gz` / `danke_details_ledger.json.gz` | 课评区查询与详情选择执行记录 |
| `course-groups/` | 11份补查的课程组接口快照，包含其原始课程/教师版本及返回评价，不等于全部都适用于旅游学系目标班 |
| `query-plans/` | 树洞、课评各530条实际查询计划；全名、课号、拼音、首字母和已观察简称的映射 |
| `reading-ledgers/` | 核读、排除、待核与别名注释；这些是研究台账，与原始接口对象区分 |
| [manifest.json](manifest.json) | 逐文件源哈希、发布哈希、解压哈希、脱敏计数及统计 |

官方原始接口、培养方案DOCX、课表已在[官方资料](../官方资料/README.md)随前次提交提供。

## 树洞正文公开范围

关键词命中中含同名异课及个人生活内容，不能整批当作课程评价转载。本包保留有效命中和已采集上下文的对象ID及分页关联，公开已核读的课程相关原文与必要上下文，共537个去重楼层；未核实课程相关性及无关个人内容的正文用 `_publication_body_status` 标记未公开。被标记的正文不是原站空帖，也不表示已经排除全部研究价值。

原有632楼核读计数包含排除项，不等于本包公开正文数；实际公开ID列表见清单。误生成的单字母 `s` 查询独占对象不纳入有效命中，查询错误本身另存[排除记录](excluded-queries.json)。

账号密码、会话字段、个人联系方式、签名参数已处理；已删除或明确限制转载的正文不发布，公开署名按原接口保留。JSON有必要脱敏及格式规范化，因此是采集原始数据的发布版，不称为逐字节未改动的HTTP响应。未新增抓取或恢复已删内容。

## 读取方法

所有`.json.gz`均为标准gzip压缩的UTF-8 JSON，可直接用Python标准库读取：

```python
import gzip, json
with gzip.open("raw/danke_details_results.json.gz", "rt", encoding="utf-8") as f:
    data = json.load(f)
print(data["reviews"].keys())
```

`items`为搜索合并结果；详情与上下文按`groups/courses/reviews`和`holes/floors`索引。抓取、核读、采用是不同状态，来源与学期归属以原始字段和核读台账共同判断。图片与小红书、知乎、公众号全文不包含在本包；这轮登录态站内检索仍未完成。
