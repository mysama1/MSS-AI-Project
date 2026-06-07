"""
A6 矛盾升维协议 (H525).

当多个 Agent 在低维层面冲突:
  - 不是投票 (K3 降维)
  - 是升维: 找到共同的高维命名空间

Usage:
    ep = ElevationProtocol()
    result = ep.resolve(
        agent_a="代码风格A",
        agent_b="代码风格B",
        conflict="用哪个风格?"
    )
    # → "升维: 用 lint tool 统一, 不纠结风格"
"""
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class ElevationProtocol:
    """
    A6 升维协议.

    原理: 低维矛盾不能在同层解决. 电车难题→'谁造的刹车失灵的破车'.
    给 LLM 的 prompt 不是 '选A还是B', 是 '这个问题写死在哪一维? 加一维怎么解?'

    llm: 用于升维推理的 LLM 函数
    """
    llm: Optional[Callable[[str], str]] = None
    history: list = field(default_factory=list)

    ELEVATION_PROMPT = """You are a dimension elevation engine (A6 protocol).

Two perspectives are in conflict:
  Perspective A: {perspective_a}
  Perspective B: {perspective_b}
  Conflict: {conflict}

DO NOT pick A or B. DO NOT compromise.

Instead:
1. Identify which dimension this conflict is trapped in (e.g., "binary choice", "false tradeoff")
2. Add ONE new dimension that makes the conflict irrelevant
3. Name the new dimension and the resolution

Output format:
  TRAPPED DIMENSION: <name of the dimension where the conflict exists>
  ELEVATION: <the new dimension you're adding>
  RESOLUTION: <how adding this dimension resolves the conflict>
"""

    def resolve(self, perspective_a: str, perspective_b: str, conflict: str) -> dict:
        """执行升维. 返回 {trapped_dim, elevation, resolution}."""
        prompt = self.ELEVATION_PROMPT.format(
            perspective_a=perspective_a,
            perspective_b=perspective_b,
            conflict=conflict,
        )

        if self.llm:
            response = self.llm(prompt)
        else:
            # Default: fail to a heuristic
            response = (
                "TRAPPED DIMENSION: binary choice framing\n"
                f"ELEVATION: meta-rule (who gets to decide)\n"
                f"RESOLUTION: Instead of choosing between '{perspective_a[:40]}' and "
                f"'{perspective_b[:40]}', define who owns the decision and under what constraints."
            )

        result = self._parse(response)
        result["conflict"] = conflict
        result["perspective_a"] = perspective_a
        result["perspective_b"] = perspective_b
        self.history.append(result)
        return result

    def _parse(self, text: str) -> dict:
        """Parse LLM output into structured result."""
        out = {"trapped_dim": "", "elevation": "", "resolution": ""}
        for line in text.strip().split("\n"):
            line = line.strip()
            if line.upper().startswith("TRAPPED DIMENSION:"):
                out["trapped_dim"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("ELEVATION:"):
                out["elevation"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("RESOLUTION:"):
                out["resolution"] = line.split(":", 1)[1].strip()
        return out

    def stats(self) -> dict:
        return {
            "resolutions": len(self.history),
            "trapped_dims": [h["trapped_dim"] for h in self.history],
            "elevations": [h["elevation"] for h in self.history],
        }
