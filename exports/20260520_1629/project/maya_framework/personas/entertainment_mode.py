"""
Entertainment Mode (娱乐家)
C-end product persona - K4 meaning embedded in engaging content
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import random

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode


@dataclass
class ContentContext:
    """Context for content generation"""
    platform: str  # wechat, douyin, xiaohongshu, bilibili
    content_type: str  # article, video_script, meme, story
    target_audience: str  # general, tech, business, youth
    topic: str
    engagement_goal: float = 0.7  # 0-1, target engagement rate
    k4_depth: float = 0.3  # 0-1, how deep K4 concepts are embedded


class EntertainmentMode:
    """
    Entertainment persona for C-end content creation.
    
    Core strategy: Embed K4 meaning structures in entertaining content.
    Like hiding medicine in candy - the audience enjoys the content
    while subconsciously absorbing K4 concepts.
    """
    
    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self._content_history: List[Dict[str, Any]] = []
        self._engagement_metrics: Dict[str, float] = {}
    
    def create_content(self, context: ContentContext) -> Dict[str, Any]:
        """
        Create entertaining content with embedded K4 meaning.
        
        Args:
            context: Content generation context
            
        Returns:
            Content package with metadata
        """
        # Select content template based on platform and type
        template = self._select_template(context)
        
        # Generate K4-embedded content
        content = self._generate_with_embedding(context, template)
        
        # Add engagement hooks
        content_with_hooks = self._add_engagement_hooks(content, context.platform)
        
        # Track
        content_id = f"CONTENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._content_history.append({
            'content_id': content_id,
            'context': context,
            'template': template,
            'k4_depth': context.k4_depth,
        })
        
        return {
            'content_id': content_id,
            'content': content_with_hooks,
            'platform': context.platform,
            'estimated_engagement': self._estimate_engagement(context),
            'k4_concepts_embedded': self._count_k4_concepts(content),
        }
    
    def _select_template(self, context: ContentContext) -> str:
        """Select content template based on context"""
        templates = {
            ('wechat', 'article'): 'long_form_storytelling',
            ('douyin', 'video_script'): 'short_punchy_hook',
            ('xiaohongshu', 'article'): 'lifestyle_aesthetic',
            ('bilibili', 'video_script'): 'edutainment_deep_dive',
        }
        return templates.get(
            (context.platform, context.content_type),
            'generic_engaging'
        )
    
    def _generate_with_embedding(self, context: ContentContext, 
                                  template: str) -> str:
        """Generate content with K4 concepts embedded"""
        # K4 concepts to embed based on depth
        k4_concepts = self._select_k4_concepts(context.k4_depth)
        
        # Translate to audience-appropriate language
        audience_concepts = [
            self._translate_for_audience(concept, context.target_audience)
            for concept in k4_concepts
        ]
        
        prompt = f"""
        Create {context.content_type} content about "{context.topic}" for {context.platform}.
        Template: {template}
        Audience: {context.target_audience}
        
        Subtly weave in these concepts:
        {chr(10).join(f"- {concept}" for concept in audience_concepts)}
        
        Requirements:
        - Engaging and entertaining first
        - Educational second
        - Never preachy or obvious
        - Use storytelling and examples
        """
        
        config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.8,
        )
        
        return self.backend.generate(prompt, config)
    
    def _select_k4_concepts(self, depth: float) -> List[str]:
        """Select K4 concepts based on embedding depth"""
        all_concepts = [
            "thermal tax",
            "meaning structure",
            "distributed networks",
            "entropy and order",
            "phase transitions",
            "resonance and harmony",
            "catalysis and acceleration",
        ]
        
        num_concepts = max(1, int(len(all_concepts) * depth))
        return random.sample(all_concepts, num_concepts)
    
    def _translate_for_audience(self, concept: str, audience: str) -> str:
        """Translate K4 concept for target audience"""
        translations = {
            "general": {
                "thermal tax": "the hidden costs of rushing",
                "meaning structure": "what really matters",
                "distributed networks": "working together without central control",
            },
            "tech": {
                "thermal tax": "technical debt and system friction",
                "meaning structure": "data architecture and information flow",
                "distributed networks": "decentralized systems and peer-to-peer",
            },
            "business": {
                "thermal tax": "operational inefficiency and hidden costs",
                "meaning structure": "strategic value alignment",
                "distributed networks": "flat organizational structures",
            },
            "youth": {
                "thermal tax": "the burnout from always being 'on'",
                "meaning structure": "finding your purpose",
                "distributed networks": "community-driven movements",
            },
        }
        
        audience_dict = translations.get(audience, translations["general"])
        return audience_dict.get(concept, concept)
    
    def _add_engagement_hooks(self, content: str, platform: str) -> str:
        """Add platform-specific engagement hooks"""
        hooks = {
            'wechat': "\n\n💡 思考：如果...会怎样？留言告诉我你的想法",
            'douyin': "\n\n🔥 双击收藏，下期揭秘背后的真相",
            'xiaohongshu': "\n\n✨ 收藏这篇，下次遇到类似情况就知道怎么办了",
            'bilibili': "\n\n📺 点赞三连，解锁更多深度内容",
        }
        
        return content + hooks.get(platform, "")
    
    def _estimate_engagement(self, context: ContentContext) -> float:
        """Estimate engagement rate based on context"""
        base_rate = 0.05  # 5% base
        platform_multiplier = {
            'douyin': 2.0,
            'xiaohongshu': 1.5,
            'bilibili': 1.3,
            'wechat': 1.0,
        }
        
        return min(
            base_rate * platform_multiplier.get(context.platform, 1.0) * 
            (1 + context.engagement_goal),
            0.5  # Cap at 50%
        )
    
    def _count_k4_concepts(self, content: str) -> int:
        """Count embedded K4 concepts (including translated forms)"""
        k4_indicators = [
            # Direct K4 terms
            "thermal", "entropy", "distributed", "resonance", 
            "phase", "catalysis", "meaning structure",
            # Translated forms that indicate embedding
            "hidden costs", "friction", "decentralized", "synergy",
            "paradigm", "acceleration", "alignment", "purpose",
            "community", "burnout", "debt", "architecture",
        ]
        return sum(1 for indicator in k4_indicators 
                  if indicator in content.lower())
    
    def get_content_performance(self) -> Dict[str, Any]:
        """Get content performance summary"""
        return {
            'total_content': len(self._content_history),
            'avg_k4_depth': sum(
                c['k4_depth'] for c in self._content_history
            ) / max(len(self._content_history), 1),
            'platforms_used': list(set(
                c['context'].platform for c in self._content_history
            )),
        }
