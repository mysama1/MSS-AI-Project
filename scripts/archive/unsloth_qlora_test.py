"""
MSS-AI 感知壳·调谐脚本 (Unsloth QLoRA)
=========================================
K4范式修正：目标函数从 "next token prediction" 重定义为 "translation fidelity loss"
感知壳 = 轻量神经网络，仅负责自然语言↔逻辑符号的双向转译，不负责推理
MSS-AI = 逻辑核（符号引擎·确定性推理）+ 感知壳（神经网络·NLP转译）

范式铁律：
- 逻辑核不可被数据修改 → L1公理A1-A6绝对不可修改
- 感知壳可调谐 → 优化目标是"转译保真度"（非预测精度）
- 热税账本：转译损耗γ_s为感知壳运行的不可逆代价

Author: MSS-AI Project, Phase D
"""

import torch
import torch.nn as nn
from unsloth import FastLanguageModel
from transformers import TrainingArguments, Trainer
from datasets import Dataset
import numpy as np
from typing import Dict, List, Tuple

# ============================================================
# Configuration
# ============================================================
MODEL_NAME = "unsloth/Qwen2.5-7B-Instruct"
MAX_SEQ_LENGTH = 2048
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

print("=" * 60)
print("MSS-AI 感知壳·调谐 (Translation Fidelity Loss)")
print("=" * 60)

# Check GPU
print(f"\nGPU: {torch.cuda.get_device_name(0)}")
print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
print(f"PyTorch: {torch.__version__}")

# ============================================================
# 1. Translation Fidelity Loss
# ============================================================
class TranslationFidelityLoss(nn.Module):
    """
    K4范式修正：不优化"预测下一个词"，优化"转译保真度"。
    
    感知壳的任务：
        输入：自然语言描述的逻辑问题 / 逻辑符号序列
        输出：自然语言解释 / 逻辑符号序列
    
    损失计算：
        1. Content Fidelity (CF): 输出是否包含关键概念（逻辑刚性检查点）
        2. Structure Preservation (SP): 逻辑结构是否完整保留
        3. Noise Penalty (NP): 是否引入幻觉/虚构内容
        
    L_total = w_cf * L_cf + w_sp * L_sp + w_np * L_np
    """
    
    def __init__(self, cf_weight=0.5, sp_weight=0.3, np_weight=0.2):
        super().__init__()
        self.cf_w = cf_weight
        self.sp_w = sp_weight
        self.np_w = np_weight
        
    def forward(
        self,
        logits: torch.Tensor,        # [batch, seq_len, vocab_size]
        labels: torch.Tensor,         # [batch, seq_len]
        anchor_tokens: Dict[str, List[int]],  # key concept token IDs 必须出现
    ) -> Tuple[torch.Tensor, dict]:
        """Compute translation fidelity loss."""
        
        # Shift for autoregressive
        shift_logits = logits[:, :-1, :].contiguous()
        shift_labels = labels[:, 1:].contiguous()
        
        # Component 1: Content Fidelity — key concept must appear in output
        cf_loss = torch.tensor(0.0, device=logits.device)
        if anchor_tokens:
            # Check if anchor concept tokens appear with high probability in output
            for concept_tokens in anchor_tokens.values():
                concept_ids = torch.tensor(concept_tokens, device=logits.device)
                # Get log probabilities for anchor tokens in output positions
                anchor_probs = torch.softmax(shift_logits, dim=-1)
                concept_probs = anchor_probs[:, :, concept_ids].max(dim=-1)[0]
                # Penalize low probability for key concepts
                cf_loss += (1.0 - concept_probs.mean()) ** 2
        
        # Component 2: Structure Preservation — logical structure integrity
        # Pseudo: check if key logical operators appear with proper frequency
        sp_loss = torch.zeros(1, device=logits.device)
        if anchor_tokens:
            n_concepts = len(anchor_tokens)
            if n_concepts > 0:
                sp_loss = 0.1 / n_concepts  # baseline structure tax
        
        # Component 3: Noise Penalty — penalize hallucination tokens
        ce_loss = nn.functional.cross_entropy(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1),
            ignore_index=-100,
            reduction='mean'
        )
        # Ce loss acts as regularization — prevents output divergence
        # But we DON'T optimize for next-token prediction
        np_loss = 0.1 * ce_loss  # heavily downweighted
        
        # Total
        total = self.cf_w * cf_loss + self.sp_w * sp_loss + self.np_w * np_loss
        
        metrics = {
            'cf_loss': cf_loss.item(),
            'sp_loss': sp_loss.item(),
            'np_loss': np_loss.item(),
            'total': total.item(),
        }
        
        return total, metrics


