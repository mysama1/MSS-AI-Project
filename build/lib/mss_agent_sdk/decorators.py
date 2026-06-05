"""
MSS-Agent SDK 装饰器
提供零侵入的审计和锚定功能
"""
import functools
from typing import Optional, Callable, Any

from .client import MSSClient
from .mss_types import AuditResult, AnchorResult, AnchorLevel

# 全局客户端实例（延迟初始化）
_default_client: Optional[MSSClient] = None

def _get_client() -> MSSClient:
    """获取默认客户端"""
    global _default_client
    if _default_client is None:
        _default_client = MSSClient()
    return _default_client


def mss_audit(
    context: Optional[str] = None,
    auto_print: bool = False,
    raise_on_fail: bool = False,
):
    """逻辑审计装饰器
    
    用法：
        @mss_audit()
        def my_function():
            return "some text"
    
    对函数返回值进行MSS逻辑审计
    
    Args:
        context: 审计上下文
        auto_print: 是否自动打印审计报告
        raise_on_fail: 审计未通过时是否抛出异常
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)
            
            # 只对字符串返回值审计
            if not isinstance(result, str):
                return result
            
            client = _get_client()
            audit_result = client.audit(result, context)
            
            if auto_print:
                print(audit_result.to_markdown())
            
            if raise_on_fail and not audit_result.passed:
                raise MSSAuditError(
                    f"逻辑审计未通过: M_L={audit_result.logic_rigidity:.3f}, "
                    f"γ={audit_result.heat_tax:.3f}"
                )
            
            # 将审计结果附加到返回值（通过包装类）
            class MSSString(str):
                pass
            wrapped = MSSString(result)
            wrapped._mss_audit = audit_result
            return wrapped
        
        return wrapper
    return decorator


def mss_anchor(
    level: AnchorLevel = AnchorLevel.ACTUAL,
    auto_append: bool = True,
):
    """意义锚定装饰器
    
    用法：
        @mss_anchor(level=AnchorLevel.OBJECTIVE)
        def generate_text():
            return "some claim"
    
    对函数返回值进行三层意义锚定
    
    Args:
        level: 锚定层级
        auto_append: 是否自动附加锚定标记到文本
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)
            
            if not isinstance(result, str):
                return result
            
            client = _get_client()
            anchor_result = client.anchor(result, level)
            
            if auto_append:
                return anchor_result.text
            
            # 将锚定结果附加到返回值（通过包装类）
            class MSSString(str):
                pass
            wrapped = MSSString(result)
            wrapped._mss_anchor = anchor_result
            return wrapped
        
        return wrapper
    return decorator


class MSSAuditError(Exception):
    """审计未通过异常"""
    pass


# 上下文管理器版本
class MSSAuditContext:
    """审计上下文管理器
    
    用法：
        with MSSAuditContext() as ctx:
            text = generate_some_text()
            result = ctx.audit(text)
            print(result.to_markdown())
    """
    
    def __init__(self, config=None):
        self.client = MSSClient(config)
        self.results = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def audit(self, text: str, context: Optional[str] = None) -> AuditResult:
        """审计文本"""
        result = self.client.audit(text, context)
        self.results.append(result)
        return result
    
    def anchor(self, text: str, level: AnchorLevel = AnchorLevel.ACTUAL) -> AnchorResult:
        """锚定文本"""
        return self.client.anchor(text, level)
    
    def summary(self) -> str:
        """生成审计摘要"""
        if not self.results:
            return "无审计记录"
        
        passed = sum(1 for r in self.results if r.passed)
        avg_m_l = sum(r.logic_rigidity for r in self.results) / len(self.results)
        avg_gamma = sum(r.heat_tax for r in self.results) / len(self.results)
        
        return f"""## MSS审计摘要
- 总审计数: {len(self.results)}
- 通过: {passed} / {len(self.results)}
- 平均逻辑刚性 M_L: {avg_m_l:.3f}
- 平均热税 γ: {avg_gamma:.3f}
"""
