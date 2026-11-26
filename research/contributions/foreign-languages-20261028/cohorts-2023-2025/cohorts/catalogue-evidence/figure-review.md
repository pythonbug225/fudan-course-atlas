# 官方 Word 内嵌图片核查

核查日期：2026-11-26。42份Word共133张内嵌图，按SHA-256去重为73种；全部完成视觉核查。12种包含知识技能箭头的课程体系图另看了原始分辨率图片。

2023、2024的19份Word仅含共同的“复旦大学”书法校名图；2025原件还含培养目标、学分要求、培养路径、分学期课程/技能体系。并非全部图片相同。

| 图片类别 | 去重图数 | 含重复副本图数 |
|---|---:|---:|
| university_wordmark | 1 | 42 |
| learning_objectives | 17 | 23 |
| degree_credit_requirements | 22 | 22 |
| degree_pathway_credit_diagram | 14 | 22 |
| semester_curriculum_table | 6 | 8 |
| semester_skills_diagram | 12 | 15 |
| programme_module_tree | 1 | 1 |

12种课程体系图中记录了47条箭头，例如“俄语语言基础 → 词汇/语法/阅读/会话”。这是官方图示的知识技能分解，没有逐课代码，也没有“先修通过后才可修读”的说明，因此未提升为课程先修边。培养路径图的箭头表示模块合成和学分路径，学期表则不因排列顺序自动产生先修。

逐图SHA、全部副本、来源方案、观察结论，以及47条概念箭头详见 [figure-review.json](figure-review.json)。JSON中的 `verified_course_prerequisite_edges: 0` 只表示这些图片没有提供可验证的逐课先修证据，不表示所有课程没有先修要求。
