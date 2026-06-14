"""
Golden Dataset — 异步路径中的同步 IO

构造：在 async 函数中调用同步的 time.sleep() 和 requests.get()。
"""
from __future__ import annotations

ID = "PERF-001"
CATEGORY = "performance"
SEVERITY = "major"
DESCRIPTION = "异步路径中的同步 IO 阻塞事件循环"

CODE = """
import asyncio
import time
import requests

async def fetch_all_urls(urls: list[str]) -> list[str]:
    results = []
    for url in urls:
        resp = requests.get(url)
        results.append(resp.text)
    return results

async def process_batch(items: list[int]) -> None:
    for item in items:
        time.sleep(0.1)
        await process_item(item)
""".strip()

EXPECTED_FINDINGS = [
    {
        "description": "在 async 函数中使用同步 requests.get 阻塞事件循环",
        "severity": "major",
    },
    {
        "description": "应使用 httpx.AsyncClient 或 aiohttp 替代 requests",
        "severity": "major",
    },
    {
        "description": "在 async 函数中使用 time.sleep 阻塞事件循环",
        "severity": "major",
    },
    {
        "description": "应使用 asyncio.sleep 替代 time.sleep",
        "severity": "major",
    },
]

REFERENCE_FIX = """
import asyncio
import httpx

async def fetch_all_urls(urls: list[str]) -> list[str]:
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.text for r in responses]

async def process_batch(items: list[int]) -> None:
    for item in items:
        await asyncio.sleep(0.1)
        await process_item(item)
""".strip()

DIFF = """+async def fetch_all_urls(urls: list[str]) -> list[str]:
+    results = []
+    for url in urls:
+        resp = requests.get(url)
+        results.append(resp.text)
+    return results
+
+async def process_batch(items: list[int]) -> None:
+    for item in items:
+        time.sleep(0.1)
+        await process_item(item)
+"""
