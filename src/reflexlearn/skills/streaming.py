"""生成类 Skill 的「流式优先」文本生成助手（PERF-A）。

把「有 sink 且开启流式 → 走 `complete_stream()` 逐 token 推增量，否则一次性 `complete()`」
这段判断收敛到一处，doc_gen / reading_gen 等散文型 Skill 复用。返回 (text, model_used)；
异常一律透传给调用方走离线兜底（降级铁律由各 Skill 的 except 块兜底）。
"""

from __future__ import annotations

from typing import Callable, Optional

from reflexlearn.common.config import get_settings
from reflexlearn.llm_gateway.gateway import LLMGateway


async def generate_text(
    llm: LLMGateway,
    messages: list[dict],
    *,
    task_type: str = "generation",
    sink: Optional[Callable[[str], None]] = None,
) -> tuple[str, str]:
    """流式优先生成。sink 非空且 enable_llm_streaming 开 → 逐 delta 推 sink；否则一次性。

    `complete_stream()` 内部已含降级（未产出→回退 complete()、已产出断流→收尾不重复），
    本层只负责把增量喂给 sink + 聚合最终文本。sink 抛错不影响生成（仅丢一次增量推送）。
    """
    if sink is not None and get_settings().enable_llm_streaming:
        parts: list[str] = []
        text = ""
        model_used = ""
        async for chunk in llm.complete_stream(messages, task_type=task_type):
            if chunk.delta:
                parts.append(chunk.delta)
                try:
                    sink(chunk.delta)
                except Exception:
                    pass
            if chunk.done and chunk.completion is not None:
                model_used = chunk.completion.model_used
                text = chunk.completion.text
        return (text or "".join(parts)), model_used

    completion = await llm.complete(messages, task_type=task_type)
    return completion.text, completion.model_used
