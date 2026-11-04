# 全校课表、大纲和方案来源快照

范围与计数见 [核对说明](../../../docs/全校课表与培养方案核对_20261031.md)。

- `official-sections.json.gz`：2025秋和2026春14,812个班次。数组字段依次为学期、lesson ID、班号、课程代码、课名、学分、开课院系、教师数组。
- `2026-autumn-sections.json.gz`：完整秋季索引仅作已有卡片和参考大纲的身份核验，不代表本轮全量收录该学期。
- `plans.json.gz`：429份方案；每行字段依次为代码、课名、开课院系、学分、模块内必修标记、计划学期、模块标题、模块层级、祖先模块约束路径。模块内必修还须结合祖先约束，不代表无条件全专业必修。
- `integration-report.full.json`：新增卡片/班次及大纲绑定、原响应SHA256、内嵌图片哈希。
- `existing-autumn-recheck.json`：已有秋季班次字段更新前后值。
- `course-coverage.csv`：9,509张卡片逐项列大纲、摘要、参考大纲、方案及学生评价状态。
- `verification.json`：独立全量关联检查结果。
- `baseline-course-categories.json`：之前7151张卡片的分类快照，供历史批次回归测试固定原有样本范围。新增样本由全校检查验证。

这些是仅保留课程信息的规范化快照，未包含账号、Cookie、学生名单或私人聊天原文。官方接口原响应哈希用于来源核查，不与脱敏HTML或gzip文件哈希混同。

运行 `npm test` 可验证全量课表和方案关联、大纲身份、图片哈希、无课评标记、方案课程检索及无损压缩加载。源码的课程目录需用 `scripts/read-catalog.cjs` 或 `scripts/catalog_io.py` 读取有序分片。

[离线大纲与方案课程模块包](https://github.com/pythonbug225/fudan-course-atlas/releases/tag/all-school-syllabi-20261031)。包内大纲保留完整课程正文，剔除联系方式及网页脚本；方案HTML是完整递归课程模块索引，不冒充包含所有毕业细则的正式附件。全校已有正式方案附件继续在对应课程资料区保留。
