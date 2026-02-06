#!/usr/bin/env python
"""
测试配液可行性验证功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from PySide6.QtWidgets import QApplication
from src.models import SystemConfig, DilutionChannel
from src.dialogs.prep_solution import PrepSolutionDialog

def test_feasibility_logic():
    """测试配液可行性检查逻辑"""
    print("🧪 测试配液可行性验证功能\n")
    
    # 创建QApplication
    app = QApplication(sys.argv)
    
    # 创建测试配置
    config = SystemConfig()
    config.dilution_channels = [
        DilutionChannel(
            channel_id=1,
            solution_name="H2SO4",
            stock_concentration=1.0,  # 1.0 M
            pump_address=4,
            color="#FF5722"
        ),
        DilutionChannel(
            channel_id=2,
            solution_name="NaOH", 
            stock_concentration=0.5,  # 0.5 M
            pump_address=5,
            color="#2196F3"
        ),
        DilutionChannel(
            channel_id=3,
            solution_name="H2O",
            stock_concentration=0.0,  # 溶剂
            pump_address=6,
            color="#00BCD4"
        )
    ]
    
    # 创建对话框实例用于测试
    dialog = PrepSolutionDialog(config)
    
    # 测试场景1：正常配制（0.1M H2SO4）
    print("📋 测试场景1：正常配制 (0.1M H2SO4)")
    channels = config.dilution_channels[:2]  # H2SO4, NaOH
    target_concs = [0.1, 0.0]  # 目标浓度
    is_solvents = [False, False]
    dialog.total_vol_spin.setValue(1.0)  # 1mL
    
    errors = dialog._check_dilution_feasibility(channels, target_concs, is_solvents)
    if errors:
        print("❌ 不可行:")
        for err in errors:
            print(f"   {err}")
    else:
        print("✅ 可配制")
    
    # 测试场景2：目标浓度过高（2.0M H2SO4，储备只有1.0M）
    print("\n📋 测试场景2：目标浓度过高")
    target_concs = [2.0, 0.0]  # 目标浓度高于储备浓度
    
    errors = dialog._check_dilution_feasibility(channels, target_concs, is_solvents)
    if errors:
        print("❌ 不可行:")
        for err in errors:
            print(f"   {err}")
    else:
        print("✅ 可配制")
    
    # 测试场景3：储备浓度为0
    print("\n📋 测试场景3：储备浓度为0")
    channels_with_zero = config.dilution_channels[2:]  # 只用H2O（浓度为0）
    target_concs = [0.1]  # 想要0.1M的水？
    is_solvents = [False]
    
    errors = dialog._check_dilution_feasibility(channels_with_zero, target_concs, is_solvents)
    if errors:
        print("❌ 不可行:")
        for err in errors:
            print(f"   {err}")
    else:
        print("✅ 可配制")
    
    # 测试场景4：多个溶剂
    print("\n📋 测试场景4：多个溶剂")
    channels = config.dilution_channels[:3]  # 所有通道
    target_concs = [0.1, 0.0, 0.0]
    is_solvents = [False, True, True]  # 两个溶剂
    
    errors = dialog._check_dilution_feasibility(channels, target_concs, is_solvents)
    if errors:
        print("❌ 不可行:")
        for err in errors:
            print(f"   {err}")
    else:
        print("✅ 可配制")
    
    # 测试场景5：体积计算超限
    print("\n📋 测试场景5：体积计算超限")
    channels = config.dilution_channels[:2]  # H2SO4, NaOH
    target_concs = [0.8, 0.4]  # 两个都很高的浓度
    is_solvents = [False, False]
    dialog.total_vol_spin.setValue(1.0)  # 1mL总体积
    
    errors = dialog._check_dilution_feasibility(channels, target_concs, is_solvents)
    if errors:
        print("❌ 不可行:")
        for err in errors:
            print(f"   {err}")
    else:
        print("✅ 可配制")
        # 显示计算的体积
        volumes = dialog._calculate_volumes_for_validation(channels, target_concs, is_solvents, 1000.0)
        total_needed = sum(volumes)
        print(f"   需要体积: {volumes} μL, 总计: {total_needed:.1f} μL")
    
    print("\n🎉 测试完成")

if __name__ == "__main__":
    test_feasibility_logic()