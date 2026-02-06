#!/usr/bin/env python3
"""
阶段5集成测试 - 实验引擎

测试内容：
1. ProgStep 创建和序列化
2. ExpProgram 管理和组合参数
3. CHInstrument Mock模式
4. ExperimentEngine 完整流程
5. 数据导出
"""
import sys
import time
import json
import tempfile
from pathlib import Path

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_prog_step():
    """测试 ProgStep 模块"""
    print("\n" + "=" * 60)
    print("测试 1: ProgStep 模块")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import (
        ProgStep, StepType, ProgStepFactory,
        PrepSolConfig, ECConfig, FlushConfig
    )
    
    # 1.1 创建各类型步骤
    print("\n1.1 创建各类型步骤...")
    
    steps = [
        ProgStepFactory.create_prep_sol(
            name="配液测试",
            concentrations={"D1": 0.1, "D2": 0.2},
            total_volume_ul=100.0
        ),
        ProgStepFactory.create_transfer(
            name="移液测试",
            pump_address=1,
            volume_ul=50.0
        ),
        ProgStepFactory.create_flush(
            name="冲洗测试",
            cycles=3
        ),
        ProgStepFactory.create_cv(
            name="CV测试",
            e_low=-0.5,
            e_high=0.5,
            scan_rate=0.1
        ),
        ProgStepFactory.create_blank(
            name="等待测试",
            wait_time=5.0
        ),
        ProgStepFactory.create_evacuate(
            name="抽空测试",
            evacuate_time=10.0
        ),
    ]
    
    for step in steps:
        duration = step.get_duration()
        errors = step.validate()
        print(f"  ✅ {step.name}: 类型={step.step_type.value}, 预估时长={duration:.1f}s, 验证={len(errors)==0}")
    
    # 1.2 序列化测试
    print("\n1.2 序列化测试...")
    cv_step = steps[3]
    json_str = cv_step.to_json()
    restored = ProgStep.from_json(json_str)
    assert restored.name == cv_step.name
    assert restored.step_type == cv_step.step_type
    assert restored.ec_config.scan_rate == cv_step.ec_config.scan_rate
    print(f"  ✅ JSON 序列化/反序列化成功")
    
    # 1.3 复制测试
    print("\n1.3 复制测试...")
    copy_step = cv_step.copy()
    copy_step.name = "CV复制"
    assert cv_step.name != copy_step.name
    print(f"  ✅ 步骤复制成功")
    
    print("\n✅ ProgStep 模块测试通过！")
    return True


def test_exp_program():
    """测试 ExpProgram 模块"""
    print("\n" + "=" * 60)
    print("测试 2: ExpProgram 模块")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory
    from src.echem_sdl.core.exp_program import ExpProgram, ComboParameter
    
    # 2.1 创建程序
    print("\n2.1 创建程序...")
    program = ExpProgram(name="测试程序", description="阶段5集成测试")
    
    # 添加步骤
    program.add_step(ProgStepFactory.create_flush(name="冲洗", cycles=2))
    program.add_step(ProgStepFactory.create_prep_sol(
        name="配液",
        concentrations={"D1": 0.1},
        total_volume_ul=100.0
    ))
    program.add_step(ProgStepFactory.create_cv(name="CV", scan_rate=0.1))
    
    print(f"  ✅ 程序创建: {program.step_count} 步骤")
    
    # 2.2 验证程序
    print("\n2.2 验证程序...")
    errors = program.validate()
    if errors:
        print(f"  ⚠️ 验证错误: {errors}")
    else:
        print(f"  ✅ 程序验证通过")
    
    # 2.3 程序摘要
    print("\n2.3 程序摘要...")
    summary = program.get_summary()
    print(f"  名称: {summary['name']}")
    print(f"  步骤数: {summary['step_count']}")
    print(f"  预估时长: {summary['single_duration_s']:.1f}s")
    
    # 2.4 组合参数
    print("\n2.4 组合参数...")
    program.add_combo_param(ComboParameter(
        name="扫描速率",
        target_path="steps[2].ec_config.scan_rate",
        values=[0.05, 0.1, 0.2],
        unit="V/s"
    ))
    
    program.fill_param_matrix()
    print(f"  ✅ 组合数: {program.combo_count}")
    
    # 加载不同组合
    for i in range(program.combo_count):
        program.load_param_values(i)
        params = program.get_current_params()
        print(f"  组合 {i+1}: {params}")
    
    # 2.5 序列化测试
    print("\n2.5 序列化测试...")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
    
    program.save(temp_path)
    loaded = ExpProgram.load(temp_path)
    
    assert loaded.name == program.name
    assert loaded.step_count == program.step_count
    assert len(loaded.combo_params) == len(program.combo_params)
    
    temp_path.unlink()
    print(f"  ✅ 文件保存/加载成功")
    
    print("\n✅ ExpProgram 模块测试通过！")
    return True


