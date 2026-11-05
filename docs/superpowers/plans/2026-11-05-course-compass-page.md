# 课途规划器新页面实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**目标：** 在复旦课程地图中增加 `/compass` 页面，接入站点原生登录、用户规划快照同步和仅在会话中使用的 DeepSeek Key。

**架构：** 将独立课途的静态 HTML/JavaScript 规划器作为同源静态子应用放入 `public/compass/`，由 Next/Vinext 的 `/compass` 页面承载。通过 Cloudflare D1 保存用户隔离的版本化快照；由登录保护的 API 路由代理 DeepSeek 请求，不持久化用户 Key。

**技术栈：** Next 16 / Vinext、Cloudflare Workers、D1、Drizzle、现有 HTML/CSS/JavaScript、站点原生 ChatGPT 身份。

**设计稿：** [`docs/superpowers/specs/2026-11-05-course-compass-page-design.md`](../specs/2026-11-05-course-compass-page-design.md)

## 全局约束

- 分支从 `origin/main` 建立为 `codex/course-compass-page`，不把功能混入工程资料 PR #5。
- 新页面位于 Atlas 同源 `/compass`；独立的 `fudan-course-compass.xiasinm.chatgpt.site` 不作修改。
- 课程浏览保持公开；AI 规划和个人数据同步要求站点原生登录。
- 所有个人数据查询必须使用服务端可信身份 ID；不能信任客户端传入的 user ID。
- DeepSeek API Key 只能存于当前页面 JavaScript 内存中，不能进入数据库、`localStorage`、`sessionStorage`、Cookie、日志或错误追踪。
- 首次同步时保留本地和云端快照并由用户选择；快照更新有版本校验，不能静默覆盖。
- 复用课途规划工具与对应数据结构；模型推荐仍由现有确定性逻辑核对课程和班次。
- 不增加依赖，不改写课程库，不自动替用户选课。

## 人工审阅重点

- 未登录 API 请求和伪造其他用户 ID 时，服务端仍按身份拒绝或隔离数据。
- 本地与云端快照同时存在时，两份均保留；切换活动快照不删除另一份。
- 并发设备提交旧版本时，接口返回冲突而不是覆盖新版本。
- 无效 Key、代理错误和登出会清除内存 Key，响应与日志不回显 Key。
- `/compass`、`/compass/planner.html` 与模块/课程数据的相对路径在同源部署中可正确加载。

## 文件职责

- `app/compass/page.tsx`：提供 `/compass` 路由并承载静态规划器页面。
- `public/compass/`：课途 HTML、CSS、JS 模块与模块所需的静态课程/培养方案数据。
- `public/index.html`：课程地图入口中增加课途导航链接。
- `app/api/compass/profile/route.ts`：列出用户快照及活动快照，并切换活动快照。
- `app/api/compass/snapshots/route.ts`：创建/导入本地快照。
- `app/api/compass/snapshots/[snapshotId]/route.ts`：按版本保存用户快照。
- `app/api/compass/model/route.ts`：验证身份及请求后代理 DeepSeek。
- `lib/compass-state.ts`：状态解析、快照持久化、身份范围和版本冲突逻辑。
- `db/schema.ts`、`drizzle/0002_course_compass.sql`、`drizzle/meta/*`：D1 `compass_profiles`/`compass_snapshots` 表及迁移记录。

---

### Task 1：加入课途静态规划器页面

**文件：**
- 创建：`app/compass/page.tsx`
- 创建：`public/compass/planner.html`（静态资源不能命名为 `index.html`，以免遮蔽 `/compass` 应用路由）
- 创建：`public/compass/app.js`
- 创建：`public/compass/agent.js`
- 创建：`public/compass/audit.js`
- 创建：`public/compass/engine.js`
- 创建：`public/compass/features.js`
- 创建：`public/compass/style.css`
- 创建：`public/compass/data/` 中规划器实际请求的课程、详情与培养方案文件
- 修改：`public/index.html`

- [x] 将已发布课途使用的页面模块和它们依赖的数据放入 `public/compass/`，保留相对模块导入与原始数据结构；首页加载时不得请求这些大文件。
- [x] 创建全屏 `/compass` 页面，承载 `/compass/planner.html`；添加从课程地图导航到 `/compass` 的入口。
- [x] 只调整必要的页面链接和 API URL；不重写课程搜索、工具调用或排课规则。
- [x] 页面路径预览结果应为 Atlas 下的 `/compass`，其脚本、样式和数据请求均指向 Atlas 同源路径。

### Task 2：增加用户隔离的 D1 快照存储

**文件：**
- 修改：`db/schema.ts`
- 创建：`drizzle/0002_course_compass.sql` 及 Drizzle snapshot/journal 更新
- 创建：`lib/compass-state.ts`
- 创建：`app/api/compass/profile/route.ts`
- 创建：`app/api/compass/snapshots/route.ts`
- 创建：`app/api/compass/snapshots/[snapshotId]/route.ts`

