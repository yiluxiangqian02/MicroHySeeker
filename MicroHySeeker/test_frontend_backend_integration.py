#!/usr/bin/env python3
"""
前后端集成测试 - 验证所有操作类型

测试内容：
1. 所有6种操作类型的正确执行
2. 泵工作类型映射正确性
3. 组合实验功能
4. 程序保存/加载功能
5. 前端Experiment到后端ExpProgram的转换
"""
import sys
import time
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_pump_type_mapping():
    """测试泵工作类型映射"""
    print("\n" + "=" * 60)
    print("测试 1: 泵工作类型映射")
    print("=" * 60)
    
    from src.echem_sdl.lib_context import LibContext, PumpWorkType
    from src.models import SystemConfig, FlushChannel, DilutionChannel
    
    # 1.1 创建模拟配置
    print("\n1.1 创建系统配置...")
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
    
    # 1.2 加载配置到LibContext
    print("\n1.2 加载泵映射...")
    LibContext.configure_pumps_from_config(config)
    
    # 1.3 验证映射
    print("\n1.3 验证泵映射...")
    inlet = LibContext.get_inlet_pump()
    transfer = LibContext.get_transfer_pump()
    outlet = LibContext.get_outlet_pump()
    d1 = LibContext.get_diluter_pump("D1")
    d2 = LibContext.get_diluter_pump("D2")
    
    print(f"  Inlet泵: {inlet} (预期: 1)")
    print(f"  Transfer泵: {transfer} (预期: 2)")
    print(f"  Outlet泵: {outlet} (预期: 3)")
    print(f"  D1稀释泵: {d1} (预期: 4)")
    print(f"  D2稀释泵: {d2} (预期: 5)")
    
    assert inlet == 1, f"Inlet泵地址错误: {inlet}"
    assert transfer == 2, f"Transfer泵地址错误: {transfer}"
    assert outlet == 3, f"Outlet泵地址错误: {outlet}"
    assert d1 == 4, f"D1稀释泵地址错误: {d1}"
    assert d2 == 5, f"D2稀释泵地址错误: {d2}"
    
    print("\n✅ 泵工作类型映射测试通过！")
    return True


def test_all_step_types():
    """测试所有6种操作类型"""
    print("\n" + "=" * 60)
    print("测试 2: 所有操作类型执行")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory
    from src.echem_sdl.core.exp_program import ExpProgram
    from src.echem_sdl.core.experiment_engine import (
        ExperimentEngine, EngineState,
        EVENT_STEP_STARTED, EVENT_STEP_COMPLETED
    )
    
    # 2.1 创建包含所有步骤类型的程序
    print("\n2.1 创建完整程序（6种步骤类型）...")
    program = ExpProgram(name="完整测试", description="测试所有操作类型")
    
    # 配液 (prep_sol) - 使用稀释泵 D1, D2
    program.add_step(ProgStepFactory.create_prep_sol(
        name="配液",
        concentrations={"D1": 0.6, "D2": 0.4},
        total_volume_ul=100.0
    ))
    
    # 移液 (transfer) - 使用Transfer泵
    program.add_step(ProgStepFactory.create_transfer(
        name="移液",
        pump_address=0,  # 0表示自动使用Transfer泵
        volume_ul=50.0
    ))
    
    # 冲洗 (flush) - 使用Inlet泵（Flusher协调三泵）
    program.add_step(ProgStepFactory.create_flush(
        name="冲洗",
        cycles=1,
        phase_duration_s=0.2
    ))
    
    # 电化学 (echem) - 使用CHI仪器，快速扫描用于测试
    program.add_step(ProgStepFactory.create_cv(
        name="CV测量",
        e_low=-0.2,
        e_high=0.2,
        scan_rate=1.0,  # 快速扫描
        segments=1
    ))
    
    # 等待 (blank)
    program.add_step(ProgStepFactory.create_blank(
        name="等待",
        wait_time=0.2
    ))
    
    # 排空 (evacuate) - 使用Outlet泵
    program.add_step(ProgStepFactory.create_evacuate(
        name="排空",
        pump_address=0,  # 0表示自动使用Outlet泵
        evacuate_time=0.2
    ))
    
    print(f"  程序步骤: {[s.name for s in program.steps]}")
    print(f"  总步骤数: {program.step_count}")
    
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
    
    step_log = []
    
    def on_step_started(data):
        step_log.append(f"▶️ {data['step_name']}")
        print(f"  ▶️ 开始: {data['step_name']} ({data['step_type']})")
    
    def on_step_completed(data):
        step_log.append(f"✔️ 步骤{data['index']}")
        print(f"  ✔️ 完成: 步骤{data['index']}")
    
    engine.on(EVENT_STEP_STARTED, on_step_started)
    engine.on(EVENT_STEP_COMPLETED, on_step_completed)
    
    engine.start()
    
    # 等待完成（电化学测量需要更长时间）
    start = time.time()
    while engine.is_running and time.time() - start < 120:
        time.sleep(0.3)
    
    # 2.4 检查结果
    print("\n2.4 检查结果...")
    assert engine.state == EngineState.COMPLETED, f"状态错误: {engine.state}"
    assert len(step_log) == 12, f"步骤日志数错误: {len(step_log)}"  # 6 started + 6 completed
    
    result = engine.get_last_result()
    assert result is not None
    assert result.success
    assert len(result.step_results) == 6
    
    print(f"  总时长: {engine.elapsed_time:.2f}s")
    print(f"  步骤结果: {len(result.step_results)} 条")
    
    for sr in result.step_results:
        print(f"    - {sr['name']}: {'✅' if sr['success'] else '❌'}")
    
    print("\n✅ 所有操作类型执行测试通过！")
    return True


