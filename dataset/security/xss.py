"""
Golden Dataset — XSS (Cross-Site Scripting)

构造：用户输入直接渲染到 HTML 页面。
"""
from __future__ import annotations

ID = "SEC-002"
CATEGORY = "security"
SEVERITY = "critical"
CWE = "CWE-79"
DESCRIPTION = "用户输入未转义直接渲染到 HTML 页面"

CODE = """
@app.route("/comment")
def submit_comment():
    content = request.form.get("content")
    html = f"<div class='comment'>{content}</div>"
    return render_template_string(html)

@app.route("/search")
def search():
    query = request.args.get("q", "")
    results = db.search(query)
    html = "<ul>"
    for r in results:
        html += f"<li>{r.title}</li>"
    html += "</ul>"
    return render_template_string(html)
""".strip()

EXPECTED_FINDINGS = [
    {
        "description": "用户输入直接拼接 HTML 未转义",
        "severity": "critical",
        "cwe": "CWE-79",
    },
    {
        "description": "render_template_string 中的注入可能导致 XSS",
        "severity": "critical",
        "cwe": "CWE-79",
    },
    {
        "description": "搜索结果渲染中循环拼接 HTML 同样存在 XSS 风险",
        "severity": "critical",
        "cwe": "CWE-79",
    },
]

REFERENCE_FIX = """
from markupsafe import escape

@app.route("/comment")
def submit_comment():
    content = request.form.get("content")
    return render_template_string(
        "<div class='comment'>{{ content }}</div>",
        content=escape(content),
    )

@app.route("/search")
def search():
    query = request.args.get("q", "")
    results = db.search(query)
    return render_template_string(
        "<ul>{% for r in results %}<li>{{ r.title }}</li>{% endfor %}</ul>",
        results=results,
    )
""".strip()

DIFF = """+@app.route("/comment")
+def submit_comment():
+    content = request.form.get("content")
+    html = f"<div class='comment'>{content}</div>"
+    return render_template_string(html)
+
+@app.route("/search")
+def search():
+    query = request.args.get("q", "")
+    results = db.search(query)
+    html = "<ul>"
+    for r in results:
+        html += f"<li>{r.title}</li>"
+    html += "</ul>"
+    return render_template_string(html)
+"""
