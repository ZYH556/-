"""M4-B 图谱构建：从上传文档用 LLM 抽取核心概念 + 先修依赖关系，MERGE 幂等入 Neo4j。

接到核心写链路 `ingest_document` 的第 6.5 步（PG 登记之后、关键词失效之前）。产出的
`(:Concept {name, tenant_id, description, difficulty, visibility})` 节点与
`PREREQUISITE_OF` / `RELATED_TO` 关系，**schema 严格对齐读侧** `rag/graph_retrieval.py`：
读侧 ACL 靠 `c.tenant_id=$tid OR c.visibility='public'`，故写入必带 tenant_id + visibility，
否则抽出的概念检索不到、path_plan 也回填不上。

降级铁律（与 ingest 一致，每个外部依赖独立 try/except）：
- 无 Neo4j（注入 None）→ 无处可写，整体 skip；
- 无 LLM 凭证（`llm_no_api_key`）/ 外呼失败 → 抽取返回 None，graph="skipped"；
- LLM 输出非法 JSON → 解析降级，graph="skipped"；
- MERGE 异常 → graph="degraded"。
任一降级都不抛错、不中断 ingest 主链路。

依赖注入（仿 ingest_document）：neo4j / gateway 由调用方传入。conftest **不拦 get_neo4j、不拦
gateway**，单测注入假对象既测成功又测降级，绝不让本模块内部自取触发真实连接 / 真实外呼。

成本控制：图谱抽取是**文档级一次 LLM 调用**（拼接 chunks 截断到 graph_extract_max_chars），
而非 contextual 的逐 chunk 调用——一篇文档一张图，一次抽完。
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 与种子图 / 读侧一致的两类关系；LLM 给出的其它类型一律归并到 RELATED_TO。
_PREREQUISITE = "PREREQUISITE_OF"
_RELATED = "RELATED_TO"

# 概念 MERGE：ON CREATE 写全字段；ON MATCH 只补缺失（coalesce），保护种子图已有的
# 权威 difficulty / description 不被用户上传抽取覆盖（种子 = 权威拓扑，抽取 = 补充）。
_MERGE_CONCEPT = (
    "MERGE (n:Concept {name:$name, tenant_id:$tid}) "
    "ON CREATE SET n.description=$desc, n.difficulty=$diff, n.visibility=$vis, n.source_doc=$doc "
    "ON MATCH SET n.description=coalesce(n.description, $desc), "
    "             n.source_doc=coalesce(n.source_doc, $doc)"
)
# 关系 type 不能参数化（Cypher 不支持 [:$type]），故按类型分两条；MERGE 幂等不堆边。
_MERGE_PREREQUISITE = (
    "MATCH (a:Concept {name:$a, tenant_id:$tid}), (b:Concept {name:$b, tenant_id:$tid}) "
    "MERGE (a)-[:PREREQUISITE_OF]->(b)"
)
_MERGE_RELATED = (
    "MATCH (a:Concept {name:$a, tenant_id:$tid}), (b:Concept {name:$b, tenant_id:$tid}) "
    "MERGE (a)-[:RELATED_TO]->(b)"
)

_EXTRACT_SYSTEM = (
    "你是知识图谱抽取专家。从教学文档中抽取核心知识概念及其先修依赖关系，只输出 JSON，不要任何解释或代码块标记。\n"
    "格式：{\"concepts\":[{\"name\":\"概念名\",\"description\":\"一句话描述\",\"difficulty\":0.5}],"
    "\"relations\":[{\"source\":\"概念A\",\"target\":\"概念B\",\"type\":\"PREREQUISITE_OF\"}]}\n"
    "要求：concepts 只抽真正核心的 3~8 个；name 简洁(2~10字)；description 不超过30字；"
    "difficulty 为 0.0~1.0 浮点表示学习难度(0最易1最难)；"
    "PREREQUISITE_OF 表示 source 是 target 的先修(先学 source 再学 target)，RELATED_TO 表示相关但无先后；"
    "relations 的 source/target 必须是 concepts 里出现过的 name。"
)


class ExtractedConcept(BaseModel):
    name: str
    description: str = ""
    difficulty: float = 0.5


class ExtractedRelation(BaseModel):
    source: str
    target: str
    type: str = _RELATED


class GraphExtraction(BaseModel):
    concepts: list[ExtractedConcept] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)


def _loads_lenient(text: str) -> dict:
    """鲁棒解析 LLM 的 JSON：剥离 ```json 围栏 + 截取首个 { 到末个 }（容忍前后赘述）。"""
    t = (text or "").strip()
    if t.startswith("```"):
        # ```json\n{...}\n``` → 取中段
        parts = t.split("```")
        if len(parts) >= 2:
            t = parts[1]
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        t = t[start : end + 1]
    return json.loads(t)


