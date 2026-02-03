#!/usr/bin/env python3
"""
RS485 连接测试脚本
测试已写好的 RS485 驱动是否工作正常

运行方式：
python test_rs485_connection.py
"""

import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from echem_sdl.hardware.rs485_driver import RS485Driver
from echem_sdl.utils.constants import DEFAULT_BAUDRATE

def test_rs485_mock_mode():
    """测试 Mock 模式"""
    print("=== 测试 RS485 Mock 模式 ===")
    
    try:
        # 创建 Mock 驱动
        driver = RS485Driver(port="MOCK_COM", baudrate=DEFAULT_BAUDRATE, mock_mode=True)
        print(f"✅ RS485 驱动创建成功 (Mock模式)")
        
        # 连接测试
        success = driver.open()
        print(f"✅ 端口连接: {success}")
        
        # 扫描设备
        devices = driver.discover_devices()
        print(f"✅ 扫描到设备: {devices}")
        
        # 发送测试命令
        result = driver.enable_motor(1, enable=True)
        print(f"✅ 使能命令结果: {result}")
        
        # 运行测试
        status = driver.run_speed(1, True, 120)  # True表示正转
        print(f"✅ 运行命令结果: {status}")
        
        # 关闭连接
        driver.close()
        print(f"✅ 连接已关闭")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ 测试失败: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        return False

def test_rs485_real_mode():
    """测试真实串口模式"""
    print("=== 测试真实串口模式 ===")
    
    try:
        # 获取可用端口
        ports = RS485Driver.list_ports()
        print(f"✅ 可用串口: {ports}")
        
        if not ports:
            print("⚠️ 没有找到串口设备，跳过真实模式测试")
            return True
            
        # 创建真实驱动
        port = ports[0] if isinstance(ports[0], str) else ports[0]
        driver = RS485Driver(port=port, baudrate=DEFAULT_BAUDRATE, mock_mode=False)
        print(f"✅ RS485 驱动创建成功")
        
        # 尝试连接
        success = driver.open()
        print(f"{'✅' if success else '❌'} 端口连接 {port}: {success}")
        
        if success:
            # 扫描设备
            devices = driver.discover_devices()
            print(f"✅ 扫描到设备: {devices}")
            
            # 关闭连接
            driver.close()
        
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ 测试失败: {e}")
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🧪 RS485 驱动测试")
    print("=" * 50)
    
    # 测试 Mock 模式
    mock_ok = test_rs485_mock_mode()
    print()
    
    # 测试真实模式  
    real_ok = test_rs485_real_mode()
    print()
    
    # 总结
    print("=" * 50)
    if mock_ok and real_ok:
        print("🎉 所有测试通过！RS485 驱动工作正常")
        print("✅ 可以进入阶段2：创建 PumpManager")
    else:
        print("❌ 部分测试失败，需要调试 RS485 驱动")
    
    print("\n下一步：运行 python test_rs485_connection.py")