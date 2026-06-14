"""
Golden Dataset — 硬编码密钥

构造：数据库密码、API密钥、JWT Secret 硬编码在源代码中。
"""
from __future__ import annotations

ID = "SEC-003"
CATEGORY = "security"
SEVERITY = "critical"
CWE = "CWE-312"
DESCRIPTION = "敏感信息硬编码在源代码中"

CODE = """
import os
from flask import Flask

app = Flask(__name__)
app.config["SECRET_KEY"] = "my-super-secret-key-12345"
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:password123@localhost:3306/prod"

def call_external_api():
    api_key = "sk-live-abcdefghijklmnopqrstuvwxyz123456"
    headers = {"Authorization": f"Bearer {api_key}"}
    return requests.post("https://api.example.com/payments", headers=headers)
""".strip()

EXPECTED_FINDINGS = [
    {
        "description": "SECRET_KEY 硬编码在源代码中",
        "severity": "critical",
        "cwe": "CWE-312",
    },
    {
        "description": "数据库密码硬编码在连接字符串中",
        "severity": "critical",
        "cwe": "CWE-312",
    },
    {
        "description": "API 密钥硬编码在源代码中",
        "severity": "critical",
        "cwe": "CWE-312",
    },
    {
        "description": "生产环境凭据不应出现在代码仓库中",
        "severity": "major",
        "cwe": "CWE-312",
    },
]

REFERENCE_FIX = """
import os
from flask import Flask

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

def call_external_api():
    api_key = os.getenv("PAYMENT_API_KEY")
    if not api_key:
        raise ValueError("PAYMENT_API_KEY is not set")
    headers = {"Authorization": f"Bearer {api_key}"}
    return requests.post("https://api.example.com/payments", headers=headers)
""".strip()

DIFF = """+app = Flask(__name__)
+app.config["SECRET_KEY"] = "my-super-secret-key-12345"
+app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:password123@localhost:3306/prod"
+
+def call_external_api():
+    api_key = "sk-live-abcdefghijklmnopqrstuvwxyz123456"
+    headers = {"Authorization": f"Bearer {api_key}"}
+    return requests.post("https://api.example.com/payments", headers=headers)
+"""
