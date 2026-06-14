<div align="center">

<!-- ================================================================== -->
<!-- Badges                                                              -->
<!-- ================================================================== -->

<p>
  <a href="https://github.com/soren-max/PR-AI-Reviewer/actions/workflows/ci.yml">
    <img src="https://github.com/soren-max/PR-AI-Reviewer/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI">
  </a>
  <a href="https://codecov.io/gh/soren-max/PR-AI-Reviewer">
    <img src="https://img.shields.io/codecov/c/github/soren-max/PR-AI-Reviewer/main" alt="Codecov">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.12-blue?logo=python" alt="Python">
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img src="https://img.shields.io/badge/Framework-FastAPI-009688?logo=fastapi" alt="FastAPI">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/badge/code%20style-ruff-000000" alt="Ruff">
  </a>
  <a href="https://mypy-lang.org/">
    <img src="https://img.shields.io/badge/types-mypy-blue" alt="Mypy">
  </a>
  <a href="https://conventionalcommits.org">
    <img src="https://img.shields.io/badge/commits-conventional-brightgreen" alt="Conventional Commits">
  </a>
</p>

<!-- ================================================================== -->
<!-- Title                                                               -->
<!-- ================================================================== -->

<h1 align="center">🤖 AI PR Review</h1>
<p align="center">
  <em>Intelligent Pull Request analysis — powered by LLM</em>
</p>

<p align="center">
  <strong>
    输入 GitHub PR 链接 → AI 自动分析代码质量、安全、性能 → 输出结构化审核报告
  </strong>
</p>

<!-- ================================================================== -->
<!-- Demo Video — 显眼位置                                               -->
<!-- ================================================================== -->

<br>

## 🎥 Demo 视频

<p align="center">
  <a href="https://www.bilibili.com/video/BV1xxxxxxxxxxxxx/">
    <img src="https://img.shields.io/badge/▶️%20Demo%20Video-Bilibili-00A1D6?style=for-the-badge&logo=bilibili" alt="Demo Video">
  </a>
  &nbsp;&nbsp;
  <a href="https://drive.google.com/your-video-link">
    <img src="https://img.shields.io/badge/▶️%20Demo%20Video-%E4%BA%91%E7%9B%98-4285F4?style=for-the-badge&logo=google-drive" alt="Cloud Backup">
  </a>
</p>

<p align="center">
  <strong>⬆️ 点击上方按钮查看完整功能演示 ⬆️</strong><br>
  <sub>视频包含：PR 提交 → 状态轮询 → 报告展示 → 错误处理 全流程讲解</sub>
</p>

<br>

</div>

<!-- ================================================================== -->
<!-- Table of Contents                                                   -->
<!-- ================================================================== -->

## 📑 目录

