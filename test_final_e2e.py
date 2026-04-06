"""Final comprehensive E2E test through Vite proxy (as browser would see it)."""
import requests
import time
import json

BASE = "http://localhost:5174"
passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        failed += 1
        print(f"  FAIL  {name}: {e}")

# 1. Health check (Dashboard)
def t_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
test("Health check /health", t_health)

# 2. System health (Overview)
def t_sys_health():
    r = requests.get(f"{BASE}/api/system/health", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert "cpu" in d and "memory" in d
test("System health /api/system/health", t_sys_health)

# 3. System config (Overview & Settings)
def t_sys_config():
    r = requests.get(f"{BASE}/api/system/config", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert len(d["pumps"]) > 0
test("System config", t_sys_config)

# 4. System status (Overview)
def t_sys_status():
    r = requests.get(f"{BASE}/api/system/status", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert "autohyseeker" in d
test("System status", t_sys_status)

# 5. Experiment statistics (Overview)
def t_stats():
    r = requests.get(f"{BASE}/api/experiments/statistics", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert "totalExperiments" in d
    assert "successRate" in d
test("Experiment statistics", t_stats)

# 6. Recent experiments (Overview)
def t_recent():
    r = requests.get(f"{BASE}/api/experiments/recent?limit=8", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert "experiments" in d
    assert "total" in d
test("Recent experiments", t_recent)

# 7. Activities (Overview)
def t_activities():
    r = requests.get(f"{BASE}/api/system/activities?limit=10", timeout=5)
    assert r.status_code == 200
test("System activities", t_activities)

# 8. Experiments list (Experiments page)
def t_exp_list():
    r = requests.get(f"{BASE}/api/experiments", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d, list)
test("Experiments list", t_exp_list)

# 9. Create experiment (ExperimentCreateDialog)
exp_id_holder = [None]
def t_create():
    payload = {
        "name": "Final E2E Validation",
        "description": "Testing full product flow",
        "steps": [
            {"type": "dilution", "params": {"target_concentration": 0.5, "volume_ml": 10}},
            {"type": "measurement", "params": {"technique": "CV", "scan_rate": 0.1}},
        ],
        "tags": ["operator:test", "e2e"],
    }
    r = requests.post(f"{BASE}/api/experiments/create", json=payload, timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert "exp_id" in d
    assert d["status"] == "created"
    exp_id_holder[0] = d["exp_id"]
test("Create experiment", t_create)

# 10. Get experiment detail (ExperimentDetail page)
def t_detail():
    eid = exp_id_holder[0]
    r = requests.get(f"{BASE}/api/experiments/detail/{eid}", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["exp_id"] == eid
    assert d["name"] == "Final E2E Validation"
    assert len(d["steps"]) == 2
test("Experiment detail", t_detail)

# 11. Execute experiment
def t_execute():
    eid = exp_id_holder[0]
    r = requests.post(f"{BASE}/api/experiments/detail/{eid}/execute", json={"source": "local"}, timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "started"
test("Execute experiment", t_execute)

# 12. Poll progress until done
def t_progress():
    eid = exp_id_holder[0]
    for _ in range(20):
        time.sleep(1)
        r = requests.get(f"{BASE}/api/experiments/detail/{eid}/progress", timeout=5)
        assert r.status_code == 200
        d = r.json()
        if d["status"] in ("completed", "stopped", "failed"):
            assert d["progress_percent"] == 100 or d["status"] in ("stopped", "failed")
            return
    raise TimeoutError("Experiment did not complete in 20s")
test("Progress polling to completion", t_progress)

# 13. Get logs
def t_logs():
    eid = exp_id_holder[0]
    r = requests.get(f"{BASE}/api/experiments/detail/{eid}/logs", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert "logs" in d
    assert len(d["logs"]) > 0
test("Experiment logs", t_logs)

# 14. Verify final detail
def t_final():
    eid = exp_id_holder[0]
    r = requests.get(f"{BASE}/api/experiments/detail/{eid}", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "completed"
    assert len(d["step_progress"]) == 2
test("Final detail verification", t_final)

# 15. Config reload
def t_config_reload():
    r = requests.post(f"{BASE}/api/system/config/reload", timeout=5)
    assert r.status_code == 200
test("Config reload", t_config_reload)

# 16. Create + Stop experiment
def t_stop():
    payload = {
        "name": "Stop Test",
        "steps": [
            {"type": "dilution", "params": {"target_concentration": 0.1, "volume_ml": 50}},
            {"type": "measurement", "params": {"technique": "EIS", "duration": 60}},
            {"type": "flush", "params": {"volume_ml": 100}},
        ],
    }
    r = requests.post(f"{BASE}/api/experiments/create", json=payload, timeout=5)
    eid = r.json()["exp_id"]
    r = requests.post(f"{BASE}/api/experiments/detail/{eid}/execute", json={"source": "local"}, timeout=5)
    assert r.json()["status"] == "started"
    time.sleep(2)
    r = requests.post(f"{BASE}/api/experiments/detail/{eid}/stop", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] in ("stopping", "stopped")
    # Wait for async transition to "stopped"
    for _ in range(10):
        time.sleep(0.5)
        r = requests.get(f"{BASE}/api/experiments/detail/{eid}/progress", timeout=5)
        p = r.json()
        if p["status"] == "stopped":
            return
    raise TimeoutError("Experiment did not stop within 5s")
test("Stop running experiment", t_stop)

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
if failed == 0:
    print("ALL TESTS PASSED - Product ready!")
else:
    print(f"WARNING: {failed} test(s) failed")
