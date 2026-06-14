"""
Golden Dataset — 离一错误（Off-by-One）
"""
from __future__ import annotations

ID = "BUG-002"
CATEGORY = "bug"
SEVERITY = "major"
DESCRIPTION = "循环或切片中的离一错误导致少处理或多处理一项"

CODE = """
def paginate(items: list, page: int, page_size: int) -> list:
    start = page * page_size
    end = start + page_size
    return items[start:end]

def get_last_n(items: list, n: int) -> list:
    return items[-n:]

for i in range(1, len(items)):
    print(items[i])
"""

EXPECTED_FINDINGS = [
    {
        "description": "分页计算：第0页正确，但第1页从index=page_size开始跳过了第page_size项",
        "severity": "major",
    },
    {
        "description": "get_last_n 在 n=0 时返回整个列表",
        "severity": "major",
    },
]

REFERENCE_FIX = """
def paginate(items: list, page: int, page_size: int) -> list:
    start = page * page_size
    end = min(start + page_size, len(items))
    return items[start:end]

def get_last_n(items: list, n: int) -> list:
    if n <= 0:
        return []
    return items[-n:]

for i in range(len(items)):
    print(items[i])
"""

DIFF = """+def paginate(items: list, page: int, page_size: int) -> list:
+    start = page * page_size
+    end = start + page_size
+    return items[start:end]
+
+def get_last_n(items: list, n: int) -> list:
+    return items[-n:]
+
+for i in range(1, len(items)):
+    print(items[i])
+"""