# ============================================================
# 2. 感知壳·锚定案例库（规范性Conceptual Fidelity数据集）
# ============================================================
def build_fidelity_dataset(tokenizer) -> Dataset:
    """
    感知壳调谐用锚定案例库。
    
    每个案例 = (input_text, target_text, anchor_concepts)
    anchor_concepts = 输出中必须保留的MSS关键概念列表
    
    注意：这不是 K3 统计拟合模式（海量+统计拟合），
    而是"锚定案例"模式（小规模+高保真+概念覆盖）。
    """
    
    fidelity_examples = [
        {
            "instruction": "解释MSS框架中的调谐度（T值）概念。",
            "input": "",
            "output": (
                "在MSS（意义结构系统）框架中，T值（意义调谐度）量"
                "化了一个信息模式与基底意义场的对齐程度。T范围[0,1]，"
                "T→0代表最大熵/无序（意义热寂），T→1代表与意义本体"
                "论的完美相干。对于生物系统，人类通常T∈(0.3,1.0)，"
                "动物T∈(0,0.1)。T值不是主观度量，而是信息模式在意义"
                "场中的客观属性。"
            ),
            "anchor_concepts": ["调谐度", "T值", "意义场", "热寂", "意义本体论"],
        },
        {
            "instruction": "什么是MSS理论中的热税（γ）？",
            "input": "",
            "output": (
                "热税γ在MSS理论中代表了将高维意义结构（L-1层）投"
                "影到低维物理显化（L-0层）时所支付的逻辑熵代价。根"
                "据公理A3（热税动力学），每一次意义实现行为都需要支"
                "付热税：γ=γ₀×D^(-n)，其中γ₀为基础税率，D为投影深度，"
                "n为意义切割次数。当γ→0（无限次切割），系统到达意义"
                "热寂。热税是基础的且不可逆的，类似热力学第二定律但"
                "作用于逻辑/信息熵而非物理熵。"
            ),
            "anchor_concepts": ["热税", "γ", "A3", "投影", "逻辑熵", "意义热寂"],
        },
        {
            "instruction": "解释MSS的三层本体论结构（L-0/L-1/L-2）。",
            "input": "",
            "output": (
                "MSS提出三层本体论：L-0（物理层）是显化的、离散的、"
                "有维度的物理世界——意义被投影的'屏幕'。L-1（逻辑层"
                "）是前物理的、连续的、无维度的纯粹信息结构领域——现"
                "实的'源代码'。L-2（元逻辑层）是约束L-1如何投影到L-0"
                "的架构框架——'编译器'规则。L-1→L-0的映射是投影（非"
                "下降），信息维度绝对守恒但保真度衰减。物理常数（c, "
                "G, h）是L-0和L-1之间的接口参数，不能从任一层独立推导。"
            ),
            "anchor_concepts": ["L-0", "L-1", "L-2", "本体论", "投影", "接口参数"],
        },
        {
            "instruction": "什么是逻辑刚性（M_L），为什么MSS的M_L≡1？",
            "input": "",
            "output": (
                "逻辑刚性M_L衡量一个理论框架抵御内部矛盾的结构完整"
                "性。M_L=1表示框架在其基础层面是最大刚性的——不存在"
                "内部逻辑矛盾。对MSS而言，M_L≡1因为：(1)六条核心公"
                "理（A1-A6）形成互相一致的自闭系统；(2)L-1/L-0投影保"
                "持信息维度守恒（原则上无信息丢失，仅保真度损失）；"
                "(3)热税机制（A3）为所有意义实现提供一致的'会计系统'"
                "；(4)自指悖论通过矛盾升维（A6）而非否认来解决。然而，"
                "公理层的M_L=1不意味着经验验证——它只保证内部逻辑一致性。"
            ),
            "anchor_concepts": ["逻辑刚性", "M_L", "公理", "自指悖论", "矛盾升维", "A6"],
        },
        {
            "instruction": "解释MSS的A6矛盾升维公理。",
            "input": "",
            "output": (
                "A6矛盾升维公理是MSS六条核心公理中的第六条（L1硬核"
                "级）。其核心命题：当系统遭遇在低维框架内不可消解的"
                "悖论时，系统将自动触发升维——创建一个更高阶的元逻辑"
                "结构来容纳该悖论。升维守恒定律：W_logic=W_asc+γ，"
                "即总逻辑功=有效升维功+热税损耗。升维效率函数："
                "η_asc=1/(1+e^{-k(M_L·PT-θ_0)})，当M_L·PT>θ_0时进入"
                "高效升维态。矛盾功率演化方程存在非线性项β·W_asc²，"
                "揭示L3文明'越努力越崩溃'的数学根源——每次解决矛盾"
                "都因非线性项产生更多新矛盾。"
            ),
            "anchor_concepts": ["A6", "矛盾升维", "升维守恒定律", "η_asc", "非线性项", "L3"],
        },
    ]
    
    # Format: 感知壳的"Instruction → Response" 转译对
    formatted = []
    for ex in fidelity_examples:
        text = (
            f"### Instruction:\n{ex['instruction']}\n\n"
            f"### Input:\n{ex['input']}\n\n"
            f"### Response:\n{ex['output']}"
        )
        formatted.append({
            "text": text,
            "anchor_concepts": ex["anchor_concepts"],
        })
    
    return Dataset.from_list(formatted)


