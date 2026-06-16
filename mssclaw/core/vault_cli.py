"""
Vault CLI — 极简命令行密码管理器

用法:
  # 首次
  python -m mssclaw.core.vault_cli setup
  python -m mssclaw.core.vault_cli add github_token ghp_xxx -c token
  python -m mssclaw.core.vault_cli get github_token
  python -m mssclaw.core.vault_cli list
  python -m mssclaw.core.vault_cli gen github_key -c api_key  # 生成强密码并存入

设计原则: 一条命令一件事, 不要选项轰炸.
"""
import sys
import os
import getpass
from pathlib import Path

VAULT_PATH = Path.home() / ".mssclaw" / "vault.db"


def _get_vault():
    from mssclaw.core.credential_vault import CredentialVault
    v = CredentialVault(str(VAULT_PATH))
    v.AUTO_LOCK_SECONDS = 9999
    return v


def cmd_setup():
    """初始化保险箱."""
    v = _get_vault()
    pw = getpass.getpass("设置主密码: ")
    pw2 = getpass.getpass("确认主密码: ")
    if pw != pw2:
        print("❌ 两次密码不一致")
        return
    if v.setup(pw):
        print(f"✅ 保险箱已创建: {VAULT_PATH}")
    else:
        print("❌ 初始化失败")


def cmd_unlock():
    """解锁."""
    v = _get_vault()
    pw = getpass.getpass("主密码: ")
    if v.unlock(pw):
        print("✅ 已解锁")
    else:
        print("❌ 密码错误")


def cmd_lock():
    """锁定."""
    v = _get_vault()
    v.lock()
    print("✅ 已锁定")


def cmd_add(key: str, value: str = None, category: str = "api_key"):
    """添加凭证."""
    v = _get_vault()
    if v.is_locked:
        cmd_unlock()
        v = _get_vault()
    if v.is_locked:
        print("❌ 未解锁")
        return

    if value is None:
        value = getpass.getpass(f"输入 {key} 的值: ")

    if v.put(key, value, category=category):
        print(f"✅ 已存储 {key}")
    else:
        print(f"❌ 存储失败")


def cmd_get(key: str):
    """获取凭证."""
    v = _get_vault()
    if v.is_locked:
        cmd_unlock()
        v = _get_vault()
    if v.is_locked:
        print("❌ 未解锁")
        return

    val = v.get(key)
    if val:
        print(val)
    else:
        print(f"❌ 未找到 {key}")


def cmd_list(category: str = None):
    """列出所有凭证."""
    v = _get_vault()
    if v.is_locked:
        cmd_unlock()
        v = _get_vault()
    if v.is_locked:
        print("❌ 未解锁")
        return

    keys = v.list_keys(category=category)
    if not keys:
        print("(空)")
        return

    for k in keys:
        icon = {"api_key": "🔌", "password": "🔑", "token": "🎫", "personal_info": "🪪"}.get(k["category"], "📌")
        tags = f" [{','.join(k['tags'])}]" if k.get("tags") else ""
        print(f"  {icon} {k['key']} ({k['category']}){tags}")


def cmd_delete(key: str):
    """删除凭证."""
    v = _get_vault()
    if v.is_locked:
        cmd_unlock()
        v = _get_vault()

    if v.delete(key):
        print(f"✅ 已删除 {key}")
    else:
        print(f"❌ 删除失败")


def cmd_gen(key: str, category: str = "password"):
    """生成强密码并存入."""
    from mssclaw.core.vault_toolkit import PasswordGenerator
    v = _get_vault()
    if v.is_locked:
        cmd_unlock()
        v = _get_vault()
    if v.is_locked:
        print("❌ 未解锁")
        return

    pwd, entropy = PasswordGenerator.generate()
    if v.put(key, pwd, category=category, tags=["auto-generated"]):
        print(f"{pwd}")
        print(f"✅ 已存入 {key} (熵值: {entropy} bits)")
    else:
        print("❌ 存储失败")


def cmd_export(fmt: str = "json"):
    """导出凭证."""
    from mssclaw.core.vault_toolkit import VaultIO
    v = _get_vault()
    if v.is_locked:
        cmd_unlock()
        v = _get_vault()

    if fmt == "csv":
        print(VaultIO.export_csv(v))
    else:
        print(VaultIO.export_json(v))


