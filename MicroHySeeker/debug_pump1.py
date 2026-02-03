"""
泵1通信完整调试脚本
逐层测试通信链路，找出问题所在
"""
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# ============================================================================
# 测试1: 直接使用 pyserial 测试原始通信
# ============================================================================
def test_raw_serial():
    """直接使用pyserial测试，绕过所有封装"""
    print("\n" + "="*60)
    print("测试1: 直接使用 pyserial 原始通信")
    print("="*60)
    
    try:
        import serial
    except ImportError:
        print("❌ pyserial 未安装")
        return False
    
    port = "COM7"
    baudrate = 38400
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            stopbits=2,
            parity='N',
            timeout=0.5
        )
        print(f"✅ 串口打开成功: {port}@{baudrate}")
    except Exception as e:
        print(f"❌ 串口打开失败: {e}")
        return False
    
    # 构建泵1的速度命令帧 (与MKS软件完全一致)
    # FA 01 F6 80 64 10 E5 - 启动泵1, 正向100RPM
    tx_frame = bytes([0xFA, 0x01, 0xF6, 0x80, 0x64, 0x10, 0xE5])
    
    print(f"\n发送帧: {' '.join(f'{b:02X}' for b in tx_frame)}")
    
    # 清空接收缓冲区
    ser.reset_input_buffer()
    
    # 发送
    ser.write(tx_frame)
    print("✅ 发送完成")
    
    # 等待响应
    time.sleep(0.3)
    
    # 读取响应
    response = ser.read(100)
    if response:
        print(f"✅ 收到响应: {' '.join(f'{b:02X}' for b in response)}")
    else:
        print("❌ 无响应 (超时)")
    
    # 发送停止命令
    stop_frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10, 0x01])
    print(f"\n发送停止帧: {' '.join(f'{b:02X}' for b in stop_frame)}")
    ser.write(stop_frame)
    time.sleep(0.3)
    response = ser.read(100)
    if response:
        print(f"✅ 停止响应: {' '.join(f'{b:02X}' for b in response)}")
    else:
        print("❌ 停止无响应")
    
    ser.close()
    print("串口已关闭")
    return True


# ============================================================================
# 测试2: 使用 RS485Driver 测试
# ============================================================================
def test_rs485_driver():
    """测试RS485Driver层"""
    print("\n" + "="*60)
    print("测试2: 使用 RS485Driver 测试")
    print("="*60)
    
    from echem_sdl.hardware.rs485_driver import RS485Driver
    from echem_sdl.hardware.rs485_protocol import frame_to_hex
    
    driver = RS485Driver(port="COM7", baudrate=38400, mock_mode=False)
    
    received_frames = []
    
    def on_frame(addr, cmd, payload):
        print(f"  📥 回调收到: addr={addr}, cmd=0x{cmd:02X}, payload={payload.hex()}")
        received_frames.append((addr, cmd, payload))
    
    driver.set_callback(on_frame)
    
    try:
        driver.open()
        print("✅ RS485Driver 打开成功")
    except Exception as e:
        print(f"❌ RS485Driver 打开失败: {e}")
        return False
    
    time.sleep(0.2)
    
    # 测试泵1
    print("\n--- 测试泵1 ---")
    received_frames.clear()
    
    # 使用 send_frame 发送
    print("发送速度命令 (0xF6, 正向100RPM)...")
    success = driver.send_frame(addr=1, cmd=0xF6, payload=bytes([0x80, 0x64, 0x10]))
    print(f"  send_frame 返回: {success}")
    
    time.sleep(0.5)
    print(f"  收到 {len(received_frames)} 个响应帧")
    
    # 停止泵1
    print("\n发送停止命令...")
    driver.send_frame(addr=1, cmd=0xF6, payload=bytes([0x00, 0x00, 0x10]))
    time.sleep(0.3)
    
    # 测试泵2作为对比
    print("\n--- 测试泵2 (对比) ---")
    received_frames.clear()
    
    print("发送速度命令到泵2...")
    driver.send_frame(addr=2, cmd=0xF6, payload=bytes([0x80, 0x64, 0x10]))
    time.sleep(0.5)
    print(f"  收到 {len(received_frames)} 个响应帧")
    
    # 停止泵2
    driver.send_frame(addr=2, cmd=0xF6, payload=bytes([0x00, 0x00, 0x10]))
    time.sleep(0.3)
    
    driver.close()
    print("\nRS485Driver 已关闭")
    return True


