"""
硬件全流程测试：真实 RS485，不含电化学步骤
步骤：prep_sol (Ni(OH)2 10µL) + flush (inlet 10s) + transfer (5s)
"""
import urllib.request
import json
import time
import sys


AHS = "http://127.0.0.1:8200"
MHS = "http://127.0.0.1:8100"


def get(url, timeout=5):
    r = urllib.request.urlopen(url, timeout=timeout)
    return json.loads(r.read())


def post(url, body, timeout=10):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())


def check(label, url):
    try:
        data = get(url)
        print(f"  ✅ {label}: OK")
        return data
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        sys.exit(1)


print("=" * 60)
print("硬件全流程测试 (无电化学)")
print("=" * 60)

# ── 1. 基础检查 ──────────────────────────────────────────────
print("\n[1] 服务状态检查")
check("AHS 8200", f"{AHS}/health")

mhs_status = check("MHS 8100", f"{MHS}/api/experiment/status")
print(f"      MHS state: {mhs_status.get('state')}")

mhs_conn = check("MHS RS485", f"{MHS}/api/device/connection")
connected = mhs_conn.get("connected")
mock_mode = mhs_conn.get("mock_mode")
print(f"      RS485 connected={connected}, mock_mode={mock_mode}")

if not connected:
    print("  ❌ RS485 未连接，无法测试真实硬件")
    sys.exit(1)
if mock_mode:
    print("  ⚠️  Mock 模式，非真实硬件")
else:
    print("  ✅ 真实硬件模式")

# ── 2. 获取通道配置 ──────────────────────────────────────────
print("\n[2] 通道配置")
cfg = get(f"{AHS}/api/system/config")
dch = cfg.get("dilution_channels", [])
fch = cfg.get("flush_channels", [])
print(f"      配液通道: {[(c['solution_name'], 'pump'+str(c['pump_address'])) for c in dch]}")
print(f"      冲洗通道: {[(c['channel_id'], c['work_type']) for c in fch]}")

if not dch:
    print("  ❌ 没有配液通道配置")
    sys.exit(1)

# 用前两个配液通道（主液 + 溶剂）
sol_main = dch[0]["solution_name"]   # e.g. "Ni(OH)2"
sol_solvent = dch[1]["solution_name"] if len(dch) > 1 else dch[0]["solution_name"]
# 用第一个冲洗通道（Inlet）
flush_ch_obj = next((c for c in fch if c.get("work_type") == "Inlet"), fch[0] if fch else None)
if not flush_ch_obj:
    print("  ❌ 没有冲洗通道配置")
    sys.exit(1)
flush_ch_id = flush_ch_obj["channel_id"]
flush_pump = flush_ch_obj["pump_address"]
flush_rpm = flush_ch_obj.get("rpm", 100)
print(f"      主液: {sol_main}, 溶剂: {sol_solvent}, 冲洗通道: {flush_ch_id}(pump{flush_pump})")

# ── 3. 创建实验 ──────────────────────────────────────────────
print("\n[3] 创建实验")
exp_def = {
    "name": "硬件测试_无电化学",
    "description": "E2E hardware test without echem",
    "category": "test",
    "tags": ["hardware_test"],
    "steps": [
        {
            "step_type": "prep_sol",
            "description": f"配液 {sol_main} 10µL",
            "params": {
                "prep_sol_params": {
                    "total_volume_ul": 10.0,
                    "injection_order": [sol_main, sol_solvent],
                    "target_concentrations": {sol_main: 0.01, sol_solvent: 0.0},
                    "solvent_flags": {sol_main: False, sol_solvent: True},
                    "selected_solutions": {sol_main: True, sol_solvent: True},
                    "injection_order_numbers": {sol_main: 1, sol_solvent: 2},
                }
            }
        },
        {
            "step_type": "flush",
            "description": f"冲洗通道{flush_ch_id} 2次×5s",
            "params": {
                "flush_channel_id": flush_ch_id,
                "flush_rpm": flush_rpm,
                "flush_cycle_duration_s": 5,
                "flush_cycles": 2,
            }
        },
        {
            "step_type": "transfer",
            "description": "移液 pump9 10µL",
            "params": {
                "pump_address": flush_pump,
                "pump_direction": "FWD",
                "pump_rpm": flush_rpm,
                "volume_ul": 10.0,
            }
        }
    ]
}

try:
    exp = post(f"{AHS}/api/experiments/create", exp_def)
    exp_id = exp.get("id") or exp.get("exp_id")
    print(f"  ✅ 实验创建成功: {exp_id}")
except Exception as e:
    print(f"  ❌ 创建失败: {e}")
    sys.exit(1)

# ── 4. 执行实验 ──────────────────────────────────────────────
print("\n[4] 开始执行")
try:
    result = post(f"{AHS}/api/experiments/detail/{exp_id}/execute", {})
    print(f"  ✅ 执行启动: {result}")
except Exception as e:
    print(f"  ❌ 执行启动失败: {e}")
    sys.exit(1)

# ── 5. 轮询进度 ──────────────────────────────────────────────
print("\n[5] 执行进度（每 2s 轮询一次）")
start_ts = time.time()
last_step = -1
MAX_WAIT = 180

while True:
    elapsed = time.time() - start_ts
    if elapsed > MAX_WAIT:
        print(f"\n  ⏱️  超时 {MAX_WAIT}s")
        break

    try:
        prog = get(f"{AHS}/api/experiments/detail/{exp_id}/progress")
        status = prog.get("status", "?")
        step = prog.get("current_step", 0)
        total = prog.get("total_steps", 0)
        mhs_st = prog.get("mhs_state", "?")

        if step != last_step:
            logs = prog.get("recent_logs", [])
            last_log = logs[-1].get("message", "") if logs else ""
            print(f"  [{elapsed:5.1f}s] 步骤 {step}/{total}  状态={status}  MHS={mhs_st}")
            if last_log:
                print(f"           └─ {last_log}")
            last_step = step

        if status in ("completed", "failed", "stopped"):
            print(f"\n  ── 实验结束: {status} ──")
            break

    except Exception as e:
        print(f"  轮询出错: {e}")

    time.sleep(2)

# ── 6. 最终状态 & MHS 日志 ──────────────────────────────────
print("\n[6] 最终结果")
try:
    detail = get(f"{AHS}/api/experiments/detail/{exp_id}")
    print(f"  状态: {detail.get('status')}")
    print(f"  执行模式: {detail.get('execution_mode', 'N/A')}")
    print(f"  开始: {detail.get('started_at', 'N/A')}")
    print(f"  结束: {detail.get('completed_at', 'N/A')}")
    logs = detail.get("logs", [])
    print(f"\n  AHS 实验日志 ({len(logs)} 条):")
    for entry in logs:
        lvl = entry.get("level", "info").upper()
        msg = entry.get("message", "")
        print(f"    [{lvl}] {msg}")
except Exception as e:
    print(f"  获取详情失败: {e}")

# MHS 最近日志
print("\n  MHS 最近日志:")
try:
    mhs_logs = get(f"{MHS}/api/experiment/logs")
    for line in (mhs_logs.get("logs", []) or [])[-20:]:
        print(f"    {line}")
except Exception as e:
    print(f"  获取 MHS 日志失败: {e}")

print("\n" + "=" * 60)
print("测试结束")
print("=" * 60)
