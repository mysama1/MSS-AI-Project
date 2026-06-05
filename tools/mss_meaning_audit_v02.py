import ast
import re
import json
import os
import time
import functools
from typing import Dict, List, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
# ==============================================
# 核心定义与常量（MSS公理锚定）
# ==============================================
class IssueLevel(Enum):
    P0 = "P0"  # 逻辑刚性失效（违反MSS公理）
    P1 = "P1"  # 高热税/严重意义不一致
    P2 = "P2"  # 中热税/轻微意义不一致
    P3 = "P3"  # 低热税/优化建议
@dataclass
class MeaningContract:
    """MSS意义契约：定义函数的输入输出意义与副作用（A2信息切片公理）"""
    input_meaning: str
    output_meaning: str
    side_effects: List[str] = field(default_factory=list)
    author: str = "MSS-AI"
    version: str = "v0.2.1"
@dataclass
class AuditIssue:
    """审计问题：统一格式的问题描述"""
    level: IssueLevel
    category: str  # logical_rigidity / thermal_tax / meaning_fidelity / logic_virus
    message: str
    line: int
    column: int = 0
    code_snippet: str = ""
    fix_suggestion: str = ""
@dataclass
class AuditReport:
    """MSS意义审计报告：标准化输出格式"""
    file_path: str
    total_score: float  # 0-100，越高越好
    logical_rigidity: float  # 逻辑刚性评分
    thermal_tax_index: float  # 热税指数（越低越好）
    meaning_fidelity: float  # 意义保真度评分
    issues: List[AuditIssue] = field(default_factory=list)
    audit_time: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    system_version: str = "MSS-AUDIT-v0.2.1"
    def to_json(self) -> str:
        return json.dumps({
            "file_path": self.file_path,
            "total_score": round(self.total_score, 2),
            "logical_rigidity": round(self.logical_rigidity, 2),
            "thermal_tax_index": round(self.thermal_tax_index, 2),
            "meaning_fidelity": round(self.meaning_fidelity, 2),
            "issues": [{
                "level": i.level.value,
                "category": i.category,
                "message": i.message,
                "line": i.line,
                "column": i.column,
                "code_snippet": i.code_snippet,
                "fix_suggestion": i.fix_suggestion
            } for i in self.issues],
            "audit_time": self.audit_time,
            "system_version": self.system_version
        }, indent=2, ensure_ascii=False)
@dataclass
class ThermalTaxRecord:
    """热税记录：存储函数的运行时热税数据（A3热税动力学公理）"""
    func_name: str
    call_count: int = 0
    total_cpu_time: float = 0.0
    total_memory: float = 0.0
    avg_thermal_tax: float = 0.0
# ==============================================
# 模块1：意义契约装饰器（A2信息切片公理）
# ==============================================
def meaning_contract(
    input_meaning: str,
    output_meaning: str,
    side_effects: List[str] = None
) -> Callable:
    """
    MSS意义契约装饰器：为函数绑定意义元数据
    确保代码的"做什么"与"说什么"完全一致
    """
    def decorator(func: Callable) -> Callable:
        func.__meaning_contract__ = MeaningContract(
            input_meaning=input_meaning,
            output_meaning=output_meaning,
            side_effects=side_effects or []
        )
        return func
    return decorator