def test_chi_instrument():
    """测试 CHInstrument Mock模式"""
    print("\n" + "=" * 60)
    print("测试 3: CHInstrument Mock模式")
    print("=" * 60)
    
    from src.echem_sdl.hardware.chi import (
        CHIInstrument, ECParameters, ECTechnique, CHIState
    )
    
    # 3.1 创建 Mock CHI
    print("\n3.1 创建 Mock CHI...")
    chi = CHIInstrument(mock_mode=True)
    assert chi.state == CHIState.DISCONNECTED
    print(f"  ✅ CHI 创建成功, 状态: {chi.state.value}")
    
    # 3.2 连接
    print("\n3.2 连接...")
    result = chi.connect()
    assert result == True
    assert chi.state == CHIState.IDLE
    print(f"  ✅ 连接成功, 状态: {chi.state.value}")
    
    # 3.3 设置参数
    print("\n3.3 设置参数...")
    params = ECParameters(
        technique=ECTechnique.CV,
        e_init=0.0,
        e_high=0.5,
        e_low=-0.5,
        scan_rate=0.5,  # 快速扫描用于测试
        segments=2,
        quiet_time=0.1
    )
    chi.set_parameters(params)
    print(f"  ✅ CV 参数设置完成")
    
    # 3.4 估算时间
    print("\n3.4 估算时间...")
    duration = chi.get_estimated_duration(params)
    print(f"  预估时长: {duration:.1f}s")
    
    # 3.5 运行测量
    print("\n3.5 运行测量...")
    data_count = [0]
    
    def on_data(point):
        data_count[0] += 1
    
    chi.on_data(on_data)
    chi.run()
    
    # 等待一小段时间收集数据
    time.sleep(0.5)
    
    # 检查状态
    print(f"  运行中: {chi.is_running}")
    print(f"  数据点数: {data_count[0]}")
    
    # 停止
    chi.stop()
    print(f"  ✅ 测量已停止, 收集 {data_count[0]} 个数据点")
    
    # 3.6 获取数据
    print("\n3.6 获取数据...")
    data = chi.get_data()
    print(f"  总数据点: {len(data)}")
    if data:
        print(f"  第一个点: t={data[0].time:.3f}s, E={data[0].potential:.3f}V, I={data[0].current:.2e}A")
    
    # 3.7 获取数据集
    print("\n3.7 获取数据集...")
    data_set = chi.get_data_set()
    print(f"  数据集名称: {data_set.name}")
    print(f"  技术类型: {data_set.technique}")
    
    # 3.8 断开连接
    print("\n3.8 断开连接...")
    chi.disconnect()
    assert chi.state == CHIState.DISCONNECTED
    print(f"  ✅ 已断开连接")
    
    print("\n✅ CHInstrument Mock模式测试通过！")
    return True


