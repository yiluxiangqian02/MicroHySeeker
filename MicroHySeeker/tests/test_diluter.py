"""
Diluter 模块单元测试

测试 Diluter 类的基本功能。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import time
from echem_sdl.hardware.diluter import Diluter, DiluterConfig, DiluterState
from echem_sdl.lib_context import LibContext
from echem_sdl.services.logger_service import LoggerService, LogLevel


def test_diluter_basic():
    """测试 Diluter 基本功能"""
    print("\n=== 测试1: Diluter 基本功能 ===")
    
    # 初始化 LibContext（Mock模式）
    ctx = LibContext(mock_mode=True)
    logger = LoggerService(level=LogLevel.INFO)
    
    # 创建 Diluter 配置
    config = DiluterConfig(
        address=1,
        name="H2SO4",
        stock_concentration=1.0,
        default_rpm=120
    )
    
    # 创建 Diluter 实例
    diluter = Diluter(config, ctx.pump_manager, logger, mock_mode=True)
    
    # 验证初始状态
    assert diluter.state == DiluterState.IDLE, "初始状态应为IDLE"
    assert diluter.target_volume_ul == 0.0, "初始目标体积应为0"
    assert diluter.infused_volume_ul == 0.0, "初始已注入体积应为0"
    
    print("✅ 基本功能测试通过")


def test_volume_conversion():
    """测试体积转换"""
    print("\n=== 测试2: 体积转换 ===")
    
    ctx = LibContext(mock_mode=True)
    logger = LoggerService(level=LogLevel.INFO)
    
    config = DiluterConfig(
        address=1,
        name="H2SO4",
        stock_concentration=1.0
    )
    
    diluter = Diluter(config, ctx.pump_manager, logger, mock_mode=True)
    
    # 测试准备配液：目标浓度 0.1M，总体积 1000μL
    volume = diluter.prepare(target_conc=0.1, total_volume_ul=1000.0)
    
    # 预期：(0.1 / 1.0) * 1000 = 100μL
    expected_volume = 100.0
    assert abs(volume - expected_volume) < 0.01, f"体积计算错误: 预期{expected_volume}, 实际{volume}"
    assert abs(diluter.target_volume_ul - expected_volume) < 0.01, "目标体积设置错误"
    
    print(f"✅ 体积转换正确: 目标浓度0.1M -> 需要注入{volume:.2f}μL")


def test_mock_mode():
    """测试 Mock 模式"""
    print("\n=== 测试3: Mock 模式注液 ===")
    
    ctx = LibContext(mock_mode=True)
    logger = LoggerService(level=LogLevel.INFO)
    
    config = DiluterConfig(
        address=1,
        name="H2SO4",
        stock_concentration=1.0,
        default_rpm=120
    )
    
    diluter = Diluter(config, ctx.pump_manager, logger, mock_mode=True)
    
    # 准备注液
    diluter.prepare(target_conc=0.1, total_volume_ul=1000.0)
    
    # 开始注液
    success = diluter.infuse(volume_ul=100.0)
    assert success, "Mock注液应该成功启动"
    assert diluter.is_infusing, "状态应为INFUSING"
    
    print("⏳ 等待Mock注液完成...")
    
    # 等待足够长时间让Mock注液完成
    # 计算预期时间
    duration = Diluter.calculate_duration(100.0, 120)
    print(f"   预计时长: {duration:.2f}秒")
    
    time.sleep(duration + 0.5)  # 多等0.5秒确保完成
    
    # 验证完成状态
    assert diluter.state == DiluterState.COMPLETED, f"状态应为COMPLETED，实际为{diluter.state}"
    assert abs(diluter.infused_volume_ul - 100.0) < 0.01, "已注入体积应等于目标体积"
    
    print("✅ Mock模式测试通过")


def test_prepare_with_different_concentrations():
    """测试不同浓度计算"""
    print("\n=== 测试4: 不同浓度计算 ===")
    
    ctx = LibContext(mock_mode=True)
    logger = LoggerService(level=LogLevel.INFO)
    
    # 储备浓度 2.0M
    config = DiluterConfig(
        address=1,
        name="NaOH",
        stock_concentration=2.0
    )
    
    diluter = Diluter(config, ctx.pump_manager, logger, mock_mode=True)
    
    # 测试案例
    test_cases = [
        (0.5, 1000.0, 250.0),   # 0.5M -> 250μL
        (1.0, 1000.0, 500.0),   # 1.0M -> 500μL
        (0.1, 500.0, 25.0),     # 0.1M, 500μL总体积 -> 25μL
    ]
    
    for target_conc, total_vol, expected in test_cases:
        volume = diluter.prepare(target_conc, total_vol)
        assert abs(volume - expected) < 0.01, \
            f"浓度{target_conc}M, 总体积{total_vol}μL: 预期{expected}μL, 实际{volume:.2f}μL"
        print(f"   ✓ {target_conc}M, {total_vol}μL -> {volume:.2f}μL")
    
    print("✅ 不同浓度计算测试通过")


def test_stop_and_reset():
    """测试停止和重置"""
    print("\n=== 测试5: 停止和重置 ===")
    
    ctx = LibContext(mock_mode=True)
    logger = LoggerService(level=LogLevel.INFO)
    
    config = DiluterConfig(
        address=1,
        name="H2SO4",
        stock_concentration=1.0
    )
    
    diluter = Diluter(config, ctx.pump_manager, logger, mock_mode=True)
    
    # 开始注液
    diluter.infuse(volume_ul=100.0)
    assert diluter.is_infusing, "应该正在注液"
    
    # 停止
    time.sleep(0.5)  # 等待一小段时间
    success = diluter.stop()
    assert success, "停止应该成功"
    assert not diluter.is_infusing, "停止后不应该正在注液"
    
    # 重置
    diluter.reset()
    assert diluter.state == DiluterState.IDLE, "重置后状态应为IDLE"
    assert diluter.target_volume_ul == 0.0, "重置后目标体积应为0"
    assert diluter.infused_volume_ul == 0.0, "重置后已注入体积应为0"
    
    print("✅ 停止和重置测试通过")


def test_duration_calculation():
    """测试时长计算"""
    print("\n=== 测试6: 时长计算 ===")
    
    # 测试案例：体积(μL), 转速(RPM), 每转微升数, 预期时间(秒)
    test_cases = [
        (100.0, 120, 100.0, 0.5),     # 100μL @ 120RPM -> 0.5秒
        (1000.0, 120, 100.0, 5.0),    # 1000μL @ 120RPM -> 5秒
        (500.0, 60, 100.0, 5.0),      # 500μL @ 60RPM -> 5秒
    ]
    
    for volume, rpm, ul_per_rev, expected in test_cases:
        duration = Diluter.calculate_duration(volume, rpm, ul_per_rev)
        assert abs(duration - expected) < 0.01, \
            f"体积{volume}μL @ {rpm}RPM: 预期{expected}秒, 实际{duration:.2f}秒"
        print(f"   ✓ {volume}μL @ {rpm}RPM -> {duration:.2f}秒")
    
    print("✅ 时长计算测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("Diluter 单元测试")
    print("=" * 60)
    
    try:
        test_diluter_basic()
        test_volume_conversion()
        test_mock_mode()
        test_prepare_with_different_concentrations()
        test_stop_and_reset()
        test_duration_calculation()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
