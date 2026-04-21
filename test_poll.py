"""Test: Directly send to MHS and poll at 200ms intervals to catch running state."""
import requests, json, time, threading

def poll_mhs(stop_event):
    """Background polling at 200ms."""
    while not stop_event.is_set():
        try:
            s = requests.get("http://127.0.0.1:8100/api/experiment/status", timeout=3).json()
            state = s["state"]
            run_id = s.get("run_id", "?")
            steps = s.get("total_steps", 0)
            success = s.get("last_finished_success")
            ts = time.strftime("%H:%M:%S")
            print(f"  [{ts}] state={state} steps={steps} success={success} run_id={run_id[-12:]}")
            if state == "running":
                print("  >>> EXPERIMENT IS RUNNING!")
        except Exception as e:
            print(f"  poll error: {e}")
        time.sleep(0.2)

# Start polling
stop = threading.Event()
t = threading.Thread(target=poll_mhs, args=(stop,), daemon=True)
t.start()

time.sleep(0.5)  # Let first poll print

# Send experiment
plan = {
    "plan": {
        "name": "test_poll_fast",
        "description": "Test",
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
                    "injection_order_numbers": {"Ni": 1},
                    "injection_order": ["Ni"]
                }
            },
            "description": "test pump",
            "parallel_group": 0
        }],
        "tags": []
    }
}

print("\n=== Sending to MHS ===")
r = requests.post("http://127.0.0.1:8100/api/experiment/start", json=plan, timeout=10)
print(f"Start: {r.status_code} run_id={r.json().get('run_id','?')}")

# Wait for completion
time.sleep(10)
stop.set()
time.sleep(0.5)

# Check data dir
import os
data_dir = r"d:\AI4S\MicroHySeeker\MicroHySeeker\data\2026-04-16"
dirs = sorted(os.listdir(data_dir)) if os.path.exists(data_dir) else []
print(f"\nData dirs: {dirs}")
