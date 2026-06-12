# 资源发现与 B 站搜索接入计划

文档性质：讨论与执行计划  
适用阶段：H4 之后的资源发现后端接入  
范围：B 站、公开课程、官方文档等外部学习资源的搜索、筛选、推荐和元数据保存

---

## 0. 当前完成状态

已完成第一版资源发现闭环：

- 前端 `/resources` 已展示按当前画像推荐、按学习目标搜索和外部来源策略。
- 后端已新增 `POST /api/resources/discover`。
- 当前接口返回 B 站、官方文档、公开课程候选资源元数据。
- 前端已接入候选资源展示区。
- 第一版不做网络抓取，候选由确定性模板和安全搜索链接生成。

已验证：

```bash
bash scripts/test_unit.sh tests/unit/learning/test_resource_discovery.py tests/unit/api/test_resource_discovery_api.py
bash scripts/check_frontend_ia.sh
bash scripts/build_frontend.sh
```

---

## 1. 目标

资源库不能只展示系统已经生成或沉淀的资源。下一阶段要让它具备“发现资源”的能力：

- 根据学习画像、当前目标、薄弱点和错题模式推荐搜索方向。
- 从 B 站、公开课程、官方文档等外部平台获取候选资源元数据。
- 由 AI 导师或推荐策略对候选资源排序、解释推荐理由。
- 把被选中的资源保存为平台资源元数据，服务 Today、学习路径和成长档案。

第一版只做搜索和元数据，不做视频下载、内容转存或版权绕过。

---

## 2. 合规边界

必须遵守：

- B 站资源只保存标题、作者/提供方、BV 链接、封面链接、时长、搜索关键词、推荐理由和可选 iframe 地址。
- 不下载视频。
- 不转存音视频文件。
- 不把外部平台内容伪装成 ReflexLearn 自有资源。
- 不绕过平台播放、登录、地区、版权或防盗链限制。
- 外部链接必须新窗口打开。
- 若使用嵌入播放，只使用平台允许的 iframe 或公开嵌入方式。

资源字段建议固定为：

```text
provider = Bilibili / Coursera / Khan Academy / scikit-learn / PyTorch / ...
source_label = B 站视频 / 公开课程 / 官方文档
href = 外部原始链接
embed_url = 可选嵌入地址
usage_mode = metadata_only
source_policy = embed_or_redirect_only
```

---

## 3. 推荐数据合同

后端统一返回：

```json
{
  "items": [
    {
      "resource_id": "candidate-bilibili-BVxxxx",
      "type": "external_video",
      "title": "线性回归损失函数直观讲解",
      "content_preview": "候选资源摘要或搜索片段",
      "provider": "Bilibili",
      "source_label": "B 站视频",
      "href": "https://www.bilibili.com/video/BVxxxx",
      "embed_url": "https://player.bilibili.com/player.html?bvid=BVxxxx",
      "usage_mode": "metadata_only",
      "source_policy": "embed_or_redirect_only",
      "estimated_minutes": 14,
      "reason": "适合先建立损失曲线直觉，再回到公式推导。",
      "matched_goal": "掌握线性回归与梯度下降",
      "matched_weak_points": ["损失函数", "梯度方向"],
      "rank_score": 0.86
    }
  ],
  "query": {
    "goal": "掌握线性回归与梯度下降",
    "weak_points": ["损失函数", "梯度方向"],
    "providers": ["bilibili", "official_doc", "oer"]
  },
  "degraded": []
}
```

---

## 4. 后端接口建议

第一阶段新增一个轻量接口：

```text
POST /api/resources/discover
```

请求：

```json
{
  "goal": "掌握线性回归与梯度下降",
  "weak_points": ["损失函数", "梯度方向"],
  "providers": ["bilibili", "official_doc", "oer"],
  "limit": 12
}
```

响应使用第 3 节数据合同。

保存候选资源时复用现有资源表：

```text
POST /api/resources/save-candidate
```

也可以先不新增保存接口，第一版让 AI 导师把候选资源转成已有资源生成链路。

---

## 5. 搜索来源策略

### 5.1 B 站

可用策略：

- 第一版使用搜索 URL 构造，让用户跳转外部平台。
- 第二版接入公开搜索结果解析或第三方搜索 API，只提取元数据。
- 若解析稳定性不足，降级为搜索链接和 AI 推荐关键词。

关键词组合：

```text
{当前目标} + {薄弱点}
{课程主题} + 入门
{知识点} + 可视化讲解
{知识点} + 例题
```

### 5.2 公开课程

候选平台：

- Coursera
- Khan Academy
- MIT OpenCourseWare
- edX
- 中国大学 MOOC

第一版优先保存课程链接、章节标题、预计时长和推荐理由。

### 5.3 官方文档

候选来源：

- scikit-learn
- PyTorch
- TensorFlow
- Python Docs
- MDN
- 课程或教材官网

官方文档适合用于确认概念边界、API 用法和代码案例，不适合替代课程讲解。

---

## 6. 前端交互建议

`/resources` 分为三层：

1. 顶部资源发现入口：按画像推荐、按学习目标搜索、外部来源策略。
2. 候选资源区：展示 B 站/公开课程/官方文档候选项，支持保存到资源库。
3. 已保存资源库：保留现有过滤、来源标识和外部访问策略。

候选资源卡片必须显示：

- 来源平台。
- 外部链接。
- 是否可站内播放。
- 推荐理由。
- 与哪个薄弱点匹配。
- 保存到资源库动作。

---

## 7. 验收标准

- `/resources` 页面不再只是资源列表。
- 用户能看到“按当前画像推荐”和“按学习目标搜索”。
- B 站、公开课程、官方文档被清晰标注为外部来源。
- 外部资源只保存元数据和链接。
- 页面文案不出现内部开发词或临时占位表述。
- 构建通过：`bash scripts/build_frontend.sh`
- 信息架构检查通过：`bash scripts/check_frontend_ia.sh`

---

## 8. 暂不做

- 不做视频下载。
- 不做自动搬运字幕。
- 不做外部平台账号登录。
- 不做版权内容解析。
- 不把搜索结果直接注入 RAG 内容库。
- 不宣称平台拥有外部课程内容。
