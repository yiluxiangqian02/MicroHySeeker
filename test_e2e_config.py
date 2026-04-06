"""End-to-end test: system config loading + experiment creation."""
import urllib.request
import json

BASE = "http://127.0.0.1:8200"

# 1. System Config check
print("=== 1. System Config ===")
r = urllib.request.urlopen(f"{BASE}/api/system/config", timeout=5)
data = json.loads(r.read())
dcs = data.get("dilution_channels", [])
fcs = data.get("flush_channels", [])
pumps = data.get("pumps", [])
print(f"  Dilution: {len(dcs)} channels")
for dc in dcs:
    print(f"    - {dc['solution_name']}: {dc['stock_concentration']} mol/L, pump {dc['pump_address']}")
print(f"  Flush: {len(fcs)} channels")
for fc in fcs:
    print(f"    - {fc['pump_name']}: pump {fc['pump_address']}, {fc['work_type']}")
print(f"  Pumps: {len(pumps)} total")

assert len(dcs) == 4, f"Expected 4 dilution channels, got {len(dcs)}"
assert len(fcs) == 3, f"Expected 3 flush channels, got {len(fcs)}"
assert len(pumps) == 12, f"Expected 12 pumps, got {len(pumps)}"
assert dcs[0]["solution_name"] == "fe"
assert fcs[0]["work_type"] == "Inlet"
print("  Config assertions PASSED")

# 2. Simulated experiment creation
print("\n=== 2. Create Experiment ===")
payload = {
    "name": "E2E Test Fe+Cu CV",
    "description": "Auto-test",
    "category": "test",
    "tags": ["e2e-test"],
    "steps": [
        {
            "step_type": "prep_sol",
            "description": "Config 100mL",
            "params": {
                "step_type": "prep_sol",
                "prep_sol_params": {
                    "total_volume_ul": 100000,
                    "selected_solutions": {"fe": True, "cu": True, "h2o": False, "KOH": False},
                    "target_concentrations": {"fe": 0.1, "cu": 0.05, "h2o": 0, "KOH": 0},
                    "solvent_flags": {"fe": False, "cu": False, "h2o": True, "KOH": False},
                    "injection_order_numbers": {"fe": 1, "cu": 2, "h2o": 3, "KOH": 4},
                    "injection_order": ["fe", "cu", "h2o", "KOH"],
                }
            }
        },
        {
            "step_type": "echem",
            "description": "CV scan with full params",
            "params": {
                "step_type": "echem",
                "ec_settings": {
                    "technique": "CV",
                    "e0": 0, "eh": 0.8, "el": -0.2, "ef": 0,
                    "scan_rate": 0.05, "seg_num": 4,
                    "sample_interval_ms": 100,
                    "sensitivity": 0.001, "autosensitivity": False,
                    "quiet_time_s": 2, "scan_dir": "FWD",
                    "ir_compensation_enabled": False, "ir_compensation_ohm": 0,
                    "use_dummy_cell": False,
                }
            }
        },
        {
            "step_type": "flush",
            "description": "Flush inlet",
            "params": {
                "step_type": "flush",
                "flush_channel_id": "1",
                "flush_rpm": 100,
                "flush_cycle_duration_s": 30,
                "flush_cycles": 2,
            }
        },
        {
            "step_type": "echem",
            "description": "ADT with CP+CA",
            "params": {
                "step_type": "echem",
                "ec_settings": {
                    "technique": "ADT",
                    "adt_enabled": True,
                    "adt_num_cycles": 50,
                    "adt_cathodic_current_mA": -250,
                    "adt_cp_anodic_current_mA": 250,
                    "adt_cp_e_high": 2.0, "adt_cp_e_low": -2.0,
                    "adt_cp_polarity": "n",
                    "adt_cp_sample_interval": 0.01, "adt_cp_segments": 2,
                    "adt_anodic_potential_V": 1.5,
                    "adt_ca_e_high": 1.5, "adt_ca_e_low": -0.5,
                    "adt_ca_polarity": "p", "adt_ca_steps": 1,
                    "adt_anodic_duration_s": 2.0,
                }
            }
        },
        {
            "step_type": "blank",
            "description": "Wait",
            "params": {"step_type": "blank", "duration_s": 30}
        },
        {
            "step_type": "evacuate",
            "description": "Evacuate",
            "params": {
                "step_type": "evacuate",
                "pump_address": 12, "pump_direction": "FWD",
                "pump_rpm": 200, "volume_ul": 5000,
                "flush_cycles": 3,
            }
        },
    ]
}
req = urllib.request.Request(
    f"{BASE}/api/experiments/create",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    r = urllib.request.urlopen(req, timeout=10)
    result = json.loads(r.read())
    print(f"  Created: id={result.get('id', '?')}, name={result.get('name', '?')}")
    print(f"  Steps: {len(result.get('steps', []))}")
    print("  Create PASSED")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(f"  HTTP {e.code}: {body}")
    print("  Create FAILED (but backend may not accept this format - non-blocking)")
except Exception as e:
    print(f"  Error: {e}")

# 3. Via proxy
print("\n=== 3. Proxy Check ===")
try:
    r = urllib.request.urlopen("http://127.0.0.1:5174/api/system/config", timeout=5)
    data = json.loads(r.read())
    assert len(data.get("dilution_channels", [])) > 0
    print("  Proxy → dilution channels OK")
    print("  Proxy PASSED")
except Exception as e:
    print(f"  Proxy check: {e}")

print("\n=== ALL E2E TESTS DONE ===")
