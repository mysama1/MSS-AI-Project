"""
MSS-Proof: TPTP Parser
解析TPTP (Thousands of Problems for Theorem Provers) 格式的数学定理
支持 FOF (First-Order Form), CNF (Clause Normal Form), TFF (Typed First-Order Form)

Phase 1 M1.1 | D5-033 楔子穿刺项目
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class TPTPRole(Enum):
    AXIOM = "axiom"
    HYPOTHESIS = "hypothesis"
    CONJECTURE = "conjecture"
    NEGATED_CONJECTURE = "negated_conjecture"
    DEFINITION = "definition"
    LEMMA = "lemma"
    THEOREM = "theorem"
    UNKNOWN = "unknown"


class FormulaType(Enum):
    FOF = "fof"          # First-Order Formula
    CNF = "cnf"          # Clause Normal Form
    TFF = "tff"          # Typed First-Order Form
    THF = "thf"          # Typed Higher-Order Form
    INCLUDE = "include"


@dataclass
class TPTPStatement:
    """单条TPTP语句"""
    name: str
    role: TPTPRole
    formula_type: FormulaType
    raw_formula: str
    annotations: Dict[str, str] = field(default_factory=dict)

    def __repr__(self):
        return f"TPTPStatement({self.formula_type.value}({self.name}, {self.role.value}))"


@dataclass
class TPTPProblem:
    """完整TPTP问题"""
    path: str = ""
    statements: List[TPTPStatement] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)

    @property
    def axioms(self) -> List[TPTPStatement]:
        return [s for s in self.statements if s.role == TPTPRole.AXIOM]

    @property
    def conjectures(self) -> List[TPTPStatement]:
        return [s for s in self.statements if s.role == TPTPRole.CONJECTURE]

    @property
    def hypotheses(self) -> List[TPTPStatement]:
        return [s for s in self.statements if s.role == TPTPRole.HYPOTHESIS]

    def summary(self) -> str:
        return (f"Problem({self.path}): {len(self.statements)} statements "
                f"[{len(self.axioms)} axioms, {len(self.hypotheses)} hypotheses, "
                f"{len(self.conjectures)} conjectures]")


class TPTPParser:
    """TPTP格式解析器"""
    
    # Regex patterns for TPTP syntax
    COMMENT_RE = re.compile(r'%.*$', re.MULTILINE)
    INCLUDE_RE = re.compile(r'include\(\s*[\'"]([^\'"]+)[\'"]\s*[,\)]')
    
    FOF_RE = re.compile(
        r'fof\(\s*([^,]+)\s*,\s*(axiom|hypothesis|conjecture|definition|lemma|theorem|negated_conjecture)\s*,',
        re.IGNORECASE
    )
    CNF_RE = re.compile(
        r'cnf\(\s*([^,]+)\s*,\s*(axiom|hypothesis|conjecture|definition|lemma|theorem|negated_conjecture)\s*,',
        re.IGNORECASE
    )
    TFF_RE = re.compile(
        r'tff\(\s*([^,]+)\s*,\s*(axiom|hypothesis|conjecture|definition|lemma|theorem|negated_conjecture)\s*,',
        re.IGNORECASE
    )
    THF_RE = re.compile(
        r'thf\(\s*([^,]+)\s*,\s*(axiom|hypothesis|conjecture|definition|lemma|theorem|negated_conjecture)\s*,',
        re.IGNORECASE
    )
    
    FORMULA_TYPE_MAP = {
        'fof': (FOF_RE, FormulaType.FOF),
        'cnf': (CNF_RE, FormulaType.CNF),
        'tff': (TFF_RE, FormulaType.TFF),
        'thf': (THF_RE, FormulaType.THF),
    }
    
    @classmethod
    def parse_role(cls, role_str: str) -> TPTPRole:
        role_map = {
            'axiom': TPTPRole.AXIOM,
            'hypothesis': TPTPRole.HYPOTHESIS,
            'conjecture': TPTPRole.CONJECTURE,
            'negated_conjecture': TPTPRole.NEGATED_CONJECTURE,
            'definition': TPTPRole.DEFINITION,
            'lemma': TPTPRole.LEMMA,
            'theorem': TPTPRole.THEOREM,
        }
        return role_map.get(role_str.lower().strip(), TPTPRole.UNKNOWN)
    
    @classmethod
    def parse_file(cls, filepath: str) -> TPTPProblem:
        """解析TPTP问题文件"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return cls.parse_string(content, filepath)
    
    @classmethod
    def parse_string(cls, content: str, path: str = "") -> TPTPProblem:
        """解析TPTP格式字符串"""
        problem = TPTPProblem(path=path)
        
        # Remove comments
        cleaned = cls.COMMENT_RE.sub('', content)
        
        # Extract includes
        for m in cls.INCLUDE_RE.finditer(cleaned):
            problem.includes.append(m.group(1))
        
        # Parse each statement type
        for prefix, (regex, formula_type) in cls.FORMULA_TYPE_MAP.items():
            # Find all statements of this type by scanning for keyword
            pos = 0
            while True:
                idx = cleaned.find(f'{prefix}(', pos)
                if idx == -1:
                    break
                    
                match = regex.search(cleaned, idx)
                if not match:
                    pos = idx + 1
                    continue
                
                name = match.group(1).strip()
                role_str = match.group(2).strip()
                
                # Extract formula body (handle nested parentheses)
                start = match.end()
                body, end_pos = cls._extract_parenthesized(cleaned, start)
                
                statement = TPTPStatement(
                    name=name,
                    role=cls.parse_role(role_str),
                    formula_type=formula_type,
                    raw_formula=body,
                )
                problem.statements.append(statement)
                pos = end_pos if end_pos > pos else idx + 1
        
        return problem
    
    @classmethod
    def _extract_parenthesized(cls, text: str, start: int) -> Tuple[str, int]:
        """提取括号内的内容，处理嵌套"""
        if start >= len(text) or text[start] != '(':
            return "", start
        
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return text[start+1:i].strip(), i + 1
            i += 1
        
        return text[start+1:].strip(), len(text)
    
    # ---- 公式操作 ---- 
    
    @staticmethod
    def get_predicates(formula: str) -> List[str]:
        """提取公式中的谓词符号 (TPTP FOF用小写)"""
        preds = set()
        # TPTP FOF: 谓词和函数都是小写标识符 + '('
        pattern = re.compile(r'([a-z][a-zA-Z0-9_]*)\s*\(')
        # 排除逻辑关键词
        logic_keywords = {'fof', 'cnf', 'tff', 'thf', 'include', 'not', 'and', 'or'}
        for m in pattern.finditer(formula):
            name = m.group(1)
            if name not in logic_keywords:
                preds.add(name)
        return sorted(preds)
    
    @staticmethod
    def get_functions(formula: str) -> List[str]:
        """提取公式中的函数符号"""
        # 匹配小写字母开头的标识符后跟'('
        funcs = set()
        pattern = re.compile(r'([a-z][a-zA-Z0-9_]*)\s*\(')
        for m in pattern.finditer(formula):
            fname = m.group(1)
            # 排除逻辑连接词
            if fname not in ('fof', 'cnf', 'tff', 'thf', 'include'):
                funcs.add(fname)
        return sorted(funcs)
    
    @staticmethod
    def get_quantifiers(formula: str) -> List[Tuple[str, str]]:
        """提取量词: 返回 [(type, variable), ...]"""
        quant_pattern = re.compile(r'(!|\\?)\s*\[\s*([^]]+)\s*\]')
        results = []
        for m in quant_pattern.finditer(formula):
            qtype = 'forall' if m.group(1) == '!' else 'exists'
            variables = [v.strip() for v in m.group(2).split(',')]
            for v in variables:
                results.append((qtype, v))
        return results
    
    @classmethod
    def to_z3_smt(cls, formula: str) -> str:
        """将TPTP公式转换为Z3 SMT-LIB2格式 (粗略转换)"""
        # 基础替换映射
        replacements = {
            '~': 'not',
            '|': 'or',
            '&': 'and',
            '=>': '=>',
            '<=>': '=',
            '!': 'forall',
            '?': 'exists',
            '$true': 'true',
            '$false': 'false',
        }
        result = formula
        for tptp_op, smt_op in replacements.items():
            result = result.replace(f' {tptp_op} ', f' {smt_op} ')
        
        # 处理量词: ![X]:P → (forall ((X Type)) P)
        # 简化版: 这里只做基础转换，完整版需要类型推断
        result = re.sub(r'!\s*\[([^\]]+)\]\s*:', r'(forall (\1))', result)
        result = re.sub(r'\?\s*\[([^\]]+)\]\s*:', r'(exists (\1))', result)
        
        return result


