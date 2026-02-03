"""
RS485 模块使用示例

演示如何使用 RS485 协议层和驱动层进行泵控制。
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import time
from echem_sdl.hardware.rs485_driver import RS485Driver
from echem_sdl.hardware.rs485_protocol import (
    build_speed_frame, build_enable_frame,
    frame_to_hex, decode_speed
)


def example_1_basic_mock():
    """示例1: 基本Mock模式使用"""
    print("=== 示例1: 基本Mock模式 ===\n")
    
    # 创建Mock驱动
    driver = RS485Driver(port='COM3', baudrate=38400, mock_mode=True)
    
    # 打开串口
    driver.open()
    print("串口已打开\n")
    
    # 发送使能命令
    driver.enable_motor(addr=1, enable=True)
    print("已发送使能命令\n")
    
    # 发送速度命令
    driver.run_speed(addr=1, rpm=100, forward=True)
    print("已发送速度命令\n")
    
    # 关闭
    driver.close()
    print("串口已关闭\n")


def example_2_with_callback():
    """示例2: 使用回调接收响应"""
    print("=== 示例2: 使用回调 ===\n")
    
    # 回调函数
    def on_response(addr: int, cmd: int, payload: bytes):
        print(f"收到响应: 地址={addr}, 命令=0x{cmd:02X}, 数据={payload.hex()}")
    
    # 创建驱动并设置回调
    driver = RS485Driver(port='COM3', mock_mode=True)
    driver.set_callback(on_response)
    driver.open()
    
    # 发送命令
    print("发送使能命令...")
    driver.enable_motor(addr=1, enable=True)
    time.sleep(0.2)  # 等待响应
    
    print("\n发送速度命令...")
    driver.run_speed(addr=1, rpm=200, forward=True)
    time.sleep(0.2)
    
    driver.close()
    print()


def example_3_device_discovery():
    """示例3: 设备扫描"""
    print("=== 示例3: 设备扫描 ===\n")
    
    driver = RS485Driver(port='COM3', mock_mode=True)
    driver.open()
    
    print("正在扫描地址 1-5...")
    devices = driver.discover_devices(addresses=[1, 2, 3, 4, 5], timeout_per_addr=0.1)
    print(f"发现设备: {devices}\n")
    
    driver.close()


def example_4_context_manager():
    """示例4: 使用上下文管理器"""
    print("=== 示例4: 上下文管理器 ===\n")
    
    with RS485Driver(port='COM3', mock_mode=True) as driver:
        print("串口自动打开")
        driver.run_speed(addr=1, rpm=150, forward=True)
        print("已发送速度命令")
    print("串口自动关闭\n")


def example_5_protocol_only():
    """示例5: 仅使用协议层"""
    print("=== 示例5: 协议层独立使用 ===\n")
    
    # 构建使能帧
    enable_frame = build_enable_frame(addr=1, enable=True)
    print(f"使能帧: {frame_to_hex(enable_frame)}")
    
    # 构建速度帧
    speed_frame = build_speed_frame(addr=1, rpm=100, forward=True)
    print(f"速度帧: {frame_to_hex(speed_frame)}")
    
    # 解析速度数据
    from echem_sdl.hardware.rs485_protocol import encode_speed, decode_speed
    speed_data = encode_speed(250, forward=False)
    print(f"速度编码 (250 RPM 反转): {speed_data.hex()}")
    
    rpm, forward = decode_speed(speed_data)
    print(f"速度解码: {rpm} RPM, {'正转' if forward else '反转'}\n")


def example_6_multi_pump():
    """示例6: 控制多个泵"""
    print("=== 示例6: 多泵控制 ===\n")
    
    received_count = [0]  # 使用列表以便在闭包中修改
    
    def on_response(addr: int, cmd: int, payload: bytes):
        received_count[0] += 1
        print(f"  泵 #{addr} 响应")
    
    driver = RS485Driver(port='COM3', mock_mode=True)
    driver.set_callback(on_response)
    driver.open()
    
    # 启动3个泵
    print("启动3个泵...")
    for addr in [1, 2, 3]:
        driver.enable_motor(addr=addr, enable=True)
        driver.run_speed(addr=addr, rpm=100, forward=True)
        time.sleep(0.1)
    
    time.sleep(0.5)  # 等待所有响应
    print(f"\n总共收到 {received_count[0]} 个响应\n")
    
    driver.close()


def main():
    """运行所有示例"""
    print("RS485 模块使用示例\n")
    print("=" * 60)
    print()
    
    try:
        example_1_basic_mock()
        example_2_with_callback()
        example_3_device_discovery()
        example_4_context_manager()
        example_5_protocol_only()
        example_6_multi_pump()
        
        print("=" * 60)
        print("所有示例运行完成！")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
