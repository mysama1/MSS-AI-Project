# MSS-VDP 运维手册

## 一、发版流程

```bash
# 1. 本地打 tag 并推送
cd E:\QClaw-Data\skills\mss-vdp
git tag v2.0.1
git push origin v2.0.1

# 2. 去 GitHub Releases 页面创建 release
#    https://github.com/mysama1/MSS-AI-Project/releases/new
#    Tag: v2.0.1 → Publish Release

# 3. publish.yml 自动触发 → 构建并推送到 PyPI
#    完成后: pip install mss-vdp 即可获取新版本
```

## 二、Git 操作

```bash
repo = E:\QClaw-Data\skills\mss-vdp
remote = https://github.com/mysama1/MSS-AI-Project.git
branch = main

cd E:\QClaw-Data\skills\mss-vdp
git add -A
git commit -m "描述"
git push origin main
```

## 三、skill_api.py 服务

```bash
# 文件位置
E:\QClaw-Data\skills\skill_api.py
E:\QClaw-Data\skills\mss-vdp\skill_api.py  (repo 副本)

# 端口 53000 (NSSM 管理，或直接启动)
py -3.11 E:\QClaw-Data\skills\skill_api.py

# 重启
netstat -ano | findstr :53000    # 找 PID
taskkill /PID <PID> /F
py -3.11 E:\QClaw-Data\skills\skill_api.py
```

### API 端点

```
GET  /health               健康检查
GET  /vdp/scan/languages   语言列表
POST /vdp/scan/py          扫描 Python
POST /vdp/scan/js          JS/TS
POST /vdp/scan/rust        Rust
POST /vdp/scan/java        Java
POST /vdp/scan/cpp         C/C++
POST /vdp/scan/go          Go
POST /vdp/scan/ruby        Ruby
POST /vdp/scan/php         PHP
POST /vdp/scan/kotlin      Kotlin
POST /vdp/scan/csharp      C#
POST /vdp/scan/all         全语言
POST /vdp/scan             V1-V6 传统扫描
POST /vdp/audit            文件+对话审计
GET  /vdp/vaccine          边界标记注入
POST /vdp/ps_verify/detect PS POSIX 检测
GET  /vdp/ps_verify/rules  PS 铁律
GET  /query                KB 查询
```

## 四、PyPI — Trusted Publishing (OIDC)

```
链路: git push tag → GitHub Release → Actions 跑 publish.yml → PyPI

已配置:
  PyPI:    项目 mss-vdp, Publisher mysama1/MSS-AI-Project, workflow publish.yml, env pypi
  GitHub:  Settings → Environments → pypi (created)

无需 token，无需密钥。
如果 OIDC 失败，备选 token 已存在 PyPI 账户中。
```

## 五、CI Pipeline

```
文件: .github/workflows/vdp-pipeline.yml
触发: push/PR to main, 手动 workflow_dispatch

12 步骤:
  1. Checkout    2. Setup Python    3. 安装依赖
  4. Python V1-V6   5. JS/TS     6. Rust
  7. Java/C/C++     8. Go        9. Ruby
  10. PHP           11. Kotlin   12. C#
  13. PS 检查       14. Unified Audit
  15. 上传 JSON     16. 上传 PDF

所有步骤 continue-on-error: true (不阻断)
```

## 六、Dashboard

```bash
路径: C:\Users\Administrator\.qclaw\canvas\documents\dashboard\index.html
刷新: 直接覆盖该文件即可
```

## 七、项目结构速查

```
E:\QClaw-Data\
  skills\
    skill_api.py              ← API 服务入口
    mss-vdp\                   ← VDP 项目（Git repo）
      vdp_scan.py              Python V1-V6 扫描器
      js_scan.py               JS/TS 扫描器
      rust_scan.py             Rust
      java_cpp_scan.py         Java + C/C++
      go_scan.py               Go
      ruby_scan.py             Ruby
      php_scan.py              PHP
      kotlin_scan.py           Kotlin
      csharp_scan.py           C#
      vdp_pipeline.py         统一流水线
      vdp_fuzzer.py           模糊测试
      service_monitor.py      服务监控
      alert_sender.py         告警推送
      rate_limiter.py         限流器
      smoke_test.py           冒烟测试 (19/19)
      ps_verify.py            PS 矫正
      .github\workflows\
        vdp-pipeline.yml      扫描流水线
        publish.yml           发布到 PyPI
  workspace\
    task_bar.json             任务栏
    AGENTS.md                 Agent 规则
    TOOLS.md                  本地笔记
    MEMORY.md                 长期记忆
```

## 八、关键凭据

```
GitHub:  token → 见本地 QClaw 聊天记录 or GitHub Settings
         用户 mysama1, 仓库 MSS-AI-Project

PyPI:    token → 见本地 QClaw 聊天记录 or PyPI Account Settings
         项目 mss-vdp
```

## 九、常见问题

| 问题 | 解决 |
|------|------|
| 53000 端口被占用 | `netstat -ano \| findstr :53000` 找 PID kill |
| CI scan 失败 | 检查 scanner 是否支持目录参数 `.` |
| PowerShell 乱码 | 所有中文 I/O 加 `-Encoding UTF8` |
| Git push 被拒 | 检查 `git pull` 是否冲突 |
| pip 安装找不到 | 确保已 `pip install mss-vdp` |

---

最后更新: 2026-06-05  v2.0.0