def test_experiment_engine():
    """测试 ExperimentEngine"""
    print("\n" + "=" * 60)
    print("测试 4: ExperimentEngine")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory
    from src.echem_sdl.core.exp_program import ExpProgram
    from src.echem_sdl.core.experiment_engine import (
        ExperimentEngine, EngineState,
        EVENT_EXPERIMENT_STARTED, EVENT_EXPERIMENT_COMPLETED,
        EVENT_STEP_STARTED, EVENT_STEP_COMPLETED
    )
    
    # 4.1 创建引擎
    print("\n4.1 创建引擎...")
    engine = ExperimentEngine(context=None, mock_mode=True)
    assert engine.state == EngineState.IDLE
    print(f"  ✅ 引擎创建成功, 状态: {engine.state.value}")
    
    # 4.2 创建测试程序
    print("\n4.2 创建测试程序...")
    program = ExpProgram(name="快速测试")
    program.add_step(ProgStepFactory.create_blank(name="等待1", wait_time=0.2))
    program.add_step(ProgStepFactory.create_blank(name="等待2", wait_time=0.2))
    program.add_step(ProgStepFactory.create_blank(name="等待3", wait_time=0.2))
    print(f"  ✅ 程序创建: {program.step_count} 步骤")
    
    # 4.3 加载程序
    print("\n4.3 加载程序...")
    result = engine.load_program(program)
    assert result == True
    assert engine.state == EngineState.READY
    print(f"  ✅ 程序加载成功, 状态: {engine.state.value}")
    
    # 4.4 设置事件回调
    print("\n4.4 设置事件回调...")
    events = []
    
    def on_event(event_type, data):
        events.append((event_type, data))
        print(f"  📢 事件: {event_type}")
    
    engine.on_event(on_event)
    print(f"  ✅ 事件回调已设置")
    
    # 4.5 启动实验
    print("\n4.5 启动实验...")
    result = engine.start(combo_mode=False)
    assert result == True
    print(f"  ✅ 实验已启动")
    
    # 4.6 等待完成
    print("\n4.6 等待完成...")
    start_time = time.time()
    while engine.is_running and time.time() - start_time < 10:
        status = engine.get_status()
        print(f"  进度: {status.progress*100:.0f}%, 步骤: {status.current_step_index}")
        time.sleep(0.3)
    
    # 4.7 检查结果
    print("\n4.7 检查结果...")
    assert engine.state == EngineState.COMPLETED
    print(f"  ✅ 实验完成, 状态: {engine.state.value}")
    print(f"  总时长: {engine.elapsed_time:.2f}s")
    print(f"  事件数: {len(events)}")
    
    # 检查事件
    event_types = [e[0] for e in events]
    assert EVENT_EXPERIMENT_STARTED in event_types
    assert EVENT_EXPERIMENT_COMPLETED in event_types
    assert event_types.count(EVENT_STEP_STARTED) == 3
    assert event_types.count(EVENT_STEP_COMPLETED) == 3
    print(f"  ✅ 所有事件正确触发")
    
    print("\n✅ ExperimentEngine 测试通过！")
    return True


def test_engine_pause_stop():
    """测试引擎暂停和停止"""
    print("\n" + "=" * 60)
    print("测试 5: 引擎暂停和停止")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory
    from src.echem_sdl.core.exp_program import ExpProgram
    from src.echem_sdl.core.experiment_engine import ExperimentEngine, EngineState
    
    # 5.1 测试暂停/恢复
    print("\n5.1 测试暂停/恢复...")
    engine = ExperimentEngine(mock_mode=True)
    program = ExpProgram(name="暂停测试")
    program.add_step(ProgStepFactory.create_blank(name="长等待", wait_time=5.0))
    
    engine.load_program(program)
    engine.start()
    
    time.sleep(0.3)
    assert engine.is_running
    
    # 暂停
    engine.pause()
    assert engine.is_paused
    print(f"  ✅ 暂停成功")
    
    time.sleep(0.2)
    
    # 恢复
    engine.resume()
    assert engine.is_running
    print(f"  ✅ 恢复成功")
    
    # 5.2 测试停止
    print("\n5.2 测试停止...")
    time.sleep(0.2)
    engine.stop()
    time.sleep(0.3)
    assert engine.state == EngineState.IDLE
    print(f"  ✅ 停止成功")
    
    print("\n✅ 暂停/停止测试通过！")
    return True


def test_combo_experiment():
    """测试组合实验"""
    print("\n" + "=" * 60)
    print("测试 6: 组合实验")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory, ProgStep, StepType, BlankConfig
    from src.echem_sdl.core.exp_program import ExpProgram, ComboParameter
    from src.echem_sdl.core.experiment_engine import (
        ExperimentEngine, EngineState, EVENT_COMBO_ADVANCED
    )
    
    # 6.1 创建带组合参数的程序
    print("\n6.1 创建带组合参数的程序...")
    program = ExpProgram(name="组合测试")
    
    # 添加一个参数可变的步骤
    step = ProgStep(
        step_type=StepType.BLANK,
        name="可变等待",
        blank_config=BlankConfig(wait_time=0.1)
    )
    program.add_step(step)
    
    # 添加组合参数
    program.add_combo_param(ComboParameter(
        name="等待时间",
        target_path="steps[0].blank_config.wait_time",
        values=[0.1, 0.15, 0.2]  # 3个组合
    ))
    
    print(f"  ✅ 程序创建: {program.combo_count} 组合")
    
    # 6.2 运行组合实验
    print("\n6.2 运行组合实验...")
    engine = ExperimentEngine(mock_mode=True)
    engine.load_program(program)
    
    combo_events = []
    def on_combo(data):
        combo_events.append(data)
        print(f"  📢 组合切换: {data['index']+1}/{data['total']}")
    
    engine.on(EVENT_COMBO_ADVANCED, on_combo)
    
    engine.start(combo_mode=True)
    
    # 等待完成
    start_time = time.time()
    while engine.is_running and time.time() - start_time < 10:
        time.sleep(0.1)
    
    # 6.3 检查结果
    print("\n6.3 检查结果...")
    assert engine.state == EngineState.COMPLETED
    assert len(combo_events) == 2  # 第一个组合不触发事件，后续2个触发
    print(f"  ✅ 组合实验完成")
    
    results = engine.get_results()
    print(f"  结果数: {len(results)}")
    for i, result in enumerate(results):
        print(f"  结果 {i+1}: combo={result.combo_index}, params={result.combo_params}")
    
    print("\n✅ 组合实验测试通过！")
    return True