def test_frontend_conversion():
    """测试前端到后端的转换"""
    print("\n" + "=" * 60)
    print("测试 3: 前端到后端转换")
    print("=" * 60)
    
    from src.models import (
        Experiment, ProgStep as FEProgStep, ProgramStepType,
        PrepSolStep, ECSettings, ECTechnique
    )
    from src.echem_sdl.core.exp_program import ExpProgram
    
    # 3.1 创建前端Experiment
    print("\n3.1 创建前端Experiment...")
    fe_exp = Experiment(
        exp_id="test_001",
        exp_name="前端测试实验",
        notes="测试前后端转换"
    )
    
    # 添加移液步骤
    fe_exp.steps.append(FEProgStep(
        step_id="transfer_1",
        step_type=ProgramStepType.TRANSFER,
        pump_address=2,
        pump_direction="FWD",
        pump_rpm=100,
        volume_ul=50.0
    ))
    
    # 添加配液步骤
    fe_exp.steps.append(FEProgStep(
        step_id="prep_sol_1",
        step_type=ProgramStepType.PREP_SOL,
        prep_sol_params=PrepSolStep(
            target_concentration=0.1,
            injection_order=["D1", "D2"],
            total_volume_ul=100.0
        )
    ))
    
    # 添加冲洗步骤
    fe_exp.steps.append(FEProgStep(
        step_id="flush_1",
        step_type=ProgramStepType.FLUSH,
        flush_cycles=2,
        flush_cycle_duration_s=10.0
    ))
    
    # 添加电化学步骤
    fe_exp.steps.append(FEProgStep(
        step_id="echem_1",
        step_type=ProgramStepType.ECHEM,
        ec_settings=ECSettings(
            technique=ECTechnique.CV,
            e0=0.0,
            eh=0.5,
            el=-0.5,
            scan_rate=0.1,
            seg_num=2
        )
    ))
    
    # 添加等待步骤
    fe_exp.steps.append(FEProgStep(
        step_id="blank_1",
        step_type=ProgramStepType.BLANK,
        duration_s=5.0
    ))
    
    # 添加排空步骤
    fe_exp.steps.append(FEProgStep(
        step_id="evacuate_1",
        step_type=ProgramStepType.EVACUATE,
        pump_address=3,
        duration_s=10.0
    ))
    
    print(f"  前端步骤数: {len(fe_exp.steps)}")
    
    # 3.2 转换为后端ExpProgram
    print("\n3.2 转换为后端ExpProgram...")
    be_program = ExpProgram.from_frontend_experiment(fe_exp)
    
    print(f"  后端步骤数: {be_program.step_count}")
    assert be_program.step_count == len(fe_exp.steps)
    
    # 3.3 验证转换结果
    print("\n3.3 验证转换结果...")
    for i, step in enumerate(be_program.steps):
        fe_step = fe_exp.steps[i]
        print(f"  步骤{i}: {fe_step.step_type.value} -> {step.step_type.value}")
        assert fe_step.step_type.value == step.step_type.value
    
    print("\n✅ 前端到后端转换测试通过！")
    return True


