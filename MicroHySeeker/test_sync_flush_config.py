"""
测试冲洗配置同步

验证 ConfigDialog 中的冲洗通道配置与 FlusherDialog 正确同步
"""
import sys
sys.path.insert(0, '.')

from src.models import SystemConfig, FlushChannel

def test_flusher_dialog_reads_config():
    """测试 FlusherDialog 从系统配置读取冲洗通道"""
    # 创建带有完整冲洗配置的 SystemConfig
    config = SystemConfig()
    
    # 添加三个冲洗通道
    config.flush_channels = [
        FlushChannel(
            channel_id="1",
            pump_name="进水泵",
            pump_address=5,
            direction="FWD",
            rpm=150,
            cycle_duration_s=15.0,
            work_type="Inlet"
        ),
        FlushChannel(
            channel_id="2",
            pump_name="移液泵",
            pump_address=6,
            direction="FWD",
            rpm=200,
            cycle_duration_s=20.0,
            work_type="Transfer"
        ),
        FlushChannel(
            channel_id="3",
            pump_name="出水泵",
            pump_address=7,
            direction="REV",
            rpm=250,
            cycle_duration_s=25.0,
            work_type="Outlet"
        )
    ]
    
    # 创建 FlusherDialog (不显示UI)
    from src.dialogs.flusher_dialog import FlusherDialog
    
    # 测试解析逻辑
    dialog = FlusherDialog.__new__(FlusherDialog)
    dialog.config = config
    dialog._inlet_channel = None
    dialog._transfer_channel = None
    dialog._outlet_channel = None
    dialog._parse_flush_channels()
    
    # 验证解析结果
    assert dialog._inlet_channel is not None, "Inlet channel should be parsed"
    assert dialog._transfer_channel is not None, "Transfer channel should be parsed"
    assert dialog._outlet_channel is not None, "Outlet channel should be parsed"
    
    assert dialog._inlet_channel.pump_address == 5, f"Inlet address should be 5, got {dialog._inlet_channel.pump_address}"
    assert dialog._inlet_channel.rpm == 150, f"Inlet rpm should be 150, got {dialog._inlet_channel.rpm}"
    
    assert dialog._transfer_channel.pump_address == 6, f"Transfer address should be 6, got {dialog._transfer_channel.pump_address}"
    assert dialog._transfer_channel.rpm == 200, f"Transfer rpm should be 200, got {dialog._transfer_channel.rpm}"
    
    assert dialog._outlet_channel.pump_address == 7, f"Outlet address should be 7, got {dialog._outlet_channel.pump_address}"
    assert dialog._outlet_channel.direction == "REV", f"Outlet direction should be REV"
    
    print("✅ 冲洗通道解析测试通过")


def test_incomplete_config_detection():
    """测试不完整配置检测"""
    config = SystemConfig()
    
    # 只添加两个通道
    config.flush_channels = [
        FlushChannel(
            channel_id="1",
            pump_name="进水泵",
            pump_address=5,
            direction="FWD",
            work_type="Inlet"
        ),
        FlushChannel(
            channel_id="2",
            pump_name="移液泵",
            pump_address=6,
            direction="FWD",
            work_type="Transfer"
        )
    ]
    
    from src.dialogs.flusher_dialog import FlusherDialog
    
    dialog = FlusherDialog.__new__(FlusherDialog)
    dialog.config = config
    dialog._inlet_channel = None
    dialog._transfer_channel = None
    dialog._outlet_channel = None
    dialog._parse_flush_channels()
    
    # 应该检测到配置不完整
    assert not dialog._check_config_complete(), "Config should be incomplete (missing Outlet)"
    
    print("✅ 不完整配置检测测试通过")


def test_get_channel_display():
    """测试通道显示文本生成"""
    from src.dialogs.flusher_dialog import FlusherDialog
    
    channel = FlushChannel(
        channel_id="1",
        pump_name="测试泵",
        pump_address=8,
        direction="REV",
        rpm=300,
        cycle_duration_s=12.5,
        work_type="Transfer"
    )
    
    dialog = FlusherDialog.__new__(FlusherDialog)
    
    assert dialog._get_channel_display(channel, 'address') == "泵 8"
    assert dialog._get_channel_display(channel, 'direction') == "反向"
    assert dialog._get_channel_display(channel, 'rpm') == "300"
    assert dialog._get_channel_display(channel, 'duration') == "12.5"
    
    # 测试未配置通道
    assert dialog._get_channel_display(None, 'address') == "<未配置>"
    
    print("✅ 通道显示文本测试通过")


if __name__ == "__main__":
    test_flusher_dialog_reads_config()
    test_incomplete_config_detection()
    test_get_channel_display()
    print("\n🎉 所有测试通过！冲洗配置同步功能正常工作")
