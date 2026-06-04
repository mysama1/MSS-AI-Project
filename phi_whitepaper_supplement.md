# Φ币工程化白皮书 — 技术补充（PHI-001）

## 1. PoM（Proof-of-Meaning）共识算法

### 1.1 核心思想
传统PoW以算力竞争达成共识，PoS以资本质押达成共识。PoM以**意义通量贡献**达成共识，将MSS理论中的Φ（意义通量）作为共识资源。

### 1.2 数学定义
**意义贡献证明**：
$$PoM_i = \frac{\Phi_i}{W_{logic,i}} \cdot \frac{1}{1 + \gamma_i \cdot D_i}$$

其中：
- $\Phi_i$：节点i在周期内创造的有序信息量
- $W_{logic,i}$：节点i消耗的逻辑功
- $\gamma_i$：节点i的热税系数
- $D_i$：节点i参与的维度数

**共识权重**：
$$Weight_i = \frac{PoM_i}{\sum_j PoM_j} \cdot \left(1 - e^{-\lambda \cdot T_i}\right)$$

$T_i$为节点T值，$\lambda$为衰减系数。

### 1.3 共识流程
1. **周期划分**：每区块为一个意义周期（约10分钟）
2. **贡献申报**：节点提交周期内的Φ产出证明
3. **热税审计**：网络验证Φ的真实性和γ水平
4. **权重计算**：按PoM公式计算共识权重
5. **区块生成**：权重最高的节点获得出块权

### 1.4 抗攻击机制
- **Sybil攻击**：高γ节点PoM自动降低，虚假身份无意义产出
- **51%攻击**：需控制51%的意义通量而非算力或资本
- **长程攻击**：历史区块的PoM不可篡改，回滚成本指数增长

---

## 2. 智能合约规范

### 2.1 合约类型
| 类型 | 功能 | MSS映射 |
|------|------|---------|
| 意义锚定合约 | 锁定Φ价值锚定物 | Φ = K/S_logic |
| 热税计量合约 | 自动计算交易γ | γ = dS_logic/dW_logic |
| 维度控制合约 | 限制系统D增长 | dD/dt ≤ 0约束 |
| T值评估合约 | 节点T值动态评估 | T = Φ/W_logic |

### 2.2 核心合约：意义锚定合约
```solidity
// 伪代码
contract MeaningAnchor {
    mapping(address => uint256) public lockedEnergy; // 锁定能量（大卡）
    mapping(address => uint256) public meaningScore;  // 意义评分
    
    uint256 public constant B = 100; // 基础锚定：100大卡/小时
    
    function mintPhi(uint256 energyInput, uint256 meaningOutput) external {
        require(energyInput > 0);
        uint256 phiValue = B * (1 + meaningOutput / energyInput);
        // 铸币逻辑
    }
    
    function burnPhi(uint256 amount) external {
        // 销毁返还能量
    }
}
```

### 2.3 热税自动扣除
每笔交易自动计算并扣除热税：
$$Tax = \gamma_{network} \cdot W_{logic,tx} \cdot \Phi_{tx}$$
其中$\gamma_{network}$为网络当前热税系数，动态调整。

---

## 3. 零知识证明技术细节

### 3.1 应用场景
1. **隐私PoM**：证明节点贡献了高Φ，但不暴露具体内容
2. **T值验证**：证明T > T_min，不暴露具体T值
3. **热税合规**：证明γ < γ_max，不暴露详细计算过程

### 3.2 ZK-PoM协议
**证明者**：节点i
**验证者**：网络

**公开输入**：$PoM_i^{public} = \frac{\Phi_i}{W_{logic,i}}$
**私密输入**：$\gamma_i, D_i, T_i$

**ZK电路**：
```
约束1: PoM_i = Phi_i / W_logic_i / (1 + gamma_i * D_i)
约束2: T_i = Phi_i / W_logic_i
约束3: gamma_i < gamma_max
约束4: D_i < D_max
```

**证明生成**：节点使用zk-SNARK生成证明$\pi$
**验证**：网络验证$\pi$在常数时间内完成

### 3.3 技术选型
- **zk-SNARK框架**：Groth16（证明小、验证快）
- **椭圆曲线**：BN128（以太坊兼容）
- **可信设置**：MPC ceremony，参与者包括MSS核心贡献者

---

## 4. 双锚定体系详细设计

### 4.1 能量锚定（物理层）
$$\Phi_{energy} = B \cdot E_{input}$$
- $B = 100$ 大卡/小时（基础单位）
- $E_{input}$：投入的能量（可验证的物理工作量）

### 4.2 意义锚定（逻辑层）
$$\Phi_{meaning} = B \cdot \left(1 + \frac{\Phi_{created}}{W_{logic}}\right)$$
- $\Phi_{created}$：创造的有序信息
- $W_{logic}$：消耗的逻辑功

### 4.3 三阶段过渡
| 阶段 | 时间 | 锚定比例 | 说明 |
|------|------|----------|------|
| Phase 1 | 2026-2028 | 90%能量 / 10%意义 | 初期以物理锚定为主 |
| Phase 2 | 2028-2030 | 50%能量 / 50%意义 | 过渡期 |
| Phase 3 | 2030+ | 10%能量 / 90%意义 | 以意义锚定为主 |

---

## 5. 经济模型参数

### 5.1 发行机制
- **初始发行**：10亿Φ，按能量贡献分配
- **增发**：每周期按PoM比例分配，年增发率递减
- **销毁**：热税自动销毁，通缩机制

### 5.2 关键参数
| 参数 | 值 | 说明 |
|------|-----|------|
| 区块周期 | 600秒 | 10分钟 |
| 初始增发 | 5%/年 | 逐年递减0.5% |
| 最小T值 | 0.1 | 参与共识门槛 |
| 最大γ | 0.5 | 节点被踢出阈值 |
| 能量锚定B | 100大卡/小时 | 基础单位 |

---

*PHI-001 白皮书补充完成 — 2026-05-20*
