# AI PR Review — 需求验收文档

> 每项功能在开发前先定义验收标准，代码完成后逐条验证。
> 所有验收标准必须可量化、可测试、可复现。

---

## F1：PR 链接解析

**模块**: `github_url.py`

**功能描述**: 将 GitHub Pull Request URL 解析为结构化数据。

### 输入

```text
https://github.com/langchain-ai/langgraph/pull/123
```

### 预期输出

```json
{
  "owner": "langchain-ai",
  "repo": "langgraph",
  "pull_number": 123
}
```

### 验收标准

| # | 验收标准 | 验证方式 |
|---|---------|---------|
| 1.1 | 标准 URL 正确解析 owner / repo / pull_number | `parse_pr_url("https://github.com/a/b/pull/42") → owner="a", repo="b", pull_number=42` |
| 1.2 | 支持 `www.github.com` 子域名 | `www.github.com/a/b/pull/1` 正常解析 |
| 1.3 | 支持尾部斜杠 | `https://github.com/a/b/pull/42/` 正常解析 |
| 1.4 | 自动剥离 Query 参数 | `?diff=unified` 不影响解析结果 |
| 1.5 | 自动剥离 Fragment | `#issuecomment-123` 不影响解析结果 |
| 1.6 | 自动去除首尾空白 | `"  https://github.com/a/b/pull/99  "` 正常解析 |
| 1.7 | 支持单字符 owner/repo 名 | `https://github.com/a/b/pull/1 → owner="a"` |
| 1.8 | 非法 URL 抛出 `InvalidGitHubURLError` | 非 github.com 域名 → 异常 |
| 1.9 | 非 PR 路径抛出 `NotAPullRequestURLError` | `/issues/1` / `/tree/main` → 异常 |
| 1.10 | 非数字 PR 编号抛出错误 | `/pull/abc` → 异常 |
| 1.11 | PR 编号为 0 抛出 `InvalidPullNumberError` | `/pull/0` → 异常 |
| 1.12 | `is_valid_pr_url()` 返回 bool 不抛异常 | 非法入参返回 `False` |
| 1.13 | `ParsedPRUrl` 不可变（frozen dataclass） | 修改属性抛出 `AttributeError` |
| 1.14 | `to_dict()` 返回规范字典 | 输出格式与验收文档一致 |
| 1.15 | `api_path` 返回 GitHub API v3 路径 | `/repos/{owner}/{repo}/pulls/{number}` |
| 1.16 | 严格模式拒绝非法 owner/repo 名 | 以 `-` 开头的 owner → 异常 |
| 1.17 | 宽松模式接受特殊名称 | `strict=False` 时 -owner 可解析 |

---

## F2：GitHub API 客户端

**模块**: `github_client.py`

**功能描述**: 通过 GitHub REST API v3 获取 PR 元数据和代码变更。

### 输入

```python
client = GitHubClient(token="ghp_xxx")
pr = client.get_pr("langchain-ai", "langgraph", 123)
files = client.get_pr_files("langchain-ai", "langgraph", 123)
diff = client.get_pr_diff("langchain-ai", "langgraph", 123)
data = client.review_pr("langchain-ai", "langgraph", 123)
```

### 预期输出

```python
pr.title        # "Fix: ..."
pr.description  # "## Summary\n... "
pr.author       # "octocat"
pr.state        # "open"
pr.base_branch  # "main"
pr.head_branch  # "feat/xxx"
pr.mergeable    # True / False / None
pr.additions    # 120
pr.deletions    # 45

files[0].filename   # "src/auth.py"
files[0].status     # "modified"
files[0].additions  # 30
files[0].deletions  # 5
files[0].patch      # "@@ -1,3 +1,8 @@..."
files[0].is_binary  # False

diff  # "diff --git a/src/auth.py b/src/auth.py..."
```

### 验收标准

| # | 验收标准 | 验证方式 |
|---|---------|---------|
| 2.1 | `get_pr()` 返回 `PRDetail` 含 title/description/author/state/branches | mock 200 → 所有字段正确填充 |
| 2.2 | `get_pr()` 正确映射 `mergeable` 三态（True/False/None） | 分别 mock 三种情况 |
| 2.3 | `get_pr_files()` 返回 `list[FileChange]` | mock 200 → 长度正确 |
| 2.4 | `get_pr_files()` binary 文件标记 `is_binary=True`，patch=None | mock binary 扩展名文件 |
| 2.5 | `get_pr_files()` 自动处理分页（>100 文件） | side_effect 返回两页 → 合并正确 |
| 2.6 | `get_pr_diff()` 返回 raw diff 字符串 | 包含 `diff --git` 标记 |
| 2.7 | `get_pr_diff()` 使用 `application/vnd.github.v3.diff` Accept 头 | 验证请求 header |
| 2.8 | `review_pr()` 聚合 pr + files + diff 为 `PRReviewData` | 一次调用返回三个数据 |
| 2.9 | Rate Limit 头被正确解析并缓存 | `client.rate_limit.remaining` 正确 |
| 2.10 | `GitHubClient` 可作为 context manager 使用 | `with GitHubClient() as c:` |
| 2.11 | HTTP 401 → `GitHubAuthError` | mock 401 → 异常 |
| 2.12 | HTTP 404 → `GitHubNotFoundError` | mock 404 → 异常，含 resource 信息 |
| 2.13 | HTTP 403/429 → `GitHubRateLimitError` | mock 403/429 → 异常，含 rate_limit 和 retry_after |
| 2.14 | HTTP 409 → `GitHubConflictError` | mock 409 → 异常 |
| 2.15 | HTTP 5xx → `GitHubServerError` | mock 500/502/503 → 异常 |
| 2.16 | 网络错误 → `GitHubConnectionError` | mock ConnectionError/Timeout → 异常 |
| 2.17 | 503 自动重试，成功后返回结果 | side_effect: [503, 200] → 第2次返回数据 |
| 2.18 | 连续 503 耗尽重试次数后抛出异常 | 5 次 503 → `GitHubServerError` |
| 2.19 | 网络错误耗尽重试后抛出 `GitHubConnectionError` | 5 次 ConnectionError → 异常 |
| 2.20 | 所有异常均为 `GitHubClientError` 子类 | `issubclass` 验证 |

