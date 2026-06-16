# Project Score

Assessment date: 2026-06-16

## Week2 Score

| Area | Score | Notes |
| --- | ---: | --- |
| 架构 | 8.0 | 后端主链路已按 API、service、provider、review domain 分层，ReviewService 支持依赖注入，GitHub/LLM/报告生成边界更清晰；仍存在仓库根目录原型代码与 `ai-pr-review/` 产品代码并存的问题。 |
| 代码质量 | 8.4 | 修复了 GitHub 分页、PR body 丢失、删除文件状态不规范、配置解析、LLM JSON 解析、Prompt 截断和测试隔离问题；backend Ruff 全量通过。 |
| 工程能力 | 8.5 | CI 已拆分 backend 与 legacy quality gate，backend 支持 lint、compile、pytest，API 测试迁移到 ASGITransport，外部依赖使用 mock 注入。 |
| AI能力 | 8.2 | Review Prompt V2 已要求 JSON 结构化输出，输入包含 PR metadata、diff、risk context，并限制大 diff token 浪费；下一阶段仍需做代码上下文检索与分块聚合。 |
| 可维护性 | 8.0 | Prompt、风险分析、diff 解析、报告生成更集中，测试覆盖关键路径；但同步报告生成与异步报告生成还存在两套兼容逻辑。 |
| 扩展性 | 8.0 | LLM provider factory 支持 DeepSeek/OpenAI/Qwen，ReviewService 已可替换 GitHub/LLM client；后续可扩展 provider fallback、任务队列、上下文检索和审计日志。 |
| 部署能力 | 7.6 | GitHub Actions 已覆盖核心质量门禁，backend 生产启动风险降低；仍缺少迁移策略、生产级 Redis/PostgreSQL 配置、observability 和 secret rotation 文档。 |
| 测试能力 | 8.3 | backend `77 passed`，legacy selected `146 passed`，覆盖 API、service、GitHub mock、LLM mock、task mock；前端测试和覆盖率门禁仍待补齐。 |
| Overall | 8.1 | 已达到 Week2 进入 Week3 的最低工程标准，具备可继续扩展的 AI PR Review MVP 能力；尚未达到完整中大型互联网企业 AI 应用项目标准。 |

## Week2 Acceptance

| Requirement | Status | Evidence |
| --- | --- | --- |
| Diff Analysis | Done | `app/services/review/diff_parser.py` 自包含解析逻辑，legacy diff analyzer tests 通过。 |
| Risk Detection | Done | `app/services/review/risk_analyzer.py` 生成 deterministic risk context，并进入 LLM prompt。 |
| Review Prompt V2 | Done | `prompts/pr_review_agent.md` 约束 JSON-only、severity、category、line range 和修复建议。 |
| JSON结构化输出 | Done | `report_generator.py` 兼容 V2 schema，并保留 legacy fallback。 |
| pytest | Done | backend `77 passed`，legacy selected `146 passed`。 |
| Mock Test | Done | API、GitHub、LLM、background task 均使用 mock/override。 |
| GitHub Actions | Done | `.github/workflows/ci.yml` 执行 backend lint、compile、pytest 和 legacy selected tests。 |

## Week3 Gate

Conclusion:
可以进入 Week3，但必须在用户验收并提交 Week2 变更后进入。

Conditions:

- Week3 第一优先级应是代码上下文获取设计和现有重复模块治理。
- 不建议直接上 LangGraph 或 RAG。应先把上下文检索边界、数据结构、缓存和评测样例设计清楚。
- 根目录旧测试 `tests/test_review_service.py` 仍属于历史债务，当前 CI 已避开，但后续需要删除、迁移或修复。

## Remaining Issues

### P0

None.

### P1

Issue:
根目录 legacy 原型代码与 `ai-pr-review/backend` 产品代码并存。

Impact:
新成员容易误改旧模块，CI 需要选择性执行，长期会造成行为分叉。

Best Practice:
明确根目录模块生命周期：归档、迁移为 package，或删除重复实现。

Suggested Fix:
Week3 开始前建立 `legacy/` 归档计划，迁移仍有价值的测试到 backend。

### P1

Issue:
LLM 输出 schema 目前由 prompt 和报告解析兜底约束，缺少独立 schema validator。

Impact:
模型输出字段漂移时可以被兼容解析，但无法稳定给前端、API、后续 Agent 使用。

Best Practice:
使用 Pydantic model 校验 Review JSON，并输出标准错误与 fallback report。

Suggested Fix:
新增 `ReviewOutput` schema，LLM result 先 parse/validate，再进入 markdown/report generation。

### P2

Issue:
前端自动化测试和端到端测试仍缺失。

Impact:
Review JSON schema 或 API 响应字段变化时，前端可能静默损坏。

Best Practice:
补充组件测试、API contract mock、关键页面 smoke test。

Suggested Fix:
Week3 或 Week4 引入 frontend test gate。

## Enterprise Evaluation

当前项目已经超过 Demo 水平，具备企业级 AI PR Review Platform 的雏形：有稳定后端 API、GitHub PR/Diff 获取、AI Review prompt、风险识别、结构化输出、mock 测试和 CI 门禁。

但还没有达到中大型互联网企业 AI 应用项目完整标准。主要缺口在生产级上下文检索、模型输出强校验、队列与异步任务可靠性、观测指标、权限安全、前端测试和部署治理。
