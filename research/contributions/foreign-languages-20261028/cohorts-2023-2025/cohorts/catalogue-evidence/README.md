# 官方来源核查

采集日：2026-11-26。当前教务系统按年级与外院ID 2551筛选分别列出2023年5份、2024年14份、2025年23份方案；已与同年全校目录及外院全历史456条目录交叉核对。

- `directory-foreign-all-years.json`：未加年份的外院全部历史目录，用于检查年级筛选漏项；其他年份行不因此进入本次图谱。
- `directory-foreign-all-years-source.json`：目录请求URL和SHA-256。
- 各年 `official/raw/`：目录页原始响应与逐方案原始JSON gzip；`official/programmes.json`记录原件路径、时间及哈希。
- 2023/2024接口缺列部分专业，因此另以教务处整校原PDF补全；原PDF、外院摘页、适用视图及页码审计在各年 `official/`。
- [图片视觉核查](figure-review.md)：133个图片副本、73种去重图片；逐图记录、概念箭头及来源见 `figure-review.json`。
- `2024-handbook-guidance-review.json`：学院学习手册34—44页选课指导的审读结论，记录模块层级建议，未擅自扩写为逐课先修。

当前公开目录的缺项不代表该专业当年不存在。接口可能更新历史年级课号，故与当年出版PDF并列保存；同名不自动合并、不同适用人群不混为同一方案。