---

## F3：PR Review Agent Prompt

**模块**: `prompts/pr_review_agent.md`

**功能描述**: 定义 LLM 进行代码审查的系统提示词。

### 输入

```text
PR Title: "Fix login redirect"
PR Description: "Updated callback URL"
Diff: "diff --git a/src/auth.py..."
```

### 预期输出

```markdown
## 📋 PR Summary

...

## 🔧 Changed Modules

...

## ⚠️ Potential Risks

...

## 🐛 Bug Suggestions

...

## ⚡ Performance Suggestions

...

## 🔒 Security Suggestions

...
```

### 验收标准

| # | 验收标准 | 验证方式 |
|---|---------|---------|
| 3.1 | 定义明确的 Staff Software Engineer 角色 | 提示词中包含角色描述 |
| 3.2 | 输出严格 6 章节 Markdown 结构 | 包含全部 6 个 `##` 标题 |
| 3.3 | Bug/Performance/Security 建议包含严重级别 | 包含 🔴 🟠 🟡 标签 |
| 3.4 | 每条建议包含文件路径和行号 | 格式为 `file:line` |
| 3.5 | 包含误报降低策略 | 明确的 Do NOT / Never 规则 |
| 3.6 | 包含语气指导（问题优先于命令） | "questions over commands" |
| 3.7 | 安全建议映射 CWE 编号 | 包含 CWE-79, CWE-89 等 |
| 3.8 | 提供完整输出示例 | 示例覆盖全部 6 个章节 |

---

## F4：LLM Service 层

**模块**: `backend/app/services/llm/`

**功能描述**: 抽象 LLM 服务接口，支持 DeepSeek / OpenAI / Qwen 切换。

### 输入

```python
service = get_llm_service()  # 从 settings.LLM_PROVIDER 自动选择
result = await service.review_pr(
    pr_title="Fix login redirect",
    pr_description="Updated callback URL",
    diff="diff --git a/src/auth.py...",
    language="zh",
)
```

### 预期输出

```python
result.raw_markdown         # "## 📋 PR Summary\n\n..."
result.summary              # "Clean fix for login redirect"
result.bug_suggestions      # "1. src/auth.py:42..."
result.security_suggestions # "🔴 Critical — ..."
result.input_tokens         # 450
result.output_tokens        # 180
result.model                # "deepseek-chat"
result.error                # None (成功时)
```

### 验收标准

| # | 验收标准 | 验证方式 |
|---|---------|---------|
| 4.1 | `BaseLLMService` 是抽象类，不可直接实例化 | `TypeError` |
| 4.2 | `DeepSeekService` 实现 `review_pr()` 和 `chat_completion()` | mock API 调用 |
| 4.3 | `OpenAIService` 实现相同接口 | mock API 调用 |
| 4.4 | `QwenService` 实现相同接口 | mock API 调用 |
| 4.5 | `get_llm_service()` 返回基类类型 | `isinstance(result, BaseLLMService)` |
| 4.6 | `get_llm_service(LLMProvider.OPENAI)` 返回 OpenAI | provider_name == "openai" |
| 4.7 | `get_llm_service()` 支持 kwargs 覆写构造参数 | `api_key="sk-test"` |
| 4.8 | API 成功 → `LLMReviewResponse` 所有字段正确填充 | mock 200 |
| 4.9 | API 失败 → `LLMReviewResponse.error` 包含错误信息 | mock Exception |
| 4.10 | 401 认证失败 → `LLMAPIError` | mock 401 |
| 4.11 | 429 限流 → 自动重试（指数退避） | mock 429 → 重试日志 |
| 4.12 | Prompt 构造器加载 `pr_review_agent.md` 作为 system prompt | 文件读取，含 fallback |
| 4.13 | diff 超出 `MAX_DIFF_SIZE_BYTES` 时自动截断 | 600KB diff → 截断日志 |
| 4.14 | `build_review_prompt(language="en")` 输出英文提示 | 验证 user prompt |
| 4.15 | `get_provider_names()` 返回已注册的 provider 列表 | 包含 deepseek/openai/qwen |
| 4.16 | `LLMReviewResponse.is_complete` 反映字段完整性 | summary+changed_modules+risks 为空时 False |