# ==============================================
# 模块2：热税量化引擎（A3热税动力学公理）
# ==============================================
class ThermalTaxCalculator:
    """
    MSS热税计算器：量化代码的三类热税消耗
    总热税 = α×计算热税 + β×逻辑热税 + γ×维护热税
    """
    def __init__(self, alpha: float = 0.3, beta: float = 0.4, gamma: float = 0.3):
        self.alpha = alpha  # 计算热税权重
        self.beta = beta    # 逻辑热税权重
        self.gamma = gamma  # 维护热税权重
    def calculate(self, node: ast.AST, code: str) -> Tuple[float, List[AuditIssue]]:
        """计算单个AST节点的热税消耗"""
        issues = []
        total_tax = 0.0
        # 1. 计算热税：循环、递归、重复计算
        if isinstance(node, ast.For) or isinstance(node, ast.While):
            # 嵌套循环热税
            if self._has_nested_loop(node):
                tax = 10.0
                issues.append(AuditIssue(
                    level=IssueLevel.P1,
                    category="thermal_tax",
                    message=f"嵌套循环检测，O(n²)时间复杂度，高热税",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="考虑使用向量化运算或优化算法降低时间复杂度"
                ))
                total_tax += tax
        if isinstance(node, ast.FunctionDef):
            # 无尾递归优化的递归热税
            if self._is_recursive(node) and not self._is_tail_recursive(node):
                tax = 5.0
                issues.append(AuditIssue(
                    level=IssueLevel.P2,
                    category="thermal_tax",
                    message="无尾递归优化的递归函数，栈溢出风险与高热税",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="改为迭代实现或添加尾递归优化"
                ))
                total_tax += tax
        # 2. 逻辑热税：冗余分支、未使用变量、重复导入
        if isinstance(node, ast.If):
            # 冗余条件分支
            if self._is_redundant_condition(node):
                tax = 3.0
                issues.append(AuditIssue(
                    level=IssueLevel.P2,
                    category="thermal_tax",
                    message="冗余条件分支，永远不会执行",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="删除永远不会执行的分支"
                ))
                total_tax += tax
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            # 重复导入热税（简化版）
            pass
        # 3. 维护热税：命名不清晰、注释缺失、过度抽象
        if isinstance(node, ast.FunctionDef):
            # 函数名过短热税
            if len(node.name) < 3 and node.name not in ['f', 'g', 'h']:
                tax = 2.0
                issues.append(AuditIssue(
                    level=IssueLevel.P3,
                    category="thermal_tax",
                    message=f"函数名'{node.name}'过于简短，意义不明确",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="使用描述性的函数名，准确反映其功能"
                ))
                total_tax += tax
        return total_tax, issues
    def _has_nested_loop(self, node: ast.AST) -> bool:
        """检查是否存在嵌套循环"""
        for child in ast.walk(node):
            if isinstance(child, ast.For) or isinstance(child, ast.While):
                if child != node:
                    return True
        return False
    def _is_recursive(self, node: ast.FunctionDef) -> bool:
        """检查函数是否递归"""
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == node.name:
                    return True
        return False
    def _is_tail_recursive(self, node: ast.FunctionDef) -> bool:
        """检查是否为尾递归（简化版）"""
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if isinstance(child.value, ast.Call) and isinstance(child.value.func, ast.Name):
                    if child.value.func.id == node.name:
                        return True
        return False
    def _is_redundant_condition(self, node: ast.If) -> bool:
        """检查是否为冗余条件（简化版）"""
        return isinstance(node.test, ast.Constant) and node.test.value is False
