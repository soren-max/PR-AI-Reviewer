# AI PR Review Platform 企业级开发规范

> 本项目所有开发任务必须遵循本规范。
>
> AI（Codex / Claude Code / Reasonix）不得跳过任何流程。

---

# 一、开发工作流（GitHub Flow）

采用 GitHub Flow。

规则：

* main 永远保持可部署
* 禁止直接向 main 提交业务代码
* 所有开发必须基于 feature 分支
* 所有修改必须通过 Pull Request 合并

流程：

Issue

↓

Feature Branch

↓

Coding

↓

Test

↓

Documentation

↓

Commit

↓

Pull Request

↓

Code Review

↓

CI

↓

Merge

↓

Delete Branch

---

# 二、Branch 命名规范

功能：

feature/github-client

feature/diff-analysis

feature/risk-detection

feature/langgraph-workflow

修复：

fix/review-parser

fix/json-output

文档：

docs/readme

docs/api

测试：

test/github-client

CI：

ci/github-actions

重构：

refactor/review-service

---

# 三、Issue 规范

任何开发必须先创建 Issue。

Issue 必须包含：

标题

背景

目标

验收标准

影响范围

预计工时

Priority：

P0

P1

P2

P3

---

# 四、PR 规范

一个 PR：

只完成一个功能。

禁止：

一个 PR：

同时：

Review

Context

Prompt

README

全部修改。

PR 建议：

200~400 行以内。

---

PR 必须包含：

# 标题

一句话描述本次功能。

例如：

Add Risk Detection Engine

---

# 背景

为什么做。

---

# 功能描述

用户价值。

---

# 实现思路

核心设计。

---

# 修改范围

修改哪些模块。

---

# 测试方式

pytest

API

Mock

人工验证

---

# 风险影响

是否影响：

API

数据库

Prompt

前端

---

Checklist：

* [ ] 一个 PR 一个功能
* [ ] pytest通过
* [ ] GitHub Actions通过
* [ ] README已更新
* [ ] 文档已同步
* [ ] 无TODO
* [ ] 无Debug代码

---

# 五、Commit 规范

必须采用：

Conventional Commits

例如：

feat(review): add risk detection engine

feat(langgraph): implement workflow v1

fix(parser): handle invalid github url

docs(readme): update architecture

test(diff): add unit tests

refactor(service): simplify review pipeline

ci(actions): add github workflow

禁止：

update

modify

test

final

123

---

# 六、Code Review 规范

Merge 前必须检查：

Bug

Code Smell

重复代码

异常处理

日志

Prompt

Magic Number

Hardcode

Dead Code

TODO

性能

安全

所有问题：

P0

P1

P2

排序。

---

# 七、测试规范

任何新增功能：

必须补测试。

至少：

Unit Test

API Test

Mock Test

Review Prompt Test（后期）

Eval Test（Harness阶段）

CI：

pytest

必须100%通过。

---

# 八、文档规范

每个 PR：

根据情况更新：

README

ROADMAP

CHANGELOG

API 文档

设计文档

新增模块：

必须新增：

Architecture Diagram

Sequence Diagram（重要模块）

---

# 九、CI/CD

GitHub Actions：

自动：

Lint

pytest

Coverage

Build

PR：

必须：

CI Pass

才能Merge。

---

# 十、Branch Protection

main：

开启：

Require Pull Request

Require Status Checks

Dismiss Stale Reviews

Require Conversation Resolution

Require Linear History（推荐）

Require Signed Commits（可选）

Include Administrators

---

# 十一、AI 开发规范

Codex / Claude Code / Reasonix：

不得：

直接写代码。

必须：

扫描项目

↓

分析影响

↓

创建Issue

↓

创建Branch

↓

开发

↓

补测试

↓

运行CI

↓

更新README

↓

生成Commit

↓

生成PR

↓

Code Review

↓

Merge Report

如果遗漏：

README

Commit

PR

Issue

Test

CI

Documentation

必须主动补齐。

---

# 十二、AI PR Review Platform 特殊规范

本项目最终目标：

企业级 AI Code Review Platform。

不得满足于：

Demo。

所有设计必须优先考虑：

Context Understanding

Accuracy

False Positive

False Negative

Latency

Scalability

Maintainability

未来：

Tree-sitter

LangGraph

Code RAG

Harness

MCP

必须保持可扩展。

---

# 十三、Definition of Done（DoD）

一个功能只有满足以下条件才算完成：

✅ 功能开发完成

✅ 测试通过

✅ 文档更新

✅ README同步

✅ Commit规范

✅ PR规范

✅ Code Review完成

✅ CI通过

✅ Merge Report生成

否则：

视为未完成。
