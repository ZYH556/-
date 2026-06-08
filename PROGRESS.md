# ReflexLearn · 开发进度与接管手册

> **这份文档的用途**：会话/人员中断后 30 秒内接管开发。需求拆分到可执行粒度，
> 标注「做到哪、改了什么、下一步做什么」。**每完成一轮开发，更新第 5 节（追加本轮）+ 第 6 节（勾掉已完成）+ 第 2.3 节（服务状态）。**
> single source of truth 是 `docs/00-项目蓝图与里程碑.md`，本文件是它的「执行态快照」。

最后更新：2026-06-05 · 本轮成果：P0 第二包完成：后端生产环境安全开关加固，禁止生产关闭 auth 和默认 demo 密码；前端新增最小登录门禁，chat / knowledge upload / video job 请求统一携带 Bearer token；脚本拆分为安全冒烟与依赖真写两类检查；前端构建通过。此前 P0 第一包已完成后端演示登录、HMAC token、CurrentUser 鉴权依赖、受保护 API、CORS 白名单和上传基础校验；M1-M4 机制已落地，M5-A/B/C/C2/D 评测闭环与正式报告已完成；当前全量单测 312 passed, 2 warnings。

---

## 1. 项目一句话

ReflexLearn = 软件杯 A3「自进化学习多智能体系统」。LangGraph 多智能体编排，按学习者画像生成
5+ 种学习资源（讲解文档/思维导图/代码/练习题/拓展阅读/多模态视频），具备 Reflexion 自我反思、
混合 RAG、个性化学习路径规划。前端流式展示 Agent 协作过程。

**当前里程碑：M1–M4 机制全部落地，P0 第一包和第二包已完成，M5 已启动。M4（大数据栈 + 多模态视频）六子项 A 写链路 / B 图谱 / C Kafka / D Spark·MinIO / E 视频 / F 前端均完成并配单测；Kafka+MinIO、API 写链路、前端上传/视频工具区已做真集群活体。M5-A/B/C 已能用 `scripts/run_eval.sh` 输出单策略报告，用 `scripts/run_eval.sh --compare` 输出消融对比报告；M5-C2 已具备 `--tags ablation` 切片、`resource_coverage` 指标与 controlled RAG/Reflexion 受控基线；M5-D 正式报告已落 docs。**

**仍需后续推进**：完整产品信息架构重构、数据库用户体系、HttpOnly Cookie + CSRF、登录限流、审计、上传隔离/扫描、防盗链、AI Safety Gateway 和对象级资源归属仍未完成。

---

## 2. 快速接管（必读）

### 2.1 环境致命陷阱（踩过的坑，务必遵守）

| # | 陷阱 | 正确做法 |
|---|------|---------|
| 1 | `.venv` 由 **uv** 创建，**无 pip** | 跑 python 一律用 `.venv/Scripts/python.exe`；装包用 `uv pip install` |
| 2 | 源码在 `src/` 布局 | 跑任何脚本/测试前置 `PYTHONPATH=src` |
| 3 | Windows 本机**死代理**，直连/镜像会被代理拦截卡死 | 命令前置 `NO_PROXY='*' no_proxy='*' HTTP_PROXY= HTTPS_PROXY= ALL_PROXY=` |
| 4 | **后台 Bash 命令的 cwd 不继承**项目根（相对路径 `.venv/...` 报 No such file） | 后台命令开头加 `cd /d/2026/multagent &&`（同时让 `.env` 被 pydantic 读到） |
| 5 | **双份 bge 模型死锁**：单测 e2e 会加载真实 2GB bge，叠加常驻后端的另一份 → 内存换页卡死 480s+ | 单测靠 `tests/conftest.py` autouse 守卫拦 `_get_model`（hermetic）；活体脚本与带 RAG 后端**不要同时**加载模型 |
| 6 | **Windows curl 命令行中文参数编码错乱** → 后端 400 "error parsing the body" | SSE/POST 中文 body 用 UTF-8 文件传：`--data-binary @body.json`（body 文件用 Write 工具写，保证 UTF-8） |
| 7 | HF 模型下载需镜像 + 离线优先 | 加 `HF_HUB_OFFLINE=1 HF_ENDPOINT=https://hf-mirror.com`；限线程 `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` |
| 8 | **BM25 中文小语料 IDF=0**（N≤3 时命中半数文档的词得分归零）+ 双模型死锁升级版 | 测试/小数据 ≥4 文档；图扩展**不 embed**；RAGService 的 `gather` **只并行召回、rerank 串行其后**（详见 memory 三条新坑） |

### 2.2 常用命令（复制即用）

```bash
# —— 全量单元测试（hermetic，预期 292 passed）——
bash scripts/test_unit.sh

# —— M5 消融切片 smoke（ablation: rag_required + reflexion_required）——
bash scripts/run_eval.sh --compare --tags ablation --max-cases 2 --timeout 12

# —— M5 受控消融靶向验证 ——
bash scripts/run_eval.sh --compare --tags ablation,rag_required \
  --strategies no_rag,controlled_rag,single_agent_baseline --max-cases 1 --timeout 12
bash scripts/run_eval.sh --compare --tags ablation,reflexion_required \
  --strategies no_reflexion,controlled_reflexion,single_agent_baseline --max-cases 1 --timeout 12

# —— 启动后端（后台工作态，:8000）——
bash scripts/start_api.sh
# 健康检查：curl -s --noproxy '*' -w "%{http_code}" http://127.0.0.1:8000/docs

# —— 启动前端（frontend/）——
bash scripts/start_frontend.sh
bash scripts/build_frontend.sh     # 生产构建；可传 API base
bash scripts/stop_frontend.sh      # 停止前端；默认 :3000，可 bash scripts/stop_frontend.sh 3001 覆盖

# —— 启动中间件 ——
bash scripts/start_graph.sh      # core + graph
bash scripts/start_bigdata.sh    # Kafka + MinIO（会触发 Kafka 镜像拉取）
bash scripts/check_bigdata.sh    # Kafka produce/consume + MinIO put/get/remove
bash scripts/start_full.sh       # core + graph + bigdata + observe
# P0 安全底座后，check_api 会自动用 REFLEXLEARN_HEALTH_USER / REFLEXLEARN_HEALTH_PASSWORD 登录。
# 默认开发账号：admin / reflexlearn-admin；生产必须通过环境变量改掉。
bash scripts/check_api.sh        # 兼容入口：默认只跑安全冒烟；默认 :8000，可 bash scripts/check_api.sh 8001 覆盖
bash scripts/check_api_security.sh 8001      # 鉴权、受保护路由、上传 guard、视频提交；不依赖 Qdrant/PG
bash scripts/check_api_integrations.sh 8001  # Qdrant/PG 真写和视频降级；需要依赖中间件可用
bash scripts/stop_api.sh         # 停止 API；默认 :8000，可 bash scripts/stop_api.sh 8001 覆盖

# —— SSE 联调（中文 body 必须走文件）——
# 先写 body.json: {"message":"线性回归从入门到精通","user_id":"demo"}
curl -N -s --noproxy '*' -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" --data-binary @body.json
```

### 2.3 当前服务状态（跨会话会失效，用上方命令重启）

- **后端**：本轮临时启动 `:8002` 并执行 `bash scripts/check_api_security.sh 8002`，安全冒烟通过：health、未登录 401、auth login、auth me、非法上传 415、视频提交鉴权均 OK；随后已执行 `bash scripts/stop_api.sh 8002` 清理，当前未保留 8001/8002 常驻监听。`scripts/check_api.sh` 现在默认转发安全冒烟；Qdrant/PG 真写需显式运行 `scripts/check_api_integrations.sh`。
- **前端**：本轮新增最小登录门禁和 Bearer token 注入，`bash scripts/build_frontend.sh` 构建通过（首屏 467kB）；当前未保留 3001 常驻监听。统一用 `scripts/start_frontend.sh` / `scripts/build_frontend.sh` / `scripts/stop_frontend.sh` 启停与构建并写 `logs/`。
- **依赖中间件**：core+graph+bigdata 当前已运行：Redis（:16379 healthy）/ Qdrant（:16333 healthy）/ PG（:15432 healthy）/ Neo4j（17474/17687，4 Concept + 4 PREREQUISITE_OF + 1 RELATED_TO）/ Kafka（:19092）/ MinIO（:19000/:19001）。`scripts/check_bigdata.sh` 已验证 Kafka produce/consume + MinIO put/get/remove。Kafka 新建 health topic 时会出现短暂 metadata/leader warning，最终读写成功即可。
- **知识写链路（M4-A/B）**：`POST /api/knowledge/upload`（multipart：`file` + `course_id`/`user_id`/`tenant_id`/`visibility`/`title`/`enable_contextual`/`enable_graph_build`）→ 解析/分块/向量化/入库 +（可选）LLM 抽概念/先修关系入 Neo4j，返回 `IngestResult`（chunks/embedded/qdrant_written/pg_written/contextual/**graph/graph_concepts/graph_relations**/degraded/status）。唯一写入口 `data_engineering/ingest.py:ingest_document`（B 图谱已并入第 6.5 步；C Kafka 共用）。
- **增量链路（M4-C 新增）**：`enable_kafka=true` 时上传走异步——投递 `knowledge.changes` 事件、消费进程 `scripts/kafka_consumer.py` 异步入库（复用 `ingest_document`）；broker 不可用上传自动降级同步。aiokafka 0.14.0 已装；Kafka 当前在 :19092，`scripts/check_bigdata.sh` 已验证 produce/consume。
- **批处理（M4-D 新增）**：MinIO 原始存储（minio 7.2 已装，:19000）+ 批清洗 `scripts/run_clean.py`（clean 纯函数 + Spark/pandas/纯 Python 三级 runner）。MinIO 当前已通过 put/get/remove 活体；pyspark/pandas 未装 → 当前真实走纯 Python 清洗。
- **视频作业（M4-E 新增）**：`POST /api/video/jobs`（提交 storyboard）→ asyncio 后台 SeeDance 生成 → `GET /api/video/jobs/{id}` 轮询。JobStore Redis 降级内存；`enable_seedance=false`/无 key → 作业 degraded、storyboard 分镜脚本占位（不假装出视频）。

---

## 3. 里程碑总览（来自 docs/00，附执行态）