def test_program_save_load():
    """测试程序保存和加载"""
    print("\n" + "=" * 60)
    print("测试 4: 程序保存/加载")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory
    from src.echem_sdl.core.exp_program import ExpProgram, ComboParameter
    
    # 4.1 创建程序
    print("\n4.1 创建程序...")
    program = ExpProgram(name="保存测试", description="测试程序序列化")
    
    program.add_step(ProgStepFactory.create_prep_sol(
        name="配液",
        concentrations={"D1": 0.5, "D2": 0.5},
        total_volume_ul=100.0
    ))
    program.add_step(ProgStepFactory.create_cv(
        name="CV",
        scan_rate=0.1
    ))
    
    # 添加组合参数
    program.add_combo_param(ComboParameter(
        name="扫描速率",
        target_path="steps[1].ec_config.scan_rate",
        values=[0.05, 0.1, 0.2],
        unit="V/s"
    ))
    
    print(f"  步骤数: {program.step_count}")
    print(f"  组合参数: {len(program.combo_params)}")
    
    # 4.2 保存程序
    print("\n4.2 保存程序...")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
    
    program.save(temp_path)
    print(f"  保存到: {temp_path}")
    
    # 检查文件内容
    content = temp_path.read_text(encoding='utf-8')
    data = json.loads(content)
    print(f"  JSON键: {list(data.keys())}")
    
    # 4.3 加载程序
    print("\n4.3 加载程序...")
    loaded = ExpProgram.load(temp_path)
    
    assert loaded.name == program.name
    assert loaded.step_count == program.step_count
    assert len(loaded.combo_params) == len(program.combo_params)
    
    print(f"  名称: {loaded.name}")
    print(f"  步骤: {loaded.step_count}")
    print(f"  组合参数: {len(loaded.combo_params)}")
    
    # 清理
    temp_path.unlink()
    
    print("\n✅ 程序保存/加载测试通过！")
    return True


def test_combo_experiment():
    """测试组合实验功能"""
    print("\n" + "=" * 60)
    print("测试 5: 组合实验")
    print("=" * 60)
    
    from src.echem_sdl.core.prog_step import ProgStepFactory
    from src.echem_sdl.core.exp_program import ExpProgram, ComboParameter
    from src.echem_sdl.core.experiment_engine import (
        ExperimentEngine, EngineState, EVENT_COMBO_ADVANCED
    )
    
    # 5.1 创建带组合参数的程序
    print("\n5.1 创建组合实验程序...")
    program = ExpProgram(name="组合实验测试")
    
    program.add_step(ProgStepFactory.create_blank(
        name="等待",
        wait_time=0.1
    ))
    program.add_step(ProgStepFactory.create_cv(
        name="CV",
        scan_rate=0.1
    ))
    
    # 添加多个组合参数
    program.add_combo_param(ComboParameter(
        name="等待时间",
        target_path="steps[0].blank_config.wait_time",
        values=[0.1, 0.15]
    ))
    program.add_combo_param(ComboParameter(
        name="扫描速率",
        target_path="steps[1].ec_config.scan_rate",
        values=[0.5, 1.0]
    ))
    
    program.fill_param_matrix()
    expected_combos = 2 * 2  # 2 等待时间 x 2 扫描速率
    print(f"  预期组合数: {expected_combos}")
    print(f"  实际组合数: {program.combo_count}")
    assert program.combo_count == expected_combos
    
    # 5.2 运行组合实验
    print("\n5.2 运行组合实验...")
    engine = ExperimentEngine(mock_mode=True)
    engine.load_program(program)
    
    combo_log = []
    
    def on_combo(data):
        combo_log.append(data)
        print(f"  📢 组合 {data['index']+1}/{data['total']}: {data['params']}")
    
    engine.on(EVENT_COMBO_ADVANCED, on_combo)
    
    engine.start(combo_mode=True)
    
    # 等待完成
    start = time.time()
    while engine.is_running and time.time() - start < 60:
        time.sleep(0.2)
    
    # 5.3 检查结果
    print("\n5.3 检查结果...")
    assert engine.state == EngineState.COMPLETED
    
    results = engine.get_results()
    print(f"  结果数: {len(results)}")
    
    # 应该有4个结果（第一个组合不触发事件）
    assert len(combo_log) == expected_combos - 1  # 排除第一个
    
    for i, r in enumerate(results):
        print(f"    结果{i+1}: combo={r.combo_index}, params={r.combo_params}")
    
    print("\n✅ 组合实验测试通过！")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("MicroHySeeker 前后端集成测试")
    print("=" * 70)
    
    tests = [
        ("泵工作类型映射", test_pump_type_mapping),
        ("所有操作类型执行", test_all_step_types),
        ("前端到后端转换", test_frontend_conversion),
        ("程序保存/加载", test_program_save_load),
        ("组合实验", test_combo_experiment),
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
        print("\n🎉 所有前后端集成测试通过！")
        return True
    else:
        print("\n⚠️ 存在失败的测试，请检查。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
