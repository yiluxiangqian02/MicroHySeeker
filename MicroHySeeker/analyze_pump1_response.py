#!/usr/bin/env python3
"""
深入分析泵1的响应数据
不做校验和验证，看看它到底返回什么
"""
import serial
import time

def checksum(data: bytes) -> int:
    return sum(data) & 0xFF

def main():
    port = "COM7"
    baudrate = 38400
    
    print("=" * 70)
    print("深入分析泵1响应数据")
    print("=" * 70)
    
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        stopbits=2,
        parity='N',
        timeout=0.5
    )
    
    print(f"✅ 串口打开成功: {port} @ {baudrate} bps")
    
    # 清空缓冲
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.3)
    
    print("\n" + "=" * 70)
    print("测试: 发送速度命令给泵1 (停止命令)")
    print("=" * 70)
    
    for i in range(10):
        ser.reset_input_buffer()
        time.sleep(0.05)
        
        # 发送: FA 01 F6 00 00 10 01
        frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10, 0x01])
        
        print(f"\n[{i+1}] TX: {frame.hex(' ').upper()}")
        ser.write(frame)
        time.sleep(0.3)
        
        # 读取响应
        rx = b''
        while ser.in_waiting:
            rx += ser.read(ser.in_waiting)
            time.sleep(0.01)
        
        if rx:
            print(f"[{i+1}] RX: {rx.hex(' ').upper()} (长度: {len(rx)})")
            
            # 分析响应
            if len(rx) >= 4:
                header = rx[0]
                addr = rx[1]
                cmd = rx[2]
                
                # 校验和验证
                expected_chk = checksum(rx[:-1]) if len(rx) > 1 else 0
                actual_chk = rx[-1]
                chk_ok = expected_chk == actual_chk
                
                print(f"    Header: 0x{header:02X} {'✅' if header == 0xFB else '❌'}")
                print(f"    Addr:   0x{addr:02X} {'✅' if addr == 0x01 else '❌'}")
                print(f"    Cmd:    0x{cmd:02X} {'✅' if cmd == 0xF6 else '❌'}")
                print(f"    Checksum: 期望 0x{expected_chk:02X}, 实际 0x{actual_chk:02X} {'✅' if chk_ok else '❌'}")
                
                # 完整有效性判断
                if header == 0xFB and addr == 0x01 and cmd == 0xF6:
                    if chk_ok:
                        print(f"    ✅ 完全有效的响应!")
                    else:
                        print(f"    ⚠️ 地址和命令正确，但校验和错误")
                else:
                    print(f"    ❌ 响应格式异常")
        else:
            print(f"[{i+1}] 无响应")
        
        time.sleep(0.1)
    
    # 对比泵2
    print("\n" + "=" * 70)
    print("对比: 泵2响应分析")
    print("=" * 70)
    
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
            print(f"[{i+1}] RX: {rx.hex(' ').upper()}")
            
            if len(rx) >= 4:
                expected_chk = checksum(rx[:-1])
                actual_chk = rx[-1]
                print(f"    Checksum: 期望 0x{expected_chk:02X}, 实际 0x{actual_chk:02X} {'✅' if expected_chk == actual_chk else '❌'}")
    
    ser.close()
    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    print("""
如果泵1的响应中地址(addr)是0x01但校验和错误，
这表明泵1的硬件可能有以下问题:
1. RS485芯片损坏导致数据传输错误
2. 接线松动导致信号衰减/干扰
3. 电源不稳定影响通信

建议:
- 检查泵1的RS485接线(A/B是否接反)
- 检查泵1的电源连接
- 尝试单独测试泵1(断开其他泵的连接)
- 使用示波器检查RS485信号质量
""")

if __name__ == "__main__":
    main()