| 里程碑 | 可交付 | 状态 |
|--------|--------|------|
| M1 Agent 核心闭环 | Planner→Executor→Verifier→Critic；画像；讲解文档；流式前端 | ✅ |
| M2 多资源 + 前端 MVP | 5 种资源全通；多模态卡片；中心化/流水线协作 | ✅ |
| **M3 RAG + 记忆 + 路径** | Qdrant+Neo4j 混合检索；ACL；三级记忆；Reflexion；路径规划+推送 | ✅ |
| M4 大数据栈 + 多模态视频 | docker 全栈；文档清洗→分块→向量化→图谱；Kafka；SeeDance 视频 | ✅ 机制全落地（A 写链路 / B 图谱 / C Kafka / D Spark·MinIO / E 视频 / F 前端，全配单测；Kafka+MinIO、API 写链路、前端上传/视频工具区已活体） |
| **M5 评测 + 消融 + 微调** | eval harness；LLM-as-a-judge；消融报告；（GPU 行）LoRA | 🚧 已启动：M5-A/B/C 最小评测闭环、LLM judge 降级链路、JSON/Markdown 报告、消融对比 smoke 已完成；真实有区分度消融 / LoRA 未开始 |

---

## 4. M3 详细拆分与状态（已全部完成）

| 子项（评分项） | 状态 | 落点 / 备注 |
|---------------|------|------------|
| ACL 物理隔离 | ✅ | reflexion 已验证跨用户召回为空；payload 带 tenant/visibility |
| Reflexion 自我反思 | ✅ | 上轮闭环增强：真实向量写入 + 语义召回 + 降级门控（见 5.2） |
| **个性化学习路径规划 + 推送** | ✅ | **本轮完成**：`path_plan` 节点 + 端到端推前端（见 5.1） |
| 三级记忆 + 递归摘要 + summary buffer | ✅ | **本轮完成**：L1 上下文工程（trim + 递归摘要）+ 多轮 Redis 持久化 + MemoryManager 补全 + 对话式 UI（见 5.0） |
| 混合 RAG（Qdrant 语义 + Neo4j 图谱 + 关键词）+ rerank | ✅ | **本轮完成**：`rag/` 9 模块，三路 + RRF(k=60) + bge-reranker + ACL；活体 `routes_used` 三路全命中（见 5.0） |
| 冲突辩论 | ✅ | debate/judge 节点已在主链路 |

---

## 5. 已完成轮次（倒序，含改动文件清单）

### P0 前端登录与生产安全加固第二包 ✅ · 前端 Bearer 闭环 / 生产安全开关 / 脚本拆分

**背景**：P0 第一包完成后，后端已要求 Bearer token，但前端仍没有登录门禁，chat / upload / video 请求无法在鉴权开启后闭环；同时生产环境仍需要禁止默认 demo 密码和 `AUTH_ENABLED=false` 逃生口，API 活体脚本也需要区分“安全冒烟”和“依赖真写”。

**关键实现**：
- `common.auth.validate_auth_runtime()` 统一校验生产环境 auth 运行配置；`create_app()`、`get_current_user()`、`/api/auth/login` 都接入校验，生产关闭 auth、默认 secret、默认 demo 密码都会失败或返回 `auth_misconfigured`。
- 前端新增短期 Bearer MVP：`frontend/lib/auth.ts` 只用 `sessionStorage` 恢复刷新态，不写 `localStorage`，不存 refresh token；`AuthGate` 负责登录、恢复和退出清理。
- `frontend/lib/apiClient.ts` 与 `parseSSEStream(..., token)` 统一注入 `Authorization`；chat / knowledge upload / video submit / video poll 均携带 Bearer token。
- `frontend/lib/types.ts` 新增 `CurrentUser` / `AuthToken`，并将 `SSEMessage.data` 从 `any` 收紧为 `unknown`；`KnowledgeUpload` / `VideoJobCard` 去掉本轮涉及的 `any`。
- `scripts/check_api_security.sh` 只检查 health、login、me、未登录 401、非法上传 415、视频提交鉴权；`scripts/check_api_integrations.sh` 保留 Qdrant/PG 真写检查；`scripts/check_api.sh` 兼容转发安全冒烟并保留日志契约。
- 架构处理：`frontend/components` 已达 8 个条目上限，本轮新增登录门禁与工作台组件放入 `frontend/app/_components/`，避免继续扩大共享组件根目录。

**验证结果**：
- `bash scripts/test_unit.sh tests/unit/test_auth_security.py -q`：通过，20 passed。
- `bash scripts/test_unit.sh`：通过，312 passed, 2 warnings。
- `bash -n scripts/*.sh`：通过。
- `bash scripts/build_frontend.sh`：通过。
- `bash scripts/check_api_security.sh 8002`：通过，health、未登录 401、auth login、auth me、非法上传 415、视频提交鉴权均 OK；随后 `bash scripts/stop_api.sh 8002` 已清理。
- `rg -n "any|catch \(e: any\)|result: any|SSEMessage.*any" frontend/app frontend/components frontend/lib`：仅剩 `frontend/components/cards/MarkdownView.tsx` 的第三方 `oneDark as any`，不属于本轮核心类型扩散。

**诚实限制**：当前前端 token 方案为短期 Bearer MVP，使用 `sessionStorage` 恢复刷新态，不是最终生产会话方案。后续应升级为 HttpOnly Cookie + CSRF、数据库用户体系、登录限流、审计和对象级资源归属。`frontend/components` 已达目录条目上限，后续新增共享组件前建议先做组件目录分层。

### P0 最小安全闭环第一包 ✅ · 后端鉴权 / 租户注入 / CORS / 上传基础校验

**背景**：安全审查指出后端缺少最小认证边界，上传接口信任表单 `user_id` / `tenant_id`，CORS 仍是 `* + credentials`，上传文件缺少基础类型校验。本轮只做 P0 第一包，不扩展完整 SaaS 用户系统和前端登录页。

**关键实现**：
- 新增 `common.auth`：演示用户认证、HMAC-SHA256 token 签发/验签、`CurrentUser` / `TokenPayload` / `AuthToken` 强类型模型；生产环境默认 secret 会拒绝签发。
- 新增 `api.deps.get_current_user` 与 `routes/auth.py`：`POST /api/auth/login` 公开，`GET /api/auth/me` 需要 Bearer token。
- `chat` / `knowledge` / `video` 三组接口默认需要登录；`knowledge` 不再从表单读取可信 `user_id` / `tenant_id`，统一使用 token 中的用户与租户。
- `api.app` 接入配置化 CORS 白名单与 `TrustedHostMiddleware`，移除 `allow_origins=["*"]`。
- 新增 `api.upload_guard`：上传文件统一经过大小、扩展名、MIME、魔数和 visibility 校验；route 不再直接 `file.read()`。
- `scripts/check_api.sh` 保持 health 公开，上传和视频检查前自动登录并携带 Bearer token。

**验证结果**：
- `bash scripts/test_unit.sh tests/unit/test_auth_security.py tests/unit/test_knowledge_upload.py tests/unit/test_kafka_io.py tests/unit/test_video_jobs.py -q`：通过，39 passed。
- `bash scripts/test_unit.sh`：通过，309 passed, 2 warnings。
- `bash -n scripts/*.sh`：通过。
- 可选活体：`bash scripts/start_api.sh 8002` 后执行 `bash scripts/check_api.sh 8002`，health 与 auth login 通过；上传在真写入检查处失败，原因是当前环境 Qdrant/PG 不可用（返回 `qdrant:ResponseHandlingException`、`pg:unavailable`）。随后已执行 `bash scripts/stop_api.sh 8002` 清理。

**诚实限制**：当前只是最小后端安全边界，仍未完成数据库用户体系、前端登录页、上传隔离区、病毒扫描、内容审核、防盗链签名 URL、AI Safety Gateway、视频作业对象级归属校验。`tests/unit/` 文件数量仍远超“每层尽量不超过 8 个”的理想指标，本轮按计划不做测试目录重构，后续可单独整理。

### M5-A ✅ · 评测最小闭环（默认 ML 评测集 + 规则 Judge + EvalRunner + CLI）

**背景**：原规划 M5 要求 eval harness、LLM-as-a-judge、消融报告与量化证据。接手时 `src/reflexlearn/eval/` 只有空包，`scripts/run_eval.sh` 只有外壳并提示 `scripts/run_eval.py is not implemented yet.`。本轮先补一条快速可跑的 smoke 评测链路，为后续 LLM judge / 消融对比铺接口。

**关键设计决策**：
- **先离线规则 Judge，后接 LLM judge**：`RuleJudge` 用概念覆盖、难度区间、内容完整度、格式提示打分，无 LLM key 也能稳定跑；后续可在同一接口下扩展 LLM-as-a-judge。
- **真实编排接入但有超时**：`EvalRunner` 接收 async orchestrator，CLI 默认调用 `run_session()`，每个 case 有 `per_case_timeout_s`，避免主对话长链路拖死评测。
- **默认 smoke 关闭 RAG/多轮**：`scripts/run_eval.py` 默认设置 `ENABLE_RAG=false`、`ENABLE_MULTI_TURN=false`，优先保证速度与演示稳定；需要真实 RAG 评测时再显式调整环境。

**改动文件清单**：
- 新建 `src/reflexlearn/eval/schemas.py`：`EvalProfile` / `EvalCase` / `EvalResource` / `JudgeScore` / `EvalResult` / `EvalReport`。
- 新建 `src/reflexlearn/eval/dataset.py`：3 条机器学习默认评测 case（线性回归、过拟合正则化、神经网络路径）。
- 新建 `src/reflexlearn/eval/judge.py`：`RuleJudge` 确定性 fallback 评审器。
- 新建 `src/reflexlearn/eval/runner.py`：事件收集、资源解析、超时处理、指标聚合。
- 新建 `scripts/run_eval.py`：CLI 运行评测并输出 `logs/eval_report.json`；改 `scripts/run_eval.sh` 透传参数。
- 新建 `tests/unit/test_eval_harness.py`：TDD 红绿覆盖数据集、judge、runner 聚合、timeout、脚本契约。

**验证结果**：
- 红灯：缺少 `eval.dataset` / `eval.judge` / `eval.runner` / `scripts/run_eval.py` 时 5 个新增测试失败。
- 绿灯：`bash scripts/test_unit.sh tests/unit/test_eval_harness.py` 实际跑全量单测，**274 passed, 2 warnings**。
- 脚本：`bash -n scripts/*.sh` 通过。
- Smoke：`bash scripts/run_eval.sh --max-cases 2 --timeout 12 --strategy full-smoke` 通过，`task_completion_rate=1.0`，`avg_overall=0.8103`，报告写入 `logs/eval_report.json`。

