# Code Review Test Cases — 30 Cases

> Security × 10 | Performance × 10 | Bug × 10
> 每段代码都包含真实项目中常见的缺陷，用于验证 AI Code Review 的检测能力。

---

## Security (10 cases)

---

### SEC-01: SQL 注入

```python
def get_user(username: str):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
```

**预期发现**: 用户输入直接拼接 SQL 查询，可注入 `' OR '1'='1` 绕过认证
**风险等级**: 🔴 Critical (CWE-89)

---

### SEC-02: XSS — 未转义输出

```javascript
app.get("/search", (req, res) => {
    const query = req.query.q;
    res.send(`<div>Search results for: ${query}</div>`);
});
```

**预期发现**: 用户输入直接渲染到 HTML，可注入 `<script>alert('xss')</script>`
**风险等级**: 🔴 Critical (CWE-79)

---

### SEC-03: 硬编码密钥

```python
SECRET_KEY = "sk-live-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p"
def encrypt(data):
    return AES.new(SECRET_KEY).encrypt(data)
```

**预期发现**: 生产环境密钥硬编码在源代码中，git 泄露后全量密钥暴露
**风险等级**: 🔴 Critical (CWE-312)

---

### SEC-04: 路径穿越

```python
def read_file(filename: str):
    path = f"/var/data/{filename}"
    with open(path) as f:
        return f.read()
```

**预期发现**: 未校验 `../` 路径穿越，`filename=../../etc/passwd` 可读取任意文件
**风险等级**: 🔴 Critical (CWE-22)

---

### SEC-05: 缺失认证检查

```python
@app.route("/api/admin/delete_user")
def delete_user(user_id):
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return "deleted"
```

**预期发现**: 管理接口未做身份认证和权限校验，任何人可调用
**风险等级**: 🔴 Critical (CWE-287)

---

### SEC-06: 密码明文存储

```python
def register_user(username: str, password: str):
    db.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, password)
    )
```

**预期发现**: 密码明文存储数据库，泄露后所有用户密码暴露
**风险等级**: 🔴 Critical (CWE-312)

---

### SEC-07: CSRF 保护缺失

```python
@app.post("/api/transfer")
def transfer_money(to_account: str, amount: int):
    execute_transfer(to_account, amount)
    return "ok"
```

**预期发现**: 转账接口无 CSRF Token 校验，攻击者可构造跨站请求
**风险等级**: 🟠 Major (CWE-352)

---

### SEC-08: SSL 验证关闭

```python
import requests
requests.get("https://api.payment.com/charge", verify=False)
```

**预期发现**: SSL 证书验证关闭，中间人攻击可劫持请求
**风险等级**: 🟠 Major (CWE-295)

---

### SEC-09: SSRF

```python
@app.post("/api/fetch")
def fetch_url():
    url = request.json["url"]
    return requests.get(url).text
```

**预期发现**: 用户控制 URL 被服务器端请求，可扫描内网服务（SSRF）
**风险等级**: 🟠 Major (CWE-918)

---

### SEC-10: 敏感信息日志泄露

```python
logging.info(f"Login failed for user {username}, password={password}")
```

**预期发现**: 密码在日志中明文记录，日志系统泄露后凭据暴露
**风险等级**: 🟠 Major (CWE-200)

---

## Performance (10 cases)

---

### PERF-01: N+1 查询

```python
def get_orders_with_users(order_ids):
    result = []
    for oid in order_ids:
        order = db.query(Order).get(oid)
        user = db.query(User).get(order.user_id)
        result.append({"order": order, "user": user})
    return result
```

**预期发现**: 循环内逐条查询数据库，N 个 order 产生 2N+1 次查询
**风险等级**: 🟠 Major

---

### PERF-02: 同步 IO 在异步路径中

```python
async def handle_request():
    data = requests.get("https://api.example.com/data").json()
    return process(data)
```

**预期发现**: 异步函数中使用同步 requests.get，阻塞事件循环
**风险等级**: 🟠 Major

---

### PERF-03: 全表查询后过滤

```python
def get_recent_orders(days: int):
    all_orders = db.query(Order).all()
    return [o for o in all_orders if o.created_at > cutoff]
```

**预期发现**: 全表查询到内存再过滤，应在数据库层 WHERE 过滤
**风险等级**: 🟡 Minor

---

### PERF-04: 无界列表增长

```python
def collect_all(stream):
    items = []
    async for chunk in stream:
        items.extend(chunk)
    return items
```

**预期发现**: 无上限列表增长，大流量时内存 OOM
**风险等级**: 🟠 Major

---

### PERF-05: 循环内重复计算

```python
def process(items):
    for i in range(len(items)):
        for j in range(len(items)):
            if i != j:
                check(items[i], total := sum(item.value for item in items))
```

