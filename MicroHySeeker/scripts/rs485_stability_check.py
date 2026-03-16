import argparse
import statistics
import time

from src.services.rs485_wrapper import get_rs485_instance


def parse_addresses(text: str):
    return [int(x.strip()) for x in text.split(',') if x.strip()]


def main():
    parser = argparse.ArgumentParser(description="RS485 泵通讯稳定性诊断")
    parser.add_argument("--port", default="COM3", help="串口号，例如 COM3")
    parser.add_argument("--baud", type=int, default=38400, help="波特率")
    parser.add_argument("--addresses", default="1,2,3", help="待测地址列表，逗号分隔")
    parser.add_argument("--loops", type=int, default=120, help="每个地址测试轮数")
    parser.add_argument("--interval", type=float, default=0.05, help="轮询间隔秒")
    parser.add_argument("--mock", action="store_true", help="使用 mock 模式")
    args = parser.parse_args()

    addresses = parse_addresses(args.addresses)
    if not addresses:
        raise SystemExit("地址列表为空")

    rs = get_rs485_instance(force_reload=True)
    rs.set_mock_mode(args.mock)

    print(f"[INFO] connect {args.port}@{args.baud}, mock={args.mock}")
    ok = rs.open_port(args.port, args.baud)
    if not ok:
        raise SystemExit("[FAIL] open_port failed")

    # 先做一次全停，避免运动状态影响状态查询
    rs.stop_all()
    time.sleep(0.2)

    report = {}
    try:
        for addr in addresses:
            success = 0
            fail = 0
            durations = []
            statuses = {}

            for _ in range(args.loops):
                t0 = time.perf_counter()
                try:
                    status = rs.read_run_status(addr)
                except Exception:
                    status = None
                dt_ms = (time.perf_counter() - t0) * 1000.0

                if status is None:
                    fail += 1
                else:
                    success += 1
                    durations.append(dt_ms)
                    statuses[status] = statuses.get(status, 0) + 1

                time.sleep(args.interval)

            total = success + fail
            ok_rate = (success / total * 100.0) if total else 0.0
            p50 = statistics.median(durations) if durations else None
            p95 = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else None

            report[addr] = {
                "total": total,
                "success": success,
                "fail": fail,
                "ok_rate": ok_rate,
                "p50_ms": p50,
                "p95_ms": p95,
                "status_dist": statuses,
            }

        print("\n===== RS485 稳定性报告 =====")
        for addr in addresses:
            r = report[addr]
            print(
                f"addr={addr:>2} total={r['total']:>4} ok={r['success']:>4} "
                f"fail={r['fail']:>4} ok_rate={r['ok_rate']:>6.2f}% "
                f"p50={r['p50_ms'] if r['p50_ms'] is not None else 'NA'}ms "
                f"p95={r['p95_ms'] if r['p95_ms'] is not None else 'NA'}ms "
                f"status={r['status_dist']}"
            )

        print("\n===== 诊断建议 =====")
        base = report[addresses[0]]["ok_rate"]
        worst_addr = min(addresses, key=lambda a: report[a]["ok_rate"])
        worst = report[worst_addr]["ok_rate"]

        if worst < 70:
            print(f"[HIGH] 地址{worst_addr} 通讯极不稳定（ok_rate={worst:.1f}%）")
            print("- 若仅地址1异常，优先怀疑: 地址1驱动板/地址1接线/地址1泵负载")
            print("- 先做A/B互换测试：地址1与地址2互换泵电机线，观察问题是否跟随")
        elif worst < 90:
            print(f"[MEDIUM] 地址{worst_addr} 有明显丢包（ok_rate={worst:.1f}%）")
            print("- 优先检查 RS485 A/B 接线压接、地线共地、端接与偏置")
            print("- 可尝试把波特率降到 9600 复测，若明显改善=链路质量问题")
        else:
            print("[LOW] 通讯层面整体正常，若仍自转更偏向驱动板上电默认行为或泵机械问题")

        # 对比第一地址与其余地址
        if len(addresses) > 1:
            others = [report[a]["ok_rate"] for a in addresses[1:]]
            avg_other = sum(others) / len(others)
            delta = avg_other - base
            if delta > 15:
                print(f"[CLUE] 地址{addresses[0]} 比其余地址低 {delta:.1f}%：强烈指向该地址硬件通道问题")

    finally:
        try:
            rs.stop_all()
            rs.close_port()
        except Exception:
            pass


if __name__ == "__main__":
    main()