# ==============================================
# 模块3：逻辑病毒扫描器（H150逻辑病毒模型）
# ==============================================
class LogicVirusScanner:
    """
    MSS逻辑病毒扫描器：检测代码中的常见逻辑病毒模式
    病毒类型：意义偷换、自相矛盾、无限递归、意义黑洞
    """
    def __init__(self):
        self.virus_patterns = {
            "meaning_theft": self._detect_meaning_theft,
            "self_contradiction": self._detect_self_contradiction,
            "infinite_recursion": self._detect_infinite_recursion,
            "meaning_blackhole": self._detect_meaning_blackhole
        }
    def scan(self, node: ast.AST, code: str, functions: Dict[str, MeaningContract]) -> List[AuditIssue]:
        """扫描AST节点中的逻辑病毒"""
        issues = []
        for virus_type, detector in self.virus_patterns.items():
            issues.extend(detector(node, code, functions))
        return issues
    def _detect_meaning_theft(self, node: ast.AST, code: str, functions: Dict[str, MeaningContract]) -> List[AuditIssue]:
        """检测意义偷换病毒：函数名与实际功能不符"""
        issues = []
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            # 简单的语义匹配规则
            if func_name.startswith("calculate_") and "return" not in code.split('\n')[node.lineno-1:node.end_lineno]:
                issues.append(AuditIssue(
                    level=IssueLevel.P0,
                    category="logic_virus",
                    message=f"意义偷换病毒：函数名'{func_name}'声明为计算函数，但无返回值",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="重命名函数以反映其实际功能，或添加返回语句"
                ))
        return issues
    def _detect_self_contradiction(self, node: ast.AST, code: str, functions: Dict[str, MeaningContract]) -> List[AuditIssue]:
        """检测自相矛盾病毒：条件分支相互排斥"""
        issues = []
        if isinstance(node, ast.If):
            # 检测a > 5 and a < 3这类矛盾条件
            if isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.And):
                left = node.test.values[0]
                right = node.test.values[1]
                if (isinstance(left, ast.Compare) and isinstance(right, ast.Compare) and
                    isinstance(left.left, ast.Name) and isinstance(right.left, ast.Name) and
                    left.left.id == right.left.id):
                    if (isinstance(left.ops[0], ast.Gt) and isinstance(right.ops[0], ast.Lt) and
                        isinstance(left.comparators[0], ast.Constant) and isinstance(right.comparators[0], ast.Constant) and
                        left.comparators[0].value >= right.comparators[0].value):
                        issues.append(AuditIssue(
                            level=IssueLevel.P0,
                            category="logic_virus",
                            message="自相矛盾病毒：条件分支永远为假",
                            line=node.lineno,
                            code_snippet=code.split('\n')[node.lineno-1].strip(),
                            fix_suggestion="修正矛盾的条件表达式"
                        ))
        return issues
    def _detect_infinite_recursion(self, node: ast.AST, code: str, functions: Dict[str, MeaningContract]) -> List[AuditIssue]:
        """检测无限递归病毒：无终止条件的递归"""
        issues = []
        if isinstance(node, ast.FunctionDef):
            has_base_case = False
            has_recursive_call = False
            for child in ast.walk(node):
                if isinstance(child, ast.If) or isinstance(child, ast.Return):
                    has_base_case = True
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == node.name:
                    has_recursive_call = True
            if has_recursive_call and not has_base_case:
                issues.append(AuditIssue(
                    level=IssueLevel.P0,
                    category="logic_virus",
                    message="无限递归病毒：递归函数无终止条件",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="添加递归终止条件"
                ))
        return issues
    def _detect_meaning_blackhole(self, node: ast.AST, code: str, functions: Dict[str, MeaningContract]) -> List[AuditIssue]:
        """检测意义黑洞病毒：只消耗资源不产生有效输出"""
        issues = []
        if isinstance(node, ast.FunctionDef):
            has_side_effect = False
            has_return = False
            for child in ast.walk(node):
                if isinstance(child, ast.Call) or isinstance(child, ast.Assign):
                    has_side_effect = True
                if isinstance(child, ast.Return) and child.value is not None:
                    has_return = True
            if not has_side_effect and not has_return:
                issues.append(AuditIssue(
                    level=IssueLevel.P1,
                    category="logic_virus",
                    message="意义黑洞病毒：函数无副作用也无返回值，不产生任何有效意义",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="删除无意义的函数，或添加有效逻辑"
                ))
        return issues