**诚实记录**：当前是规则评测，不是 LLM-as-a-judge；指标可用于 smoke 和趋势对比，但不能单独作为最终比赛质量证据。下一步要补 LLM judge、固定评测报告 Markdown、消融策略开关与可观测指标汇总。

### M5-B ✅ · LLM-as-a-judge 降级链路 + Markdown 评测报告

**背景**：M5-A 已经能输出规则 judge 的 JSON smoke 报告，但还不能体现 `docs/06` 规划的 LLM-as-a-judge，也不方便 PPT/答辩直接引用。本轮在不牺牲速度的前提下补 LLM judge 接口和 Markdown 报告。

**关键设计决策**：
- **LLMJudge 与 RuleJudge 同接口**：`LLMJudge.evaluate(...)` 调 `LLMGateway.complete(..., task_type="judgment", schema=JudgeScore, temperature=0.0)`；无 key、外呼异常、JSON/schema 异常全部降级 `RuleJudge`。
- **报告双输出**：`scripts/run_eval.py` 同时写 `logs/eval_report.json` 和 `logs/eval_report.md`，JSON 供机器处理，Markdown 供 PPT/答辩/评审阅读。
- **保持 smoke 稳定**：默认仍设置 `ENABLE_RAG=false`、`ENABLE_MULTI_TURN=false`，避免真实模型/Redis/RAG 状态拖慢评测；有 LLM key 时自动尝试 LLM judge，无 key 自动规则降级。

**改动文件清单**：
- 改 `src/reflexlearn/eval/judge.py`：新增 `LLMJudge`、judge prompt、异常降级到 `RuleJudge`。
- 新建 `src/reflexlearn/eval/report.py`：`report_to_markdown(EvalReport)`，输出总览指标和 case 明细表。
- 改 `scripts/run_eval.py`：接入 `LLMJudge(LLMGateway())`，输出 JSON + Markdown。
- 改 `src/reflexlearn/eval/__init__.py`：导出 `LLMJudge` / `report_to_markdown`。
- 改 `tests/unit/test_eval_harness.py`：新增 LLM judge 调用参数、LLM 失败降级、Markdown 报告契约测试。

**验证结果**：
- 红灯：缺 `LLMJudge` / `report_to_markdown` / `eval_report.md` 输出时 4 个新增测试失败。
- 绿灯：`bash scripts/test_unit.sh tests/unit/test_eval_harness.py` 实际跑全量单测，**277 passed, 2 warnings**。
- 脚本：`bash -n scripts/*.sh` 通过。
- Smoke：`bash scripts/run_eval.sh --max-cases 2 --timeout 12 --strategy full-smoke` 通过，`task_completion_rate=1.0`，`avg_overall=0.8103`，报告写入 `logs/eval_report.json` 和 `logs/eval_report.md`。

**诚实记录**：当前环境没有 LLM key 时仍会走规则 judge；这条链路已经具备 LLM judge 调用契约，但最终质量论据仍需要有 key 环境跑一次真实 LLM-as-a-judge，并配人工抽检。

### M5-C ✅ · 消融对比基础设施（strategy suite + comparison report）

**背景**：M5 需要“单 Agent vs 多 Agent、有/无 RAG、有/无 Reflexion”等消融论据。M5-B 只有单策略报告，不能批量跑策略和生成对比表。本轮先补消融对比基础设施，保证后续只改策略环境即可跑多组。

**关键设计决策**：
- **策略配置独立建模**：`EvalStrategy(name, description, env)` 表示一个消融策略，默认提供 `full-smoke` / `no_rag` / `no_reflexion` / `single_agent_baseline`。
- **环境切换带 cache 清理**：`strategy_env` 设置策略环境变量并清理 `get_settings` 缓存，结束后恢复环境，避免策略之间串配置。
- **对比报告单独输出**：`scripts/run_eval.py --compare` 运行多个策略，输出 `logs/eval_comparison.json` + `logs/eval_comparison.md`。
- **smoke 策略不触碰慢外部依赖**：`no_rag` 也显式设置 `ENABLE_REFLEXION=false`，避免评测 smoke 因 memory recall 触碰 Qdrant；`single_agent_baseline` 只生成 doc，用于和多 Agent 资源包拉开基础差距。

**改动文件清单**：
- 新建 `src/reflexlearn/eval/strategies.py`：`EvalStrategy`、默认策略、环境上下文、`run_strategy_suite`。
- 新建 `src/reflexlearn/eval/baselines.py`：`single_agent_baseline` 朴素单 Agent/doc-only 基线。
- 改 `src/reflexlearn/eval/report.py`：新增 `comparison_to_markdown`。
- 改 `scripts/run_eval.py`：新增 `--compare` / `--strategies` 参数，输出消融对比报告。
- 改 `scripts/test_unit.sh`：支持位置参数透传到 pytest，后续可 `bash scripts/test_unit.sh tests/unit/test_eval_harness.py -q` 定向验证。
- 改 `src/reflexlearn/eval/__init__.py`：导出策略与对比报告函数。
- 改 `tests/unit/test_eval_harness.py`：新增策略、环境恢复、suite、comparison Markdown、CLI 合约测试。

**验证结果**：
- 红灯：缺 `eval.strategies` / `comparison_to_markdown` / `--compare` 时 5 个新增测试失败。
- 绿灯：`bash scripts/test_unit.sh tests/unit/test_eval_harness.py` 定向通过，**13 passed**；`bash scripts/test_unit.sh` 全量通过，**284 passed, 2 warnings**。
- 脚本：`bash -n scripts/*.sh` 通过。
- Smoke：`bash scripts/run_eval.sh --compare --max-cases 2 --timeout 12` 通过，生成 `logs/eval_comparison.json` / `logs/eval_comparison.md`；输出无 Qdrant 相关告警。当前 `full-smoke avg_overall=0.8103`，`single_agent_baseline avg_overall=0.7258`。

**诚实记录**：当前 `full-smoke` 为保证速度也关闭慢依赖，因此 `full-smoke` / `no_rag` / `no_reflexion` 的 smoke 分数相同；`single_agent_baseline` 已能体现 doc-only 基线差距，但仍只是 smoke 论据。要形成比赛论据，需要在可控环境下放开 RAG/LLM judge，并设计能触发失败重试的 Reflexion case。

### M5-C2 阶段一 ✅ · 消融靶场增强（ablation case tags + resource_coverage）

**背景**：M5-C 已能跑 strategy suite，但 smoke 默认关闭慢依赖，`full-smoke` / `no_rag` / `no_reflexion` 分数相同；已有 `single_agent_baseline` 只能从 overall 间接看出差距。为了后续形成可解释消融论据，本轮先补“评测靶场”：能筛选检索依赖 / 失败修复依赖 case，并在报告中展示资源覆盖率。

**关键设计决策**：
- **case tags 做切片入口**：新增 `select_eval_cases(tags=[...], max_cases=...)`，`--tags ablation` 可只跑消融靶场；多个 tag 采用 all-match，`--tags ablation,rag_required` 只跑 RAG 依赖 case。
- **新增 resource_coverage 指标**：按 `expected_resource_types` 计算每个 case 的资源覆盖率，再聚合成 `avg_resource_coverage`；它能直接暴露单 Agent/doc-only 基线与多资源生成的结构差距。
- **先靶场、后真实依赖**：新增 `rag_required` / `reflexion_required` case，但默认 smoke 仍不触碰真实 Qdrant/Reflexion。真实消融时复用同一批 case，放开 RAG/LLM judge 后再得正式结论。

**改动文件清单**：
- 改 `src/reflexlearn/eval/dataset.py`：新增 `ml-004`（RAG 三路检索依赖）与 `ml-005`（失败归因/修复策略依赖），新增 `select_eval_cases`。
- 改 `src/reflexlearn/eval/schemas.py` / `runner.py`：`EvalResult.resource_coverage`、`EvalReport.avg_resource_coverage` 与聚合计算。
- 改 `src/reflexlearn/eval/report.py`：单策略报告和消融对比报告展示 `resource_coverage`。
- 改 `scripts/run_eval.py`：新增 `--tags` 过滤；无匹配 case 返回非 0。
- 新建 `tests/unit/test_eval_ablation.py`：覆盖 ablation case、tag 过滤、资源覆盖率聚合、报告列与 CLI 契约。

**验证结果**：
- 红灯：`bash scripts/test_unit.sh tests/unit/test_eval_ablation.py` 初次运行 5 failed，分别缺 case、selector、coverage 字段、报告列与 `--tags` 参数。
- 绿灯：`bash scripts/test_unit.sh tests/unit/test_eval_ablation.py` 通过，**5 passed**；`bash scripts/test_unit.sh tests/unit/test_eval_harness.py` 通过，**13 passed**。
- Smoke：`bash scripts/run_eval.sh --compare --tags ablation --max-cases 2 --timeout 12` 通过；`full-smoke avg_resource_coverage=1.0 avg_overall=0.6260`，`single_agent_baseline avg_resource_coverage=0.3333 avg_overall=0.5275`。

**诚实记录**：这一步让“结构覆盖差距”可量化，但还不是最终 RAG/Reflexion 真实效果结论。`ml-004` 在当前 smoke 下 correctness 很低，正说明它需要真实知识库/RAG 内容；下一步应启动受控 RAG 环境或注入固定知识上下文跑 `rag_required` 切片。

### M5-C2 阶段二 ✅ · 受控 RAG / Reflexion 消融基线

**背景**：阶段一有了 ablation 切片，但 `full-smoke` 仍关闭慢依赖，不能在 correctness 上证明“有知识上下文 / 有失败经验”会提升。为保证速度且不依赖外部 Qdrant/Redis，本轮补 eval-only 受控基线：把固定参考知识或失败修复经验注入生成资源，用于量化上限和区分目标能力。

**关键设计决策**：
- **明确命名为 controlled，不伪装真实链路**：`controlled_rag` / `controlled_reflexion` 不触碰外部向量库或记忆库，只是 eval 靶场中的受控上限基线。
- **按标签定向注入**：`controlled_rag_baseline` 只对 `rag_required` case 注入 `reference_concepts`；`controlled_reflexion_baseline` 只对 `reflexion_required` case 注入失败归因 / 修复策略概念。
- **输出资源类型对齐 expected_resource_types**：受控基线不是 doc-only，而是按 case 期望资源类型生成，用 `resource_coverage` 与 correctness 同时展示结构覆盖与内容命中。

