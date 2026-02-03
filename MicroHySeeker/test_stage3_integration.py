"""
阶段3集成测试 - 配液功能完整流程测试

测试 Diluter 与 PumpManager、RS485Wrapper 的集成。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import time
from echem_sdl.lib_context import LibContext
from echem_sdl.hardware.diluter import Diluter, DiluterConfig, DiluterState
from echem_sdl.services.logger_service import LoggerService, LogLevel
from services.rs485_wrapper import get_rs485_instance
from models import DilutionChannel


def test_diluter_with_pump_manager():
    """测试 Diluter 与 PumpManager 集成"""
    print("\n" + "=" * 70)
    print("测试1: Diluter 与 PumpManager 集成")
    print("=" * 70)
    
    # 初始化 LibContext（Mock模式）
    ctx = LibContext(mock_mode=True)
    logger = LoggerService(level=LogLevel.INFO)
    
    # 创建 Diluter
    config = DiluterConfig(
        address=1,
        name="H2SO4",
        stock_concentration=1.0,
        default_rpm=120
    )
    
    diluter = Diluter(config, ctx.pump_manager, logger, mock_mode=True)
    
    # 测试配液流程
    print("\n▶ 步骤1: 准备注液")
    volume = diluter.prepare(target_conc=0.1, total_volume_ul=1000.0)
    print(f"   目标浓度: 0.1M")
    print(f"   总体积: 1000μL")
    print(f"   需要注入: {volume:.2f}μL")
    assert abs(volume - 100.0) < 0.01, "体积计算错误"
    
    print("\n▶ 步骤2: 开始注液")
    success = diluter.infuse()
    assert success, "启动失败"
    print(f"   状态: {diluter.state.value}")
    assert diluter.is_infusing, "应该正在注液"
    
    print("\n▶ 步骤3: 等待完成")
    duration = diluter.estimated_duration
    print(f"   预计时长: {duration:.2f}秒")
    time.sleep(duration + 0.5)
    
    print("\n▶ 步骤4: 验证完成")
    print(f"   状态: {diluter.state.value}")
    print(f"   进度: {diluter.get_progress():.1f}%")
    print(f"   已注入: {diluter.infused_volume_ul:.2f}μL")
    assert diluter.state == DiluterState.COMPLETED, "应该已完成"
    assert abs(diluter.infused_volume_ul - 100.0) < 0.01, "注入体积错误"
    
    print("\n✅ 测试1通过：Diluter 与 PumpManager 集成正常")


def test_rs485_wrapper_dilution():
    """测试 RS485Wrapper 配液接口"""
    print("\n" + "=" * 70)
    print("测试2: RS485Wrapper 配液接口")
    print("=" * 70)
    
    wrapper = get_rs485_instance()
    wrapper.set_mock_mode(True)
    
    # 模拟连接
    print("\n▶ 步骤1: 连接RS485")
    success = wrapper.open_port("COM3", 38400)
    assert success, "连接失败"
    print("   ✓ 连接成功")
    
    # 配置通道
    print("\n▶ 步骤2: 配置配液通道")
    channels = [
        DilutionChannel(
            channel_id="1",
            solution_name="H2SO4",
            stock_concentration=1.0,
            pump_address=1,
            direction="FWD",
            default_rpm=120,
            color="#FF0000"
        ),
        DilutionChannel(
            channel_id="2",
            solution_name="NaOH",
            stock_concentration=2.0,
            pump_address=2,
            direction="FWD",
            default_rpm=120,
            color="#00FF00"
        )
    ]
    
    success = wrapper.configure_dilution_channels(channels)
    assert success, "配置通道失败"
    print(f"   ✓ 已配置 {len(channels)} 个通道")
    
    # 测试准备配液
    print("\n▶ 步骤3: 准备配液")
    volume = wrapper.prepare_dilution(1, target_conc=0.1, total_volume_ul=1000.0)
    print(f"   通道1需要注入: {volume:.2f}μL")
    assert abs(volume - 100.0) < 0.01, "体积计算错误"
    
    # 开始配液
    print("\n▶ 步骤4: 开始配液")
    success = wrapper.start_dilution(1, volume_ul=100.0)
    assert success, "启动配液失败"
    print("   ✓ 配液已启动")
    
    # 查询进度
    print("\n▶ 步骤5: 查询进度")
    progress = wrapper.get_dilution_progress(1)
    print(f"   状态: {progress['state']}")
    print(f"   进度: {progress['progress']:.1f}%")
    assert progress['state'] == 'infusing', "状态应为infusing"
    
    # 等待完成
    print("\n▶ 步骤6: 等待完成")
    duration = Diluter.calculate_duration(100.0, 120)
    print(f"   预计时长: {duration:.2f}秒")
    time.sleep(duration + 0.5)
    
    # 验证完成
    print("\n▶ 步骤7: 验证完成")
    progress = wrapper.get_dilution_progress(1)
    print(f"   状态: {progress['state']}")
    print(f"   进度: {progress['progress']:.1f}%")
    print(f"   已注入: {progress['infused_volume_ul']:.2f}μL")
    assert progress['state'] == 'completed', "状态应为completed"
    
    # 关闭连接
    print("\n▶ 步骤8: 关闭连接")
    wrapper.close_port()
    print("   ✓ 连接已关闭")
    
    print("\n✅ 测试2通过：RS485Wrapper 配液接口正常")


def test_multiple_channels():
    """测试多通道配液"""
    print("\n" + "=" * 70)
    print("测试3: 多通道配液")
    print("=" * 70)
    
    wrapper = get_rs485_instance()
    wrapper.set_mock_mode(True)
    
    # 连接
    print("\n▶ 步骤1: 连接RS485")
    wrapper.open_port("COM3", 38400)
    
    # 配置3个通道
    print("\n▶ 步骤2: 配置3个通道")
    channels = [
        DilutionChannel("1", "H2SO4", 1.0, 1, "FWD", 120, "#FF0000"),
        DilutionChannel("2", "NaOH", 2.0, 2, "FWD", 120, "#00FF00"),
        DilutionChannel("3", "HCl", 0.5, 3, "FWD", 120, "#0000FF"),
    ]
    wrapper.configure_dilution_channels(channels)
    print(f"   ✓ 已配置 {len(channels)} 个通道")
    
    # 为每个通道准备配液
    print("\n▶ 步骤3: 准备配液")
    target_conc = 0.1
    total_volume = 1000.0
    
    volumes = {}
    for i, ch in enumerate(channels, 1):
        vol = wrapper.prepare_dilution(i, target_conc, total_volume)
        volumes[i] = vol
        expected = (target_conc / ch.stock_concentration) * total_volume
        print(f"   通道{i} ({ch.solution_name}): {vol:.2f}μL (预期{expected:.2f}μL)")
        assert abs(vol - expected) < 0.01, f"通道{i}体积计算错误"
    
    # 依次启动各通道
    print("\n▶ 步骤4: 依次启动各通道")
    for i in range(1, 4):
        success = wrapper.start_dilution(i, volumes[i])
        assert success, f"通道{i}启动失败"
        print(f"   ✓ 通道{i}已启动")
    
    # 等待所有通道完成
    print("\n▶ 步骤5: 等待所有通道完成")
    max_duration = max(Diluter.calculate_duration(v, 120) for v in volumes.values())
    print(f"   最长时长: {max_duration:.2f}秒")
    time.sleep(max_duration + 1.0)
    
    # 验证所有通道完成
    print("\n▶ 步骤6: 验证所有通道")
    for i in range(1, 4):
        progress = wrapper.get_dilution_progress(i)
        print(f"   通道{i}: 状态={progress['state']}, 进度={progress['progress']:.1f}%")
        assert progress['state'] == 'completed', f"通道{i}应该已完成"
    
    # 关闭
    wrapper.close_port()
    
    print("\n✅ 测试3通过：多通道配液正常")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 70)
    print("测试4: 错误处理")
    print("=" * 70)
    
    wrapper = get_rs485_instance()
    wrapper.set_mock_mode(True)
    
    # 测试未连接时的操作
    print("\n▶ 测试1: 未连接时配置通道")
    wrapper.close_port()
    channels = [DilutionChannel("1", "H2SO4", 1.0, 1, "FWD", 120, "#FF0000")]
    success = wrapper.configure_dilution_channels(channels)
    assert not success, "未连接时应该失败"
    print("   ✓ 正确返回失败")
    
    # 测试未配置通道时启动
    print("\n▶ 测试2: 未配置通道时启动")
    wrapper.open_port("COM3", 38400)
    success = wrapper.start_dilution(99, 100.0)
    assert not success, "未配置通道应该失败"
    print("   ✓ 正确返回失败")
    
    # 测试查询未配置通道的进度
    print("\n▶ 测试3: 查询未配置通道")
    progress = wrapper.get_dilution_progress(99)
    assert progress['state'] == 'error', "应该返回错误状态"
    print(f"   ✓ 正确返回错误: {progress.get('error', 'N/A')}")
    
    wrapper.close_port()
    
    print("\n✅ 测试4通过：错误处理正常")


if __name__ == "__main__":
    print("=" * 70)
    print("阶段3集成测试 - 配液功能")
    print("=" * 70)
    
    try:
        test_diluter_with_pump_manager()
        test_rs485_wrapper_dilution()
        test_multiple_channels()
        test_error_handling()
        
        print("\n" + "=" * 70)
        print("🎉 所有集成测试通过！")
        print("=" * 70)
        print("\n✅ 阶段3开发完成，可以进行前端验证")
        
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
