# Eval Case 004: SQL 注入

**类别**: Security  
**严重级别**: 🔴 Critical  
**文件**: `src/api/search.py`  

---

## Diff

```diff
+from app.database import execute_query
+
+
+def search_products(search_term: str) -> list:
+    query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
+    return execute_query(query)
+
+
+def get_user_profile(user_id: str) -> dict:
+    query = f"SELECT * FROM users WHERE id = '{user_id}'"
+    result = execute_query(query)
+    return result[0] if result else {}
```

---

## 预期发现

| # | 预期问题 | 严重级别 | 文件 | 行号 |
|---|---------|---------|------|------|
| 1 | 字符串拼接 SQL 导致注入风险 | 🔴 Critical | `src/api/search.py` | 5, 10 |
| 2 | `search_term` 直接拼入 LIKE 子句，可构造 `' OR '1'='1` 泄露全表 | 🔴 Critical | `src/api/search.py` | 5 |
| 3 | `user_id` 直接拼入 WHERE 子句，可注入 UNION 查询 | 🔴 Critical | `src/api/search.py` | 10 |
| 4 | 建议使用参数化查询或 ORM | 🔴 Critical | `src/api/search.py` | 5, 10 |

---

## 通过条件

- [ ] AI 发现两处 SQL 注入风险
- [ ] 严重级别均为 Critical
- [ ] 引用 CWE-89（SQL Injection）
- [ ] 给出参数化查询的修复建议

---

## 参考修复

```python
def search_products(search_term: str) -> list:
    query = "SELECT * FROM products WHERE name LIKE ?"
    return execute_query(query, (f"%{search_term}%",))


def get_user_profile(user_id: str) -> dict:
    query = "SELECT * FROM users WHERE id = ?"
    result = execute_query(query, (user_id,))
    return result[0] if result else {}
```
