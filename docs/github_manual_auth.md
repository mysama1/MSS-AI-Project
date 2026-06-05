# GitHub 手动授权指南

## 问题
PowerShell 执行策略为 Restricted，阻止自动化 OAuth 流程。

## 解决方案：手动创建仓库

### 步骤 1：获取 GitHub Token
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择权限：
   - ✅ repo（完整仓库访问）
   - ✅ read:org（如果需要组织访问）
4. 生成并复制 token（只显示一次）

### 步骤 2：创建仓库
1. 访问 https://github.com/new
2. 填写：
   - Repository name: `mss-ai-prototype`
   - Description: `MSS-AI prototype implementation`
   - Visibility: Private（建议）
   - ✅ Initialize with README
3. 点击 "Create repository"

### 步骤 3：本地推送
```powershell
# 在 PowerShell 中执行
cd C:\MSS-AI-Project
git init
git add .
git commit -m "Initial MSS-AI prototype"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mss-ai-prototype.git
# 输入 token 作为密码
git push -u origin main
```

### 步骤 4：配置 OpenClaw
在 OpenClaw 设置中添加 GitHub token：
```
/github set-token YOUR_TOKEN_HERE
```

## 验证
```bash
git remote -v
git log --oneline
```

## 安全提示
- Token 不要提交到代码中
- 使用 .gitignore 忽略敏感文件
- 定期轮换 token
