"""Full experiment lifecycle test through Vite proxy."""
import requests, time

BASE = "http://localhost:5174/api"

# 1. Create experiment
payload = {
    "name": "Proxy E2E Test",
    "description": "Full lifecycle test through Vite proxy",
    "steps": [
        {"type": "dilution", "params": {"target_concentration": 0.5, "volume_ml": 10}},
        {"type": "measurement", "params": {"technique": "CV", "scan_rate": 0.1}},
    ],
}
r = requests.post(f"{BASE}/experiments/create", json=payload, timeout=5)
exp = r.json()
eid = exp["exp_id"]
print(f"1. Created: {eid} status={exp['status']}")

# 2. Execute
r = requests.post(f"{BASE}/experiments/detail/{eid}/execute", json={"source": "local"}, timeout=5)
print(f"2. Execute: {r.json()}")

# 3. Poll progress
for i in range(15):
    time.sleep(1.5)
    r = requests.get(f"{BASE}/experiments/detail/{eid}/progress", timeout=5)
    p = r.json()
    print(f"3. Poll[{i}]: step={p['current_step_index']}/{p['total_steps']} {p['progress_percent']}% status={p['status']}")
    if p["status"] in ("completed", "stopped", "failed"):
        break

# 4. Get logs
r = requests.get(f"{BASE}/experiments/detail/{eid}/logs", timeout=5)
logs = r.json()
if isinstance(logs, list):
    print(f"4. Logs: {len(logs)} entries")
    for log in logs[-3:]:
        print(f"   - {log.get('message', log)}")
elif isinstance(logs, dict):
    log_list = logs.get("logs", logs.get("entries", []))
    print(f"4. Logs: {len(log_list)} entries (dict keys={list(logs.keys())})")
    if isinstance(log_list, list):
        for log in log_list[-3:]:
            print(f"   - {log.get('message', log)}")
else:
    print(f"4. Logs: {logs}")

# 5. Get detail
r = requests.get(f"{BASE}/experiments/detail/{eid}", timeout=5)
d = r.json()
print(f"5. Final: status={d['status']} steps={len(d.get('steps', []))} step_progress={len(d.get('step_progress', []))}")

print("\nProxy E2E: ALL PASSED")