**改动文件清单**：
- 改 `src/reflexlearn/eval/baselines.py`：新增 `controlled_rag_baseline` / `controlled_reflexion_baseline` 与共享受控资源生成器。
- 改 `src/reflexlearn/eval/strategies.py`：默认策略加入 `controlled_rag` / `controlled_reflexion`。
- 改 `scripts/run_eval.py`：`EVAL_BASELINE` 映射新增两个受控 orchestrator。
- 改 `src/reflexlearn/eval/__init__.py`：导出受控基线。
- 改 `tests/unit/test_eval_ablation.py`：新增 3 个红绿测试覆盖策略注册、RAG 目标 case 提升、Reflexion 目标 case 提升。

**验证结果**：
- 红灯：`bash scripts/test_unit.sh tests/unit/test_eval_ablation.py` 初次运行新增 3 failed，缺 `controlled_rag` / `controlled_reflexion` 策略与 baseline 导出。
- 绿灯：`bash scripts/test_unit.sh tests/unit/test_eval_ablation.py` 通过，**8 passed**；`bash scripts/test_unit.sh tests/unit/test_eval_harness.py` 通过，**13 passed**。
- Smoke：`bash scripts/run_eval.sh --compare --tags ablation --max-cases 2 --timeout 12` 通过；`controlled_rag avg_correctness=0.6000 avg_overall=0.7871`，`controlled_reflexion avg_correctness=0.5000 avg_overall=0.7598`，均高于 `full-smoke avg_overall=0.6260` 与 `single_agent_baseline avg_overall=0.5275`。
- 靶向证据：`bash scripts/run_eval.sh --compare --tags ablation,rag_required --strategies no_rag,controlled_rag,single_agent_baseline --max-cases 1 --timeout 12` 通过，`no_rag avg_correctness=0.0000 avg_overall=0.6058`，`controlled_rag avg_correctness=1.0000 avg_overall=0.9495`。
- 靶向证据：`bash scripts/run_eval.sh --compare --tags ablation,reflexion_required --strategies no_reflexion,controlled_reflexion,single_agent_baseline --max-cases 1 --timeout 12` 通过，`no_reflexion avg_correctness=0.2000 avg_overall=0.6463`，`controlled_reflexion avg_correctness=1.0000 avg_overall=0.9521`。

**诚实记录**：这仍是受控上限基线，不是“真 Qdrant/真 Reflexion 召回”的最终证明。它的价值是把评测靶场、报告字段和对照逻辑全部跑通；下一步若要比赛级论据，应在相同 `--tags` 切片上接真实知识库或固定假 Qdrant/RAG service。

### M5-D ✅ · 正式评测报告沉淀

**背景**：M5-C/M5-C2 的报告此前主要写在 `logs/`，属于运行产物，跨会话容易被覆盖。docs/ 需要有正式版本承接当前结论、限制与下一步计划。

**改动文件清单**：
- 新建 `docs/08-评测报告与消融结果.md`：汇总 M5-A/B/C/C2 的评测集、指标定义、已验证命令、RAG/Reflexion 靶向消融结果、当前限制与后续计划。
- 改 `PROGRESS.md`：更新 M5-D 状态与快速接管摘要。

**验证结果**：
- 报告引用的命令均已在本轮跑通：脚本语法、全量单测、RAG 靶向消融、Reflexion 靶向消融。

**诚实记录**：该文档是当前阶段的正式报告，不是最终比赛版报告。最终版仍需真实 RAG/Reflexion 环境、LLM-as-a-judge key 环境和人工抽检结果补齐。

### 5.0 本轮 ✅ · M4 大数据栈推进（持续）—— B 图谱 + C Kafka + D Spark·MinIO + E 视频 + F 前端

> 本轮（同一接管会话）连续推进 M4 各子项（docs/04），全程降级铁律、零回归。为免反复重排历史编号，本轮各子项以 `####` 小节追加于此章。

#### 接手补丁 · Run & Debug 脚本 + 文件日志契约 + 真集群活体

**背景**：AGENTS 规则要求所有 Run & Debug 操作统一走 `scripts/*.sh`，且启动/调试前必须有文件日志输出到 `logs/`。接手时脚本只覆盖 core/graph/full/api/stop，且 `start_api.sh`、README、Makefile 仍引导直接 `uv`/`npm`/pytest；`logs/` 目录不存在，API 无应用级文件日志。

**改动文件清单**：
- 新建 `scripts/_lib.sh`：统一 `PROJECT_ROOT`/`LOG_DIR`、`ensure_logs`、本地网络变量、Python 默认环境、`.venv` 解释器定位。
- 新建 `scripts/start_bigdata.sh`、`check_bigdata.sh`、`start_frontend.sh`、`test_unit.sh`、`init_all.sh`、`run_eval.sh`、`check_api.sh`、`stop_api.sh`；改 `start_core.sh`/`start_graph.sh`/`start_full.sh`/`start_api.sh`/`stop_all.sh`，全部 `tee -a "$LOG_DIR/*.log"`。
- 新建 `common/logging.py` 并在 `api/app.py:create_app` 调用；`REFLEXLEARN_LOG_FILE` 默认 `logs/api.log`。
- 改 `docker-compose.yml`：Kafka/MinIO 镜像走 `${DOCKER_IMAGE_PREFIX:-docker.m.daocloud.io/}`，避免直连 Docker Hub。
- 改 `common/embedding.py`：embedding 默认本地缓存优先，传 `local_files_only=True`，并设置 HF/Transformers 离线变量与 `DISABLE_SAFETENSORS_CONVERSION=1`；避免上传活体时联网卡死。
- 改 `Makefile` 和 `README.md`，把初始化/测试/启动入口改为脚本封装。
- 改 `tests/unit/test_core.py` / `test_embedding.py`，新增脚本契约、文件日志、mirror 镜像、API 端口覆盖、stop_api 清理、embedding 离线加载测试。

**验证结果**：
- TDD 红灯已确认：缺少公共脚本库与 `common.logging` 时 `test_core.py` 两测失败。
- `bash scripts/test_unit.sh`：当时 **268 passed, 2 warnings**；当前基线已随前端脚本契约测试更新为 **269 passed, 2 warnings**（FastAPI TestClient/httpx2 弃用提醒；jieba/pkg_resources 弃用提醒）。
- `bash -n scripts/*.sh` 通过；`bash scripts/start_graph.sh` 通过并写 `logs/start_graph.log`，core+graph 四容器保持运行。
- `bash scripts/start_bigdata.sh`：Kafka/MinIO 经 mirror 拉取并启动；`bash scripts/check_bigdata.sh`：MinIO put/get/remove + Kafka produce/consume 通过。
- `bash scripts/start_api.sh 8001` + `bash scripts/check_api.sh 8001`：health、上传真写、视频作业降级均通过；`bash scripts/stop_api.sh 8001` 清理成功，无 uvicorn/check/test 残留进程。脚本仍保留 `API_PORT=8001` 环境变量写法，但位置参数在 Windows/PowerShell 调用链中更稳定。

**环境结论**：当前 Windows/WSL 混合 shell 下 `uv run ...` 会卡住，且 Bash `export` 不会传给 Windows `.venv/Scripts/python.exe`；脚本内部运行 Python 任务改走 `.venv`，端口等运行参数优先用命令行参数传递，依赖安装/维护仍应使用 uv。

#### 前端依赖升级 · Next 15.4 / React 19 / Tailwind 4 + 浏览器活体联调

**背景**：AGENTS 硬性规则要求 Next.js v15.4、React v19、Tailwind CSS v4。接手时 `frontend/package.json` 仍是 Next 14.2.5 / React 18.3.1 / Tailwind 3.4.7，且前端构建/停止没有脚本封装，`NEXT_PUBLIC_API_BASE` 在 Windows Git Bash → Windows Node 调用链中不能稳定继承。

**改动文件清单**：
- 改 `frontend/package.json` / `package-lock.json`：升级到 `next@15.4.11`、`react@19.2.7`、`react-dom@19.2.7`、`tailwindcss@4.3.0`、`@tailwindcss/postcss@4.3.0`、`@types/react@19.2.16`、`@types/react-dom@19.2.3`；移除 `autoprefixer`。
- 改 `frontend/postcss.config.mjs`：PostCSS 插件改为 `@tailwindcss/postcss`。
- 改 `frontend/app/globals.css`：Tailwind v4 入口改为 `@import "tailwindcss";`。
- 删 `frontend/tailwind.config.ts`：Tailwind v4 CSS-first 与自动内容检测下不再需要 v3 config。
- 改 `scripts/start_frontend.sh`：支持 `bash scripts/start_frontend.sh 3001 http://localhost:8001/api`；Windows 下用 `cmd.exe /C "set NEXT_PUBLIC_API_BASE=...&& npm ..."` 确保 API base 进入 Node 进程。
- 新增 `scripts/build_frontend.sh` / `scripts/stop_frontend.sh`：前端构建和停止也统一走脚本并写 `logs/`。
- 改 `frontend/lib/useChat.ts`：修复“停止生成”只 abort 但不退出 streaming 的状态机问题；同时将异常处理从 `any` 收紧为 `unknown`。
- 改 `tests/unit/test_core.py`：新增前端脚本契约测试，锁定端口/API base 覆盖与 Windows env 注入。

**验证结果**：
- `npm ls next react react-dom tailwindcss @tailwindcss/postcss @types/react @types/react-dom --depth=0`：确认 Next 15.4.11 / React 19.2.7 / Tailwind 4.3.0。
- `bash -n scripts/*.sh`：通过。
- `bash scripts/build_frontend.sh http://localhost:8001/api`：Next 15.4.11 生产构建通过，静态页 5/5，首屏 466kB。
- `bash scripts/test_unit.sh`：**269 passed, 2 warnings**（第三方 FastAPI/httpx2、jieba/pkg_resources 弃用提醒）。
- Playwright 活体（前端 `:3001` → API `:8001`）：页面标题正常、控制台 error/warning 为 0；上传 `data/knowledge/linear_regression.md` → `POST http://localhost:8001/api/knowledge/upload` 200，页面显示 `ok`、chunks=5、embedded=5、Qdrant=5、PG=✓；视频 storyboard → `POST /api/video/jobs` 200、`GET /api/video/jobs/{id}` 200，页面显示 `降级（展示分镜脚本）`；主对话 SSE 请求命中 `http://localhost:8001/api/chat`，点击“停止生成”后 UI 退出 streaming，网络请求为浏览器主动 `ERR_ABORTED`。

