# 文物与博物馆学系原始数据发布版

本目录直接提交到既有院系分支 `research/wenbo-20261029`。文件保留在Git中，可克隆后离线读取。

| 原始资料 | 本目录内容 |
| --- | --- |
| 官方原始接口 | 11份方案目录、详情和两个学期教学班响应；`official/responses/` |
| 官方方案原件 | 7份DOCX，`official/programme-docx/`；逐字节一致 |
| 方案模块索引 | `official/programme-modules.json.gz`，明确为派生索引 |
| 蛋壳响应 | 452条搜索课程组、239个详情课程组、1363个历史班级、43条原评；`collected/danke_*` |
| 树洞响应 | 17956条命中及24洞313楼层的关联结构；课程证据原文来自175个去重楼层，其中174个正文公开，1个因源站敏感标记保留定位、隐去正文 |
| 查询与分页 | 树洞和蛋壳各892个查询词，保留返回ID、页数、状态；`query-plans/`与`ledgers/` |
| 人工判读原档 | `reading/`保留逐条采用、排除、未归属及全文/前缀筛查边界 |

[source-inventory.json](source-inventory.json)列出每个文件的原相对路径、来源URL、压缩前后字节数、SHA-256和脱敏计数。`.json.gz`使用标准gzip；解压后是UTF-8 JSON。官方接口与Word标记 `source_byte_identical=true`，按原始SHA-256核验；社区响应为必要脱敏后的原始数据发布版，不能把发布版哈希当作本地未脱敏缓存哈希。

## 读取方式

```python
import gzip, json
from pathlib import Path
root = Path("research/contributions/wenbo-20261029/raw")
with gzip.open(root / "collected/danke_details_results.json.gz", "rt", encoding="utf-8") as f:
    data = json.load(f)
```

树洞保留所有搜索命中ID和查询关系，但只有已归属的课程证据公开正文。无关、未采用、敏感、删除和限制转载正文保留 `archive_body_status`；缺失正文不代表没有命中。43条蛋壳原评含2条跨院系排除项，`research_adoption`注明采用边界。机器返回量、已读量、采用记录数和独立作者人数不同。

原始响应中带有正文的课程评价依据[旦挞社区协议](https://danxi.fduhole.com/doc/community-user-agreement)的默认CC BY 4.0条款处理；作者的另行声明优先。可用的公开匿名名、原站链接与修改说明保留。未公开内容及处理原因见[rights-and-exclusions.json](rights-and-exclusions.json)。未取得的小红书、知乎和公众号正文不存在于本地原档，因此没有这三类原始正文文件。