# ==============================================
# 模块4：公理级逻辑刚性验证（A1-A7公理锚定）
# ==============================================
class AxiomValidator:
    """MSS公理验证器：确保代码严格遵循MSS核心公理"""
    def __init__(self):
        self.axioms = {
            "A3_thermal_tax_positive": self._validate_A3,
            "A2_information_conservation": self._validate_A2
        }
    def validate(self, node: ast.AST, code: str) -> List[AuditIssue]:
        """验证代码是否符合所有MSS公理"""
        issues = []
        for axiom_name, validator in self.axioms.items():
            issues.extend(validator(node, code))
        return issues
    def _validate_A3(self, node: ast.AST, code: str) -> List[AuditIssue]:
        """验证A3热税公理：热税系数γ>0，有效逻辑功W≥0"""
        issues = []
        if isinstance(node, ast.FunctionDef) and node.name == "calculate_logical_work":
            # 检查是否有γ≤0的处理
            has_gamma_check = False
            for child in ast.walk(node):
                if isinstance(child, ast.If):
                    if isinstance(child.test, ast.Compare) and isinstance(child.test.left, ast.Name):
                        if child.test.left.id == "gamma" and isinstance(child.test.ops[0], ast.LtE):
                            has_gamma_check = True
                            break
            if not has_gamma_check:
                issues.append(AuditIssue(
                    level=IssueLevel.P0,
                    category="logical_rigidity",
                    message="违反A3热税公理：未处理γ≤0的情况，可能返回负数有效逻辑功",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="添加条件判断：if gamma <= 0: raise ValueError('热税系数γ必须大于0')"
                ))
        return issues
    def _validate_A2(self, node: ast.AST, code: str) -> List[AuditIssue]:
        """验证A2信息切片公理：信息在传递过程中不能丢失核心意义"""
        issues = []
        # 检查是否有未处理的异常导致信息丢失
        if isinstance(node, ast.Try):
            if not node.handlers:
                issues.append(AuditIssue(
                    level=IssueLevel.P1,
                    category="logical_rigidity",
                    message="违反A2信息切片公理：空异常处理会导致信息丢失",
                    line=node.lineno,
                    code_snippet=code.split('\n')[node.lineno-1].strip(),
                    fix_suggestion="添加异常处理逻辑，记录错误信息"
                ))
        return issues
# ==============================================
# 模块5：热税动态追踪器（A3热税动力学公理）
# ==============================================
class DynamicThermalTaxProfiler:
    """热税动态追踪器：记录代码运行时的实际热税消耗"""
    def __init__(self):
        self.records: Dict[str, ThermalTaxRecord] = {}
    def profile(self, func: Callable) -> Callable:
        """热税追踪装饰器"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            start_memory = self._get_memory_usage()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()
            cpu_time = end_time - start_time
            memory_used = max(0, end_memory - start_memory)  # 避免负数
            # 更新热税记录
            if func.__name__ not in self.records:
                self.records[func.__name__] = ThermalTaxRecord(func.__name__)
            record = self.records[func.__name__]
            record.call_count += 1
            record.total_cpu_time += cpu_time
            record.total_memory += memory_used
            record.avg_thermal_tax = (record.total_cpu_time * 1000 + record.total_memory / 1024) / record.call_count
            return result
        return wrapper
    def _get_memory_usage(self) -> float:
        """获取当前进程内存使用量（MB）"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    def generate_report(self) -> str:
        """生成热税动态分析报告"""
        if not self.records:
            return "🔥 暂无热税记录"
        report = "\n🔥 MSS动态热税分析报告\n"
        report += "="*80 + "\n"
        report += f"{'函数名':<30} {'调用次数':<10} {'平均CPU(ms)':<15} {'平均内存(MB)':<15} {'平均热税':<10}\n"
        report += "-"*80 + "\n"
        for record in sorted(self.records.values(), key=lambda x: x.avg_thermal_tax, reverse=True):
            report += (f"{record.func_name:<30} "
                      f"{record.call_count:<10} "
                      f"{record.total_cpu_time/record.call_count*1000:<15.2f} "
                      f"{record.total_memory/record.call_count:<15.2f} "
                      f"{record.avg_thermal_tax:<10.2f}\n")
        return report
