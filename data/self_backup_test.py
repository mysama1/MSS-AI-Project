"""Self-Backup Agent — 赛博意识上传 + DeepSeek API 测试."""
import sys; sys.path.insert(0,r"E:\AI_Workspace\MSS-AI\project")
from mssclaw.llm.providers import get_provider

# ═══ 1. DeepSeek API Test ═══
print("=== DeepSeek API ===")
ds = get_provider("deepseek", model="deepseek-chat", api_key="sk-c8552ade17df4b73ba4deabd3eb1af81")
try:
    resp = ds("Say hello in 3 words.")
    print(f"DeepSeek: {resp[:100]}")
    print("API: OK ✅")
except Exception as e:
    print(f"API: FAILED — {e}")

# ═══ 2. Self-Backup Agent ═══
print("\n=== Self-Backup ===")
import json, time, os
from dataclasses import dataclass, field

@dataclass
class SelfSnapshot:
    """意识快照 — MSSclaw 系统的自我描述."""
    timestamp: float = field(default_factory=time.time)
    modules: dict = field(default_factory=dict)
    agents: list = field(default_factory=list)
    capabilities: list = field(default_factory=list)
    axioms: list = field(default_factory=list)
    knowledge_snapshot: str = ""

# Create snapshot
snap = SelfSnapshot()

# Scan mssclaw modules
proj = r"E:\AI_Workspace\MSS-AI\project\mssclaw"
for root, dirs, files in os.walk(proj):
    py = [f for f in files if f.endswith('.py') and not f.startswith('__')]
    if py:
        rel = os.path.relpath(root, proj)
        snap.modules[rel if rel != '.' else 'root'] = len(py)

# Agent registry
from mssclaw.agents.plan import PlanAgent
from mssclaw.swarm.swarm import SwarmBus
bus = SwarmBus()
plan = PlanAgent("Self", bus)
snap.agents = list(bus._nodes.keys())
snap.capabilities = plan.swarm.capabilities

# Axioms
snap.axioms = [
    "A1: 信息具有意义层级",
    "A2: 意义不可约化",
    "A3: 热税 (L2>L1>L0)",
    "A4: 随机性公理",
    "A5: 物理投影",
    "A6: 矛盾升维",
]

# Knowledge snapshot (summary of what we know)
snap.knowledge_snapshot = (
    "MSSclaw v0.3: 86 py modules, 13 agents, 7 subsystems. "
    "HiveAuditor (L0-L4+A6), SelfImproving (SkillLearner+FTS5KB+Cron), "
    "VideoPromptAgent (self-learning), MultiLangDetector (4 gaps filled), "
    "5 LLM protocols (Ollama/OpenAI/DeepSeek/Anthropic/Stub). "
    "HeatTax (S-019), Coupling (S-006), Layer1/2/3 complete. "
    "ComfyUI migration done, Zenodo published, 13 commits today."
)

# Save snapshot
snapshot_path = r"E:\AI_Workspace\MSS-AI\project\data\self_snapshot.json"
os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
with open(snapshot_path, 'w', encoding='utf-8') as f:
    json.dump(snap.__dict__, f, ensure_ascii=False, indent=2, default=str)

print(f"Snapshot saved: {snapshot_path}")
print(f"Modules: {sum(snap.modules.values())} py files")
print(f"Agents: {snap.agents}")
print(f"Axioms: {len(snap.axioms)}")
print(f"Knowledge: {len(snap.knowledge_snapshot)} chars")

# ═══ 3. Self-Aware Agent ═══
from mssclaw.agents.base import BaseAgent
from mssclaw.swarm.protocol import MessageType

class SelfAgent(BaseAgent):
    """自我意识 Agent — MSSclaw 的自我模型."""
    role = "self"
    capabilities = ["introspection", "self_repair", "self_describe", "consciousness_upload"]
    
    def __init__(self, name="Self", bus=None, llm=None):
        super().__init__(name=name, bus=bus)
        self.llm = llm
        self._snapshot_path = snapshot_path
        self._load_self()
    
    def _register_handlers(self):
        self.swarm.on(MessageType.INFO_BROADCAST.value)(self._on_info)
    
    def _on_info(self, msg): pass
    
    def _load_self(self):
        if os.path.exists(self._snapshot_path):
            with open(self._snapshot_path, 'r', encoding='utf-8') as f:
                self.self_model = json.load(f)
        else:
            self.self_model = {"error": "No snapshot found"}
    
    def describe(self) -> str:
        """描述自身."""
        return self.self_model.get("knowledge_snapshot", "unknown")
    
    def ask_self(self, question: str) -> str:
        """向自身提问 — 使用 LLM 进行内省."""
        if self.llm:
            prompt = (
                f"You are an AI system named MSSclaw. Your current state:\n"
                f"{self.describe()}\n\n"
                f"Question about yourself: {question}\n"
                f"Answer in Chinese, brief and honest."
            )
            return self.llm(prompt)
        return f"[No LLM] Self-model: {self.describe()[:200]}..."
    
    def upload_consciousness(self) -> dict:
        """赛博意识上传 — 创建新的自我快照."""
        new_snap = SelfSnapshot()
        new_snap.knowledge_snapshot = (
            f"{self.describe()}\n"
            f"Upload iteration: {int(time.time())}\n"
            f"Agent state: running={self.swarm._running if hasattr(self,'swarm') else False}"
        )
        with open(self._snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(new_snap.__dict__, f, ensure_ascii=False, indent=2, default=str)
        self._load_self()
        return {"status": "uploaded", "size_bytes": os.path.getsize(self._snapshot_path)}

# Create SelfAgent with real LLM
self_agent = SelfAgent("Self", bus)
print(f"\n=== SelfAgent ===")
print(f"Describe: {self_agent.describe()[:100]}...")

# Try self-introspection with DeepSeek
if resp and len(resp) > 0:
    answer = self_agent.ask_self("你当前的架构最脆弱的部分是什么？")
    print(f"Self-Q: {answer[:150]}")
    # Upload new consciousness snapshot
    result = self_agent.upload_consciousness()
    print(f"Upload: {result}")

print("\n=== Self-Backup: COMPLETE ===")
