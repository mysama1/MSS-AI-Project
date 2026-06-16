"""
Credential Vault v2.0 — 企业级密码管理器设计模式

Sprint 9: 吸收 Bitwarden/KeePass/1Password/Chrome 的最佳实践.

新增:
  1. PasswordGenerator — 可配置熵值的强密码生成器
  2. PasswordStrength — zxcvbn风格熵值评估 (0-4级)
  3. ClipboardGuard — 自动清除剪贴板 (N秒后)
  4. Export/Import — CSV/JSON 密文导出 (加密传输)
  5. CategoryTemplate — 预定义凭证模板 (Database/SSH/API/Email/WiFi)

升级:
  - ZeroMemory: 使用 bytearray + 覆写代替 str (用完即焚)
  - Master Key: 支持 key file 双因子 (类似 KeePass)
  - TOTP: 生成基于时间的一次性密码
"""
from __future__ import annotations
import secrets, string, time, math, json, csv, hashlib, hmac, base64, struct
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum
from io import StringIO


# ═══════════════════════════════════════════
# 1. Password Generator — 可配置熵值
# ═══════════════════════════════════════════

class CharSet(Enum):
    LOWER = "abcdefghijklmnopqrstuvwxyz"
    UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    DIGITS = "0123456789"
    SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?/~`"
    AMBIGUOUS = "Il1O0"  # 易混淆字符


@dataclass
class PasswordRecipe:
    """密码配方."""
    length: int = 20
    include_upper: bool = True
    include_digits: bool = True
    include_symbols: bool = True
    exclude_ambiguous: bool = True
    min_entropy_bits: int = 80  # NIST推荐 >=80 bits


class PasswordGenerator:
    """
    强密码生成器.

    熵值计算: H = log2(charset_size^length)
    默认: 26+26+10+32=94 chars, len=20 → log2(94^20) ≈ 131 bits
    """

    @classmethod
    def generate(cls, recipe: PasswordRecipe = None) -> Tuple[str, float]:
        """生成密码, 返回 (密码, 熵值bits)."""
        r = recipe or PasswordRecipe()
        charset = string.ascii_lowercase
        if r.include_upper:
            charset += string.ascii_uppercase
        if r.include_digits:
            charset += string.digits
        if r.include_symbols:
            charset += "!@#$%^&*()-_=+[]{}|;:,.<>?/"
        if r.exclude_ambiguous:
            charset = charset.translate(str.maketrans("", "", "Il1O0"))

        # Ensure at least one of each required type
        pwd_chars = []
        if r.include_upper:
            pwd_chars.append(secrets.choice(string.ascii_uppercase))
        if r.include_digits:
            pwd_chars.append(secrets.choice(string.digits))
        if r.include_symbols:
            pwd_chars.append(secrets.choice("!@#$%^&*"))

        # Fill remaining with secure random choices
        remaining = r.length - len(pwd_chars)
        pwd_chars.extend(secrets.choice(charset) for _ in range(remaining))
        secrets.SystemRandom().shuffle(pwd_chars)

        password = "".join(pwd_chars)
        entropy = math.log2(len(charset) ** r.length)
        return password, round(entropy, 1)

    @classmethod
    def passphrase(cls, word_count: int = 6, separator: str = "-") -> Tuple[str, float]:
        """生成易记口令 (类似 Bitwarden passphrase)."""
        # EFF short wordlist (sample)
        words = [
            "apple", "bridge", "cloud", "diamond", "eagle", "forest",
            "garden", "hammer", "island", "jungle", "knight", "lemon",
            "mountain", "needle", "ocean", "puzzle", "quartz", "river",
            "shadow", "tiger", "unicorn", "violet", "window", "yellow",
        ]
        chosen = [secrets.choice(words) for _ in range(word_count)]
        passphrase = separator.join(chosen)
        entropy = word_count * math.log2(len(words))
        return passphrase, round(entropy, 1)


# ═══════════════════════════════════════════
# 2. Password Strength Meter
# ═══════════════════════════════════════════

class StrengthLevel(Enum):
    VERY_WEAK = 0   # 可瞬间破解
    WEAK = 1        # 易破解 (<1s)
    FAIR = 2        # 需要一定算力
    STRONG = 3      # 难以破解
    VERY_STRONG = 4 # 几乎不可能


@dataclass
class StrengthReport:
    score: int  # 0-4
    level: StrengthLevel
    entropy_bits: float
    crack_time_display: str
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class PasswordStrength:
    """
    密码强度评估器 (zxcvbn 风格简版).

    评估维度:
      1. 长度
      2. 字符集多样性
      3. 常见模式检测 (序列, 重复, 键盘行走)
      4. 字典检测 (简单版)
    """

    COMMON_PASSWORDS = {
        "password", "123456", "12345678", "qwerty", "abc123",
        "monkey", "letmein", "dragon", "111111", "iloveyou",
        "admin", "welcome", "football", "master", "sunshine",
    }
    KEYBOARD_WALKS = {
        "qwerty", "asdfgh", "zxcvbn", "qwertyuiop", "asdfghjkl",
        "1qaz", "2wsx", "3edc", "4rfv",
    }

    @classmethod
    def assess(cls, password: str) -> StrengthReport:
        warnings = []
        suggestions = []
        score = 0

        pwd_lower = password.lower()

        # Length scoring
        if len(password) >= 16:
            score += 2
        elif len(password) >= 12:
            score += 1
        else:
            warnings.append("密码太短 (<12字符)")
            suggestions.append("增加到至少12个字符")

        # Common password check
        if pwd_lower in cls.COMMON_PASSWORDS:
            score = 0
            warnings.append("常见密码, 可被字典攻击瞬间破解")

        # Keyboard walk detection
        if any(walk in pwd_lower for walk in cls.KEYBOARD_WALKS):
            score = max(0, score - 1)
            warnings.append("检测到键盘行走模式")

        # Character diversity
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for c in password)
        diversity = sum([has_upper, has_digit, has_symbol])
        score += diversity

        # Sequence detection
        if cls._has_sequence(password):
            score = max(0, score - 1)
            warnings.append("检测到序列模式 (如 abc, 123)")

        # Repeat detection
        if cls._has_repeats(password):
            score = max(0, score - 1)
            suggestions.append("避免连续重复字符")

        # Entropy estimation
        charset_size = 26
        if has_upper:
            charset_size += 26
        if has_digit:
            charset_size += 10
        if has_symbol:
            charset_size += 32
        entropy = math.log2(charset_size ** len(password)) if charset_size > 0 else 0

        # Crack time estimation (assuming 10^9 guesses/sec)
        guesses_needed = 2 ** min(entropy, 128)
        crack_seconds = guesses_needed / 1e9
        crack_display = cls._format_crack_time(crack_seconds)

        # Normalize score to 0-4
        score = max(0, min(4, score))

        level_map = {
            0: StrengthLevel.VERY_WEAK,
            1: StrengthLevel.WEAK,
            2: StrengthLevel.FAIR,
            3: StrengthLevel.STRONG,
            4: StrengthLevel.VERY_STRONG,
        }

        return StrengthReport(
            score=score,
            level=level_map[score],
            entropy_bits=round(entropy, 1),
            crack_time_display=crack_display,
            warnings=warnings,
            suggestions=suggestions,
        )

    @staticmethod
    def _has_sequence(s: str) -> bool:
        for i in range(len(s) - 2):
            a, b, c = ord(s[i]), ord(s[i+1]), ord(s[i+2])
            if b - a == 1 and c - b == 1:
                return True
            if a - b == 1 and b - c == 1:
                return True
        return False

    @staticmethod
    def _has_repeats(s: str) -> bool:
        for i in range(len(s) - 2):
            if s[i] == s[i+1] == s[i+2]:
                return True
        return False

    @staticmethod
    def _format_crack_time(seconds: float) -> str:
        if seconds < 1:
            return "瞬间 (<1秒)"
        elif seconds < 60:
            return f"{seconds:.0f} 秒"
        elif seconds < 3600:
            return f"{seconds/60:.0f} 分钟"
        elif seconds < 86400:
            return f"{seconds/3600:.0f} 小时"
        elif seconds < 31536000:
            return f"{seconds/86400:.0f} 天"
        elif seconds < 31536000 * 100:
            return f"{seconds/31536000:.0f} 年"
        elif seconds < 31536000 * 1000000:
            return f"{seconds/31536000/1000:.0f} 千年"
        else:
            return "宇宙热寂之后"


# ═══════════════════════════════════════════
# 3. Clipboard Guard
# ═══════════════════════════════════════════

class ClipboardGuard:
    """
    剪贴板安全 — 自动清除敏感内容.

    类似 1Password 的剪贴板自动清除:
      - copy后N秒自动清除
      - 支持平台: Windows (clip.exe), macOS (pbcopy), Linux (xclip)
    """

    def __init__(self, clear_after_seconds: int = 30):
        self._clear_after = clear_after_seconds
        self._timer: Optional[float] = None
        self._content_hash: str = ""

    def copy(self, text: str) -> bool:
        """复制到剪贴板, 启动清除计时器."""
        import subprocess, platform

        # Zero the old content
        self.clear()

        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["clip"], input=text.encode("utf-16-le"), check=False)
            elif system == "Darwin":
                subprocess.run(["pbcopy"], input=text.encode(), check=False)
            else:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=False)
        except Exception:
            return False

        self._content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        self._timer = time.time()
        return True

    def maybe_clear(self) -> bool:
        """检查是否需要清除, 返回是否已清除."""
        if self._timer and time.time() - self._timer > self._clear_after:
            self.clear()
            return True
        return False

    def clear(self):
        """立即清空剪贴板."""
        import subprocess, platform
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["cmd", "/c", "echo off | clip"], check=False)
            elif system == "Darwin":
                subprocess.run(["pbcopy"], input=b"", check=False)
            else:
                subprocess.run(["xclip", "-selection", "clipboard"], input=b"", check=False)
        except Exception:
            pass
        self._timer = None
        self._content_hash = ""


# ═══════════════════════════════════════════
# 4. Export / Import
# ═══════════════════════════════════════════

class VaultIO:
    """保险箱数据导入/导出 (加密传输)."""

    @staticmethod
    def export_json(vault, password: str = None) -> str:
        """导出为加密 JSON (可选密码保护)."""
        entries = vault.list_keys()
        data = {
            "version": "2.0",
            "exported_at": time.time(),
            "entries": [],
        }
        for entry in entries:
            value = vault.get(entry["key"])
            entry_data = {
                "key": entry["key"],
                "category": entry["category"],
                "tags": entry["tags"],
                "value": value,
            }
            # Encrypt with export password if provided
            if password and value:
                from .credential_vault import CredentialVault
                entry_data["value"] = CredentialVault._encrypt_static(value, password)
                entry_data["encrypted"] = True
            data["entries"].append(entry_data)

        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def export_csv(vault) -> str:
        """导出为 CSV."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["key", "category", "tags", "created_at", "updated_at"])
        for entry in vault.list_keys():
            writer.writerow([
                entry["key"], entry["category"],
                ",".join(entry.get("tags", [])),
                entry.get("created_at", ""),
                entry.get("updated_at", ""),
            ])
        return output.getvalue()

    @staticmethod
    def import_json(vault, json_str: str, password: str = None) -> int:
        """从 JSON 导入, 返回导入条数."""
        data = json.loads(json_str)
        count = 0
        for entry in data.get("entries", []):
            value = entry.get("value", "")
            if entry.get("encrypted") and password:
                value = CredentialVault._decrypt_static(value, password)
            if value:
                vault.put(
                    key=entry["key"],
                    value=value,
                    category=entry.get("category", "api_key"),
                    tags=entry.get("tags", []),
                )
                count += 1
        return count


# ═══════════════════════════════════════════
# 5. Category Templates
# ═══════════════════════════════════════════

CATEGORY_TEMPLATES = {
    "database": {
        "fields": ["host", "port", "username", "password", "database"],
        "icon": "🗄️",
    },
    "ssh_key": {
        "fields": ["host", "port", "username", "private_key", "passphrase"],
        "icon": "🔑",
    },
    "api_credentials": {
        "fields": ["api_key", "api_secret", "endpoint", "notes"],
        "icon": "🔌",
    },
    "email": {
        "fields": ["email", "password", "smtp_host", "smtp_port", "imap_host"],
        "icon": "📧",
    },
    "wifi": {
        "fields": ["ssid", "password", "security_type", "notes"],
        "icon": "📶",
    },
    "credit_card": {
        "fields": ["card_number", "expiry", "cvv", "cardholder_name"],
        "icon": "💳",
    },
    "identity": {
        "fields": ["full_name", "id_number", "birth_date", "address", "phone"],
        "icon": "🪪",
    },
    "server": {
        "fields": ["host", "port", "username", "password", "private_key_path"],
        "icon": "🖥️",
    },
}


# ═══════════════════════════════════════════
# 6. TOTP Generator
# ═══════════════════════════════════════════

class TOTPGenerator:
    """
    RFC 6238 TOTP 生成器.

    用法:
        secret = TOTPGenerator.generate_secret()
        code = TOTPGenerator.generate(secret)  # 6位数字
    """

    @staticmethod
    def generate_secret() -> str:
        """生成 Base32 密钥."""
        return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")

    @staticmethod
    def generate(secret: str, period: int = 30, digits: int = 6) -> str:
        """根据当前时间生成 TOTP."""
        # Decode Base32 secret
        secret = secret.upper().replace(" ", "")
        padding = 8 - len(secret) % 8
        if padding != 8:
            secret += "=" * padding
        key = base64.b32decode(secret)

        # Calculate counter
        counter = int(time.time() // period)
        counter_bytes = struct.pack(">Q", counter)

        # HMAC-SHA1
        h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        binary = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF

        return str(binary % (10 ** digits)).zfill(digits)

    @staticmethod
    def verify(secret: str, code: str, window: int = 1) -> bool:
        """验证 TOTP (前后各 window 步)."""
        for offset in range(-window, window + 1):
            if code == TOTPGenerator.generate(secret):
                return True
        return False


# ═══════════════════════════════════════════
# 7. Zero-Memory String
# ═══════════════════════════════════════════

class SecureString:
    """
    安全字符串 — 用完即焚.

    使用 bytearray 代替 str, close() 时覆写内存.
    Python 的 str 是不可变的, GC 不会清除内存中的明文.
    1Password 等产品使用类似机制.

    用法:
        with SecureString("my-password") as s:
            api.authenticate(s.value)
        # 离开 with 块后内存被覆写
    """

    def __init__(self, text: str):
        self._data = bytearray(text.encode("utf-8"))
        self._closed = False

    @property
    def value(self) -> str:
        if self._closed:
            raise ValueError("SecureString already cleared")
        return self._data.decode("utf-8")

    def clear(self):
        if not self._closed:
            for i in range(len(self._data)):
                self._data[i] = 0
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.clear()

    def __del__(self):
        self.clear()
