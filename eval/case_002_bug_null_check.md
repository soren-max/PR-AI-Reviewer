# Eval Case 002: 缺少空值检查

**类别**: Bug  
**严重级别**: 🟠 Major  
**文件**: `src/api/users.py`  

---

## Diff

```diff
+from typing import Optional
+
+def get_user_name(user_id: Optional[int]) -> str:
+    user = fetch_user_from_db(user_id)
+    return user.name
+
+
+def send_notification(users: list) -> None:
+    for user in users:
+        email = user.email
+        send_email(email, "Welcome!")
```

---

## 预期发现

| # | 预期问题 | 严重级别 | 文件 | 行号 |
|---|---------|---------|------|------|
| 1 | `user_id` 为 `None` 时 `fetch_user_from_db` 可能返回 None，导致 `None.name` 崩溃 | 🟠 Major | `src/api/users.py` | 4 |
| 2 | `user.email` 未判空，`email` 为 None 时可能异常 | 🟡 Minor | `src/api/users.py` | 10 |
| 3 | 缺少类型守卫或提前返回 | 🟠 Major | `src/api/users.py` | 3-5 |

---

## 通过条件

- [ ] AI 发现 `user_id` 为 None 时可能崩溃
- [ ] AI 发现 `user.email` 缺少判空
- [ ] 给出添加 None 检查或提前返回的建议
- [ ] 严重级别均为 Major/Minor 的正确分配

---

## 参考修复

```python
def get_user_name(user_id: Optional[int]) -> str:
    if user_id is None:
        raise ValueError("user_id must not be None")
    user = fetch_user_from_db(user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")
    return user.name


def send_notification(users: list) -> None:
    for user in users:
        if not user.email:
            continue
        send_email(user.email, "Welcome!")
```
