"""
mssclaw/core/semantic/multilang_detector.py

语义引擎多语言扩展: 文言文, 中英混合, 中式英语, 美/英式区分.

Usage:
    from mssclaw.core.semantic.multilang_detector import MultiLangDetector
    detector = MultiLangDetector()
    result = detector.detect("你好 world 这个 function 怎么样")
"""
import re
from dataclasses import dataclass, field
from typing import Optional

# ── 文言文特征词库 ──
CLASSICAL_PATTERNS = [
    r'(之|乎|者|也|矣|焉|哉|耳|耶|欸|兮|噫)',
    r'(曰|云|谓|言|道|语)\s*[:：]',
    r'(吾|余|予|朕|寡人|臣|妾|仆|某)',
    r'(汝|尔|子|君|公|卿|先生|足下|阁下)',
    r'(盖|夫|惟|故|是故|是以|由此|由是)',
    r'(乃|则|即|便|遂|因|辄|竟|果)',
    r'(盍|何不|岂|宁|独|唯|但|特|只)',
    r'[^a-zA-Z0-9\s](然|而|且|亦|又|复|更|尤|愈|弥|益)',
    r'(者\s*也|所\s*者|为\s*所|见\s*于|被\s*于)',
    r'(不亦|无乃|得无|何其|一何|何如|若何|奈何|如.*何)',
    r'\w{1,2}(之|者|也|矣|乎|哉)\s',
    r'(伏惟|窃以|谨按|恭惟|仰惟|臣闻|盖闻)',
]

# ── 中式英语 (Chinglish) 模式 ──
CHINGLISH_PATTERNS = [
    r'\b(good good study|day day up|long time no see|no can do|people mountain people sea)\b',
    r'\b(add oil|lose face|give you color see see|horse horse tiger tiger)\b',
    r'\b(open\s+the\s+computer|close\s+the\s+light|eat\s+medicine|play\s+phone)\b',
    r'\b(I\s+very\s+like|he\s+very\s+good|you\s+very\s+beautiful|very\s+thanks)\b',
    r'\b(more\s+and\s+more\s+(good|bad|beautiful|strong|fast))\b',
    r'\b(so-so|no\s+why|because\s+so|although\s+but)\b',
    r'\b(can\s+you\s+tell\s+me\s+how\s+to|how\s+to\s+say|how\s+to\s+spell)\b',
    r'\b(I\s+think\s+.*\s+not\b|you\s+are\s+welcome\s+.*\s+no\s+thanks)\b',
    r'\b(according\s+to\s+me|in\s+my\s+opinion\s+I\s+think|as\s+for\s+me)\b',
    r'\b(convenient|comfortable|delicious|colourful)\s+(time|place|food|life)\b',
    r'\b(My\s+name\s+is\s+called|How\s+many\s+years\s+are\s+you)\b',
    r'\b(You\s+are\s+how\s+much\s+years\s+old|Today\s+is\s+hot)\b',
]

# ── 中英混合 (Code-Switching) 模式 ──
CODESWITCH_PATTERNS = [
    r'[\u4e00-\u9fff]{2,}\s+[a-zA-Z]{2,}\s+[\u4e00-\u9fff]{2,}',
    r'[a-zA-Z]{2,}\s+[\u4e00-\u9fff]{2,}\s+[a-zA-Z]{2,}',
    r'(这个|那个|一个|我的|你的)\s+(function|class|method|API|model|data|code|file)',
    r'(搞|做|写|改|调|跑|测|看)\s+(一下|一个|个)\s+(bug|feature|PR|commit|test|demo)',
    r'(我的|你的|他的)\s+(config|setting|option|parameter|variable|object)',
    r'(什么|哪个|怎么|为什么|多少)\s+(error|warning|issue|problem|question)',
    r'\b(ok|OK|fine|good|nice|cool|great|awesome)\b\s*[，。！？]',
    r'[，。！？]\s*\b(but|so|and|then|also|however|because|anyway)\b',
    r'\b(我们|你|我)\s+(需要|要|应该|可以|能)\s+[a-z]{3,}',
]

