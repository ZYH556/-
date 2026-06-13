# 24 · Claude 全栈接管代码审查交接（给 codex）

> 2026-06-13 · 用户安排 codex 审查 Claude 全栈接管以来的代码。本文件是审查向导：
> 划清审查范围、列出关注点、**主动暴露我自己判断存疑的边界**（审查精华在 §4），
> 附验证命令。目标是让审查聚焦在真正可能有问题的地方，而非泛读 ~2 万行 diff。

---

## 1. 审查范围

接管以来 5 个 commit（`git log --oneline a50b516^..HEAD`）：

| commit | 轮次 | 主题 |
|--------|------|------|
| a50b516 | FS-1 | 验收 codex 资源发现/画像历史 + 沉淀闭环三波（保存/档案化/小账） |
| 8a0fbf1 | FS-2 | W1 收口：资源详情页 + 学习状态回写 + 种子接线 + 导师中间态 |
| 67c1e80 | FS-3 | W2：B 站真实搜索（wbi 签名）+ 学习状态喂画像快照 |
| 3b9f0ae | FS-4 | W3：/plan 节点操作（标完成/补救插入）+ /growth 双序列火花线 |
| 110d9cc | FS-5 | W3 续：路径节点关联资源（plan↔resources 闭环） |

**注意范围边界**：`a50b516` 的 diff 含大量 **codex 自己历史未提交产出**（H 阶段前端、companion/today/profile 页、seed 等）被一并提交——那些不在本次审查范围。**Claude 真正新写/改的核心文件见 §2**，请聚焦它们。

## 2. Claude 新写/改的核心文件（按层）

