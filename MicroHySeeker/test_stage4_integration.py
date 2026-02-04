"""
Stage 4 集成测试 - Flusher 冲洗功能

测试内容:
1. Flusher 基本功能
2. 与 PumpManager 集成
3. RS485Wrapper 冲洗接口
"""
import sys
import time
import threading
from pathlib import Path

# 确保导入路径正确
sys.path.insert(0, str(Path(__file__).parent))

def test_flusher_basic():
    """测试 Flusher 基本功能"""
    print("\n" + "=" * 60)
    print("测试 1: Flusher 基本功能")
    print("=" * 60)
    
    from src.echem_sdl.hardware.flusher import (
        Flusher, FlusherConfig, FlusherPumpConfig,
        FlusherState, FlusherPhase
    )
    
    # 创建配置
    config = FlusherConfig(
        inlet=FlusherPumpConfig(address=1, name="Inlet", rpm=200, duration_s=0.2),
        transfer=FlusherPumpConfig(address=2, name="Transfer", rpm=200, duration_s=0.2),
        outlet=FlusherPumpConfig(address=3, name="Outlet", rpm=200, duration_s=0.2),
        default_cycles=2
    )
    
    # Mock模式创建 Flusher
    flusher = Flusher(config, pump_manager=None, logger=None, mock_mode=True)
    
    # 测试初始状态
    assert flusher.state == FlusherState.IDLE, "初始状态应为 IDLE"
    assert flusher.phase == FlusherPhase.IDLE, "初始阶段应为 IDLE"
    assert flusher.current_cycle == 0, "初始循环数应为 0"
    print("✅ 初始状态正确")
    
    # 测试设置循环数
    flusher.set_cycles(3)
    assert flusher.total_cycles == 3, "总循环数应为 3"
    print("✅ 设置循环数成功")
    
    # 测试进度计算
    assert flusher.progress == 0.0, "初始进度应为 0"
    print("✅ 进度计算正确")
    
    # 测试状态查询
    status = flusher.get_status()
    assert status["state"] == "idle"
    assert status["phase"] == "idle"
    assert status["total_cycles"] == 3
    print("✅ 状态查询正确")
    
    print("\n✅ Flusher 基本功能测试通过!")
    return True


def test_flusher_lifecycle():
    """测试 Flusher 生命周期"""
    print("\n" + "=" * 60)
    print("测试 2: Flusher 生命周期 (start/stop)")
    print("=" * 60)
    
    from src.echem_sdl.hardware.flusher import (
        Flusher, FlusherConfig, FlusherPumpConfig,
        FlusherState, FlusherPhase
    )
    
    # 短时间配置用于快速测试
    config = FlusherConfig(
        inlet=FlusherPumpConfig(address=1, name="Inlet", duration_s=0.1),
        transfer=FlusherPumpConfig(address=2, name="Transfer", duration_s=0.1),
        outlet=FlusherPumpConfig(address=3, name="Outlet", duration_s=0.1),
        default_cycles=1
    )
    
    flusher = Flusher(config, pump_manager=None, logger=None, mock_mode=True)
    flusher.set_cycles(1)
    
    # 测试启动
    result = flusher.start()
    assert result == True, "启动应返回 True"
    assert flusher.state == FlusherState.RUNNING, "启动后状态应为 RUNNING"
    assert flusher.current_cycle == 1, "启动后循环数应为 1"
    print("✅ 启动成功")
    
    # 测试停止
    flusher.stop()
    assert flusher.state == FlusherState.IDLE, "停止后状态应为 IDLE"
    print("✅ 停止成功")
    
    # 测试重复启动
    result1 = flusher.start()
    result2 = flusher.start()  # 重复启动应返回 False
    assert result1 == True
    assert result2 == False, "重复启动应返回 False"
    print("✅ 重复启动检测正确")
    
    flusher.stop()
    
    print("\n✅ Flusher 生命周期测试通过!")
    return True