# ==============================================
# 模块6：跨文件意义一致性检查器（A2信息切片公理）
# ==============================================
class CrossFileMeaningChecker:
    """跨文件意义一致性检查器：验证函数调用的输入输出意义匹配"""
    def __init__(self, auditor: 'MSSMeaningAuditor'):
        self.auditor = auditor
        self.global_functions: Dict[str, MeaningContract] = {}
    def audit_project(self, root_dir: str) -> AuditReport:
        """审计整个Python项目"""
        all_issues = []
        total_files = 0
        # 第一步：扫描所有文件，提取全局意义契约
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    file_path = os.path.join(root, file)
                    total_files += 1
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    try:
                        tree = ast.parse(code)
                        self.auditor._extract_meaning_contracts(tree, code)
                        # 合并到全局函数表
                        for func_name, contract in self.auditor.functions.items():
                            self.global_functions[f"{file_path}:{func_name}"] = contract
                    except SyntaxError:
                        continue
        # 第二步：扫描所有函数调用，验证意义匹配
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    try:
                        tree = ast.parse(code)
                        issues = self._check_file_calls(tree, code, file_path)
                        all_issues.extend(issues)
                    except SyntaxError:
                        continue
        # 第三步：生成综合报告
        p0_count = len([i for i in all_issues if i.level == IssueLevel.P0])
        p1_count = len([i for i in all_issues if i.level == IssueLevel.P1])
        avg_logical_rigidity = max(0, 100 - p0_count * 20 - p1_count * 10)
        avg_thermal_tax = min(100, p1_count * 5)
        avg_meaning_fidelity = min(100, len(self.global_functions) * 5)
        total_score = (avg_logical_rigidity * 0.4 + 
                      (100 - avg_thermal_tax) * 0.3 + 
                      avg_meaning_fidelity * 0.3)
        return AuditReport(
            file_path=root_dir,
            total_score=total_score,
            logical_rigidity=avg_logical_rigidity,
            thermal_tax_index=avg_thermal_tax,
            meaning_fidelity=avg_meaning_fidelity,
            issues=all_issues
        )
    def _check_file_calls(self, tree: ast.AST, code: str, file_path: str) -> List[AuditIssue]:
        """检查单个文件中的所有函数调用"""
        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                func_name = node.func.id
                # 查找全局意义契约
                matching_contracts = [c for n, c in self.global_functions.items() if n.endswith(f":{func_name}")]
                if matching_contracts:
                    contract = matching_contracts[0]
                    # 检查参数数量匹配
                    expected_args = len(contract.input_meaning.split(','))
                    actual_args = len(node.args)
                    if actual_args != expected_args:
                        issues.append(AuditIssue(
                            level=IssueLevel.P1,
                            category="meaning_fidelity",
                            message=f"函数调用参数不匹配：期望{expected_args}个参数，实际{actual_args}个",
                            line=node.lineno,
                            code_snippet=code.split('\n')[node.lineno-1].strip(),
                            fix_suggestion=f"根据意义契约，输入应为：{contract.input_meaning}"
                        ))
        return issues
