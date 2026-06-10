from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable


def topo_order(
    resources: list[dict],
    graph: dict,
    sort_key: Callable[[dict], tuple],
) -> tuple[list[dict], dict[str, list[str]]]:
    """按概念依赖图 graph(concept->[prereqs]) 对 resources 做 Kahn 拓扑排序。"""
    graph_concepts = _graph_concepts(graph)
    by_concept: dict[str, list[dict]] = defaultdict(list)
    off_graph: list[dict] = []
    for r in resources:
        concept = _match_concept(r.get("concept", ""), graph_concepts)
        by_concept[concept].append(r) if concept else off_graph.append(r)

    if not by_concept:
        return sorted(resources, key=sort_key), {}

    present = set(by_concept)
    indeg = {c: 0 for c in present}
    adj: dict[str, list[str]] = defaultdict(list)
    for c in present:
        for pre in graph.get(c, []):
            if pre in present:
                adj[pre].append(c)
                indeg[c] += 1

    order_concepts = _kahn_order(present, indeg, adj, by_concept, sort_key)
    if len(order_concepts) < len(present):
        return sorted(resources, key=sort_key), {}

    ordered: list[dict] = []
    for c in order_concepts:
        ordered.extend(sorted(by_concept[c], key=sort_key))
    ordered.extend(sorted(off_graph, key=sort_key))
    return ordered, _prereq_task_ids(present, graph, by_concept, sort_key)


def _graph_concepts(graph: dict) -> list[str]:
    all_concepts = set(graph.keys())
    for prereqs in graph.values():
        all_concepts.update(prereqs)
    return list(all_concepts)


def _match_concept(resource_concept: str, graph_concepts: list[str]) -> str | None:
    rc_l = (resource_concept or "").lower()
    if not rc_l:
        return None
    for graph_concept in graph_concepts:
        gc_l = graph_concept.lower()
        if gc_l and (gc_l in rc_l or rc_l in gc_l):
            return graph_concept
    return None


def _kahn_order(
    present: set[str],
    indeg: dict[str, int],
    adj: dict[str, list[str]],
    by_concept: dict[str, list[dict]],
    sort_key: Callable[[dict], tuple],
) -> list[str]:
    def concept_key(concept: str):
        return min(sort_key(r) for r in by_concept[concept])

    ready = sorted([c for c in present if indeg[c] == 0], key=concept_key)
    order_concepts: list[str] = []
    while ready:
        concept = ready.pop(0)
        order_concepts.append(concept)
        for nxt in adj[concept]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
        ready = sorted(ready, key=concept_key)
    return order_concepts


def _prereq_task_ids(
    present: set[str],
    graph: dict,
    by_concept: dict[str, list[dict]],
    sort_key: Callable[[dict], tuple],
) -> dict[str, list[str]]:
    prereq_tids: dict[str, list[str]] = {}
    for concept in present:
        dep_tids: list[str] = []
        for pre in graph.get(concept, []):
            if pre in present:
                anchor = max(by_concept[pre], key=sort_key)
                if anchor.get("task_id"):
                    dep_tids.append(anchor["task_id"])
        for r in by_concept[concept]:
            if r.get("task_id"):
                prereq_tids[r["task_id"]] = list(dep_tids)
    return prereq_tids
