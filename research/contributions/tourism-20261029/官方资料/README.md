# 复旦大学旅游学系培养方案与教学班官方资料

获取时间（上海时区）：2026-10-29T21:54:47+08:00

## 方案范围

- 教务系统全校2026级目录接口完整返回 428 条（页面统计和本页条数一致）。按 `DEPART_IDS=2595`、`YEARS=2026` 查询旅游学系，完整返回 1 条方案；系统名称为“2026旅游管理专业本科培养方案（留学生适用）”，适用对象为留学生。没有把2025秋/2026春的实际教学班误当成2026级方案。
- 全校同一目录另查到 1 条标题或专业含“旅游”的其他院系方案，单独列为“关联方案”：2026历史学-旅游管理双学士学位项目培养方案（历史学系，ID 154078）。
- 每个方案另存详情JSON和Word原件；详情核对方案ID、方案名称、年级、归属院系；Word核对 ZIP 完整性、主文档 XML 和正文“旅游管理”。原始Word导出接口没有返回PDF。

## 实际教学班

- 过滤条件：`openDepartmentAssocs=2595`，开课院系为旅游学系；2025秋学期ID 504、2026春学期ID 505；单页每次500条。两学期接口页面总数和本地行数相等，均为1页。
- 共123条实际教学班记录（2025秋 54、2026春 69），按学期+课程代码汇总为87行，课程代码去重85个。课程教学班文件保留课程名称、教师、课号、班号、教学班ID、学期、院系及原始排课文本；course_catalog 文件按课程代码和学期聚合班号、教师。

## 原始来源与校验

- 培养方案目录：`https://fdjwgl.fudan.edu.cn/manager/bizType/2/page-center/major-program-search-view/search?skipAuth=1&YEARS=2026&queryPage__=1,1000`；院系目录：`https://fdjwgl.fudan.edu.cn/manager/bizType/2/page-center/major-program-search-view/search?skipAuth=1&YEARS=2026&DEPART_IDS=2595&queryPage__=1,500`。
- 方案详情：`https://fdjwgl.fudan.edu.cn/manager/bizType/2/major-program-search/info/{id}?skipAuth=1`；原件：`https://fdjwgl.fudan.edu.cn/manager/bizType/2/major-program-search/export-word`，以POST `ids=<方案编号>`下载。
- 实际教学班：`https://fdjwgl.fudan.edu.cn/student/for-all/lesson-search/semester/{sid}/search/{sid}?openDepartmentAssocs=2595&queryPage__=1,500`。所有原始JSON、下载Word原件、SHA256及各学期计数见同目录和 `统计摘要.json`。没有使用账号凭证或登录态。

## 原件许可状态

两份DOCX均来自公开官方查询与导出接口；本批未取得单独的再利用许可声明，公开访问不等于开放授权。原件权利归原权利人，本研究清单的说明不授予新的转载许可。
