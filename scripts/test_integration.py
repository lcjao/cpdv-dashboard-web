#!/usr/bin/env python3
"""CPDV Dashboard 前后端联动测试脚本

用法:
    python scripts/test_integration.py [--base-url BASE_URL]

默认:
    - Backend: http://127.0.0.1:8765
    - Frontend: http://localhost:5173
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def test_endpoint(url, method="GET", body=None, timeout=10):
    try:
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except Exception as e:
        return 0, str(e)[:200]


def format_result(name, status, data):
    icon = "OK" if status == 200 else "FAIL"
    details = ""
    if status == 200 and data:
        if isinstance(data, dict):
            keys = list(data.keys())[:3]
            details = f" -> {keys}"
        elif isinstance(data, list):
            details = f" -> {len(data)} items"
    return f"{icon} {name}: {status}{details}"


def main():
    parser = argparse.ArgumentParser(description="Test CPDV dashboard integration")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765", help="Backend URL")
    parser.add_argument("--frontend-url", default="http://localhost:5173", help="Frontend URL")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    print("=" * 60)
    print("CPDV Dashboard Integration Test")
    print("=" * 60)
    print(f"Backend:  {base}")
    print()

    tests = [
        ("Backend Root", "GET", f"{base}/"),
        ("AI Commands Meta", "GET", f"{base}/api/ai/commands/meta"),
        ("AI pipeline.list", "POST", f"{base}/api/ai/command", {"jsonrpc": "2.0", "id": "t1", "method": "pipeline.list", "params": {}}),
        ("AI data.query", "POST", f"{base}/api/ai/command", {"jsonrpc": "2.0", "id": "t2", "method": "data.query", "params": {"artifact": "dashboard_summary"}}),
        ("AI dashboard.sync", "POST", f"{base}/api/ai/command", {"jsonrpc": "2.0", "id": "t3", "method": "dashboard.sync", "params": {}}),
        ("Algorithm Libraries", "GET", f"{base}/api/algorithm/libraries"),
        ("Algorithm Topology", "GET", f"{base}/api/algorithm/topology"),
        ("Algorithm Symbols", "GET", f"{base}/api/algorithm/symbols?q=test"),
        ("Algorithm Timeline", "GET", f"{base}/api/algorithm/timeline"),
        ("Algorithm Git Repos", "GET", f"{base}/api/algorithm/git/repos"),
        ("Dashboard Data", "GET", f"{base}/api/dashboard"),
        ("Bridges", "GET", f"{base}/api/bridges"),
    ]

    passed = failed = 0
    for t in tests:
        name, method, url = t[0], t[1], t[2]
        body = t[3] if len(t) > 3 else None
        status, data = test_endpoint(url, method, body)
        print(format_result(name, status, data))
        (passed if status == 200 else failed) and None or None
        if status == 200:
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"Result: {passed}/{passed+failed} endpoints working")
    if failed > 0:
        print(f"WARNING: {failed} endpoint(s) failed")
        sys.exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    main()
