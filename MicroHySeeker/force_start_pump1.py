#!/usr/bin/env python3
"""
强制启动泵1测试
即使通信返回乱码，也尝试发送启动命令
看看泵1是否实际上会响应并转动
"""
import serial
import time

def main():
    port = "COM7"
    baudrate = 38400
    
    print("=" * 70)
    print("强制启动泵1测试")
    print("=" * 70)
    print("""
测试原理:
RS485是单向广播，即使响应乱码，泵1可能仍然能接收并执行命令。
我们发送正确的命令，观察泵1是否物理上开始转动。
""")
    
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        stopbits=2,
        parity='N',
        timeout=0.5
    )
    
    print(f"✅ 串口打开成功: {port} @ {baudrate} bps\n")
    
    # 清空缓冲
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.3)
    
    # 步骤1: 使能泵1
    print("步骤1: 发送使能命令给泵1...")
    frame = bytes([0xFA, 0x01, 0xF3, 0x01, 0xEF])
    print(f"TX: {frame.hex(' ').upper()}")
    ser.write(frame)
    time.sleep(0.3)
    rx = ser.read(100)
    print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
    
    # 步骤2: 启动泵1正转100RPM
    print("\n步骤2: 发送启动命令 (正转100RPM)...")
    # FA 01 F6 80 64 10 E5 - 与MKS软件相同
    frame = bytes([0xFA, 0x01, 0xF6, 0x80, 0x64, 0x10, 0xE5])
    print(f"TX: {frame.hex(' ').upper()}")
    ser.write(frame)
    time.sleep(0.3)
    rx = ser.read(100)
    print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
    
    print("\n" + "=" * 70)
    print("⏳ 请观察泵1是否正在转动...")
    print("   如果泵1转动了，说明它能接收命令但响应有问题")
    print("   如果没有转动，说明通信双向都有问题")
    print("=" * 70)
    print("\n等待5秒...")
    time.sleep(5)
    
    # 步骤3: 停止泵1
    print("\n步骤3: 发送停止命令...")
    # 先设速度为0
    frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10, 0x01])
    print(f"TX: {frame.hex(' ').upper()}")
    ser.write(frame)
    time.sleep(0.3)
    rx = ser.read(100)
    print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
    
    # 禁用
    frame = bytes([0xFA, 0x01, 0xF3, 0x00, 0xEE])
    print(f"TX: {frame.hex(' ').upper()}")
    ser.write(frame)
    time.sleep(0.3)
    rx = ser.read(100)
    print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
    
    print("\n" + "=" * 70)
    print("对比: 测试泵2")
    print("=" * 70)
    
    # 使能泵2
    frame = bytes([0xFA, 0x02, 0xF3, 0x01, 0xF0])
    print(f"\n使能TX: {frame.hex(' ').upper()}")
    ser.write(frame)
    time.sleep(0.3)
    rx = ser.read(100)
    print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
    
    # 启动泵2
    frame = bytes([0xFA, 0x02, 0xF6, 0x80, 0x64, 0x10, 0xE6])
    print(f"启动TX: {frame.hex(' ').upper()}")
    ser.write(frame)
    time.sleep(0.3)
    rx = ser.read(100)
    print(f"RX: {rx.hex(' ').upper() if rx else '无响应'}")
    
    print("\n等待3秒...")
    time.sleep(3)
    
    # 停止泵2
    frame = bytes([0xFA, 0x02, 0xF6, 0x00, 0x00, 0x10, 0x02])
    ser.write(frame)
    time.sleep(0.2)
    frame = bytes([0xFA, 0x02, 0xF3, 0x00, 0xEF])
    ser.write(frame)
    time.sleep(0.2)
    print("泵2已停止")
    
    ser.close()
    
    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    print("""
如果泵1确实转动了:
  - 说明泵1的TX(发送)功能正常，能接收命令
  - 但泵1的RX(响应)功能有问题，返回乱码
  - 解决方案: 修改软件以不依赖泵1的响应确认
  
如果泵1没有转动:
  - 说明泵1的通信完全失败
  - 需要检查硬件连接或更换泵1
""")

if __name__ == "__main__":
    main()
