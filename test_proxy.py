import requests
# Test proxy through frontend dev server
try:
    r = requests.get("http://127.0.0.1:5174/api/system/config", timeout=5)
    print(f"Proxy test via 5174: status={r.status_code}")
    if r.status_code == 200:
        cfg = r.json()
        print(f"  Pumps: {len(cfg.get('pumps', []))}")
    else:
        print(f"  Body: {r.text[:200]}")
except Exception as e:
    print(f"Proxy test failed (may need vite restart): {e}")

# Also test direct backend
try:
    r = requests.get("http://127.0.0.1:8200/api/system/config", timeout=5)
    print(f"Direct backend test: status={r.status_code}, pumps={len(r.json().get('pumps', []))}")
except Exception as e:
    print(f"Direct backend test failed: {e}")