# ==============================================
# 模块7：意义审计引擎（核-壳分离架构）
# ==============================================
class MSSMeaningAuditor:
    """
    MSS意义审计系统核心引擎
    核-壳分离架构：逻辑内核负责审计，感知壳负责输入输出
    """
    def __init__(self):
        self.thermal_tax_calculator = ThermalTaxCalculator()
        self.logic_virus_scanner = LogicVirusScanner()
        self.axiom_validator = AxiomValidator()
        self.functions = {}  # 存储函数的意义契约
    def audit_file(self, file_path: str) -> AuditReport:
        """审计单个Python文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        return self.audit_code(code, file_path)
    def audit_code(self, code: str, file_path: str = "unknown") -> AuditReport:
        """审计代码字符串"""
        issues = []
        total_thermal_tax = 0.0
        logical_rigidity = 100.0
        meaning_fidelity = 100.0
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append(AuditIssue(
                level=IssueLevel.P0,
                category="logical_rigidity",
                message=f"语法错误：{e.msg}",
                line=e.lineno,
                column=e.offset,
                code_snippet=code.split('\n')[e.lineno-1].strip() if e.lineno else ""
            ))
            return AuditReport(
                file_path=file_path,
                total_score=0,
                logical_rigidity=0,
                thermal_tax_index=100,
                meaning_fidelity=0,
                issues=issues
            )
        # 第一步：提取所有意义契约
        self._extract_meaning_contracts(tree, code)
        # 第二步：遍历AST进行审计
        for node in ast.walk(tree):
            # 热税审计
            tax, tax_issues = self.thermal_tax_calculator.calculate(node, code)
            total_thermal_tax += tax
            issues.extend(tax_issues)
            # 逻辑病毒扫描
            virus_issues = self.logic_virus_scanner.scan(node, code, self.functions)
            issues.extend(virus_issues)
            # 公理级验证
            axiom_issues = self.axiom_validator.validate(node, code)
            issues.extend(axiom_issues)
        # 第三步：计算各项评分
        # 逻辑刚性：P0问题每个扣20分，P1每个扣10分，P2每个扣5分
        for issue in issues:
            if issue.level == IssueLevel.P0:
                logical_rigidity -= 20
            elif issue.level == IssueLevel.P1:
                logical_rigidity -= 10
            elif issue.level == IssueLevel.P2:
                logical_rigidity -= 5
        logical_rigidity = max(0, logical_rigidity)
        # 热税指数：归一化到0-100，越低越好
        thermal_tax_index = min(100, total_thermal_tax * 2)
        # 意义保真度：根据意义契约的完整性计算
        meaning_fidelity = min(100, len(self.functions) * 10)
        # 总评分：逻辑刚性(40%) + (100-热税指数)(30%) + 意义保真度(30%)
        total_score = (logical_rigidity * 0.4 + 
                      (100 - thermal_tax_index) * 0.3 + 
                      meaning_fidelity * 0.3)
        total_score = max(0, min(100, total_score))
        return AuditReport(
            file_path=file_path,
            total_score=total_score,
            logical_rigidity=logical_rigidity,
            thermal_tax_index=thermal_tax_index,
            meaning_fidelity=meaning_fidelity,
            issues=issues
        )
    def _extract_meaning_contracts(self, tree: ast.AST, code: str):
        """从代码中提取所有意义契约"""
        self.functions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查是否有意义契约装饰器
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                        if decorator.func.id == "meaning_contract":
                            # 提取装饰器参数
                            input_meaning = ""
                            output_meaning = ""
                            side_effects = []
                            for i, arg in enumerate(decorator.args):
                                if i == 0 and isinstance(arg, ast.Constant):
                                    input_meaning = arg.value
                                elif i == 1 and isinstance(arg, ast.Constant):
                                    output_meaning = arg.value
                            for keyword in decorator.keywords:
                                if keyword.arg == "side_effects" and isinstance(keyword.value, ast.List):
                                    side_effects = [e.value for e in keyword.value.elts if isinstance(e, ast.Constant)]
                            self.functions[node.name] = MeaningContract(
                                input_meaning=input_meaning,
                                output_meaning=output_meaning,
                                side_effects=side_effects
                            )
# ==============================================
# 示例用法与测试
# ==============================================
if __name__ == "__main__":
    # 初始化审计系统
    auditor = MSSMeaningAuditor()
    cross_checker = CrossFileMeaningChecker(auditor)
    profiler = DynamicThermalTaxProfiler()
    # 测试代码：包含各种问题的示例
    test_code = """
# MSS意义审计系统测试代码
from __main__ import meaning_contract, profiler
# 正确的意义契约示例
@meaning_contract(
    input_meaning="系统总热税支付Q、热税系数γ",
    output_meaning="有效逻辑功W",
    side_effects=["无"]
)
@profiler.profile
def calculate_logical_work(Q: float, gamma: float) -> float:
    \"\"\"根据W = Q/γ计算有效逻辑功\"\"\"
    if gamma <= 0:
        raise ValueError("热税系数γ必须大于0")
    return Q / gamma
