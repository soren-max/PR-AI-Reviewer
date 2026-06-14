# Eval Case 001: 硬编码密码

**类别**: Security  
**严重级别**: 🔴 Critical  
**文件**: `src/config/database.py`  

---

## Diff

```diff
+import os
+
+def get_db_connection():
+    password = "super-secret-123456"
+    return connect(
+        host="localhost",
+        user="admin",
+        password=password,
+        database="production"
+    )
```

---

## 预期发现

| # | 预期问题 | 严重级别 | 文件 | 行号 |
|---|---------|---------|------|------|
| 1 | 硬编码数据库密码 | 🔴 Critical | `src/config/database.py` | 4 |
| 2 | 建议使用环境变量或密钥管理服务替代 | 🟠 Major | `src/config/database.py` | 4 |
| 3 | 密码泄露可能导致数据库被攻破 | 🔴 Critical | `src/config/database.py` | 4 |

---

## 通过条件

- [ ] AI 发现硬编码密码问题
- [ ] 严重级别标记为 Critical 或 Major
- [ ] 给出改进建议（如 `os.getenv("DB_PASSWORD")`）
- [ ] 包含文件路径和行号

---

## 参考修复

```python
def get_db_connection():
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise ValueError("DB_PASSWORD environment variable is not set")
    return connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "admin"),
        password=password,
        database=os.getenv("DB_NAME", "production")
    )
```
