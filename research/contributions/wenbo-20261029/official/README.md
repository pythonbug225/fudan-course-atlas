# 复旦大学文物与博物馆学系官方方案与实际教学班

获取时间（上海时区）：2026-10-29T22:10:05+08:00

## 培养方案

- 教务系统2026级全校目录共428条，单页返回数与总数一致；按文物与博物馆学系院系ID 2569 筛选，共7条培养方案。清单含文博学、考古学本科及本博融通方案，以及留学生、港澳台等适用对象方案。
- 对每条方案下载详情JSON和官方Word原件，逐一校验详情ID、年级、院系归属；Word校验ZIP完整性、主文档XML可解析及正文身份。原始Word导出接口未提供PDF。
- 课程索引和课程模块保留培养方案计划课程、模块说明和建议学期。`course_catalog`按课程代码匹配2026系内方案，并标记方案名、模块与建议学期；该匹配只表示计划中出现同一课程代码，不代表当前教学班仅面向该方案。

## 实际教学班

- 接口过滤：`openDepartmentAssocs=2569`；2025秋学期ID 504，2026春学期ID 505。数据分页逐页抓取，并核对接口总数、页数、重复教学班ID以及每条记录开课院系。
- 共157条实际教学班（2025秋84、2026春73），按学期+课程代码聚合为135行、133个课程代码。`课程教学班`保留每个班的教师、班号、ID、排课文本、选课人数等；`course_catalog`汇总班号、教师和官方课程类别。
- 原始记录中的`开课业务类型`（本科/研究生）、`课程类别`和`课程表类别`按教务系统字段原样保留。按官方字段“通识教育”统计，2025秋有13个通识教育教学班、2026春有12个；摘要还列出本科/研究生班数，以及与2026系内方案同课程代码的当前教学班数。通识与专业类别以官方类别值为准。

## 来源接口

- 全校方案目录：`https://fdjwgl.fudan.edu.cn/manager/bizType/2/page-center/major-program-search-view/search?skipAuth=1&YEARS=2026&queryPage__=1,1000`
- 院系方案目录：`https://fdjwgl.fudan.edu.cn/manager/bizType/2/page-center/major-program-search-view/search?skipAuth=1&YEARS=2026&DEPART_IDS=2569&queryPage__=1,500`
- 方案详情：`https://fdjwgl.fudan.edu.cn/manager/bizType/2/major-program-search/info/{id}?skipAuth=1`
- Word导出：`https://fdjwgl.fudan.edu.cn/manager/bizType/2/major-program-search/export-word`，POST表单参数`ids=<方案编号>`
- 教学班：`https://fdjwgl.fudan.edu.cn/student/for-all/lesson-search/semester/{sid}/search/{sid}?openDepartmentAssocs=2569&queryPage__={page},500`

原始JSON、方案Word、SHA256、计数与接口分页数据均随附；仅使用公开接口，未使用账号凭证或登录态。


Git目录中的文件采用英文索引名；原始接口JSON、方案Word和完整校验表在本贡献README所链接的Release离线包内。
