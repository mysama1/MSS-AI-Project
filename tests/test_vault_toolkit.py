"""
Sprint 9: Vault Toolkit 测试 — 密码生成/强度/剪贴板/TOTP/模板/SecureString
"""
from __future__ import annotations
import sys, os, tempfile, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_password_generator():
    """PasswordGenerator: 生成强密码 + 熵值验证."""
    from mssclaw.core.vault_toolkit import PasswordGenerator, PasswordRecipe

    # Default recipe
    pwd, entropy = PasswordGenerator.generate()
    assert len(pwd) == 20
    assert entropy > 100  # 20 chars × 94 charset ≈ 131 bits
    assert any(c.isupper() for c in pwd)
    assert any(c.isdigit() for c in pwd)

    # Short password
    short, _ = PasswordGenerator.generate(PasswordRecipe(length=8))
    assert len(short) == 8

    # No symbols
    no_sym, _ = PasswordGenerator.generate(PasswordRecipe(include_symbols=False))
    assert not any(c in "!@#$%^&*()" for c in no_sym)

    # Passphrase
    phrase, ent = PasswordGenerator.passphrase(word_count=4)
    assert phrase.count("-") == 3
    assert ent > 15  # 4 words x 24 choices ~ 18 bits


def test_password_strength():
    """PasswordStrength: 0-4级强度评估."""
    from mssclaw.core.vault_toolkit import PasswordStrength, StrengthLevel

    # Very weak
    r = PasswordStrength.assess("password")
    assert r.level == StrengthLevel.VERY_WEAK
    assert len(r.warnings) > 0

    # Weak
    r2 = PasswordStrength.assess("abc12345")
    assert r2.score <= 1

    # Strong
    r3 = PasswordStrength.assess("Tr0ub4dor&3Secure!")
    assert r3.score >= 2
    assert r3.entropy_bits > 40

    # Very strong
    r4 = PasswordStrength.assess("k8$QmP!xR3vL9nW@tZ5")
    assert r4.score >= 3

    # Keyboard walk detection
    r5 = PasswordStrength.assess("qwerty123456")
    assert any("键盘" in w for w in r5.warnings)

    # Sequence detection
    r6 = PasswordStrength.assess("abcdefgh1234")
    assert any("序列" in w for w in r6.warnings)

    # Crack time display
    assert r4.crack_time_display


def test_clipboard_guard():
    """ClipboardGuard: 复制 + 超时清除."""
    from mssclaw.core.vault_toolkit import ClipboardGuard

    guard = ClipboardGuard(clear_after_seconds=0.01)
    # Copy (may fail on headless, that's OK)
    ok = guard.copy("test-secret-123")
    if ok:
        time.sleep(0.02)
        assert guard.maybe_clear()
    # Clear should always work
    guard.clear()


def test_totp_generator():
    """TOTPGenerator: 生成 + 验证."""
    from mssclaw.core.vault_toolkit import TOTPGenerator

    # Generate secret
    secret = TOTPGenerator.generate_secret()
    assert len(secret) >= 16

    # Generate code
    code = TOTPGenerator.generate(secret)
    assert len(code) == 6
    assert code.isdigit()

    # Verify own code
    assert TOTPGenerator.verify(secret, code)

    # Wrong code
    assert not TOTPGenerator.verify(secret, "000000")


def test_category_templates():
    """CategoryTemplate: 预定义模板结构."""
    from mssclaw.core.vault_toolkit import CATEGORY_TEMPLATES

    assert "database" in CATEGORY_TEMPLATES
    assert "ssh_key" in CATEGORY_TEMPLATES
    assert "api_credentials" in CATEGORY_TEMPLATES
    assert "email" in CATEGORY_TEMPLATES
    assert "wifi" in CATEGORY_TEMPLATES
    assert "credit_card" in CATEGORY_TEMPLATES
    assert "identity" in CATEGORY_TEMPLATES
    assert "server" in CATEGORY_TEMPLATES

    db = CATEGORY_TEMPLATES["database"]
    assert "host" in db["fields"]
    assert "password" in db["fields"]
    assert db["icon"]


def test_vault_export_import():
    """VaultIO: JSON/CSV 导入导出."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_toolkit import VaultIO

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "export_test.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("test123")
        v.put("api_key", "secret-value", category="api_key", tags=["prod"])
        v.put("db_pass", "db-secret", category="password", tags=["staging"])

        # JSON export (unencrypted)
        json_str = VaultIO.export_json(v)
        data = json.loads(json_str)
        assert data["version"] == "2.0"
        assert len(data["entries"]) == 2

        # CSV export
        csv_str = VaultIO.export_csv(v)
        assert "api_key" in csv_str
        assert "db_pass" in csv_str

        # JSON import into new vault
        db2_path = os.path.join(tmp, "import_test.db")
        v2 = CredentialVault(db2_path)
        v2.AUTO_LOCK_SECONDS = 9999
        v2.setup("test123")
        count = VaultIO.import_json(v2, json_str)
        assert count == 2
        assert v2.get("api_key") == "secret-value"

        v.close()
        v2.close()


def test_secure_string():
    """SecureString: 用完即焚."""
    from mssclaw.core.vault_toolkit import SecureString

    with SecureString("my-secret-password") as s:
        assert s.value == "my-secret-password"

    # After with-block, should be cleared
    try:
        _ = s.value
        assert False, "Should have raised"
    except ValueError:
        pass  # expected


def test_vault_with_toolkit_integration():
    """CredentialVault + toolkit: 完整工作流."""
    from mssclaw.core.credential_vault import CredentialVault
    from mssclaw.core.vault_toolkit import (
        PasswordGenerator, PasswordStrength, TOTPGenerator, SecureString
    )

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "full.db")
        v = CredentialVault(db_path)
        v.AUTO_LOCK_SECONDS = 9999
        v.setup("master-password-123")

        # Generate a strong password
        pwd, entropy = PasswordGenerator.generate()
        assert PasswordStrength.assess(pwd).score >= 3

        # Store with SecureString
        with SecureString(pwd) as s:
            v.put("generated_key", s.value, category="api_key", tags=["auto-generated"])
        # s is now cleared from memory

        # Read back
        stored = v.get("generated_key")
        assert stored == pwd

        # Generate TOTP secret and store
        totp_secret = TOTPGenerator.generate_secret()
        v.put("totp_secret", totp_secret, category="token")

        # Verify TOTP works
        code = TOTPGenerator.generate(totp_secret)
        assert TOTPGenerator.verify(totp_secret, code)

        v.close()
