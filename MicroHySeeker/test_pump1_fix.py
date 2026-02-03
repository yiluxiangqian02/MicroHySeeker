#!/usr/bin/env python
"""
测试泵1配液功能修复
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def test_pump1_dilution():
    """测试泵1配液功能"""
    print("=" * 60)
    print("🔧 测试泵1配液功能修复")
    print("=" * 60)
    
    # 1. 获取RS485实例
    print("\n[1] 连接硬件...")
    from src.services.rs485_wrapper import get_rs485_instance
    
    rs485 = get_rs485_instance(force_reload=True)
    
    if not rs485.is_connected():
        print("❌ 硬件未连接")
        return False
    
    print("✅ 硬件连接成功")
    
    # 2. 扫描泵
    print("\n[2] 扫描泵...")
    pumps = rs485.scan_pumps()
    print(f"   在线泵: {pumps}")
    
    if 1 not in pumps:
        print("❌ 泵1不在线")
        return False
    
    # 3. 测试手动控制泵1
    print("\n[3] 测试手动控制泵1...")
    success = rs485.start_pump(1, "FWD", 100)
    if success:
        print("✅ 手动启动泵1成功")
        import time
        time.sleep(1)
        rs485.stop_pump(1)
        print("✅ 手动停止泵1成功")
    else:
        print("❌ 手动控制泵1失败")
        return False
    
    # 4. 配置配液通道（泵1）
    print("\n[4] 配置配液通道（泵1）...")
    from src.models import DilutionChannel
    
    pump1_channel = DilutionChannel(
        channel_id="pump1_test",
        solution_name="泵1测试溶液",
        stock_concentration=1.0,
        pump_address=1,
        direction="FWD",
        default_rpm=120
    )
    
    success = rs485.configure_dilution_channels([pump1_channel])
    if not success:
        print("❌ 配置配液通道失败")
        return False
    
    print("✅ 配液通道配置成功")
    
    # 5. 测试配液功能
    print("\n[5] 测试配液功能...")
    
    # 准备配液
    volume = rs485.prepare_dilution(1, 0.5, 1000)
    print(f"   计算得出注入体积: {volume:.2f} μL")
    
    if volume <= 0:
        print("❌ 体积计算错误")
        return False
    
    # 开始配液
    print("   开始配液...")
    success = rs485.start_dilution(1, volume)
    
    if success:
        print("✅ 配液启动成功")
        
        # 监控进度
        import time
        max_wait = 10  # 最多等10秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            progress = rs485.get_dilution_progress(1)
            state = progress.get('state', 'unknown')
            percent = progress.get('progress', 0)
            
            print(f"   状态: {state}, 进度: {percent:.1f}%", end='\r')
            
            if state == 'completed':
                print(f"\n✅ 配液完成! 进度={percent:.1f}%")
                return True
            elif state == 'error':
                print(f"\n❌ 配液出错")
                return False
            
            time.sleep(0.5)
        
        print(f"\n⚠️ 配液超时")
        return False
    else:
        print("❌ 配液启动失败")
        return False


def main():
    """主测试流程"""
    try:
        success = test_pump1_dilution()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ 泵1配液功能修复成功!")
            print("   现在可以正常使用配制溶液功能")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ 泵1配液功能仍有问题")
            print("   请检查硬件连接或联系技术支持")
            print("=" * 60)
        
        return success
        
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)