**诚实记录**：主对话后端长链路在 RAG/记忆查询后超过 2 分钟未自然收尾；前端请求与停止状态机已验证，后端服务端取消/长耗时需下一轮单独排查，不归入本轮前端依赖升级范围。

#### M4-B · 图谱构建（LLM 抽取概念/先修关系 → MERGE 入 Neo4j，写读闭环）

**背景**：M4-A 打通了「上传 → 解析/分块/向量化入 Qdrant + documents 登记」的写链路，但 `IngestResult.graph` 仅占位，Neo4j 知识图谱只有 `scripts/ingest_graph.py` 灌的 4 个手工种子概念。本轮补齐 docs/04 的图谱构建：上传链路用 LLM 从文档抽取核心概念 + 先修依赖关系，MERGE 幂等入 Neo4j，使 6.1 的图谱检索（`graph_retrieval`）与 path_plan 拓扑回填能吃到用户上传的真实知识，而非仅种子。

**三个关键设计决策**：
- **schema 严格对齐读侧**（写读闭环的命门）：写入 `(:Concept {name, tenant_id, description, difficulty, visibility})` + `PREREQUISITE_OF`/`RELATED_TO`，与 `rag/graph_retrieval.py` 读侧逐字段对齐——读侧 ACL 靠 `c.tenant_id=$tid OR c.visibility='public'`，故**写入必带 tenant_id + visibility**，否则抽出的概念检索不到、path_plan 回填不上。
- **文档级一次抽取**（非 contextual 的逐 chunk）：拼接 chunks 截断到 `graph_extract_max_chars`（默认 8000），一篇文档一次 LLM 调用产出一张概念图，控成本/时延；与每 chunk 一次的 contextual 摘要正交、互不干扰。
- **ON CREATE / ON MATCH 分治保护种子**：概念 MERGE 时 `ON CREATE SET` 全字段、`ON MATCH SET coalesce(...)` 只补缺失——种子图（权威 difficulty / 拓扑）不被用户上传抽取覆盖，抽取仅作补充。关系 type 不能参数化，按 PREREQUISITE_OF / RELATED_TO 分两条 Cypher（仿种子脚本）。

**依赖注入（延续 M4-A 范式）**：`build_graph(*, neo4j, gateway=None, ...)` 由 `ingest_document` 注入 `neo4j`（route 经 `_safe_neo4j()` 取，连接失败吞 None）。conftest **不拦 get_neo4j、不拦 gateway**，单测注入假 neo4j / 假 gateway 既测成功又测降级，绝不让函数内自取触发真实连接 / 外呼。

**改动文件清单**：
- 新建 `data_engineering/graph_build.py`：`GraphExtraction`/`ExtractedConcept`/`ExtractedRelation` schema + `extract_concepts`（LLM 抽取，`schema=GraphExtraction` 触发 json_object）+ `_loads_lenient`（剥 json 代码块围栏 + 截首尾花括号，容忍 LLM 赘述）+ `_sanitize`（去空名 / 去重 / difficulty 夹 [0,1] / 悬空·自环关系过滤 / type 归一）+ `merge_into_neo4j`（MERGE 幂等）+ `build_graph`（编排，返回 status/concepts/relations/notes 四元组）
- 改 `data_engineering/ingest.py`：`IngestResult` +`graph_concepts`/`graph_relations`（`graph` 状态语义化 disabled|skipped|ok|degraded）；`ingest_document` +`neo4j`/`enable_graph_build` 注入参数 + 第 6.5 步图谱构建（PG 登记后、关键词失效前）
- 改 `api/routes/knowledge.py`（+`_safe_neo4j` + 注入 + `enable_graph_build` Form）、`common/config.py`（+`enable_graph_build`/`graph_extract_max_chars`）

**验证结果**：
- 单测 **227 passed**（212→227，+15，零回归）：test_graph_build —— `_loads_lenient` 剥围栏 / `_sanitize` 去重·clamp·过滤 / extract 成功·围栏·LLM 降级·JSON 降级·空文本 / merge 概念+关系分流（断言 tid/vis/doc 参数对齐读侧 ACL）/ build_graph 四态（neo4j None→skipped、成功→ok、LLM 挂→skipped、MERGE 异常→degraded）/ ingest 集成三态（成功 graph=ok·2概念1关系、默认 disabled、neo4j None→skipped）。
- **诚实记录**：Docker daemon 未起（同往轮）→ 真 Neo4j 写入未活体；`.env` LLM key 全空 → 真 LLM 抽取未跑。机制完整：抽取/MERGE/降级全单测覆盖，schema 对齐由 merge 测试的参数断言锁定，Cypher 语法（MERGE / ON CREATE / ON MATCH、关系分治）与已活体验证的 `scripts/ingest_graph.py` 同构，真环境就绪即自动切换无需改业务代码。

**降级矩阵**：开关关→graph=disabled；neo4j None→skipped(`graph:neo4j_unavailable`)；LLM 无凭证/外呼失败→skipped(`graph:llm_*`)；LLM 输出非法 JSON→skipped(`graph:parse_*`)；抽不出概念→skipped(`graph:no_concepts`)；MERGE 异常→degraded(`graph:merge_*`)。任一降级不抛错、不中断 ingest 主链路（qdrant/pg 照常）。

**本轮要点**（并入 memory）：写侧图谱 schema 必须对齐读侧 ACL 字段（tenant_id + visibility），否则写了也检索不到——写读闭环的命门。

#### M4-C · Kafka 增量（aiokafka 生产/消费，broker 不可用降级同步链路）

**背景**：M4-A/B 打通同步写链路（上传即解析/分块/向量化/图谱）。docs/04 §7 要求 Kafka 增量：上传只投递事件、消费端异步入库，削峰 + 解耦。本轮落地生产/消费两端 + route 分流，并坚守降级铁律——broker 不可用时上传**降级为同步链路**，用户仍立即得结果，绝不因 broker 挂而上传失败。

**关键设计决策**：
- **生产端 broker 不可用降级同步**（铁律命门）：`enable_kafka=True` 时 route 先 `enqueue_document` 投递 `doc_added` 事件；broker 连不上 → 返回 None → route **回退同步 `ingest_document`**。`enable_kafka=False` 直接同步。三态单测全覆盖。
- **事件载荷内联 base64**：M4-C 简化为 payload 内联 `content_b64`（小/中文档；Kafka 默认单消息 ~1MB 上限）。M4-D 接 MinIO 后改投递 object key、消费端从对象存储拉，规避大消息边界（docs/04 §7.3）。
- **消费端复用唯一写入口**：`handle_event` 解码 → `ingest_document`（与上传 API 同链路，含图谱构建），单条事件失败不拖垮消费循环。消费者是**独立进程**（`scripts/kafka_consumer.py`），不塞进后端 lifespan——避免后端启动依赖 broker。
- **依赖注入 + aiokafka 已装**：`publish_event`/`handle_event` 的 producer/qdrant/pg/neo4j 由调用方注入。aiokafka 0.14.0 已装（import 不降级，只 broker 连接降级），单测注入假 producer **绝不真连 broker**（127.0.0.1:19092 会超时卡死）。

**改动文件清单**：
- 新建 `data_engineering/events.py`（`KnowledgeEvent` schema + `build_doc_event`（raw→base64）+ `decode_payload_raw` + topic/event_type 常量；**无 aiokafka 依赖**，生产/消费/单测共用）
- 新建 `data_engineering/kafka_io.py`（`_get_producer` 惰性单例 + `publish_event`（失败 False）+ `enqueue_document`（成功 queued dict / broker 挂 None）+ `handle_event`（消费→ingest）+ `run_consumer`（消费循环）+ `KafkaUnavailable`）
- 新建 `scripts/kafka_consumer.py`（消费进程入口，仿 ingest_graph.py）
- 改 `api/routes/knowledge.py`（+`get_settings` import + `enable_kafka` 分流：投递成功返 queued、broker 挂降级同步）

**验证结果**：
- 单测 **236 passed**（227→236，+9，零回归）：test_kafka_io —— 事件 JSON 往返、publish 成功/broker 降级、enqueue 成功/broker None、handle_event doc_added 入库（payload 还原经唯一写入口）/doc_deleted noop、route enable_kafka 投递 queued / broker 挂降级同步。
- **诚实记录**：无真实 Kafka broker（Docker 未起）→ 真投递/消费未活体；机制完整：生产/消费/降级/route 分流全单测覆盖，事件编解码 JSON 往返验证，真 broker 就绪 + `enable_kafka=true` + 跑 `scripts/kafka_consumer.py` 即生效。

**降级矩阵**：enable_kafka=False→同步链路（M4-A/B 原样）；enable_kafka=True + broker 挂→publish/enqueue 失败→route 降级同步；消费端单条事件解析/入库失败→记日志跳过、不中断循环；消费端 broker 挂→启动报错退出（后端不受影响）。

#### M4-D · Spark/MinIO 批清洗（clean 纯函数 + 三级 runner 降级）

**背景**：docs/04 §6 要求离线批清洗（去重/标准化/术语统一/质量过滤）保证知识底座质量 + MinIO/HDFS 原始存储。本轮落地：清洗逻辑写成**引擎无关纯函数**，runner 三级降级（Spark local[*]→pandas→纯 Python），MinIO 作原始/中间结果对象存储。

**关键设计决策**：
- **clean 纯函数与执行引擎解耦**：`cleaning.clean_one`/`clean_batch` 无 pyspark/pandas/settings 依赖，是确定性清洗内核；Spark UDF（`rdd.map`）、pandas（`apply`）、纯 Python 三种 runner 复用同一函数——引擎只决定并行度、不改清洗语义，便于测试（纯函数真实可跑）与降级。
- **三级 runner 降级**：`run_cleaning` 探测 `import pyspark`→spark、`import pandas`→pandas、都缺→`clean_batch` 纯 Python。环境实测 **pyspark/pandas 均未装 → 真实走纯 Python**；装上任一自动提速无需改码。`report.engine` 标记实际引擎。
- **去重简化为精确 hash**：`content_hash`=归一化文本 sha1 前 16 位（同文判重）。docs §6.1 的 SimHash/MinHash 近似去重需指纹库，留待；精确去重已覆盖「同文重传」主场景。
- **MinIO 注入降级**：`storage` 全 I/O try/except 吞错（无服务返回 False/空），`run_cleaning_job` 无 MinIO 返回 None 跳过。client 注入，单测用内存假 client 绝不真连。

