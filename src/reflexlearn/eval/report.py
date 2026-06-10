from __future__ import annotations

from reflexlearn.eval.schemas import EvalReport, EvalResult


def report_to_markdown(report: EvalReport) -> str:
    lines = [
        "# ReflexLearn 评测报告",
        "",
        f"- 策略：`{report.strategy}`",
        f"- 生成时间：`{report.generated_at.isoformat()}`",
        f"- 用例数：{report.total_cases}",
        f"- 任务完成率：{_pct(report.task_completion_rate)}",
        f"- 平均资源覆盖率：{_pct(report.avg_resource_coverage)}",
        f"- 平均综合分：{report.avg_overall:.4f}",
        f"- Judge 来源：{_judge_source(report)}",
        "",
        "## 总览指标",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| resource_coverage | {report.avg_resource_coverage:.4f} |",
        f"| correctness | {report.avg_correctness:.4f} |",
        f"| profile_match | {report.avg_profile_match:.4f} |",
        f"| completeness | {report.avg_completeness:.4f} |",
        f"| format_quality | {report.avg_format_quality:.4f} |",
        f"| overall | {report.avg_overall:.4f} |",
        "",
        "## 用例明细",
        "",
        "| Case | 完成 | 资源类型 | 资源覆盖率 | 平均分 | 延迟(ms) | 最后事件 | 最后摘要 | 错误 |",
        "|---|---:|---|---:|---:|---:|---|---|---|",
    ]
    for result in report.results:
        lines.append(_case_row(result))
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 当前报告可由规则 judge 或 LLM-as-a-judge 生成。")
    lines.append("- 无 LLM 凭证或 LLM 输出异常时自动降级为规则 judge。")
    return "\n".join(lines) + "\n"


def comparison_to_markdown(reports: list[EvalReport]) -> str:
    lines = [
        "# ReflexLearn 消融对比报告",
        "",
        "| Strategy | Judge 来源 | 用例数 | 任务完成率 | resource_coverage | correctness | profile_match | completeness | format_quality | overall | Δoverall |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    base = reports[0].avg_overall if reports else 0.0
    for report in reports:
        delta = report.avg_overall - base
        lines.append(
            "| "
            f"{report.strategy} | "
            f"{_judge_source(report)} | "
            f"{report.total_cases} | "
            f"{_pct(report.task_completion_rate)} | "
            f"{_pct(report.avg_resource_coverage)} | "
            f"{report.avg_correctness:.4f} | "
            f"{report.avg_profile_match:.4f} | "
            f"{report.avg_completeness:.4f} | "
            f"{report.avg_format_quality:.4f} | "
            f"{report.avg_overall:.4f} | "
            f"{delta:+.4f} |"
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 该报告用于对比不同 Agent/RAG/Reflexion 策略的 smoke 结果。")
    lines.append("- 当前默认策略优先保证快速稳定，真实评测可放开 RAG 与 LLM judge。")
    return "\n".join(lines) + "\n"


def _case_row(result: EvalResult) -> str:
    types = ", ".join(result.resource_types_generated) or "-"
    avg_score = _avg([score.overall for score in result.resource_scores])
    done = "是" if result.task_completed else "否"
    error = result.error or "-"
    last_event = result.last_event or "-"
    last_summary = result.event_trace[-1].summary if result.event_trace else "-"
    return (
        f"| {result.case_id} | {done} | {types} | {_pct(result.resource_coverage)} | "
        f"{avg_score:.4f} | {result.latency_ms} | {last_event} | {last_summary or '-'} | {error} |"
    )


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _judge_source(report: EvalReport) -> str:
    scores = [score for result in report.results for score in result.resource_scores]
    if not scores:
        return "无评分"
    if all(score.reasoning.startswith("rule:") for score in scores):
        return "规则降级"
    return "LLM 或混合"
