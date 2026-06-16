# MSS-VDP 用户手册 v1.0

**DEV-006 | 2026-06-05**
**覆盖**: API端点 (15个) | CLI工具 (7个) | 基准测试 (15域45轮)

---

## 1. 快速开始

```bash
# 服务管理
net start MssSkillApi    # 启动 (端口 53000)
net stop MssSkillApi     # 停止

# 健康检查
curl http://localhost:53000/health

# 一键全扫描
py vdp_pipeline.py <项目目录> --strictness 0.7
```

## 2. API 端点 (端口 53000)

### 知识库 (3端点)

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/health` | 服务健康检查 |
| GET | `/query?q=关键词` | GET方式知识库查询 |
| POST | `/query` | POST方式知识库查询 `{"query":"..."}` |

### KB 向量搜索 (3端点)

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/kb/search?q=关键词&k=10` | TF-IDF向量搜索 |
| POST | `/kb/search` | 全参数向量搜索 `{"query":"...","k":10}` |
| GET | `/kb/status` | 索引状态 (条目数/构建时间) |

### VDP 扫描 (6端点)

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/vdp/scan` | V1-V7 验证纪律扫描 `{"content":"...","filetype":"python_script"}` |
| POST | `/vdp/precommit` | 提交前检查 (CLI-001, NAMING-002) |
| POST | `/vdp/audit` | VDP 疫苗审计 (文本 + 转录双重扫描) |
| GET | `/vdp/vaccine` | LVC 边界标记 (防止话语模板污染) |
| POST | `/vdp/anchor` | 锚点白名单验证 `{"content":"...","ref":"..."}` |
| POST | `/vdp/blackhole` | K3 黑洞检测 `{"content":"..."}` |

**响应格式**:
```json
{
  "verdict": "pass|warn|reject",
  "violations": [{"rule_id":"V1_PATH","loc":"L15","severity":"reject","detail":"..."}],
  "scores": {"composite": 95, "total_violations": 2}
}
```

### 统一审计 (1端点)

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/audit` | 四层统一审计 (L0实体/L1逻辑/L2热税/L3边界) |

**参数**: `content`, `ref`(可选), `format`(可选: `html`)

### 基准测试 (2端点)

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/benchmark/judge` | LLM裁判评分 `{"domain_id":"sre","round_num":1,"response":"..."}` |
| GET | `/benchmark/status` | 最新基准结果摘要 |

---

## 3. CLI 工具

### vdp_pipeline.py — 一键扫描→聚合→报告
```bash
py vdp_pipeline.py <目标目录> --strictness 0.7
py vdp_pipeline.py <目标目录> --json     # JSON输出
py vdp_pipeline.py <目标目录> -o reports # 指定输出目录
```
3阶段: vdp_scan (V1-V6) → vdp_precommit (CLI/NAMING) → unified_audit (四层)
输出: `.vdp_reports/vdp_report_*.json` + `.html`

### vdp_scan.py — V1-V6 验证纪律
```bash
py vdp_scan.py <文件>              # 扫描单文件
py vdp_scan.py <文件> --format json # JSON输出
py vdp_scan.py <文件> --strict     # 严格模式 (CJK编码警告→拒绝)
```

### vdp_precommit.py — 提交前静态检查
```bash
py vdp_precommit.py check --dir <目录>        # 递归扫描
py vdp_precommit.py check --dir <目录> --json # JSON输出
py vdp_precommit.py check --stdin             # 从stdin读取
```

### unified_audit.py — 四层LLM幻觉审计
```bash
py unified_audit.py --output <文本> --strictness 0.7
py unified_audit.py --output <文本> --ref <参考>  # 带锚点参考
py unified_audit.py --output <文本> --json        # JSON输出
py unified_audit.py --output <文本> --brief       # 仅结论
```

### benchmark_pipeline.py — 自动化基准流水线
```bash
py benchmark_pipeline.py   # 手动触发 (5阶段: 自检→运行→评分→报告→告警)
```
定时触发: Windows Scheduled Task `MSS-Benchmark-Pipeline` (每日14:00)

### benchmark_runner.py — 幻觉压制基准
```bash
py benchmark_runner.py --self-test          # 仅验证检测引擎
py benchmark_runner.py --suite all --run    # 全量运行+LLM
py benchmark_runner.py --suite L1 --report  # 运行L1套件+生成MD报告
```

### report_generator.py — HTML报告生成
```python
from report_generator import generate_html
with open("report.html", "w") as f:
    f.write(generate_html(audit_result, "报告标题"))
```

---

## 4. 基准测试体系

**15领域 × 3轮 = 45轮**

| # | 领域 | 文件 |
|:---|:---|:---|
| 1-7 | SRE/AI/安全/游戏/数据库/IoT/DevOps | golden_answers.json v2.0 |
| 8-15 | 后端/数据/前端/移动/区块链/MLOps/嵌入式/云架构 | golden_answers_v3.json |

**评分**: LLM裁判 (judge.py) vs 黄金答案 → 0-100%
**告警**: 低于95% → `ALERT_*.txt` + 定时任务通知

---

## 5. 知识库工具

```bash
# MSS CLI 统一入口
mss kb query "热税公理"
mss kb stats
mss cache --fresh
mss verify
```
索引: 553条 (H1-H475), TF-IDF + jieba, <25ms查询

---

## 6. 常见问题

**Q: 服务启动失败?**
```bash
net stop MssSkillApi; net start MssSkillApi
# 查看日志: E:\QClaw-Data\skills\skill_api.log
```

**Q: 扫描无输出?**
- 确认目标目录有 `.py` 文件
- 检查 `--strictness` 参数 (0.0-1.0)
- 查看 `.vdp_reports/` 目录

**Q: 基准测试超时?**
- Ollama 模型时间: 约90s/轮 × 21轮 ≈ 31分钟
- 增加超时: 修改 `benchmark_pipeline.py` timeout参数

**Q: 我需要只扫描单个文件的VDP违规?**
```bash
py vdp_scan.py path/to/file.py --format json
```

---

## 7. 版本

- skill_api.py: v2.4 (2026-06-05)
- vdp_pipeline: v1.0 (2026-06-05)
- benchmark_pipeline: v1.0 (2026-06-05)
- golden_answers: v3.0 (15域45轮)
