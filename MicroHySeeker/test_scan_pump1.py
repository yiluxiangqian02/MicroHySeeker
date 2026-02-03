#!/usr/bin/env python
"""
测试扫描功能是否能正常检测到泵1
"""

import sys
sys.path.append("src")  # 添加到搜索路径

import logging
from echem_sdl.hardware.rs485_driver import RS485Driver

def test_pump_scanning():
    """测试泵扫描功能，特别针对泵1的检测"""
    print("🔍 泵扫描测试")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        # 创建RS485驱动
        print("=== 创建RS485驱动 ===")
        driver = RS485Driver(port='COM7', baudrate=38400, logger=logger)
        
        # 打开连接
        if not driver.open():
            print("❌ 无法打开COM7端口")
            return False
            
        print("✅ COM7端口连接成功")
        
        # 扫描所有设备
        print("\n=== 扫描所有设备 ===")
        online_pumps = driver.discover_devices()
        print(f"扫描结果: {online_pumps}")
        
        if 1 in online_pumps:
            print("✅ 泵1已被检测到！")
        else:
            print("❌ 泵1未被检测到")
            
        # 特别测试泵1的连接
        print("\n=== 测试泵1单独扫描 ===")
        pump1_result = driver.discover_devices(addresses=[1])  # 只扫描泵1
        print(f"泵1单独扫描结果: {pump1_result}")
        
        # 测试泵1控制
        print("\n=== 测试泵1控制 ===")
        try:
            # 使能泵1
            result = driver.enable_motor(1, enable=True)
            print(f"泵1使能结果: {result}")
            
            # 启动泵1 (正确的参数顺序: addr, rpm, forward)
            start_result = driver.run_speed(1, 100, True)  # 地址1, 100 RPM, 正转
            print(f"泵1启动结果: {start_result}")
            
            # 停止泵1
            stop_result = driver.run_speed(1, 0, True)  # 速度设为0
            print(f"泵1停止结果: {stop_result}")
            
        except Exception as e:
            print(f"泵1控制测试异常: {e}")
        
        # 关闭连接
        driver.close()
        print("\n✅ 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_pump_scanning()