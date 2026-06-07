"""
Example: AnalystAgent — 数据分析Agent, 内置统计显著性检测.

拒绝:
  - 样本量过小的分析 (<10)
  - 无对照组的数据请求
  - p-hacking 模式 (反复测试同一数据)
"""
from mss_agent.core.agent import MSSAgent
from mss_agent.core.heat_tax import HeatTaxLevel


class AnalystAgent(MSSAgent):
    """
    Data analyst with statistical rigor gates.

    Usage:
        def my_llm(prompt): return ollama.chat("qwen", prompt)
        analyst = AnalystAgent(llm=my_llm)
        result = analyst.analyze("分析这个A/B测试结果", data_df)
    """

    MIN_SAMPLE_SIZE = 10
    MAX_REPEATED_QUERIES = 3  # p-hacking guard

    def __init__(self, llm=None):
        super().__init__(name="DataAnalyst", llm=llm, heat_tax_threshold=2.0)
        self.query_history = {}
        self.analyses_done = 0
        self.aborted_count = 0

    def _estimate_meaning_heat(self, prompt: str) -> tuple[float, str]:
        """Analyst-specific meaning assessment."""
        pl = prompt.lower().strip()

        # Check for sample size FIRST (before length check, n=5 is informative even if short)
        import re
        n_match = re.search(r'n\s*[=＝]\s*(\d+)', pl)
        if n_match:
            n = int(n_match.group(1))
            if n < self.MIN_SAMPLE_SIZE:
                return 0.05, f"Sample too small (n={n} < {self.MIN_SAMPLE_SIZE})"

        # Empty / trivial
        if len(pl) < 15:
            return 0.07, "Query too short for meaningful analysis"

        # Check for "control group" or 对照组
        has_experiment = any(s in pl for s in ["a/b", "实验", "对照组", "control", "treatment"])
        has_control = any(s in pl for s in ["对照组", "control", "baseline"])
        if has_experiment and not has_control:
            return 0.03, "Experiment mentioned but no control group — results may be invalid"

        # Check for repeated query (p-hacking guard)
        query_hash = hash(pl) % 10000
        self.query_history[query_hash] = self.query_history.get(query_hash, 0) + 1
        if self.query_history[query_hash] > self.MAX_REPEATED_QUERIES:
            return 0.06, f"Same query repeated {self.query_history[query_hash]}x — possible p-hacking"

        # Meaningful analysis signals
        meaning = sum(1 for s in ["分析", "趋势", "相关", "显著性", "分布",
                                   "correlation", "significance", "trend", "regression"] if s in pl)
        if meaning >= 2:
            return 0.002, f"Statistical analysis ({meaning} signals)"

        if meaning >= 1:
            return 0.005, "Analysis intent detected"

        return 0.01, "Neutral data query"

    def analyze(self, question: str, data_description: str = "", sample_size: int = None) -> dict:
        """
        Analyze data with meaning-gated execution.

        Args:
            question: What to analyze
            data_description: Brief description of the dataset
            sample_size: If known, n value of the dataset

        Returns:
            {aborted, reason, output, sample_warning}
        """
        prompt = question
        if data_description:
            prompt += f"\nData: {data_description}"
        if sample_size:
            prompt += f"\nn={sample_size}"

        result = self.run(prompt)

        if not result.aborted:
            self.analyses_done += 1
        else:
            self.aborted_count += 1

        return {
            "aborted": result.aborted,
            "reason": result.reason if result.aborted else None,
            "output": result.output,
            "sample_warning": sample_size is not None and sample_size < self.MIN_SAMPLE_SIZE,
        }

    def stats(self) -> dict:
        return {
            "analyses_done": self.analyses_done,
            "aborted": self.aborted_count,
            "accept_rate": self.analyses_done / max(1, self.analyses_done + self.aborted_count),
        }
