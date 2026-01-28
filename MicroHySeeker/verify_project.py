#!/usr/bin/env python
"""Quick verification script for the entire project."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("MicroHySeeker - 项目验证脚本")
print("=" * 60)

# 1. 测试导入
print("\n[1] 测试模块导入...")
try:
    from core import ExpProgram, ProgStep, PROG_STEP_SCHEMA, EXP_PROGRAM_SCHEMA
    print("  ✓ Core 模块导入成功")
except Exception as e:
    print(f"  ✗ Core 模块导入失败: {e}")
    sys.exit(1)

try:
    from services import SettingsService, LoggerService, TranslatorService
    print("  ✓ Services 模块导入成功")
except Exception as e:
    print(f"  ✗ Services 模块导入失败: {e}")
    sys.exit(1)

try:
    from hardware import PumpManager, RS485Driver
    print("  ✓ Hardware 模块导入成功")
except Exception as e:
    print(f"  ✗ Hardware 模块导入失败: {e}")
    sys.exit(1)

# 2. 测试数据序列化
print("\n[2] 测试数据序列化...")
try:
    step = ProgStep(
        step_id=1,
        step_type="配液",
        step_name="Test Step",
        solution_type="Solution A",
        high_concentration=1.0,
        target_volume=10.0,
        pump_address=1,
        pump_speed=5.0
    )
    step_dict = step.to_dict()
    step_restored = ProgStep.from_dict(step_dict)
    assert step_restored.step_id == 1
    assert step_restored.step_type == "配液"
    print("  ✓ ProgStep 序列化/反序列化成功")
except Exception as e:
    print(f"  ✗ ProgStep 序列化失败: {e}")
    sys.exit(1)

try:
    program = ExpProgram(
        program_id="prog_001",
        program_name="Test Program"
    )
    program.steps.append(step)
    prog_dict = program.to_dict()
    prog_json = json.dumps(prog_dict)
    prog_dict_restored = json.loads(prog_json)
    program_restored = ExpProgram.from_dict(prog_dict_restored)
    assert program_restored.program_id == "prog_001"
    assert len(program_restored.steps) == 1
    print("  ✓ ExpProgram JSON 序列化/反序列化成功")
except Exception as e:
    print(f"  ✗ ExpProgram JSON 序列化失败: {e}")
    sys.exit(1)

# 3. 测试硬件驱动
print("\n[3] 测试硬件驱动...")
try:
    pump_manager = PumpManager()
    pump_manager.add_syringe_pump(1, "COM1")
    pump_manager.add_peristaltic_pump(1, "COM1")
    pumps = pump_manager.list_all_pumps()
    assert 1 in pumps['syringe_pumps']
    assert 1 in pumps['peristaltic_pumps']
    print("  ✓ PumpManager 初始化成功")
except Exception as e:
    print(f"  ✗ PumpManager 失败: {e}")
    sys.exit(1)

try:
    rs485 = RS485Driver(port="COM1", use_mock=True)
    rs485.connect()
    assert rs485.is_connected
    devices = rs485.scan_devices()
    print(f"  ✓ RS485 驱动初始化成功 (扫描到 {len(devices)} 个设备)")
except Exception as e:
    print(f"  ✗ RS485 驱动失败: {e}")
    sys.exit(1)

# 4. 测试服务
print("\n[4] 测试应用服务...")
try:
    settings = SettingsService("test_config.json")
    settings.set("test_key", "test_value")
    assert settings.get("test_key") == "test_value"
    print("  ✓ SettingsService 工作正常")
except Exception as e:
    print(f"  ✗ SettingsService 失败: {e}")
    sys.exit(1)

try:
    logger = LoggerService("test_logs")
    logger.info("Test message")
    logger.warning("Test warning")
    assert len(logger.messages) >= 2
    print("  ✓ LoggerService 工作正常")
except Exception as e:
    print(f"  ✗ LoggerService 失败: {e}")
    sys.exit(1)

try:
    translator = TranslatorService("zh_CN")
    text = translator.translate("Save")
    assert isinstance(text, str)
    print("  ✓ TranslatorService 工作正常")
except Exception as e:
    print(f"  ✗ TranslatorService 失败: {e}")
    sys.exit(1)

# 5. 总结
print("\n" + "=" * 60)
print("✅ 所有验证测试通过！")
print("=" * 60)
print("\n应用可以启动运行:")
print("  python run_ui.py")
print("\n菜单快捷键:")
print("  • 文件 > 单次实验 (Alt+S)")
print("  • 工具 > 设置 (Alt+S)")
print("  • 工具 > 手动控制 (Alt+M)")
print("\n项目目录: F:\\BaiduSyncdisk\\micro1229\\MicroHySeeker")
print("="* 60)
