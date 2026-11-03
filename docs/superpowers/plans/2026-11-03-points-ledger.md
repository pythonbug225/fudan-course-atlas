# 服务端积分账本实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将签到与试卷单文件积分改为登录用户共享的服务端 D1 账本，并让前端按 API 结果展示与打开单份文件。

**Architecture:** D1 保存不可变积分事件，`(user_id, event_key)` 唯一约束提供签到和文件解锁幂等性；服务端根据平台身份头、上海日期及受控文件目录执行读写。静态前端从积分 API 读取真实余额，提交签到/解锁请求后再展示单文件链接。

**Tech Stack:** Vinext/Next route handlers、Cloudflare Workers D1、Drizzle SQLite schema/migrations、静态 HTML/CSS/JS、Node 内置测试运行器和 SQLite。

**Spec:** `docs/superpowers/specs/2026-11-03-points-ledger-design.md`

## Global Constraints

- 保持试卷 GitHub 仓库公开；积分不阻止绕过本站直接访问公开文件。
- 每位用户按 `Asia/Shanghai` 每日签到至多 +5 分。
- 每位用户首次解锁一个有效文件 ID 扣 1 分；同一 ID 再次打开免费，不同 ID 单独计费。
- 真实账户从 0 分开始，不导入浏览器本地演示余额。
- 未登录、余额不足、无效文件、数据库失败均不得显示成功解锁。
- 投稿奖励在审核流程落地前不进入真实账本；课评和课程资料浏览免费。
- 只修改 `codex/engineering-course-contributions` 当前 PR 分支，不改主分支，不重写历史。
- 当前 checkout 使用 sparse-checkout；只扩展必要的 `lib`、`db`、`drizzle`、`.openai` 与 `tests` 路径，不关闭 sparse-checkout。

## Review Focus

- 上海午夜边界：使用 `Asia/Shanghai` 计算事件键；归属相邻 UTC 日期的请求必须按上海自然日判断。**测试：** `checkin_uses_shanghai_calendar_day`。
- 未登录或跨来源写请求：拒绝写入并保持余额不变。**测试：** `anonymous_and_cross_origin_writes_are_rejected`。
- 重复/并发请求：同一用户同一日期只发一次 +5，同一文件只扣一次；不同用户相互隔离。**测试：** `checkin_and_unlock_are_idempotent_per_user_key`。
- 客户端篡改请求：提交伪造的 user ID、日期、金额或 URL 不影响服务端身份、定价、文件映射。**测试：** `unlock_ignores_client_supplied_identity_cost_and_url`。
- 不足余额与失效文件：不得产生负余额、账目事件或成功链接。**测试：** `insufficient_balance_and_unknown_file_do_not_write_or_return_url`。

---

### Task 1: D1 积分事件表与可测试账本逻辑

**Files:**
- Modify: `db/schema.ts`
- Create: `lib/points.ts`
- Generate: `drizzle/0002_*.sql`, `drizzle/meta/*`
- Create: `tests/points.test.mjs`
- Modify: `package.json`

**Interfaces:**
- Produces `pointEvents` Drizzle table: `id`, `userId`, `eventType`, `eventKey`, `delta`, `createdAt`; unique `(userId, eventKey)` and user/time index.
- Produces `getPointsResponse(req, db, now)`, `checkInResponse(req, db, now)`, and `unlockExamResponse(req, db, fileId, now)`; `db` is an injected `D1Database | null`, so the logic can be exercised directly without a running Worker.
- These response functions live in `lib/points.ts`, use the request's platform identity header, and do not import Cloudflare runtime globals. `unlockExamResponse` resolves `fileId` from the checked-in exam index.
- `Summary` is `{ balance: number; checkedInToday: boolean; events: PointEvent[] }`, where `PointEvent` is `{ id: string; eventType: 'checkin' | 'exam_unlock'; referenceId: string | null; delta: number; createdAt: string }`; events are limited to the newest 20.
- `MutationResult` is `{ awarded: 0 | 5; alreadyCheckedIn: boolean; balance: number }`. `UnlockResult` is either `{ status: 'unlocked' | 'already_unlocked'; url: string; charged: 0 | 1; balance: number }`, `{ status: 'insufficient_points'; balance: number }`, or `{ status: 'unknown_file' }`.

- [ ] **Step 1: Add named cases** `checkin_uses_shanghai_calendar_day`, `anonymous_and_cross_origin_writes_are_rejected`, `checkin_and_unlock_are_idempotent_per_user_key`, `unlock_ignores_client_supplied_identity_cost_and_url`, and `insufficient_balance_and_unknown_file_do_not_write_or_return_url`; run them with a D1-compatible adapter over Node's built-in `node:sqlite`.
- [ ] **Step 2: Run `node --experimental-strip-types --experimental-sqlite tests/points.test.mjs`** and confirm the cases fail before the ledger functions exist.
- [ ] **Step 3: Add the `point_events` schema** and generate a new Drizzle migration with `npm run db:generate`; inspect that the generated migration adds only the new table/indexes and preserves earlier migration history.
- [ ] **Step 4: Implement the three exported response functions** in `lib/points.ts`; derive identity/date/cost from server state, validate file IDs against the checked-in exam index and fixed GitHub path, and make file unlock a single conditional insert keyed by user and file.
- [ ] **Step 5: Rerun `node --experimental-strip-types --experimental-sqlite tests/points.test.mjs`**; all date, idempotency, isolation, API-auth, and balance assertions must pass.
- [ ] **Step 6: Add the new ledger test to the existing `npm test` script** without dropping any existing test command.

