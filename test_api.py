import requests
import time

results = []

def record(name, passed, detail=""):
    results.append({"name": name, "passed": passed, "detail": detail})

# ---------- Test 1: GET https://httpbin.org/get ----------
test_name = "GET /get"
try:
    start = time.time()
    resp = requests.get("https://httpbin.org/get", timeout=10)
    elapsed_ms = int((time.time() - start) * 1000)

    checks = []
    if resp.status_code != 200:
        checks.append(f"status {resp.status_code} != 200")
    ct = resp.headers.get("Content-Type", "")
    if "application/json" not in ct:
        checks.append(f"Content-Type '{ct}' missing application/json")
    body = resp.json()
    for key in ("url", "headers", "origin"):
        if key not in body:
            checks.append(f"missing key '{key}' in body")

    if checks:
        record(test_name, False, "; ".join(checks))
    else:
        record(test_name, True, f"200 OK ({elapsed_ms}ms)")
except Exception as e:
    record(test_name, False, str(e))

# ---------- Test 2: POST https://httpbin.org/post ----------
test_name = "POST /post"
payload = {"name": "test", "value": 123}
try:
    start = time.time()
    resp = requests.post("https://httpbin.org/post", json=payload, timeout=10)
    elapsed_ms = int((time.time() - start) * 1000)

    checks = []
    if resp.status_code != 200:
        checks.append(f"status {resp.status_code} != 200")
    ct = resp.headers.get("Content-Type", "")
    if "application/json" not in ct:
        checks.append(f"Content-Type '{ct}' missing application/json")
    body = resp.json()
    for key in ("json", "url", "headers"):
        if key not in body:
            checks.append(f"missing key '{key}' in body")
    if "json" in body and body["json"] != payload:
        checks.append(f"json mismatch: {body['json']} != {payload}")

    if checks:
        record(test_name, False, "; ".join(checks))
    else:
        record(test_name, True, f"200 OK ({elapsed_ms}ms)")
except Exception as e:
    record(test_name, False, str(e))

# ---------- Report ----------
print("\n=== Test Results ===")
pass_count = sum(1 for r in results if r["passed"])
fail_count = len(results) - pass_count
for r in results:
    tag = "PASS" if r["passed"] else "FAIL"
    print(f"[{tag}] {r['name']} -- {r['detail']}")
print("=" * 24)
print(f"Total: {len(results)} | Pass: {pass_count} | Fail: {fail_count}")