def cmd_audit():
    """查看审计日志."""
    v = _get_vault()
    if v.is_locked:
        cmd_unlock()
        v = _get_vault()

    for r in v.audit_log(limit=10):
        status = "✅" if r["ok"] else "❌"
        print(f"  {status} {r['action']:15s} {r['key']:20s} {r.get('detail', '')}")


def cmd_health():
    """安全体检."""
    from mssclaw.core.vault_health import VaultHealth
    v = _get_vault()
    if v.is_locked:
        cmd_unlock()
        v = _get_vault()

    report = VaultHealth.check(v)
    print(f"📊 总条目: {report['total_entries']}")
    print(f"🛡️  健康分: {report['health_score']}/100 (Grade {report['grade']})")
    print(f"   ✅ 健康: {report['healthy_count']}")

    if report['weak_passwords']:
        print(f"\n⚠️  弱密码 ({len(report['weak_passwords'])}):")
        for w in report['weak_passwords']:
            print(f"   - {w['key']}: {w['warning']}")

    if report['duplicate_passwords']:
        print(f"\n🔄 重复密码 ({len(report['duplicate_passwords'])}):")
        for d in report['duplicate_passwords']:
            print(f"   - {d['key1']} = {d['key2']}")

    if report['stale_passwords']:
        print(f"\n⏰ 过期密码 ({len(report['stale_passwords'])}):")
        for s in report['stale_passwords']:
            print(f"   - {s['key']}: {s['days_old']}天未更新")

    if not report['weak_passwords'] and not report['duplicate_passwords'] and not report['stale_passwords']:
        print("\n   🎉 全部健康!")


def cmd_backup(subcmd: str = None, path: str = None):
    """备份 / 恢复."""
    from mssclaw.core.vault_health import VaultHealth
    v = _get_vault()

    if subcmd == "restore" and path:
        if VaultHealth.restore(v, path):
            print(f"✅ 已从 {path} 恢复")
        else:
            print("❌ 恢复失败")
        return

    if subcmd == "list":
        backups = VaultHealth.list_backups(v)
        if not backups:
            print("(无备份)")
        for b in backups:
            print(f"  {b['time']}  {b['size_kb']}KB  {b['path']}")
        return

    # Default: backup
    path = VaultHealth.backup(v)
    if path:
        print(f"✅ 已备份到 {path}")
    else:
        print("❌ 备份失败")


# ═══════════════════════════════════════════

USAGE = """mssclaw vault — 极简密码管理

  setup                    初始化保险箱
  unlock                   解锁
  lock                     锁定
  add <key> [value]        添加 (无value则隐藏输入)
  get <key>                获取
  list [category]          列出
  delete <key>             删除
  gen <key> [category]     生成强密码并存入
  export [json|csv]        导出
  import [url_filter]     从Chrome/Edge导入密码
  health                  安全体检
  backup [restore PATH]   备份/恢复
  audit                    审计日志"""


def main():
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        return

    cmd = args[0]

    if cmd == "setup":
        cmd_setup()
    elif cmd == "unlock":
        cmd_unlock()
    elif cmd == "lock":
        cmd_lock()
    elif cmd == "add" and len(args) >= 2:
        cmd_add(args[1], args[2] if len(args) > 2 else None, args[3] if len(args) > 3 else "api_key")
    elif cmd == "get" and len(args) >= 2:
        cmd_get(args[1])
    elif cmd == "list":
        cmd_list(args[1] if len(args) > 1 else None)
    elif cmd == "delete" and len(args) >= 2:
        cmd_delete(args[1])
    elif cmd == "gen" and len(args) >= 2:
        cmd_gen(args[1], args[2] if len(args) > 2 else "password")
    elif cmd == "export":
        cmd_export(args[1] if len(args) > 1 else "json")
    elif cmd == "import":
        from mssclaw.core.chrome_import import cmd_import
        cmd_import(args[1] if len(args) > 1 else None)
    elif cmd == "audit":
        cmd_audit()
    elif cmd == "health":
        cmd_health()
    elif cmd == "backup":
        cmd_backup(args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else None)
    else:
        print(USAGE)


if __name__ == "__main__":
    main()
