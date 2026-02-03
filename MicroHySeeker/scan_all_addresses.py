#!/usr/bin/env python3
"""
扫描所有RS485地址(1-254)，寻找泵1的真实地址
"""
import serial
import time

def main():
    port = "COM7"
    baudrate = 38400
    
    print("=" * 60)
    print("RS485地址全扫描 - 寻找所有响应的设备")
    print("=" * 60)
    
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        stopbits=2,
        parity='N',
        timeout=0.2  # 短超时，快速扫描
    )
    print(f"✅ 串口打开成功: {port} @ {baudrate} bps")
    
    found_devices = []
    
    # 扫描地址1-20（通常泵地址不会超过这个范围）
    print("\n扫描地址 1-20...")
    for addr in range(1, 21):
        ser.reset_input_buffer()
        time.sleep(0.02)
        
        # 构建帧: FA [addr] F6 00 00 10 [checksum]
        frame = bytes([0xFA, addr, 0xF6, 0x00, 0x00, 0x10])
        checksum = sum(frame) & 0xFF
        frame = frame + bytes([checksum])
        
        ser.write(frame)
        time.sleep(0.15)
        
        rx = b''
        while ser.in_waiting:
            rx += ser.read(ser.in_waiting)
            time.sleep(0.01)
        
        if rx:
            # 检查是否是有效响应
            # 正确响应格式: FB [addr] F6 [data] [checksum]
            valid = False
            if len(rx) >= 4 and rx[0] == 0xFB and rx[1] == addr and rx[2] == 0xF6:
                valid = True
                found_devices.append((addr, rx, "✅ 正确响应"))
                print(f"地址 {addr:2d}: {rx.hex(' ').upper()} ✅ 正确响应")
            else:
                # 有响应但格式不对
                print(f"地址 {addr:2d}: {rx.hex(' ').upper()} ⚠️ 异常响应")
                found_devices.append((addr, rx, "⚠️ 异常响应"))
    
    print("\n" + "=" * 60)
    print("扫描结果汇总")
    print("=" * 60)
    
    print("\n正确响应的设备:")
    correct = [(addr, rx, status) for addr, rx, status in found_devices if "正确" in status]
    for addr, rx, status in correct:
        print(f"  地址 {addr}: {rx.hex(' ').upper()}")
    
    print("\n异常响应的设备:")
    abnormal = [(addr, rx, status) for addr, rx, status in found_devices if "异常" in status]
    for addr, rx, status in abnormal:
        print(f"  地址 {addr}: {rx.hex(' ').upper()}")
    
    if not correct:
        print("\n⚠️ 没有找到正确响应的设备!")
    
    # 检查地址1是否真的存在问题
    print("\n" + "=" * 60)
    print("详细分析地址1的响应")
    print("=" * 60)
    
    print("\n连续测试地址1共10次:")
    addr1_responses = []
    for i in range(10):
        ser.reset_input_buffer()
        time.sleep(0.02)
        
        frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10, 0x01])
        ser.write(frame)
        time.sleep(0.15)
        
        rx = b''
        while ser.in_waiting:
            rx += ser.read(ser.in_waiting)
            time.sleep(0.01)
        
        addr1_responses.append(rx)
        print(f"  [{i+1:2d}] RX: {rx.hex(' ').upper() if rx else '无'}")
    
    # 分析一致性
    unique_responses = set([r.hex() for r in addr1_responses if r])
    print(f"\n地址1响应一致性: {len(unique_responses)} 种不同响应 (共10次)")
    if len(unique_responses) > 1:
        print("⚠️ 响应不一致 - 表明存在硬件问题或信号干扰")
    
    ser.close()
    print("\n✅ 串口已关闭")

if __name__ == "__main__":
    main()