# ---- 自测 ----

def _test():
    """TPTP Parser自测"""
    test_fof = """
    % Test problem
    fof(a1, axiom, ![X]: (p(X) => q(X))).
    fof(h1, hypothesis, p(a)).
    fof(c1, conjecture, q(a)).
    """
    
    problem = TPTPParser.parse_string(test_fof, "test.p")
    
    # Test 1: Parse count
    assert len(problem.statements) == 3, f"Expected 3, got {len(problem.statements)}"
    print("PASS: Parse 3 statements")
    
    # Test 2: Axiom count
    assert len(problem.axioms) == 1
    print("PASS: 1 axiom")
    
    # Test 3: Conjecture count
    assert len(problem.conjectures) == 1
    print("PASS: 1 conjecture")
    
    # Test 4: Hypothesis count
    assert len(problem.hypotheses) == 1
    print("PASS: 1 hypothesis")
    
    # Test 5: Predicate extraction
    preds = TPTPParser.get_predicates("![X]: (p(X) => q(X))")
    assert 'p' in preds and 'q' in preds, f"Expected p,q in {preds}"
    print(f"PASS: Predicates extracted: {preds}")
    
    # Test 6: Quantifier extraction
    quants = TPTPParser.get_quantifiers("![X]: (p(X) => q(X))")
    assert len(quants) == 1 and quants[0][0] == 'forall'
    print("PASS: Quantifier extraction")
    
    # Test 7: Summary
    summary = problem.summary()
    assert "3 statements" in summary
    print(f"PASS: Summary = {summary}")
    
    # Test 8: Parenthesis extraction
    body, _ = TPTPParser._extract_parenthesized("(a => (b | c)) extra", 0)
    assert body == "a => (b | c)"
    print(f"PASS: Nested paren extraction: {body}")
    
    print("\n=== TPTP Parser: 8/8 PASS ===")
    return True


if __name__ == "__main__":
    _test()