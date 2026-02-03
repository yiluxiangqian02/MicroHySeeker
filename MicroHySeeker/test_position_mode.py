"""
SR_VFOC 位置模式功能测试脚本

测试内容:
1. 协议层：位置帧构建和解码
2. PumpManager：位置模式方法
3. Diluter：位置模式注液

用法:
    python test_position_mode.py
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from src.echem_sdl.utils.constants import (
    ENCODER_DIVISIONS_PER_REV,
    CMD_POSITION_REL,
    CMD_POSITION_ABS,
    CMD_READ_ENCODER_ACCUM,
    DEFAULT_DILUTION_SPEED,
    DEFAULT_DILUTION_ACCELERATION,
    RUN_STATUS_STOPPED,
    POS_CTRL_START,
    POS_CTRL_COMPLETE,
)
from src.echem_sdl.hardware.rs485_protocol import (
    build_position_rel_frame,
    build_position_abs_frame,
    build_read_encoder_accum_frame,
    build_read_run_status_frame,
    decode_encoder_accum,
    decode_run_status,
    decode_position_response,
)
from src.echem_sdl.hardware.diluter import Diluter, DiluterConfig


def test_protocol_layer():
    """测试协议层函数"""
    print("\n" + "="*60)
    print(" 1. 协议层测试")
    print("="*60)
    
    # 测试位置模式3帧构建 (0xF4)
    print("\n[测试] build_position_rel_frame()")
    frame = build_position_rel_frame(addr=1, rel_axis=16384, speed=600, acceleration=2)
    print(f"  地址=1, 位移=16384(1圈), 速度=600RPM, 加速度=2")
    print(f"  帧数据: {frame.hex(' ')}")
    print(f"  帧长度: {len(frame)} 字节")
    assert frame[0] == 0xFA, "帧头错误"
    assert frame[1] == 0x01, "地址错误"
    assert frame[2] == CMD_POSITION_REL, "命令错误"
    print("  ✅ 通过")
    
    # 测试位置模式4帧构建 (0xF5)
    print("\n[测试] build_position_abs_frame()")
    frame = build_position_abs_frame(addr=2, abs_axis=32768, speed=300, acceleration=5)
    print(f"  地址=2, 绝对位置=32768(2圈), 速度=300RPM, 加速度=5")
    print(f"  帧数据: {frame.hex(' ')}")
    assert frame[2] == CMD_POSITION_ABS, "命令错误"
    print("  ✅ 通过")
    
    # 测试反转（负值）
    print("\n[测试] build_position_rel_frame() 反转")
    frame = build_position_rel_frame(addr=1, rel_axis=-8192, speed=100, acceleration=2)
    print(f"  地址=1, 位移=-8192(反转0.5圈)")
    print(f"  帧数据: {frame.hex(' ')}")
    # 验证负数编码
    # 帧格式: FA(1) addr(1) cmd(1) speed(2) acc(1) relAxis(4) CRC(1)
    # 坐标值在索引 6-9 (第7-10字节)
    rel_bytes = frame[6:10]  # 坐标值4字节
    rel_value = int.from_bytes(rel_bytes, 'big', signed=True)
    print(f"  坐标字节: {rel_bytes.hex(' ')} -> {rel_value}")
    assert rel_value == -8192, f"负数编码错误: {rel_value}"
    print("  ✅ 通过")
    
    # 测试读取编码器累加值帧构建
    print("\n[测试] build_read_encoder_accum_frame()")
    frame = build_read_encoder_accum_frame(addr=3)
    print(f"  地址=3")
    print(f"  帧数据: {frame.hex(' ')}")
    assert frame[2] == CMD_READ_ENCODER_ACCUM, "命令错误"
    print("  ✅ 通过")
    
    # 测试编码器累加值解码
    print("\n[测试] decode_encoder_accum()")
    # 正值: 1圈 = 0x4000
    data_pos = bytes([0x00, 0x00, 0x00, 0x00, 0x40, 0x00])
    value = decode_encoder_accum(data_pos)
    print(f"  数据: {data_pos.hex(' ')} -> {value} (预期16384)")
    assert value == 16384, f"正值解码错误: {value}"
    
    # 负值: -1圈
    data_neg = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xC0, 0x00])
    value_neg = decode_encoder_accum(data_neg)
    print(f"  数据: {data_neg.hex(' ')} -> {value_neg} (预期-16384)")
    assert value_neg == -16384, f"负值解码错误: {value_neg}"
    print("  ✅ 通过")
    
    # 测试运行状态解码
    print("\n[测试] decode_run_status()")
    assert decode_run_status(bytes([0x01])) == 1, "停止状态错误"
    assert decode_run_status(bytes([0x04])) == 4, "全速状态错误"
    print("  ✅ 通过")
    
    # 测试位置响应解码
    print("\n[测试] decode_position_response()")
    assert decode_position_response(bytes([POS_CTRL_START])) == POS_CTRL_START
    assert decode_position_response(bytes([POS_CTRL_COMPLETE])) == POS_CTRL_COMPLETE
    print("  ✅ 通过")
    
    print("\n✅ 协议层测试全部通过!")
    return True


def test_diluter_calculation():
    """测试Diluter的编码器计数计算"""
    print("\n" + "="*60)
    print(" 2. Diluter计算测试 (Mock模式)")
    print("="*60)
    
    # 创建配置
    config = DiluterConfig(
        address=1,
        name="测试溶液",
        stock_concentration=1.0,
        default_rpm=100,
        tube_diameter_mm=1.0,
        ul_per_encoder_count=0.0,  # 未校准
        calibration_valid=False
    )
    
    # 创建Mock模式Diluter
    diluter = Diluter(
        config=config,
        pump_manager=None,  # Mock模式不需要
        logger=None,
        mock_mode=True
    )
    
    # 测试未校准时的编码器计数计算
    print("\n[测试] calculate_encoder_counts() - 未校准")
    counts = diluter.calculate_encoder_counts(100.0)  # 100μL
    expected = int(100.0 / 100.0 * ENCODER_DIVISIONS_PER_REV)  # 假设每圈100μL
    print(f"  100μL -> {counts} counts (预期约{expected})")
    assert counts == expected, f"未校准计算错误: {counts}"
    print("  ✅ 通过")
    
    # 测试设置校准后的计算
    print("\n[测试] set_calibration() 和 calculate_encoder_counts()")
    # 设置校准: 每count = 0.01μL (即每圈约163.84μL)
    diluter.set_calibration(0.01)
    assert diluter.config.calibration_valid, "校准状态错误"
    
    counts_calibrated = diluter.calculate_encoder_counts(100.0)  # 100μL
    expected_calibrated = int(100.0 / 0.01)  # 10000 counts
    print(f"  100μL -> {counts_calibrated} counts (预期{expected_calibrated})")
    assert counts_calibrated == expected_calibrated, f"校准后计算错误: {counts_calibrated}"
    print("  ✅ 通过")
    
    # 测试Mock模式注液
    print("\n[测试] infuse_by_position() - Mock模式")
    diluter.prepare(target_conc=0.5, total_volume_ul=200.0)
    print(f"  目标体积: {diluter.target_volume_ul}μL")
    
    # 同步模式（等待完成）
    import time
    start = time.time()
    success = diluter.infuse_by_position(
        speed=200,
        wait_complete=True,
        timeout_s=5.0
    )
    elapsed = time.time() - start
    print(f"  注液结果: {'成功' if success else '失败'}, 耗时: {elapsed:.2f}s")
    print(f"  状态: {diluter.state}")
    assert success, "Mock注液失败"
    assert diluter.has_infused, "状态未更新为completed"
    print("  ✅ 通过")
    
    print("\n✅ Diluter计算测试全部通过!")
    return True


def test_constants():
    """验证常量定义"""
    print("\n" + "="*60)
    print(" 3. 常量定义验证")
    print("="*60)
    
    print(f"  ENCODER_DIVISIONS_PER_REV = {ENCODER_DIVISIONS_PER_REV} (预期16384)")
    assert ENCODER_DIVISIONS_PER_REV == 16384
    
    print(f"  CMD_POSITION_REL = 0x{CMD_POSITION_REL:02X} (预期0xF4)")
    assert CMD_POSITION_REL == 0xF4
    
    print(f"  CMD_POSITION_ABS = 0x{CMD_POSITION_ABS:02X} (预期0xF5)")
    assert CMD_POSITION_ABS == 0xF5
    
    print(f"  DEFAULT_DILUTION_SPEED = {DEFAULT_DILUTION_SPEED}")
    print(f"  DEFAULT_DILUTION_ACCELERATION = {DEFAULT_DILUTION_ACCELERATION}")
    
    print("\n✅ 常量定义验证通过!")
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print(" SR_VFOC 位置模式功能测试")
    print("="*60)
    
    results = []
    
    try:
        results.append(("常量定义", test_constants()))
    except Exception as e:
        print(f"\n❌ 常量定义测试失败: {e}")
        results.append(("常量定义", False))
    
    try:
        results.append(("协议层", test_protocol_layer()))
    except Exception as e:
        print(f"\n❌ 协议层测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("协议层", False))
    
    try:
        results.append(("Diluter计算", test_diluter_calculation()))
    except Exception as e:
        print(f"\n❌ Diluter计算测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Diluter计算", False))
    
    # 汇总结果
    print("\n" + "="*60)
    print(" 测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print("\n⚠️ 有测试失败，请检查!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