def test_echem_step():
    """测试电化学步骤执行"""
    print("\n" + "=" * 60)
    print("测试 7: 电化学步骤执行")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory
    from src.echem_sdl.core.exp_program import ExpProgram
    from src.echem_sdl.core.experiment_engine import (
        ExperimentEngine, EngineState, EVENT_ECHEM_DATA
    )
    
    # 7.1 创建包含电化学步骤的程序
    print("\n7.1 创建电化学程序...")
    program = ExpProgram(name="电化学测试")
    program.add_step(ProgStepFactory.create_cv(
        name="快速CV",
        e_low=-0.2,
        e_high=0.2,
        scan_rate=1.0,  # 快速扫描
        segments=1
    ))
    
    print(f"  ✅ 程序创建完成")
    
    # 7.2 运行并收集数据
    print("\n7.2 运行并收集数据...")
    engine = ExperimentEngine(mock_mode=True)
    engine.load_program(program)
    
    ec_data = []
    def on_ec_data(data):
        ec_data.append(data)
    
    engine.on(EVENT_ECHEM_DATA, on_ec_data)
    
    engine.start()
    
    # 等待完成
    start_time = time.time()
    while engine.is_running and time.time() - start_time < 10:
        time.sleep(0.1)
    
    # 7.3 检查结果
    print("\n7.3 检查结果...")
    assert engine.state == EngineState.COMPLETED
    print(f"  ✅ 电化学测量完成")
    print(f"  数据点数: {len(ec_data)}")
    
    result = engine.get_last_result()
    if result and result.ec_data_sets:
        ds = result.ec_data_sets[0]
        print(f"  数据集: {ds.name}, {len(ds.points)} 点")
    
    print("\n✅ 电化学步骤测试通过！")
    return True


def test_data_exporter():
    """测试数据导出"""
    print("\n" + "=" * 60)
    print("测试 8: 数据导出")
    print("=" * 60)
    
    from src.echem_sdl.services.data_exporter import DataExporter
    import tempfile
    
    # 8.1 创建导出器
    print("\n8.1 创建导出器...")
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = DataExporter(export_dir=Path(tmpdir))
        
        # 8.2 导出CSV
        print("\n8.2 导出CSV...")
        data = [(0.0, 1.0), (0.1, 1.5), (0.2, 2.0), (0.3, 1.8)]
        path = exporter.export_csv(data, "test_data.csv")
        assert path.exists()
        print(f"  ✅ CSV 导出成功: {path.name}")
        
        # 8.3 导出字典列表
        print("\n8.3 导出字典列表...")
        rows = [
            {"time": 0.0, "potential": 0.1, "current": 1e-6},
            {"time": 0.1, "potential": 0.2, "current": 2e-6},
        ]
        path = exporter.export_dict_list(rows, "test_rows.csv")
        assert path.exists()
        print(f"  ✅ 字典列表导出成功: {path.name}")
    
    print("\n✅ 数据导出测试通过！")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("MicroHySeeker 阶段5 集成测试")
    print("实验引擎模块")
    print("=" * 70)
    
    tests = [
        ("ProgStep 模块", test_prog_step),
        ("ExpProgram 模块", test_exp_program),
        ("CHInstrument Mock模式", test_chi_instrument),
        ("ExperimentEngine 基础", test_experiment_engine),
        ("引擎暂停/停止", test_engine_pause_stop),
        ("组合实验", test_combo_experiment),
        ("电化学步骤", test_echem_step),
        ("数据导出", test_data_exporter),
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
        print("\n🎉 所有测试通过！阶段5实验引擎已就绪。")
        return True
    else:
        print("\n⚠️ 存在失败的测试，请检查。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
