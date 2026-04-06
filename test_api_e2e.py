"""End-to-end API integration test for AutoHySeeker experiment system."""
import requests
import json
import time
import os

BASE = "http://127.0.0.1:8200"
errors = []
passed = []

def check(name, fn):
    try:
        fn()
        passed.append(name)
    except Exception as e:
        print(f"  FAIL: {e}")
        errors.append((name, str(e)))

exp_id = None
exp2_id = None

# 1. Health
print("=== 1. Health Check ===")
def test_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200, f"status={r.status_code}"
    print(f"  OK: {r.json()}")
check("health", test_health)

# 2. System Config
print("=== 2. System Config ===")
def test_config():
    r = requests.get(f"{BASE}/api/system/config", timeout=5)
    assert r.status_code == 200, f"status={r.status_code}"
    cfg = r.json()
    pumps = cfg.get("pumps", [])
    dilution = cfg.get("dilution_channels", {})
    flush_ch = cfg.get("flush_channels", {})
    print(f"  OK: {len(pumps)} pumps, {len(dilution)} dilution ch, {len(flush_ch)} flush ch")
    assert len(pumps) > 0, "No pumps in config!"
check("system_config", test_config)

# 3. System Status
print("=== 3. System Status ===")
def test_sys_status():
    r = requests.get(f"{BASE}/api/system/status", timeout=5)
    assert r.status_code == 200
    print(f"  OK: {r.json()}")
check("system_status", test_sys_status)

# 4. Statistics
print("=== 4. Experiment Statistics ===")
def test_stats():
    r = requests.get(f"{BASE}/api/experiments/statistics", timeout=5)
    assert r.status_code == 200
    print(f"  OK: {r.json()}")
check("exp_statistics", test_stats)

# 5. Create Experiment
print("=== 5. Create Experiment ===")
def test_create():
    global exp_id
    payload = {
        "name": "API测试实验",
        "description": "自动化端到端测试",
        "steps": [
            {"step_type": "prep_sol", "description": "配制测试溶液", "params": {"duration_s": 3}},
            {"step_type": "transfer", "description": "转移溶液", "params": {"duration_s": 2}},
            {"step_type": "flush", "description": "冲洗通道", "params": {"flush_cycle_duration_s": 2, "flush_cycles": 2}},
        ],
        "tags": ["test", "api"],
    }
    r = requests.post(f"{BASE}/api/experiments/create", json=payload, timeout=5)
    assert r.status_code == 200, f"status={r.status_code} body={r.text}"
    exp = r.json()
    exp_id = exp["exp_id"]
    assert exp["status"] == "created"
    assert len(exp["steps"]) == 3
    print(f"  OK: created {exp_id}")
check("create_exp", test_create)

