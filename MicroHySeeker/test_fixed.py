#!/usr/bin/env python
"""
验证硬件问题修复
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def test_fixed_configuration():
    """测试修复后的配置"""
    print("🔧 测试修复后的配置...")
    
    # 1. 检查配置文件
    try:
        import json
        with open("config/system.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"   Mock模式: {config.get('mock_mode')}")
        print(f"   串口: {config.get('rs485_port')}")
        
        if not config.get('mock_mode'):
            print("   ❌ 配置仍为硬件模式")
            return False
        
    except Exception as e:
        print(f"   ❌ 配置检查失败: {e}")
        return False
    
    # 2. 测试RS485连接
    try:
        from src.services.rs485_wrapper import get_rs485_instance
        
        print("   🔗 获取RS485实例...")
        rs485 = get_rs485_instance(force_reload=True)  # 强制重载
        
        if not rs485.is_connected():
            print("   ❌ RS485连接失败")
            return False
        
        print("   ✅ RS485连接成功 (Mock模式)")
        
    except Exception as e:
        print(f"   ❌ RS485测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 快速配液测试
    try:
        from src.models import DilutionChannel
        
        test_channel = DilutionChannel(
            channel_id="test",
            solution_name="测试溶液",
            stock_concentration=1.0,
            pump_address=1,
            default_rpm=120
        )
        
        print("   🧪 配置测试通道...")
        success = rs485.configure_dilution_channels([test_channel])
        
        if success:
            print("   ✅ 通道配置成功")
            
            # 计算配液体积
            volume = rs485.prepare_dilution(1, 0.5, 1000)
            print(f"   📊 配液体积: {volume:.2f} μL")
            
            # 启动配液
            if rs485.start_dilution(1, volume):
                print("   ✅ 配液启动成功")
                
                # 检查进度
                import time
                time.sleep(1)
                progress = rs485.get_dilution_progress(1)
                print(f"   📈 配液进度: {progress}")
                
                return True
        
        return False
        
    except Exception as e:
        print(f"   ❌ 配液测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 MicroHySeeker 修复验证")
    print("=" * 50)
    
    success = test_fixed_configuration()
    
    if success:
        print("\n✅ 修复成功！现在可以正常使用Mock模式")
        print("\n建议操作:")
        print("   1. 重启UI: python run_ui.py") 
        print("   2. 测试配制溶液功能")
        print("   3. 硬件就绪后修改 config/system.json 中 mock_mode 为 false")
    else:
        print("\n❌ 仍有问题，请检查错误信息")
    
    print("=" * 50)