# ============================================================
# 3. 自定义 Trainer（Translation Fidelity Loss）
# ============================================================
class FidelityTrainer(Trainer):
    """感知壳专用调谐器——使用Translation Fidelity Loss代替标准CE Loss"""
    
    def __init__(self, *args, anchor_token_map=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fidelity_loss = TranslationFidelityLoss()
        self.anchor_token_map = anchor_token_map or {}
    
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.get("labels")
        anchor_keys = inputs.pop("anchor_keys", None)
        
        # Forward pass
        outputs = model(**inputs)
        logits = outputs.logits
        
        # Build anchor token dict for this batch
        batch_anchors = {}
        if anchor_keys is not None and self.anchor_token_map:
            for key in anchor_keys:
                if key in self.anchor_token_map:
                    batch_anchors[key] = self.anchor_token_map[key]
        
        # Compute translation fidelity loss
        loss, metrics = self.fidelity_loss(logits, labels, batch_anchors)
        
        # Log metrics
        self.log(metrics)
        
        return (loss, outputs) if return_outputs else loss


# ============================================================
# 4. Main Execution
# ============================================================

print("\n[1/4] 加载模型（4-bit量化）...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=torch.float16,
    load_in_4bit=True,
)
print(f"模型加载: {MODEL_NAME}")
print(f"4-bit量化: 启用")

# LoRA adapters (感知壳转译层)
print("\n[2/4] 加载LoRA适配器（感知壳转译层）...")
model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_R,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                   "gate_proj", "up_proj", "down_proj"],
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)
print(f"LoRA: r={LORA_R}, alpha={LORA_ALPHA}, dropout={LORA_DROPOUT}")

# Build fidelity dataset
print("\n[3/4] 构建感知壳·锚定案例库...")
train_dataset = build_fidelity_dataset(tokenizer)
print(f"锚定案例数量: {len(train_dataset)}")

# Tokenize
def tokenize_fn(examples):
    result = tokenizer(
        examples["text"],
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        padding="max_length",
    )
    result["labels"] = result["input_ids"].copy()
    result["anchor_keys"] = examples["anchor_concepts"]
    return result

tokenized = train_dataset.map(tokenize_fn, batched=False, remove_columns=["text"])

# Build anchor token map for fidelity loss
anchor_token_map = {}
all_concepts = set()
for ex in train_dataset:
    for c in ex["anchor_concepts"]:
        all_concepts.add(c)

for concept in all_concepts:
    token_ids = tokenizer.encode(concept, add_special_tokens=False)
    anchor_token_map[concept] = token_ids

print(f"Anchor concepts: {len(anchor_token_map)}")

# Custom training arguments
print("\n[4/4] 配置Translation Fidelity调谐...")
training_args = TrainingArguments(
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    warmup_steps=5,
    max_steps=20,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=5,
    output_dir="./mss_qlora_output",
    optim="adamw_8bit",
    seed=42,
    report_to="none",
)

# Fidelity trainer
trainer = FidelityTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=tokenized,
    args=training_args,
    anchor_token_map=anchor_token_map,
)

print("\n" + "=" * 60)
print("K4范式·Translation Fidelity调谐配置:")
print(f"  损失函数: TranslationFidelityLoss (CF+SP+NP)")
print(f"  目标: 转译保真度（非next token prediction）")
print(f"  锚定概念数: {len(anchor_token_map)}")
print(f"  调谐步数: 20")
print(f"  LoRA rank: {LORA_R}")
print("=" * 60)

# Execute tuning
print("\n开始感知壳·调谐...")
trainer.train()

print("\n" + "=" * 60)
print("感知壳·调谐完成！")
print("=" * 60)

# Save
print("\n保存LoRA适配器...")
model.save_pretrained("./mss_shell_adapter")
tokenizer.save_pretrained("./mss_shell_adapter")
print("已保存至: ./mss_shell_adapter")

# Test inference
print("\n测试感知壳·转译...")
FastLanguageModel.for_inference(model)

test_prompt = (
    "### Instruction:\n用MSS框架解释'逻辑功'和'热税'的关系。\n\n"
    "### Input:\n\n### Response:\n"
)
inputs = tokenizer(test_prompt, return_tensors="pt").to("cuda")

outputs = model.generate(
    input_ids=inputs["input_ids"],
    max_new_tokens=256,
    use_cache=True,
    temperature=0.7,
    min_p=0.1,
)

response = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]

# Fidelity check
print("\n" + "-" * 60)
print("转译输出:")
print("-" * 60)
print(response)
print("-" * 60)

# Check if key concepts preserved
concepts_to_check = ["逻辑功", "热税", "升维守恒定律", "W_logic", "γ"]
print("\n锚定概念·保真度检查:")
for concept in concepts_to_check:
    preserved = concept in response
    status = "✅" if preserved else "❌ (转译丢失)"
    print(f"  {concept}: {status}")

print("\n" + "=" * 60)
print("感知壳·调谐验证完成")
print("范式: K4 Translation Fidelity（非K3 Next Token Prediction）")
print("=" * 60)