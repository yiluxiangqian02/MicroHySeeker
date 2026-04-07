"""全流程E2E泵测试：配液→移液→冲洗→空白→排空，验证泵运行日志。"""
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
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {err_body}")
        return None


def check_services():
    print("=" * 60)
    print("1. 检查服务状态")
    print("=" * 60)
    for label, url in [("AHS", f"{AHS}/api/system/health"),
                       ("MHS", f"{MHS}/api/experiment/status"),
                       ("Vite", "http://127.0.0.1:5173/")]:
        try:
            urllib.request.urlopen(url, timeout=3)
            print(f"  {label}: OK")
        except Exception as e:
            print(f"  {label}: DOWN - {e}")
            if label == "MHS":
                print("  ⚠ MHS未启动，泵命令将使用本地模拟（无真实硬件）")
            return label != "AHS"  # AHS必须在线
    return True


def create_experiment():
    print("\n" + "=" * 60)
    print("2. 创建全流程实验（无电化学）")
    print("=" * 60)
    payload = {
        "name": "E2E泵全流程测试",
        "description": "配液→移液→冲洗→空白→排空，验证泵运行日志",
        "category": "test",
        "steps": [
            {
                "step_type": "prep_sol",
                "description": "配液: fe(0.1M) + h2o(溶剂), 2mL",
                "params": {
                    "prep_sol_params": {
                        "total_volume_ul": 2000,
                        "injection_order": ["fe", "h2o"],
                        "target_concentrations": {"fe": 0.1, "h2o": 0},
                        "solvent_flags": {"fe": False, "h2o": True},
                        "selected_solutions": {"fe": True, "h2o": True},
                        "injection_order_numbers": {"fe": 1, "h2o": 2}
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
                "description": "冲洗进液管路 (泵5/Inlet, 100RPM, 1mL)",
                "params": {
                    "pump_address": 5,
                    "pump_direction": "REV",
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
                "params": {
                    "duration_s": 3
                }
            },
            {
                "step_type": "evacuate",
                "description": "排空反应杯 (泵12/Outlet, 100RPM, 3mL)",
                "params": {
                    "pump_address": 12,
                    "pump_direction": "FWD",
                    "pump_rpm": 100,
                    "volume_ul": 3000
                }
            }
        ]
    }

    result = api("POST", f"{AHS}/api/experiments/create", payload)
    if not result:
        print("  创建失败!")
        return None

    exp_id = result["exp_id"]
    print(f"  实验ID: {exp_id}")
    print(f"  步骤数: {len(result['steps'])}")
    for i, s in enumerate(result["steps"]):
        print(f"    步骤{i+1}: [{s['step_type']}] {s['description']}")
    return exp_id


def execute_and_monitor(exp_id):
    print("\n" + "=" * 60)
    print("3. 启动实验执行")
    print("=" * 60)
    result = api("POST", f"{AHS}/api/experiments/detail/{exp_id}/execute")
    if not result:
        print("  启动失败!")
        return False

    print(f"  状态: {result['status']}, 来源: {result['source']}")

    print("\n" + "=" * 60)
    print("4. 实时监控进度与日志")
    print("=" * 60)
    seen_logs = 0
    last_step = -1
    poll_count = 0
    max_polls = 120  # 最多等4分钟（120 * 2s）

    while poll_count < max_polls:
        time.sleep(2)
        poll_count += 1

        progress = api("GET", f"{AHS}/api/experiments/detail/{exp_id}/progress")
        if not progress:
            print("  轮询失败，重试...")
            continue

        status = progress.get("status", "unknown")
        step_idx = progress.get("current_step_index", 0)
        total = progress.get("total_steps", 0)
        pct = progress.get("progress_percent", 0)
        elapsed = progress.get("elapsed_seconds", 0)

        # 打印新日志
        logs = progress.get("logs", [])
        for log in logs[seen_logs:]:
            ts_short = log["ts"][11:19] if len(log["ts"]) > 19 else log["ts"]
            level = log.get("level", "info").upper()
            msg = log["message"]
            prefix = "⚠" if level == "WARN" else "❌" if level == "ERROR" else "📋"
            print(f"  {prefix} [{ts_short}] {msg}")
        seen_logs = len(logs)

        # 步骤变化时打印进度
        if step_idx != last_step:
            cur = progress.get("current_step")
            step_desc = ""
            if cur:
                step_desc = f" [{cur.get('step_type','')}] {cur.get('description','')}"
            print(f"  ⏳ 进度: {pct}% | 步骤 {step_idx+1}/{total}{step_desc} | 耗时 {elapsed:.0f}s")
            last_step = step_idx

        if status in ("completed", "failed", "stopped"):
            print(f"\n  ✅ 实验结束: {status}")
            break
    else:
        print("  ⏰ 监控超时（4分钟）")

    return True


def verify_results(exp_id):
    print("\n" + "=" * 60)
    print("5. 验证实验结果与数据保存")
    print("=" * 60)

    # 5a. 检查实验记录
    exp = api("GET", f"{AHS}/api/experiments/detail/{exp_id}")
    if not exp:
        print("  获取实验记录失败!")
        return

    print(f"  实验名称: {exp['name']}")
    print(f"  状态: {exp['status']}")
    print(f"  执行模式: {exp.get('execution_mode', 'N/A')}")
    print(f"  创建时间: {exp.get('created_at', 'N/A')}")
    print(f"  完成时间: {exp.get('completed_at', 'N/A')}")

    # 5b. 步骤进度
    sp = exp.get("step_progress", [])
    print(f"\n  步骤执行情况:")
    for i, p in enumerate(sp):
        if p:
            print(f"    步骤{i+1}: {p.get('status','N/A')} "
                  f"(开始: {p.get('started_at','')[:19]}, "
                  f"完成: {p.get('completed_at','')[:19] if p.get('completed_at') else '-'})")

    # 5c. 日志统计
    logs = exp.get("logs", [])
    print(f"\n  总日志数: {len(logs)}")
    pump_logs = [l for l in logs if any(kw in l.get("message", "")
                 for kw in ["泵", "转发", "MicroHySeeker", "pump", "配液", "移液",
                            "冲洗", "排空", "位移", "编码器", "RPM"])]
    print(f"  泵相关日志: {len(pump_logs)}")
    for l in pump_logs:
        print(f"    [{l.get('level','info')}] {l['message']}")

    mhs_logs = [l for l in logs if "MicroHySeeker" in l.get("message", "")]
    if mhs_logs:
        print(f"\n  MHS交互日志: {len(mhs_logs)}")
        for l in mhs_logs:
            print(f"    {l['message']}")

    # 5d. 检查磁盘上的 experiments.json
    import os
    exp_file = os.path.join(os.path.dirname(__file__), "AutoHySeeker", "data", "experiments.json")
    if os.path.exists(exp_file):
        size = os.path.getsize(exp_file)
        print(f"\n  experiments.json: {size} bytes")
        with open(exp_file, "r", encoding="utf-8") as f:
            all_exps = json.load(f)
        our_exp = [e for e in all_exps if e.get("exp_id") == exp_id]
        if our_exp:
            print(f"  磁盘记录状态: {our_exp[0].get('status')}")
            print(f"  磁盘日志条数: {len(our_exp[0].get('logs', []))}")
        else:
            print(f"  ⚠ 磁盘上未找到本实验记录")
    else:
        print(f"\n  ⚠ experiments.json 文件不存在: {exp_file}")


def main():
    print("🔬 全流程E2E泵运行测试")
    print("  (配液→移液→冲洗→空白→排空，不含电化学)")
    print()

    if not check_services():
        print("AHS 不在线，无法继续")
        return

    exp_id = create_experiment()
    if not exp_id:
        return

    execute_and_monitor(exp_id)
    verify_results(exp_id)

    print("\n" + "=" * 60)
    print("🏁 E2E测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
