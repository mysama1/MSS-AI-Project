"""
MSS-Agent SDK 独立测试套件（无需pytest）
"""
import sys
import traceback
from mss_agent_sdk import MSSClient, mss_audit, mss_anchor
from mss_agent_sdk.mss_types import AnchorLevel, Confidence, AuditResult
from mss_agent_sdk.config import SDKConfig


class TestRunner:
    """简易测试运行器"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run(self, name, func):
        """运行单个测试"""
        try:
            func()
            print(f"  ✅ {name}")
            self.passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            self.errors.append((name, traceback.format_exc()))
            self.failed += 1
    
    def summary(self):
        """打印摘要"""
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"测试结果: {self.passed}/{total} 通过")
        if self.failed > 0:
            print(f"失败: {self.failed}")
            for name, err in self.errors:
                print(f"\n--- {name} ---")
                print(err[:500])
        return self.failed == 0


def test_client_init_default():
    client = MSSClient()
    assert client.config is not None
    assert client.config.logic_rigidity_threshold == 0.6


def test_client_init_custom_config():
    config = SDKConfig(logic_rigidity_threshold=0.8)
    client = MSSClient(config)
    assert client.config.logic_rigidity_threshold == 0.8


def test_local_audit_pass():
    client = MSSClient()
    result = client.audit("这是一个正常的陈述，没有绝对化表述。")
    assert isinstance(result, AuditResult)
    assert result.layer in ["L1", "L2", "L3", "L4"]


def test_local_audit_forbidden_words():
    client = MSSClient()
    result = client.audit("这是终极真理，完美无缺。")
    assert not result.passed
    assert len(result.contradictions) > 0
    assert any("终极" in c for c in result.contradictions)


def test_estimate_logic_rigidity():
    client = MSSClient()
    # 形式化表述加分
    m_l_formal = client._estimate_logic_rigidity("∀x ∈ S, P(x) ⇒ Q(x)")
    assert m_l_formal > 0.5
    # 绝对化扣分
    m_l_abs = client._estimate_logic_rigidity("这绝对是完美的")
    assert m_l_abs < 0.5


def test_estimate_heat_tax():
    client = MSSClient()
    gamma = client._estimate_heat_tax("这是一个简单的陈述")
    assert gamma >= 0
    # 矛盾信号增加热税
    gamma_contra = client._estimate_heat_tax("虽然A，但是B")
    assert gamma_contra > gamma


def test_mss_audit_decorator():
    @mss_audit()
    def generate_text():
        return "这是一个测试文本"
    
    result = generate_text()
    assert isinstance(result, str)
    assert hasattr(result, "_mss_audit")


def test_mss_anchor_decorator():
    @mss_anchor(level=AnchorLevel.OBJECTIVE)
    def make_claim():
        return "信息是宇宙的本体"
    
    result = make_claim()
    assert "[A1-A6公理框架内]" in result


def test_mss_anchor_actual():
    @mss_anchor(level=AnchorLevel.ACTUAL)
    def state_fact():
        return "地球绕太阳公转"
    
    result = state_fact()
    assert "[可验证]" in result


def test_anchor_savings():
    client = MSSClient()
    result = client.anchor("测试文本", AnchorLevel.OBJECTIVE)
    assert result.anchored is True
    assert result.heat_tax_after < result.heat_tax_before
    assert 0 <= result.savings <= 1


def test_to_markdown():
    result = AuditResult(
        passed=True,
        logic_rigidity=0.85,
        heat_tax=0.15,
        confidence=Confidence.HIGH,
        layer="L2",
        contradictions=[],
        suggestions=["建议补充形式化论证"],
    )
    md = result.to_markdown()
    assert "MSS逻辑审计报告" in md
    assert "0.8500" in md
    assert "建议补充形式化论证" in md


def test_config_validation():
    config = SDKConfig()
    assert config.validate() is True


def test_config_invalid_threshold():
    config = SDKConfig(logic_rigidity_threshold=1.5)
    try:
        config.validate()
        assert False, "应该抛出异常"
    except AssertionError:
        pass  # 预期行为


def main():
    """运行所有测试"""
    runner = TestRunner()
    
    print("="*50)
    print("MSS-Agent SDK v0.1 独立测试套件")
    print("="*50)
    
    # 核心客户端测试
    print("\n[TestMSSClient]")
    runner.run("test_client_init_default", test_client_init_default)
    runner.run("test_client_init_custom_config", test_client_init_custom_config)
    runner.run("test_local_audit_pass", test_local_audit_pass)
    runner.run("test_local_audit_forbidden_words", test_local_audit_forbidden_words)
    runner.run("test_estimate_logic_rigidity", test_estimate_logic_rigidity)
    runner.run("test_estimate_heat_tax", test_estimate_heat_tax)
    
    # 装饰器测试
    print("\n[TestDecorators]")
    runner.run("test_mss_audit_decorator", test_mss_audit_decorator)
    runner.run("test_mss_anchor_decorator", test_mss_anchor_decorator)
    runner.run("test_mss_anchor_actual", test_mss_anchor_actual)
    
    # 结果测试
    print("\n[TestAnchorResult]")
    runner.run("test_anchor_savings", test_anchor_savings)
    
    print("\n[TestAuditResult]")
    runner.run("test_to_markdown", test_to_markdown)
    
    # 配置测试
    print("\n[TestConfig]")
    runner.run("test_config_validation", test_config_validation)
    runner.run("test_config_invalid_threshold", test_config_invalid_threshold)
    
    # 摘要
    success = runner.summary()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
