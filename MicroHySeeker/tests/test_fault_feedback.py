import json

from src.services.experiment_data_manager import ExperimentDataManager
from src.services.fault_feedback import PumpFaultTracker


def test_pump_fault_tracker_emits_fault_offline_and_recovery_events():
    tracker = PumpFaultTracker()

    assert tracker.consume_state(3, {"online": True, "fault": 0}) == []

    fault_events = tracker.consume_state(3, {"online": True, "fault": 1})
    assert len(fault_events) == 1
    assert fault_events[0].level == "ERROR"
    assert "堵转保护触发" in fault_events[0].message

    offline_events = tracker.consume_state(3, {"online": False, "fault": 1})
    assert len(offline_events) == 1
    assert offline_events[0].level == "ERROR"
    assert "离线" in offline_events[0].message

    recovery_events = tracker.consume_state(3, {"online": True, "fault": 0})
    assert len(recovery_events) == 2
    assert {event.level for event in recovery_events} == {"INFO"}
    assert any("通信已恢复" in event.message for event in recovery_events)
    assert any("故障已清除" in event.message for event in recovery_events)


def test_experiment_data_manager_collects_unique_warning_and_error_messages(tmp_path):
    dm = ExperimentDataManager(base_dir=str(tmp_path))
    dm.begin_run("fault-feedback", {"exp_name": "fault-feedback"})

    dm.log("WARNING", "RUNNER", "泵 1 持续减速")
    dm.log("WARNING", "RUNNER", "泵 1 持续减速")
    dm.log("ERROR", "RUNNER", "泵 2 堵转保护触发")
    dm.log("ERROR", "RUNNER", "泵 2 堵转保护触发")

    summary_path = dm.end_run(success=False)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["warnings"] == ["泵 1 持续减速"]
    assert summary["errors"] == ["泵 2 堵转保护触发"]
