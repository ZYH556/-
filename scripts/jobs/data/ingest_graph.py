"""灌种子知识图谱到 Neo4j（确定性领域知识，不依赖 LLM）。

无 LLM 凭证环境下 LLM 抽取走不通，故用手工种子；4 个 Concept 的 name 对齐 data/knowledge/*.md
主题与 path_plan 的 concept，使回填可对上。全 MERGE 幂等（仿 ingest_knowledge.py），重跑覆盖不堆积。

用法（项目根，需 docker compose --profile graph up -d neo4j 已起）：
    NO_PROXY='*' PYTHONPATH=src .venv/Scripts/python.exe scripts/jobs/data/ingest_graph.py
"""
from __future__ import annotations

import asyncio

from reflexlearn.common.db import get_neo4j

TENANT = "default"

CONCEPTS = [
    {"name": "线性回归", "difficulty": 0.3, "description": "最基础的监督学习算法，建模特征与目标的线性关系"},
    {"name": "梯度下降", "difficulty": 0.4, "description": "沿损失函数梯度反方向迭代更新参数以最小化损失"},
    {"name": "过拟合与正则化", "difficulty": 0.5, "description": "模型泛化不足的成因及 L1/L2/Dropout 等缓解手段"},
    {"name": "神经网络基础", "difficulty": 0.7, "description": "多层非线性变换与前向传播/反向传播训练机制"},
]

# A -> B 表示 A 是 B 的前置（先学 A 再学 B）
PREREQUISITE_OF = [
    ("线性回归", "梯度下降"),
    ("线性回归", "过拟合与正则化"),
    ("梯度下降", "神经网络基础"),
    ("过拟合与正则化", "神经网络基础"),
]
RELATED_TO = [
    ("梯度下降", "过拟合与正则化"),
]


async def main() -> None:
    driver = get_neo4j()
    try:
        async with driver.session() as s:
            for c in CONCEPTS:
                await s.run(
                    "MERGE (n:Concept {name:$name, tenant_id:$tid}) "
                    "SET n.description=$desc, n.difficulty=$diff, n.visibility='public'",
                    name=c["name"], tid=TENANT, desc=c["description"], diff=c["difficulty"],
                )
            for a, b in PREREQUISITE_OF:
                await s.run(
                    "MATCH (a:Concept {name:$a, tenant_id:$tid}), (b:Concept {name:$b, tenant_id:$tid}) "
                    "MERGE (a)-[:PREREQUISITE_OF]->(b)",
                    a=a, b=b, tid=TENANT,
                )
            for a, b in RELATED_TO:
                await s.run(
                    "MATCH (a:Concept {name:$a, tenant_id:$tid}), (b:Concept {name:$b, tenant_id:$tid}) "
                    "MERGE (a)-[:RELATED_TO]->(b)",
                    a=a, b=b, tid=TENANT,
                )
        print(f"[OK] 已灌入 {len(CONCEPTS)} 个概念、{len(PREREQUISITE_OF)} 条前置依赖、{len(RELATED_TO)} 条相关边")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
