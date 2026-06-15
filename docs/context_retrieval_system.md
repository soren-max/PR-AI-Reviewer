# Code Context Retrieval System — 设计文档

> Author: Principal Engineer  
> Status: Draft v1  
> Timeline: 3 Sprints

---

## 1. 问题域分析

### 现状

当前 Review 只分析 **Diff 本身的变更**：

```
diff --git a/src/auth/login.py b/src/auth/login.py
@@ -42,6 +42,8 @@ def login():
```

→ AI 只看到 `login()` 函数中新增了 2 行代码。

### 问题

```
变更: 删除 check_session() 调用
影响: 所有调用 login() 的上层函数
         login() 依赖的 UserService
         相关的测试文件
         相关的 API 文档
```

没有上下文，Review 无法判断变更的**影响范围**。

### 目标

```
Diff 一行变更 → 系统自动检索:

  直接影响:
    ├─ 本文件: login() 函数
    ├─ 调用者: auth_controller.py::handle_login()
    │           middleware.py::authenticate()
    └─ 被调用者: user_service.py::validate_credentials()
                 session.py::create_session()

  间接影响:
    ├─ 测试文件: tests/test_auth.py
    ├─ 接口文档: docs/api/auth.md
    └─ 配置影响: config/auth.py
```

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Review Pipeline                               │
│                                                                       │
│  Diff  →  DiffParser  →  ContextRetriever  →  PromptBuilder  →  LLM  │
│                              │                                        │
│                              ▼                                        │
│                    Code Context Retrieval System                       │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    ContextRetriever                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │   │
│  │  │ Function │  │  Class   │  │  File    │  │  Doc         │ │   │
│  │  │ Finder   │  │  Finder  │  │  Finder  │  │  Finder      │ │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │   │
│  └───────┼──────────────┼─────────────┼───────────────┼─────────┘   │
│          │              │             │               │              │
│          ▼              ▼             ▼               ▼              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Index Layer                                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │   │
│  │  │ Symbol   │  │ Call     │  │ Import   │  │ Doc          │ │   │
│  │  │ Table    │  │ Graph    │  │ Graph    │  │ Index        │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Static Analyzer                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │   │
│  │  │ Python   │  │   AST    │  │  Import  │  │  Docstring   │ │   │
│  │  │ Parser   │  │ Resolver │  │ Scanner  │  │  Extractor   │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Storage Layer                                │   │
│  │  ┌──────────┐  ┌────────────────┐  ┌──────────────────────┐  │   │
│  │  │ SQLite   │  │ GitHub Blob    │  │ In-Memory LRU       │  │   │
│  │  │ (Persist)│  │ Cache (Redis)  │  │ Cache (dict)        │  │   │
│  │  └──────────┘  └────────────────┘  └──────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| **Python Parser** | `ast` (标准库) | 零依赖，Python 原生语法树，支持 3.8-3.13 |
| **JS/TS Parser** | `tree-sitter` | 增量解析，支持 JSX/TSX，社区成熟 |
| **Symbol Table** | 自研 `SymbolTable` | 针对 Review 场景优化，轻量 |
| **Call Graph** | 自研 `CallGraph` | 静态分析 + 动态 fallback |
| **持久化** | SQLite | 零运维，单文件，适合 MVP |
| **缓存** | `functools.lru_cache` + disk | 内存缓存热点数据，磁盘持久化分析结果 |
| **远程存储** | GitHub API 按需拉取 | 无需 clone 完整仓库 |

### 为什么不用...

| 方案 | 放弃原因 |
|------|---------|
| **Pyright/PyLance** | 太重，为 IDE 设计，不是为 API 设计 |
| **jedi** | 交互式补全优化，批量分析慢 |
| **Neo4j** | MVP 不需要图数据库，SQLite 足够 |
| **Redis** | MVP 不需要独立缓存服务 |
| **Full Git Clone** | PR Review 只需要变更文件及其依赖 |

---

## 4. 数据结构

### 4.1 Symbol Table

```python
@dataclass
class Symbol:
    """代码中的符号（函数/类/变量）。"""
    name: str
    kind: Literal["function", "class", "variable", "method"]
    file_path: str
    line_start: int
    line_end: int
    docstring: str = ""
    is_public: bool = True

@dataclass
class SymbolTable:
    """所有已知符号的索引。"""
    symbols: dict[str, list[Symbol]]  # name → symbols (同名不同文件)
    by_file: dict[str, list[Symbol]]  # file_path → symbols

    def find(self, name: str, file_path: str = "") -> list[Symbol]:
        ...

    def find_by_file(self, file_path: str) -> list[Symbol]:
        ...
```

### 4.2 Call Graph