**改动文件清单**：
- 新建 `data_engineering/cleaning.py`（`normalize_text`（bs4 去标签缺库回退正则）+ `normalize_terms`（术语词典）+ `content_hash` + `is_quality` + `clean_one`/`clean_batch` 纯函数）
- 新建 `data_engineering/batch.py`（`run_cleaning` 三级 runner + `_run_spark`/`_run_pandas` + `run_cleaning_job` 串 MinIO + `CleaningReport`）
- 新建 `data_engineering/storage.py`（MinIO `make_minio_client` + `put_bytes`/`get_bytes` + `put_documents`/`get_documents` JSON Lines，全降级）
- 新建 `scripts/run_clean.py`（批清洗作业入口）；改 `common/config.py`（+minio_* / enable_minio / clean_min_chars）

**验证结果**：
- 单测 **248 passed**（236→248，+12，零回归）：test_data_clean —— 纯函数（normalize/terms/hash/quality/clean_one/clean_batch 去重过滤）、runner（engine/计数/空输入）、MinIO 假 client（往返/失败降级/job 注入/无 MinIO 返回 None）。
- **诚实记录**：环境 minio 已装但无 MinIO 服务（Docker 未起）→ 真对象存储未活体（单测内存假 client 覆盖）；pyspark/pandas 未装 → Spark/pandas runner 缺库降级路径验证，**纯 Python 清洗是真实活体路径**（单测真跑）。装 spark/pandas + 起 MinIO 即切换。

**降级矩阵**：pyspark 缺→pandas；pandas 缺→纯 Python（永不失败）；clean 纯函数无外部依赖永不降级；MinIO 不可用→storage 返回 False/空、run_cleaning_job 返回 None 跳过；坏 JSON 行→跳过不中断。

#### M4-E · 多模态视频（SeeDance 异步作业 + 轮询 + storyboard 降级）

**背景**：VideoGenSkill（M2）已产出 storyboard 分镜脚本，docs/00 点名 SeeDance 视频生成、docs/05 §3.3 用 Celery 异步重任务。本轮落地视频生成作业系统：storyboard → SeeDance 异步生成 → 前端轮询，无凭证降级 storyboard 占位。

**关键设计决策**：
- **asyncio 轻量异步替代 Celery**：提交作业 `asyncio.create_task` 后台跑 `process_job`，免独立 worker 进程；提交立即返回 job_id（pending），前端轮询 `GET /api/video/jobs/{id}`。`submit_video_job(autostart=False)` 供单测只创建不跑后台（确定性）。
- **JobStore Redis 降级内存**（仿 session_store）：作业状态优先 Redis（`video_job:{id}` + TTL，多 worker 共享）、不可用降级内存 dict（同进程轮询仍工作）。redis 注入，单测假 redis 绝不真连。
- **SeeDance 降级 storyboard 占位**（铁律）：`enable_seedance=false`/无 key/外呼失败 → 作业落 `degraded`、video_url=None、storyboard 分镜脚本作占位（前端展示脚本，不假装出视频），呼应 docs/00 §「降级图文」对策。
- **依赖注入**：`call_seedance(client=...)`/`JobStore(redis=...)` 注入，单测假 httpx client + 假 redis，绝不真外呼/真连。

**改动文件清单**：
- 新建 `executor/video_jobs.py`（`VideoJob` + `JobStore`（Redis 降级内存）+ `call_seedance`（httpx，无凭证抛）+ `process_job`（running→done/degraded/failed）+ `submit_video_job`/`get_video_job` + `SeeDanceUnavailable`）
- 新建 `api/routes/video.py`（POST 提交 + GET 轮询）；改 `api/app.py`（注册 video 路由）、`common/config.py`（+seedance_* / enable_seedance / video_job_ttl）

**验证结果**：
- 单测 **259 passed**（248→259，+11，零回归）：test_video_jobs —— JobStore Redis 往返/降级内存、call_seedance 无 key 抛/假 client 取 url/无 url 抛、process_job 降级（storyboard 占位）/成功/作业不存在、submit pending、route 提交+查询/404。
- **诚实记录**：无 SeeDance 凭证（enable_seedance=false）→ 真视频生成未活体，降级 storyboard 占位是真实运行路径；无 Redis → JobStore 降级内存（真实路径，单测假 redis 覆盖 Redis 路径）。真 ARK key + enable_seedance + Redis 就绪即切换。

**降级矩阵**：enable_seedance=false/无 key→degraded + storyboard 占位；SeeDance 外呼失败→degraded；响应无 url→degraded；其他异常→failed；Redis 不可用→JobStore 内存；作业不存在→404。

#### M4-F · 前端上传可视化（拖拽上传 + 结果面板 + 视频卡轮询）

**背景**：M4-A~E 的后端能力（上传写链路 / 图谱 / Kafka / 批清洗 / 视频作业）需要前端入口演示。本轮在对话式 UI 上叠加 M4 数据工程工具区，复用既有 Tailwind/组件范式，零侵入主对话流。

**关键设计决策**：
- **折叠工具区零侵入**：page.tsx 在 header 与对话流之间插入 `<details>` 折叠区（默认收起），含上传 + 视频两组件，不挤占多轮对话 UX。
- **上传结果可视化**：`KnowledgeUpload` 拖拽/选择文件 → FormData POST `/api/knowledge/upload` → 面板展示 IngestResult 全字段（分块/向量化/Qdrant/PG/图谱/概念/关系 + status 徽标 + degraded 列表）；queued（Kafka）单独提示。
- **视频卡轮询**：`VideoJobCard` 提交 storyboard → POST `/api/video/jobs` → 2s setTimeout 轮询 GET 直到 done/degraded/failed（≤30 次）；done 显示视频链接、degraded 展示 storyboard 占位、卸载清定时器。
- **API base 复用既有范式**：`process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api"`（同 useChat），CORS 已开 `*`。

**改动文件清单**：
- 新建 `frontend/components/KnowledgeUpload.tsx`（拖拽上传 + IngestResultPanel）、`frontend/components/VideoJobCard.tsx`（提交 + 轮询）
- 改 `frontend/lib/types.ts`（+IngestResult / VideoJob 接口）、`frontend/app/page.tsx`（import + 折叠工具区接入）

**验证结果**：
- `npm run build` **类型检查零错**、5/5 静态页生成、首屏 445kB（Next.js 14.2）。
- **诚实记录**：UI 交互未起 dev server 活体点击（同往轮，需 `npm run dev` + 后端联调）；类型与构建全绿，组件逻辑（拖拽/FormData/轮询/降级展示）直观可审，后端就绪即端到端联通。

### 5.1 ✅ · M4-A 知识写链路（上传 API + 多格式解析 + 结构感知分块 + 向量化入库）

**背景**：M3 收官进入 M4。`data_engineering/` 此前是空目录，写侧仅 `scripts/ingest_knowledge.py`（朴素灌种子）。本轮补齐 docs/04 的 L0 写链路：文档上传 → 多格式解析 → 结构感知分块 →（可选 contextual 摘要）→ 真实 bge 向量化入 Qdrant + `documents` 表登记 + 关键词索引失效，作 B（图谱）/C（Kafka）共用的唯一写入口。

**四个关键设计决策**：
- **依赖注入（仿 reflexion.write_reflection）**：`ingest_document(*, qdrant, pg_pool, ...)` 由调用方传入。因 conftest **不拦 pg**，若函数内 `get_pg_pool()` 自取，单测会触发真实 asyncpg 连接卡死——故注入而非自取，单测注入假对象/None 既测成功又测降级。
- **payload.content 存原文、向量含 contextual 增强**：Anthropic contextual retrieval 语义——embed 带 LLM 定位摘要前缀的文本，但 payload 存原文供检索展示。
- **contextual 默认关 + Semaphore(4) + 上限**：每 chunk 一次 LLM，大文档串行会拉长上传时延；`enable_contextual=False` 默认，超 `contextual_max_chunks` 整体跳过。
- **不建 document_chunks 表**：读侧 chunk 全从 Qdrant payload / Neo4j 读，`documents` 表（已存在）足够；`uuid5(tenant::course::file)`→doc_id 幂等、`uuid5(doc_id::idx)`→point 幂等。

**改动文件清单**：
- 新建 `data_engineering/parsing.py`（ParsedDoc/Section + `parse_document` 按扩展名分派；pdf=PyMuPDF / docx=python-docx / pptx=python-pptx / html=bs4 均函数内 import、缺库抛 `ParserUnavailable`；md/txt 内置永不降级；`detect_format`）
- 新建 `data_engineering/chunking.py`（结构感知分块：section 边界内段落聚合到 max_chars、超长滑窗带 overlap、heading 随块带出；算法与 ingest_knowledge 一致）
- 新建 `data_engineering/ingest.py`（`ingest_document` 核心写链路 + `IngestResult` + `_contextualize`；7 步全 try/except 降级，payload 八字段对齐既有契约 + heading/doc_id，source_trust=0.7）
- 新建 `api/routes/knowledge.py`（`POST /api/knowledge/upload` multipart；`_safe_qdrant`/`_safe_pg` 吞连接失败为 None）
- 改 `api/app.py`（注册 knowledge 路由）、`common/config.py`（+enable_contextual/contextual_max_chunks）、`pyproject.toml`（+data/kafka/storage extra）

**验证结果**：
- 单测 **212 passed**（182→212，+30，零回归）：test_chunking(7) / test_parsing(11，含 fitz/docx/pptx 真实解析活体) / test_data_ingest(12，成功+每条降级+contextual) / test_knowledge_upload(2)。
- 活体（真实 bge-large-zh 离线缓存加载）：md 文档 → chunks=2 / embedded=2 / 向量 1024 维非零 / payload 八字段契约齐全（source_trust=0.7、visibility=public）；qdrant=None+pg=None → status=degraded、degraded=['qdrant:unavailable','pg:unavailable'] 不崩、embedding 仍真实。
- **诚实记录**：Docker daemon 未起 → Qdrant/PG 真集群写入活体受限（同往轮 reranker/真 LLM）；真实写入由 CaptureQdrant 活体脚本 + hermetic 单测的降级路径覆盖，机制完整、真环境就绪即自动切换无需改业务代码。

