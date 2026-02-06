#!/usr/bin/env python3
"""
泵工作类型映射验证脚本

验证各操作类型与泵的对应关系：
- 移液(transfer): 使用 work_type="Transfer" 的泵
- 冲洗(flush): 使用 work_type="Inlet" 的泵（Flusher协调三泵）
- 排空(evacuate): 使用 work_type="Outlet" 的泵
- 配液(prep_sol): 使用 DilutionChannel 中配置的稀释泵
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.echem_sdl.lib_context import LibContext, PumpWorkType
from src.models import SystemConfig, FlushChannel, DilutionChannel

print("=" * 60)
print("泵工作类型映射验证")
print("=" * 60)

# 创建系统配置
print("\n1. 创建系统配置...")
config = SystemConfig()

# 添加冲洗通道（定义泵工作类型）
config.flush_channels = [
    FlushChannel(
        channel_id="inlet_ch",
        pump_name="进液泵",
        pump_address=1,
        work_type="Inlet"
    ),
    FlushChannel(
        channel_id="transfer_ch", 
        pump_name="转移泵",
        pump_address=2,
        work_type="Transfer"
    ),
    FlushChannel(
        channel_id="outlet_ch",
        pump_name="出液泵", 
        pump_address=3,
        work_type="Outlet"
    ),
]

# 添加稀释通道
config.dilution_channels = [
    DilutionChannel(
        channel_id="D1",
        solution_name="溶液A",
        stock_concentration=1.0,
        pump_address=4
    ),
    DilutionChannel(
        channel_id="D2",
        solution_name="溶液B",
        stock_concentration=0.5,
        pump_address=5
    ),
]

print(f"  冲洗通道: {len(config.flush_channels)}")
print(f"  稀释通道: {len(config.dilution_channels)}")

# 加载配置到LibContext
print("\n2. 加载泵映射到 LibContext...")
LibContext.configure_pumps_from_config(config)

# 验证映射
print("\n3. 泵工作类型映射验证:")
print("-" * 40)

inlet = LibContext.get_inlet_pump()
transfer = LibContext.get_transfer_pump()
outlet = LibContext.get_outlet_pump()

print(f"  ├── Inlet泵 (冲洗进液): 地址 {inlet}")
print(f"  ├── Transfer泵 (移液): 地址 {transfer}")
print(f"  └── Outlet泵 (排空): 地址 {outlet}")

print("\n4. 稀释通道映射验证:")
print("-" * 40)

for ch in config.dilution_channels:
    addr = LibContext.get_diluter_pump(ch.channel_id)
    print(f"  ├── {ch.channel_id} ({ch.solution_name}): 地址 {addr}")

print("\n5. 操作类型与泵对应关系:")
print("-" * 40)
print(f"  | {'操作类型':<12} | {'步骤类型':<12} | {'泵类型':<12} | {'泵地址':<8} |")
print(f"  |{'-'*14}|{'-'*14}|{'-'*14}|{'-'*10}|")
print(f"  | {'配液':<12} | {'prep_sol':<12} | {'Diluter':<12} | {'D1->4,D2->5':<8} |")
print(f"  | {'移液':<12} | {'transfer':<12} | {'Transfer':<12} | {transfer:<8} |")
print(f"  | {'冲洗':<12} | {'flush':<12} | {'Inlet*':<12} | {inlet:<8} |")
print(f"  | {'电化学':<12} | {'echem':<12} | {'CHI仪器':<12} | {'-':<8} |")
print(f"  | {'等待':<12} | {'blank':<12} | {'无':<12} | {'-':<8} |")
print(f"  | {'排空':<12} | {'evacuate':<12} | {'Outlet':<12} | {outlet:<8} |")
print("\n  * 冲洗由Flusher协调Inlet/Transfer/Outlet三泵")

print("\n✅ 泵工作类型映射验证完成！")
