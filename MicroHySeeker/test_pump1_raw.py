#!/usr/bin/env python3
"""
直接使用pyserial测试泵1，完全绕过所有包装层
这是最纯净的测试，与MKS软件使用相同的方法
"""
import serial
import time

def calc_checksum(data: bytes) -> int:
    """计算校验和"""
    return sum(data) & 0xFF

def build_frame(addr: int, cmd: int, data: bytes = b'') -> bytes:
    """构建帧"""
    frame = bytes([0xFA, addr, cmd]) + data
    frame += bytes([calc_checksum(frame)])
    return frame

def main():
    port = "COM7"
    baudrate = 38400
    
    print("=" * 60)
    print("泵1原始通信测试 - 直接使用pyserial")
    print("=" * 60)
    
    try:
        # 打开串口 - 与MKS软件相同的参数
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            stopbits=2,
            parity='N',
            timeout=1.0
        )
        print(f"✅ 串口打开成功: {port} @ {baudrate} bps")
        
        # 清空缓冲区
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
        
        # 测试1: 读取泵1状态 (CMD_SPEED=0xF6, speed=0)
        print("\n" + "-" * 40)
        print("测试1: 读取泵1状态 (设置速度为0)")
        # FA 01 F6 00 00 10 01 (与MKS软件相同)
        frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10])
        checksum = sum(frame) & 0xFF
        frame = frame + bytes([checksum])
        print(f"TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        rx = ser.read(100)
        print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
        
        # 测试2: 启用泵1 (CMD_ENABLE=0xF3, enable=1)
        print("\n" + "-" * 40)
        print("测试2: 启用泵1 (使能)")
        frame = bytes([0xFA, 0x01, 0xF3, 0x01])
        checksum = sum(frame) & 0xFF
        frame = frame + bytes([checksum])
        print(f"TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        rx = ser.read(100)
        print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
        
        # 测试3: 启动泵1 (CMD_SPEED=0xF6, FWD 100RPM)
        print("\n" + "-" * 40)
        print("测试3: 启动泵1 (正转 100RPM)")
        # FA 01 F6 80 64 10 E5 (与MKS软件相同)
        frame = bytes([0xFA, 0x01, 0xF6, 0x80, 0x64, 0x10])
        checksum = sum(frame) & 0xFF
        frame = frame + bytes([checksum])
        print(f"TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        rx = ser.read(100)
        print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
        
        print("\n⏳ 泵1应该正在转动，等待3秒...")
        time.sleep(3)
        
        # 测试4: 停止泵1 (CMD_SPEED=0xF6, speed=0)
        print("\n" + "-" * 40)
        print("测试4: 停止泵1")
        frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10])
        checksum = sum(frame) & 0xFF
        frame = frame + bytes([checksum])
        print(f"TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        rx = ser.read(100)
        print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
        
        # 测试5: 禁用泵1 (CMD_ENABLE=0xF3, enable=0)
        print("\n" + "-" * 40)
        print("测试5: 禁用泵1")
        frame = bytes([0xFA, 0x01, 0xF3, 0x00])
        checksum = sum(frame) & 0xFF
        frame = frame + bytes([checksum])
        print(f"TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        rx = ser.read(100)
        print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
        
        # 对比测试: 测试泵2
        print("\n" + "=" * 60)
        print("对比测试: 泵2")
        print("=" * 60)
        
        # 读取泵2状态
        print("\n" + "-" * 40)
        print("测试: 读取泵2状态")
        frame = bytes([0xFA, 0x02, 0xF6, 0x00, 0x00, 0x10])
        checksum = sum(frame) & 0xFF
        frame = frame + bytes([checksum])
        print(f"TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        rx = ser.read(100)
        print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
        
        ser.close()
        print("\n✅ 串口已关闭")
        
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main()