def test_flusher_full_cycle():
    """测试完整冲洗循环"""
    print("\n" + "=" * 60)
    print("测试 3: 完整冲洗循环 (阶段切换)")
    print("=" * 60)
    
    from src.echem_sdl.hardware.flusher import (
        Flusher, FlusherConfig, FlusherPumpConfig,
        FlusherState, FlusherPhase
    )
    
    # 非常短的时间配置
    config = FlusherConfig(
        inlet=FlusherPumpConfig(address=1, name="Inlet", duration_s=0.1),
        transfer=FlusherPumpConfig(address=2, name="Transfer", duration_s=0.1),
        outlet=FlusherPumpConfig(address=3, name="Outlet", duration_s=0.1),
        default_cycles=1
    )
    
    flusher = Flusher(config, pump_manager=None, logger=None, mock_mode=True)
    
    # 收集阶段变化
    phases_visited = []
    cycle_completed = []
    completed = threading.Event()
    
    def on_phase(phase):
        phases_visited.append(phase)
        print(f"  阶段变化: {phase.value}")
    
    def on_cycle(cycle_num):
        cycle_completed.append(cycle_num)
        print(f"  循环完成: {cycle_num}")
    
    def on_complete():
        completed.set()
        print("  冲洗全部完成!")
    
    flusher.on_phase_change(on_phase)
    flusher.on_cycle_complete(on_cycle)
    flusher.on_complete(on_complete)
    
    # 启动并等待完成
    flusher.set_cycles(1)
    flusher.start()
    
    # 等待最多2秒
    completed.wait(timeout=2.0)
    
    # 验证阶段
    assert FlusherPhase.INLET in phases_visited, "应经过 INLET 阶段"
    assert FlusherPhase.TRANSFER in phases_visited, "应经过 TRANSFER 阶段"
    assert FlusherPhase.OUTLET in phases_visited, "应经过 OUTLET 阶段"
    print("✅ 所有阶段已执行")
    
    assert len(cycle_completed) >= 1, "至少应完成1个循环"
    print("✅ 循环计数正确")
    
    assert completed.is_set(), "应触发完成事件"
    print("✅ 完成回调已触发")
    
    print("\n✅ 完整冲洗循环测试通过!")
    return True


def test_flusher_evacuate_transfer():
    """测试排空和移液操作"""
    print("\n" + "=" * 60)
    print("测试 4: 排空和移液操作")
    print("=" * 60)
    
    from src.echem_sdl.hardware.flusher import (
        Flusher, FlusherConfig, FlusherPumpConfig,
        FlusherState, FlusherPhase
    )
    
    config = FlusherConfig(
        inlet=FlusherPumpConfig(address=1, name="Inlet", duration_s=0.1),
        transfer=FlusherPumpConfig(address=2, name="Transfer", duration_s=0.1),
        outlet=FlusherPumpConfig(address=3, name="Outlet", duration_s=0.1),
        default_cycles=1
    )
    
    flusher = Flusher(config, pump_manager=None, logger=None, mock_mode=True)
    
    # 测试排空
    evacuate_done = threading.Event()
    flusher.on_complete(lambda: evacuate_done.set())
    
    result = flusher.evacuate(duration_s=0.1)
    assert result == True, "排空应返回 True"
    assert flusher.phase == FlusherPhase.OUTLET, "排空阶段应为 OUTLET"
    print("✅ 排空启动成功")
    
    evacuate_done.wait(timeout=1.0)
    assert evacuate_done.is_set(), "排空应完成"
    print("✅ 排空完成")
    
    # 重置
    flusher.reset()
    
    # 测试移液
    transfer_done = threading.Event()
    flusher.on_complete(lambda: transfer_done.set())
    
    result = flusher.transfer(duration_s=0.1, forward=True)
    assert result == True, "移液应返回 True"
    assert flusher.phase == FlusherPhase.TRANSFER, "移液阶段应为 TRANSFER"
    print("✅ 移液启动成功")
    
    transfer_done.wait(timeout=1.0)
    assert transfer_done.is_set(), "移液应完成"
    print("✅ 移液完成")
    
    print("\n✅ 排空和移液测试通过!")
    return True