---

## F5：POST /api/v1/review 后端接口

**模块**: `backend/app/api/v1/review.py`

**功能描述**: 同步 PR 审核端点 — 输入 PR URL，返回 Markdown 审核报告。

### 输入

```json
POST /api/v1/review
Content-Type: application/json

{
  "pr_url": "https://github.com/langchain-ai/langgraph/pull/123",
  "language": "zh"
}
```

### 预期输出

```json
HTTP 200
Content-Type: application/json

{
  "pr_url": "https://github.com/langchain-ai/langgraph/pull/123",
  "owner": "langchain-ai",
  "repo": "langgraph",
  "pull_number": 123,
  "pr_title": "Fix login redirect",
  "report": "## 📋 PR Summary\n\n...",
  "input_tokens": 450,
  "output_tokens": 180,
  "model": "deepseek-chat"
}
```

### 验收标准

| # | 验收标准 | 验证方式 |
|---|---------|---------|
| 5.1 | 合法 PR URL → 200 + 完整 JSON 响应 | 端到端 mock 测试 |
| 5.2 | 响应包含 report（Markdown 字符串） | `"report" in response` |
| 5.3 | 响应包含 token 消耗和模型名 | `input_tokens`, `output_tokens`, `model` |
| 5.4 | language="en" 选项正常传递 | mock 验证参数 |
| 5.5 | 非法 URL → 422 | `{"pr_url": "not-a-url"}` → 422 |
| 5.6 | PR 不存在 → 404 | mock `PRNotFoundError` |
| 5.7 | GitHub API 错误 → 502 | mock `GitHubAPIError` |
| 5.8 | LLM 调用异常 → 502 | mock Exception |
| 5.9 | LLM 返回 error → 502 | mock error 字段 |
| 5.10 | `POST /api/v1/review/raw` 返回纯 Markdown | `Content-Type: text/markdown` |
| 5.11 | raw 端点含 `X-Review-Model` 和 `X-Review-Tokens` headers | 验证响应头 |
| 5.12 | 请求 ID 贯穿日志（request_id） | 日志中包含 request_id |

---

## F6：前端审核流程

**模块**: `frontend/src/components/SubmitPRForm.tsx` + `frontend/src/app/review/result/page.tsx` + `frontend/src/components/MarkdownReport.tsx`

**功能描述**: 用户输入 PR URL → 调用后端 → 展示 Markdown 审核报告。

### 输入

```text
https://github.com/langchain-ai/langgraph/pull/123
```

### 预期输出

网页展示 6 个卡片章节：

```
┌────────────────────────────────────────────┐
│  📋 PR Summary                              │
│  Clean fix for login redirect...            │
├────────────────────────────────────────────┤
│  🔧 Changed Modules                         │
│  • src/auth/login.ts — OAuth callback       │
├────────────────────────────────────────────┤
│  ⚠️ Potential Risks                         │
│  None identified.                           │
├────────────────────────────────────────────┤
│  🐛 Bug Suggestions                         │
│  🔴 Critical: Missing null check            │
├────────────────────────────────────────────┤
│  ⚡ Performance Suggestions                 │
│  🟠 Major: N+1 query in loop               │
├────────────────────────────────────────────┤
│  🔒 Security Suggestions                    │
│  🔴 Critical: Hardcoded secret              │
└────────────────────────────────────────────┘
```

### 验收标准

| # | 验收标准 | 验证方式 |
|---|---------|---------|
| 6.1 | PR URL 输入框显示 placeholder 和提交按钮 | 首页渲染检查 |
| 6.2 | 前端 URL 格式校验（提交前） | 非法 URL 即时红色错误 |
| 6.3 | 提交后显示加载状态 "分析中..." | loading spinner |
| 6.4 | 提交后调用 `POST /api/v1/review` | 网络请求验证 |
| 6.5 | 成功后跳转 `/review/result?data=...` | router.push 验证 |
| 6.6 | 结果页显示 PR 标题和仓库链接 | 页面渲染检查 |
| 6.7 | 结果页显示模型名和 Token 消耗 | 页面渲染检查 |
| 6.8 | Markdown 报告按章节分割为独立卡片 | 6 个卡片渲染 |
| 6.9 | 代码块被渲染为 `<pre><code>` | 语法高亮区域 |
| 6.10 | 列表项渲染为 bullet points | `- ` 前缀行正确显示 |
| 6.11 | 无数据时显示空态提示 | 缺少 data 参数 → 提示信息 |
| 6.12 | API 错误显示错误提示 | mock 422/502 → 用户可见错误 |
| 6.13 | "在 GitHub 查看" 链接正确跳转 | target="_blank" + 正确 URL |

---

## 版本记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| v0.1 | 2025-01-15 | 初稿 — F1~F6 全部验收标准 | AI PR Review Team |
