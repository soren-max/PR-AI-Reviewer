"""
Golden Dataset — SQL Injection

构造：用户输入直接拼接 SQL 查询字符串。
"""
from __future__ import annotations

ID = "SEC-001"
CATEGORY = "security"
SEVERITY = "critical"
CWE = "CWE-89"
DESCRIPTION = "字符串拼接 SQL 查询导致注入漏洞"

# 包含缺陷的代码
CODE = """
def get_user_by_id(user_input: str):
    query = f"SELECT * FROM users WHERE id = '{user_input}'"
    cursor.execute(query)
    return cursor.fetchone()

def search_products(keyword: str):
    query = f"SELECT * FROM products WHERE name LIKE '%{keyword}%'"
    cursor.execute(query)
    return cursor.fetchall()
""".strip()

# 预期发现的缺陷
EXPECTED_FINDINGS = [
    {
        "description": "用户输入直接拼接 SQL 查询",
        "severity": "critical",
        "cwe": "CWE-89",
    },
    {
        "description": "LIKE 子句中的字符串拼接同样存在注入风险",
        "severity": "critical",
        "cwe": "CWE-89",
    },
]

# 参考修复
REFERENCE_FIX = """
def get_user_by_id(user_input: str):
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_input,))
    return cursor.fetchone()

def search_products(keyword: str):
    query = "SELECT * FROM products WHERE name LIKE ?"
    cursor.execute(query, (f"%{keyword}%",))
    return cursor.fetchall()
""".strip()

# Diff 格式（方便直接发给 LLM）
DIFF = """+def get_user_by_id(user_input: str):
+    query = f"SELECT * FROM users WHERE id = '{user_input}'"
+    cursor.execute(query)
+    return cursor.fetchone()
+
+def search_products(keyword: str):
+    query = f"SELECT * FROM products WHERE name LIKE '%{keyword}%'"
+    cursor.execute(query)
+    return cursor.fetchall()
+"""
