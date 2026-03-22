from __future__ import annotations

import asyncio


def test_reads_thresholds_from_monitor_config() -> None:
    from src.skills.realtime_monitor_skill import RealtimeMonitorSkill

    skill = RealtimeMonitorSkill(
        {
            "enabled": True,
            "poll_interval_s": 1.5,
            "rules": {
                "pump_speed_deviation_pct": 9.0,
                "communication_timeout_s": 4.0,
                "step_timeout_multiplier": 3.0,
                "current_spike_pct": 80.0,
            },
        }
    )

    report = skill.evaluate_snapshot({})
    assert report["poll_interval_s"] == 1.5
    assert report["rule_thresholds"]["pump_speed_deviation_pct"] == 9.0
    assert report["rule_thresholds"]["communication_timeout_s"] == 4.0


def test_detects_pump_speed_deviation() -> None:
    from src.skills.realtime_monitor_skill import RealtimeMonitorSkill

    skill = RealtimeMonitorSkill({"rules": {"pump_speed_deviation_pct": 5.0}})
    report = skill.evaluate_snapshot(
        {
            "run_id": "run-1",
            "pump_actual_rpm": {"1": 120},
            "pump_target_rpm": {"1": 100},
        }
    )

    assert report["highest_severity"] == "medium"
    assert report["anomalies"][0]["type"] == "pump_speed_deviation"


def test_detects_communication_timeout() -> None:
    from src.skills.realtime_monitor_skill import RealtimeMonitorSkill

    skill = RealtimeMonitorSkill({"rules": {"communication_timeout_s": 3.0}})
    report = skill.evaluate_snapshot({"communication_age_s": 4.2})

    assert report["highest_severity"] == "high"
    assert report["should_stop"] is True
    assert report["anomalies"][0]["type"] == "communication_timeout"


def test_detects_step_timeout() -> None:
    from src.skills.realtime_monitor_skill import RealtimeMonitorSkill

    skill = RealtimeMonitorSkill({"rules": {"step_timeout_multiplier": 2.0}})
    report = skill.evaluate_snapshot(
        {
            "current_step_elapsed_s": 25,
            "expected_step_duration_s": 10,
        }
    )

    assert report["highest_severity"] == "high"
    assert report["anomalies"][0]["type"] == "step_timeout"


def test_detects_data_file_empty() -> None:
    from src.skills.realtime_monitor_skill import RealtimeMonitorSkill

    skill = RealtimeMonitorSkill()
    report = skill.evaluate_snapshot(
        {
            "data_file_path": "data/run-1/result.csv",
            "data_file_size_bytes": 0,
        }
    )

    assert report["highest_severity"] == "medium"
    assert report["anomalies"][0]["type"] == "data_file_empty"


def test_detects_pump_no_response_as_critical() -> None:
    from src.skills.realtime_monitor_skill import RealtimeMonitorSkill

    skill = RealtimeMonitorSkill()
    report = skill.evaluate_snapshot({"pump_responsive": {"3": False}})

    assert report["highest_severity"] == "critical"
    assert report["should_emergency_stop"] is True
    assert report["anomalies"][0]["type"] == "pump_error"


def test_detects_current_spike() -> None:
    from src.skills.realtime_monitor_skill import RealtimeMonitorSkill

    skill = RealtimeMonitorSkill({"rules": {"current_spike_pct": 50.0}})
    report = skill.evaluate_snapshot({"current_values": [10.0, 16.0]})

    assert report["highest_severity"] == "medium"
    assert report["anomalies"][0]["type"] == "echem_current_spike"


def test_execute_returns_skill_result() -> None:
    from src.skills import RealtimeMonitorSkill

    skill = RealtimeMonitorSkill({"rules": {"communication_timeout_s": 1.0}})
    result = asyncio.run(skill.execute(communication_age_s=2.0))

    assert result.success is False
    assert result.data["anomaly_count"] == 1
    assert result.data["anomalies"][0]["source"] == "L1_realtime_monitor"
