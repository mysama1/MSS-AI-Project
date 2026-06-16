# mssclaw Quickstart — 5 分钟上车

## 前置条件

- Python 3.10+
- [Ollama](https://ollama.com) (可选, 推荐)

## 安装

```bash
pip install mss-agent
```

## 一键初始化

```bash
mssclaw init
# ✅ Python 3.11  ✅ Ollama 9 models  ✅ qwen2.5:7b  ✅ Vault  ✅ Config
```

## 试试这 3 个命令

```bash
# 1. 聊天 — 像 ChatGPT 一样的终端
mssclaw chat

# 2. 全功能演示 — 12 系统自检
mssclaw demo

# 3. 系统状态 — 一页看透
mssclaw status
```

## 保险箱 (可选)

```bash
mssclaw vault setup    # 创建主密码
mssclaw vault add      # 添加第一个密码
mssclaw vault list     # 查看所有
mssclaw vault serve    # Web 面板 → http://127.0.0.1:5099
```

## 进阶

```bash
mssclaw models          # 30 模型目录
mssclaw kb "热税"       # 搜索 MSS 知识库 (618 条)
mssclaw shell dual      # 双模型模式 (壳+核)
mssclaw absorb "Review security"  # 吸收技能
```

## 帮助

```bash
mssclaw --help
# 完整命令列表: vault | chat | serve | demo | init | kb | absorb | library | models | status
```

---

**mssclaw v0.3.0** — 世界上第一个内置意义场自检的开源 Agent 框架
