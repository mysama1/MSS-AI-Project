"""
MSS-Agent SDK 测试套件
"""
import pytest
from mss_agent_sdk import MSSClient, mss_audit, mss_anchor
from mss_agent_sdk.types import AnchorLevel, Confidence, AuditResult
from mss_agent_sdk.config import SDKConfig


class TestMSSClient:
    """测试核心客户端"""
    
    def test_client_init_default(self):
        client = MSSClient()
        assert client.config is not None
        assert client.config.logic_rigidity_threshold == 0.6
    
    def test_client_init_custom_config(self):
        config = SDKConfig(logic_rigidity_threshold=0.8)
        client = MSSClient(config)
        assert client.config.logic_rigidity_threshold == 0.8
    
    def test_local_audit_pass(self):
        client = MSSClient()
        result = client.audit("这是一个正常的陈述，没有绝对化表述。")
        assert isinstance(result, AuditResult)
        assert result.layer in ["L1", "L2", "L3", "L4"]
    
    def test_local_audit_forbidden_words(self):
        client = MSSClient()
        result = client.audit("这是终极真理，完美无缺。")
        assert not result.passed
        assert len(result.contradictions) > 0
        assert any("终极" in c for c in result.contradictions)
    
    def test_estimate_logic_rigidity(self):
        client = MSSClient()
        # 形式化表述加分
        m_l_formal = client._estimate_logic_rigidity("∀x ∈ S, P(x) ⇒ Q(x)")
        assert m_l_formal > 0.5
        # 绝对化扣分
        m_l_abs = client._estimate_logic_rigidity("这绝对是完美的")
        assert m_l_abs < 0.5
    
    def test_estimate_heat_tax(self):
        client = MSSClient()
        gamma = client._estimate_heat_tax("这是一个简单的陈述")
        assert gamma >= 0
        # 矛盾信号增加热税
        gamma_contra = client._estimate_heat_tax("虽然A，但是B")
        assert gamma_contra > gamma


class TestDecorators:
    """测试装饰器"""
    
    def test_mss_audit_decorator(self):
        @mss_audit()
        def generate_text():
            return "这是一个测试文本"
        
        result = generate_text()
        assert isinstance(result, str)
        assert hasattr(result, "_mss_audit")
    
    def test_mss_anchor_decorator(self):
        @mss_anchor(level=AnchorLevel.OBJECTIVE)
        def make_claim():
            return "信息是宇宙的本体"
        
        result = make_claim()
        assert "[A1-A6公理框架内]" in result
    
    def test_mss_anchor_actual(self):
        @mss_anchor(level=AnchorLevel.ACTUAL)
        def state_fact():
            return "地球绕太阳公转"
        
        result = state_fact()
        assert "[可验证]" in result


class TestAnchorResult:
    """测试锚定结果"""
    
    def test_anchor_savings(self):
        client = MSSClient()
        result = client.anchor("测试文本", AnchorLevel.OBJECTIVE)
        assert result.anchored is True
        assert result.heat_tax_after < result.heat_tax_before
        assert 0 <= result.savings <= 1


class TestAuditResult:
    """测试审计结果"""
    
    def test_to_markdown(self):
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


class TestConfig:
    """测试配置"""
    
    def test_config_validation(self):
        config = SDKConfig()
        assert config.validate() is True
    
    def test_config_invalid_threshold(self):
        config = SDKConfig(logic_rigidity_threshold=1.5)
        with pytest.raises(AssertionError):
            config.validate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
