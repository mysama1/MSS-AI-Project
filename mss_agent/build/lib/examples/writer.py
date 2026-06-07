"""
Example: Writer Agent — 内置热税预算的写作助手.

拒绝无意义写作任务 (empty prompt, pure paraphrasing, etc.)
"""
from mss_agent.core.agent import MSSAgent
from mss_agent.core.heat_tax import HeatTaxLevel, HeatTaxAbort


class WriterAgent(MSSAgent):
    """
    Writer Agent 示例.

    Usage:
        def my_llm(prompt): return ollama.chat("qwen", prompt)
        writer = WriterAgent(llm=my_llm)
        result = writer.run("写一篇关于开源精神的文章")
        if not result.aborted:
            print(result.output)
        writer.health_report()
    """

    def __init__(self, llm=None):
        super().__init__(name="Writer", llm=llm, heat_tax_threshold=1.5)
        self.style_guide = "简洁、准确、有人味"

    def _estimate_meaning_heat(self, prompt: str) -> tuple[float, str]:
        """Writer-specific meaning assessment."""
        prompt_lower = prompt.lower().strip()

        # Empty / trivial
        if len(prompt) < 10:
            return 0.09, "Prompt too short: likely a throwaway task"

        # Pure paraphrasing
        paraphrase_signals = ["改写", "重新说", "换个写法", "rewrite", "rephrase"]
        if any(s in prompt_lower for s in paraphrase_signals):
            if "因为" not in prompt_lower and "because" not in prompt_lower:
                return 0.06, "Pure paraphrasing without stated reason"

        # Meaningful writing
        creation_signals = ["写", "创作", "生成", "write", "create", "draft", "compose"]
        if any(s in prompt_lower for s in creation_signals) and len(prompt) > 30:
            return 0.003, "Creative writing task"

        return 0.01, "Neutral writing task"
