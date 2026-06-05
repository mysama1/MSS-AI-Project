"""
MSS-AI 记忆层集成模块 v1.0
基于 mem0 的智能记忆层，为 MSS-AI 提供长期记忆能力

功能：
1. 用户分析历史持久化存储
2. 概念网络实体链接
3. 跨会话上下文保持
4. 时间感知检索

作者：QClaw
日期：2026-05-20
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import hashlib

# 尝试导入 mem0，如果未安装则提供降级方案
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    print("警告：mem0 未安装，使用内存降级方案")
    print("安装命令：pip install mem0ai")

# ============================================================
# 数据模型
# ============================================================

@dataclass
class MSSAnalysisResult:
    """MSS分析结果数据结构"""
    user_id: str
    timestamp: str
    system_dimension: float      # D: 系统维度
    logic_entropy: float         # S_logic: 逻辑熵
    heat_tax: float             # γ: 热税系数
    meaning_flux: float         # Φ: 意义通量
    total_information: float     # K: 总信息
    organization_degree: float   # Od: 组织度
    resilience_index: float      # M: 韧性指数
    analysis_type: str          # 分析类型：organization / text / system
    raw_data: Dict[str, Any]    # 原始分析数据
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MSSAnalysisResult':
        return cls(**data)

@dataclass
class UserMSSProfile:
    """用户MSS画像"""
    user_id: str
    created_at: str
    last_analysis: str
    total_analyses: int
    average_dimension: float
    average_heat_tax: float
    trend: str  # improving / stable / declining
    key_entities: List[str]  # 关联实体
    
# ============================================================
# 记忆层核心类
# ============================================================

class MSSMemoryLayer:
    """
    MSS-AI 记忆层
    
    封装 mem0 的记忆功能，提供 MSS 特定的记忆操作
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化记忆层
        
        Args:
            config: mem0 配置字典，可选
        """
        self.config = config or {}
        
        if MEM0_AVAILABLE:
            self.memory = Memory(**self.config)
            self.backend = "mem0"
        else:
            # 降级方案：内存存储
            self._memory_store: Dict[str, List[Dict]] = {}
            self.backend = "memory"
        
        print(f"MSS记忆层初始化完成，后端：{self.backend}")
    
    # ============================================================
    # 核心存储方法
    # ============================================================
    
    def store_analysis(self, result: MSSAnalysisResult, 
                      context: Optional[str] = None) -> bool:
        """
        存储MSS分析结果到记忆层
        
        Args:
            result: MSS分析结果
            context: 额外上下文信息
            
        Returns:
            存储是否成功
        """
        try:
            # 构建记忆内容
            memory_content = self._build_analysis_memory(result, context)
            
            # 构建元数据
            metadata = {
                "type": "mss_analysis",
                "analysis_type": result.analysis_type,
                "timestamp": result.timestamp,
                "heat_tax_range": self._categorize_heat_tax(result.heat_tax),
                "dimension_range": self._categorize_dimension(result.system_dimension),
            }
            
            if self.backend == "mem0":
                # 使用 mem0 存储
                self.memory.add(
                    memory_content,
                    user_id=result.user_id,
                    metadata=metadata
                )
            else:
                # 降级方案
                self._store_in_memory(result.user_id, memory_content, metadata)
            
            return True
            
        except Exception as e:
            print(f"存储分析结果失败：{e}")
            return False
    
    def store_concept(self, user_id: str, concept: str, 
                     concept_type: str, relationships: List[str] = None) -> bool:
        """
        存储MSS概念到记忆层
        
        Args:
            user_id: 用户ID
            concept: 概念名称
            concept_type: 概念类型（axiom/definition/theorem/entity）
            relationships: 关联概念列表
            
        Returns:
            存储是否成功
        """
        try:
            content = f"MSS概念：{concept}（类型：{concept_type}）"
            if relationships:
                content += f"，关联：{', '.join(relationships)}"
            
            metadata = {
                "type": "mss_concept",
                "concept_type": concept_type,
                "relationships": relationships or [],
            }
            
            if self.backend == "mem0":
                self.memory.add(content, user_id=user_id, metadata=metadata)
            else:
                self._store_in_memory(user_id, content, metadata)
            
            return True
            
        except Exception as e:
            print(f"存储概念失败：{e}")
            return False
    
    def store_interaction(self, user_id: str, query: str, 
                         response: str, interaction_type: str = "general") -> bool:
        """
        存储用户交互历史
        
        Args:
            user_id: 用户ID
            query: 用户查询
            response: 系统响应
            interaction_type: 交互类型
            
        Returns:
            存储是否成功
        """
        try:
            content = f"用户询问：{query}\n系统回答：{response}"
            metadata = {
                "type": "interaction",
                "interaction_type": interaction_type,
                "timestamp": datetime.now().isoformat(),
            }
            
            if self.backend == "mem0":
                self.memory.add(content, user_id=user_id, metadata=metadata)
            else:
                self._store_in_memory(user_id, content, metadata)
            
            return True
            
        except Exception as e:
            print(f"存储交互失败：{e}")
            return False
    
    # ============================================================
    # 核心检索方法
    # ============================================================
    
    def retrieve_analysis_history(self, user_id: str, 
                                 limit: int = 10) -> List[Dict]:
        """
        检索用户分析历史
        
        Args:
            user_id: 用户ID
            limit: 返回结果数量
            
        Returns:
            分析历史列表
        """
        try:
            if self.backend == "mem0":
                results = self.memory.search(
                    "MSS分析结果",
                    user_id=user_id,
                    limit=limit
                )
                return self._filter_by_type(results, "mss_analysis")
            else:
                return self._retrieve_from_memory(user_id, "mss_analysis", limit)
                
        except Exception as e:
            print(f"检索分析历史失败：{e}")
            return []
    
    def retrieve_concepts(self, user_id: str, 
                         concept_type: Optional[str] = None) -> List[Dict]:
        """
        检索用户相关的MSS概念
        
        Args:
            user_id: 用户ID
            concept_type: 概念类型过滤
            
        Returns:
            概念列表
        """
        try:
            if self.backend == "mem0":
                results = self.memory.search(
                    "MSS概念",
                    user_id=user_id,
                    limit=50
                )
                concepts = self._filter_by_type(results, "mss_concept")
                
                if concept_type:
                    concepts = [c for c in concepts 
                              if c.get("metadata", {}).get("concept_type") == concept_type]
                
                return concepts
            else:
                concepts = self._retrieve_from_memory(user_id, "mss_concept", 50)
                if concept_type:
                    concepts = [c for c in concepts 
                              if c.get("metadata", {}).get("concept_type") == concept_type]
                return concepts
                
        except Exception as e:
            print(f"检索概念失败：{e}")
            return []
    
    def retrieve_relevant_context(self, user_id: str, 
                                 query: str, limit: int = 5) -> str:
        """
        检索与查询相关的上下文
        
        Args:
            user_id: 用户ID
            query: 查询内容
            limit: 返回结果数量
            
        Returns:
            格式化的上下文字符串
        """
        try:
            if self.backend == "mem0":
                results = self.memory.search(query, user_id=user_id, limit=limit)
            else:
                results = self._search_memory(user_id, query, limit)
            
            # 格式化上下文
            context_parts = []
            for i, result in enumerate(results, 1):
                content = result.get("memory", result.get("content", ""))
                context_parts.append(f"[历史记录 {i}]\n{content}")
            
            return "\n\n".join(context_parts) if context_parts else "无相关历史记录"
            
        except Exception as e:
            print(f"检索上下文失败：{e}")
            return ""
    
    def get_user_profile(self, user_id: str) -> Optional[UserMSSProfile]:
        """
        获取用户MSS画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户画像，如果没有则返回None
        """
        try:
            history = self.retrieve_analysis_history(user_id, limit=100)
            
            if not history:
                return None
            
            # 计算统计信息
            total = len(history)
            avg_dimension = sum(h.get("metadata", {}).get("system_dimension", 0) 
                              for h in history) / total
            avg_heat_tax = sum(h.get("metadata", {}).get("heat_tax", 0) 
                             for h in history) / total
            
            # 判断趋势
            if total >= 2:
                recent = history[-1].get("metadata", {}).get("heat_tax", 0)
                previous = history[-2].get("metadata", {}).get("heat_tax", 0)
                if recent < previous:
                    trend = "improving"
                elif recent > previous:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"
            
            # 提取关键实体
            concepts = self.retrieve_concepts(user_id)
            key_entities = [c.get("memory", "").split("：")[1].split("（")[0] 
                          for c in concepts if "：" in c.get("memory", "")]
            
            return UserMSSProfile(
                user_id=user_id,
                created_at=history[0].get("metadata", {}).get("timestamp", ""),
                last_analysis=history[-1].get("metadata", {}).get("timestamp", ""),
                total_analyses=total,
                average_dimension=avg_dimension,
                average_heat_tax=avg_heat_tax,
                trend=trend,
                key_entities=list(set(key_entities))[:10]  # 去重，最多10个
            )
            
        except Exception as e:
            print(f"获取用户画像失败：{e}")
            return None
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    def _build_analysis_memory(self, result: MSSAnalysisResult, 
                              context: Optional[str]) -> str:
        """构建分析结果的记忆内容"""
        parts = [
            f"MSS分析结果（{result.analysis_type}）",
            f"系统维度 D = {result.system_dimension}",
            f"逻辑熵 S_logic = {result.logic_entropy}",
            f"热税系数 γ = {result.heat_tax}",
            f"意义通量 Φ = {result.meaning_flux}",
            f"组织度 Od = {result.organization_degree}",
            f"韧性指数 M = {result.resilience_index}",
        ]
        
        if context:
            parts.append(f"上下文：{context}")
        
        return "\n".join(parts)
    
    def _categorize_heat_tax(self, gamma: float) -> str:
        """热税分类"""
        if gamma < 0.2:
            return "low"
        elif gamma < 0.5:
            return "medium"
        elif gamma < 0.8:
            return "high"
        else:
            return "critical"
    
    def _categorize_dimension(self, dimension: float) -> str:
        """维度分类"""
        if dimension < 10:
            return "small"
        elif dimension < 50:
            return "medium"
        elif dimension < 200:
            return "large"
        else:
            return "enterprise"
    
    def _filter_by_type(self, results: List[Dict], 
                       mem_type: str) -> List[Dict]:
        """按类型过滤记忆结果"""
        return [r for r in results 
                if r.get("metadata", {}).get("type") == mem_type]
    
    # ============================================================
    # 降级方案：内存存储
    # ============================================================
    
    def _store_in_memory(self, user_id: str, content: str, 
                        metadata: Dict) -> None:
        """内存存储实现"""
        if user_id not in self._memory_store:
            self._memory_store[user_id] = []
        
        self._memory_store[user_id].append({
            "memory": content,
            "metadata": metadata,
            "id": hashlib.md5(f"{user_id}:{content}:{datetime.now()}".encode()).hexdigest()
        })
    
    def _retrieve_from_memory(self, user_id: str, 
                             mem_type: str, limit: int) -> List[Dict]:
        """内存检索实现"""
        if user_id not in self._memory_store:
            return []
        
        results = [m for m in self._memory_store[user_id]
                  if m.get("metadata", {}).get("type") == mem_type]
        
        # 按时间倒序
        results.sort(key=lambda x: x.get("metadata", {}).get("timestamp", ""), 
                    reverse=True)
        
        return results[:limit]
    
    def _search_memory(self, user_id: str, query: str, 
                      limit: int) -> List[Dict]:
        """简单关键词搜索"""
        if user_id not in self._memory_store:
            return []
        
        query_lower = query.lower()
        results = []
        
        for mem in self._memory_store[user_id]:
            content = mem.get("memory", "").lower()
            if any(word in content for word in query_lower.split()):
                results.append(mem)
        
        return results[:limit]

# ============================================================
# 便捷函数
# ============================================================

def create_memory_layer(config: Optional[Dict] = None) -> MSSMemoryLayer:
    """创建记忆层实例的便捷函数"""
    return MSSMemoryLayer(config)

# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MSS-AI 记忆层测试")
    print("=" * 60)
    
    # 创建记忆层
    memory = create_memory_layer()
    
    # 测试用户
    test_user = "test_user_001"
    
    # 1. 存储分析结果
    print("\n[测试1] 存储分析结果")
    result = MSSAnalysisResult(
        user_id=test_user,
        timestamp=datetime.now().isoformat(),
        system_dimension=25.0,
        logic_entropy=80.0,
        heat_tax=0.35,
        meaning_flux=6.0,
        total_information=500.0,
        organization_degree=0.6,
        resilience_index=0.4,
        analysis_type="organization",
        raw_data={"departments": 5, "employees": 50}
    )
    
    success = memory.store_analysis(result, "季度组织韧性扫描")
    print(f"存储结果：{'成功' if success else '失败'}")
    
    # 2. 存储概念
    print("\n[测试2] 存储概念")
    memory.store_concept(
        test_user,
        "逻辑熵增",
        "axiom",
        ["热税", "意义通量", "道枢系统"]
    )
    memory.store_concept(
        test_user,
        "热税",
        "definition",
        ["逻辑熵增", "协调成本"]
    )
    print("概念存储完成")
    
    # 3. 存储交互
    print("\n[测试3] 存储交互")
    memory.store_interaction(
        test_user,
        "我们公司是不是快热寂了？",
        "根据分析，您的组织热税系数γ=0.35，处于亚健康状态...",
        "consultation"
    )
    print("交互存储完成")
    
    # 4. 检索分析历史
    print("\n[测试4] 检索分析历史")
    history = memory.retrieve_analysis_history(test_user)
    print(f"找到 {len(history)} 条历史记录")
    for h in history[:3]:
        print(f"  - {h.get('memory', '')[:50]}...")
    
    # 5. 检索概念
    print("\n[测试5] 检索概念")
    concepts = memory.retrieve_concepts(test_user, "axiom")
    print(f"找到 {len(concepts)} 个公理概念")
    for c in concepts:
        print(f"  - {c.get('memory', '')}")
    
    # 6. 检索上下文
    print("\n[测试6] 检索上下文")
    context = memory.retrieve_relevant_context(test_user, "热税系数")
    print(f"相关上下文：\n{context[:200]}...")
    
    # 7. 获取用户画像
    print("\n[测试7] 获取用户画像")
    profile = memory.get_user_profile(test_user)
    if profile:
        print(f"用户：{profile.user_id}")
        print(f"分析次数：{profile.total_analyses}")
        print(f"平均维度：{profile.average_dimension:.2f}")
        print(f"平均热税：{profile.average_heat_tax:.2f}")
        print(f"趋势：{profile.trend}")
        print(f"关键实体：{', '.join(profile.key_entities)}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