**接口：**
- `GET /api/compass/profile` 返回当前登录者的快照摘要、活动快照和资料版本。
- `PUT /api/compass/profile` 接收 `{ snapshotId, expectedVersion }`，只切换该用户自己的活动快照。
- `POST /api/compass/snapshots` 接收 `{ label, state, source, importKey }`，验证并创建快照；`importKey` 用于避免刷新时重复导入同一份本地状态。
- `PUT /api/compass/snapshots/:snapshotId` 接收 `{ expectedVersion, state }`；仅当快照属于当前身份且版本匹配时保存，否则返回 `404` 或 `409`。
- 状态帮助函数只接收由服务端解析的 `userId`，SQL 始终以 `user_id` 为查询/更新条件。

**数据结构与帮助函数：**
- `compass_profiles(user_id PRIMARY KEY, active_snapshot_id, version, updated_at)` 保存活动快照指针。
- `compass_snapshots(snapshot_id PRIMARY KEY, user_id, label, state_json, version, source, import_key, created_at, updated_at)` 保存每份个人快照；为 `(user_id, import_key)` 建唯一索引以保证本地导入幂等。
- `parseCompassSnapshot(input: unknown): CompassSnapshot` 验证 `course-compass-v2` 的持久化字段，不接受 API Key 或聊天记录。
- `listCompassProfile(db, userId): Promise<CompassProfile>` 返回用户快照摘要和活动版本。
- `createCompassSnapshot(db, userId, input): Promise<CompassSnapshot>` 创建或按 `importKey` 返回已导入快照。
- `saveCompassSnapshot(db, userId, snapshotId, expectedVersion, state): Promise<CompassSnapshot>` 以版本比较更新用户自己的快照；版本不匹配时抛出冲突错误。
- `activateCompassSnapshot(db, userId, snapshotId, expectedVersion): Promise<CompassProfile>` 校验归属后更新活动指针；版本冲突时不切换。

- [x] 在 Drizzle schema 中按上述字段定义 `compass_profiles` 与 `compass_snapshots`，并加入 `(user_id, import_key)` 幂等索引和用户更新时间索引。
- [x] 生成下一条 D1 迁移，并同步 `_journal.json` 与最新 schema snapshot。
- [x] 实现状态 JSON 的形状、体积和字段校验；活动指针与快照访问都按用户 ID 限定。
- [x] 用 `oai-authenticated-user-id` 保护以上 API；匿名请求返回 `401`，跨用户 ID/快照访问不得泄露内容。
- [x] 对快照更新执行版本比较；过期版本返回 `409`，保留原快照，不覆盖。

### Task 3：加入 DeepSeek 请求代理

**文件：**
- 创建：`app/api/compass/model/route.ts`
- 创建：`lib/compass-model.ts`
- 修改：`public/compass/` 中实际发起模型请求的模块

**接口：**
- `POST /api/compass/model` 接收现有 OpenAI-compatible 请求体和 `x-deepseek-key` 请求头，向固定的 `https://api.deepseek.com/chat/completions` 转发，并返回兼容响应。

- [x] 要求可信登录身份，缺少 Key、请求体过大或 JSON 无效时返回明确错误。
- [x] 固定 DeepSeek 目标主机；禁止客户端控制转发地址，避免开放代理/SSRF。
- [x] 仅在转发请求期间使用 Key；不写入存储，不在日志或错误响应中输出 Key。
- [x] 无效 Key/上游故障返回可恢复的状态和简短错误，不将上游敏感响应原样暴露。

### Task 4：连接登录、快照选择和模型规划

**文件：**
- 修改：`public/compass/planner.html`
- 修改：`public/compass/app.js`
- 修改：`public/compass/agent.js` 或实际调用模型的模块
- 必要时修改：`app/api/session/route.ts`（仅在现有会话响应不足时）

- [x] 使用 `/api/session` 显示登录状态；登录/登出使用现有站点路径与 `target="_top"`，返回地址为 `/compass`。
- [x] 未登录用户仍可浏览课程；启动 AI 对话或云端保存时引导登录。
- [x] 登录后加载本地状态与云端快照：只有一份时加载该份；两份都存在时分别保留，展示选择界面，用户选择后设置活动快照。
- [x] 页面保留本地快照；保存云端时带版本号。冲突时保留两份并提示选择，不静默覆盖。
- [x] Key 仅保存在内存；每次刷新需重新输入；清除、退出、连接失败时立即置空。
- [x] AI 生成课程建议后仍走课途现有工具与确定性时间/学分校验，并展示可核对的课程证据。

### Task 5：文档、构建和预览

**文件：**
- 修改：`README.md` 或适当的维护文档
- 可选修改：`public/compass/` 中的帮助文字

- [x] 说明新页面路径、站点原生登录要求、DeepSeek Key 的会话级使用方式，以及旧独立站点的 localStorage 不会自动迁移。
- [x] 安装仓库依赖后运行 `npm run build`；构建命令退出码为 `0`。
- [x] 本地预览的 `/compass`、规划器 HTML、脚本、课程目录与方案文件均通过 HTTP 检查，匿名 profile API 返回 `401`；桌面浏览器截图工具无法访问该本机预览，因此视觉布局仍需通过 PR 预览复核。
- [x] 用户已明确授权推送新分支并创建独立 PR；不部署；保持 PR #5 与主分支不变。
