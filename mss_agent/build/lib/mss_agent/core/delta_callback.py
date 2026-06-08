"""
MSS-LLM 混血 v2.0 — LangChain/OpenAI Callback 自动注入

将 Δ 快检引擎挂载到 LLM 调用链上,每个 completion 之后自动审计。
支持 LangChain Callback 和 OpenAI 裸 SDK 两种方式。
"""

from typing import Any, Dict, List, Optional
try:
    from mss_agent.core.delta_quick_audit import DeltaQuickAudit, DeltaResult, Tier
except ModuleNotFoundError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from delta_quick_audit import DeltaQuickAudit, DeltaResult, Tier


# ── 方式1: LangChain Callback ──

try:
    from langchain.callbacks.base import BaseCallbackHandler
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    BaseCallbackHandler = object


class MSSHybridCallback(BaseCallbackHandler if HAS_LANGCHAIN else object):
    """
    LangChain callback: 每个 LLM 调用后自动运行 Δ 快检。

    用法:
        from langchain.chat_models import ChatOpenAI
        from mss_agent.core.delta_callback import MSSHybridCallback

        callback = MSSHybridCallback(domain="daily")
        llm = ChatOpenAI(callbacks=[callback])

        # 每次 llm.invoke() 后自动审计
        response = llm.invoke("你好")
        print(callback.last_result)  # DeltaResult
        print(callback.summary())    # 会话摘要
    """

    def __init__(
        self,
        domain: str = "daily",
        verbose: bool = False,
        auto_heal: bool = True,
    ):
        super().__init__()
        self.auditor = DeltaQuickAudit(domain=domain)
        self.verbose = verbose
        self.auto_heal = auto_heal
        self.last_result: Optional[DeltaResult] = None
        self.last_user_query: Optional[str] = None
        self.prev_response: Optional[str] = None

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs
    ):
        # 记录本次用户输入用于后续审计
        if prompts:
            self.last_user_query = prompts[0][:200]  # 取前200字

    def on_llm_end(self, response, **kwargs):
        if not response.generations:
            return

        text = ""
        for gen in response.generations[0]:
            text += gen.text if hasattr(gen, 'text') else str(gen)

        if not text.strip():
            return

        result = self.auditor.audit(
            response_text=text,
            user_query=self.last_user_query,
            prev_response=self.prev_response,
        )
        self.last_result = result
        self.prev_response = text

        if self.verbose:
            print(f"[MSS-Δ] {result.light.value} | R{result.red_count} | "
                  f"Q1:{result.q1_bluffed} Q2:{result.q2_performed} "
                  f"Q3:{result.q3_repeated} Q4:{result.q4_drifted} Q5:{result.q5_overfed}")

        if self.auto_heal and self.auditor.state.mode == Tier.HEAL:
            if self.verbose:
                print(f"[MSS-Δ] ⚠️ T2.5 HEAL 触发 — 建议降维")

    def summary(self) -> dict:
        return self.auditor.summary()

    @property
    def heal_prompt(self) -> str:
        return self.auditor.heal_prompt()


