"""E2E泵测试v3 - 极小体积快速测试，确保在Mock模式下几十秒内完成。"""
import json
import time
import os
import urllib.request
import urllib.error

AHS = "http://127.0.0.1:8200"
MHS = "http://127.0.0.1:8100"


def api(method, url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method,
                                headers={"Content-Type": "application/json"} if body else {})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {err_body}")
        return None
    except Exception as e:
        print(f"  请求失败: {e}")
        return None


def main():
    print("=" * 70)
    print("E2E泵全流程测试 v3 (极小体积，快速Mock测试)")
    print("=" * 70)

    # 1. 检查服务
    conn = api("GET", MHS + "/api/device/connection")
    if not conn or not conn.get("connected"):
        print("MHS未连接! 尝试连接Mock串口...")
        r = api("POST", MHS + "/api/device/connect", {"port": "COM3", "baudrate": 38400})
        if not r:
            print("连接失败!")
            return
        print(f"Mock连接: {r}")

    # 2. 创建实验 - 极小体积
    # ul_per_sec=0.5, so:
    # 5 uL → 10s, 2 uL → 4s, 1 uL → 2s
    payload = {
        "name": "E2E快速泵测试v3",
        "description": "极小体积快速验证5步全流程+泵日志",
        "category": "test",
        "steps": [
            {
                "step_type": "prep_sol",
                "description": "快速配液: Ni(OH)2(0.05M)+H2O, 10uL",
                "params": {
                    "prep_sol_params": {
                        "total_volume_ul": 10,  # 极小: 10uL
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
                "description": "快速移液 (泵4, 80RPM, 5uL)",
                "params": {
                    "pump_address": 4,
                    "pump_direction": "FWD",
                    "pump_rpm": 80,
                    "volume_ul": 5
                }
            },
            {
                "step_type": "flush",
                "description": "快速冲洗 (泵9/Inlet, 100RPM, 5uL)",
                "params": {
                    "pump_address": 9,
                    "pump_direction": "FWD",
                    "pump_rpm": 100,
                    "flush_rpm": 100,
                    "volume_ul": 5,
                    "flush_channel_id": "Inlet",
                    "flush_cycles": 1,
                    "flush_cycle_duration_s": 5
                }
            },
            {
                "step_type": "blank",
                "description": "空白等待 2秒",
                "params": {"duration_s": 2}
            },
            {
                "step_type": "evacuate",
                "description": "快速排空 (泵11/Outlet, 100RPM, 5uL)",
                "params": {
                    "pump_address": 11,
                    "pump_direction": "FWD",
                    "pump_rpm": 100,
                    "volume_ul": 5
                }
            }
        ]
    }

    print("\n--- 创建实验 ---")
    result = api("POST", AHS + "/api/experiments/create", payload)
    if not result:
        return
    exp_id = result["exp_id"]
    print(f"实验ID: {exp_id}")
    for i, s in enumerate(result["steps"]):
        print(f"  步骤{i+1}: [{s['step_type']}] {s['description']}")

    # 3. 启动执行
    print("\n--- 启动执行 ---")
    start_result = api("POST", AHS + f"/api/experiments/detail/{exp_id}/execute")
    if not start_result:
        return
    print(f"状态: {start_result.get('status')}")

    # 4. 轮询监控 (最多5分钟)
    print("\n--- 实时日志 ---")
    seen = 0
    start_time = time.time()
    while time.time() - start_time < 300:
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

        status = progress.get("status")
        elapsed = progress.get("elapsed_seconds", 0)
        pct = progress.get("progress_percent", 0)

        if status in ("completed", "failed", "stopped"):
            print(f"\n  🏁 实验 {status} (耗时 {elapsed:.0f}s, {pct}%)")
            break
    else:
        print("\n  ⏰ 等待超时 (5分钟)")

    # 5. 验证结果
    time.sleep(1)
    print("\n--- 验证结果 ---")
    exp = api("GET", AHS + f"/api/experiments/detail/{exp_id}")
    if not exp:
        return

    print(f"状态: {exp.get('status')}")
    print(f"执行模式: {exp.get('execution_mode', 'N/A')}")

    sp = exp.get("step_progress", [])
    steps = exp.get("steps", [])
    print("\n步骤结果:")
    for i, p in enumerate(sp):
        desc = steps[i].get("description", "") if i < len(steps) else ""
        st = p.get("status", "N/A") if p else "N/A"
        print(f"  步骤{i+1}: {st} | {desc}")

    # All logs
    all_logs = exp.get("logs", [])
    print(f"\n全部AHS日志 ({len(all_logs)} 条):")
    for log in all_logs:
        ts = log["ts"][11:19] if len(log["ts"]) > 19 else log["ts"]
        lvl = log.get("level", "info").upper()
        print(f"  [{lvl}] [{ts}] {log['message']}")

    # 6. MHS侧详细日志
    print("\n--- MHS侧泵执行日志 ---")
    log_dir = r"d:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker\logs"
    all_log_files = []
    for root, dirs, files in os.walk(log_dir):
        for f in files:
            if f.startswith("app_") and f.endswith(".log"):
                fp = os.path.join(root, f)
                all_log_files.append((os.path.getmtime(fp), fp))
    if all_log_files:
        all_log_files.sort(reverse=True)
        newest = all_log_files[0][1]
        with open(newest, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Show pump-related lines from this experiment
        keywords = ["RUNNER", "配液", "移液", "冲洗", "排空", "泵", "编码器", "注入",
                     "RPM", "批次", "等待", "步骤", "预检查", "实验"]
        relevant = []
        for line in lines:
            if any(kw in line for kw in keywords):
                relevant.append(line.rstrip())
        # Show last 60 relevant lines (from our run)
        print(f"(来自 {os.path.basename(newest)}, 共 {len(relevant)} 条相关日志)")
        for line in relevant[-60:]:
            print(f"  {line}")

    # 7. 确认磁盘持久化
    print("\n--- 磁盘持久化 ---")
    exp_file = r"d:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\data\experiments.json"
    if os.path.exists(exp_file):
        with open(exp_file, "r", encoding="utf-8") as f:
            all_exps = json.load(f)
        our = [e for e in all_exps if e.get("exp_id") == exp_id]
        if our:
            stored = our[0]
            print(f"  状态: {stored.get('status')}")
            print(f"  执行模式: {stored.get('execution_mode', 'N/A')}")
            print(f"  日志条数: {len(stored.get('logs', []))}")
            print(f"  步骤数: {len(stored.get('steps', []))}")
            print(f"  ✅ 数据已正确保存到磁盘")
        else:
            print(f"  ⚠ 未在磁盘找到实验 {exp_id}")
    else:
        print(f"  ⚠ experiments.json 不存在")

    # 8. MHS侧数据保存检查
    mhs_data_dir = r"d:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker\data"
    # Find directories from today
    today_dirs = []
    if os.path.exists(mhs_data_dir):
        for d in os.listdir(mhs_data_dir):
            dp = os.path.join(mhs_data_dir, d)
            if os.path.isdir(dp) and d.startswith("2026-04"):
                for sub in os.listdir(dp):
                    if exp_id in sub:
                        today_dirs.append(os.path.join(dp, sub))
    if today_dirs:
        print(f"\n  MHS侧数据目录:")
        for d in today_dirs:
            print(f"    {d}")
            for f in os.listdir(d):
                print(f"      {f}")

    print("\n" + "=" * 70)
    print("🏁 E2E测试v3 完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
