#!/usr/bin/env python3
"""
调试帧解析器 - 检查泵1的响应是否被正确解析
"""
import sys
sys.path.insert(0, 'src')

import serial
import time
from echem_sdl.hardware.rs485_protocol import FrameStreamParser

def main():
    port = "COM7"
    baudrate = 38400
    
    print("=" * 70)
    print("调试帧解析器")
    print("=" * 70)
    
    # 创建宽松模式的解析器
    parser = FrameStreamParser(strict_checksum=False)
    
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        stopbits=2,
        parity='N',
        timeout=0.5
    )
    
    print(f"✅ 串口打开成功: {port} @ {baudrate} bps")
    print(f"解析器宽松模式: strict_checksum={parser._strict_checksum}")
    
    # 清空缓冲
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.3)
    
    print("\n" + "=" * 70)
    print("测试泵1")
    print("=" * 70)
    
    for i in range(10):
        ser.reset_input_buffer()
        parser.clear()
        time.sleep(0.05)
        
        # 发送命令
        frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10, 0x01])
        print(f"\n[{i+1}] TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        
        # 读取响应
        rx = b''
        while ser.in_waiting:
            rx += ser.read(ser.in_waiting)
            time.sleep(0.01)
        
        print(f"[{i+1}] RX: {rx.hex(' ').upper() if rx else '无'} (长度: {len(rx)})")
        
        # 使用解析器解析
        if rx:
            frames = parser.push(rx)
            print(f"[{i+1}] 解析结果: {len(frames)} 个帧")
            for f in frames:
                print(f"    -> addr={f.addr}, cmd=0x{f.cmd:02X}, payload={f.payload.hex()}")
                
                # 检查是否是泵1的响应
                if f.addr == 1 and f.cmd == 0xF6:
                    print(f"    ✅ 找到泵1的有效响应!")
        
        time.sleep(0.1)
    
    print("\n" + "=" * 70)
    print("对比泵2")
    print("=" * 70)
    
    for i in range(3):
        ser.reset_input_buffer()
        parser.clear()
        time.sleep(0.05)
        
        frame = bytes([0xFA, 0x02, 0xF6, 0x00, 0x00, 0x10, 0x02])
        print(f"\n[{i+1}] TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        
        rx = b''
        while ser.in_waiting:
            rx += ser.read(ser.in_waiting)
            time.sleep(0.01)
        
        print(f"[{i+1}] RX: {rx.hex(' ').upper() if rx else '无'}")
        
        if rx:
            frames = parser.push(rx)
            print(f"[{i+1}] 解析结果: {len(frames)} 个帧")
            for f in frames:
                print(f"    -> addr={f.addr}, cmd=0x{f.cmd:02X}, payload={f.payload.hex()}")
    
    ser.close()
    print("\n✅ 完成")

if __name__ == "__main__":
    main()