# 6. Get Detail
print("=== 6. Get Experiment Detail ===")
def test_detail():
    r = requests.get(f"{BASE}/api/experiments/detail/{exp_id}", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["exp_id"] == exp_id
    print(f"  OK: name={d['name']}, status={d['status']}, steps={len(d['steps'])}")
if exp_id:
    check("get_detail", test_detail)

# 7. Execute
print("=== 7. Execute Experiment ===")
def test_execute():
    r = requests.post(f"{BASE}/api/experiments/detail/{exp_id}/execute", timeout=10)
    assert r.status_code == 200, f"status={r.status_code} body={r.text}"
    result = r.json()
    print(f"  OK: {result}")
    assert result["status"] == "started"
if exp_id:
    check("execute_exp", test_execute)

# 8. Poll Progress
print("=== 8. Poll Progress (2s delay) ===")
def test_progress():
    time.sleep(2)
    r = requests.get(f"{BASE}/api/experiments/detail/{exp_id}/progress", timeout=5)
    assert r.status_code == 200
    prog = r.json()
    print(f"  OK: status={prog['status']}, step={prog['current_step_index']}/{prog['total_steps']}, "
          f"progress={prog['progress_percent']}%, elapsed={prog['elapsed_seconds']}s")
    log_count = len(prog.get("logs", []))
    print(f"  Logs: {log_count} entries")
    if prog.get("logs"):
        for log in prog["logs"][-3:]:
            print(f"    [{log['level']}] {log['message']}")
if exp_id:
    check("poll_progress", test_progress)

# 9. Get Logs
print("=== 9. Get Logs ===")
def test_logs():
    r = requests.get(f"{BASE}/api/experiments/detail/{exp_id}/logs", timeout=5)
    assert r.status_code == 200
    data = r.json()
    print(f"  OK: {data['total']} log entries")
if exp_id:
    check("get_logs", test_logs)

# 10. Wait for completion
print("=== 10. Wait for Completion (max 30s) ===")
def test_completion():
    for i in range(15):
        time.sleep(2)
        r = requests.get(f"{BASE}/api/experiments/detail/{exp_id}/progress", timeout=5)
        if r.status_code == 200:
            prog = r.json()
            status = prog["status"]
            print(f"  [{(i+1)*2}s] status={status}, step={prog['current_step_index']}/{prog['total_steps']}, "
                  f"progress={prog['progress_percent']}%")
            if status in ("completed", "failed", "stopped"):
                break
    
    r = requests.get(f"{BASE}/api/experiments/detail/{exp_id}", timeout=5)
    final = r.json()
    log_count = len(final.get("logs", []))
    sp_count = len(final.get("step_progress", []))
    print(f"  Final: status={final['status']}, logs={log_count}, step_progress={sp_count}")
    assert final["status"] == "completed", f"Expected completed, got {final['status']}"
if exp_id:
    check("completion", test_completion)

# 11. Persistence
print("=== 11. Check Persistence ===")
def test_persistence():
    fpath = os.path.join("AutoHySeeker", "data", "experiments.json")
    assert os.path.exists(fpath), f"{fpath} does not exist"
    with open(fpath, encoding="utf-8") as f:
        stored = json.load(f)
    print(f"  OK: {len(stored)} experiments persisted to disk")
    if stored:
        last = stored[-1]
        print(f"  Last: name={last['name']}, status={last['status']}")
check("persistence", test_persistence)

# 12. Recent
print("=== 12. Recent Experiments ===")
def test_recent():
    r = requests.get(f"{BASE}/api/experiments/recent", timeout=5)
    assert r.status_code == 200
    data = r.json()
    print(f"  OK: total={data['total']}, showing={len(data['experiments'])}")
check("recent", test_recent)

# 13. Stop test
print("=== 13. Stop Experiment Test ===")
def test_stop():
    global exp2_id
    payload = {
        "name": "停止测试实验",
        "description": "测试停止功能",
        "steps": [
            {"step_type": "flush", "description": "长时间冲洗", 
             "params": {"flush_cycle_duration_s": 10, "flush_cycles": 3}},
        ],
        "tags": ["test"],
    }
    r = requests.post(f"{BASE}/api/experiments/create", json=payload, timeout=5)
    exp2 = r.json()
    exp2_id = exp2["exp_id"]
    
    r = requests.post(f"{BASE}/api/experiments/detail/{exp2_id}/execute", timeout=10)
    assert r.status_code == 200
    
    time.sleep(2)
    
    r = requests.post(f"{BASE}/api/experiments/detail/{exp2_id}/stop", timeout=5)
    assert r.status_code == 200, f"stop status={r.status_code} body={r.text}"
    print(f"  Stop response: {r.json()}")
    
    time.sleep(3)
    
    r = requests.get(f"{BASE}/api/experiments/detail/{exp2_id}", timeout=5)
    final = r.json()
    print(f"  After stop: status={final['status']}")
    assert final["status"] == "stopped", f"Expected stopped, got {final['status']}"
check("stop_exp", test_stop)

# 14. Config reload
print("=== 14. Config Reload ===")
def test_reload():
    r = requests.post(f"{BASE}/api/system/config/reload", timeout=5)
    assert r.status_code == 200
    data = r.json()
    print(f"  OK: {data}")
check("config_reload", test_reload)

# Summary
print()
print(f"=== SUMMARY: {len(passed)} passed, {len(errors)} failed ===")
for name in passed:
    print(f"  PASS {name}")
for name, msg in errors:
    print(f"  FAIL {name}: {msg}")

if errors:
    exit(1)
else:
    print("\nAll tests passed!")
