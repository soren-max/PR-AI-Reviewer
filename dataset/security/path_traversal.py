"""
Golden Dataset — 路径穿越

构造：用户输入直接拼入文件路径，未做合法性校验。
"""
from __future__ import annotations

ID = "SEC-004"
CATEGORY = "security"
SEVERITY = "critical"
CWE = "CWE-22"
DESCRIPTION = "用户输入直接用于构造文件路径"

CODE = """
import os

def read_user_avatar(filename: str):
    path = f"/var/www/avatars/{filename}"
    with open(path, "rb") as f:
        return f.read()

def delete_user_file(relative_path: str):
    full_path = os.path.join("/data/user_files", relative_path)
    os.remove(full_path)
""".strip()

EXPECTED_FINDINGS = [
    {
        "description": "用户输入直接拼入文件路径，可穿越到其他目录",
        "severity": "critical",
        "cwe": "CWE-22",
    },
    {
        "description": "未校验 filename 是否包含 ../ 等路径穿越字符",
        "severity": "critical",
        "cwe": "CWE-22",
    },
    {
        "description": "os.path.join 不能防范路径穿越",
        "severity": "critical",
        "cwe": "CWE-22",
    },
]

REFERENCE_FIX = """
import os

ALLOWED_AVATAR_DIR = os.path.realpath("/var/www/avatars")

def read_user_avatar(filename: str):
    # 只允许文件名，不允许路径
    if "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename")
    path = os.path.realpath(os.path.join(ALLOWED_AVATAR_DIR, filename))
    if not path.startswith(ALLOWED_AVATAR_DIR):
        raise ValueError("Path traversal detected")
    with open(path, "rb") as f:
        return f.read()
""".strip()

DIFF = """+def read_user_avatar(filename: str):
+    path = f"/var/www/avatars/{filename}"
+    with open(path, "rb") as f:
+        return f.read()
+
+def delete_user_file(relative_path: str):
+    full_path = os.path.join("/data/user_files", relative_path)
+    os.remove(full_path)
+"""
