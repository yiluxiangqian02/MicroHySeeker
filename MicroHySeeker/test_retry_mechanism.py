#!/usr/bin/env python3
"""
测试重试机制是否能解决泵1的通信问题
"""
import sys
sys.path.insert(0, 'src')

from echem_sdl.lib_context import LibContext

def main():
    print("=" * 60)
    print("测试重试机制 - 泵1通信")
    print("=" * 60)
    
    # 通过LibContext获取PumpManager（硬件模式）
    manager = LibContext.get_pump_manager(mock_mode=False)
    
    print("\n连接到 COM7...")
    manager.connect("COM7", 38400, timeout=0.1)
    print("✅ 连接成功")
    
    # 扫描设备（使用5次重试）
    print("\n" + "=" * 60)
    print("扫描设备（每个地址5次重试）")
    print("=" * 60)
    online_pumps = manager.scan_devices(retries=5)
    print(f"\n在线泵: {online_pumps}")
    
    # 测试泵1
    if 1 in online_pumps:
        print("\n" + "=" * 60)
        print("✅ 泵1检测成功！测试启动泵1...")
        print("=" * 60)
        
        result = manager.start_pump(1, "FWD", 100)
        if result:
            print("✅ 泵1启动成功！")
            import time
            time.sleep(3)
            print("\n停止泵1...")
            manager.stop_pump(1)
            print("✅ 泵1已停止")
        else:
            print("❌ 泵1启动失败")
    else:
        print("\n❌ 泵1未检测到，即使经过5次重试")
        print("   这表明泵1确实存在严重的硬件问题")
    
    # 对比测试泵2
    print("\n" + "=" * 60)
    print("对比测试泵2")
    print("=" * 60)
    if 2 in online_pumps:
        result = manager.start_pump(2, "FWD", 100)
        if result:
            print("✅ 泵2启动成功")
            import time
            time.sleep(2)
            manager.stop_pump(2)
            print("✅ 泵2已停止")
    
    manager.disconnect()
    LibContext.reset()
    print("\n✅ 测试完成")

if __name__ == "__main__":
    main()
