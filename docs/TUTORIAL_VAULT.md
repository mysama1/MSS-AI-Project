# Tutorial: MSS Vault — 本地加密保险箱

本地 AES-256-GCM 加密密码管理，零信任架构。

## 第一步：创建保险箱

```bash
mss-vault setup
# Enter master password: ********
# Vault ready: ~/.mssclaw/vault.db
```

## 第二步：添加凭证

```bash
mss-vault add
# Service: github
# Username: octocat
# Password: ********
# URL (optional): https://github.com
# Notes (optional): Personal account
# ✅ Added: github
```

## 第三步：日常使用

```bash
# 列出所有
mss-vault list

# 搜索
mss-vault search github

# 获取密码
mss-vault get github
# 输入主密码解锁...

# 删除
mss-vault delete github
```

## 第四步：Web 面板

```bash
mss-vault serve
# Dashboard: http://127.0.0.1:5099
```

浏览器打开 → 输入主密码 → 搜索/复制/管理。

## 第五步：从浏览器迁移

```bash
mss-vault import-chrome
# 自动读取 Chrome 保存的密码
# 加密导入到 Vault
```

## 密码卫生检查

```bash
mss-vault health
# ✅ Strong: 8
# ⚠️  Weak: 2 (github-personal, twitter)
# 🔄 Duplicates: 1
# ⏱️  Old (>1yr): 3
```

## 自动备份

```bash
mss-vault backup
# Backup saved: ~/.mssclaw/backups/vault_20260616.bak
# Auto-rotation: keeps last 5 backups
```

---

**安全特性**:
- AES-256-GCM 加密
- 零信任：密码永不明文存储
- 主密码只在内存中，退出即清
- 自动备份轮转
