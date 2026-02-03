#!/usr/bin/env python
"""
测试真实硬件的手动控制功能
"""

import sys
sys.path.append("src")

import logging
from src.services.rs485_wrapper import RS485Wrapper

def test_real_hardware():
    """测试真实硬件"""
    print("🔌 真实硬件测试 - 泵1控制")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # 创建RS485Wrapper（不使用Mock模式）
        print("=== 初始化RS485Wrapper（真实硬件）===")
        rs485 = RS485Wrapper()
        rs485.set_mock_mode(False)  # 关闭Mock模式
        
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
        
        # 测试泵1的启动（小速度测试）
        print("\n=== 测试泵1启动（正向，50 RPM）===")
        success = rs485.start_pump(1, "FWD", 50)
        print(f"启动结果: {'✅ 成功' if success else '❌ 失败'}")
        
        if success:
            import time
            print("运行3秒... (请观察泵是否旋转)")
            time.sleep(3)
            
            # 停止泵1
            print("\n=== 停止泵1 ===")
            success = rs485.stop_pump(1)
            print(f"停止结果: {'✅ 成功' if success else '❌ 失败'}")
        
        # 关闭连接
        rs485.close_port()
        print("\n✅ 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_real_hardware()
