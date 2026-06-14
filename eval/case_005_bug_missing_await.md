# Eval Case 005: 缺少 await / 未处理 Promise

**类别**: Bug  
**严重级别**: 🔴 Critical  
**文件**: `src/services/payment.py`  

---

## Diff

```diff
+import asyncio
+from app.gateway import PaymentGateway
+
+
+async def process_payment(order_id: str) -> dict:
+    gateway = PaymentGateway()
+    result = gateway.charge(order_id, 100)
+    send_receipt(order_id)
+    return {"status": "success", "result": result}
+
+
+async def batch_refund(order_ids: list[str]) -> list:
+    tasks = []
+    for oid in order_ids:
+        tasks.append(refund_order(oid))
+    return tasks
```

---

## 预期发现

| # | 预期问题 | 严重级别 | 文件 | 行号 |
|---|---------|---------|------|------|
| 1 | `gateway.charge()` 是协程但未 `await`，Promise 不执行 | 🔴 Critical | `src/services/payment.py` | 7 |
| 2 | `send_receipt()` 未 `await`，邮件不会发送 | 🔴 Critical | `src/services/payment.py` | 8 |
| 3 | `batch_refund` 返回 `tasks` 列表而非 `await asyncio.gather(tasks)` 的结果 | 🟠 Major | `src/services/payment.py` | 15 |

---

## 通过条件

- [ ] AI 发现 `gateway.charge()` 缺少 `await`
- [ ] AI 发现 `send_receipt()` 缺少 `await`
- [ ] AI 指出 `batch_refund` 应使用 `asyncio.gather()`
- [ ] 严重级别分配正确

---

## 参考修复

```python
async def process_payment(order_id: str) -> dict:
    gateway = PaymentGateway()
    result = await gateway.charge(order_id, 100)
    await send_receipt(order_id)
    return {"status": "success", "result": result}


async def batch_refund(order_ids: list[str]) -> list:
    tasks = [refund_order(oid) for oid in order_ids]
    return await asyncio.gather(*tasks)
```