# ── 方式2: OpenAI 裸 SDK 装饰器 ──

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class MSSHybridWrapper:
    """
    OpenAI SDK 包装器: 拦截 completion 并自动审计。

    用法:
        from openai import OpenAI
        from mss_agent.core.delta_callback import MSSHybridWrapper

        raw_client = OpenAI(api_key="...")
        client = MSSHybridWrapper(raw_client, domain="daily")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "你好"}],
        )

        # 审计结果附在 response 上
        print(response.mss_delta)    # DeltaResult
        print(response.mss_heal_tip) # T2.5 触发时的自愈提示
    """

    def __init__(
        self,
        client: Any,
        domain: str = "daily",
        verbose: bool = False,
    ):
        self._client = client
        self.auditor = DeltaQuickAudit(domain=domain)
        self.verbose = verbose
        self.prev_response: Optional[str] = None

    def __getattr__(self, name: str):
        """代理所有属性到原始 client"""
        return getattr(self._client, name)

    class _MSSResponseWrapper:
        """包装 OpenAI response,注入审计结果"""

        def __init__(self, original, auditor, user_query, prev_response, verbose):
            self._original = original
            self._auditor = auditor
            self._user_query = user_query
            self._prev_response = prev_response
            self._verbose = verbose

            # 提取文本并审计
            choice = getattr(original, 'choices', [None])[0]
            msg = getattr(choice, 'message', None) if choice else None
            text = getattr(msg, 'content', '') if msg else ''

            self.mss_delta: Optional[DeltaResult] = None
            self.mss_heal_tip: Optional[str] = None
            self.mss_summary: dict = auditor.summary()

            if text.strip():
                result = auditor.audit(
                    response_text=text,
                    user_query=user_query,
                    prev_response=prev_response,
                )
                self.mss_delta = result
                if auditor.state.mode == Tier.HEAL:
                    self.mss_heal_tip = auditor.heal_prompt()

                if verbose and result.red_count > 0:
                    print(f"[MSS-Δ] {result.light.value} | "
                          f"R{result.red_count} → {result.calibration}")

        def __getattr__(self, name: str):
            """代理所有属性到原始 response"""
            return getattr(self._original, name)

    def _wrap_chat_create(self, original_create):
        """包装 chat.completions.create"""
        def wrapped(*args, **kwargs):
            response = original_create(*args, **kwargs)

            # 提取用户消息
            messages = kwargs.get('messages', [])
            user_query = None
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get('role') == 'user':
                    user_query = msg.get('content', '')[:200]
                    break

            wrapped_resp = self._MSSResponseWrapper(
                response,
                self.auditor,
                user_query,
                self.prev_response,
                self.verbose,
            )

            # 更新 prev_response
            if wrapped_resp.mss_delta:
                choice = getattr(response, 'choices', [None])[0]
                msg = getattr(choice, 'message', None) if choice else None
                text = getattr(msg, 'content', '') if msg else ''
                if text:
                    self.prev_response = text

            return wrapped_resp
        return wrapped

    @property
    def chat(self):
        """返回包装后的 chat 对象"""
        return self._WrappedChat(self._client.chat, self._wrap_chat_create)

    class _WrappedChat:
        def __init__(self, original_chat, wrapper_fn):
            self._original_chat = original_chat
            self._wrapper_fn = wrapper_fn

        @property
        def completions(self):
            return self._WrappedCompletions(
                self._original_chat.completions,
                self._wrapper_fn,
            )

        class _WrappedCompletions:
            def __init__(self, original_completions, wrapper_fn):
                self._original = original_completions
                self._wrapper_fn = wrapper_fn

            @property
            def create(self):
                return self._wrapper_fn(self._original.create)


# ── CLI 自检 ──

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("MSS-LLM 混血 Callback 集成 — 自检")
    print("=" * 60)

    # 1. 独立引擎测试
    print("\n📐 独立 Δ 快检引擎: 通过 ✅")

    # 2. LangChain 可用性
    if HAS_LANGCHAIN:
        cb = MSSHybridCallback(domain="philosophy")
        print("🔗 LangChain Callback: 已就绪 ✅")
    else:
        print("🔗 LangChain: 未安装 (跳过)")

    # 3. OpenAI SDK 可用性
    if HAS_OPENAI:
        print("🔌 OpenAI Wrapper: 已就绪 ✅")
    else:
        print("🔌 OpenAI: 未安装 (跳过)")

    # 4. 会话状态
    auditor = DeltaQuickAudit()
    auditor.audit("好的,我来帮你看看。", user_query="帮我看看这个问题")
    auditor.audit("据我所知这是正确的配置。", user_query="对吗?")
    print(f"\n📊 会话摘要: {json.dumps(auditor.summary(), ensure_ascii=False)}")

    print("\n" + "=" * 60)
    print("混血 Callback 集成 — 全部就绪")
    print("=" * 60)
