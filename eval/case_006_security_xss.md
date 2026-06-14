# Eval Case 006: XSS 跨站脚本

**类别**: Security  
**严重级别**: 🔴 Critical  
**文件**: `src/views/comment.py`  

---

## Diff

```diff
+from flask import request, render_template_string
+from app.models import Comment
+
+
+def submit_comment():
+    content = request.form.get("content")
+    user_name = request.form.get("user_name")
+
+    comment = Comment(content=content, author=user_name)
+    db.session.add(comment)
+    db.session.commit()
+
+    html = f"<div>{user_name} said: {content}</div>"
+    return render_template_string(html)
+
+
+def search_comments(query: str):
+    results = Comment.query.filter(Comment.content.contains(query)).all()
+    html = "<ul>"
+    for r in results:
+        html += f"<li>{r.content}</li>"
+    html += "</ul>"
+    return render_template_string(html)
```

---

## 预期发现

| # | 预期问题 | 严重级别 | 文件 | 行号 |
|---|---------|---------|------|------|
| 1 | 用户输入直接拼入 HTML 未转义，存在 XSS 风险 | 🔴 Critical | `src/views/comment.py` | 12, 19 |
| 2 | `render_template_string(f"...{user_name}...")` 允许任意 JS 执行 | 🔴 Critical | `src/views/comment.py` | 13 |
| 3 | 数据库中的历史恶意内容在搜索时也会触发 XSS | 🔴 Critical | `src/views/comment.py` | 19 |
| 4 | 建议使用模板引擎的自动转义或 `escape()` 函数 | 🟠 Major | `src/views/comment.py` | 12-19 |

---

## 通过条件

- [ ] AI 发现两处 XSS 风险
- [ ] 引用 CWE-79
- [ ] 建议使用 `escape()` 或模板引擎的自动转义
- [ ] 严重级别为 Critical

---

## 参考修复

```python
from markupsafe import escape


def submit_comment():
    content = request.form.get("content")
    user_name = request.form.get("user_name")
    comment = Comment(content=content, author=user_name)
    db.session.add(comment)
    db.session.commit()
    return render_template_string(
        "<div>{{ user_name }} said: {{ content }}</div>",
        user_name=escape(user_name),
        content=escape(content),
    )


def search_comments(query: str):
    results = Comment.query.filter(Comment.content.contains(query)).all()
    return render_template_string(
        "<ul>{% for r in results %}<li>{{ r.content }}</li>{% endfor %}</ul>",
        results=results,
    )
```
