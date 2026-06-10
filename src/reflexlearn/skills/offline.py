"""LLM 不可用时的离线降级内容生成。

生成类 Skill 的 try 块只包 LLMGateway.complete 调用，因此调用抛出的任何异常
（未配置 key、key 失效如中转站 403 GROUP_DISABLED、网络不可达、网关 5xx）
都意味着「本次 LLM 不可用」，各 Skill 统一调用此处函数产出结构化占位内容，保证：
- 端到端链路在离线 / 无凭证 / 凭证失效环境下行为一致，仍能产出多模态资源；
- 内容长度足以通过质量校验的规则兜底（len > 50）；
- mindmap 产出合法 Mermaid 语法、code 产出带语言标注的代码块；
- 降级有日志与 degraded_from 标注，绝不假装真实生成。
LLM 恢复可用后自动切换为真实生成，本模块不再生效。
"""

import logging

OFFLINE_TAG = "no_api_key"

logger = logging.getLogger(__name__)


def log_llm_fallback(skill_name: str, exc: Exception) -> None:
    """记录一次「LLM 不可用 → 离线占位」降级，无 key 走 info、其余异常走 warning。"""
    if OFFLINE_TAG in str(exc):
        logger.info("%s degraded (no api key) -> offline content", skill_name)
    else:
        logger.warning(
            "%s degraded (llm %s: %s) -> offline content",
            skill_name,
            type(exc).__name__,
            str(exc)[:120],
        )


def _concept(spec: dict) -> str:
    return ", ".join(spec.get("concept_ids", ["该主题"]))


def _refine_block(spec: dict) -> str:
    issues = [str(item).strip() for item in spec.get("previous_issues", []) if str(item).strip()]
    if not issues:
        return ""
    notes = "\n".join(f"- {item}" for item in issues)
    return f"\n\n### 元认知修复建议\n{notes}"


def offline_content(kind: str, spec: dict) -> str:
    """按资源类型产出离线占位内容。kind ∈ {doc, quiz, mindmap, code, reading, video}。"""
    concept = _concept(spec)

    if kind == "mindmap":
        return (
            "mindmap\n"
            f"  root(({concept}))\n"
            "    核心概念\n"
            "      定义与直觉\n"
            "    关键方法\n"
            "      典型步骤\n"
            "    常见误区\n"
            "    练习方向\n"
        )

    if kind == "code":
        return (
            f"# {concept} · 代码案例（离线占位）\n\n"
            "```python\n"
            "import numpy as np\n\n"
            f"# 演示 {concept} 的最小可运行骨架\n"
            "def demo(x: np.ndarray) -> np.ndarray:\n"
            "    return x\n\n"
            'if __name__ == "__main__":\n'
            "    print(demo(np.arange(5)))\n"
            "```\n\n"
            "> 当前为离线降级内容，配置 LLM API Key 后将生成完整可运行案例与讲解。"
        )

    if kind == "quiz":
        return (
            f"## {concept} · 练习题（离线占位）\n\n"
            f"1. 用一句话概括 {concept} 的核心思想。\n"
            f"2. {concept} 适用于哪些典型场景？请举例说明。\n"
            f"3. 实现 {concept} 时常见的陷阱有哪些？如何规避？\n\n"
            "> 配置 LLM API Key 后将生成带难度标签、标准答案与详细解析的题目。"
        )

    if kind == "reading":
        return (
            f"## {concept} · 拓展阅读（离线占位）\n\n"
            "- 📘 经典教材相关章节 —— 打牢基础\n"
            "- 📄 领域综述论文 —— 建立全局视角\n"
            "- 💻 开源实现仓库 —— 对照代码加深理解\n\n"
            "> 配置 LLM API Key 后将生成精选、分级的阅读清单与推荐理由。"
        )

    if kind == "video":
        return (
            f"## {concept} · 多模态视频分镜脚本（离线占位）\n\n"
            "> 🎬 以下为视频分镜脚本，配置视频生成服务（如 SeeDance）后将渲染为讲解视频 / 动画。\n\n"
            "**时长**：约 3 分钟 ｜ **风格**：动画讲解 + 旁白\n\n"
            "### 分镜 1 · 开场（0:00–0:20）\n"
            f"- 画面：{concept} 标题动画，抛出核心问题\n"
            f"- 旁白：用一句话点明 {concept} 要解决的问题。\n\n"
            "### 分镜 2 · 概念可视化（0:20–1:30）\n"
            f"- 画面：动态图示逐层拆解 {concept} 的核心机制\n"
            "- 旁白：分步讲解关键直觉，配合动画展开。\n\n"
            "### 分镜 3 · 实例演示（1:30–2:30）\n"
            "- 画面：一个典型例子的动态推演\n"
            f"- 旁白：结合具体数据 / 场景展示 {concept} 如何运作。\n\n"
            "### 分镜 4 · 小结（2:30–3:00）\n"
            "- 画面：要点回顾卡片 + 延伸问题\n"
            "- 旁白：总结 3 个要点，引出下一步学习方向。\n"
        )

    # doc 及默认
    return (
        f"## {concept}\n\n"
        f"本节介绍 **{concept}** 的核心概念、关键直觉与学习要点。\n\n"
        "### 概念定义\n"
        f"{concept} 的基本定义与适用范围。\n\n"
        "### 关键直觉\n"
        "用通俗的方式理解其工作原理与设计动机。\n\n"
        "### 要点总结\n"
        "- 核心思想\n"
        "- 典型应用场景\n"
        "- 实践注意事项\n\n"
        f"{_refine_block(spec)}\n\n"
        "> 当前为离线降级内容，配置 LLM API Key 后将生成结构化的完整讲解文档。"
    )
