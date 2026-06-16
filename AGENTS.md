# AI PR Review Platform 开发工作流（必须遵守）

每次开发任何功能，都必须遵循以下流程。

固定说：

> 请按照 AGENTS.md 中定义的开发工作流完成本次开发。不要直接修改代码，必须依次完成：Issue → Branch → 开发 → 测试 → README 更新 → Commit → PR 描述 → Code Review → Merge Report。所有新增功能必须以一个独立 PR 的形式完成，保持 main 分支始终可运行。若发现遗漏（例如未生成 PR 描述、未更新文档、未补测试），请主动补齐后再结束任务。

---

## Step 1 — 扫描当前项目

确认：

- 当前阶段（参考 `docs/ROADMAP.md`）
- 当前 Roadmap 进度
- 已有 PR（`git log --oneline origin/main..HEAD` 或 GitHub PR 列表）
- 已有 Issue（GitHub Issues 列表）

**目标**：避免重复开发。

---

## Step 2 — 创建 Issue

输出：

- **Issue 标题** — 遵循 `feat(scope): description` 格式
- **Issue 描述** — 功能背景、目标、影响范围
- **验收标准** — 可量化、可验证的条件列表
- **预计工作量** — Small (1-2h) / Medium (4-8h) / Large (1-3d)

---

## Step 3 — 创建 Feature Branch

```bash
git checkout -b feature/risk-detection
```

命名规范：

| 类型 | 格式 | 示例 |
|------|------|------|
| 新功能 | `feature/<name>` | `feature/context-retrieval` |
| Bug 修复 | `fix/<name>` | `fix/github-429-retry` |
| 文档 | `docs/<name>` | `docs/api-reference` |
| 重构 | `refactor/<name>` | `refactor/prompt-builder` |

---

## Step 4 — 开发功能

要求：

- **一个 PR 只完成一个功能** — 大功能拆分为多个小 PR
- **不得修改无关模块** — 变更范围 = Issue 描述的范围
- 遵循 [Conventional Commits](https://www.conventionalcommits.org/)
- 遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 中的 PR 规范

---

## Step 5 — 自动补充测试

必须包含：

- **pytest** — 单元测试覆盖 happy path + error path
- **Mock Test** — 所有外部 API 调用（GitHub、LLM）必须 mock
- **API Test** — 如有新端点，必须测试 200 / 422 / 404 / 502

---

## Step 6 — 运行测试

```bash
python -m pytest tests/ -v --cov --cov-fail-under=80
```

如果失败：

- 分析失败原因
- 自动修复代码或测试
- 直到全部通过（`OK`）

---

## Step 7 — 更新文档

必须更新：

- **README.md** — 如新增功能影响用户使用方式
- **docs/ROADMAP.md** — 标记对应 Stage 的交付物为 ✅
- **CHANGELOG** — 记录本次变更
- **API 文档** — 如有新端点或接口变更

---

## Step 8 — 生成 Commit

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat(review): add risk detection engine
fix(github): handle paginated API responses
test(parser): add URL validation edge cases
docs(readme): update API reference
refactor(service): extract prompt builder module
```

---

## Step 9 — 生成 Pull Request

PR 必须包含：

1. **标题** — `feat(scope): description` 格式
2. **功能描述** — 这个 PR 做了什么，为什么需要
3. **实现思路** — 技术选型和核心逻辑说明
4. **测试方式** — 如何验证功能正常运行（命令 + 预期结果）
5. **风险影响** — 对现有功能的影响评估
6. **验收标准** — 从 Issue 复制的验收条件（已完成的打 ✅）

---

## Step 10 — Code Review

检查项：

| 维度 | 检查内容 |
|------|---------|
| Bug | 是否存在逻辑错误、边界条件遗漏、空值处理不足 |
| 重复代码 | 是否与已有代码重复，是否可以抽取公共逻辑 |
| 测试覆盖 | 是否达到 ≥80%，是否覆盖异常路径 |
| Prompt | Prompt 变更是否影响输出质量 |
| 异常处理 | 外部调用是否有 try/except，错误信息是否清晰 |
| 日志 | 关键路径是否有日志，日志级别是否正确 |
| 性能 | 是否存在 N+1 查询、同步阻塞、内存泄漏 |

如果存在问题：

- 自动整改
- 重新运行测试
- 更新 PR

---

## Step 11 — Merge Report

输出 Merge Report，包括：

- ✅ 所有测试通过
- ✅ Coverage ≥ 80%
- ✅ CI 全部绿色
- ✅ Code Review 通过
- ✅ 文档已更新

如果全部满足：

> **可以 Merge**

否则：

> **继续整改**，重复 Step 5-10。

---

## 规则（不可违反）

| 规则 | 说明 |
|------|------|
| ❌ 不得跳过 Issue | 每个功能必须有对应的 Issue |
| ❌ 不得跳过 PR | 所有代码通过 PR 合并，禁止直接 push main |
| ❌ 不得跳过测试 | 新功能必须有测试，Bug 修复必须有回归测试 |
| ❌ 不得跳过 README 更新 | 影响用户使用的变更必须更新文档 |

---

## 快速检查清单

```bash
# 开发完成后的自检
□ git log --oneline -3          # Commit 格式正确
□ python -m pytest tests/ -v    # 全部通过
□ git diff origin/main --stat   # 变更范围合理
□ 检查 docs/ROADMAP.md 已更新
□ 检查 CHANGELOG 已更新
```