**后端 learning/**
- `profile_history.py` — 画像快照趋势 + **内容去重**（`_dimensions_equal`，避免同质快照灌满趋势窗口）+ `completed_resources` 解析
- `resource_detail.py` — 资源详情聚合 + 学习状态回写（`ResourceStudyStore` 内存兜底）
- `bilibili_search.py` — B 站 wbi 签名搜索（缓存/限频/降级/`trust_env=False`）
- `path_ops.py` — 路径节点读取/标完成/补救插入 + **按 concept 关联资源**（`_resources_by_concept`）
- `resource_discovery.py` — `merge_live_videos`（合并真实视频）/`discovery_query`（goal+薄弱点组合词）
- `assets.py` — `save_resource`（candidate_id 幂等 + PG 降级内存）
- `today.py` — `_real_path_nodes`（真实路径节点）+ 节点资源透传
- `seed_demo_cli.py` — 路径节点 concept 对齐真实资源 concept

**后端 api/routes/**
- `plan.py`（新）— PATCH status / POST insert
- `workspace.py` — resources save/detail/status/discover 路由
- `today.py` — 真实路径节点接入
- `profile.py` — `study_stats` 聚合 + 快照合并

**前端**：`components/growth/GrowthTrendChart.tsx`、`components/plan/PlanTimeline.tsx`、`components/resource/{ResourceCandidates,ResourceStudyActions,resourceView}.tsx`、`app/(app)/resources/[id]/page.tsx`、`lib/{planApi,resourceDetailApi,resourceDiscoveryApi}.ts`

**测试**：`tests/unit/learning/test_{profile_history,path_ops,bilibili_search,resource_detail...}.py`、`tests/unit/api/test_{resource_save,resource_detail,plan}_api.py`

## 3. 关键设计决策（审查时对照项目铁律）

1. **依赖注入**：所有 PG/外呼函数 `pg_pool`/`client` 参数注入，不在函数内自取（conftest 不拦 pg/redis，自取会卡死单测）。
2. **降级矩阵**：每个新能力 PG/外呼失败返回 degraded 标记或 None，绝不假装成功、不中断主链路。
3. **hermetic 守卫**：conftest 类级拦 `BiliSearchClient.search_videos`（原方法存 `_original_search_videos` 供测试）；路由层测试必须 mock `safe_pg_pool`。
4. **ACL**：对象级操作走 `assert_object_access`（owner/tenant/visibility）；写学习状态/路径节点强制 owner。

## 4. ⚠️ 我主动暴露的待确认边界（审查请重点验证这些）

> 这些是我自己判断"应该没问题但不完全确定"的地方，最值得 codex 用对抗视角验证。

1. **`path_ops.load_active_path_items` 读侧 ACL**：靠 SQL `WHERE lg.user_id=$1 AND lg.tenant_id=$2` 过滤，没有走 `assert_object_access`。读自己的活跃路径——这层够吗？是否存在 tenant 边界绕过？（写侧 `_owned_path_id` 有显式 owner 校验。）

2. **画像快照节流缺口**：`save_profile_snapshot` 只做"内容相同不写"去重，**没有同一天多次变化的节流**。study_stats 合入快照后，用户一天内多次改学习状态会各产生一条快照——趋势窗口（LIMIT 20）是否会被一天的高频操作占满？要不要加"同 user 同天最多 N 条"或"距上次 < M 分钟跳过"？

3. **concept 自动匹配可能偏严**：`_resources_by_concept` 用 `concept = ANY($3)` **精确匹配**。路径节点 concept 与资源 concept 必须字面相等才命中，泛步节点（建立直觉等）必然无资源。这是否太脆？（备选：模糊匹配 / 让 LLM 按节点目标推荐——但会引入成本。当前判断是精确匹配够用 + 诚实留空。）

4. **cookie 模式 token 空串**：已修 PlanTimeline 的 `Boolean(token && ...)` 误判（cookie 会话 access_token 为空串）。**请全局 grep 其他 `token &&` / `if (!token)` 残留**——我只确认了 PlanTimeline，可能别处还有同类 UI 可用性误判。

5. **`merge_live_videos` candidate_id 唯一性**：真实视频 candidate_id = `candidate-bilibili-{bvid}`，依赖 bvid 唯一。保存幂等键也是它。若同一 bvid 在不同 goal 下被发现，保存会判重——这是期望行为还是 bug？（我认为期望：同一视频对用户只存一份。）

6. **内存兜底多 worker 不共享**：`ResourceStudyStore` / `save_resource` 的内存降级路径在多 uvicorn worker 下各持一份。生产单 worker 或 PG 可用时无影响，但多 worker + PG 挂时状态会漂移。是否需要标注"内存兜底仅单进程有效"？

7. **行数压线文件**：`assets.py`(295) / `workspace.py`(~290) / `mistakes/page.tsx`(291) 逼近 300 行硬约束。下次加功能前可能需要先拆。

## 5. 验证命令

```bash
# 全量单测（预期 557 passed）
bash scripts/test_unit.sh

# 定向：本轮新增模块
bash scripts/test_unit.sh tests/unit/learning/test_path_ops.py \
  tests/unit/learning/test_bilibili_search.py \
  tests/unit/learning/test_profile_history.py \
  tests/unit/api/test_plan_api.py \
  tests/unit/api/test_resource_detail_api.py \
  tests/unit/api/test_resource_save_api.py

# 前端类型 + IA 契约
cd frontend && npx tsc --noEmit
bash scripts/check_frontend_ia.sh

# 脚本语法
bash -n scripts/*.sh
```

活体（需 8000 后端 + Docker PG + 干净种子 `bash scripts/seed_product.sh`）：登录 admin/reflexlearn-admin → /plan 标记完成看进度联动 + 节点「这一步可以看」资源 → /resources 候选区真实 B 站条目可保存 → /growth 双序列火花线 + 学习证据。

## 6. 审查产出建议

发现问题请按"文件:行 + 问题 + 严重度（阻断/建议/可选）"列出。§4 的 7 项若有结论（确认 OK / 需改）请逐条回应——那是我最想要反馈的部分。审查结果可写回本文件 §7 或单独文件，我接手修复。
