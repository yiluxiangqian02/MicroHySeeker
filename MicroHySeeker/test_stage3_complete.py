"""
阶段3完整测试脚本 - Mock模式和硬件模式

测试完整的配液流程。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import time
from services.rs485_wrapper import get_rs485_instance
from models import SystemConfig, DilutionChannel


def test_mock_mode():
    """测试Mock模式配液"""
    print("\n" + "=" * 70)
    print("测试1: Mock模式配液流程")
    print("=" * 70)
    
    # 获取RS485实例
    rs485 = get_rs485_instance()
    rs485.set_mock_mode(True)
    
    # 连接
    print("\n▶ 步骤1: 连接RS485 (Mock模式)")
    success = rs485.open_port("COM3", 38400)
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
        ),
    ]
    
    success = rs485.configure_dilution_channels(channels)
    assert success, "配置失败"
    print(f"   ✓ 已配置 {len(channels)} 个通道")
    
    # 测试配液
    print("\n▶ 步骤3: 测试配液 - 目标浓度0.1M, 总体积1000μL")
    
    # 通道1: H2SO4
    print("\n   通道1: H2SO4 (1.0M -> 0.1M)")
    volume1 = rs485.prepare_dilution(1, 0.1, 1000.0)
    print(f"   需要注入: {volume1:.2f}μL (预期100μL)")
    
    success = rs485.start_dilution(1, volume1)
    assert success, "启动失败"
    print("   ✓ 配液已启动")
    
    # 等待完成
    from echem_sdl.hardware.diluter import Diluter
    duration = Diluter.calculate_duration(volume1, 120)
    print(f"   预计时长: {duration:.2f}秒")
    
    time.sleep(duration + 0.5)
    
    # 检查完成状态
    progress = rs485.get_dilution_progress(1)
    print(f"   状态: {progress['state']}")
    print(f"   进度: {progress['progress']:.1f}%")
    assert progress['state'] == 'completed', "应该已完成"
    print("   ✓ 通道1配液完成")
    
    # 通道2: NaOH
    print("\n   通道2: NaOH (2.0M -> 0.1M)")
    volume2 = rs485.prepare_dilution(2, 0.1, 1000.0)
    print(f"   需要注入: {volume2:.2f}μL (预期50μL)")
    
    success = rs485.start_dilution(2, volume2)
    assert success, "启动失败"
    
    duration = Diluter.calculate_duration(volume2, 120)
    print(f"   预计时长: {duration:.2f}秒")
    time.sleep(duration + 0.5)
    
    progress = rs485.get_dilution_progress(2)
    print(f"   状态: {progress['state']}")
    print(f"   进度: {progress['progress']:.1f}%")
    assert progress['state'] == 'completed', "应该已完成"
    print("   ✓ 通道2配液完成")
    
    # 关闭
    print("\n▶ 步骤4: 关闭连接")
    rs485.close_port()
    print("   ✓ 连接已关闭")
    
    print("\n✅ Mock模式测试通过")


def test_hardware_mode():
    """测试硬件模式配液"""
    print("\n" + "=" * 70)
    print("测试2: 硬件模式配液流程")
    print("=" * 70)
    
    # 获取RS485实例
    rs485 = get_rs485_instance()
    rs485.set_mock_mode(False)
    
    # 连接真实硬件
    print("\n▶ 步骤1: 连接真实RS485硬件")
    print("   可用端口:", rs485.list_available_ports())
    
    # 尝试连接
    port = "COM3"  # 根据实际情况修改
    success = rs485.open_port(port, 38400)
    if not success:
        print(f"   ✗ 无法连接到 {port}")
        print("   跳过硬件测试")
        return
    
    print(f"   ✓ 已连接到 {port}")
    
    # 扫描设备
    print("\n▶ 步骤2: 扫描泵设备")
    online_pumps = rs485.scan_pumps()
    print(f"   在线泵: {online_pumps}")
    
    if not online_pumps:
        print("   ✗ 未发现任何泵")
        print("   跳过硬件测试")
        rs485.close_port()
        return
    
    # 配置通道（使用扫描到的第一个泵）
    print("\n▶ 步骤3: 配置配液通道（使用泵1）")
    channels = [
        DilutionChannel(
            channel_id="1",
            solution_name="测试溶液",
            stock_concentration=1.0,
            pump_address=1,
            direction="FWD",
            default_rpm=120,
            color="#FF0000"
        )
    ]
    
    success = rs485.configure_dilution_channels(channels)
    assert success, "配置失败"
    print("   ✓ 通道配置完成")
    
    # 测试配液（小体积）
    print("\n▶ 步骤4: 测试配液（小体积：10μL）")
    volume = 10.0  # 小体积测试
    
    success = rs485.start_dilution(1, volume)
    if not success:
        print("   ✗ 启动配液失败")
        rs485.close_port()
        return
    
    print(f"   ✓ 配液已启动: {volume}μL")
    
    # 监控进度
    print("\n   监控进度:")
    from echem_sdl.hardware.diluter import Diluter
    duration = Diluter.calculate_duration(volume, 120)
    max_wait = duration + 5.0
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        progress = rs485.get_dilution_progress(1)
        state = progress['state']
        percent = progress['progress']
        
        print(f"     {percent:5.1f}% - {state}", end='\r')
        
        if state == 'completed':
            print()  # 换行
            break
        elif state == 'error':
            print("\n   ✗ 配液出错")
            break
        
        time.sleep(0.5)
    
    # 验证完成
    progress = rs485.get_dilution_progress(1)
    if progress['state'] == 'completed':
        print("   ✓ 硬件配液完成")
    else:
        print(f"   ⚠️ 配液未完成，最终状态: {progress['state']}")
    
    # 关闭
    print("\n▶ 步骤5: 关闭连接")
    rs485.close_port()
    print("   ✓ 连接已关闭")
    
    print("\n✅ 硬件模式测试完成")


def main():
    print("=" * 70)
    print("阶段3完整测试 - 配液功能")
    print("=" * 70)
    
    try:
        # 先测试Mock模式
        test_mock_mode()
        
        # 询问是否测试硬件
        print("\n" + "=" * 70)
        response = input("是否测试真实硬件？(y/n): ").strip().lower()
        if response == 'y':
            test_hardware_mode()
        else:
            print("跳过硬件测试")
        
        print("\n" + "=" * 70)
        print("🎉 所有测试完成！")
        print("=" * 70)
        
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


if __name__ == "__main__":
    main()
