# H 阶段学习闭环产品化执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 把 ReflexLearn 登录后的学习系统从“有页面骨架”推进为“能解释推荐、能管理路径、能展示成长、能发现资源”的学习闭环产品。

**架构：** 不重写全站，不先做视觉返工。优先复用现有 FastAPI 路由、Next.js App Router、React 19、Tailwind v4、`apiClient` 与 workspace 组件。每个阶段先补可验收的产品行为，再进入下一阶段。

**技术栈：** FastAPI、Pydantic、PostgreSQL、Next.js 15.4、React 19、TypeScript、Tailwind CSS v4、现有 `scripts/*.sh` 运维脚本。

---

## 0. 当前基线

已完成：

- `/today` 已接入 `GET /api/today`，接口失败有离线建议兜底。
- `/spaces/[id]` 已是学习目标详情页。
- `/resources` 已区分外部视频、官方资料、开放课程、AI 讲解文档、针对练习、个人资料。
- `/chat` 已是 1 对 1 AI 学习导师入口。
- AI 学伴「牛牛」已接入登录后页面，`/chat` 退场避免双入口。
- `/api/profile` 已存在，能聚合目标、知识基础、薄弱点、偏好、进度、错题统计、空间数、资源数。

主要缺口：

- `/profile` 前端页面不存在，用户看不到系统“记住了什么”。
- `/plan` 仍是说明页，不是路径管理页。
- `/growth` 仍偏协作轨迹与 LoRA 样本导出，不像学生成长趋势页。
- `/resources` 还没有真实搜索/发现体验，B 站和公开资源链路仍停留在元数据展示。

---

## 1. 文件结构规划

### H1 学习画像页

- 新增：`frontend/lib/profileApi.ts`
  - 封装 `GET /api/profile`。
  - 保持后端 snake_case 合同，前端只做轻量展示。
- 新增：`frontend/components/profile/ProfileOverview.tsx`
  - 展示目标、画像来源、进度和关键统计。
- 新增：`frontend/components/profile/ProfileEvidence.tsx`
  - 展示薄弱点、知识基础、偏好、错题模式和推荐解释。
- 新增：`frontend/app/(app)/profile/page.tsx`
  - 组合画像页面，处理 loading/error/degraded。
- 修改：`frontend/lib/nav.ts`
  - 增加“学习画像”入口。
- 新增：`scripts/checks/frontend/check_profile_page.sh`
  - 静态验收画像页结构。
- 新增：`scripts/check_profile_page.sh`
  - 根脚本入口，统一走 `scripts/`。

### H2 学习路径页

- 修改：`frontend/app/(app)/plan/page.tsx`
  - 从说明页升级为路径管理页。
- 可新增：`frontend/components/plan/PlanTimeline.tsx`
  - 当前路径节点、状态、推荐理由。
- 可新增：`frontend/components/plan/PlanActions.tsx`
  - 从 Today、AI 导师、错题复盘进入路径调整。
- 可复用：`GET /api/today` 和 `GET /api/spaces/{space_id}/detail`
  - 第一版不新增后端接口。

### H3 成长档案页

- 修改：`frontend/app/(app)/growth/page.tsx`
  - 保留协作轨迹和样本导出，但改为辅助证据。
- 可新增：`frontend/components/growth/GrowthSignals.tsx`
  - 展示薄弱点变化、复习队列、资源沉淀、学习趋势。
- 可复用：`GET /api/profile`、`GET /api/today`、`GET /api/collaboration/traces`。

### H4 资源发现与推荐

- 修改：`frontend/app/(app)/resources/page.tsx`
  - 增加“按当前画像推荐”“按目标搜索”“外部平台访问策略”。
- 后续可新增：`src/reflexlearn/api/routes/resource_search.py`
  - 统一公开资源/B 站搜索元数据，不下载、不转存、不伪装来源。

---

## 2. Task H1：学习画像页产品化

**Files:**

- Create: `frontend/lib/profileApi.ts`
- Create: `frontend/components/profile/ProfileOverview.tsx`
- Create: `frontend/components/profile/ProfileEvidence.tsx`
- Create: `frontend/app/(app)/profile/page.tsx`
- Modify: `frontend/lib/nav.ts`
- Create: `scripts/checks/frontend/check_profile_page.sh`
- Create: `scripts/check_profile_page.sh`

- [x] **Step 1: 编写画像页静态验收脚本**

创建 `scripts/checks/frontend/check_profile_page.sh`，检查：

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

test -f frontend/app/\(app\)/profile/page.tsx
test -f frontend/lib/profileApi.ts
test -f frontend/components/profile/ProfileOverview.tsx
test -f frontend/components/profile/ProfileEvidence.tsx

grep -q "学习画像" frontend/app/\(app\)/profile/page.tsx
grep -q "系统记住了什么" frontend/app/\(app\)/profile/page.tsx
grep -q "getProfileSummary" frontend/lib/profileApi.ts
grep -q "知识基础" frontend/components/profile/ProfileEvidence.tsx
grep -q "薄弱点" frontend/components/profile/ProfileEvidence.tsx
grep -q "错题模式" frontend/components/profile/ProfileEvidence.tsx
grep -q "学习画像" frontend/lib/nav.ts

