#!/usr/bin/env python
"""
硬件模式问题诊断和修复脚本
"""
import sys
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def diagnose_hardware_issues():
    """诊断硬件控制问题"""
    print("=" * 60)
    print("🔍 MicroHySeeker 硬件问题诊断")
    print("=" * 60)
    
    # 1. 检查配置文件
    config_path = Path("config/system.json")
    print(f"\n[1] 检查配置文件: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"   串口: {config.get('rs485_port', 'N/A')}")
        print(f"   波特率: {config.get('rs485_baudrate', 'N/A')}")
        print(f"   Mock模式: {config.get('mock_mode', 'N/A')}")
        
        # 检查是否需要修改为Mock模式
        if not config.get('mock_mode', True):
            print("   ⚠️ 当前配置为真实硬件模式，但可能硬件未连接")
            
            response = input("\n是否切换到Mock模式进行测试？[Y/n]: ")
            if response.lower() in ['', 'y', 'yes']:
                return fix_mock_mode(config_path, config)
    
    except Exception as e:
        print(f"   ❌ 读取配置文件失败: {e}")
        return False
    
    # 2. 测试RS485连接
    print(f"\n[2] 测试RS485连接...")
    return test_rs485_connection(config)

def fix_mock_mode(config_path, config):
    """修复Mock模式配置"""
    print(f"\n🔧 修复Mock模式配置...")
    
    # 备份原配置
    backup_path = config_path.with_suffix('.json.backup')
    try:
        import shutil
        shutil.copy2(config_path, backup_path)
        print(f"   ✅ 已备份原配置到: {backup_path}")
    except Exception as e:
        print(f"   ⚠️ 备份失败: {e}")
    
    # 修改配置
    config['mock_mode'] = True
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"   ✅ 已设置mock_mode=true")
        
        # 测试修复后的配置
        return test_mock_mode()
        
    except Exception as e:
        print(f"   ❌ 修改配置失败: {e}")
        return False

def test_rs485_connection(config):
    """测试RS485真实硬件连接"""
    print("   测试真实硬件连接...")
    
    try:
        from src.services.rs485_wrapper import RS485Wrapper
        
        # 创建新的RS485实例（不使用单例）
        rs485 = RS485Wrapper()
        rs485.set_mock_mode(False)  # 强制真实硬件模式
        
        # 尝试连接
        success = rs485.open_port(config['rs485_port'], config['rs485_baudrate'])
        
        if success:
            print("   ✅ 硬件连接成功")
            
            # 扫描泵
            pumps = rs485.scan_pumps()
            print(f"   📡 扫描到泵: {pumps}")
            
            if len(pumps) > 0:
                # 测试单个泵
                test_pump = pumps[0]
                print(f"   🧪 测试泵 {test_pump}...")
                
                test_success = rs485.start_pump(test_pump, "FWD", 60)
                if test_success:
                    import time
                    time.sleep(1)
                    rs485.stop_pump(test_pump)
                    print(f"   ✅ 泵 {test_pump} 测试成功")
                    rs485.close_port()
                    return True
                else:
                    print(f"   ❌ 泵 {test_pump} 启动失败")
            else:
                print("   ⚠️ 未扫描到任何泵，可能硬件未连接")
        
        rs485.close_port()
        
    except Exception as e:
        print(f"   ❌ 硬件测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n   💡 建议切换到Mock模式进行开发测试")
    return False

def test_mock_mode():
    """测试Mock模式"""
    print(f"\n[3] 测试Mock模式...")
    
    try:
        from src.services.rs485_wrapper import get_rs485_instance
        
        # 重新获取实例（应该读取新配置）
        rs485 = get_rs485_instance()
        
        if not rs485.is_connected():
            print("   ❌ Mock模式连接失败")
            return False
        
        print("   ✅ Mock模式连接成功")
        
        # 创建测试通道
        from src.models import DilutionChannel
        
        test_channels = [
            DilutionChannel(
                channel_id="test1",
                solution_name="测试溶液1",
                stock_concentration=1.0,
                pump_address=1,
                default_rpm=120
            )
        ]
        
        # 配置测试
        success = rs485.configure_dilution_channels(test_channels)
        if success:
            print("   ✅ 配液通道配置成功")
            
            # 快速配液测试
            volume = rs485.prepare_dilution(1, 0.5, 1000)
            if volume > 0:
                print(f"   ✅ 配液计算成功: {volume:.2f} μL")
                
                # 启动配液
                if rs485.start_dilution(1, volume):
                    print("   ✅ Mock配液启动成功")
                    
                    # 等待完成
                    import time
                    time.sleep(2)
                    
                    progress = rs485.get_dilution_progress(1)
                    print(f"   📊 配液状态: {progress}")
                    
                    return True
        
        return False
        
    except Exception as e:
        print(f"   ❌ Mock模式测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主诊断流程"""
    try:
        success = diagnose_hardware_issues()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ 问题修复完成！建议操作:")
            print("   1. 重新启动UI: python run_ui.py")
            print("   2. 使用Mock模式进行配液测试")
            print("   3. 等硬件就绪后再切换到真实模式")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ 问题未完全解决，建议:")
            print("   1. 检查硬件连接（COM3端口）")
            print("   2. 确认泵设备电源开启") 
            print("   3. 检查RS485通信线路")
            print("   4. 或继续使用Mock模式开发")
            print("=" * 60)
        
        return success
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 诊断异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)