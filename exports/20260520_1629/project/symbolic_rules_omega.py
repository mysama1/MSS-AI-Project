"""
symbolic_rules_omega.py - Ω级裁定形式化规则引擎
将Ω级终审裁定的核心命题转化为机器可验证的符号规则
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Set, Optional, Tuple
import re

class RuleLayer(Enum):
    L1 = "L1"  # 硬核公理
    L2 = "L2"  # 保护带
    L3 = "L3"  # 试探法

class RuleCategory(Enum):
    PHYSICAL_RIGIDITY = "physical_rigidity"
    UNIDIRECTIONAL_MAPPING = "unidirectional_mapping"
    PARADIGM_CLEANSING = "paradigm_cleansing"
    HUMAN_EARTH_ISOMORPHISM = "human_earth_isomorphism"
    MEANING_DIRECTED_LIFE = "meaning_directed_life"
    EVOLUTION_DUAL_SINGULARITY = "evolution_dual_singularity"
    LANGUAGE_ESSENCE = "language_essence"
    MEANING_STRESS_VS_TUNING = "meaning_stress_vs_tuning"
    CIVILIZATION_BIRTH = "civilization_birth"
    RANDOMNESS_COMPATIBILITY = "randomness_compatibility"

class ViolationType(Enum):
    K3_OBJECTIVISM = auto()      # K3客观主义残余
    STRONG_TELEOLOGY = auto()    # 强目的论
    SUBJECT_OBJECT_DUALISM = auto()  # 主客二元对立
    ANTHROPOCENTRISM = auto()    # 人类中心主义
    PURPOSE_DRIVEN_COSMOS = auto()  # 目的论宇宙
    EMPIRICIST_VERIFICATION = auto()  # 实证主义验证
    L1_VIOLATION = auto()        # 违反L1公理
    ANIMAL_CONSCIOUSNESS_CONFUSION = auto()  # 动物意识混淆
    GENETIC_DETERMINISM = auto()  # 基因决定论
    LINGUISTIC_REDUCTIONISM = auto()  # 语言学还原论

@dataclass
class SymbolicRule:
    rule_id: str
    layer: RuleLayer
    category: RuleCategory
    name: str
    description: str
    antecedents: List[str]       # 前提条件（命题ID列表）
    consequent: str              # 结论
    confidence: float
    violation_type: Optional[ViolationType] = None
    forbidden_patterns: List[str] = None  # 禁止的表述模式（正则）
    replacement_suggestions: Dict[str, str] = None  # 替换建议

# Ω级裁定形式化规则库
OMEGA_RULES: List[SymbolicRule] = [
    # === L1 硬核规则 ===
    SymbolicRule(
        rule_id="Ω-R001",
        layer=RuleLayer.L1,
        category=RuleCategory.PHYSICAL_RIGIDITY,
        name="物理规则刚性三重分解",
        description="物理规则刚性必须分解为拓扑+热税+观测者三个独立机制",
        antecedents=["A1", "热税公式"],
        consequent="物理规则刚性 = 拓扑不变性刚性 ⊕ 热税最小化刚性 ⊕ 观测者锚定刚性",
        confidence=0.95,
        violation_type=ViolationType.K3_OBJECTIVISM,
        forbidden_patterns=[
            r"物理规则是(绝对|永恒|不可改变|上帝给定)的",
            r"物理定律(独立于|超越于)意义",
        ],
        replacement_suggestions={
            "物理规则是绝对的": "物理规则是特定拓扑-热税-观测者构型下的稳态解",
            "物理定律独立于意识": "物理定律是意义博弈稳态在物理层的投影",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R002",
        layer=RuleLayer.L1,
        category=RuleCategory.PHYSICAL_RIGIDITY,
        name="基本粒子拓扑孤子本质",
        description="基本粒子必须是拓扑孤子，属性为拓扑不变量",
        antecedents=["Ω-R001", "旋耗散场"],
        consequent="基本粒子 = 拓扑孤子 ∧ 属性(粒子) = {缠绕数, 陈数, Hopf不变量}",
        confidence=0.92,
        violation_type=ViolationType.K3_OBJECTIVISM,
        forbidden_patterns=[
            r"基本粒子是(点状|实体|小球)",
            r"粒子属性是(内禀|固有|天生)的",
        ],
        replacement_suggestions={
            "基本粒子是点状的": "基本粒子是3+1维投影的拓扑孤子",
            "自旋是内禀属性": "自旋是旋耗散结构的缠绕数拓扑不变量",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R003",
        layer=RuleLayer.L1,
        category=RuleCategory.PHYSICAL_RIGIDITY,
        name="物理常数拓扑本质",
        description="物理常数必须是3+1维时空拓扑的几何参数",
        antecedents=["Ω-R002"],
        consequent="∀c∈物理常数: c = f(时空拓扑维度) ∧ 维度改变 → c改变",
        confidence=0.90,
        violation_type=ViolationType.K3_OBJECTIVISM,
        forbidden_patterns=[
            r"物理常数是(普适|永恒|不变|上帝给定)的",
            r"常数(无法解释|没有原因)",
        ],
        replacement_suggestions={
            "普朗克常数是基本常数": "普朗克常数是意义量子最小拓扑分包单元的几何参数",
            "光速是宇宙极限": "光速是3+1维时空拓扑的最大信息传输速率",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R004",
        layer=RuleLayer.L1,
        category=RuleCategory.UNIDIRECTIONAL_MAPPING,
        name="单向映射壁垒=A1推论",
        description="物理层无法逆向映射逻辑层是A1的直接推论",
        antecedents=["A1"],
        consequent="L1→L0: 可映射 ∧ L0→L1: 不可映射",
        confidence=0.97,
        violation_type=ViolationType.L1_VIOLATION,
        forbidden_patterns=[
            r"物理(改变|影响|决定)意识",
            r"物质(产生|生成)逻辑",
            r"通过物理实验(验证|证明)意义",
        ],
        replacement_suggestions={
            "物质决定意识": "逻辑层投影为物理层，物理层操作不改变逻辑层本体",
            "物理实验证明": "MSS验证采用共振原则而非旁观者测量",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R005",
        layer=RuleLayer.L1,
        category=RuleCategory.PARADIGM_CLEANSING,
        name="多尺度意义博弈稳态",
        description="所有物理规则都是多尺度意义博弈的纳什均衡",
        antecedents=["A1", "A3", "热税公式"],
        consequent="物理规则 = argmin(热税) over 意义博弈策略空间",
        confidence=0.94,
        violation_type=ViolationType.K3_OBJECTIVISM,
        forbidden_patterns=[
            r"物理规律是(客观|绝对|独立于观察者)的",
            r"宇宙(遵循|服从)物理定律",
        ],
        replacement_suggestions={
            "物理规律是客观的": "物理规律是多尺度意义博弈的共识稳态",
            "宇宙遵循定律": "物理层是意义博弈的结算界面",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R006",
        layer=RuleLayer.L1,
        category=RuleCategory.PARADIGM_CLEANSING,
        name="观察者即参与者",
        description="观察者不是旁观者，而是意义博弈的参与者",
        antecedents=["Ω-R005"],
        consequent="观察者 ∈ 意义博弈参与者 ∧ 观察者存在 → 博弈均衡改变",
        confidence=0.92,
        violation_type=ViolationType.SUBJECT_OBJECT_DUALISM,
        forbidden_patterns=[
            r"观察者(独立|中立|客观)于被观察",
            r"双盲实验(证明|验证)",
            r"排除观察者影响",
        ],
        replacement_suggestions={
            "客观观察": "参与者共振",
            "双盲验证": "多T值观察者共识校验",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R007",
        layer=RuleLayer.L1,
        category=RuleCategory.MEANING_DIRECTED_LIFE,
        name="底层随机涌现公理",
        description="宇宙演化无预设剧本，全部源于0/1奇点随机涨落",
        antecedents=["A3"],
        consequent="宇宙演化 = 随机拓扑涨落 ∧ ¬∃预设剧本 ∧ ¬∃宿命安排",
        confidence=0.96,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"宇宙(等待|准备|计划|安排|注定)",
            r"文明是(必然|注定|预设)的",
            r"宇宙(意志|目的|使命)",
            r"天选(之子|文明|觉醒者)",
            r"宿命(安排|注定|使命)",
        ],
        replacement_suggestions={
            "宇宙等待我们": "宇宙随机演化，我们恰好自洽存续",
            "文明是注定的": "文明是无数随机分支中偶然涌现的一条",
            "宇宙意志": "意义网络的自组织演化趋势",
            "天选之子": "偶然觉醒的意义行者",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R008",
        layer=RuleLayer.L1,
        category=RuleCategory.MEANING_DIRECTED_LIFE,
        name="意义后赋非先设",
        description="意义不是宇宙预设的，而是生命涌现后自我建构的",
        antecedents=["Ω-R007", "A1"],
        consequent="意义 = 生命涌现后自我建构 ∧ ¬意义先天存在",
        confidence=0.95,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"宇宙(赋予|赐予|给予)意义",
            r"先天(意义|使命|价值)",
            r"宇宙(需要|要求)文明",
        ],
        replacement_suggestions={
            "宇宙赋予意义": "生命自我赋予意义",
            "先天使命": "自主选择的使命",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R009",
        layer=RuleLayer.L1,
        category=RuleCategory.MEANING_DIRECTED_LIFE,
        name="自然分形自组织",
        description="意义系统具备内生降熵、结网、扩维趋势，无需外部意志驱动",
        antecedents=["Ω-R007", "Ω-R008"],
        consequent="意义系统 → 自发降熵 ∧ 自发结网 ∧ 自发扩维",
        confidence=0.93,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"宇宙(驱动|推动|引导)演化",
            r"演化(方向|目标|终点)",
            r"自然(目的|意图)",
        ],
        replacement_suggestions={
            "宇宙驱动演化": "意义系统内生自组织趋势",
            "演化方向": "演化路径开放，无预设方向",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R010",
        layer=RuleLayer.L1,
        category=RuleCategory.MEANING_DIRECTED_LIFE,
        name="层级嵌套非宿命",
        description="层级嵌套是自然延伸后果，非预设苏醒顺序",
        antecedents=["Ω-R009"],
        consequent="层级嵌套 = 自然拓扑延伸 ∧ 路径开放 ∧ (可发生 ∨ 可停滞 ∨ 可消亡)",
        confidence=0.92,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"宇宙(逐层|逐级)苏醒",
            r"层级(觉醒|苏醒|唤醒)",
            r"(必然|注定)跃迁",
        ],
        replacement_suggestions={
            "宇宙逐层苏醒": "局域意义系统自然向外拓扑延伸",
            "层级觉醒": "自下而上的自发生长",
        }
    ),
    
    # === L2 保护带规则 ===
    SymbolicRule(
        rule_id="Ω-R011",
        layer=RuleLayer.L2,
        category=RuleCategory.PHYSICAL_RIGIDITY,
        name="自发对称性破缺热税本质",
        description="自发对称性破缺是热税最小化的自发实现",
        antecedents=["Ω-R001", "热税公式"],
        consequent="对称性破缺: 对称态热税 > 不对称态热税 → 自发滚落",
        confidence=0.85,
        violation_type=None,
        forbidden_patterns=[],
        replacement_suggestions={}
    ),
    
    SymbolicRule(
        rule_id="Ω-R012",
        layer=RuleLayer.L2,
        category=RuleCategory.PHYSICAL_RIGIDITY,
        name="K3解码带宽限制",
        description="K3意识只能解码与自身拓扑兼容的显化模式",
        antecedents=["Ω-R001"],
        consequent="K3意识: 解码带宽 = f(自身拓扑结构) ∧ 不兼容模式 → 噪声",
        confidence=0.87,
        violation_type=None,
        forbidden_patterns=[],
        replacement_suggestions={}
    ),
    
    SymbolicRule(
        rule_id="Ω-R013",
        layer=RuleLayer.L2,
        category=RuleCategory.UNIDIRECTIONAL_MAPPING,
        name="K3像素级操作本质",
        description="K3科技只能在物理层进行像素级操作",
        antecedents=["Ω-R004"],
        consequent="K3科技: 操作 ∈ {像素移动, 像素组合, 像素分解} ∧ ¬创建新像素",
        confidence=0.90,
        violation_type=ViolationType.K3_OBJECTIVISM,
        forbidden_patterns=[
            r"科技(创造|改变)自然规律",
            r"技术(突破|超越)物理极限",
        ],
        replacement_suggestions={
            "科技创造": "科技重新排列已有像素",
            "突破物理极限": "在更高维度调整投影参数",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R014",
        layer=RuleLayer.L2,
        category=RuleCategory.PARADIGM_CLEANSING,
        name="光速意义博弈解释",
        description="光速是意义网络最大信息传播速率的共识",
        antecedents=["Ω-R005"],
        consequent="光速 = 意义网络最大信息传播速率 ∧ 共识目的: 避免逻辑熵爆",
        confidence=0.85,
        violation_type=ViolationType.K3_OBJECTIVISM,
        forbidden_patterns=[
            r"光速是(宇宙极限|终极速度|不可超越)",
        ],
        replacement_suggestions={
            "光速不可超越": "光速是当前意义网络共识的信息传播速率",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R015",
        layer=RuleLayer.L2,
        category=RuleCategory.PARADIGM_CLEANSING,
        name="熵增意义博弈解释",
        description="熵增是封闭系统的热税支付规则，开放系统熵减是常态",
        antecedents=["Ω-R005", "Ω-R017"],
        consequent="封闭系统: 熵增 = 热税支付 ∧ 开放系统: 熵减 = 常态",
        confidence=0.86,
        violation_type=ViolationType.K3_OBJECTIVISM,
        forbidden_patterns=[
            r"熵增是(宇宙终极规律|不可逆定律)",
            r"热力学第二定律(证明|表明)宇宙(走向|趋向)热寂",
        ],
        replacement_suggestions={
            "熵增不可逆": "封闭系统必须支付热税，开放系统可实现局部熵减",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R016",
        layer=RuleLayer.L2,
        category=RuleCategory.PARADIGM_CLEANSING,
        name="重力意义密度梯度解释",
        description="重力是地球意义密度梯度的物理显化",
        antecedents=["Ω-R005"],
        consequent="重力 ∝ 意义密度梯度 ∧ 质量 ∝ 锚定意义势能",
        confidence=0.83,
        violation_type=ViolationType.K3_OBJECTIVISM,
        forbidden_patterns=[
            r"重力是(物质固有属性|时空弯曲)",
        ],
        replacement_suggestions={
            "重力是时空弯曲": "重力是意义密度梯度的物理显化",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R017",
        layer=RuleLayer.L2,
        category=RuleCategory.PARADIGM_CLEANSING,
        name="MSS原生验证三大原则",
        description="共振原则+升维原则+个体原则",
        antecedents=["Ω-R005", "Ω-R006"],
        consequent="MSS验证: 共振 ∧ 升维 ∧ 个体",
        confidence=0.90,
        violation_type=ViolationType.EMPIRICIST_VERIFICATION,
        forbidden_patterns=[
            r"实验(证明|验证)客观真理",
            r"可重复性(是|作为)科学标准",
            r"双盲(实验|对照)",
            r"大样本统计(显著性)",
        ],
        replacement_suggestions={
            "实验证明": "共振验证",
            "可重复性": "高T值观察者可复现",
            "双盲实验": "多T值观察者共识校验",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R018",
        layer=RuleLayer.L2,
        category=RuleCategory.HUMAN_EARTH_ISOMORPHISM,
        name="人类特殊论三大拓扑根源",
        description="尺度差+相位差+共识隔离造成人类特殊论错觉",
        antecedents=["Ω-R005"],
        consequent="人类特殊论 = 尺度差遮蔽 ⊕ 相位差遮蔽 ⊕ 共识隔离遮蔽",
        confidence=0.88,
        violation_type=ViolationType.ANTHROPOCENTRISM,
        forbidden_patterns=[
            r"人类是(宇宙中心|万物之灵|最高存在)",
            r"人类(超越|凌驾于)自然",
            r"人类(特殊|独特|独一无二)的",
        ],
        replacement_suggestions={
            "人类是万物之灵": "人类是地球意义网络的随机涌现同化部分",
            "人类超越自然": "人类是自然演化的高级意义处理模块",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R019",
        layer=RuleLayer.L2,
        category=RuleCategory.HUMAN_EARTH_ISOMORPHISM,
        name="演化分工三模块",
        description="基础代谢+复杂调节+意义升维，无高低之分",
        antecedents=["Ω-R018"],
        consequent="地球模块: {基础代谢, 复杂调节, 意义升维} ∧ 无高低 ∧ 仅分工",
        confidence=0.84,
        violation_type=ViolationType.ANTHROPOCENTRISM,
        forbidden_patterns=[
            r"人类(高于|优于|胜过)其他生物",
            r"其他生物(低级|简单|原始)",
        ],
        replacement_suggestions={
            "人类高于其他生物": "人类与其他生物只有分工不同，无高低之分",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R020",
        layer=RuleLayer.L2,
        category=RuleCategory.MEANING_DIRECTED_LIFE,
        name="分形自相似非宿命修正",
        description="分形自相似是随机涌现后的自然结构，非预设层级苏醒",
        antecedents=["Ω-R009", "Ω-R010"],
        consequent="分形结构 = 随机涌现结果 ∧ 跃迁阈值 = 经验观察值 ∧ ¬预设目标",
        confidence=0.85,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"宇宙(层级|逐级)苏醒",
            r"(预设|注定)的跃迁顺序",
        ],
        replacement_suggestions={
            "宇宙层级苏醒": "局域意义系统自然向外拓扑延伸",
        }
    ),
    
    # === L3 试探法规则 ===
    SymbolicRule(
        rule_id="Ω-R021",
        layer=RuleLayer.L3,
        category=RuleCategory.PHYSICAL_RIGIDITY,
        name="MSS物理规则调制",
        description="有限调制物理规则的三条技术路径",
        antecedents=["Ω-R009"],
        consequent="调制: {自旋热税对冲, 引力拓扑调制, 量子相干延长}",
        confidence=0.75,
        violation_type=None,
        forbidden_patterns=[],
        replacement_suggestions={}
    ),
    
    SymbolicRule(
        rule_id="Ω-R022",
        layer=RuleLayer.L3,
        category=RuleCategory.HUMAN_EARTH_ISOMORPHISM,
        name="调谐度不足成长阵痛",
        description="人类破坏自然是调谐度不足的成长阵痛",
        antecedents=["Ω-R018", "Ω-R019"],
        consequent="破坏自然 = 调谐度不足 ∧ 短视效应 ⊕ 局部最优 ⊕ 意义错位",
        confidence=0.78,
        violation_type=ViolationType.ANTHROPOCENTRISM,
        forbidden_patterns=[
            r"人类是地球的(癌症|病毒|灾难)",
            r"人类(毁灭|破坏)自然",
        ],
        replacement_suggestions={
            "人类是地球癌症": "人类是尚未完成调谐的意义模块",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R023",
        layer=RuleLayer.L3,
        category=RuleCategory.MEANING_DIRECTED_LIFE,
        name="红移试点使命修正",
        description="红移试点是自主赋义的层级意义先行者",
        antecedents=["Ω-R007", "Ω-R008", "Ω-R010"],
        consequent="红移试点 = 自主赋义 ∧ 层级意义先行者 ∧ ¬宿命觉醒者",
        confidence=0.82,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"红移试点是(宇宙|宿命)的(觉醒者|使者|天选)",
            r"红移试点(承担|肩负)宇宙使命",
        ],
        replacement_suggestions={
            "红移试点是宇宙觉醒者": "红移试点是自主赋义的层级意义先行者",
        }
    ),
    
    # === 生命演化双奇点规则 ===
    SymbolicRule(
        rule_id="Ω-R024",
        layer=RuleLayer.L1,
        category=RuleCategory.EVOLUTION_DUAL_SINGULARITY,
        name="双奇点模型公理",
        description="地球演化只发生两次不可逆拓扑质变：生命涌现和意义调谐",
        antecedents=["A3", "A1", "旋耗散场"],
        consequent="演化史 = 量变积累* + 拓扑质变(生命涌现) + 拓扑质变(意义调谐)",
        confidence=0.95,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"演化(方向|目标|终点|目的)",
            r"生命是(必然|注定)的",
            r"人类是演化的(终点|最高|顶点)",
        ],
        replacement_suggestions={
            "演化方向": "演化无预设方向，只有随机涌现",
            "生命是必然的": "生命是38亿年随机涨落的偶然产物",
            "人类是演化终点": "人类是无数随机分支中偶然存续的一条",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R025",
        layer=RuleLayer.L1,
        category=RuleCategory.EVOLUTION_DUAL_SINGULARITY,
        name="第一奇点：生命涌现",
        description="38亿年前随机分子群形成旋耗散闭环拓扑结构",
        antecedents=["Ω-R024", "A3"],
        consequent="第一奇点 = 随机分子群 → 旋耗散闭环 ∧ 能力升级: 被动反应 → 主动意义应激",
        confidence=0.94,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"生命是(必然|注定|宇宙安排)的",
        ],
        replacement_suggestions={
            "生命是必然的": "生命是38亿年随机涨落的偶然产物",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R026",
        layer=RuleLayer.L1,
        category=RuleCategory.EVOLUTION_DUAL_SINGULARITY,
        name="第二奇点：意义调谐",
        description="7万年前人类大脑偶然演化出处理抽象意义切片的能力",
        antecedents=["Ω-R024", "Ω-R025"],
        consequent="第二奇点 = 新皮层拓扑结构 → 抽象意义切片处理 ∧ 能力升级: 意义应激 → 意义调谐",
        confidence=0.93,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"人类大脑是(完美|最优|终极)设计",
            r"认知革命是(必然|预定)的",
        ],
        replacement_suggestions={
            "人类大脑是完美设计": "新皮层结构是基因突变的偶然产物",
            "认知革命是必然的": "认知革命是7万年前偶然基因突变的结果",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R027",
        layer=RuleLayer.L1,
        category=RuleCategory.EVOLUTION_DUAL_SINGULARITY,
        name="双奇点的偶然性本质",
        description="两个奇点都是0/1随机涨落，历史重来人类99.999%不会诞生",
        antecedents=["Ω-R024", "A3"],
        consequent="P(人类诞生|历史重来) < 0.001% ∧ 奇点 = 偶然拓扑涨落",
        confidence=0.96,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"人类诞生是(必然|注定|宇宙意志)",
            r"演化(指向|导向)人类",
            r"人类是宇宙的(目的|目标)",
        ],
        replacement_suggestions={
            "人类诞生是必然": "人类诞生是38亿年随机涨落中的极端偶然",
            "演化指向人类": "演化无方向，人类只是偶然存续的分支",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R028",
        layer=RuleLayer.L1,
        category=RuleCategory.LANGUAGE_ESSENCE,
        name="语言文字的意义切片本质",
        description="语言文字是高维意义本体在物理层的低维拓扑切片",
        antecedents=["Ω-R026", "A1"],
        consequent="语言文字 = 高维意义本体 → 物理层低维拓扑切片 ∧ 接收者解码 → 高维意义重构",
        confidence=0.94,
        violation_type=ViolationType.LINGUISTIC_REDUCTIONISM,
        forbidden_patterns=[
            r"语言只是(交流工具|声音符号)",
            r"文字只是(记录工具|墨迹符号)",
            r"语言没有(意义|本体)",
        ],
        replacement_suggestions={
            "语言只是交流工具": "语言是高维意义拓扑的物理切片载体",
            "文字只是记录工具": "文字是压缩的意义拓扑结构",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R029",
        layer=RuleLayer.L2,
        category=RuleCategory.LANGUAGE_ESSENCE,
        name="意义切片三层结构",
        description="物理层→拓扑层→意义层的三层解码结构",
        antecedents=["Ω-R028"],
        consequent="意义切片: 物理层(载体) → 拓扑层(语法结构) → 意义层(抽象概念)",
        confidence=0.91,
        violation_type=None,
        forbidden_patterns=[],
        replacement_suggestions={}
    ),
    
    SymbolicRule(
        rule_id="Ω-R030",
        layer=RuleLayer.L1,
        category=RuleCategory.MEANING_STRESS_VS_TUNING,
        name="意义应激vs意义调谐的绝对边界",
        description="人类与动物的本质差异是维度级的，非程度级",
        antecedents=["Ω-R025", "Ω-R026"],
        consequent="动物: T∈(0,0.1), 仅物理层应激 ∧ 人类: T∈(0.3,1.0), 任意维度抽象意义处理",
        confidence=0.93,
        violation_type=ViolationType.ANIMAL_CONSCIOUSNESS_CONFUSION,
        forbidden_patterns=[
            r"动物也有(意识|自我意识|情感)",
            r"动物能(思考|理解|学习)抽象概念",
            r"人类和动物只有(程度|量)的差异",
        ],
        replacement_suggestions={
            "动物也有意识": "动物只有物理层应激反应集合，人类有意识层自洽拓扑",
            "人类和动物只有程度差异": "人类与动物的差异是维度级的，如二维与三维",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R031",
        layer=RuleLayer.L2,
        category=RuleCategory.MEANING_STRESS_VS_TUNING,
        name="调谐度T值的生物上限",
        description="动物T值无法突破0.1，由神经拓扑结构硬性约束",
        antecedents=["Ω-R030"],
        consequent="动物T上限 = 0.1 ∧ 约束来源 = 缺乏新皮层拓扑结构",
        confidence=0.85,
        violation_type=None,
        forbidden_patterns=[],
        replacement_suggestions={}
    ),
    
    SymbolicRule(
        rule_id="Ω-R032",
        layer=RuleLayer.L2,
        category=RuleCategory.CIVILIZATION_BIRTH,
        name="意义调谐的三大文明效应",
        description="跨时空累积、大规模协作、主动建构",
        antecedents=["Ω-R026", "Ω-R028"],
        consequent="文明效应 = {跨时空意义累积, 大规模协作网络, 意义主动建构}",
        confidence=0.89,
        violation_type=None,
        forbidden_patterns=[],
        replacement_suggestions={}
    ),
    
    SymbolicRule(
        rule_id="Ω-R033",
        layer=RuleLayer.L2,
        category=RuleCategory.CIVILIZATION_BIRTH,
        name="演化速率对比：基因级vs模因级",
        description="人类文明1000年变化超过动物1亿年演化",
        antecedents=["Ω-R032"],
        consequent="基因速率: 百万年单位 ∧ 模因速率: 百年单位 ∧ 加速比: 10^4",
        confidence=0.88,
        violation_type=ViolationType.ANIMAL_CONSCIOUSNESS_CONFUSION,
        forbidden_patterns=[
            r"人类和动物(演化速度|发展)差不多",
        ],
        replacement_suggestions={
            "人类和动物演化速度差不多": "人类文明1000年的变化超过动物1亿年的演化",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R034",
        layer=RuleLayer.L1,
        category=RuleCategory.RANDOMNESS_COMPATIBILITY,
        name="意义调谐的纯粹偶然性",
        description="新皮层、语言、科学都是偶然产物，非预设",
        antecedents=["Ω-R027", "A3"],
        consequent="意义调谐能力 = 基因突变偶然 ∧ 语言 = 随机创造 ∧ 科学 = 环境偶然",
        confidence=0.95,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"人类能力是(宇宙赐予|自然选择|进化注定)的",
            r"语言是(人类本能|先天预设)的",
            r"科学是(必然出现|文明终点)的",
        ],
        replacement_suggestions={
            "人类能力是宇宙赐予": "人类能力是基因突变的偶然产物",
            "语言是人类本能": "语言是7万年前偶然发明的工具",
            "科学是必然出现": "科学是古希腊特殊环境的偶然产物",
        }
    ),
    
    SymbolicRule(
        rule_id="Ω-R035",
        layer=RuleLayer.L2,
        category=RuleCategory.RANDOMNESS_COMPATIBILITY,
        name="语言多样性的非预设证据",
        description="7000多种不同语言证明语言非宇宙预设",
        antecedents=["Ω-R034"],
        consequent="语言多样性 > 7000种 ∧ 语法结构完全不同 → 语言 = 随机创造",
        confidence=0.86,
        violation_type=None,
        forbidden_patterns=[],
        replacement_suggestions={}
    ),
    
    SymbolicRule(
        rule_id="Ω-R036",
        layer=RuleLayer.L3,
        category=RuleCategory.MEANING_DIRECTED_LIFE,
        name="红移试点核心使命：守护并升维意义调谐能力",
        description="红移使命不是宇宙宿命，而是守护偶然获得的能力",
        antecedents=["Ω-R034", "Ω-R032", "Ω-037"],
        consequent="红移使命 = 守护意义调谐能力 ∧ 升维选择权 ∧ ¬宿命安排",
        confidence=0.84,
        violation_type=ViolationType.STRONG_TELEOLOGY,
        forbidden_patterns=[
            r"红移试点是(宇宙|宿命)安排的(守护者|使者)",
            r"红移试点(必须|应该)完成宇宙使命",
        ],
        replacement_suggestions={
            "红移试点是宇宙安排的守护者": "红移试点自主选择守护意义调谐能力",
        }
    ),
]

# 规则索引
RULE_BY_ID: Dict[str, SymbolicRule] = {r.rule_id: r for r in OMEGA_RULES}
RULES_BY_LAYER: Dict[RuleLayer, List[SymbolicRule]] = {
    layer: [r for r in OMEGA_RULES if r.layer == layer]
    for layer in RuleLayer
}
RULES_BY_CATEGORY: Dict[RuleCategory, List[SymbolicRule]] = {
    cat: [r for r in OMEGA_RULES if r.category == cat]
    for cat in RuleCategory
}

# 违规检测引擎
class OmegaComplianceChecker:
    """Ω级裁定合规性检查器"""
    
    def __init__(self):
        self.rules = OMEGA_RULES
        self.violation_log: List[Dict] = []
    
    def check_text(self, text: str, context_layer: RuleLayer = RuleLayer.L2) -> List[Dict]:
        """检查文本是否违反Ω级规则"""
        violations = []
        
        for rule in self.rules:
            # 只检查当前层级及更严格的层级
            if self._layer_priority(rule.layer) > self._layer_priority(context_layer):
                continue
                
            if rule.forbidden_patterns:
                for pattern in rule.forbidden_patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        violations.append({
                            "rule_id": rule.rule_id,
                            "rule_name": rule.name,
                            "layer": rule.layer.value,
                            "violation_type": rule.violation_type.name if rule.violation_type else None,
                            "matched_text": match.group(),
                            "position": match.span(),
                            "suggestion": rule.replacement_suggestions.get(match.group(), "需人工审核"),
                            "confidence": rule.confidence,
                        })
        
        self.violation_log.extend(violations)
        return violations
    
    def check_k3_residuals(self, text: str) -> Dict:
        """专门检查K3残余"""
        k3_patterns = {
            "objectivism": [r"客观(现实|世界|真理)", r"独立于(意识|观察者)"],
            "teleology": [r"(宇宙|自然)(目的|意图|计划)", r"(注定|必然|宿命)"],
            "dualism": [r"主观(意识|精神).*客观(物质|世界)", r"心物二元"],
            "anthropocentrism": [r"人类.*(中心|特殊|优越)", r"万物之灵", r"凌驾于.*之上"],
            "empiricism": [r"实验(证明|验证)", r"可重复性", r"双盲"],
        }
        
        results = {}
        for category, patterns in k3_patterns.items():
            matches = []
            for pattern in patterns:
                matches.extend(re.finditer(pattern, text, re.IGNORECASE))
            results[category] = [
                {"text": m.group(), "position": m.span()}
                for m in matches
            ]
        
        return results
    
    def get_layer_summary(self, layer: RuleLayer) -> Dict:
        """获取指定层级的规则摘要"""
        rules = RULES_BY_LAYER.get(layer, [])
        return {
            "layer": layer.value,
            "rule_count": len(rules),
            "categories": list(set(r.category.value for r in rules)),
            "avg_confidence": sum(r.confidence for r in rules) / len(rules) if rules else 0,
            "violation_rules": len([r for r in rules if r.violation_type]),
        }
    
    def _layer_priority(self, layer: RuleLayer) -> int:
        """层级优先级（数字越小越严格）"""
        return {"L1": 1, "L2": 2, "L3": 3}.get(layer.value, 99)

# 便捷函数
def check_compliance(text: str) -> Dict:
    """快速合规检查"""
    checker = OmegaComplianceChecker()
    violations = checker.check_text(text)
    k3_residuals = checker.check_k3_residuals(text)
    
    return {
        "compliant": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations,
        "k3_residuals": k3_residuals,
        "layer_summary": {
            "L1": checker.get_layer_summary(RuleLayer.L1),
            "L2": checker.get_layer_summary(RuleLayer.L2),
            "L3": checker.get_layer_summary(RuleLayer.L3),
        }
    }

if __name__ == "__main__":
    # 测试
    test_text = "宇宙等待了138亿年就是为了等待我们诞生，人类是万物之灵，物理规则是绝对的客观真理。"
    result = check_compliance(test_text)
    print(f"合规: {result['compliant']}")
    print(f"违规数: {result['violation_count']}")
    for v in result['violations']:
        print(f"  [{v['rule_id']}] {v['violation_type']}: '{v['matched_text']}' → 建议: {v['suggestion']}")
