# 符号推理引擎 v4.0 架构设计

## 设计目标

将现有符号引擎（symbolic_engine_v3.py）重构为生产级模块，支持：
- 模块化拆分（parser / reasoner / validator / exporter）
- 插件系统（动态规则加载）
- 缓存层（热点查询缓存）
- API接口（RESTful + WebSocket）

## 模块架构

```
symbolic_engine_v4/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── graph.py          # 图数据结构（CSR稀疏矩阵）
│   ├── node.py           # 节点定义
│   ├── edge.py           # 边定义
│   └── types.py          # 类型枚举
├── parser/
│   ├── __init__.py
│   ├── jsonl_parser.py   # JSONL知识库解析
│   ├── axiom_parser.py   # 公理解析
│   └── validation.py     # 输入验证
├── reasoner/
│   ├── __init__.py
│   ├── transitive.py     # 传递闭包推理
│   ├── cycle_detector.py # 循环检测
│   ├── path_finder.py    # 路径查找（A*算法）
│   └── heat_tax.py       # 热税计算
├── validator/
│   ├── __init__.py
│   ├── consistency.py    # 一致性检查
│   ├── completeness.py   # 完整性检查
│   └── omega_rules.py    # Ω级规则验证
├── exporter/
│   ├── __init__.py
│   ├── json_exporter.py  # JSON输出
│   ├── markdown.py       # Markdown报告
│   └── graphviz.py       # 图可视化
├── plugins/
│   ├── __init__.py
│   ├── base.py           # 插件基类
│   └── loader.py         # 插件加载器
├── cache/
│   ├── __init__.py
│   ├── lru_cache.py      # LRU缓存
│   └── redis_cache.py    # Redis缓存（可选）
└── api/
    ├── __init__.py
    ├── rest.py           # RESTful API
    ├── websocket.py      # WebSocket流
    └── schemas.py        # Pydantic模型
```

## 核心改进

### 1. 图数据结构优化

```python
# v3: 邻接表
class ConceptGraph:
    def __init__(self):
        self.nodes = {}  # dict
        self.edges = []  # list

# v4: CSR稀疏矩阵
class CSRGraph:
    def __init__(self):
        self.indptr = []   # 行指针
        self.indices = []  # 列索引
        self.data = []     # 边数据
        self.node_map = {} # 节点映射
```

**性能提升**:
- 内存占用减少60%
- 遍历速度提升3x
- 支持百万级节点

### 2. 推理算法优化

```python
# v3: Dijkstra
class TransitiveReasoner:
    def find_path(self, start, end):
        return dijkstra(self.graph, start, end)

# v4: A*启发式搜索
class AStarReasoner:
    def find_path(self, start, end):
        heuristic = self._layer_heuristic(end)
        return a_star(self.graph, start, end, heuristic)
```

**性能提升**:
- 平均搜索深度减少40%
- 大规模图查询<100ms

### 3. 插件系统

```python
class MSSPlugin(ABC):
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def process(self, graph: ConceptGraph) -> PluginResult:
        pass

# 示例：自定义规则插件
class CustomRulePlugin(MSSPlugin):
    def name(self):
        return "custom_rules"
    
    def process(self, graph):
        # 加载自定义规则
        rules = self.load_rules()
        violations = []
        for rule in rules:
            if not rule.check(graph):
                violations.append(rule.violation)
        return PluginResult(violations=violations)
```

### 4. 缓存层

```python
class QueryCache:
    def __init__(self, backend="lru", maxsize=10000):
        if backend == "lru":
            self.cache = LRUCache(maxsize)
        elif backend == "redis":
            self.cache = RedisCache()
    
    def get(self, query_hash):
        return self.cache.get(query_hash)
    
    def set(self, query_hash, result, ttl=3600):
        self.cache.set(query_hash, result, ttl)
```

## API设计

### RESTful API

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AnalyzeRequest(BaseModel):
    knowledge_base: str
    query: str
    options: Optional[Dict]

class AnalyzeResponse(BaseModel):
    result: Dict
    confidence: float
    execution_time: float

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    engine = SymbolicEngineV4()
    result = await engine.analyze(request.knowledge_base, request.query)
    return AnalyzeResponse(
        result=result,
        confidence=result.confidence,
        execution_time=result.time
    )

@app.post("/validate")
async def validate(request: ValidateRequest):
    validator = OmegaValidator()
    result = validator.validate(request.axioms)
    return ValidateResponse(
        valid=result.valid,
        violations=result.violations
    )
```

### WebSocket流

```python
@app.websocket("/ws/reasoning")
async def reasoning_stream(websocket: WebSocket):
    await websocket.accept()
    
    engine = SymbolicEngineV4()
    
    async for message in websocket.iter_text():
        query = json.loads(message)
        
        # 流式返回推理步骤
        async for step in engine.reason_stream(query):
            await websocket.send_json({
                "step": step.number,
                "type": step.type,
                "content": step.content,
                "confidence": step.confidence
            })
```

## 性能目标

| 指标 | v3现状 | v4目标 | 提升 |
|------|--------|--------|------|
| 查询延迟 | 500ms | <100ms | 5x |
| 内存占用 | 500MB | <200MB | 2.5x |
| 并发QPS | 10 | 1000 | 100x |
| 可用性 | 99% | 99.9% | - |
| 准确率 | 85% | >95% | 10% |

## 实施计划

### Week 1: 架构搭建
- [ ] 创建模块目录结构
- [ ] 实现核心图数据结构（CSR）
- [ ] 实现基础解析器

### Week 2: 推理引擎
- [ ] 实现A*路径查找
- [ ] 实现传递闭包优化
- [ ] 实现热税计算

### Week 3: 验证与插件
- [ ] 实现Ω级规则验证
- [ ] 实现插件系统
- [ ] 实现缓存层

### Week 4: API与测试
- [ ] 实现RESTful API
- [ ] 实现WebSocket流
- [ ] 端到端测试

## 文件路径

```
C:\MSS-AI-Project\symbolic_engine_v4\
```
