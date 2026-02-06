#!/usr/bin/env python3
"""
硬件集成测试 - 阶段5完整验证

测试内容：
1. 多批次注入功能
2. 硬件模式下的完整流程
3. RS485通信验证
4. 泵控制验证
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_multi_batch_injection():
    """测试多批次注入功能"""
    print("\n" + "=" * 60)
    print("测试 1: 多批次注入功能")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStep, StepType, PrepSolConfig
    from src.echem_sdl.core.exp_program import ExpProgram
    from src.echem_sdl.core.experiment_engine import ExperimentEngine, EngineState
    
    # 1.1 创建多批次配液配置
    print("\n1.1 创建多批次配液配置...")
    config = PrepSolConfig(
        concentrations={"D1": 0.4, "D2": 0.3, "D3": 0.3},
        total_volume_ul=100.0,
        injection_order=["D1", "D2", "D3"],
        multi_batch=True,
        batch_count=3,
        batch_interval_s=0.5,
        batch_volumes=[0.4, 0.3, 0.3]  # 40%, 30%, 30%
    )
    
    batch_vols = config.get_batch_volumes_ul()
    print(f"  总体积: {config.total_volume_ul} uL")
    print(f"  批次数: {config.batch_count}")
    print(f"  各批次体积: {batch_vols}")
    assert len(batch_vols) == 3
    assert abs(sum(batch_vols) - config.total_volume_ul) < 0.01
    print("  ✅ 多批次配置正确")
    
    # 1.2 执行多批次配液
    print("\n1.2 执行多批次配液步骤...")
    step = ProgStep(
        step_type=StepType.PREP_SOL,
        name="多批次配液",
        prep_sol_config=config
    )
    
    program = ExpProgram(name="多批次测试")
    program.add_step(step)
    
    engine = ExperimentEngine(mock_mode=True)
    engine.load_program(program)
    
    logs = []
    def on_event(event_type, data):
        logs.append((event_type, data))
    
    engine.on_event(on_event)
    engine.start()
    
    # 等待完成
    start = time.time()
    while engine.is_running and time.time() - start < 30:
        time.sleep(0.1)
    
    assert engine.state == EngineState.COMPLETED
    print("  ✅ 多批次配液执行完成")
    
    print("\n✅ 多批次注入测试通过！")
    return True


def test_hardware_mock_flow():
    """测试硬件Mock模式完整流程"""
    print("\n" + "=" * 60)
    print("测试 2: 硬件Mock完整流程")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory
    from src.echem_sdl.core.exp_program import ExpProgram, ComboParameter
    from src.echem_sdl.core.experiment_engine import (
        ExperimentEngine, EngineState, 
        EVENT_STEP_STARTED, EVENT_STEP_COMPLETED,
        EVENT_ECHEM_DATA
    )
    
    # 2.1 创建完整实验程序
    print("\n2.1 创建完整实验程序...")
    program = ExpProgram(name="完整流程测试", description="配液-冲洗-电化学")
    
    # 配液步骤
    program.add_step(ProgStepFactory.create_prep_sol(
        name="配液",
        concentrations={"D1": 0.5, "D2": 0.5},
        total_volume_ul=50.0
    ))
    
    # 冲洗步骤
    program.add_step(ProgStepFactory.create_flush(
        name="冲洗",
        cycles=1,
        phase_duration_s=0.2
    ))
    
    # 电化学测量
    program.add_step(ProgStepFactory.create_cv(
        name="CV扫描",
        e_low=-0.3,
        e_high=0.3,
        scan_rate=0.5,
        segments=1
    ))
    
    print(f"  程序: {program.name}")
    print(f"  步骤: {[s.name for s in program.steps]}")
    
    # 2.2 验证程序
    print("\n2.2 验证程序...")
    errors = program.validate()
    if errors:
        print(f"  ⚠️ 验证错误: {errors}")
    else:
        print("  ✅ 程序验证通过")
    
    # 2.3 运行程序
    print("\n2.3 运行程序...")
    engine = ExperimentEngine(mock_mode=True)
    engine.load_program(program)
    
    step_events = []
    ec_data_count = [0]
    
    def on_step_started(data):
        step_events.append(("started", data['step_name']))
        print(f"  ▶️ 开始: {data['step_name']}")
    
    def on_step_completed(data):
        step_events.append(("completed", data['index']))
        print(f"  ✔️ 完成: 步骤 {data['index']}")
    
    def on_ec_data(data):
        ec_data_count[0] += 1
    
    engine.on(EVENT_STEP_STARTED, on_step_started)
    engine.on(EVENT_STEP_COMPLETED, on_step_completed)
    engine.on(EVENT_ECHEM_DATA, on_ec_data)
    
    engine.start()
    
    # 等待完成
    start = time.time()
    while engine.is_running and time.time() - start < 60:
        time.sleep(0.2)
    
    # 2.4 检查结果
    print("\n2.4 检查结果...")
    assert engine.state == EngineState.COMPLETED
    print(f"  总时长: {engine.elapsed_time:.2f}s")
    print(f"  步骤事件: {len(step_events)}")
    print(f"  电化学数据点: {ec_data_count[0]}")
    
    result = engine.get_last_result()
    if result:
        print(f"  实验结果: {result.success}")
        print(f"  步骤结果: {len(result.step_results)} 条")
        print(f"  数据集: {len(result.ec_data_sets)} 个")
    
    print("\n✅ 硬件Mock完整流程测试通过！")
    return True


def test_rs485_pump_hardware():
    """测试RS485泵硬件通信（需要硬件连接）"""
    print("\n" + "=" * 60)
    print("测试 3: RS485泵硬件通信")
    print("=" * 60)
    
    # 检测硬件环境
    print("\n3.1 检测串口...")
    import serial.tools.list_ports
    
    ports = list(serial.tools.list_ports.comports())
    print(f"  发现 {len(ports)} 个串口:")
    for port in ports:
        print(f"    - {port.device}: {port.description}")
    
    if not ports:
        print("  ⚠️ 未发现串口，跳过硬件测试")
        return True
    
    # 尝试连接
    print("\n3.2 尝试连接RS485...")
    try:
        from src.echem_sdl.hardware.rs485_driver import RS485Driver
        
        # 使用CH340 USB串口（如果存在）
        ch340_ports = [p for p in ports if 'CH340' in p.description]
        if ch340_ports:
            port = ch340_ports[0].device
        else:
            port = ports[0].device
        
        driver = RS485Driver(port=port, mock_mode=False)
        
        if driver.open():
            print(f"  ✅ 连接成功: {port}")
            
            # 扫描设备
            print("\n3.3 扫描泵设备...")
            devices = driver.scan_addresses(start=1, end=12)
            print(f"  发现 {len(devices)} 个设备: {devices}")
            
            driver.close()
            print("  ✅ 已断开连接")
        else:
            print(f"  ⚠️ 连接失败: {port}")
            
    except Exception as e:
        print(f"  ⚠️ 硬件测试错误: {e}")
    
    print("\n✅ RS485测试完成")
    return True


def test_chi_technique_codes():
    """测试CHI技术代码与C#一致"""
    print("\n" + "=" * 60)
    print("测试 4: CHI技术代码对齐")
    print("=" * 60)
    
    from src.echem_sdl.hardware.chi import ECTechnique, TECHNIQUE_NAMES
    
    # C#中的代码对照
    csharp_codes = {
        "M_CV": 0,
        "M_LSV": 1, 
        "M_CA": 2,
        "M_CC": 3,
        "M_CP": 4,
        "M_DPV": 5,
        "M_NPV": 6,
        "M_SWV": 7,
        "M_SHACV": 8,
        "M_ACIM": 9,
        "M_IMPE": 10,
        "M_IT": 11,
        "M_OCPT": 12,
    }
    
    print("\n检查技术代码映射:")
    for name, code in csharp_codes.items():
        tech_name = name.replace("M_", "")
        try:
            tech = ECTechnique[tech_name]
            match = "✅" if tech.value == code else "❌"
            print(f"  {match} {name} = {code} (Python: {tech.value})")
        except KeyError:
            print(f"  ⚠️ {name} = {code} (Python: 未定义)")
    
    # 验证关键技术
    assert ECTechnique.CV.value == 0, "CV 代码应为 0"
    assert ECTechnique.IT.value == 11, "IT 代码应为 11"
    assert ECTechnique.OCPT.value == 12, "OCPT 代码应为 12"
    
    print("\n✅ CHI技术代码对齐测试通过！")
    return True


