"""E2E泵全流程测试v2 - Mock模式，使用正确的MHS通道名称。"""
import json
import time
import urllib.request
import urllib.error

AHS = "http://127.0.0.1:8200"
MHS = "http://127.0.0.1:8100"


def api(method, url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method,
                                headers={"Content-Type": "application/json"} if body else {})
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {err_body}")
        return None


def main():
    print("=" * 70)
    print("E2E泵全流程测试 v2 (Mock模式, 正确溶液名称)")
    print("=" * 70)

    # Check MHS connection
    conn = api("GET", MHS + "/api/device/connection")
    if conn:
        print(f"MHS连接: Connected={conn.get('connected')}, Mock={conn.get('mock_mode')}")
    else:
        print("MHS不可用!")
        return

    # Create experiment with CORRECT solution names from MHS config
    # Dilution: Ni(OH)2 → pump 1, Fe(OH)2 → pump 2
    # H2O auto-added from Inlet flush pump → pump 9
    payload = {
        "name": "E2E泵全流程测试v2-Mock",
        "description": "配液(Ni(OH)2+H2O)→移液→冲洗→空白→排空，Mock模式验证泵运行日志",
        "category": "test",
        "steps": [
            {
                "step_type": "prep_sol",
                "description": "配液: Ni(OH)2(0.05M) + H2O(溶剂), 2mL",
                "params": {
                    "prep_sol_params": {
                        "total_volume_ul": 2000,
                        "injection_order": ["Ni(OH)2", "H2O"],
                        "target_concentrations": {"Ni(OH)2": 0.05, "H2O": 0},
                        "solvent_flags": {"Ni(OH)2": False, "H2O": True},
                        "selected_solutions": {"Ni(OH)2": True, "H2O": True},
                        "injection_order_numbers": {"Ni(OH)2": 1, "H2O": 2}
                    }
                }
            },
            {
                "step_type": "transfer",
                "description": "移液到反应杯 (泵4, 80RPM, 2mL)",
                "params": {
                    "pump_address": 4,
                    "pump_direction": "FWD",
                    "pump_rpm": 80,
                    "volume_ul": 2000
                }
            },
            {
                "step_type": "flush",
                "description": "冲洗进液管路 (泵9/Inlet, 100RPM, 1mL)",
                "params": {
                    "pump_address": 9,
                    "pump_direction": "FWD",
                    "pump_rpm": 100,
                    "flush_rpm": 100,
                    "volume_ul": 1000,
                    "flush_channel_id": "Inlet",
                    "flush_cycles": 1,
                    "flush_cycle_duration_s": 5
                }
            },
            {
                "step_type": "blank",
                "description": "空白等待 3秒",
                "params": {"duration_s": 3}
            },
            {
                "step_type": "evacuate",
                "description": "排空反应杯 (泵11/Outlet, 100RPM, 3mL)",
                "params": {
                    "pump_address": 11,
                    "pump_direction": "FWD",
                    "pump_rpm": 100,
                    "volume_ul": 3000
                }
            }
        ]
    }

    # Create
    print("\n--- 创建实验 ---")
    result = api("POST", AHS + "/api/experiments/create", payload)
    if not result:
        print("创建失败!")
        return
    exp_id = result["exp_id"]
    print(f"实验ID: {exp_id}")
    for i, s in enumerate(result["steps"]):
        print(f"  步骤{i+1}: [{s['step_type']}] {s['description']}")

    # Execute
    print("\n--- 启动执行 ---")
    start_result = api("POST", AHS + f"/api/experiments/detail/{exp_id}/execute")
    if not start_result:
        print("启动失败!")
        return
    print(f"状态: {start_result.get('status')}, 来源: {start_result.get('source')}")

    # Monitor
    print("\n--- 实时日志 ---")
    seen = 0
    for _ in range(120):
        time.sleep(2)
        progress = api("GET", AHS + f"/api/experiments/detail/{exp_id}/progress")
        if not progress:
            continue

        logs = progress.get("logs", [])
        for log in logs[seen:]:
            ts = log["ts"][11:19] if len(log["ts"]) > 19 else log["ts"]
            lvl = log.get("level", "info").upper()
            prefix = "⚠" if lvl == "WARN" else "❌" if lvl == "ERROR" else "📋"
            print(f"  {prefix} [{ts}] {log['message']}")
        seen = len(logs)

        pct = progress.get("progress_percent", 0)
        elapsed = progress.get("elapsed_seconds", 0)
        status = progress.get("status")
        if status in ("completed", "failed", "stopped"):
            print(f"\n  🏁 实验结束: {status} (耗时 {elapsed:.0f}s)")
            break

    # Results
    print("\n--- 验证结果 ---")
    exp = api("GET", AHS + f"/api/experiments/detail/{exp_id}")
    if not exp:
        return

    print(f"执行模式: {exp.get('execution_mode', 'N/A')}")
    print(f"状态: {exp.get('status')}")

    print("\n步骤完成情况:")
    for i, p in enumerate(exp.get("step_progress", [])):
        step = exp["steps"][i] if i < len(exp.get("steps", [])) else {}
        st = p.get("status", "N/A") if p else "N/A"
        desc = step.get("description", "")
        print(f"  步骤{i+1}: {st} | {desc}")

    # MHS side logs
    print("\n--- MHS侧日志 ---")
    import glob
    log_dir = r"d:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker\logs"
    # Find newest log
    import os
    all_logs = []
    for root, dirs, files in os.walk(log_dir):
        for f in files:
            if f.startswith("app_") and f.endswith(".log"):
                fp = os.path.join(root, f)
                all_logs.append((os.path.getmtime(fp), fp))
    if all_logs:
        all_logs.sort(reverse=True)
        newest = all_logs[0][1]
        print(f"最新日志: {os.path.basename(newest)}")
        with open(newest, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Show lines from our experiment
        exp_lines = [l.rstrip() for l in lines if exp_id in l or "RUNNER" in l or "配液" in l or "移液" in l or "冲洗" in l or "排空" in l or "泵" in l or "Mock" in l or "编码器" in l]
        if exp_lines:
            for line in exp_lines[-40:]:
                print(f"  {line}")
        else:
            # Show last 30 lines
            print("  (未找到关键词日志，显示最后30行:)")
            for line in lines[-30:]:
                print(f"  {line.rstrip()}")

    # Data saved?
    print("\n--- 数据持久化 ---")
    exp_file = r"d:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\data\experiments.json"
    if os.path.exists(exp_file):
        with open(exp_file, "r", encoding="utf-8") as f:
            all_exps = json.load(f)
        our = [e for e in all_exps if e.get("exp_id") == exp_id]
        if our:
            print(f"experiments.json: 找到记录, status={our[0].get('status')}, logs={len(our[0].get('logs', []))}")
        else:
            print("experiments.json: 未找到本实验记录")
    else:
        print(f"experiments.json 不存在")

    print("\n" + "=" * 70)
    print("E2E测试v2 完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
