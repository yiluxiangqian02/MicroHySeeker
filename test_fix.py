"""Test prep_sol via MHS API after fix."""
import requests, json, time

plan = {
    "plan": {
        "name": "test_fixed_prepsol",
        "description": "Test after injection_order fix",
        "steps": [{
            "step_index": 0,
            "step_type": "prep_sol",
            "params": {
                "step_type": "prep_sol",
                "prep_sol_params": {
                    "total_volume_ul": 100.0,
                    "target_concentrations": {"Ni": 0.5, "H2O": 0.0},
                    "solvent_flags": {"Ni": False, "H2O": True},
                    "selected_solutions": {"Ni": True, "H2O": False},
                    "injection_order_numbers": {"Ni": 1}
                }
            },
            "description": "test pump",
            "parallel_group": 0
        }],
        "tags": []
    }
}

print("Sending prep_sol to MHS API after fix...")
r = requests.post("http://127.0.0.1:8100/api/experiment/start", json=plan, timeout=10)
print(f"Start: {r.status_code}")
if not r.ok:
    print(r.text)
    exit()

run_id = r.json().get("run_id", "?")
print(f"run_id: {run_id}")

for i in range(30):
    time.sleep(1)
    s = requests.get("http://127.0.0.1:8100/api/experiment/status", timeout=5).json()
    state = s["state"]
    running = s["is_running"]
    steps = s["total_steps"]
    success = s["last_finished_success"]
    print(f"  [{i+1}s] state={state} running={running} steps={steps} success={success}")
    if state == "idle" and i > 0:
        if steps > 0:
            print("  -> Pre-check PASSED! Experiment ran.")
        else:
            print("  -> Pre-check still failing (steps=0)")
        break
