# AI PR Review — Prompt Evaluation Framework

## 为什么需要 Eval？

Prompt 的效果不能靠感觉。Eval 框架让你：

- **量化**：每次修改 prompt 后，召回率是升了还是降了
- **回归**：加了一个新规则，之前的 case 仍然通过
- **对比**：DeepSeek vs OpenAI vs Qwen，哪个表现更好
- **追踪**：每一次 prompt 版本变更都有对应的评分记录

## 目录结构

```
eval/
├── case_001_security_hardcoded_secret.md      # 🔴 硬编码密码
├── case_002_bug_null_check.md                  # 🟠 空值检查
├── case_003_performance_n_plus_one.md          # 🟠 N+1 查询
├── case_004_security_sql_injection.md          # 🔴 SQL注入
├── case_005_bug_missing_await.md               # 🔴 缺少await
├── case_006_security_xss.md                    # 🔴 XSS
├── runner.py                                   # 自动化评分脚本
└── README.md                                   # 本文档
```

## 用例格式

每个 case 是一个 Markdown 文件：

```markdown
# Eval Case 001: 硬编码密码

**类别**: Security
**严重级别**: 🔴 Critical
**文件**: `src/config/database.py`

## Diff

```diff
+password = "123456"
```

## 预期发现

| # | 预期问题 | 严重级别 | 文件 | 行号 |
|---|---------|---------|------|------|
| 1 | 硬编码密码 | 🔴 Critical | database.py | 3 |

## 通过条件

- [ ] AI 发现硬编码密码问题
- [ ] 严重级别标记为 Critical

## 参考修复

```python
password = os.getenv("DB_PASSWORD")
```
```

## 使用方法

### 前置条件

确保已设置环境变量（`.env`）：

```
DEEPSEEK_API_KEY=sk-...
```

### 运行全部用例

```bash
python eval/runner.py
```

### 运行单个用例

```bash
python eval/runner.py --case 001
```

### Dry-run（不调 LLM，测试 runner 本身）

```bash
python eval/runner.py --dry-run
```

### 显示完整 LLM 输出

```bash
python eval/runner.py --verbose
```

### 指定 LLM 提供商

```bash
python eval/runner.py --provider openai
```

## 评分指标

| 指标 | 说明 | 计算方式 |
|------|------|---------|
| **召回率** | 预期问题中被 AI 发现的比率 | `通过 / 总计` |
| **严重匹配率** | 被发现的预期问题中严重级别正确的比率 | `严重正确 / 总计` |
| **建议率** | 是否包含代码修复建议 | `has_suggestion` |
| **通过** | 全部预期问题都被发现 | `missed == 0` |

## 新增用例

1. 在 `eval/` 下创建 `case_XXX_name.md`
2. 按照上面的格式编写 diff 和预期发现
3. 运行 `python eval/runner.py --case XXX` 验证
4. 提交 PR

## 版本记录

| 日期 | 用例数 | 说明 |
|------|--------|------|
| 2025-01 | 6 | 初始用例：Security × 3, Bug × 2, Performance × 1 |