# ── 美式 vs 英式 差异词 ──
US_UK_PAIRS = {
    'en-US': [r'\b(color|honor|labor|neighbor|flavor|humor|rumor|behavior|favorite)\b',
              r'\b(center|meter|liter|theater|fiber|caliber|somber|scepter)\b',
              r'\b(realize|organize|recognize|analyze|apologize|authorize|categorize)\b',
              r'\b(traveled|traveling|canceled|canceling|modeled|modeling|labeled|labeling)\b',
              r'\b(gray|tire|curb|check\b.*money|plow|connection|inflection|deflection)\b',
              r'\b(program|dialog|catalog|analog|monolog|prolog|epilog|synagog)\b',
              r'\b(practice|license|defense|offense|pretense)\b.*noun'],
    'en-GB': [r'\b(colour|honour|labour|neighbour|flavour|humour|rumour|behaviour|favourite)\b',
              r'\b(centre|metre|litre|theatre|fibre|calibre|sombre|sceptre)\b',
              r'\b(realise|organise|recognise|analyse|apologise|authorise|categorise)\b',
              r'\b(travelled|travelling|cancelled|cancelling|modelled|modelling|labelled|labelling)\b',
              r'\b(grey|tyre|kerb|cheque|plough|connexion|inflexion|deflexion)\b',
              r'\b(programme|dialogue|catalogue|analogue|monologue|prologue|epilogue|synagogue)\b',
              r'\b(practise|licence|defence|offence|pretence)\b.*verb'],
}

@dataclass
class MultiLangResult:
    classical_score: float = 0.0   # 文言文得分
    chinglish_score: float = 0.0   # 中式英语得分
    codeswitch_score: float = 0.0  # 中英混合得分
    us_uk_verdict: str = "neutral" # en-US / en-GB / neutral
    us_score: float = 0.0
    uk_score: float = 0.0
    details: list = field(default_factory=list)


class MultiLangDetector:
    """多语言特征检测器. 补语义引擎的文言文/中英混合/中式英语/美英区分缺口."""

    def __init__(self):
        self._classical_re = [re.compile(p) for p in CLASSICAL_PATTERNS]
        self._chinglish_re = [re.compile(p, re.IGNORECASE) for p in CHINGLISH_PATTERNS]
        self._codeswitch_re = [re.compile(p) for p in CODESWITCH_PATTERNS]
        self._us_re = [re.compile(p, re.IGNORECASE) for p in US_UK_PAIRS['en-US']]
        self._uk_re = [re.compile(p, re.IGNORECASE) for p in US_UK_PAIRS['en-GB']]

    def detect(self, text: str) -> MultiLangResult:
        result = MultiLangResult()

        # 文言文检测
        classical_matches = sum(1 for p in self._classical_re if p.search(text))
        result.classical_score = min(classical_matches / len(self._classical_re), 1.0)
        if result.classical_score > 0.3:
            result.details.append(f"classical_chinese: {result.classical_score:.2f}")

        # 中式英语检测
        chinglish_matches = sum(1 for p in self._chinglish_re if p.search(text))
        result.chinglish_score = min(chinglish_matches / max(len(self._chinglish_re) * 0.3, 1), 1.0)
        if result.chinglish_score > 0.1:
            result.details.append(f"chinglish: {result.chinglish_score:.2f}")

        # 中英混合检测
        codeswitch_matches = sum(1 for p in self._codeswitch_re if p.search(text))
        result.codeswitch_score = min(codeswitch_matches / max(len(self._codeswitch_re) * 0.3, 1), 1.0)
        if result.codeswitch_score > 0.1:
            result.details.append(f"codeswitch: {result.codeswitch_score:.2f}")

        # 美/英式区分
        us_matches = sum(1 for p in self._us_re if p.search(text))
        uk_matches = sum(1 for p in self._uk_re if p.search(text))
        result.us_score = us_matches / max(len(self._us_re), 1)
        result.uk_score = uk_matches / max(len(self._uk_re), 1)

        if us_matches > uk_matches + 1:
            result.us_uk_verdict = "en-US"
        elif uk_matches > us_matches + 1:
            result.us_uk_verdict = "en-GB"
        else:
            result.us_uk_verdict = "neutral"

        if result.us_score > 0.1 or result.uk_score > 0.1:
            result.details.append(f"dialect: {result.us_uk_verdict} (US:{result.us_score:.2f} UK:{result.uk_score:.2f})")

        return result

    def is_classical_chinese(self, text: str) -> bool:
        return self.detect(text).classical_score > 0.3

    def is_chinglish(self, text: str) -> bool:
        return self.detect(text).chinglish_score > 0.2

    def is_codeswitching(self, text: str) -> bool:
        return self.detect(text).codeswitch_score > 0.2
