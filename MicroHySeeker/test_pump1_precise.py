#!/usr/bin/env python3
"""
泵1精确通信测试 - 分析响应数据
"""
import serial
import time

def main():
    port = "COM7"
    baudrate = 38400
    
    print("=" * 60)
    print("泵1精确通信测试")
    print("=" * 60)
    
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        stopbits=2,
        parity='N',
        timeout=0.5
    )
    print(f"✅ 串口打开成功: {port} @ {baudrate} bps")
    
    # 彻底清空缓冲区
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print("清空缓冲区...")
    time.sleep(0.5)
    
    # 再次清空
    while ser.in_waiting:
        garbage = ser.read(ser.in_waiting)
        print(f"清理残留数据: {garbage.hex(' ')}")
        time.sleep(0.1)
    
    print("\n" + "=" * 60)
    print("测试: 连续发送多次读取命令到泵1")
    print("=" * 60)
    
    for i in range(5):
        # 清空输入缓冲
        ser.reset_input_buffer()
        time.sleep(0.05)
        
        frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10, 0x01])
        print(f"\n[{i+1}] TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        
        # 等待响应
        time.sleep(0.3)
        
        # 读取所有可用数据
        rx = b''
        while ser.in_waiting:
            rx += ser.read(ser.in_waiting)
            time.sleep(0.01)
        
        if rx:
            print(f"[{i+1}] RX: {rx.hex(' ').upper()} (长度: {len(rx)})")
            # 分析响应
            if len(rx) >= 5 and rx[0] == 0xFB:
                addr = rx[1]
                cmd = rx[2]
                print(f"    -> 解析: 地址=0x{addr:02X}, 命令=0x{cmd:02X}")
                if addr == 0x01 and cmd == 0xF6:
                    print(f"    ✅ 响应格式正确!")
                else:
                    print(f"    ⚠️ 响应格式异常")
        else:
            print(f"[{i+1}] RX: 无响应")
        
        time.sleep(0.2)
    
    print("\n" + "=" * 60)
    print("对比: 连续发送多次读取命令到泵2")
    print("=" * 60)
    
    for i in range(3):
        ser.reset_input_buffer()
        time.sleep(0.05)
        
        frame = bytes([0xFA, 0x02, 0xF6, 0x00, 0x00, 0x10, 0x02])
        print(f"\n[{i+1}] TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        
        time.sleep(0.3)
        
        rx = b''
        while ser.in_waiting:
            rx += ser.read(ser.in_waiting)
            time.sleep(0.01)
        
        if rx:
            print(f"[{i+1}] RX: {rx.hex(' ').upper()} (长度: {len(rx)})")
            if len(rx) >= 5 and rx[0] == 0xFB:
                addr = rx[1]
                cmd = rx[2]
                print(f"    -> 解析: 地址=0x{addr:02X}, 命令=0x{cmd:02X}")
        else:
            print(f"[{i+1}] RX: 无响应")
        
        time.sleep(0.2)
    
    ser.close()
    print("\n✅ 串口已关闭")

if __name__ == "__main__":
    main()
