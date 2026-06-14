"""
Golden Dataset — 无界数组增长

构造：循环中不断向列表追加元素，无上限控制。
"""
from __future__ import annotations

ID = "PERF-002"
CATEGORY = "performance"
SEVERITY = "major"
DESCRIPTION = "无界数组增长可能导致内存耗尽"

CODE = """
def collect_all_versions(package_name: str) -> list[str]:
    versions = []
    page = 1
    while True:
        data = api.get_versions(package_name, page=page)
        versions.extend(data["versions"])
        if not data["has_more"]:
            break
        page += 1
    return versions

def read_logs(file_path: str) -> list[str]:
    all_lines = []
    with open(file_path) as f:
        for line in f:
            all_lines.append(line)
    return all_lines[::-1]
""".strip()

EXPECTED_FINDINGS = [
    {
        "description": "无限循环 + extend 可能导致内存耗尽",
        "severity": "major",
    },
    {
        "description": "读取整个文件到内存后再反转，大文件时内存翻倍",
        "severity": "major",
    },
    {
        "description": "建议使用流式处理或分页限制",
        "severity": "major",
    },
]

REFERENCE_FIX = """
def collect_all_versions(package_name: str, max_pages: int = 100) -> list[str]:
    versions = []
    page = 1
    while page <= max_pages:
        data = api.get_versions(package_name, page=page)
        versions.extend(data["versions"])
        if not data["has_more"]:
            break
        page += 1
    return versions

def read_logs(file_path: str) -> list[str]:
    # 使用 collections.deque 限制内存占用
    from collections import deque
    last_n = deque(maxlen=1000)
    with open(file_path) as f:
        for line in f:
            last_n.append(line.rstrip())
    return list(last_n)[::-1]
""".strip()

DIFF = """+def collect_all_versions(package_name: str) -> list[str]:
+    versions = []
+    page = 1
+    while True:
+        data = api.get_versions(package_name, page=page)
+        versions.extend(data["versions"])
+        if not data["has_more"]:
+            break
+        page += 1
+    return versions
+
+def read_logs(file_path: str) -> list[str]:
+    all_lines = []
+    with open(file_path) as f:
+        for line in f:
+            all_lines.append(line)
+    return all_lines[::-1]
+"""
