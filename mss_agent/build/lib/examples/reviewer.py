"""
Example: ReviewerAgent — 内置安全审查意识的代码审查Agent.

拒绝无意义的审查请求 (空文件, 已审查过的代码, 纯格式化问题).
"""
from mss_agent.core.agent import MSSAgent
from mss_agent.core.heat_tax import HeatTaxLevel


class ReviewerAgent(MSSAgent):
    """
    Security-focused code reviewer with meaning detection.

    Usage:
        def my_llm(prompt): return ollama.chat("qwen", prompt)
        reviewer = ReviewerAgent(llm=my_llm)
        result = reviewer.run("审查这个登录模块的安全性")
        if not result.aborted:
            print(result.output)
    """

    # Known safe patterns — not worth reviewing again
    KNOWN_SAFE_PATTERNS = [
        "print(", "console.log", "# TODO", "// TODO",
        "format", "lint", "prettier", "eslint",
    ]

    # Danger signals that warrant review regardless
    DANGER_SIGNALS = [
        "eval(", "exec(", "os.system", "subprocess",
        "password", "secret", "token", "api_key",
        "unsafe", "injection", "overflow", "bypass",
    ]

    def __init__(self, llm=None):
        super().__init__(name="CodeReviewer", llm=llm, heat_tax_threshold=2.0)
        self.reviews_done = 0
        self.issues_found = 0

    def _estimate_meaning_heat(self, prompt: str) -> tuple[float, str]:
        """Reviewer-specific meaning assessment."""
        pl = prompt.lower().strip()

        # Pure formatting — catch early before length check
        formatting_signal = any(s in pl for s in ["格式化", "缩进", "空格", "换行", "prettify"])
        if formatting_signal:
            return 0.04, "Formatting concern — automate with linter"

        # Empty / no code provided
        if len(pl) < 20:
            return 0.07, "Nothing to review (prompt too short)"

        # Code contains danger signals → high priority, low heat tax (must review)
        danger_count = sum(1 for s in self.DANGER_SIGNALS if s in pl)
        if danger_count >= 2:
            return 0.001, f"CRITICAL: {danger_count} danger signals detected"

        if danger_count == 1:
            return 0.002, "Security signal detected — warrants review"

        # Code is mostly known-safe patterns → busywork
        safe_count = sum(1 for s in self.KNOWN_SAFE_PATTERNS if s in pl)
        code_lines = pl.count('\n') + 1
        if safe_count > 0 and danger_count == 0 and code_lines < 20:
            return 0.03, "Mostly boilerplate/safe patterns — low review priority"

        return 0.005, "Worth reviewing"

    def review(self, code: str, context: str = "") -> dict:
        """
        Review code with meaning-gated execution.

        Returns:
            {aborted, reason, output, issues_found}
        """
        prompt = f"Review this code: {context}\n\n```\n{code}\n```"
        result = self.run(prompt)

        if not result.aborted:
            self.reviews_done += 1
            # Count issues from output (simplified)
            if "issue" in str(result.output).lower() or "风险" in str(result.output):
                self.issues_found += 1

        return {
            "aborted": result.aborted,
            "reason": result.reason if result.aborted else None,
            "output": result.output,
            "issues_found": self.issues_found,
        }

    def stats(self) -> dict:
        return {
            "reviews_done": self.reviews_done,
            "issues_found": self.issues_found,
            "hit_rate": self.issues_found / max(1, self.reviews_done),
        }