echo "check_profile_page -> ok"
```

创建 `scripts/check_profile_page.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"
ensure_logs
exec "$SCRIPT_DIR/checks/frontend/check_profile_page.sh" "$@"
```

- [x] **Step 2: 运行脚本确认失败**

Run:

```bash
bash scripts/check_profile_page.sh
```

Expected:

```text
frontend/app/(app)/profile/page.tsx: No such file or directory
```

- [x] **Step 3: 实现 `profileApi.ts`**

创建 `frontend/lib/profileApi.ts`：

```ts
import { apiJson } from "@/lib/apiClient";
import type { ProfileSummary } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export function getProfileSummary(token: string): Promise<ProfileSummary> {
  return apiJson<ProfileSummary>(`${API_BASE}/profile`, token);
}
```

- [x] **Step 4: 实现画像展示组件**

创建 `frontend/components/profile/ProfileOverview.tsx`，展示目标、进度、空间数、资源数、错题数。

创建 `frontend/components/profile/ProfileEvidence.tsx`，展示知识基础、薄弱点、偏好、错题模式和解释性文案。

- [x] **Step 5: 实现 `/profile` 页面**

创建 `frontend/app/(app)/profile/page.tsx`：

- 使用 `useAuthSession` 读取 token。
- 使用 `getProfileSummary` 请求画像。
- loading 时展示 skeleton。
- error 时展示产品化错误文案。
- 成功后展示 `PageHeader`、`ProfileOverview`、`ProfileEvidence`。
- 提供去 `/chat` 的“更新画像”入口和去 `/today` 的“回到今日学习”入口。

- [x] **Step 6: 增加导航入口**

修改 `frontend/lib/nav.ts`，在 Today 和 AI 导师之间加入：

```ts
{ id: "profile", label: "学习画像", href: "/profile", description: "查看系统如何理解你的目标与薄弱点" },
```

- [x] **Step 7: 验证 H1**

Run:

```bash
bash scripts/check_profile_page.sh
bash scripts/check_frontend_ia.sh
bash scripts/build_frontend.sh
```

Expected:

```text
check_profile_page -> ok
```

前端构建通过。

---

## 3. Task H2：学习路径页升级

**Files:**

- Modify: `frontend/app/(app)/plan/page.tsx`
- 可新增：`frontend/components/plan/PlanTimeline.tsx`
- 可新增：`frontend/components/plan/PlanActionPanel.tsx`
- Modify: `scripts/checks/frontend/check_frontend_ia.sh`

- [x] **Step 1: 增加验收要求**

在 `scripts/checks/frontend/check_frontend_ia.sh` 中检查：

- `/plan` 页面包含“当前学习路径”。
- `/plan` 页面包含“推荐理由”。
- `/plan` 页面包含“关联资源”。
- `/plan` 页面提供去 `/chat` 和 `/mistakes` 的入口。

- [x] **Step 2: 运行脚本确认失败**

Run:

```bash
bash scripts/check_frontend_ia.sh
```

Expected:

```text
grep ... 当前学习路径 ... failed
```

- [x] **Step 3: 改造路径页**

复用 `GET /api/today` 的 `pathNodes` 和 `resources`，将 `/plan` 改为路径管理页面。

- [x] **Step 4: 验证 H2**

Run:

```bash
bash scripts/check_frontend_ia.sh
bash scripts/build_frontend.sh
```

---

## 4. Task H3：成长档案产品化

**Files:**

- Modify: `frontend/app/(app)/growth/page.tsx`
- 可新增：`frontend/components/growth/GrowthSummary.tsx`
- 可新增：`frontend/components/growth/GrowthEvidence.tsx`
- Modify: `scripts/checks/frontend/check_frontend_ia.sh`

- [x] **Step 1: 增加验收要求**

检查 `/growth` 页面包含：

- “成长趋势”
- “能力变化”
- “薄弱点变化”
- “学习证据”

- [x] **Step 2: 改造页面信息架构**

页面主视角从“协作轨迹”调整为：

- 顶部：成长趋势摘要。
- 中部：能力变化、薄弱点变化、复习状态。
- 下部：协作轨迹和 LoRA 样本导出作为技术证据。

- [x] **Step 3: 验证 H3**

Run:

```bash
bash scripts/check_frontend_ia.sh
bash scripts/build_frontend.sh
```

---

## 5. Task H4：资源发现与推荐准备

**Files:**

- Modify: `frontend/app/(app)/resources/page.tsx`
- 可新增：`frontend/components/resource/ResourceDiscovery.tsx`
- 可新增：`discuss/资源发现与B站搜索接入计划.md`

- [x] **Step 1: 先做产品入口，不直接抓取**

在 `/resources` 增加：

- 按当前画像推荐。
- 按学习目标搜索。
- B 站/公开课程/官方文档来源说明。

- [x] **Step 2: 写接入计划**

在 `discuss/资源发现与B站搜索接入计划.md` 说明：

- B 站只保存搜索元数据、BV 链接和可选 iframe。
- 不下载、不转存、不伪装来源。
- 后端统一返回 `provider`、`source_label`、`href`、`embed_url`、`usage_mode`、`source_policy`。

---

## 6. 阶段完成验收

完成 H1-H3 后至少运行：

```bash
bash scripts/check_profile_page.sh
bash scripts/check_today_page.sh
bash scripts/check_frontend_ia.sh
bash scripts/build_frontend.sh
bash scripts/test_unit.sh tests/unit/learning/test_today.py tests/unit/learning/test_assets.py tests/unit/learning/test_demo_seed.py tests/unit/api/test_today_api.py
```

验收标准：

- 登录后导航包含学习画像入口。
- `/profile` 能解释目标、薄弱点、偏好、错题模式和推荐依据。
- `/plan` 不再只是说明页。
- `/growth` 不再把原始协作轨迹当作主体验。
- 页面文案不出现“工作台”“本地草图”“后续接入”“mock/demo”等用户可见词。