```python
@dataclass
class CallEdge:
    """函数调用关系。"""
    caller_file: str
    caller_func: str
    caller_line: int
    callee_file: str
    callee_func: str
    callee_line: int

@dataclass
class CallGraph:
    """函数调用图。"""
    calls: dict[str, list[CallEdge]]    # caller → edges
    called_by: dict[str, list[CallEdge]] # callee → edges

    def get_callers(self, func_name: str, file_path: str = "") -> list[CallEdge]:
        """谁调用了这个函数？"""
        ...

    def get_callees(self, func_name: str, file_path: str = "") -> list[CallEdge]:
        """这个函数调用了谁？"""
        ...

    def get_affected_callers(self, changed_func: str, depth: int = 1) -> list[CallEdge]:
        """递归获取所有受影响的调用者（最多 depth 层）。"""
        ...
```

### 4.3 Import Graph

```python
@dataclass
class ImportEdge:
    """文件导入关系。"""
    importer: str       # from path
    imported: str       # to path
    symbol: str = ""    # from x import Y 中的 Y

@dataclass
class ImportGraph:
    """文件级别的依赖图。"""
    imports: dict[str, list[ImportEdge]]    # importer → edges
    imported_by: dict[str, list[ImportEdge]] # imported → edges

    def get_affected_files(self, file_path: str, depth: int = 1) -> list[str]:
        """修改此文件会影响哪些文件？"""
        ...
```

### 4.4 Documentation Index

```python
@dataclass
class DocEntry:
    """文档项。"""
    symbol: str
    symbol_kind: str
    file_path: str
    docstring: str
    source_line: int
    source_url: str = ""

@dataclass
class DocIndex:
    """文档索引。"""
    entries: dict[str, list[DocEntry]]  # symbol → docs

    def get_docs(self, symbol: str) -> list[DocEntry]:
        ...

    def get_docs_for_files(self, file_paths: list[str]) -> list[DocEntry]:
        ...
```

### 4.5 Context Result

```python
@dataclass
class ContextResult:
    """检索到的完整上下文。"""
    # 变更有直接关系的
    changed_functions: list[Symbol]       # diff 中涉及的函数
    callers: list[CallEdge]               # 调用这些函数的代码
    callees: list[CallEdge]               # 被这些函数调用的代码
    related_classes: list[Symbol]         # 相关类定义
    related_files: list[str]              # 受影响的文件列表

    # 文档
    docstrings: list[DocEntry]            # 相关文档

    # 元信息
    retrieval_depth: int = 1
    total_files_scanned: int = 0
    duration_ms: int = 0

    def to_prompt_context(self) -> str:
        """格式化为 LLM Prompt 可读的上下文。"""
        ...
```

---

## 5. 核心流程

```
输入: changed_files = ["src/auth/login.py"]

① Scope Resolution
   └─ 确定需要扫描的目录范围（src/）

② File Scanning
   ├─ 读取 changed_files 列表
   ├─ 对每个文件进行 AST 解析
   └─ 构建 SymbolTable

③ Import Resolution
   ├─ 解析每个文件的 import 语句
   ├─ 确定直接依赖文件
   └─ 递归解析（depth=1）

④ Call Graph Construction
   ├─ 遍历所有函数定义
   ├─ 解析函数体中的 call 表达式
   └─ 构建 caller→callee 映射

⑤ Context Retrieval
   ├─ 从 diff 中提取变更符号
   ├─ CallGraph.get_callers(changed_func)
   ├─ CallGraph.get_callees(changed_func)
   ├─ ImportGraph.get_affected_files(changed_file)
   └─ DocIndex.get_docs(symbols)

⑥ Prompt Assembly
   └─ ContextResult.to_prompt_context() → LLM 输入
```

---

## 6. API 设计

```python
# === Service 层 ===

class ContextRetrievalService:
    """上下文检索服务。"""

    async def get_context(
        self,
        diff_result: DiffResult,
        repo: str = "",
        depth: int = 1,
    ) -> ContextResult:
        ...

    async def get_context_for_file(
        self,
        file_path: str,
        changed_symbols: list[str],
        depth: int = 1,
    ) -> ContextResult:
        ...


# === 集成到 ReviewService ===

class ReviewService:
    """增强后的 Review 服务。"""

    async def review(self, inp: ReviewInput) -> ReviewOutput:
        # Step 1-3: 获取 diff、解析
        diff_result = parse_diff(diff_text)

        # Step 4: 检索上下文 ← 新增
        context = await context_service.get_context(diff_result)

        # Step 5: 构建提示词（带上下文）← 增强
        prompt = build_review_prompt(
            pr_title=pr_meta.title,
            pr_description=pr_meta.title,
            diff=diff_text,
            risk_context=risk_context,
            code_context=context.to_prompt_context(),  # ← 新增
        )

        # Step 6: 调 LLM
        llm_result = await llm.review_pr(...)
        ...
```

---

## 7. Prompt 上下文格式

```
### Code Context (Related to Changes)

#### Callers (谁调用了变更的函数)
- `auth_controller.py:45` → `handle_login()` calls `login()`
- `middleware.py:22` → `authenticate()` calls `login()`

#### Callees (变更的函数调用了谁)
- `login()` calls `validate_credentials()` at `user_service.py:88`
- `login()` calls `create_session()` at `session.py:15`

#### Related Classes
- `class UserService` defined at `user_service.py:1`
  - `validate_credentials()` at `user_service.py:85`
- `class SessionManager` defined at `session.py:1`

#### Related Files
- `tests/test_auth.py` — Test cases for login flow
- `docs/api/auth.md` — API documentation for auth endpoints

#### Documentation
- `login()` at `src/auth/login.py:42`
  """Authenticate user and create session.

  Args:
      username: User's login name
      password: User's password

  Returns:
      Session token if authentication succeeds
      None if credentials are invalid
  """
```

