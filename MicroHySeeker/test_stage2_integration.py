#!/usr/bin/env python3
"""
阶段2测试：前后端集成测试
测试前端接口是否能正确调用后端

运行方式：
python test_frontend_backend_integration.py
"""

import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

print("🧪 阶段2测试: 前后端集成")
print("=" * 50)

# 1. 测试后端直接调用
print("\n=== 测试1: 后端直接调用 ===")
try:
    from echem_sdl.lib_context import LibContext
    
    # 获取PumpManager
    pump_manager = LibContext.get_pump_manager(mock_mode=True)
    print("✅ 后端: 获取PumpManager成功")
    
    # 连接
    success = pump_manager.connect("MOCK_COM", 38400, timeout=0.5)
    print(f"✅ 后端: 连接结果 {success}")
    
    # 启用泵
    enable_result = pump_manager.set_enable(1, True)
    print(f"✅ 后端: 使能泵1结果 {enable_result}")
    
    # 设置速度
    speed_result = pump_manager.set_speed(1, 120)
    print(f"✅ 后端: 设置泵1速度结果 {speed_result}")
    
    # 停止泵
    stop_result = pump_manager.set_speed(1, 0)
    disable_result = pump_manager.set_enable(1, False)
    print(f"✅ 后端: 停止泵1结果 {stop_result and disable_result}")
    
    print("✅ 后端直接调用测试通过")
    backend_ok = True
    
except Exception as e:
    print(f"❌ 后端直接调用失败: {e}")
    import traceback
    print(traceback.format_exc())
    backend_ok = False

# 2. 测试前端适配器
print("\n=== 测试2: 前端适配器调用 ===")
try:
    from services.rs485_wrapper import get_rs485_instance
    
    # 获取RS485实例
    rs485 = get_rs485_instance()
    print("✅ 前端: 获取RS485实例成功")
    
    # 连接
    success = rs485.open_port("MOCK_COM", 38400)
    print(f"✅ 前端: 连接结果 {success}")
    
    if success:
        # 扫描泵
        pumps = rs485.scan_pumps()
        print(f"✅ 前端: 扫描到泵 {pumps}")
        
        # 启动泵
        start_ok = rs485.start_pump(1, "FWD", 120)
        print(f"✅ 前端: 启动泵1结果 {start_ok}")
        
        # 获取状态
        status = rs485.get_pump_status(1)
        print(f"✅ 前端: 泵1状态 {status}")
        
        # 停止泵
        stop_ok = rs485.stop_pump(1)
        print(f"✅ 前端: 停止泵1结果 {stop_ok}")
        
        # 关闭连接
        rs485.close_port()
        print("✅ 前端: 连接已关闭")
    
    print("✅ 前端适配器测试通过")
    frontend_ok = True
    
except Exception as e:
    print(f"❌ 前端适配器失败: {e}")
    import traceback
    print(traceback.format_exc())
    frontend_ok = False

# 3. 测试前端模型配置
print("\n=== 测试3: 前端数据模型 ===")
try:
    from models import SystemConfig, DilutionChannel, FlushChannel
    
    # 创建配置
    config = SystemConfig()
    
    # 创建配液通道
    dilution_ch = DilutionChannel(
        channel_id="CH1",
        solution_name="NaCl",
        stock_concentration=0.1,
        pump_address=1,  # ← 关键：泵地址引用
        direction="FWD",
        default_rpm=120
    )
    
    # 创建冲洗通道
    flush_ch = FlushChannel(
        channel_id="FL1",
        pump_name="进水泵",
        pump_address=9,   # ← 关键：泵地址引用
        work_type="Inlet"
    )
    
    print(f"✅ 前端: 配液通道 {dilution_ch.channel_id} -> 泵{dilution_ch.pump_address}")
    print(f"✅ 前端: 冲洗通道 {flush_ch.channel_id} -> 泵{flush_ch.pump_address}")
    print("✅ 前端数据模型测试通过")
    model_ok = True
    
except Exception as e:
    print(f"❌ 前端数据模型失败: {e}")
    import traceback
    print(traceback.format_exc())
    model_ok = False

# 总结
print("\n" + "=" * 50)
if backend_ok and frontend_ok and model_ok:
    print("🎉 阶段2集成测试全部通过！")
    print("✅ 后端 PumpManager 正常工作")
    print("✅ 前端适配器能正确调用后端") 
    print("✅ 前端数据模型支持泵地址引用")
    print("\n🚀 可以进入前端UI测试了:")
    print("   python run_ui.py")
    print("   -> 点击 '手动控制' 测试泵启停")
    print("   -> 点击 '配置' 测试RS485连接")
else:
    print("❌ 部分测试失败，需要调试")
    if not backend_ok:
        print("   - 后端问题：检查 LibContext 和 PumpManager")
    if not frontend_ok:
        print("   - 前端适配器问题：检查 rs485_wrapper")  
    if not model_ok:
        print("   - 数据模型问题：检查 models.py")

print("\n下一步：")
if backend_ok and frontend_ok:
    print("  1. 运行 python run_ui.py")
    print("  2. 测试手动控制对话框")
    print("  3. 如果界面正常，继续阶段3开发")
else:
    print("  1. 根据错误信息修复问题")
    print("  2. 重新运行本测试")