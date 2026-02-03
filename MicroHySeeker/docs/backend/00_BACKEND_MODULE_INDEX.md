# MicroHySeeker 后端模块总览索引

> **版本**: v4.0  
> **更新日期**: 2026-02-02  
> **状态**: 渐进式开发中 - 阶段3

---

## ⚠️ 开始前必读

**如果你是新接手的AI，请按以下顺序阅读文档**：

1. **[MASTER_PLAN.md](./MASTER_PLAN.md)** ⭐⭐⭐ **最重要** - 唯一的总领规划文档
   - 包含：项目概述、架构、5个开发阶段、前后端对接原则
   
2. **[STAGE_PROMPTS.md](./STAGE_PROMPTS.md)** ⭐⭐ - 分阶段提示词
   - 包含：每个阶段的独立提示词，可直接复制使用
   
3. **本文档** (00_BACKEND_MODULE_INDEX.md) ⭐ - 模块索引
   - 快速查找具体模块文档

4. **具体模块文档** (01-18) - 详细实现规范
   - 按需查阅

---

## 🎯 快速开始

### 如果你想了解整体规划
→ 阅读 [MASTER_PLAN.md](./MASTER_PLAN.md)

### 如果你想开始阶段3开发
→ 复制 [STAGE_PROMPTS.md](./STAGE_PROMPTS.md) 中的阶段3提示词

### 如果你想实现某个具体模块
→ 在下面找到对应的模块编号（01-18），查看详细文档

---

## 🚀 当前开发状态

| 阶段 | 目标前端功能 | 模块 | 状态 |
|------|------------|------|------|
| **阶段1** | RS485连接测试 | 01, 02 | ✅ 完成 |
| **阶段2** | 手动控制泵 | 05, 11 | ✅ 完成 |
| **阶段3** | 配置溶液并运行 | 03, 13 | ⭐ 当前 |
| **阶段4** | 冲洗功能 | 04 | ⏳ 待做 |
| **阶段5** | 完整实验流程 | 06, 08, 09, 10 | ⏳ 待做 |

