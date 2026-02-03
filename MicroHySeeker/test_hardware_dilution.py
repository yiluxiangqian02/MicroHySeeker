"""
硬件测试快速启动脚本

此脚本帮助快速测试真实硬件的配液功能。
使用前确保：
1. RS485转USB线已连接
2. 至少有一个泵连接到总线
3. 知道正确的COM口号
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.rs485_wrapper import get_rs485_instance
from models import DilutionChannel


def main():
    print("=" * 70)
    print("MicroHySeeker 硬件配液测试")
    print("=" * 70)
    
    rs485 = get_rs485_instance()
    rs485.set_mock_mode(False)  # 硬件模式
    
    # 1. 列出可用端口
    print("\n▶ 可用COM口:")
    ports = rs485.list_available_ports()
    for i, port in enumerate(ports, 1):
        print(f"   {i}. {port}")
    
    if not ports:
        print("   ✗ 未发现可用COM口")
        return
    
    # 2. 选择端口
    port_input = input(f"\n选择端口 (1-{len(ports)}) 或直接输入端口名: ").strip()
    if port_input.isdigit() and 1 <= int(port_input) <= len(ports):
        port = ports[int(port_input) - 1]
    else:
        port = port_input
    
    print(f"\n▶ 连接到 {port}...")
    if not rs485.open_port(port, 38400):
        print("   ✗ 连接失败")
        return
    print("   ✓ 连接成功")
    
    # 3. 扫描泵
    print("\n▶ 扫描泵设备...")
    online_pumps = rs485.scan_pumps()
    
    if not online_pumps:
        print("   ✗ 未发现任何泵")
        rs485.close_port()
        return
    
    print(f"   ✓ 发现 {len(online_pumps)} 个泵: {online_pumps}")
    
    # 4. 选择泵
    pump_addr = online_pumps[0]
    if len(online_pumps) > 1:
        pump_input = input(f"\n选择要测试的泵地址 {online_pumps}: ").strip()
        if pump_input.isdigit() and int(pump_input) in online_pumps:
            pump_addr = int(pump_input)
    
    print(f"\n▶ 使用泵 {pump_addr} 进行测试")
    
    # 5. 配置通道
    print("\n▶ 配置配液通道...")
    solution_name = input("   溶液名称 (默认: Test): ").strip() or "Test"
    stock_conc = input("   储备浓度 mol/L (默认: 1.0): ").strip() or "1.0"
    stock_conc = float(stock_conc)
    
    channel = DilutionChannel(
        channel_id=str(pump_addr),
        solution_name=solution_name,
        stock_concentration=stock_conc,
        pump_address=pump_addr,
        direction="FWD",
        default_rpm=120,
        color="#FF0000"
    )
    
    if not rs485.configure_dilution_channels([channel]):
        print("   ✗ 配置失败")
        rs485.close_port()
        return
    print("   ✓ 通道配置完成")
    
    # 6. 测试配液
    print("\n▶ 配液测试")
    volume_input = input("   注液体积 μL (建议10-50，默认20): ").strip() or "20"
    volume = float(volume_input)
    
    print(f"\n   开始注液 {volume}μL...")
    print("   ⚠️  请观察泵是否开始转动")
    
    if not rs485.start_dilution(pump_addr, volume):
        print("   ✗ 启动失败")
        rs485.close_port()
        return
    
    # 监控进度
    import time
    from echem_sdl.hardware.diluter import Diluter
    
    duration = Diluter.calculate_duration(volume, 120)
    print(f"   预计时长: {duration:.2f}秒")
    print()
    
    max_wait = duration + 10.0
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        progress = rs485.get_dilution_progress(pump_addr)
        state = progress['state']
        percent = progress['progress']
        infused = progress.get('infused_volume_ul', 0)
        
        print(f"   进度: {percent:5.1f}% ({infused:.1f}/{volume:.1f}μL) - {state}      ", end='\r')
        
        if state == 'completed':
            print()
            print("   ✓ 配液完成！")
            break
        elif state == 'error':
            print()
            print(f"   ✗ 配液出错: {progress.get('error', '未知错误')}")
            break
        
        time.sleep(0.5)
    else:
        print()
        print("   ⚠️  配液超时")
    
    # 7. 完成
    print("\n▶ 关闭连接")
    rs485.close_port()
    print("   ✓ 测试完成")
    
    # 询问重复
    print("\n" + "=" * 70)
    again = input("再次测试？(y/n): ").strip().lower()
    if again == 'y':
        print()
        main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
