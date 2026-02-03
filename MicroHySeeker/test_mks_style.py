#!/usr/bin/env python3
"""
精确模拟MKS软件的通信方式测试泵1
根据用户提供的MKS日志:
TX: FA 1 F6 80 64 10 E5  -> 启动泵1正转100RPM
RX: FF C9 D1 FF          -> 响应
TX: FA 1 F6 0 0 10 1     -> 停止泵1
RX: FB 1 F6 CD 5F F3     -> 响应
RX: FB 1 F6 2 F4         -> 响应
"""
import serial
import time
import sys

def main():
    port = "COM7"
    
    print("=" * 70)
    print("精确模拟MKS软件通信方式")
    print("=" * 70)
    print("""
MKS软件日志显示:
TX: FA 1 F6 80 64 10 E5 -> RX: FF C9 D1 FF
TX: FA 1 F6 0 0 10 1    -> RX: FB 1 F6 CD 5F F3, FB 1 F6 2 F4

注意: MKS软件的RX也有 "FF C9 D1 FF" 这种异常响应!
但它能继续工作，可能是有重试机制或忽略异常响应。
""")
    
    # 尝试MKS软件可能使用的不同配置
    configs = [
        {"baudrate": 38400, "stopbits": 2, "timeout": 0.5},
        {"baudrate": 38400, "stopbits": 1, "timeout": 0.5},
        {"baudrate": 9600, "stopbits": 2, "timeout": 1.0},
        {"baudrate": 19200, "stopbits": 2, "timeout": 0.5},
        {"baudrate": 115200, "stopbits": 2, "timeout": 0.5},
    ]
    
    for cfg in configs:
        print(f"\n{'='*70}")
        print(f"测试配置: {cfg['baudrate']}bps, {cfg['stopbits']}停止位, {cfg['timeout']}s超时")
        print("=" * 70)
        
        try:
            ser = serial.Serial(
                port=port,
                baudrate=cfg['baudrate'],
                bytesize=8,
                stopbits=cfg['stopbits'],
                parity='N',
                timeout=cfg['timeout']
            )
            
            # 清空缓冲
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            time.sleep(0.2)
            
            # 测试泵1
            success_count = 0
            for i in range(5):
                ser.reset_input_buffer()
                time.sleep(0.03)
                
                frame = bytes([0xFA, 0x01, 0xF6, 0x00, 0x00, 0x10, 0x01])
                ser.write(frame)
                time.sleep(0.2)
                
                rx = b''
                while ser.in_waiting:
                    rx += ser.read(ser.in_waiting)
                    time.sleep(0.01)
                
                if rx and len(rx) >= 4 and rx[0] == 0xFB and rx[1] == 0x01:
                    success_count += 1
                    print(f"  [{i+1}] ✅ {rx.hex(' ')}")
                else:
                    print(f"  [{i+1}] ❌ {rx.hex(' ') if rx else '无响应'}")
            
            print(f"  结果: {success_count}/5 正确响应")
            
            # 如果这个配置成功率>0，测试泵2验证
            if success_count > 0:
                print(f"\n  验证: 测试泵2")
                ser.reset_input_buffer()
                time.sleep(0.03)
                frame = bytes([0xFA, 0x02, 0xF6, 0x00, 0x00, 0x10, 0x02])
                ser.write(frame)
                time.sleep(0.2)
                rx = b''
                while ser.in_waiting:
                    rx += ser.read(ser.in_waiting)
                    time.sleep(0.01)
                print(f"  泵2响应: {rx.hex(' ') if rx else '无响应'}")
            
            ser.close()
            
        except Exception as e:
            print(f"  错误: {e}")
    
    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    print("""
根据测试结果和MKS软件日志分析:

1. MKS软件日志中泵1的响应也有异常 (FF C9 D1 FF)
   这表明泵1的硬件确实存在通信问题！

2. 但MKS软件可能有以下机制:
   - 自动重试多次
   - 忽略异常响应继续发送
   - 累积响应帧直到收到有效数据
   
3. 我们的代码对响应格式检查更严格，导致泵1被判定为通信失败

建议: 增加重试机制和宽松的响应解析
""")

if __name__ == "__main__":
    main()