### Task 2: Authenticated points and one-file unlock APIs

**Files:**
- Create: `app/api/points/route.ts`
- Create: `app/api/points/checkin/route.ts`
- Create: `app/api/exams/[fileId]/unlock/route.ts`
- Modify: `tests/points.test.mjs`

**Interfaces:**
- `GET /api/points` delegates to `getPointsResponse(req, env.DB)`; anonymous visitors receive `{ signedIn: false }`, while authenticated visitors receive the D1 summary.
- `POST /api/points/checkin` delegates to `checkInResponse(req, env.DB)`; it derives the user from `oai-authenticated-user-id`, validates same-origin, and returns `{ awarded: 0 | 5; alreadyCheckedIn: boolean; balance: number }`.
- `POST /api/exams/:fileId/unlock` delegates to `unlockExamResponse(req, env.DB, fileId)`; it derives user and URL server-side, fixes cost at 1, and returns `{ url: string; charged: 0 | 1; alreadyUnlocked: boolean; balance: number }` only after a successful or already-recorded unlock.
- API handlers return JSON errors with status 401 (no identity), 403 (invalid origin), 404 (invalid/unavailable file), 402 (insufficient points), or 503 (database unavailable).

- [ ] **Step 1: Add static route assertions** that each Next route exports its expected HTTP method and delegates to the correct response function, including the dynamic file ID.
- [ ] **Step 2: Run the points test command** and confirm these route assertions fail before the route files exist.
- [ ] **Step 3: Add the three thin Next route handlers** importing `env` from `cloudflare:workers` and delegating to `lib/points.ts`.
- [ ] **Step 4: Rerun the points test command** and confirm route assertions pass; the API boundary cases from Task 1 must remain green.

### Task 3: Replace browser-local preview with API-backed UI

**Files:**
- Modify: `public/assets/points-preview.js`
- Modify: `public/assets/exams-preview.js`
- Modify: `public/assets/exams-preview.css`
- Modify: `public/index.html`
- Create: `tests/points-ui.test.cjs`
- Modify: `package.json`

**Interfaces:**
- Points page loads `/api/points`; check-in submits to `/api/points/checkin` and renders only server-confirmed results.
- Each file button posts only its file ID to `/api/exams/:fileId/unlock`; it then shows one explicit link returned by the API. Reopening an unlocked file calls the API and incurs no second charge.
- Anonymous users get a top-level ChatGPT sign-in link returning to `#points`; content browsing stays free.

- [ ] **Step 1: Add browser-level script cases** for API loading, signed-out state, check-in success/failure, file-level request payload, duplicate unlock, insufficient points, and absence of `localStorage` reads/writes.
- [ ] **Step 2: Run `node tests/points-ui.test.cjs`** and confirm the cases expose the current local demo behavior.
- [ ] **Step 3: Replace local demo balance/history rendering** with API-backed loading, balance, check-in status and server activity; remove sample 120 balance and fake recent activity.
- [ ] **Step 4: Change exam file actions** to request server unlock before showing an external link; remove automatic async `window.open` and keep unavailable entries disabled.
- [ ] **Step 5: Update visible copy and styles** to remove preview/demo wording, show the public-link bypass notice on both relevant pages, and label contribution awards as not enabled until moderation exists.
- [ ] **Step 6: Rerun `node tests/points-ui.test.cjs`**; ensure only one returned single-file link appears and no local state can claim a real balance.

### Task 4: Full branch verification and local preview

**Files:**
- Verify: changed migration, API routes, and `public/` assets.
- Update only if needed: tests discovered while running the existing suite.

- [ ] **Step 1: Restore the repository's declared sparse-checkout paths needed for all existing tests** without altering unrelated sparse paths.
- [ ] **Step 2: Run `npm test`** and confirm the existing suite plus points tests pass; record any unrelated pre-existing failure precisely.
- [ ] **Step 3: Run `npm run build`** and confirm the Worker build includes the new routes and D1 migration metadata.
- [ ] **Step 4: Apply the generated migration to local D1** with `node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file <generated-0002-migration.sql>`; inspect the created table and indexes without replaying an already-applied migration.
- [ ] **Step 5: Start the local site and manually verify** signed-out browsing, login return path, +5 check-in, insufficient balance, one-file unlock, repeated free unlock, and the public-link limitation copy.
- [ ] **Step 6: Inspect `git diff`, `git status`, and the exact branch** to ensure only this feature and its design/plan files changed; do not merge to `main`.

