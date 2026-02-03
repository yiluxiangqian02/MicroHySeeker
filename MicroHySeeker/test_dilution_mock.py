#!/usr/bin/env python
"""
Mock模式下配液功能测试脚本
用于验证配液流程的完整性
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def test_dilution_flow():
    """测试配液流程"""
    print("=" * 50)
    print("Mock模式配液功能测试")
    print("=" * 50)
    
    # 1. 获取RS485实例并验证连接
    print("\n[1] 获取RS485实例...")
    from src.services.rs485_wrapper import get_rs485_instance
    rs485 = get_rs485_instance()
    
    if not rs485.is_connected():
        print("❌ RS485未连接")
        return False
    print("✅ RS485已连接 (Mock模式)")
    
    # 2. 创建测试配液通道
    print("\n[2] 配置配液通道...")
    from src.models import DilutionChannel
    
    channels = [
        DilutionChannel(
            channel_id="1",
            solution_name="H2SO4 (酸)",
            stock_concentration=1.0,
            pump_address=1,
            direction="FWD",
            default_rpm=120,
            color="#FF4444"
        ),
        DilutionChannel(
            channel_id="2",
            solution_name="去离子水 (溶剂)",
            stock_concentration=0.0,  # 溶剂
            pump_address=2,
            direction="FWD",
            default_rpm=150,
            color="#44FF44"
        ),
    ]
    
    success = rs485.configure_dilution_channels(channels)
    if not success:
        print("❌ 配置通道失败")
        return False
    print(f"✅ 配置了 {len(channels)} 个通道")
    
    # 3. 准备配液（计算体积）
    print("\n[3] 准备配液（计算注入体积）...")
    # 目标：0.1 mol/L H2SO4，总体积 1000 μL
    target_conc = 0.1  # mol/L
    total_volume_ul = 1000.0  # μL
    
    acid_volume = rs485.prepare_dilution(1, target_conc, total_volume_ul)
    print(f"   H2SO4 需要: {acid_volume:.2f} μL")
    
    # 4. 开始配液
    print("\n[4] 开始配液...")
    
    import time
    completion_flag = [False]  # 使用列表来在闭包中修改
    
    def on_complete():
        completion_flag[0] = True
        print("   ✅ 配液完成回调触发!")
    
    success = rs485.start_dilution(1, acid_volume, callback=on_complete)
    if not success:
        print("❌ 启动配液失败")
        return False
    print(f"✅ 配液已启动: {acid_volume:.2f} μL")
    
    # 5. 等待完成并监控进度
    print("\n[5] 监控配液进度...")
    start_time = time.time()
    max_wait = 10.0  # 最多等10秒
    
    while time.time() - start_time < max_wait:
        progress = rs485.get_dilution_progress(1)
        state = progress.get('state', 'unknown')
        percent = progress.get('progress', 0)
        
        print(f"   状态: {state}, 进度: {percent:.1f}%", end='\r')
        
        if state == 'completed' or completion_flag[0]:
            print(f"\n✅ 配液完成! 状态={state}, 进度={percent:.1f}%")
            break
        elif state == 'error':
            print(f"\n❌ 配液出错")
            return False
        
        time.sleep(0.5)
    else:
        print("\n❌ 配液超时")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Mock配液测试通过!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    try:
        success = test_dilution_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        import traceback
        print(f"\n❌ 测试异常: {e}")
        traceback.print_exc()
        sys.exit(1)