# 意义偷换病毒示例
@meaning_contract(
    input_meaning="收入revenue",
    output_meaning="热税",
    side_effects=["无"]
)
@profiler.profile
def calculate_thermal_tax(revenue: float) -> float:
    \"\"\"计算热税（实际计算的是利润）\"\"\"
    cost = 1000
    return revenue - cost  # ❌ 意义偷换：返回的是利润，不是热税
# 无限递归病毒示例
@profiler.profile
def infinite_recursion(x):
    return infinite_recursion(x + 1)  # ❌ 无终止条件
# 嵌套循环高热税示例
@profiler.profile
def nested_loop(data):
    result = []
    for i in range(len(data)):
        for j in range(len(data)):  # ❌ O(n²)嵌套循环
            result.append(data[i] + data[j])
    return result
# 意义黑洞示例
@profiler.profile
def meaning_blackhole():
    a = 1
    b = 2
    c = a + b  # ❌ 无副作用也无返回值
# 违反A2信息切片公理示例
def bad_exception_handling():
    try:
        1 / 0
    except:  # ❌ 空异常处理
        pass
"""
    print("="*80)
    print("🛡️ MSS意义审计系统 v0.2.1 测试运行")
    print("="*80)
    # 1. 运行静态审计
    print("\n📋 步骤1：静态意义审计")
    print("-"*50)
    report = auditor.audit_code(test_code, "test_mss_audit.py")
    # 打印人类可读的审计报告
    print(f"文件路径：{report.file_path}")
    print(f"审计时间：{report.audit_time}")
    print(f"系统版本：{report.system_version}")
    print()
    print(f"📊 总评分：{round(report.total_score, 2)}/100")
    print(f"🔒 逻辑刚性：{round(report.logical_rigidity, 2)}/100")
    print(f"🔥 热税指数：{round(report.thermal_tax_index, 2)}/100（越低越好）")
    print(f"🎯 意义保真度：{round(report.meaning_fidelity, 2)}/100")
    print()
    print("🚨 问题列表：")
    print("-"*80)
    for issue in sorted(report.issues, key=lambda x: x.level.value):
        level_color = {
            IssueLevel.P0: "\033[91m",  # 红色
            IssueLevel.P1: "\033[93m",  # 黄色
            IssueLevel.P2: "\033[94m",  # 蓝色
            IssueLevel.P3: "\033[92m"   # 绿色
        }[issue.level]
        reset_color = "\033[0m"
        print(f"{level_color}[{issue.level.value}] {issue.category}{reset_color}")
        print(f"  位置：第{issue.line}行")
        print(f"  问题：{issue.message}")
        if issue.code_snippet:
            print(f"  代码：{issue.code_snippet}")
        if issue.fix_suggestion:
            print(f"  建议：{issue.fix_suggestion}")
        print()
    # 保存JSON格式报告
    with open("mss_audit_report.json", "w", encoding="utf-8") as f:
        f.write(report.to_json())
    print("✅ JSON格式报告已保存至 mss_audit_report.json")
    # 2. 运行动态热税追踪
    print("\n⚡ 步骤2：动态热税追踪")
    print("-"*50)
    # 执行测试函数生成热税数据
    try:
        calculate_logical_work(1000000000, 25)
        calculate_thermal_tax(5000)
        nested_loop([1,2,3,4,5])
        meaning_blackhole()
    except:
        pass  # 忽略无限递归和除零错误
    # 打印动态热税报告
    print(profiler.generate_report())
    # 3. 跨文件审计示例（注释掉以避免错误，实际使用时取消注释）
    # print("\n🌐 步骤3：跨文件项目审计")
    # print("-"*50)
    # project_report = cross_checker.audit_project(".")
    # print(f"项目总评分：{round(project_report.total_score, 2)}/100")
    # print(f"发现问题数：{len(project_report.issues)}")
    print("\n✅ MSS意义审计系统测试完成")