#!/usr/bin/env python3
"""
硬件模式调试脚本
用于测试真实RS485硬件连接和泵控制
"""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from services.rs485_wrapper import get_rs485_instance
from echem_sdl.lib_context import LibContext


def test_hardware():
    """测试硬件模式"""
    print("=" * 60)
    print("🔧 硬件模式调试测试")
    print("=" * 60)
    
    # 清理之前的实例
    LibContext.reset()
    
    # 获取RS485实例
    rs485 = get_rs485_instance()
    
    # 设置为硬件模式
    print("\n1️⃣ 设置硬件模式...")
    rs485.set_mock_mode(False)
    
    # 连接串口（根据实际情况修改COM口）
    print("\n2️⃣ 连接串口...")
    port = "COM3"  # 修改为你的实际端口
    baudrate = 38400
    
    success = rs485.open_port(port, baudrate)
    if not success:
        print(f"❌ 连接失败: {port}")
        return False
    
    print(f"✅ 连接成功: {port}@{baudrate}")
    
    # 扫描泵
    print("\n3️⃣ 扫描泵...")
    pumps = rs485.scan_pumps()
    print(f"📊 在线泵: {pumps}")
    
    if not pumps:
        print("❌ 未发现在线泵")
        rs485.close_port()
        return False
    
    # 选择第一个泵进行测试
    test_pump = pumps[0]
    print(f"\n4️⃣ 测试泵 {test_pump}...")
    
    # 启动泵
    print(f"  ▶️ 启动泵 {test_pump}: FWD, 100RPM")
    success = rs485.start_pump(test_pump, "FWD", 100)
    if success:
        print(f"  ✅ 泵 {test_pump} 启动成功")
    else:
        print(f"  ❌ 泵 {test_pump} 启动失败")
        rs485.close_port()
        return False
    
    # 等待3秒
    print("  ⏱️ 运行3秒...")
    for i in range(3, 0, -1):
        print(f"    {i}...")
        time.sleep(1)
    
    # 获取状态
    status = rs485.get_pump_status(test_pump)
    print(f"  📊 泵状态: {status}")
    
    # 停止泵
    print(f"  ⏹️ 停止泵 {test_pump}")
    success = rs485.stop_pump(test_pump)
    if success:
        print(f"  ✅ 泵 {test_pump} 停止成功")
    else:
        print(f"  ❌ 泵 {test_pump} 停止失败")
    
    # 关闭连接
    print("\n5️⃣ 关闭连接...")
    rs485.close_port()
    print("✅ 测试完成")
    
    return True


def interactive_test():
    """交互式测试"""
    print("=" * 60)
    print("🎮 交互式硬件测试")
    print("=" * 60)
    
    LibContext.reset()
    rs485 = get_rs485_instance()
    
    # 询问端口
    print("\n可用端口:")
    ports = rs485.list_available_ports()
    for i, port in enumerate(ports, 1):
        print(f"  {i}. {port}")
    
    port_choice = input(f"\n选择端口 (1-{len(ports)}) [默认: COM3]: ").strip()
    if port_choice.isdigit() and 1 <= int(port_choice) <= len(ports):
        port = ports[int(port_choice) - 1]
    else:
        port = "COM3"
    
    # 询问模式
    mode = input("\n选择模式 (1=Mock, 2=硬件) [默认: 2]: ").strip()
    is_mock = (mode == "1")
    
    rs485.set_mock_mode(is_mock)
    print(f"\n{'🔧 Mock模式' if is_mock else '🔌 硬件模式'}")
    
    # 连接
    print(f"\n连接到 {port}@38400...")
    if not rs485.open_port(port, 38400):
        print("❌ 连接失败")
        return
    
    print("✅ 连接成功")
    
    # 扫描
    print("\n扫描泵...")
    pumps = rs485.scan_pumps()
    print(f"在线泵: {pumps}")
    
    if not pumps:
        print("未发现泵")
        rs485.close_port()
        return
    
    # 交互控制
    while True:
        print("\n" + "=" * 40)
        print("命令:")
        print("  1. 启动泵")
        print("  2. 停止泵")
        print("  3. 查询状态")
        print("  4. 重新扫描")
        print("  0. 退出")
        
        cmd = input("\n请选择: ").strip()
        
        if cmd == "0":
            break
        elif cmd == "1":
            addr = int(input("  泵地址: "))
            rpm = int(input("  转速 (RPM): "))
            direction = input("  方向 (FWD/REV): ").upper()
            rs485.start_pump(addr, direction, rpm)
        elif cmd == "2":
            addr = int(input("  泵地址: "))
            rs485.stop_pump(addr)
        elif cmd == "3":
            addr = int(input("  泵地址: "))
            status = rs485.get_pump_status(addr)
            print(f"  状态: {status}")
        elif cmd == "4":
            pumps = rs485.scan_pumps()
            print(f"  在线泵: {pumps}")
    
    # 关闭
    print("\n关闭连接...")
    rs485.close_port()
    print("✅ 完成")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "-i":
        interactive_test()
    else:
        test_hardware()