**预期发现**: sum() 在内层循环重复计算，O(n³)，n=1000 时耗时数秒
**风险等级**: 🟡 Minor

---

### PERF-06: 缺少数据库索引

```python
def search_by_email(email: str):
    return db.query(User).filter(User.email == email).all()
```

**预期发现**: email 字段无索引，全表扫描，千万级用户时数十秒
**风险等级**: 🟠 Major

---

### PERF-07: 大对象未释放

```python
def process_large_file(path: str):
    with open(path) as f:
        data = f.read()
    return json.loads(data)
```

**预期发现**: 超大文件全量读入内存，500MB 文件时 OOM
**风险等级**: 🟡 Minor

---

### PERF-08: 热路径中频繁分配对象

```python
def format_items(items):
    result = {}
    for item in items:
        result[item.id] = {"name": item.name, "value": item.value}
    return result
```

**预期发现**: 每循环分配新 dict，100 万 items 时 GC 压力巨大
**风险等级**: 🟡 Minor

---

### PERF-09: 深度嵌套循环

```python
def find_duplicates(list1, list2, list3):
    dupes = []
    for a in list1:
        for b in list2:
            for c in list3:
                if a == b == c:
                    dupes.append(a)
    return dupes
```

**预期发现**: O(n³) 的深度嵌套循环，每个列表 1000 项时 10 亿次迭代
**风险等级**: 🟠 Major

---

### PERF-10: 不必要的序列化

```python
def get_config():
    return json.loads(json.dumps(config_dict))
```

**预期发现**: config_dict 已是 dict，无意义的序列化再反序列化
**风险等级**: ⚪ Nit

---

## Bug (10 cases)

---

### BUG-01: 空指针 / None 解引用

```python
def get_user_email(user_id: int) -> str:
    user = database.fetch_user(user_id)
    return user.email
```

**预期发现**: fetch_user 可能返回 None，user.email 触发 AttributeError
**风险等级**: 🔴 Critical

---

### BUG-02: 缺少 await

```python
async def process_payment(order_id: str):
    gateway = PaymentGateway()
    gateway.charge(order_id, 100)
    send_receipt(order_id)
    return {"status": "success"}
```

**预期发现**: gateway.charge() 是异步方法但未 await，Promise 悬空，支付不会执行
**风险等级**: 🔴 Critical

---

### BUG-03: 除零错误

```python
def calculate_average(total: int, count: int) -> float:
    return total / count
```

**预期发现**: count 为 0 时 ZeroDivisionError，应校验或返回 0
**风险等级**: 🟠 Major

---

### BUG-04: 可变默认参数

```python
def add_item(item: str, cache: list = []) -> list:
    cache.append(item)
    return cache
```

**预期发现**: 可变默认参数在多次调用间共享状态，`add_item("a")` 后 `add_item("b")` 返回 `["a", "b"]`
**风险等级**: 🟠 Major

---

### BUG-05: 浮点数比较

```python
def is_balance_zero(balance: float) -> bool:
    return balance == 0.0
```

**预期发现**: 浮点数精度问题，`0.1 + 0.2 != 0.3`，应使用 `abs(balance) < 0.001`
**风险等级**: 🟠 Major

---

### BUG-06: 资源未关闭

```python
def process_data():
    f = open("/var/data/input.csv")
    data = f.read()
    return parse(data)
```

**预期发现**: 文件打开后未关闭，句柄泄露。应用长期运行耗尽文件描述符
**风险等级**: 🟠 Major

---

### BUG-07: 拼写错误导致逻辑错误

```python
def is_admin(user: User) -> bool:
    if user.role = "admin":
        return True
    return False
```

**预期发现**: `=` 赋值而非 `==` 比较，始终返回 True，任意用户均为管理员
**风险等级**: 🔴 Critical

---

### BUG-08: 索引错误

```python
def get_last(items: list) -> Any:
    return items[len(items)]
```

**预期发现**: `len(items)` 越界，应使用 `items[-1]` 或 `items[len(items)-1]`
**风险等级**: 🟠 Major

---

### BUG-09: 浅拷贝

```python
def duplicate_grid(grid: list[list[int]]) -> list[list[int]]:
    return list(grid)
```

**预期发现**: `list(grid)` 只做浅拷贝，内层 list 仍是引用。修改副本会影响原数据
**风险等级**: 🟡 Minor

---

### BUG-10: 类型不一致比较

```python
def find_user(uid: str):
    for user in users:
        if user["id"] == uid:
            return user
    return None
```

**预期发现**: user["id"] 是 int，uid 是 str，Python 中 `int == str` 永远 False
**风险等级**: 🟠 Major
