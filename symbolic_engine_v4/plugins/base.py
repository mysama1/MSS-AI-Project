"""
MSS Symbolic Engine v4.0 - Plugin System
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..core import ConceptNode, ConceptEdge, QueryResult

class Plugin(ABC):
    """Base class for symbolic engine plugins"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.enabled = True
        self.config: Dict[str, Any] = {}
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration"""
        pass
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process data through plugin"""
        pass
    
    def shutdown(self):
        """Cleanup plugin resources"""
        pass

class ValidationPlugin(Plugin):
    """Plugin for custom validation rules"""
    
    def __init__(self):
        super().__init__("validation", "1.0.0")
        self.rules: List[Dict] = []
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        self.rules = config.get("rules", [])
        return True
    
    def process(self, node: ConceptNode) -> Dict[str, Any]:
        """Validate node against custom rules"""
        violations = []
        
        for rule in self.rules:
            if rule["type"] == "length":
                min_len = rule.get("min", 0)
                if len(node.content) < min_len:
                    violations.append(f"Content too short: {len(node.content)} < {min_len}")
            
            elif rule["type"] == "required_fields":
                fields = rule.get("fields", [])
                for field in fields:
                    if not getattr(node, field, None):
                        violations.append(f"Missing required field: {field}")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }

class EnrichmentPlugin(Plugin):
    """Plugin for enriching node metadata"""
    
    def __init__(self):
        super().__init__("enrichment", "1.0.0")
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        return True
    
    def process(self, node: ConceptNode) -> ConceptNode:
        """Enrich node with additional metadata"""
        # Add word count
        node.metadata["word_count"] = len(node.content.split())
        
        # Add content hash
        import hashlib
        node.metadata["content_hash"] = hashlib.md5(
            node.content.encode()).hexdigest()[:8]
        
        return node

class PluginManager:
    """Manager for symbolic engine plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[str]] = {
            "pre_process": [],
            "post_process": [],
            "validation": [],
            "enrichment": []
        }
    
    def register(self, plugin: Plugin) -> bool:
        """Register a plugin"""
        if plugin.name in self.plugins:
            return False
        
        self.plugins[plugin.name] = plugin
        
        # Auto-register hooks based on plugin type
        if isinstance(plugin, ValidationPlugin):
            self.hooks["validation"].append(plugin.name)
        elif isinstance(plugin, EnrichmentPlugin):
            self.hooks["enrichment"].append(plugin.name)
        
        return True
    
    def unregister(self, name: str) -> bool:
        """Unregister a plugin"""
        if name not in self.plugins:
            return False
        
        del self.plugins[name]
        
        # Remove from hooks
        for hook_list in self.hooks.values():
            if name in hook_list:
                hook_list.remove(name)
        
        return True
    
    def execute_hook(self, hook_name: str, data: Any) -> Any:
        """Execute all plugins for a hook"""
        result = data
        
        for plugin_name in self.hooks.get(hook_name, []):
            plugin = self.plugins.get(plugin_name)
            if plugin and plugin.enabled:
                try:
                    result = plugin.process(result)
                except Exception as e:
                    print(f"Plugin {plugin_name} error: {e}")
        
        return result
    
    def get_plugin_info(self) -> Dict[str, Dict]:
        """Get information about all plugins"""
        return {
            name: {
                "version": plugin.version,
                "enabled": plugin.enabled
            }
            for name, plugin in self.plugins.items()
        }