**降级矩阵**：解析缺库/不支持→该文档 degraded（chunks=0）链路仍 200；embedding 不可用/RAG 关→embedded=0 不写零向量、PG 仍登记；qdrant None/异常→qdrant_written=0；pg None/异常→pg_written=False；contextual LLM 不可用→逐块回退原文；qdrant+pg 全降级仍返回 degraded 200。

**本轮新踩的坑**（已并入 memory）：写链路依赖必须**注入而非函数内自取**（conftest 不拦 pg，自取会卡死单测）；**幂等覆盖残留边界**（重传若分块变少，旧 point 残留——doc_id/source 无 payload index 暂不能 filter-delete，记为已知边界，重传分块数稳定时无影响）。

### 5.2 ✅ · 6.2 三级记忆完善 —— L1 上下文工程 + 多轮会话 + 成本感知路由 + 对话式 UI

**背景**：M3 仅剩 6.2。改造前系统**单轮无状态**（每次单条消息、无 session、profile 用朴素 `messages[-8:]`、`memory/manager.py` 仅 37 行骨架）。本轮按 docs/03 补齐 **L1 短期记忆/上下文工程**（L2 Reflexion、L3 混合检索已完成），并落地**真正多轮**。

**四个关键设计决策**（与 docs/03 的刻意差异）：
- **summary 状态归属 Redis（per-session）**，绝不放 MemoryManager 单例实例属性（docs §2.4/§6 的 `self.layers` 会跨用户串台）→ TrimStrategy / RecursiveSummaryBuffer 全做**无状态纯函数**。
- **trim 只供 LLM 调用前临时构造**，绝不回写 `state["messages"]`（add_messages reducer 只追加）→ 长对话历史走 Redis 绕过 reducer。
- **无 Mem0**：recall 转发 reflexion，promote_session 直接调 write_reflection。
- **session_store.py 薄封装**：所有 Redis I/O 收敛于此（conftest 不拦 get_redis，集成测试在此 mock）。

**改动文件清单**：
- 新建 `memory/session_store.py`（load/persist 单 key JSON + TTL，全程降级）、`memory/trim.py`（TrimConfig + trim_context + is_important，规范化 dict 兼容 BaseMessage）、`memory/recursive_summary.py`（add_and_compress/get_context/_merge，LLM 降级规则截断）
- 升级 `memory/manager.py`（+trim_context/get_summary_context/update_summary/promote_session 无状态转发；recall/recall_memory_node 不变）
- 改 `orchestration/state.py`（+session_id/+summary_layers）、`orchestration/graph.py`（run_session 接 session_id + load/persist + persist 段递归摘要 + 复用单个 LLMGateway）、`orchestration/nodes/profile.py`（`messages[-8:]`→trim_context）、`orchestration/nodes/planner.py`（summary 注入 system prompt，仿 reflections）
- 改 `api/routes/chat.py`（ChatRequest +session_id，首帧 emit `event:session`）、`common/config.py`（+enable_multi_turn/session_ttl/summary_*）、`llm_gateway/gateway.py`（`_select_model` 成本感知：summary→便宜档 qwen-turbo/claude-haiku，+summary_model 覆盖；非 summary 选型逐字节不变）
- 前端 `frontend/lib/useChat.ts`（单一 state→`turns[]`，sessionRef+localStorage+resetSession）、`frontend/app/page.tsx`（对话式累积渲染 + 「＋ 新会话」按钮，展示组件全复用）

**验证结果**：
- 单测 **182 passed**（135→182，+47，零回归）：新增 session_store(7)/multi_turn(5)/gateway(8)/trim(9)/recursive_summary(8)/memory_manager(8) + planner(2)；前端 `npm run build` 类型检查零错。
- 活体多轮（真起 Redis :16379 + 后端 `ENABLE_RAG=false` 隔离模型）：① `event:session` 首帧回传 session_id；② 两轮 HTTP 串联同 sid → Redis `session:{sid}` messages 累积 4 条（user turns=['linear regression','gradient descent']）；③ 14 条超窗口历史 → 递归摘要触发 `summary_layers=1` 层。
- **诚实记录**：`.env` 三个 LLM key 全空 → summary 走**规则截断**（"（离线摘要）..."），真 LLM 摘要内容未跑（环境所限，类似上轮 reranker）；机制完整（触发/落盘/planner 注入路径全通）。`ENABLE_RAG=false` 隔离 bge（避陷阱#5/#7）。

**降级矩阵**：Redis 挂→多轮退单轮（load 空/persist False）；LLM 无凭证→summary 规则截断、profile/planner 走 fallback；trim 短输入直返；layers 超 max_depth→merge（LLM 挂则字符串拼接）；promote 无 qdrant/pg→write_reflection 返回 False；`enable_multi_turn=False`→恒单轮。

**本轮新踩的坑**（已并入 2.1 / memory）：conftest 不拦 `get_redis`（新 Redis I/O 必须 session_store 层 try/except + 测试 mock）；add_messages 把 dict 转 BaseMessage（trim 需规范化为 dict，否则 `json.dumps` 失败——原 profile 的 `messages[-8:]` 暗藏此坑）；MemoryManager 单例不可持有 session 级可变状态；旧后端进程跨会话残留占 8000（验证前先 netstat 查杀）。

### 5.3 ✅ · 6.1 混合检索（三路 RAG）+ Neo4j 知识图谱 + path_plan 拓扑回填

**背景**：M3 DoD 要求 Qdrant 语义 + Neo4j 图谱 + 关键词 三路混合检索 + rerank + ACL 物理隔离。改造前仅
`RetrieveSkill` 单路 Qdrant 语义。本轮补全 `rag/` 模块、Neo4j 连接工厂 + 种子图，并回填上轮 path_plan 预留的真实概念依赖拓扑（`nodes/path_plan.py` 的 `graph=None`）。详见 5.2。

**三个关键设计决策**（与 docs/03 参考实现的差异，刻意为之）：
- ACL 用 **dict**（复用 `SkillContext.acl` 的 `should=OR(public/user/tenant)`），不引入 ACLScope、不照抄 docs/03 的 `__NOT__` 伪逻辑。
- 图扩展**不 embed**：图路 Cypher 查相关概念名 → 用概念名走 BM25 命中 chunk，绝不对扩展概念二次 encode（防双模型死锁 + RRF 只用名次不用分数）。
- 三路融合用 **RRF(k=60)** 而非加权分数（cosine/BM25/图间接命中量纲不可比）；rerank 做精排，`weighted_sort` 仅 rerank 不可用时降级兜底（不与 rerank 串联）。

**改动文件清单**：
- 新建 `rag/`（9 模块）：`schemas`(ChunkMeta/RetrievalStrategy/RetrievalResult)、`router`(query_type→选路)、`acl`(build_qdrant_filter + acl_check)、`semantic`、`keyword`(BM25Okapi+jieba 单例)、`graph_retrieval`(Cypher 扩展，不 embed)、`rerank`(CrossEncoder 懒加载单例)、`fusion`(rrf_fuse/fuse_and_dedup/weighted_sort)、`service`(RAGService 七步编排)
- 改现有：`common/db.py`(+`get_neo4j` 单例)、`common/config.py`(+neo4j_user/reranker_model)、`skills/retrieve.py`(`_hybrid_search` 委托 RAGService，契约 100% 不变)、`orchestration/nodes/path_plan.py`(+`_load_concept_graph` 查 Neo4j PREREQUISITE_OF)、`skills/path_plan.py`(`_rule_based_order` +`_topo_order` Kahn 拓扑)、`tests/conftest.py`(守卫加拦 `_get_reranker` + `get_qdrant` 三处绑定)
- 新建脚本：`scripts/ingest_graph.py`(灌种子图，全 MERGE 幂等)

**种子知识图谱**（Neo4j 已灌）：4 Concept（线性回归0.3 / 梯度下降0.4 / 过拟合与正则化0.5 / 神经网络基础0.7）+ 4 PREREQUISITE_OF + 1 RELATED_TO，构成 DAG，拓扑序契合由浅入深。

**验证结果**：
- 单测 **135 passed**（92→135，+43，零回归）：新增 rag_fusion/router/keyword/rerank/graph/service + concept_graph，改 retrieve。
- 活体三路混合（Neo4j + Qdrant 真起、bge-large-zh 真加载）：`routes_used=['semantic','keyword','graph']` **三路全命中**，4 个 public chunk 经 ACL 召回。
- 活体 path_plan 真拓扑：从 Neo4j 加载概念图，输出 **线性回归→{梯度下降, 过拟合}→神经网络** 真实 PREREQUISITE_OF 拓扑序，`depends_on` 跨概念前置正确。
- rerank 真 bge-reranker 精排：**能力已封装 + 单测验证**（mock CrossEncoder 按分降序、≤1 直返、is_available 失败兜底）；真模型活体推理**未跑** —— bge-reranker-v2-m3(~2.3GB) 当前网络经 hf-mirror 仅 ~1MB/min（10min 只下 10MB），数十小时不可行，已停。降级 `weighted_sort` 已活体验证（enable_rerank=false 时三路召回排序正常）。

**降级矩阵**（铁律：绝不假装成功、绝不报错中断）：enable_rag=False→mock；embedding 挂→keyword+graph 仍工作；Neo4j 挂→退两路 + path_plan 启发式；BM25 挂→退两路；reranker 挂→weighted_sort；全路挂→空→RetrieveSkill 退 mock；概念不在图/图有环→拓扑退化启发式。

**本轮新踩的坑**（已并入 memory）：BM25 中文小语料 IDF=0、双模型错峰（gather 只并行召回 rerank 串行）、图扩展不 embed。

### 5.4 ✅ · path_plan 学习路径规划 Agent 节点

**背景**：设计（docs/02 §8）主链路是 `assemble → path_plan → END`，但代码缺 `path_plan`，
`learning_path` 是 assemble 按完成顺序编号的「假路径」（无依赖/无梯度/不可解释）。本轮补全为真路径：
按**教学法 + 画像**排序，每步带「学习目标 + 排序理由」（可解释），**LLM 优先、规则降级**，端到端推前端。

**范围边界**：知识库无依赖元数据、`rag/` 空 → 图谱概念依赖只留接口（skill 入参 `graph`，本轮恒传 `None` → 启发式排序），Neo4j 真依赖留待 6.1。

**改动文件清单（13 个）**：

