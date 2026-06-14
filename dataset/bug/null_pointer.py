"""
Golden Dataset — 空指针 / None 解引用
"""
from __future__ import annotations

ID = "BUG-001"
CATEGORY = "bug"
SEVERITY = "critical"
DESCRIPTION = "未判空直接解引用会导致运行时崩溃"

CODE = """
def get_user_email(user_id: int) -> str:
    user = database.fetch_user(user_id)
    return user.email

def process_orders(customer):
    for order in customer.orders:
        ship(order)
"""

EXPECTED_FINDINGS = [
    {
        "description": "fetch_user 可能返回 None，直接取 .email 会崩溃",
        "severity": "critical",
    },
    {
        "description": "customer 参数未做类型检查和判空",
        "severity": "major",
    },
]

REFERENCE_FIX = """
def get_user_email(user_id: int) -> str:
    user = database.fetch_user(user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")
    return user.email

def process_orders(customer):
    if customer is None:
        return
    for order in customer.orders or []:
        ship(order)
"""

DIFF = """+def get_user_email(user_id: int) -> str:
+    user = database.fetch_user(user_id)
+    return user.email
+
+def process_orders(customer):
+    for order in customer.orders:
+        ship(order)
+"""