# ============================================================================
# 测试3: 使用 PumpManager 测试
# ============================================================================
def test_pump_manager():
    """测试PumpManager层"""
    print("\n" + "="*60)
    print("测试3: 使用 PumpManager 测试")
    print("="*60)
    
    from echem_sdl.lib_context import LibContext
    
    # 重置LibContext确保干净状态
    LibContext.reset()
    
    pm = LibContext.get_pump_manager(mock_mode=False)
    print(f"✅ 获取 PumpManager (mock_mode=False)")
    
    try:
        pm.connect("COM7", 38400, timeout=0.1)
        print("✅ PumpManager 连接成功")
    except Exception as e:
        print(f"❌ PumpManager 连接失败: {e}")
        return False
    
    time.sleep(0.3)
    
    # 测试泵1
    print("\n--- 测试泵1 ---")
    try:
        print("调用 start_pump(1, 'forward', 100)...")
        result = pm.start_pump(1, "forward", 100)
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  异常: {e}")
    
    time.sleep(0.5)
    
    try:
        print("调用 stop_pump(1)...")
        result = pm.stop_pump(1)
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  异常: {e}")
    
    # 测试泵2作为对比
    print("\n--- 测试泵2 (对比) ---")
    try:
        print("调用 start_pump(2, 'forward', 100)...")
        result = pm.start_pump(2, "forward", 100)
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  异常: {e}")
    
    time.sleep(0.5)
    
    try:
        print("调用 stop_pump(2)...")
        result = pm.stop_pump(2)
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  异常: {e}")
    
    pm.disconnect()
    LibContext.reset()
    print("\nPumpManager 已断开")
    return True


# ============================================================================
# 测试4: 检查 RS485Wrapper
# ============================================================================
def test_rs485_wrapper():
    """测试RS485Wrapper层"""
    print("\n" + "="*60)
    print("测试4: 使用 RS485Wrapper 测试")
    print("="*60)
    
    from echem_sdl.lib_context import LibContext
    LibContext.reset()
    
    from services.rs485_wrapper import RS485Wrapper
    
    wrapper = RS485Wrapper()
    wrapper.set_mock_mode(False)
    print(f"✅ RS485Wrapper 创建 (mock_mode=False)")
    
    success = wrapper.open_port("COM7", 38400)
    if not success:
        print("❌ RS485Wrapper 打开失败")
        return False
    print("✅ RS485Wrapper 连接成功")
    
    time.sleep(0.3)
    
    # 扫描
    print("\n--- 扫描设备 ---")
    pumps = wrapper.scan_pumps()
    print(f"  扫描结果: {pumps}")
    
    # 测试泵1
    print("\n--- 测试泵1 ---")
    result = wrapper.start_pump(1, "FWD", 100)
    print(f"  start_pump(1): {result}")
    time.sleep(0.5)
    result = wrapper.stop_pump(1)
    print(f"  stop_pump(1): {result}")
    
    # 测试泵2
    print("\n--- 测试泵2 ---")
    result = wrapper.start_pump(2, "FWD", 100)
    print(f"  start_pump(2): {result}")
    time.sleep(0.5)
    result = wrapper.stop_pump(2)
    print(f"  stop_pump(2): {result}")
    
    wrapper.close_port()
    LibContext.reset()
    print("\nRS485Wrapper 已关闭")
    return True


# ============================================================================
# 主函数
# ============================================================================
if __name__ == "__main__":
    print("="*60)
    print("泵1通信完整调试")
    print("="*60)
    print("\n⚠️ 请确保 MKS 软件已关闭，COM7 未被占用\n")
    
    input("按 Enter 开始测试...")
    
    # 测试1: 原始串口
    test_raw_serial()
    
    input("\n按 Enter 继续下一个测试...")
    
    # 测试2: RS485Driver
    test_rs485_driver()
    
    input("\n按 Enter 继续下一个测试...")
    
    # 测试3: PumpManager
    test_pump_manager()
    
    input("\n按 Enter 继续下一个测试...")
    
    # 测试4: RS485Wrapper
    test_rs485_wrapper()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