**详见**: [MASTER_PLAN.md 第4节](./MASTER_PLAN.md#4-模块列表与阶段分配)

---

## 一、前端完成度评估

### 1.1 现有前端实现概览

| 模块 | 文件路径 | 完成度 | 说明 |
|------|----------|--------|------|
| **MainWindow** | `src/ui/main_window.py` | ✅ 90% | 主界面布局完成，泵状态显示，日志区域，步骤列表 |
| **ProgramEditorDialog** | `src/dialogs/program_editor.py` | ✅ 85% | 步骤编辑器完成，支持所有步骤类型 |
| **ConfigDialog** | `src/dialogs/config_dialog.py` | ✅ 80% | RS485配置、通道配置基本完成 |
| **ManualControlDialog** | `src/dialogs/manual_control.py` | ✅ 75% | 手动控制泵基本功能 |
| **ComboExpEditor** | `src/dialogs/combo_exp_editor.py` | ✅ 70% | 组合实验编辑器框架完成 |
| **CalibrateDialog** | `src/dialogs/calibrate_dialog.py` | ✅ 60% | 校准界面基础 |
| **PrepSolutionDialog** | `src/dialogs/prep_solution.py` | ✅ 60% | 配液界面基础 |

### 1.2 数据模型实现

| 模型 | 文件路径 | 完成度 | 说明 |
|------|----------|--------|------|
| **SystemConfig** | `src/models.py` | ✅ 完成 | 系统配置数据类 |
| **PumpConfig** | `src/models.py` | ✅ 完成 | 泵配置 |
| **DilutionChannel** | `src/models.py` | ✅ 完成 | 配液通道 |
| **FlushChannel** | `src/models.py` | ✅ 完成 | 冲洗通道 |
| **ProgStep** | `src/models.py` | ✅ 完成 | 程序步骤 |
| **Experiment** | `src/models.py` | ✅ 完成 | 实验程序 |
| **ECSettings** | `src/models.py` | ✅ 完成 | 电化学设置 |

### 1.3 服务层实现

| 服务 | 文件路径 | 完成度 | 说明 |
|------|----------|--------|------|
| **SettingsService** | `src/services/settings_service.py` | ✅ 完成 | JSON配置读写 |
| **LoggerService** | `src/services/logger_service.py` | ✅ 完成 | 日志服务(Qt信号) |
| **TranslatorService** | `src/services/translator_service.py` | ⚠️ 框架 | 多语言支持框架 |
| **RS485Wrapper** | `src/services/rs485_wrapper.py` | ⚠️ 50% | 需要完善真实硬件支持 |

### 1.4 硬件层实现

| 模块 | 文件路径 | 完成度 | 说明 |
|------|----------|--------|------|
| **RS485Driver** | `src/hardware/rs485_driver.py` | ⚠️ Mock | 仅mock实现 |
| **PumpDriver** | `src/hardware/pumps.py` | ⚠️ Mock | 仅mock实现 |
| **CHIDriver** | `src/hardware/chi.py` | ⚠️ Mock | 仅mock实现 |
| **FlusherDriver** | `src/hardware/flusher.py` | ⚠️ Mock | 仅mock实现 |

### 1.5 引擎层实现

| 模块 | 文件路径 | 完成度 | 说明 |
|------|----------|--------|------|
| **ExperimentRunner** | `src/engine/runner.py` | ⚠️ 50% | 基础框架，需完善状态机 |

### 1.6 结论：是否可以开始写后端？

**✅ 可以开始后端开发**

理由：
1. 前端UI框架已经完整，所有主要对话框已实现
2. 数据模型定义清晰完整
3. 前端已定义了与后端的接口契约（见各Dialog的后端接口注释）
4. 服务层框架已搭建完成

后端开发优先级：
1. **P0 (立即)**: 完善RS485Driver真实硬件通信
2. **P0 (立即)**: 实现完整的ExperimentEngine状态机
3. **P1 (高优)**: 实现Diluter/Flusher硬件驱动
4. **P1 (高优)**: 实现LibContext依赖注入容器
5. **P2 (中优)**: 实现CHI电化学仪器驱动
6. **P3 (可选)**: 实现Positioner定位器驱动
7. **P3 (可选)**: 实现Kafka/DataExporter服务

---

## 二、后端模块完整清单

### 2.1 目录结构

```
src/echem_sdl/                          # 后端核心目录
├── app.py                              # 应用入口，装配上下文
├── lib_context.py                      # 依赖注入容器
├── core/                               # 核心业务逻辑
│   ├── __init__.py
│   ├── experiment_engine.py            # 实验引擎状态机
│   ├── prog_step.py                    # 程序步骤模型
│   ├── exp_program.py                  # 实验程序与组合参数
│   └── errors.py                       # 异常定义
├── hardware/                           # 硬件驱动层
│   ├── __init__.py
│   ├── rs485_driver.py                 # RS485底层驱动
│   ├── rs485_protocol.py               # RS485协议帧封装
│   ├── diluter.py                      # 配液器驱动
│   ├── flusher.py                      # 冲洗器驱动
│   ├── positioner.py                   # 定位器驱动（可选）
│   ├── chi.py                          # CHI电化学仪器驱动
│   └── pump_manager.py                 # 泵管理器
├── services/                           # 服务层
│   ├── __init__.py
│   ├── logger.py                       # 日志服务
│   ├── settings_service.py             # 配置服务
│   ├── translator.py                   # 翻译服务
│   ├── data_exporter.py                # 数据导出服务
│   └── kafka_client.py                 # Kafka客户端（可选）
├── utils/                              # 工具模块
│   ├── __init__.py
│   ├── constants.py                    # 常量定义
│   └── types.py                        # 类型定义
├── config/                             # 配置文件
│   ├── defaults.json                   # 默认配置
│   └── settings.json                   # 用户配置
└── assets/                             # 资源文件
    └── translations/                   # 翻译文件
```

### 2.2 模块清单与文档索引

| 序号 | 模块名称 | 文件路径 | 说明文档 | 优先级 |
|------|----------|----------|----------|--------|
| 01 | RS485Driver | `hardware/rs485_driver.py` | [01_RS485_DRIVER.md](01_RS485_DRIVER.md) | P0 |
| 02 | RS485Protocol | `hardware/rs485_protocol.py` | [02_RS485_PROTOCOL.md](02_RS485_PROTOCOL.md) | P0 |
| 03 | Diluter | `hardware/diluter.py` | [03_DILUTER.md](03_DILUTER.md) | P1 |
| 04 | Flusher | `hardware/flusher.py` | [04_FLUSHER.md](04_FLUSHER.md) | P1 |
| 05 | PumpManager | `hardware/pump_manager.py` | [05_PUMP_MANAGER.md](05_PUMP_MANAGER.md) | P1 |
| 06 | CHIInstrument | `hardware/chi.py` | [06_CHI_INSTRUMENT.md](06_CHI_INSTRUMENT.md) | P2 |
| 07 | Positioner | `hardware/positioner.py` | [07_POSITIONER.md](07_POSITIONER.md) | P3 |
| 08 | ProgStep | `core/prog_step.py` | [08_PROG_STEP.md](08_PROG_STEP.md) | P0 |
| 09 | ExpProgram | `core/exp_program.py` | [09_EXP_PROGRAM.md](09_EXP_PROGRAM.md) | P0 |
| 10 | ExperimentEngine | `core/experiment_engine.py` | [10_EXPERIMENT_ENGINE.md](10_EXPERIMENT_ENGINE.md) | P0 |
| 11 | LibContext | `lib_context.py` | [11_LIB_CONTEXT.md](11_LIB_CONTEXT.md) | P0 |
| 12 | SettingsService | `services/settings_service.py` | [12_SETTINGS_SERVICE.md](12_SETTINGS_SERVICE.md) | P0 |
| 13 | LoggerService | `services/logger.py` | [13_LOGGER_SERVICE.md](13_LOGGER_SERVICE.md) | P0 |
| 14 | TranslatorService | `services/translator.py` | [14_TRANSLATOR_SERVICE.md](14_TRANSLATOR_SERVICE.md) | P1 |
| 15 | DataExporter | `services/data_exporter.py` | [15_DATA_EXPORTER.md](15_DATA_EXPORTER.md) | P2 |
| 16 | KafkaClient | `services/kafka_client.py` | [16_KAFKA_CLIENT.md](16_KAFKA_CLIENT.md) | P3 |
| 17 | Constants | `utils/constants.py` | [17_CONSTANTS.md](17_CONSTANTS.md) | P0 |
| 18 | Errors | `core/errors.py` | [18_ERRORS.md](18_ERRORS.md) | P0 |

---

## 三、开发顺序与依赖关系

### 3.1 依赖图

```
阶段0 (基础服务) ──────────────────────────────────────────────────
    │
    ├── utils/constants.py          (无依赖)
    ├── core/errors.py              (无依赖)
    ├── services/logger.py          (无依赖)
    ├── services/settings_service.py (无依赖)
    └── services/translator.py      (无依赖)
    
阶段1 (上下文与模型) ─────────────────────────────────────────────
    │
    ├── core/prog_step.py           (依赖: constants)
    ├── core/exp_program.py         (依赖: prog_step)
    └── lib_context.py              (依赖: 服务层)
    
阶段2 (硬件驱动) ────────────────────────────────────────────────
    │
    ├── hardware/rs485_protocol.py  (依赖: constants)
    ├── hardware/rs485_driver.py    (依赖: rs485_protocol, logger)
    ├── hardware/diluter.py         (依赖: rs485_driver, lib_context)
    ├── hardware/flusher.py         (依赖: rs485_driver, lib_context)
    ├── hardware/pump_manager.py    (依赖: diluter, flusher, rs485_driver)
    ├── hardware/chi.py             (依赖: lib_context)
    └── hardware/positioner.py      (依赖: lib_context) [可选]
    
阶段3 (核心引擎) ────────────────────────────────────────────────
    │
    └── core/experiment_engine.py   (依赖: prog_step, exp_program, hardware/*, lib_context)
    
阶段4 (数据服务) ────────────────────────────────────────────────
    │
    ├── services/data_exporter.py   (依赖: lib_context)
    └── services/kafka_client.py    (依赖: lib_context) [可选]
    
阶段5 (应用入口) ────────────────────────────────────────────────
    │
    └── app.py                      (依赖: 全部)
```

### 3.2 推荐开发顺序

```
Week 1: 阶段0 + 阶段1
  - constants.py, errors.py
  - logger.py, settings_service.py, translator.py
  - prog_step.py, exp_program.py
  - lib_context.py

Week 2: 阶段2 (RS485核心)
  - rs485_protocol.py
  - rs485_driver.py
  - diluter.py
  - pump_manager.py

Week 3: 阶段2 (其他硬件) + 阶段3
  - flusher.py
  - chi.py (mock + real)
  - experiment_engine.py

Week 4: 阶段4 + 阶段5 + 集成测试
  - data_exporter.py
  - app.py 装配
  - 端到端测试
```

---

## 四、技术规范

### 4.1 Python版本与依赖

```
Python >= 3.10
PySide6 >= 6.5.0
pyserial >= 3.5
pyqtgraph >= 0.13.0
jsonschema >= 4.17.0
pydantic >= 2.0.0
openpyxl >= 3.1.0 (数据导出)
confluent-kafka >= 2.0.0 (可选)
```

### 4.2 编码规范

- 类型注解: 所有公开方法必须有完整类型注解
- 文档字符串: Google风格docstring
- 命名规范: 
  - 类名: `PascalCase`
  - 方法/变量: `snake_case`
  - 常量: `UPPER_SNAKE_CASE`
  - 私有成员: `_prefix`
- 每个模块需要对应的测试文件 `tests/test_*.py`

### 4.3 线程与异步规范

- UI线程: 仅用于界面更新
- 后台线程: 硬件通信、长时间操作
- 线程通信: Qt信号槽
- 共享数据: 使用 `threading.RLock` 保护
- 异步可选: `asyncio` 与 `qasync` 配合

### 4.4 日志规范

```python
# 日志级别
DEBUG: 调试信息，开发时使用
INFO: 正常操作信息
WARNING: 警告，不影响运行
ERROR: 错误，影响功能
CRITICAL: 严重错误，程序可能崩溃

# 日志格式
[{timestamp}] [{level}] [{module}] {message}
```

---

## 五、参考资源

### 5.1 原C#项目参考

| 模块 | C#文件路径 | 说明 |
|------|-----------|------|
| RS485驱动 | `D:\AI4S\eChemSDL\eChemSDL\MotorRS485.cs` | 电机通信协议 |
| 配液器 | `D:\AI4S\eChemSDL\eChemSDL\Diluter.cs` | 配液逻辑 |
| 冲洗器 | `D:\AI4S\eChemSDL\eChemSDL\Flusher.cs` | 三泵冲洗 |
| 定位器 | `D:\AI4S\eChemSDL\eChemSDL\Positioner.cs` | XYZ平台 |
| CHI仪器 | `D:\AI4S\eChemSDL\eChemSDL\CHInstrument.cs` | 电化学仪器 |
| 全局上下文 | `D:\AI4S\eChemSDL\eChemSDL\LIB.cs` | 静态配置 |
| 实验引擎 | `D:\AI4S\eChemSDL\eChemSDL\Experiment.cs` | 实验状态机 |
| 程序步骤 | `D:\AI4S\eChemSDL\eChemSDL\ProgStep.cs` | 步骤定义 |
| 实验程序 | `D:\AI4S\eChemSDL\eChemSDL\ExpProgram.cs` | 组合实验 |
| 技术枚举 | `D:\AI4S\eChemSDL\eChemSDL\ECTechs.cs` | 电化学技术代码 |

### 5.2 现有Python文档

| 文档 | 路径 |
|------|------|
| 系统架构 | `docs/system_architecture.md` |
| Python架构蓝图 | `docs/python_architecture_blueprint.md` |
| 实现计划 | `docs/implementation_plan.md` |
| 前端架构报告 | `docs/Frontend Architecture Summary Report.md` |
| 模块审计报告 | `docs/module_audit_report.md` |

---

## 六、下一步操作

1. **阅读各模块详细文档**: 按优先级顺序阅读 `01_RS485_DRIVER.md` 到 `18_ERRORS.md`
2. **创建目录结构**: 在 `src/echem_sdl/` 下创建完整目录
3. **按阶段开发**: 遵循依赖图，从阶段0开始逐步实现
4. **编写测试**: 每个模块完成后编写对应测试
5. **集成验证**: 每个阶段完成后进行集成测试