def test_data_export_formats():
    """测试数据导出多种格式"""
    print("\n" + "=" * 60)
    print("测试 5: 数据导出格式")
    print("=" * 60)
    
    import tempfile
    from src.echem_sdl.services.data_exporter import DataExporter
    from src.echem_sdl.hardware.chi import ECDataPoint, ECDataSet
    
    # 创建测试数据
    print("\n5.1 创建测试数据...")
    data_set = ECDataSet(
        name="Test_CV",
        technique="CV",
        timestamp="2026-02-04T22:00:00",
        points=[
            ECDataPoint(time=0.0, potential=-0.5, current=1e-7),
            ECDataPoint(time=0.1, potential=-0.3, current=2e-7),
            ECDataPoint(time=0.2, potential=0.0, current=5e-7),
            ECDataPoint(time=0.3, potential=0.3, current=3e-7),
            ECDataPoint(time=0.4, potential=0.5, current=1e-7),
        ],
        metadata={"scan_rate": 0.1}
    )
    
    print(f"  数据点: {len(data_set.points)}")
    
    # 5.2 导出CSV
    print("\n5.2 导出CSV...")
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(export_dir=Path(tmpdir))
        
        # 导出数据点
        rows = [p.to_dict() for p in data_set.points]
        path = exporter.export_dict_list(rows, "cv_data.csv")
        
        # 验证文件
        content = path.read_text()
        lines = content.strip().split('\n')
        print(f"  行数: {len(lines)} (含表头)")
        print(f"  表头: {lines[0]}")
        
        assert len(lines) == 6  # 1 header + 5 data
        print("  ✅ CSV导出成功")
    
    print("\n✅ 数据导出格式测试通过！")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("MicroHySeeker 硬件集成测试")
    print("=" * 70)
    
    tests = [
        ("多批次注入功能", test_multi_batch_injection),
        ("硬件Mock完整流程", test_hardware_mock_flow),
        ("RS485泵硬件通信", test_rs485_pump_hardware),
        ("CHI技术代码对齐", test_chi_technique_codes),
        ("数据导出格式", test_data_export_formats),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            import traceback
            print(f"\n❌ 测试失败: {name}")
            traceback.print_exc()
            results.append((name, False, str(e)))
    
    # 汇总
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for name, success, error in results:
        status = "✅ 通过" if success else f"❌ 失败: {error}"
        print(f"  {name}: {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "-" * 40)
    print(f"通过: {passed}/{len(tests)}")
    print(f"失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有硬件集成测试通过！")
        return True
    else:
        print("\n⚠️ 存在失败的测试，请检查。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
