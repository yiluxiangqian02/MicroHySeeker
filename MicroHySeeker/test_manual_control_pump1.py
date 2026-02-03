#!/usr/bin/env python
"""
测试手动控制对话框中的泵1控制功能
"""

import sys
sys.path.append("src")

import logging
from src.services.rs485_wrapper import RS485Wrapper

def test_manual_control_pump1():
    """测试手动控制功能"""
    print("🎮 手动控制泵1测试")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # 创建RS485Wrapper（模拟UI中的使用方式）
        print("=== 初始化RS485Wrapper ===")
        rs485 = RS485Wrapper()
        
        # 连接
        print("\n=== 连接COM7 ===")
        if not rs485.open_port('COM7', 38400):
            print("❌ 连接失败")
            return False
        
        print("✅ 连接成功")
        
        # 扫描设备
        print("\n=== 扫描设备 ===")
        online_pumps = rs485.scan_pumps()
        print(f"扫描结果: {online_pumps}")
        
        if 1 not in online_pumps:
            print("❌ 泵1未被扫描到")
        else:
            print("✅ 泵1已被扫描到")
        
        # 测试泵1的启动（模拟手动控制对话框的操作）
        print("\n=== 测试泵1启动（正向，100 RPM）===")
        success = rs485.start_pump(1, "FWD", 100)
        print(f"启动结果: {'✅ 成功' if success else '❌ 失败'}")
        
        import time
        print("运行2秒...")
        time.sleep(2)
        
        # 停止泵1
        print("\n=== 测试泵1停止 ===")
        success = rs485.stop_pump(1)
        print(f"停止结果: {'✅ 成功' if success else '❌ 失败'}")
        
        # 测试反向运行
        print("\n=== 测试泵1反向运行（50 RPM）===")
        success = rs485.start_pump(1, "REV", 50)
        print(f"启动结果: {'✅ 成功' if success else '❌ 失败'}")
        
        print("运行2秒...")
        time.sleep(2)
        
        # 停止
        print("\n=== 再次停止泵1 ===")
        success = rs485.stop_pump(1)
        print(f"停止结果: {'✅ 成功' if success else '❌ 失败'}")
        
        # 断开连接
        rs485.close_port()
        print("\n✅ 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_manual_control_pump1()
