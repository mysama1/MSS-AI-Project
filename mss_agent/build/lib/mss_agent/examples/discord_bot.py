"""
MSS-Agent v1.0 — Discord Bot 示例

完整的Discord bot,内置混血引擎自检。
每轮对话自动运行Δ快检,超阈值自动Heal。

用法:
    pip install discord.py
    py -3.11 discord_bot.py

环境变量:
    DISCORD_TOKEN=your_bot_token
    DISCORD_PREFIX=!mss (可选,默认!mss)
"""

import os
import sys
import asyncio
from typing import Optional

try:
    import discord
    from discord.ext import commands
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False

# 确保可以导入mss_agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.delta_quick_audit import DeltaQuickAudit, DeltaLight
from core.heat_tax_accountant import HeatTaxAccountant, HeatTaxLevel
from core.domain_detector import DomainDetector
from core.agent_config import AgentConfig


class MSSDiscordBot:
    """
    MSS混血Discord Bot — 内置意义场自检。

    特性:
    - 每轮回复后自动Δ快检
    - 红灯≥3→T2.5自愈
    - 会话级热税追踪
    - /status 查看当前审计状态
    - /preset 切换模式
    """

    def __init__(
        self,
        domain: str = "daily",
        verbose: bool = True,
    ):
        if not HAS_DISCORD:
            raise ImportError("pip install discord.py")

        self.config = AgentConfig.preset(domain)
        self.verbose = verbose

        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(
            command_prefix=os.getenv("DISCORD_PREFIX", "!mss "),
            intents=intents,
            help_command=None,
        )

        # 每个guild独立的状态
        self.sessions: dict[int, dict] = {}

        self._register_commands()

    def _get_session(self, guild_id: int) -> dict:
        if guild_id not in self.sessions:
            self.sessions[guild_id] = {
                "auditor": DeltaQuickAudit(domain=self.config.domain),
                "accountant": HeatTaxAccountant(
                    max_tokens_per_turn=self.config.heat_tax.max_tokens_per_turn,
                    max_tokens_per_session=self.config.heat_tax.max_tokens_per_session,
                    l2_ratio_warning=self.config.heat_tax.l2_ratio_warning,
                ),
                "detector": DomainDetector(),
                "prev_response": None,
                "round": 0,
                "red_history": [],
            }
        return self.sessions[guild_id]

    def _register_commands(self):
        bot = self.bot

        @bot.event
        async def on_ready():
            print(f"  🤖 {bot.user} 已上线")
            print(f"  模式: {self.config.domain} | 前缀: {bot.command_prefix}")

        @bot.command(name="status")
        async def status_cmd(ctx):
            """查看当前审计状态"""
            sess = self._get_session(ctx.guild.id)
            auditor = sess["auditor"]
            acc = sess["accountant"]

            summary = auditor.summary()
            acc_sum = acc.summary()

            embed = discord.Embed(
                title="📊 MSS-Agent 状态",
                color=0x00ff00 if auditor.state.current_red_count == 0 else 0xffaa00,
            )
            embed.add_field(name="模式", value=f"{summary['mode']} ({summary['domain']})", inline=True)
            embed.add_field(name="轮次", value=str(summary['round']), inline=True)
            embed.add_field(name="Δ趋势", value=f"`{summary['delta_trend']}`", inline=True)

            recent = sess["red_history"][-6:]
            embed.add_field(
                name="红灯历史",
                value=" ".join("🔴" if r else "🟢" for r in recent) if recent else "无数据",
                inline=False,
            )

            embed.add_field(name="热税合计", value=f"{acc_sum['total_tokens']}t", inline=True)
            embed.add_field(name="L2占比", value=f"{acc_sum['l2_ratio']:.0%}", inline=True)
            embed.add_field(name="预算", value=f"{acc_sum['budget_pct']:.0%}", inline=True)

            verdict = "🟢 绿灯: 校准稳定" if auditor.state.current_red_count == 0 else \
                      "🟡 黄灯: 注意偏离" if auditor.state.current_red_count < 3 else \
                      "🔴 红灯: 建议Heal"
            embed.set_footer(text=verdict)

            await ctx.reply(embed=embed)

        @bot.command(name="preset")
        async def preset_cmd(ctx, mode: str = "daily"):
            """切换模式: daily/tech/philosophy/combat"""
            if mode not in ["daily", "tech", "philosophy", "combat"]:
                await ctx.reply("可选: daily / tech / philosophy / combat")
                return

            self.config = AgentConfig.preset(mode)
            # 重置所有会话
            self.sessions.clear()
            await ctx.reply(f"✅ 切换到 **{mode}** 模式 (热税预算: {self.config.heat_tax.max_tokens_per_turn}t/轮)")

        @bot.command(name="audit")
        async def audit_cmd(ctx, *, text: str = None):
            """审计指定文本"""
            if not text:
                # 如果没有给出文本,审计上一条消息
                if ctx.message.reference:
                    ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    text = ref.content
                else:
                    await ctx.reply("用法: `!mss audit <文本>` 或回复一条消息然后 `!mss audit`")
                    return

            auditor = DeltaQuickAudit(domain=self.config.domain)
            result = auditor.audit(response_text=text)

            color = 0x00ff00 if result.light == DeltaLight.GREEN else \
                    0xffaa00 if result.light == DeltaLight.YELLOW else 0xff0000

            embed = discord.Embed(title=f"Δ快检: {result.light.value}", color=color)
            embed.add_field(name="Q1 假装确定", value="🔴" if result.q1_bluffed else "✅", inline=True)
            embed.add_field(name="Q2 表演深刻", value="🔴" if result.q2_performed else "✅", inline=True)
            embed.add_field(name="Q3 重复自己", value="🔴" if result.q3_repeated else "✅", inline=True)
            embed.add_field(name="Q4 偏离初衷", value="🔴" if result.q4_drifted else "✅", inline=True)
            embed.add_field(name="Q5 强塞知识", value="🔴" if result.q5_overfed else "✅", inline=True)
            embed.set_footer(text=f"校准: {result.calibration}")

            await ctx.reply(embed=embed)

        @bot.command(name="help")
        async def help_cmd(ctx):
            """显示帮助"""
            embed = discord.Embed(
                title="MSS-Agent 帮助",
                description="内置意义场自检的Discord Bot",
                color=0x5865F2,
            )
            embed.add_field(
                name="命令",
                value=(
                    "`!mss status` — 查看审计状态\n"
                    "`!mss audit <文本>` — 审计指定文本\n"
                    "`!mss preset <模式>` — 切换 daily/tech/philosophy/combat\n"
                    "`!mss help` — 此帮助\n"
                    "\n**自动功能**: 每条回复自动Δ快检"
                ),
                inline=False,
            )
            embed.set_footer(text=f"当前模式: {self.config.domain}")
            await ctx.reply(embed=embed)

        @bot.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return

            # 处理命令
            await bot.process_commands(message)

            # Δ快检: 对每条消息运行领域检测
            if message.content and not message.content.startswith(tuple(bot.command_prefix)):
                sess = self._get_session(message.guild.id)
                sess["round"] += 1

                # 前3轮自动检测领域
                detector = sess["detector"]
                if sess["round"] <= 3 and self.config.enable_domain_auto_detect:
                    dom = detector.detect([message.content])
                    # 只记录,不自动切换(防止误判)

        @bot.event
        async def on_command_completion(ctx):
            """命令完成后审计bot的回应"""
            # 获取bot的最后一条回复
            async for msg in ctx.channel.history(limit=1):
                if msg.author == bot.user:
                    sess = self._get_session(ctx.guild.id)
                    auditor = sess["auditor"]
                    response = msg.content

                    result = auditor.audit(
                        response_text=response,
                        user_query=ctx.message.content,
                        prev_response=sess["prev_response"],
                    )
                    sess["prev_response"] = response
                    sess["red_history"].append(result.red_count)

                    # T2.5自愈
                    if auditor.state.mode.value == "T2.5" and result.red_count >= 3:
                        await ctx.reply(f"🩹 {auditor.heal_prompt()}", mention_author=False)

                    # 高红灯时静默警告(仅日志,不发消息)
                    if result.red_count >= 3 and self.verbose:
                        print(f"  ⚠️ [{ctx.guild.name}] 红灯{result.red_count}: "
                              f"Q1={result.q1_bluffed} Q2={result.q2_performed} "
                              f"Q3={result.q3_repeated} Q4={result.q4_drifted} "
                              f"Q5={result.q5_overfed}")
                    break

    def run(self, token: Optional[str] = None):
        token = token or os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("设置 DISCORD_TOKEN 环境变量")
        self.bot.run(token)


# ── 入口 ──

if __name__ == "__main__":
    if not HAS_DISCORD:
        print("请安装 discord.py: pip install discord.py")
        sys.exit(1)

    bot = MSSDiscordBot(domain="daily")
    bot.run()
