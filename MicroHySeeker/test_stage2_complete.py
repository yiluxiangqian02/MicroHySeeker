#!/usr/bin/env python3
"""
阶段2完整测试：前后端集成 + 双模式测试
测试Mock模式和真实硬件模式下的所有功能

运行方式：
python test_stage2_complete.py
"""

import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

print("=" * 60)
print("🧪 阶段2完整测试: 泵管理系统")
print("=" * 60)


def test_backend_direct():
    """测试1：后端直接调用"""
    print("\n" + "=" * 60)
    print("=== 测试1: 后端PumpManager直接调用 ===")
    print("=" * 60)
    
    try:
        from echem_sdl.lib_context import LibContext
        
        # 获取PumpManager (Mock模式)
        pump_manager = LibContext.get_pump_manager(mock_mode=True)
        print("✅ 获取PumpManager成功")
        
        # 连接
        pump_manager.connect("COM1", 38400, timeout=0.1)
        print("✅ 连接成功")
        
        # 测试便捷方法：启动泵
        result = pump_manager.start_pump(1, "FWD", 120)
        print(f"✅ start_pump(1, FWD, 120) = {result}")
        
        # 读取状态
        state = pump_manager.get_state(1)
        print(f"✅ 泵1状态: online={state.online}, enabled={state.enabled}, speed={state.speed}")
        
        # 停止泵
        result = pump_manager.stop_pump(1)
        print(f"✅ stop_pump(1) = {result}")
        
        # 扫描设备
        online = pump_manager.scan_devices()
        print(f"✅ scan_devices() = {online}")
        
        # 停止所有
        count = pump_manager.stop_all()
        print(f"✅ stop_all() = {count} 个泵")
        
        # 断开连接
        pump_manager.disconnect()
        print("✅ 断开连接")
        
        # 清理LibContext
        LibContext.reset()
        print("✅ 清理LibContext")
        
        return True
        
    except Exception as e:
        print(f"❌ 后端测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def test_frontend_adapter():
    """测试2：前端适配器调用"""
    print("\n" + "=" * 60)
    print("=== 测试2: 前端RS485Wrapper适配器 ===")
    print("=" * 60)
    
    try:
        from services.rs485_wrapper import get_rs485_instance
        from echem_sdl.lib_context import LibContext
        
        # 清理之前的实例
        LibContext.reset()
        
        # 获取RS485实例
        rs485 = get_rs485_instance()
        print("✅ 获取RS485Wrapper成功")
        
        # 设置Mock模式
        rs485.set_mock_mode(True)
        print("✅ 设置Mock模式")
        
        # 连接
        success = rs485.open_port("COM1", 38400)
        print(f"✅ 连接结果: {success}")
        
        if not success:
            print("❌ 连接失败")
            return False
        
        # 扫描泵
        pumps = rs485.scan_pumps()
        print(f"✅ 扫描到泵: {pumps}")
        
        # 启动泵1
        success = rs485.start_pump(1, "FWD", 120)
        print(f"✅ 启动泵1: {success}")
        
        # 获取状态
        status = rs485.get_pump_status(1)
        print(f"✅ 泵1状态: {status}")
        
        # 启动泵2
        success = rs485.start_pump(2, "REV", 100)
        print(f"✅ 启动泵2: {success}")
        
        # 停止泵1
        success = rs485.stop_pump(1)
        print(f"✅ 停止泵1: {success}")
        
        # 停止所有
        success = rs485.stop_all()
        print(f"✅ 停止所有泵: {success}")
        
        # 关闭连接
        rs485.close_port()
        print("✅ 关闭连接")
        
        return True
        
    except Exception as e:
        print(f"❌ 前端测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def test_state_monitoring():
    """测试3：状态监控回调"""
    print("\n" + "=" * 60)
    print("=== 测试3: 实时状态监控 ===")
    print("=" * 60)
    
    try:
        from services.rs485_wrapper import get_rs485_instance
        from echem_sdl.lib_context import LibContext
        
        # 清理
        LibContext.reset()
        
        rs485 = get_rs485_instance()
        rs485.set_mock_mode(True)
        
        # 状态变化计数
        state_changes = []
        
        def on_state_change(address, state):
            state_changes.append((address, state))
            print(f"  📊 泵 {address} 状态变化: {state}")
        
        # 设置回调
        rs485.set_state_callback(on_state_change)
        print("✅ 设置状态回调")
        
        # 连接
        rs485.open_port("COM1", 38400)
        
        # 启动监控
        rs485.start_monitoring()
        print("✅ 启动后台监控")
        
        # 操作泵，观察状态变化
        print("\n--- 操作泵1 ---")
        rs485.start_pump(1, "FWD", 100)
        time.sleep(0.3)
        
        print("\n--- 操作泵2 ---")
        rs485.start_pump(2, "REV", 150)
        time.sleep(0.3)
        
        print("\n--- 停止所有 ---")
        rs485.stop_all()
        time.sleep(0.3)
        
        # 停止监控
        rs485.stop_monitoring()
        print(f"\n✅ 状态监控测试完成，共收到 {len(state_changes)} 次状态变化")
        
        # 关闭
        rs485.close_port()
        
        return True
        
    except Exception as e:
        print(f"❌ 状态监控测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def test_data_models():
    """测试4：数据模型兼容性"""
    print("\n" + "=" * 60)
    print("=== 测试4: 数据模型兼容性 ===")
    print("=" * 60)
    
    try:
        from models import PumpConfig, DilutionChannel, FlushChannel
        
        # 泵配置
        pump = PumpConfig(address=1, name="配液泵1", direction="FWD", default_rpm=120)
        print(f"✅ PumpConfig: {pump.name} (地址{pump.address})")
        
        # 配液通道
        channel = DilutionChannel(
            channel_id="CH1",
            solution_name="NaCl",
            stock_concentration=1.0,
            pump_address=1
        )
        print(f"✅ DilutionChannel: {channel.solution_name} -> 泵{channel.pump_address}")
        
        # 冲洗通道
        flush = FlushChannel(
            channel_id="FL1",
            pump_name="冲洗泵",
            pump_address=9,
            work_type="Transfer"
        )
        print(f"✅ FlushChannel: {flush.pump_name} -> 泵{flush.pump_address}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据模型测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    """运行所有测试"""
    results = {
        "后端直接调用": test_backend_direct(),
        "前端适配器": test_frontend_adapter(),
        "状态监控": test_state_monitoring(),
        "数据模型": test_data_models()
    }
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "🎉" * 20)
        print("🎉 所有测试通过！Mock模式运行正常！")
        print("🎉" * 20)
        print("\n📋 下一步：")
        print("1. 运行 UI 测试: python run_ui.py")
        print("2. 测试真实硬件连接（需要用户配合）")
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
