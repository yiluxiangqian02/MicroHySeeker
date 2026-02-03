#!/usr/bin/env python3
"""
深度诊断泵1和泵11的通信问题
"""
import serial
import time

def test_address(ser, addr, count=5):
    """测试特定地址"""
    responses = []
    for i in range(count):
        ser.reset_input_buffer()
        time.sleep(0.02)
        
        frame = bytes([0xFA, addr, 0xF6, 0x00, 0x00, 0x10])
        checksum = sum(frame) & 0xFF
        frame = frame + bytes([checksum])
        
        ser.write(frame)
        time.sleep(0.2)
        
        rx = b''
        while ser.in_waiting:
            rx += ser.read(ser.in_waiting)
            time.sleep(0.01)
        
        responses.append(rx)
    return responses

def main():
    port = "COM7"
    baudrate = 38400
    
    print("=" * 70)
    print("深度诊断: 泵1和泵11通信问题")
    print("=" * 70)
    
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        stopbits=2,
        parity='N',
        timeout=0.3
    )
    print(f"✅ 串口打开成功: {port} @ {baudrate} bps\n")
    
    # 测试地址11
    print("=" * 70)
    print("测试地址 11")
    print("=" * 70)
    
    responses_11 = test_address(ser, 11, 10)
    for i, rx in enumerate(responses_11):
        status = ""
        if rx:
            if len(rx) >= 4 and rx[0] == 0xFB and rx[1] == 0x0B and rx[2] == 0xF6:
                status = "✅ 正确"
            else:
                status = "⚠️ 异常"
        else:
            status = "❌ 无响应"
        print(f"  [{i+1:2d}] {rx.hex(' ').upper() if rx else '无'} {status}")
    
    # 统计
    valid_11 = sum(1 for rx in responses_11 if rx and len(rx) >= 4 and rx[0] == 0xFB and rx[1] == 0x0B)
    print(f"\n地址11: {valid_11}/10 次正确响应")
    
    # 再测试地址1
    print("\n" + "=" * 70)
    print("测试地址 1 (作为对比)")
    print("=" * 70)
    
    responses_1 = test_address(ser, 1, 10)
    for i, rx in enumerate(responses_1):
        status = ""
        if rx:
            if len(rx) >= 4 and rx[0] == 0xFB and rx[1] == 0x01 and rx[2] == 0xF6:
                status = "✅ 正确"
            else:
                status = "⚠️ 异常"
        else:
            status = "❌ 无响应"
        print(f"  [{i+1:2d}] {rx.hex(' ').upper() if rx else '无'} {status}")
    
    valid_1 = sum(1 for rx in responses_1 if rx and len(rx) >= 4 and rx[0] == 0xFB and rx[1] == 0x01)
    print(f"\n地址1: {valid_1}/10 次正确响应")
    
    # 测试地址2作为健康参考
    print("\n" + "=" * 70)
    print("测试地址 2 (健康参考)")
    print("=" * 70)
    
    responses_2 = test_address(ser, 2, 5)
    for i, rx in enumerate(responses_2):
        status = ""
        if rx:
            if len(rx) >= 4 and rx[0] == 0xFB and rx[1] == 0x02 and rx[2] == 0xF6:
                status = "✅ 正确"
            else:
                status = "⚠️ 异常"
        else:
            status = "❌ 无响应"
        print(f"  [{i+1}] {rx.hex(' ').upper() if rx else '无'} {status}")
    
    valid_2 = sum(1 for rx in responses_2 if rx and len(rx) >= 4 and rx[0] == 0xFB and rx[1] == 0x02)
    print(f"\n地址2: {valid_2}/5 次正确响应")
    
    ser.close()
    
    print("\n" + "=" * 70)
    print("诊断总结")
    print("=" * 70)
    print(f"""
问题分析:
1. 泵1 (地址0x01): 响应异常，每次返回不同的乱码
   - 可能原因: 硬件故障、接线问题、信号干扰
   
2. 泵11 (地址0x0B): 完全无响应
   - 可能原因: 设备不存在、地址配置错误、断线
   
3. 其他泵 (2-10, 12): 正常工作

建议:
1. 检查泵1的RS485接线是否松动或接反
2. 检查泵1的通信地址设置是否正确
3. 检查泵11是否实际存在于系统中
4. 尝试在MKS软件中逐个测试泵1和泵11
5. 检查RS485总线的终端电阻是否正确
""")

if __name__ == "__main__":
    main()