def test_rs485_wrapper_flush():
    """测试 RS485Wrapper 冲洗接口"""
    print("\n" + "=" * 60)
    print("测试 5: RS485Wrapper 冲洗接口")
    print("=" * 60)
    
    from src.services.rs485_wrapper import RS485Wrapper
    
    wrapper = RS485Wrapper()
    wrapper.set_mock_mode(True)
    wrapper.open_port("MOCK_PORT", 38400)
    
    # 配置冲洗通道
    result = wrapper.configure_flush_channels(
        inlet_address=1,
        transfer_address=2,
        outlet_address=3,
        inlet_rpm=200,
        transfer_rpm=200,
        outlet_rpm=200,
        inlet_duration_s=0.1,
        transfer_duration_s=0.1,
        outlet_duration_s=0.1,
        default_cycles=2
    )
    assert result == True, "配置冲洗应成功"
    print("✅ 冲洗通道配置成功")
    
    # 获取状态
    status = wrapper.get_flush_status()
    assert status is not None, "应能获取状态"
    assert status["state"] == "idle"
    print("✅ 冲洗状态查询成功")
    
    # 测试启动/停止
    completed = threading.Event()
    
    result = wrapper.start_flush(
        cycles=1,
        on_complete=lambda: completed.set()
    )
    assert result == True, "启动冲洗应成功"
    assert wrapper.is_flushing() == True, "应处于冲洗状态"
    print("✅ 冲洗启动成功")
    
    # 等待完成或超时
    completed.wait(timeout=2.0)
    
    # 验证完成
    time.sleep(0.1)  # 等待状态更新
    status = wrapper.get_flush_status()
    print(f"  最终状态: {status}")
    print("✅ 冲洗流程完成")
    
    # 重置
    wrapper.reset_flusher()
    
    # 测试排空
    evacuate_done = threading.Event()
    result = wrapper.start_evacuate(duration_s=0.1, on_complete=lambda: evacuate_done.set())
    assert result == True, "排空应成功启动"
    print("✅ 排空启动成功")
    
    evacuate_done.wait(timeout=1.0)
    print("✅ 排空完成")
    
    # 重置
    wrapper.reset_flusher()
    
    # 测试移液
    transfer_done = threading.Event()
    result = wrapper.start_transfer(duration_s=0.1, forward=True, on_complete=lambda: transfer_done.set())
    assert result == True, "移液应成功启动"
    print("✅ 移液启动成功")
    
    transfer_done.wait(timeout=1.0)
    print("✅ 移液完成")
    
    wrapper.close_port()
    
    print("\n✅ RS485Wrapper 冲洗接口测试通过!")
    return True


def test_flush_from_config():
    """测试从配置文件配置冲洗"""
    print("\n" + "=" * 60)
    print("测试 6: 从FlushChannel配置")
    print("=" * 60)
    
    from src.services.rs485_wrapper import RS485Wrapper
    from src.models import FlushChannel
    
    wrapper = RS485Wrapper()
    wrapper.set_mock_mode(True)
    wrapper.open_port("MOCK_PORT", 38400)
    
    # 创建 FlushChannel 列表
    channels = [
        FlushChannel(
            channel_id="inlet",
            pump_name="进水泵",
            pump_address=4,
            direction="FWD",
            rpm=150,
            cycle_duration_s=0.1,
            work_type="Inlet"
        ),
        FlushChannel(
            channel_id="transfer",
            pump_name="移液泵",
            pump_address=5,
            direction="FWD",
            rpm=180,
            cycle_duration_s=0.1,
            work_type="Transfer"
        ),
        FlushChannel(
            channel_id="outlet",
            pump_name="出水泵",
            pump_address=6,
            direction="FWD",
            rpm=200,
            cycle_duration_s=0.1,
            work_type="Outlet"
        ),
    ]
    
    result = wrapper.configure_flush_from_config(channels)
    assert result == True, "从配置列表配置应成功"
    print("✅ 从FlushChannel列表配置成功")
    
    # 验证配置
    status = wrapper.get_flush_status()
    assert status is not None
    print("✅ Flusher已正确初始化")
    
    wrapper.close_port()
    
    print("\n✅ FlushChannel配置测试通过!")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  Stage 4 集成测试 - Flusher 冲洗功能")
    print("=" * 70)
    
    tests = [
        ("Flusher 基本功能", test_flusher_basic),
        ("Flusher 生命周期", test_flusher_lifecycle),
        ("完整冲洗循环", test_flusher_full_cycle),
        ("排空和移液", test_flusher_evacuate_transfer),
        ("RS485Wrapper 冲洗接口", test_rs485_wrapper_flush),
        ("FlushChannel配置", test_flush_from_config),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {name} 失败")
        except Exception as e:
            failed += 1
            print(f"❌ {name} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"  测试结果: {passed} 通过, {failed} 失败")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