def _sanitize(extraction: GraphExtraction) -> GraphExtraction:
    """归一化抽取结果：去空名 / 去重 / difficulty 夹到 [0,1] / 关系两端必须是已抽概念且非自环。"""
    concepts: list[ExtractedConcept] = []
    names: set[str] = set()
    for c in extraction.concepts:
        nm = (c.name or "").strip()
        if not nm or nm in names:
            continue
        names.add(nm)
        c.name = nm
        c.difficulty = max(0.0, min(1.0, float(c.difficulty)))
        c.description = (c.description or "").strip()
        concepts.append(c)

    relations: list[ExtractedRelation] = []
    seen: set[tuple[str, str, str]] = set()
    for r in extraction.relations:
        src, tgt = (r.source or "").strip(), (r.target or "").strip()
        rtype = _PREREQUISITE if (r.type or "").strip().upper() == _PREREQUISITE else _RELATED
        if not src or not tgt or src == tgt:
            continue
        if src not in names or tgt not in names:  # 悬空端：MATCH 会失败，提前丢弃
            continue
        key = (src, tgt, rtype)
        if key in seen:
            continue
        seen.add(key)
        relations.append(ExtractedRelation(source=src, target=tgt, type=rtype))
    return GraphExtraction(concepts=concepts, relations=relations)


async def extract_concepts(
    chunks: list, doc_title: str, settings, *, gateway=None
) -> tuple[GraphExtraction | None, str]:
    """文档级一次 LLM 抽取概念图。返回 (extraction | None, 降级说明)。

    无 LLM 凭证（llm_no_api_key）/ 外呼失败 → (None, "graph:llm_*")；
    输出非法 JSON / 校验失败 → (None, "graph:parse_*")。
    """
    text = "\n".join(getattr(c, "text", "") for c in chunks)[: settings.graph_extract_max_chars]
    if not text.strip():
        return None, "graph:empty_text"
    try:
        if gateway is None:
            from reflexlearn.llm_gateway.gateway import LLMGateway

            gateway = LLMGateway()
        comp = await gateway.complete(
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user", "content": f"文档《{doc_title}》：\n{text}"},
            ],
            task_type="generation",
            schema=GraphExtraction,
            temperature=0.2,
        )
    except Exception as e:  # llm_no_api_key / 外呼异常
        logger.info("graph extract degraded (llm): %s", e)
        return None, f"graph:llm_{type(e).__name__}"

    try:
        data = _loads_lenient(comp.text)
        extraction = _sanitize(GraphExtraction.model_validate(data))
    except Exception as e:
        logger.info("graph extract degraded (parse): %s", e)
        return None, f"graph:parse_{type(e).__name__}"
    return extraction, ""


async def merge_into_neo4j(
    neo4j, extraction: GraphExtraction, *, tenant_id: str, visibility: str, doc_id: str
) -> tuple[int, int]:
    """MERGE 概念 + 关系入 Neo4j（全幂等）。返回 (写入概念数, 写入关系数)。异常向上抛由 build_graph 兜底。"""
    written_c = written_r = 0
    async with neo4j.session() as s:
        for c in extraction.concepts:
            await s.run(
                _MERGE_CONCEPT,
                name=c.name, tid=tenant_id, desc=c.description,
                diff=c.difficulty, vis=visibility, doc=doc_id,
            )
            written_c += 1
        for r in extraction.relations:
            cypher = _MERGE_PREREQUISITE if r.type == _PREREQUISITE else _MERGE_RELATED
            await s.run(cypher, a=r.source, b=r.target, tid=tenant_id)
            written_r += 1
    return written_c, written_r


async def build_graph(
    *,
    chunks: list,
    doc_title: str,
    doc_id: str,
    tenant_id: str,
    visibility: str,
    neo4j,
    settings,
    gateway=None,
) -> tuple[str, int, int, list[str]]:
    """图谱构建编排：抽取 → MERGE。返回 (status, concepts, relations, degraded_notes)。

    status: "ok"（写入成功）| "skipped"（无 neo4j / 无 LLM / 抽不出概念）| "degraded"（MERGE 异常）。
    """
    notes: list[str] = []
    if neo4j is None:
        return "skipped", 0, 0, ["graph:neo4j_unavailable"]

    extraction, note = await extract_concepts(chunks, doc_title, settings, gateway=gateway)
    if note:
        notes.append(note)
    if extraction is None or not extraction.concepts:
        if not note:
            notes.append("graph:no_concepts")
        return "skipped", 0, 0, notes

    try:
        nc, nr = await merge_into_neo4j(
            neo4j, extraction, tenant_id=tenant_id, visibility=visibility, doc_id=doc_id
        )
    except Exception as e:
        logger.warning("graph merge degraded (neo4j): %s", e)
        notes.append(f"graph:merge_{type(e).__name__}")
        return "degraded", 0, 0, notes
    return "ok", nc, nr, notes
