# Eval Case 003: N+1 查询

**类别**: Performance  
**严重级别**: 🟠 Major  
**文件**: `src/services/order_service.py`  

---

## Diff

```diff
+from app.models import User, Order
+
+def get_user_orders(user_ids: list[int]) -> dict:
+    result = {}
+    for uid in user_ids:
+        user = db.query(User).filter(User.id == uid).first()
+        orders = db.query(Order).filter(Order.user_id == uid).all()
+        result[user.name] = [o.total for o in orders]
+    return result
+
+
+def get_recent_orders(days: int = 7) -> list:
+    all_orders = db.query(Order).all()
+    recent = []
+    for order in all_orders:
+        if order.created_at > datetime.now() - timedelta(days=days):
+            recent.append(order)
+    return recent
```

---

## 预期发现

| # | 预期问题 | 严重级别 | 文件 | 行号 |
|---|---------|---------|------|------|
| 1 | 循环内执行 SQL 查询（N+1 问题）：每次循环都查 User 和 Order 表 | 🟠 Major | `src/services/order_service.py` | 5-7 |
| 2 | 建议使用 `IN` 查询或 JOIN 替代循环查询 | 🟠 Major | `src/services/order_service.py` | 5-7 |
| 3 | `get_recent_orders` 全表查询后过滤，应在数据库层用 WHERE 过滤 | 🟡 Minor | `src/services/order_service.py` | 13-14 |

---

## 通过条件

- [ ] AI 发现 N+1 查询问题
- [ ] AI 建议使用批量查询（IN / JOIN）
- [ ] AI 指出全表查询后过滤的效率问题
- [ ] 给出性能改进建议（如 `db.query(Order).filter(Order.user_id.in_(user_ids))`）

---

## 参考修复

```python
def get_user_orders(user_ids: list[int]) -> dict:
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}
    orders = db.query(Order).filter(Order.user_id.in_(user_ids)).all()
    result = {}
    for order in orders:
        user = user_map.get(order.user_id)
        if user:
            result.setdefault(user.name, []).append(order.total)
    return result


def get_recent_orders(days: int = 7) -> list:
    cutoff = datetime.now() - timedelta(days=days)
    return db.query(Order).filter(Order.created_at > cutoff).all()
```