---

## 8. 开发任务拆解

### Sprint 1 — 基础设施 + AST 解析器

| 任务 | 工时 | 产出 | 依赖 |
|------|------|------|------|
| 1.1 设计数据结构 | 4h | `context/models.py` — Symbol, CallEdge, ContextResult | 无 |
| 1.2 Python AST 解析器 | 8h | `context/parsers/python_ast.py` — 提取函数、类、调用 | 1.1 |
| 1.3 Symbol Table 构建器 | 6h | `context/index/symbol_table.py` | 1.2 |
| 1.4 Import 解析器 | 4h | `context/parsers/import_parser.py` — 解析 import 语句 | 1.1 |
| 1.5 单元测试 | 4h | tests 覆盖 AST 解析和 Symbol Table | 1.2-1.4 |

**验收标准**:
- [ ] 能解析 Python 文件的函数定义、类定义、函数调用
- [ ] 能提取所有 import 语句
- [ ] Symbol Table 支持按名称和文件查询

### Sprint 2 — Call Graph + Import Graph

| 任务 | 工时 | 产出 | 依赖 |
|------|------|------|------|
| 2.1 Call Graph 构建器 | 8h | `context/index/call_graph.py` | 1.3 |
| 2.2 Import Graph 构建器 | 4h | `context/index/import_graph.py` | 1.4 |
| 2.3 Docstring 提取器 | 3h | `context/parsers/docstring_extractor.py` | 1.1 |
| 2.4 跨文件引用解析 | 6h | 通过 Import Graph 解析跨文件调用 | 2.1, 2.2 |
| 2.5 单元测试 | 4h | 覆盖 Call Graph 和 Import Graph | 2.1-2.4 |

**验收标准**:
- [ ] 能构建跨文件的调用关系图
- [ ] 能追踪 "谁调用了 login()" 和 "login() 调用了谁"
- [ ] 能识别文件变更的传播影响

### Sprint 3 — ContextRetriever + Prompt 集成

| 任务 | 工时 | 产出 | 依赖 |
|------|------|------|------|
| 3.1 ContextRetrievalService | 6h | `context/retriever.py` — 编排检索流程 | 2.1-2.4 |
| 3.2 上下文格式化器 | 3h | `context/formatter.py` → LLM prompt | 3.1 |
| 3.3 缓存层 | 4h | 基于 LRU 的内存缓存 + SQLite 持久化 | 3.1 |
| 3.4 集成到 ReviewService | 4h | 改造 `review_service.py` | 3.1 |
| 3.5 集成测试 | 4h | E2E 测试：diff → context → prompt → review | 3.4 |
| 3.6 TypeScript/JS 解析器（可选） | 6h | 基于 tree-sitter 的 TS 支持 | 1.2 |

**验收标准**:
- [ ] 给定 diff，自动检索相关函数、类、文件、文档
- [ ] 上下文信息正确注入 LLM Prompt
- [ ] Review 质量显著提升（通过 Golden Dataset 验证）

---

## 9. 目录结构

```
backend/app/services/context/
├── __init__.py
├── models.py                  # 数据结构
├── retriever.py               # ContextRetrievalService
├── formatter.py               # 上下文 → Prompt 格式化
│
├── parsers/
│   ├── __init__.py
│   ├── base.py                # 抽象解析器接口
│   ├── python_ast.py          # Python AST 解析器
│   ├── import_parser.py       # 导入解析器
│   ├── docstring_extractor.py # 文档提取器
│   └── typescript.py          # TypeScript 解析器 (Sprint 3+)
│
├── index/
│   ├── __init__.py
│   ├── symbol_table.py        # 符号表
│   ├── call_graph.py          # 调用图
│   └── import_graph.py        # 导入图
│
└── cache/
    ├── __init__.py
    ├── memory_cache.py        # LRU 内存缓存
    └── sqlite_cache.py        # SQLite 持久缓存

tests/test_context/
├── test_python_ast.py
├── test_call_graph.py
├── test_import_graph.py
└── test_retriever.py
```

---

## 10. 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 大型仓库扫描慢 | 响应时间 > 30s | 中 | 增量扫描 + 缓存 + 限制 depth=1 |
| 动态调用无法解析 | 漏检 | 高 | 静态分析 + 运行时 Profile 辅助 |
| 跨语言调用链断裂 | 上下文不完整 | 中 | MVP 限定 Python，后续加 tree-sitter |
| 递归循环引用 | 死循环 | 低 | visited set 限制深度 |
| 测试文件误匹配 | 上下文过大 | 中 | 通过 test naming convention 过滤 |
