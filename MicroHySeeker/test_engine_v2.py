"""
引擎 V2 集成测试

测试内容：
1. StepState 位标志枚举
2. BatchInjectionManager 多批次注入
3. StepValidator 步骤验证
4. ExperimentEngineV2 状态机
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_step_state():
    """测试步骤状态位标志"""
    print("\n=== 测试 StepState 位标志 ===")
    
    from src.core.step_state import StepState
    
    # 测试基本状态
    assert StepState.IDLE == 0
    assert StepState.BUSY == 1
    assert StepState.NEXT_SOL == 2
    assert StepState.END == 4
    
    # 测试状态组合
    busy_next = StepState.BUSY | StepState.NEXT_SOL
    print(f"BUSY | NEXT_SOL = {busy_next} (值: {int(busy_next)})")
    assert int(busy_next) == 3
    
    # 测试状态检查
    assert busy_next.is_running() == True
    assert busy_next.needs_next_batch() == True
    assert busy_next.is_completed() == False
    
    # 测试完成状态
    end_state = StepState.END
    assert end_state.is_completed() == True
    assert end_state.is_success() == True
    
    # 测试失败状态
    failed = StepState.END | StepState.FAILED
    assert failed.is_completed() == True
    assert failed.is_success() == False
    
    print("✅ StepState 测试通过")


def test_batch_injection():
    """测试多批次注入管理器"""
    print("\n=== 测试 BatchInjectionManager ===")
    
    from src.core.batch_injection import BatchInjectionManager
    from src.core.step_state import StepState
    
    manager = BatchInjectionManager()
    
    # 配置通道
    channels = [
        {"name": "HCl", "channel_id": 1, "volume_ul": 1000, "inject_order": 1},
        {"name": "NaOH", "channel_id": 2, "volume_ul": 500, "inject_order": 1},
        {"name": "水", "channel_id": 3, "volume_ul": 8500, "inject_order": 2},
    ]
    
    batch_count = manager.configure(channels, batch_by_inject_order=True)
    print(f"配置了 {batch_count} 个批次")
    assert batch_count == 2  # 两个 inject_order 值
    
    # 获取批次摘要
    summary = manager.get_batch_summary()
    print(f"批次 1: {summary[0]['channels']}")
    print(f"批次 2: {summary[1]['channels']}")
    
    # 测试启动
    assert manager.start() == True
    assert manager.is_active == True
    
    # 获取状态
    state = manager.get_state()
    print(f"启动后状态: {state}")
    assert state == StepState.BUSY
    
    # 模拟通道完成
    manager.mark_channel_complete("HCl")
    manager.mark_channel_complete("NaOH")
    
    # 更新并检查是否需要下一批
    state = manager.update()
    print(f"批次1完成后状态: {state}")
    
    # 继续直到完成
    manager.mark_channel_complete("水")
    state = manager.update()
    print(f"最终状态: {state}")
    assert state == StepState.END
    
    print("✅ BatchInjectionManager 测试通过")


def test_step_validator():
    """测试步骤验证器"""
    print("\n=== 测试 StepValidator ===")
    
    from src.core.step_validator import StepValidator, ValidationLevel
    from src.models import ProgStep, ProgramStepType, PrepSolStep, ECSettings, ECTechnique, SystemConfig, DilutionChannel
    
    # 创建配置
    config = SystemConfig(
        dilution_channels=[
            DilutionChannel(channel_id="ch1", solution_name="HCl", pump_address=1, stock_concentration=1.0),
            DilutionChannel(channel_id="ch2", solution_name="水", pump_address=2, stock_concentration=0.0),
        ]
    )
    
    validator = StepValidator(config)
    
    # 测试移液验证
    transfer_step = ProgStep(
        step_id="t1",
        step_type=ProgramStepType.TRANSFER,
        pump_address=1,
        pump_rpm=100,
        transfer_duration=10.0
    )
    result = validator.validate_step(transfer_step)
    print(f"移液验证: is_valid={result.is_valid}")
    assert result.is_valid == True
    
    # 测试无泵地址
    bad_transfer = ProgStep(
        step_id="t2",
        step_type=ProgramStepType.TRANSFER,
        pump_address=None,
        pump_rpm=100,
        transfer_duration=10.0
    )
    result = validator.validate_step(bad_transfer)
    print(f"无泵地址验证: is_valid={result.is_valid}, errors={result.error_messages}")
    assert result.is_valid == False
    
    # 测试配液验证
    prep_step = ProgStep(
        step_id="p1",
        step_type=ProgramStepType.PREP_SOL,
        prep_sol_params=PrepSolStep(
            total_volume_ul=100000,
            selected_solutions={"HCl": True, "水": True},
            target_concentrations={"HCl": 0.1, "水": 0},
            solvent_flags={"HCl": False, "水": True},
            injection_order=["HCl", "水"]
        )
    )
    result = validator.validate_step(prep_step)
    print(f"配液验证: is_valid={result.is_valid}")
    for msg in result.messages:
        print(f"  {msg}")
    assert result.is_valid == True
    
    # 测试浓度超标
    bad_prep = ProgStep(
        step_id="p2",
        step_type=ProgramStepType.PREP_SOL,
        prep_sol_params=PrepSolStep(
            total_volume_ul=100000,
            selected_solutions={"HCl": True},
            target_concentrations={"HCl": 2.0},  # 超过母液浓度 1.0
            solvent_flags={"HCl": False},
            injection_order=["HCl"]
        )
    )
    result = validator.validate_step(bad_prep)
    print(f"浓度超标验证: is_valid={result.is_valid}, errors={result.error_messages}")
    assert result.is_valid == False
    
    # 测试电化学验证
    echem_step = ProgStep(
        step_id="e1",
        step_type=ProgramStepType.ECHEM,
        ec_settings=ECSettings(
            technique=ECTechnique.CV,
            e0=0.0,
            eh=0.8,
            el=-0.2,
            scan_rate=0.05,
            seg_num=2
        )
    )
    result = validator.validate_step(echem_step)
    print(f"电化学验证: is_valid={result.is_valid}")
    assert result.is_valid == True
    
    print("✅ StepValidator 测试通过")


def test_engine_state():
    """测试引擎状态机"""
    print("\n=== 测试 EngineState ===")
    
    from src.core.step_state import EngineState
    
    # 测试状态
    idle = EngineState.IDLE
    assert idle.can_start() == True
    assert idle.is_active() == False
    
    running = EngineState.RUNNING
    assert running.can_start() == False
    assert running.is_active() == True
    
    paused = EngineState.PAUSED
    assert paused.is_active() == True
    
    completed = EngineState.COMPLETED
    assert completed.can_start() == True
    
    print(f"IDLE: can_start={idle.can_start()}, is_active={idle.is_active()}")
    print(f"RUNNING: can_start={running.can_start()}, is_active={running.is_active()}")
    print(f"PAUSED: is_active={paused.is_active()}")
    print(f"COMPLETED: can_start={completed.can_start()}")
    
    print("✅ EngineState 测试通过")


def test_step_timing():
    """测试步骤计时"""
    print("\n=== 测试 StepTiming ===")
    
    from src.core.step_state import StepTiming
    import time
    
    timing = StepTiming(estimated_duration_s=5.0)
    
    # 开始计时
    timing.start()
    time.sleep(0.5)
    
    elapsed = timing.elapsed_seconds
    progress = timing.progress
    remaining = timing.remaining_seconds
    
    print(f"已运行: {elapsed:.2f}s")
    print(f"进度: {progress*100:.1f}%")
    print(f"剩余: {remaining:.2f}s")
    
    assert elapsed >= 0.4 and elapsed <= 0.6
    assert progress >= 0.08 and progress <= 0.12
    
    # 停止计时
    timing.stop()
    print(f"实际时长: {timing.actual_duration_s:.2f}s")
    
    print("✅ StepTiming 测试通过")


def test_step_summary():
    """测试步骤摘要"""
    print("\n=== 测试步骤摘要 ===")
    
    from src.core.step_validator import get_step_summary
    from src.models import ProgStep, ProgramStepType, PrepSolStep, ECSettings, ECTechnique
    
    # 移液摘要
    transfer = ProgStep(
        step_id="t1",
        step_type=ProgramStepType.TRANSFER,
        pump_address=1,
        pump_direction="FWD",
        pump_rpm=100,
        transfer_duration=10.0
    )
    print(f"移液: {get_step_summary(transfer)}")
    
    # 配液摘要
    prep = ProgStep(
        step_id="p1",
        step_type=ProgramStepType.PREP_SOL,
        prep_sol_params=PrepSolStep(
            total_volume_ul=100000,
            selected_solutions={"HCl": True, "水": True},
            target_concentrations={"HCl": 0.1},
            solvent_flags={"水": True},
            injection_order=["HCl", "水"]
        )
    )
    print(f"配液: {get_step_summary(prep)}")
    
    # 电化学摘要
    echem = ProgStep(
        step_id="e1",
        step_type=ProgramStepType.ECHEM,
        ec_settings=ECSettings(
            technique=ECTechnique.CV,
            el=-0.2,
            eh=0.8,
            scan_rate=0.05
        )
    )
    print(f"电化学: {get_step_summary(echem)}")
    
    print("✅ 步骤摘要测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("开始测试引擎 V2 组件")
    print("=" * 50)
    
    try:
        test_step_state()
        test_engine_state()
        test_step_timing()
        test_batch_injection()
        test_step_validator()
        test_step_summary()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
