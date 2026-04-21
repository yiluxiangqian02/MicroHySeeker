"""Test pre_check directly in MHS context."""
import sys, os
os.chdir(r"d:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker")
sys.path.insert(0, ".")

from src.models import PrepSolStep, Experiment, ProgStep, ProgramStepType, SystemConfig
from src.api.bridge import plan_to_experiment

# Load config
config = SystemConfig.load_from_file("./config/system.json")

# Build experiment from plan
plan_data = {
    "name": "test_precheck",
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
                "injection_order_numbers": {"Ni": 1}
            }
        },
        "description": "test",
        "parallel_group": 0
    }],
    "tags": []
}

flush_channels = [{"pump_address": ch.pump_address, "direction": ch.direction, "work_type": ch.work_type} for ch in config.flush_channels]
exp_dict = plan_to_experiment(plan_data, flush_channels=flush_channels)

exp = Experiment.from_dict(exp_dict)
print(f"injection_order = {exp.steps[0].prep_sol_params.injection_order}")

# Create worker and run pre_check
from src.engine.runner import ExperimentWorker
from src.services.rs485_wrapper import RS485Wrapper

# Use a dummy RS485 (not actually connected in test)
class DummyRS485:
    def is_connected(self): return True
    def get_port(self): return "COM3"

worker = ExperimentWorker(exp, DummyRS485(), config)
print(f"Worker dilution_channels: {list(worker._dilution_channels.keys())}")
print(f"Worker pump_calibration keys: {list(worker._pump_calibration.keys())}")

errors = worker.pre_check()
if errors:
    print(f"\nPRE-CHECK ERRORS ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
else:
    print("\nPRE-CHECK PASSED!")