- [项目简介](#-项目简介)
- [核心功能](#-核心功能)
- [Demo 视频](#-demo-视频)
- [系统架构](#️-系统架构)
- [快速开始](#-快速开始)
- [API 参考](#-api-参考)
- [开发指南](#-开发指南)
- [PR 提交规范](#-pr-提交规范)
- [持续交付策略](#-持续交付策略)
- [项目结构](#-项目结构)
- [技术栈](#-技术栈)
- [许可证](#-许可证)

<!-- ================================================================== -->
<!-- Project Description                                                 -->
<!-- ================================================================== -->

## 📋 项目简介

**AI PR Review** 是一个智能代码审核平台，旨在自动化 Pull Request 审查流程。用户只需提交一个 GitHub PR 链接，系统便会自动拉取 PR 变更内容，利用大语言模型进行代码质量分析，并生成结构化的审核报告。

本项目采用 **全周期持续交付** 的开发模式，从第一个 CI/Issue 发布开始，持续通过小粒度 PR 推进开发，确保主分支始终保持可运行状态。

### 解决的问题

- **人工审查耗时**: 大型 PR 的代码审查需要数小时，AI 可秒级初筛
- **审查标准不统一**: 不同审查者关注点不同，AI 提供一致的评价维度
- **安全隐患遗漏**: AI 能系统性检测常见的 OWASP 安全模式
- **新人上手慢**: 自动化审查提供即时反馈，加速团队代码规范内化

<!-- ================================================================== -->
<!-- Features                                                            -->
<!-- ================================================================== -->

## ✨ 核心功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 🔗 PR URL 解析 | 自动提取 owner / repo / pull_number，支持 query、fragment | ✅ 完成 |
| 🔍 GitHub API 集成 | 获取 PR 标题、描述、变更文件列表、Unified Diff | ✅ 完成 |
| 🔄 自动重试 | 指数退避重试（429 / 5xx / 网络超时），最多 4 次 | ✅ 完成 |
| ⏱ Rate Limit 跟踪 | 实时跟踪 GitHub API 剩余配额，耗尽自动等待 | ✅ 完成 |
| 📊 异常体系 | 6 种自定义异常（Auth/NotFound/RateLimit/Conflict/Server/Network） | ✅ 完成 |
| 🧪 测试覆盖 | 38 个单元测试 + 20 个 URL 解析测试，全部通过 | ✅ 完成 |
| 🤖 LLM 分析 | 集成 DeepSeek / OpenAI，输出结构化审核报告 | 🚧 开发中 |
| 📱 前端界面 | Next.js SPA，PR 提交 → 状态轮询 → 报告展示 | 🚧 开发中 |

<!-- ================================================================== -->
<!-- Architecture                                                        -->
<!-- ================================================================== -->

## 🏗️ 系统架构

### 整体架构

```
┌──────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Next.js SPA  │─────▶│  FastAPI Backend  │─────▶│  DeepSeek /     │
│  (Port 3000)  │      │  (Port 8000)      │      │  OpenAI API     │
└──────────────┘      └────────┬─────────┘      └─────────────────┘
                               │
                        ┌──────▼──────┐
                        │  GitHub API  │
                        │  (External)  │
                        └─────────────┘
```

### 数据流

```
① POST /api/v1/reviews  →  create Review (status=pending)
② Background task:
   ├─ status → fetching
   ├─ GET GitHub PR metadata + diff (with retry)
   ├─ status → analyzing
   ├─ Build structured prompt → call LLM
   └─ Parse response → persist comments → status → completed
③ Frontend polls GET /api/v1/reviews/{id} every 3s
④ status=completed → render report (score gauge + comments + file tree)
```

### 模块划分

```
app/
├── main.py                  # FastAPI 应用入口，路由注册
├── github_url.py            # PR URL 解析器（纯函数，无 I/O）
├── github_client.py         # GitHub API 客户端（requests，自动重试）
└── ai_reviewer.py           # LLM 分析引擎（prompt 构建 + 响应解析）

tests/
├── test_github_url.py       # URL 解析测试（20 cases）
└── test_github_client.py    # API 客户端测试（38 cases）
```

<!-- ================================================================== -->
<!-- Quick Start                                                         -->
<!-- ================================================================== -->

## 🚀 快速开始

### 前置依赖

- **Python** 3.12+
- **pip** (latest)
- 一个 [DeepSeek API Key](https://platform.deepseek.com/) 或 [OpenAI API Key](https://platform.openai.com/)

### 安装步骤（5 分钟）

```bash
# 1. 克隆仓库
git clone https://github.com/soren-max/PR-AI-Reviewer.git
cd PR-AI-Reviewer

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env:
#   DEEPSEEK_API_KEY=sk-...      (必需)
#   GITHUB_TOKEN=ghp_...         (可选，提升 API 限流配额)
```

### 启动服务

```bash
# 开发模式（热重载）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 访问 API 文档
open http://localhost:8000/docs
```

### Docker 启动

```bash
docker compose -f infra/docker-compose.yml up --build
```

<!-- ================================================================== -->
<!-- API Reference                                                       -->
<!-- ================================================================== -->

## 📖 API 参考

### 提交审核

```bash
curl -X POST http://localhost:8000/api/v1/reviews \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/42"}'
```

**响应** (201 Created):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "pr_url": "https://github.com/owner/repo/pull/42",
  "status": "pending",
  "created_at": "2025-01-01T00:00:00+00:00"
}
```

### 获取审核结果

```bash
curl http://localhost:8000/api/v1/reviews/550e8400-e29b-41d4-a716-446655440000
```

**响应** (200 OK):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "summary": {
    "overall_score": 81,
    "total_issues": 5,
    "critical": 1,
    "major": 2,
    "minor": 2
  },
  "comments": [
    {
      "file_path": "src/auth/login.py",
      "line_start": 42,
      "severity": "critical",
      "category": "security",
      "title": "Hardcoded secret key",
      "body": "Secret key is hardcoded in source code...",
      "suggestion": "Use an environment variable instead",
      "code_snippet": "SECRET_KEY = 'super-secret-123'"
    }
  ]
}
```

### 健康检查

```bash
curl http://localhost:8000/api/v1/health
```

```json
{"status": "ok", "version": "0.1.0"}
```

### 配置项

| 环境变量 | 必需 | 默认值 | 说明 |
|----------|------|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | — | DeepSeek API 密钥 |
| `OPENAI_API_KEY` | ✅ | — | OpenAI API 密钥（二选一） |
| `GITHUB_TOKEN` | ❌ | — | GitHub Token（无 token 60 req/h） |
| `DATABASE_URL` | ❌ | `sqlite+aiosqlite:///./data/db` | 数据库连接串 |
| `LOG_LEVEL` | ❌ | `INFO` | 日志级别 |

<!-- ================================================================== -->
<!-- Development                                                         -->
<!-- ================================================================== -->

## 🧪 开发指南

### 常用命令

```bash
make install      # 安装全部依赖
make run          # 启动开发服务器（热重载）
make test         # 运行全部测试
make lint         # 代码风格检查（ruff + flake8 + mypy）
make ci           # 完整 CI 流水线（lint → test）
make format       # 自动格式化代码
make docker-up    # Docker Compose 启动
```

### 测试

```bash
# 运行全部测试
make test

# 运行特定测试模块
python -m unittest tests.test_github_client -v
python -m unittest tests.test_github_url -v

# 当前覆盖率：38 个 API 客户端测试 + 20 个 URL 解析测试
# 测试框架：unittest（零外部依赖）+ mock
```

### 代码规范

- **风格**: PEP 8，由 ruff 强制
- **类型注解**: 所有函数必需，由 mypy --strict 检查
- **格式化**: ruff formatter（行宽 88）
- **导入排序**: ruff isort 兼容
- **文档**: Google 风格 docstring

<!-- ================================================================== -->
<!-- PR Standards                                                        -->
<!-- ================================================================== -->

## 📝 PR 提交规范

本项目严格遵循 **小粒度、单一职责** 的 PR 提交流程。

### 核心原则

1. **每个 PR 只做一件事**: 每个 PR 只实现或修改单一功能
2. **粒度尽可能细**: 大功能拆分为多个独立 PR 分步提交
3. **PR 描述需清晰完整**: 包含功能描述、实现思路、测试方式
4. **PR 合并后主分支可运行**: 评审者随时可复现演示

### PR 模板

每个 PR 必须包含以下内容：

```
## 功能描述
说明该功能的作用与使用方式

## 实现思路
简要说明技术选型或核心实现逻辑

## 测试方式
如何验证该功能正常运行

## 相关 Issue
Closes #XXX
```

### 开发流程示例

```
Week 1:
  PR #1  🚧 项目骨架 + CI 配置 + Makefile        ← 基础设施
  PR #2  🔧 PR URL 解析器（github_url.py）        ← 原子功能
  PR #3  🔧 GitHub API 客户端（github_client.py）  ← 原子功能

Week 2:
  PR #4  🤖 LLM 分析引擎（prompt 构建 + 响应解析） ← 核心功能
  PR #5  🎨 FastAPI 路由 + 异步任务编排            ← 集成层
  PR #6  ✅ 集成测试 + 边界情况覆盖                 ← 质量保证

Week 3:
  PR #7  🖥️ Next.js 前端 — PR 提交表单             ← 用户界面
  PR #8  🖥️ 状态轮询 + 报告展示                     ← 用户界面
  PR #9  📦 Docker Compose + 部署文档              ← DevOps
```

<!-- ================================================================== -->
<!-- CD Strategy                                                         -->
<!-- ================================================================== -->

## 🔄 持续交付策略

### 全周期持续交付

本项目从 **第一个 Issue 发布之日起** 即进入持续交付模式，严禁临尾突击提交。

**时间线规范**:

```
Day 1 ───── 发布项目骨架 + CI 配置（PR #1）
Day 2 ───── PR URL 解析模块（PR #2）
Day 3 ───── GitHub API 客户端（PR #3）
  ...      持续小粒度 PR
Day N ───── 最终功能交付
```

### Commit 规范

所有 commit 时间戳必须落在所选批次的起止时间之内，否则视为无效。

- Commit 格式：[Conventional Commits](https://www.conventionalcommits.org/)
- 类型: `feat` / `fix` / `docs` / `refactor` / `test` / `ci` / `chore`
- 示例: `feat(github): add PR URL parser with owner/repo/number extraction`

### 无效情形

以下情形将导致作品无效：

- ❌ 最后一天一次性导入所有代码
- ❌ Commit 时间戳超出批次时间范围
- ❌ PR 描述空白或与实际代码变更严重不符

<!-- ================================================================== -->
<!-- Project Structure                                                   -->
<!-- ================================================================== -->

## 📁 项目结构

```
PR-AI-Reviewer/
│
├── .github/
│   ├── workflows/
│   │   └── ci.yml                  # CI 流水线（lint + test + security）
│   ├── PULL_REQUEST_TEMPLATE.md    # PR 模板
│   └── ISSUE_TEMPLATE/             # Issue 模板（bug / feature）
│
├── app/                            # 核心应用代码
│   ├── __init__.py
│   ├── main.py                     # FastAPI 入口
│   ├── github_url.py               # PR URL 解析器（纯函数）
│   ├── github_client.py            # GitHub API 客户端（requests + 重试）
│   └── ai_reviewer.py              # LLM 分析引擎
│
├── tests/                          # 测试套件（unittest）
│   ├── __init__.py
│   ├── test_github_url.py          # 20 个 URL 解析测试
│   └── test_github_client.py       # 38 个 API 客户端测试
│
├── infra/                          # 基础设施
│   ├── docker-compose.yml          # 开发环境
│   └── docker-compose.prod.yml     # 生产环境
│
├── docs/                           # 文档
│   └── adr/                        # 架构决策记录
│
├── scripts/                        # 运维脚本
│   ├── bootstrap.sh                # 一键环境初始化
│   └── run-tests.sh                # 测试运行器
│
├── .flake8                         # Flake8 配置
├── .editorconfig                   # 编辑器统一配置
├── .gitignore                      # Git 忽略规则
├── Makefile                        # 自动化命令（18 个 target）
├── CONTRIBUTING.md                 # 贡献指南
├── CODE_OF_CONDUCT.md              # 行为准则
├── requirements.txt                # 生产依赖
└── README.md                       # ← 本文档
```

<!-- ================================================================== -->
<!-- Tech Stack                                                          -->
<!-- ================================================================== -->

## 🛠️ 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **后端框架** | Python 3.12 + FastAPI | REST API 服务 |
| **API 客户端** | requests (同步) | GitHub API 调用 |
| **LLM** | DeepSeek V4 Pro / OpenAI GPT-4 | 代码分析引擎 |
| **数据库** | SQLite (aiosqlite) | MVP 数据持久化 |
| **前端** | Next.js 14 + React 18 + TypeScript | 用户界面 |
| **样式** | Tailwind CSS | 响应式 UI |
| **测试** | unittest + mock | 单元测试（零外部依赖） |
| **CI** | GitHub Actions | 自动 lint + test + security |
| **容器化** | Docker + Docker Compose | 开发/部署环境 |
| **代码规范** | Ruff + Flake8 + Mypy (strict) | 代码质量门禁 |

<!-- ================================================================== -->
<!-- PR History                                                          -->
<!-- ================================================================== -->

## 📜 PR 历史记录

| PR | 功能 | 状态 | 日期 |
|----|------|------|------|
| #1 | 🚧 项目骨架 + CI 配置 + Makefile + README | ✅ Merged | Day 1 |
| #2 | 🔧 PR URL 解析器（github_url.py） | ✅ Merged | Day 2 |
| #3 | 🔧 GitHub API 客户端（github_client.py） | ✅ Merged | Day 3 |
| #4 | 🤖 LLM 分析引擎 | 🚧 In Progress | — |
| #5 | 🎨 FastAPI 路由 + 异步任务编排 | 📅 Planned | — |
| #6 | 🖥️ Next.js 前端 | 📅 Planned | — |

<!-- ================================================================== -->
<!-- License + Contact                                                   -->
<!-- ================================================================== -->

## 📄 许可证

本项目基于 MIT 许可证开源 — 详见 [LICENSE](./LICENSE) 文件。

---

<div align="center">

**🔗 仓库地址**: [github.com/soren-max/PR-AI-Reviewer](https://github.com/soren-max/PR-AI-Reviewer)

**🎥 Demo 视频**: [Bilibili](https://www.bilibili.com/video/BV1xxxxxxxxxxxxx/) · [云盘备份](https://drive.google.com/your-video-link)

**📧 联系**: [提交 Issue](https://github.com/soren-max/PR-AI-Reviewer/issues)

<br>
<sub>Built with ❤️ and 🐍 — 全周期持续交付，每个 PR 只做一件事</sub>

</div>
