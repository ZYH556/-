"""W3-E LoRA 数据质量门禁：训练前检查样本完整性 / 脱敏 / 重复率 / 节点覆盖。

只证明"数据可训练前检查"，不证明模型收益。质量不达标时由 registry 拒发 ready 标记。
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from reflexlearn.training.lora_samples import LoraSftSample

# 关注节点：体现自进化协作（反思/元认知/资源生成/辩论）的样本更有训练价值
_FOCUS_NODES = {"critic", "metacognition", "generate_resource", "debate", "judge", "pipeline"}

_SENSITIVE = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{12,}"),
    re.compile(r"(?i)(api_key|password|secret)\s*[:=]\s*[A-Za-z0-9._\-]{8,}"),
]


class QualityMetrics(BaseModel):
    sample_count: int = 0
    complete_triplets: int = 0
    duplicate_rate: float = 0.0
    avg_assistant_chars: float = 0.0
    sensitive_leak_count: int = 0
    node_coverage: float = 0.0


class QualityReport(BaseModel):
    passed: bool = False
    metrics: QualityMetrics = Field(default_factory=QualityMetrics)
    issues: list[str] = Field(default_factory=list)


def _is_complete(sample: LoraSftSample) -> bool:
    roles = [m.role for m in sample.messages]
    return roles == ["system", "user", "assistant"] and all(m.content.strip() for m in sample.messages)


def _sample_text(sample: LoraSftSample) -> str:
    return "\n".join(m.content for m in sample.messages)


def _has_sensitive(text: str) -> bool:
    return any(p.search(text) for p in _SENSITIVE)


def check_dataset(
    samples: list[LoraSftSample],
    *,
    min_samples: int = 1,
    min_assistant_chars: int = 20,
    max_duplicate_rate: float = 0.5,
    min_node_coverage: float = 0.2,
) -> QualityReport:
    n = len(samples)
    complete = sum(1 for s in samples if _is_complete(s))
    assistant_texts = [s.messages[-1].content for s in samples if s.messages]
    dup_rate = (1 - len(set(assistant_texts)) / len(assistant_texts)) if assistant_texts else 0.0
    avg_chars = (sum(len(t) for t in assistant_texts) / len(assistant_texts)) if assistant_texts else 0.0
    leaks = sum(1 for s in samples if _has_sensitive(_sample_text(s)))
    covered = sum(1 for s in samples if set(s.metadata.nodes) & _FOCUS_NODES)
    coverage = (covered / n) if n else 0.0

    issues: list[str] = []
    if n < min_samples:
        issues.append(f"too_few_samples:{n}<{min_samples}")
    if complete < n:
        issues.append(f"incomplete_triplets:{n - complete}")
    if leaks > 0:
        issues.append(f"sensitive_leak:{leaks}")
    if dup_rate > max_duplicate_rate:
        issues.append(f"high_duplicate_rate:{dup_rate:.2f}")
    if avg_chars < min_assistant_chars:
        issues.append(f"assistant_too_short:{avg_chars:.0f}")
    if n > 0 and coverage < min_node_coverage:
        issues.append(f"low_node_coverage:{coverage:.2f}<{min_node_coverage:.2f}")

    metrics = QualityMetrics(
        sample_count=n,
        complete_triplets=complete,
        duplicate_rate=round(dup_rate, 4),
        avg_assistant_chars=round(avg_chars, 1),
        sensitive_leak_count=leaks,
        node_coverage=round(coverage, 4),
    )
    return QualityReport(passed=not issues, metrics=metrics, issues=issues)


def quality_report_markdown(report: QualityReport) -> str:
    m = report.metrics
    lines = [
        "# LoRA 数据集质量报告",
        "",
        f"- 结论：{'✅ 通过' if report.passed else '❌ 未通过'}",
        f"- 样本数：{m.sample_count}",
        f"- 完整三段样本：{m.complete_triplets}",
        f"- 重复率：{m.duplicate_rate}",
        f"- assistant 平均字符：{m.avg_assistant_chars}",
        f"- 敏感泄漏样本：{m.sensitive_leak_count}",
        f"- 关注节点覆盖率：{m.node_coverage}",
    ]
    if report.issues:
        lines.append("")
        lines.append("## 问题")
        lines.extend(f"- {issue}" for issue in report.issues)
    return "\n".join(lines) + "\n"