后端：
- `src/reflexlearn/orchestration/schemas.py` — 新增 `LearningPathStep` / `LearningPathPlan` 两个 Pydantic 模型
- `src/reflexlearn/skills/path_plan.py` — **新增**（244 行）`PathPlanSkill`：LLM 排序 + `_rule_based_order` 规则兜底（教学序权重 doc<mindmap<code<quiz<reading<video，未知 type→99；画像 weak_points 命中提权前置）
- `src/reflexlearn/orchestration/nodes/path_plan.py` — **新增**（81 行）`path_plan_node`：从 `completed` 取 passed，按 task_id join `plan[].spec` 补 concept/difficulty；debate-verdict 容错；**不自增 iteration**；空/无 skill 回退 `_simple_fallback`
- `src/reflexlearn/orchestration/graph.py` — 8 处接线：import、`PathPlanSkill` 实例化、skills 字典、`path_plan_with_skills` 闭包、节点注册、改边 `assemble→path_plan→END`、initial_state 加 2 字段
- `src/reflexlearn/orchestration/state.py` — `AgentState` 加 `path_summary` / `path_strategy`
- `src/reflexlearn/api/routes/chat.py` — 加 `path_plan` 分支，emit `event: learning_path`（steps/summary/strategy）+ 一条 agent_step

前端：
- `frontend/lib/types.ts` — 加 `LearningPathStep` / `LearningPath` 接口
- `frontend/lib/useChat.ts` — 6 处：import、ChatState 加 `path`、Action、initialState 重置、reducer case、SSE switch case `learning_path`
- `frontend/components/LearningPathCard.tsx` — **新增**：渲染有序步骤（sequence/concept/objective/rationale/difficulty 徽标/depends_on）
- `frontend/app/page.tsx` — import + `hasOutput` 加 `|| !!state.path` + cards 前渲染 `<LearningPathCard>`
- `frontend/components/AgentTimeline.tsx` — `STEP_LABEL` 加 `path_plan: "规划学习路径"`

测试：
- `tests/unit/test_path_plan.py` — **新增** 15 测试（规则排序/画像提权/LLM 解析/各类降级/node join/集成图流转）
- `tests/unit/test_assemble.py` — **新增** 1 测试，锁定 assemble 的 bundle + 简单 path fallback 契约（防误删破坏纵深防御）

**验证结果**：
- 单测 92 passed（76→92，零回归）
- 活体降级（无凭证）：6 步路径，教学序 `doc→mindmap→code→quiz→reading→video` 正确，每步含 objective/rationale，sequence 连续
- 前端 `npm run build` 通过（类型检查零错）
- SSE 联调：`event: learning_path` 帧出现，data 含 steps（中文 UTF-8、可解释）

**本轮新踩的坑**（已并入 2.1）：质检阈值 `len>50`（#5/集成测试文本要够长）、后台 cwd（#4）、curl 中文 body 编码（#6）。

### 5.5 ✅ · Reflexion 闭环增强

把空转的「反思学习」修为真正的语义闭环。三处修复：① `_write_qdrant` 不再写 `[0.0]*1024` 零向量 →
`embed_documents` 真实向量化；② `recall_reflections` 从 scroll 拉 N 条改为 `embed_query + query_points`
语义检索 + ACL 下推；③ 补 `enable_rag` kill-switch 门控（写/召回两端，关闭时零模型加载）。
改动：`src/reflexlearn/memory/reflexion.py`（核心）+ `tests/unit/test_reflexion.py`（11 测试）+ `tests/conftest.py`（hermetic 守卫）。降级矩阵纯增强、契约零改动。

---

## 6. 未来待办（优先级排序，精细拆分）

### 6.1 ✅ 已完成（详见 5.2）· 混合检索 + Neo4j 知识图谱

三路混合检索（语义 Qdrant + 关键词 BM25 + 图谱 Neo4j）+ RRF(k=60) + bge-reranker 精排 + ACL 物理隔离已落地并活体验证；path_plan 真实 PREREQUISITE_OF 拓扑回填。详见 5.0。

**后续可选增强**：知识库 md 扩充 → 更多 Concept/边；LLM 自动抽取概念依赖入图；rerank 批处理与缓存优化。

### 6.2 ✅ 已完成（详见 5.1）· 三级记忆完善

L1 上下文工程（TrimStrategy 语义重要性保留 + 递归摘要 summary buffer）+ 多轮会话（Redis session 持久化 + 前端对话式累积 UI）+ MemoryManager 补全（trim/summary/promote）+ gateway 成本感知路由，已落地并活体验证。详见 5.0。

**后续可选增强**：引入真 LLM 凭证验证 summary 真推理；profile 跨 session 缓存（`profile:{uid}:summary`）；promote_session 接入主链路（会话结束自动经验升迁）；Mem0 替换自研 recall（若需更强记忆抽取/去重）。

### 6.3 ✅ 本轮全部完成 · M4 大数据栈 + 多模态视频

- **M4-A 核心写链路** ✅ 本轮（详见 5.0）：上传 API + 多格式解析 + 结构感知分块 + 向量化入库 + documents 登记 + KeywordIndex 失效。
- **M4-B 图谱构建** ✅ 本轮（详见 5.0）：上传链路 LLM 抽取核心概念 + 先修关系 MERGE 入 Neo4j（schema 对齐读侧 ACL：tenant_id+visibility），无 LLM/Neo4j 降级；并入 `ingest_document` 第 6.5 步。
- **M4-C Kafka 增量** ✅ 本轮（详见 5.0）：aiokafka 生产/消费，`enable_kafka` 开关，broker 不可用降级同步链路；事件经 `knowledge.changes`，消费进程 `scripts/kafka_consumer.py` 复用 `ingest_document`。
- **M4-D Spark/MinIO 批处理** ✅ 本轮（详见 5.0）：MinIO 原始存储（minio 已装）+ clean 纯函数 + 三级 runner（Spark local[*]→pandas→纯 Python，pyspark/pandas 缺降级纯 Python）；批清洗脚本 `scripts/run_clean.py`。
- **M4-E 多模态视频** ✅ 本轮（详见 5.0）：SeeDance 异步作业（asyncio）+ JobStore Redis 降级内存 + 轮询 API（提交/查询）+ storyboard 占位降级。
- **M4-F 前端上传可视化** ✅ 本轮（详见 5.0）：折叠工具区 = 拖拽上传（chunks/embedded/图谱面板 + 降级标注）+ 视频卡（提交 storyboard → 2s 轮询）；npm run build 类型检查零错。

见 docs/00 §6、docs/04。

### 6.4 🚧 已启动 · M5 评测 + 消融 + 微调

- **M5-A 评测最小闭环** ✅：默认 ML 评测集 + 规则 judge + EvalRunner + `scripts/run_eval.py` 已落地；`bash scripts/run_eval.sh --max-cases 2 --timeout 12 --strategy full-smoke` 通过。
- **M5-B LLM-as-a-judge + Markdown 报告** ✅：`LLMJudge` 接入 `LLMGateway.complete(..., task_type="judgment")`，无 key/异常自动降级规则 judge；脚本生成 `logs/eval_report.json` + `logs/eval_report.md`。
- **M5-C 消融对比基础设施** ✅：增加 strategy profile（full-smoke / no_rag / no_reflexion / single_agent_baseline）、环境切换、对比报告；`bash scripts/run_eval.sh --compare --max-cases 2 --timeout 12` 通过。
- **M5-C2 真实消融结论** 🚧：已补 `ablation` / `rag_required` / `reflexion_required` 评测切片、`--tags` 过滤、`resource_coverage` 指标、controlled RAG/Reflexion 受控上限基线；正式生产链路效果结论仍需放开真实 RAG/LLM judge 或注入固定假 Qdrant/RAG service 后再跑。
- **M5-D 正式评测报告沉淀** ✅：已新增 `docs/08-评测报告与消融结果.md`，沉淀当前评测集、指标、命令、结果、限制和下一步。
- **M5-E LoRA** ⬜：仍按原规划作为可选加强项；没有 GPU/训练数据前不抢主线。

**当前风险**：规则 judge 只能做 smoke 和趋势指标，不能替代最终 LLM-as-a-judge / 人工抽检；当前消融是管线 smoke，默认策略为保速度关闭慢依赖，尚不能作为最终创新性论据；主对话长链路虽在 eval smoke 中未复现，但 `/api/chat` 端到端长耗时仍需单独排查。

---

## 7. 关键架构事实（接管必读）

**主链路（LangGraph，build_graph in `orchestration/graph.py`）**：
```
START → profile → recall → planner → [gate 路由]
         ├─ central:  generate_resource (fan-out 并行) → critic → (replan 回 planner | 继续)
         ├─ pipeline: pipeline (串行多步)
         └─ debate:   debate → judge
       → assemble → path_plan → END
```
- 每个节点被 `harness_guard` 包裹（iteration/token 闸门，超限则跳过节点原样返回）。
- `learning_path` 等**非 reducer 字段**：后写覆盖前写（path_plan 覆盖 assemble 的兜底）。
- `completed` 是 `Annotated[..., add]` reducer：fan-out 各分支结果自动汇聚。

**降级哲学（全项目铁律）**：**绝不假装成功、绝不报错中断**。无 LLM 凭证→`gateway.complete` 抛
`RuntimeError("llm_no_api_key")`，各节点/skill 捕获走本地 fallback（规则规划、离线占位、规则排序）。
DB/模型不可用→try/except 降级。每个新功能必须配降级矩阵。

**契约边界（改动勿破坏）**：节点返回 dict 合并进 state；skill 返回 `SkillResult(ok, data)`；
质检 `quality_check._rule_check` = `len(content)>50`；`assemble_node` 保持不动（path_plan 的纵深兜底）。

---

## 8. 测试与验证基线

- **单测**：`tests/unit`，**289 passed**（新增 M5 strategy suite / comparison report / single_agent_baseline / ablation tags / resource_coverage 测试），hermetic（conftest 拦 `_get_model`/`_get_reranker`/`get_qdrant`，**不拦 `get_redis`/`get_pg_pool`/`get_neo4j`** → 多轮/写链路测试须在封装层 mock 或**注入假对象**，绝不让被测函数内自取 pg/redis）。新功能必须配单测 + 降级测试。
- **活体验证套路**：无凭证跑 `run_session()` 验证降级路径；带 RAG 后端 curl SSE 验证端到端帧。临时脚本放 `scripts/_verify_*.py`，验完即删。
- **零回归原则**：集成测试抓 assemble 帧、不断言图终止点；新增 state 字段用 `.get()` 读，不破坏手构 state 的测试。
