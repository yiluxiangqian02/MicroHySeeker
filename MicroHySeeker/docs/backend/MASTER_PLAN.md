# MicroHySeeker 后端开发总规划

> **版本**: v4.0  
> **更新日期**: 2026-02-02  
> **适用对象**: AI协作开发者  
> **文档定位**: 唯一的总领规划文档，包含完整开发策略和指导

---

## 📋 目录

1. [项目概述](#1-项目概述)
2. [架构概览](#2-架构概览)
3. [渐进式开发策略](#3-渐进式开发策略)
4. [模块列表与阶段分配](#4-模块列表与阶段分配)
5. [当前开发状态](#5-当前开发状态)
6. [开发工作流程](#6-开发工作流程)
7. [前后端对接原则](#7-前后端对接原则)
8. [测试验证策略](#8-测试验证策略)
9. [重要注意事项](#9-重要注意事项)

---

## 1. 项目概述

### 1.1 项目简介

**MicroHySeeker** 是一个电化学自动化实验控制系统，用于：
- 控制 12 个配液泵（通过 RS485）
- 控制 2 个冲洗泵
- 控制 CH Instruments 电化学工作站（通过 TCP/IP）
- 自动化执行复杂的多步实验流程
- 实时数据采集和可视化

### 1.2 技术栈

- **后端**: Python 3.12
- **前端**: PySide6 (Qt6)
- **通信协议**: RS485 (串口), TCP/IP
- **数据序列化**: JSON, Pydantic
- **测试**: pytest, Mock模拟

### 1.3 核心设计理念

1. **前后端分离**: 前端负责UI和用户交互，后端负责硬件控制和实验逻辑
2. **依赖注入**: 通过 `LibContext` 管理所有服务依赖
3. **Mock模式**: 所有硬件驱动支持Mock，无需物理设备即可开发测试
4. **渐进式开发**: 边写边测，每个阶段都有明确的前端功能验证

---

## 2. 架构概览

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                 前端层 (Frontend)                        │
│  PySide6 UI (dialogs/) + RS485Wrapper (services/)       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              硬件管理层 (Hardware Layer)                 │
│  PumpManager, Diluter, Flusher, CHInstrument           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│             驱动层 (Driver Layer)                        │
│  RS485Driver, RS485Protocol                            │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│            实验引擎层 (Experiment Engine)                │
│  ProgStep, ExpProgram, ExperimentEngine                │
└─────────────────────────────────────────────────────────┘
```

### 2.2 关键架构决策

#### 🔧 统一泵管理

**与原C#不同**，Python 实现中：
- 所有泵（配液泵 1-12 + 冲洗泵）通过 **统一的 PumpManager** 管理
- 不需要单独的 Positioner（三轴平台）
- 泵通过 `pump_address` (1-12) 区分，不再有单独的 `DilutionPump` / `FlushPump` 类

#### 🎯 前端适配器模式

- **RS485Wrapper** (`src/services/rs485_wrapper.py`) 是前端和后端的桥梁
- 前端通过 Wrapper 调用后端，不直接访问硬件层
- Wrapper 负责参数转换和错误处理

#### 🔍 Mock模式

- 所有硬件驱动支持 `mock_mode=True`
- Mock 模式下，模拟真实硬件响应
- 无需物理设备即可完整测试前端功能

---

## 3. 渐进式开发策略

### 3.1 核心原则

**边写边测，快速反馈**

❌ **不要**:
- 一次性写完所有模块
- 写完代码才开始测试
- 忽略前端需求直接写后端

✅ **要做**:
- 每个阶段只实现必要的模块
- 每写完一个模块立即测试
- 先看前端需要什么接口，再写后端
- 每个阶段都有前端功能验证

### 3.2 五个开发阶段

| 阶段 | 目标前端功能 | 需实现模块 | Mock验证 | 硬件验证 |
|------|------------|-----------|---------|---------|
| **阶段1** | RS485连接测试 | RS485Driver, RS485Protocol | test_rs485_connection.py | 可选 |
| **阶段2** | 手动控制泵 | PumpManager, LibContext, RS485Wrapper | 手动控制对话框 (Mock) | 手动控制 (硬件) |
| **阶段3** | 配置溶液并运行 | Diluter, LoggerService | 配置对话框 (Mock) | 真实配液 |
| **阶段4** | 冲洗功能 | Flusher | 冲洗对话框 (Mock) | 真实冲洗 |
| **阶段5** | 完整实验流程 | ProgStep, ExpProgram, ExperimentEngine, CHI | 完整流程 (Mock) | 真实实验 |

⚠️ **验证顺序**：每个阶段都必须先通过Mock验证，再进行硬件验证

### 3.3 每个阶段的标准流程

```
1. 阅读本文档 (MASTER_PLAN.md)
   ↓
2. 阅读 STAGE_PROMPTS.md 中对应阶段的提示词
   ↓
3. 阅读对应的 01-18 模块文档
   ↓
4. 查看源C#项目（如果需要）
   ↓
5. 查看前端代码，确认接口需求
   ↓
6. 实现后端模块（支持Mock模式）
   ↓
7. 编写集成测试
   ↓
8. Mock模式前端验证 ⭐ 必须先完成
   ↓
9. 修复问题，重复6-8直到Mock测试全部通过
   ↓
10. 硬件模式前端验证 ⭐ Mock通过后才做
   ↓
11. 修复硬件相关问题
   ↓
12. 进入下一阶段
```

**关键点**:
- Mock模式可以快速迭代，无需等待硬件
- 所有逻辑在Mock模式下验证正确后，硬件测试通常只需确认通信
- 如果硬件测试失败，优先检查通信参数，而非逻辑

---

## 4. 模块列表与阶段分配

### 4.1 阶段1：RS485基础（✅ 已完成）

| 编号 | 模块名 | 文件路径 | 文档 | 状态 |
|------|--------|---------|------|------|
| 01 | RS485Driver | `src/echem_sdl/hardware/rs485_driver.py` | [01_RS485_DRIVER.md](01_RS485_DRIVER.md) | ✅ |
| 02 | RS485Protocol | `src/echem_sdl/hardware/rs485_protocol.py` | [02_RS485_PROTOCOL.md](02_RS485_PROTOCOL.md) | ✅ |

**测试**: `test_rs485_connection.py` ✅ 通过  
**前端验证**: 无（底层驱动）

### 4.2 阶段2：泵管理（✅ 已完成）

| 编号 | 模块名 | 文件路径 | 文档 | 状态 |
|------|--------|---------|------|------|
| 05 | PumpManager | `src/echem_sdl/hardware/pump_manager.py` | [05_PUMP_MANAGER.md](05_PUMP_MANAGER.md) | ✅ |
| 11 | LibContext | `src/echem_sdl/lib_context.py` | [11_LIB_CONTEXT.md](11_LIB_CONTEXT.md) | ✅ |
| - | RS485Wrapper | `src/services/rs485_wrapper.py` | - | ✅ |

**测试**: `test_stage2_integration.py` ✅ 通过  
**前端验证**: 手动控制对话框（`src/dialogs/manual_control_dialog.py`）✅ 可用

### 4.3 阶段3：配液功能（⭐ 当前阶段）

| 编号 | 模块名 | 文件路径 | 文档 | 状态 |
|------|--------|---------|------|------|
| 03 | Diluter | `src/echem_sdl/hardware/diluter.py` | [03_DILUTER.md](03_DILUTER.md) | ⏳ 待实现 |
| 13 | LoggerService | `src/echem_sdl/services/logger_service.py` | [13_LOGGER_SERVICE.md](13_LOGGER_SERVICE.md) | ⏳ 待实现 |
| 12 | SettingsService | `src/echem_sdl/services/settings_service.py` | [12_SETTINGS_SERVICE.md](12_SETTINGS_SERVICE.md) | 可选 |

**测试**: `test_stage3_integration.py` - 待创建  
**前端验证**: 配置对话框（`src/dialogs/config_dialog.py`）- "配置溶液"功能

### 4.4 阶段4：冲洗功能

| 编号 | 模块名 | 文件路径 | 文档 | 状态 |
|------|--------|---------|------|------|
| 04 | Flusher | `src/echem_sdl/hardware/flusher.py` | [04_FLUSHER.md](04_FLUSHER.md) | ⏳ 待实现 |

**测试**: `test_stage4_integration.py` - 待创建  
**前端验证**: 冲洗对话框（`src/dialogs/flusher_dialog.py`）

### 4.5 阶段5：实验引擎

| 编号 | 模块名 | 文件路径 | 文档 | 状态 |
|------|--------|---------|------|------|
| 08 | ProgStep | `src/echem_sdl/core/prog_step.py` | [08_PROG_STEP.md](08_PROG_STEP.md) | ⏳ 待实现 |
| 09 | ExpProgram | `src/echem_sdl/core/exp_program.py` | [09_EXP_PROGRAM.md](09_EXP_PROGRAM.md) | ⏳ 待实现 |
| 10 | ExperimentEngine | `src/echem_sdl/engine/experiment_engine.py` | [10_EXPERIMENT_ENGINE.md](10_EXPERIMENT_ENGINE.md) | ⏳ 待实现 |
| 06 | CHInstrument | `src/echem_sdl/hardware/chi_instrument.py` | [06_CHI_INSTRUMENT.md](06_CHI_INSTRUMENT.md) | ⏳ 待实现 |

**测试**: `test_stage5_integration.py` - 待创建  
**前端验证**: 主窗口（`src/ui/main_window.py`）- 完整实验流程

### 4.6 辅助模块（按需实现）

| 编号 | 模块名 | 文件路径 | 文档 | 何时实现 |
|------|--------|---------|------|---------|
| 14 | TranslatorService | `src/echem_sdl/services/translator_service.py` | [14_TRANSLATOR_SERVICE.md](14_TRANSLATOR_SERVICE.md) | 阶段5 |
| 15 | DataExporter | `src/echem_sdl/services/data_exporter.py` | [15_DATA_EXPORTER.md](15_DATA_EXPORTER.md) | 阶段5 |
| 16 | KafkaClient | `src/echem_sdl/services/kafka_client.py` | [16_KAFKA_CLIENT.md](16_KAFKA_CLIENT.md) | 可选 |
| 17 | Constants | `src/echem_sdl/utils/constants.py` | [17_CONSTANTS.md](17_CONSTANTS.md) | 任意阶段 |
| 18 | Errors | `src/echem_sdl/utils/errors.py` | [18_ERRORS.md](18_ERRORS.md) | 任意阶段 |

### 4.7 已废弃模块

| 编号 | 模块名 | 原因 |
|------|--------|------|
| 07 | Positioner | 不需要三轴平台 |

---

## 5. 当前开发状态

### 5.1 已完成

✅ **阶段1 - RS485基础**
- RS485Driver: 573行，支持Mock模式
- RS485Protocol: 帧解析和构建
- 测试: test_rs485_connection.py 通过

✅ **阶段2 - 泵管理**
- PumpManager: 284行，统一管理所有泵
- LibContext: 依赖注入 + RS485DriverAdapter
- RS485Wrapper: 前端适配器
- 测试: test_stage2_integration.py 通过
- 前端: 手动控制对话框工作正常

### 5.2 当前任务

⭐ **阶段3 - 配液功能**

**需要实现**:
1. `src/echem_sdl/hardware/diluter.py`
2. `src/echem_sdl/services/logger_service.py` (基础版)

**前端已有但需对接**:
- `src/dialogs/config_dialog.py` - 配置对话框
- `src/models.py` - 数据模型（DilutionChannel）

**验证方法**:
1. 创建 `test_stage3_integration.py`
2. 运行前端，打开"配置溶液"对话框
3. 配置通道并点击"应用"
4. 验证后端能正确处理

---

## 6. 开发工作流程

### 6.1 开始新阶段前

**必须阅读的文档**（按顺序）:
1. 本文档 (MASTER_PLAN.md) - 整体规划
2. STAGE_PROMPTS.md - 当前阶段的详细提示词
3. 对应的 01-18 模块文档 - 具体实现规范

**必须检查的代码**:
1. **前端代码** - 确认需要什么接口
   - 查看对话框代码（dialogs/）
   - 查看数据模型（models.py）
   - 查看RS485Wrapper调用

2. **源C#项目** - 参考原始实现
   - 路径: `D:\AI4S\eChemSDL\eChemSDL\`
   - 重点看: 类名对应的 `.cs` 文件

### 6.2 实现过程

**标准步骤**:

1. **前端需求分析** (30分钟)
   ```python
   # 示例：查看前端如何调用
   # src/dialogs/config_dialog.py
   
   def apply_config(self):
       for channel in self.channels:
           # 前端需要什么数据？
           diluter = Diluter(address=channel.pump_address, ...)
           # 前端调用什么方法？
           diluter.infuse_volume(volume=100, ...)
   ```

2. **后端实现** (2小时)
   - 严格按照模块文档的接口定义
   - 实现所有前端需要的方法
   - 添加Mock模式支持

3. **单元测试** (30分钟)
   - 测试基本功能
   - 测试Mock模式

4. **集成测试** (1小时)
   - 测试与其他模块的交互
   - 测试LibContext集成

5. **前端验证** (30分钟)
   - 启动UI: `python run_ui.py`
   - 测试对应功能
   - 记录问题

6. **修复迭代** (根据问题)
   - 修复测试或UI中发现的问题
   - 重复测试直到通过

### 6.3 完成阶段后

**检查清单**:
- [ ] 所有模块测试通过
- [ ] 集成测试通过
- [ ] 前端UI功能正常
- [ ] Mock模式工作正常
- [ ] 代码符合规范
- [ ] 更新本文档的进度表

**提交前**:
```bash
# 1. 运行所有测试
python -m pytest tests/

# 2. 检查代码风格
# (可选)

# 3. 验证前端
python run_ui.py
```

---

## 7. 前后端对接原则

### 7.1 关键对接点

#### 🔌 RS485Wrapper 是桥梁

**前端永远不直接调用硬件层**，而是通过 `RS485Wrapper`：

```python
# ❌ 错误：前端直接调用硬件层
from src.echem_sdl.hardware.pump_manager import PumpManager
pump_mgr = PumpManager(...)

# ✅ 正确：通过Wrapper
from src.services.rs485_wrapper import RS485Wrapper
wrapper = RS485Wrapper()
wrapper.start_pump(address=1, speed=100)
```

**RS485Wrapper 提供的方法**（已实现）:
- `open_port(port, baudrate)` - 打开串口
- `close_port()` - 关闭串口
- `start_pump(address, speed, direction)` - 启动泵
- `stop_pump(address)` - 停止泵
- `scan_pumps()` - 扫描泵
- `list_available_ports()` - 列出串口

**阶段3需要添加**:
- `configure_dilution_channels(channels)` - 配置配液通道
- `start_dilution(channel_id, volume)` - 启动配液

### 7.2 前端需求分析方法

#### Step 1: 查看数据模型

```python
# src/models.py

@dataclass
class DilutionChannel:
    pump_address: int       # ← 后端需要这个
    solution_name: str      # ← 后端需要这个
    stock_concentration: float  # ← 后端需要这个
    target_concentration: float  # ← 后端需要这个
    ...
```

**结论**: Diluter 类必须接受这些参数

#### Step 2: 查看对话框代码

```python
# src/dialogs/config_dialog.py

class ConfigDialog(QDialog):
    def __init__(self):
        # 查看UI如何构建数据
        self.channels = []
        
    def apply_config(self):
        # 查看UI如何调用后端
        # 这里会告诉你需要什么接口
        ...
```

#### Step 3: 查看源C#项目

```csharp
// D:\AI4S\eChemSDL\eChemSDL\Diluter.cs

public class Diluter {
    public void InfuseVolume(double volume_ul) {
        // 原始实现逻辑
        ...
    }
}
```

**结论**: Python 版本也需要 `infuse_volume()` 方法

### 7.3 接口设计原则

1. **保持方法名一致**
   - C#: `InfuseVolume` → Python: `infuse_volume`
   - C#: `GetState` → Python: `get_state`

2. **参数类型明确**
   ```python
   def infuse_volume(
       self,
       volume_ul: float,  # 明确单位
       callback: Optional[Callable] = None
   ) -> bool:
       """注入指定体积的溶液
       
       Args:
           volume_ul: 体积（微升）
           callback: 完成回调
           
       Returns:
           是否成功启动
       """
   ```

3. **支持Mock模式**
   ```python
   if self.mock_mode:
       # 模拟真实响应
       self.logger.info(f"[MOCK] 注液 {volume_ul} µL")
       return True
   ```

---

## 8. 测试验证策略

### 8.1 三层测试 + Mock/硬件两步验证

```
单元测试 (Unit Tests)
    ↓
集成测试 (Integration Tests)
    ↓
Mock模式验证 (Frontend Mock Test) ⭐ 先做
    ↓
硬件模式验证 (Hardware Test) ⭐ 后做
```

**⚠️ 关键原则：Mock优先，硬件在后**

所有模块必须遵循以下验证顺序：
1. **Mock模式完全通过** - 无需真实硬件，快速迭代
2. **硬件模式验证** - 连接真实设备，确保实际工作

**Mock/硬件模式切换**:
- UI中可切换：勾选/取消勾选"Mock模式"
- 代码中：`wrapper.set_mock_mode(True/False)`
- 默认：Mock模式启用

### 8.2 单元测试示例

```python
# test_diluter.py

def test_diluter_basic():
    """测试 Diluter 基本功能"""
    diluter = Diluter(
        address=1,
        name="H2SO4",
        stock_concentration=1.0,
        mock_mode=True
    )
    
    # 测试注液
    assert diluter.infuse_volume(100) == True
    assert diluter.state == DiluterState.INFUSING
```

### 8.3 集成测试示例

```python
# test_stage3_integration.py

def test_dilution_with_pump_manager():
    """测试 Diluter 与 PumpManager 集成"""
    # 1. 初始化依赖
    ctx = LibContext(mock_mode=True)
    
    # 2. 创建 Diluter
    diluter = Diluter(
        address=1,
        pump_manager=ctx.pump_manager,
        logger=ctx.logger
    )
    
    # 3. 测试配液流程
    diluter.infuse_volume(100)
    time.sleep(1)
    
    # 4. 验证状态
    assert diluter.state == DiluterState.COMPLETED
```

### 8.4 Mock模式前端验证

**第一步：Mock模式测试** ⭐ 必须先完成

**步骤**:
1. 启动UI: `python run_ui.py`
2. **确认处于Mock模式**（UI上应有指示）
3. 点击"配置溶液"
4. 配置一个通道：
   - 泵地址: 1
   - 溶液名称: H2SO4
   - 储备浓度: 1.0 M
   - 目标浓度: 0.1 M
5. 点击"应用"
6. 点击"开始配液"

**Mock模式预期结果**:
- ✅ 后端正确接收配置
- ✅ 控制台打印Mock日志（如"[MOCK] 泵1启动"）
- ✅ UI显示进度
- ✅ 完成后停止
- ✅ 无异常抛出

### 8.5 硬件模式前端验证

**第二步：硬件模式测试** ⭐ Mock通过后才做

**前提条件**:
- ✅ Mock模式测试全部通过
- ✅ 真实硬件已连接（RS485泵等）

**步骤**:
1. 在UI中**取消勾选Mock模式**
2. 选择正确的COM口（如COM3）
3. 点击"连接"
4. 重复上述Mock测试流程

**硬件模式预期结果**:
- ✅ 真实泵启动并运转
- ✅ 注液量准确
- ✅ UI显示真实进度
- ✅ 完成后泵停止
- ✅ 无通信错误

---

## 9. 重要注意事项

### 9.1 架构相关

⚠️ **不需要 Positioner（三轴平台）**
- 原C#项目有 Positioner
- Python 版本不需要
- 不要实现 07_POSITIONER.md

⚠️ **统一泵管理**
- 所有泵通过 PumpManager 管理
- 没有单独的 DilutionPump / FlushPump 类
- 通过 `pump_address` 区分

⚠️ **前端已实现**
- 不要重新实现前端对话框
- 只需实现后端逻辑
- 通过 RS485Wrapper 对接

### 9.2 开发相关

⚠️ **不要跳阶段**
- 必须按阶段1→2→3→4→5顺序
- 不要一次性写完所有模块

⚠️ **先看前端再写后端**
- 先确认前端需要什么接口
- 再实现后端模块

⚠️ **Mock模式是必须的**
- 所有硬件驱动必须支持Mock
- 用于无硬件开发和测试

### 9.3 代码规范

✅ **类型注解**
```python
def infuse_volume(self, volume_ul: float) -> bool:
    ...
```

✅ **文档字符串**
```python
def infuse_volume(self, volume_ul: float) -> bool:
    """注入指定体积的溶液
    
    Args:
        volume_ul: 体积（微升）
        
    Returns:
        是否成功启动
    """
```

✅ **错误处理**
```python
try:
    result = self.pump.set_speed(speed)
except Exception as e:
    self.logger.error(f"设置速度失败: {e}")
    return False
```

### 9.4 源项目参考

**C# 项目路径**: `D:\AI4S\eChemSDL\eChemSDL\`

**关键文件对应**:
| Python 模块 | C# 文件 |
|------------|---------|
| RS485Driver | MotorRS485.cs |
| PumpManager | MotorRS485.cs (部分) |
| Diluter | Diluter.cs |
| Flusher | Flusher.cs |
| CHInstrument | CHInstrument.cs |
| ExpProgram | Program.cs |
| ExperimentEngine | ExperimentEngine.cs |

**如何参考**:
1. 查看类名和方法名
2. 理解核心逻辑
3. **不要直接翻译** - Python有更好的实现方式
4. 注意架构差异（如统一泵管理）

---

## 10. 下一步行动

### 10.1 如果你是新接手的AI

**立即开始**:
1. ✅ 阅读本文档（你正在做）
2. ⏭️ 阅读 [STAGE_PROMPTS.md](STAGE_PROMPTS.md) 的阶段3提示词
3. ⏭️ 阅读 [03_DILUTER.md](03_DILUTER.md)
4. ⏭️ 查看 `src/dialogs/config_dialog.py`
5. ⏭️ 开始实现 Diluter

### 10.2 当前阶段目标

**阶段3：实现配液功能**

**任务清单**:
- [ ] 实现 `src/echem_sdl/hardware/diluter.py`
- [ ] 实现 `src/echem_sdl/services/logger_service.py`（基础版）
- [ ] 在 RS485Wrapper 中添加配液接口
- [ ] 创建 `test_stage3_integration.py`
- [ ] 运行前端验证"配置溶液"功能

**预计时间**: 4-6小时

**成功标志**:
- test_stage3_integration.py 通过
- 前端"配置溶液"对话框工作正常
- Mock模式下能正确模拟配液流程

---

## 11. 文档索引

### 11.1 规划文档

- **MASTER_PLAN.md** (本文档) - 总规划
- **STAGE_PROMPTS.md** - 分阶段提示词

### 11.2 模块文档 (01-18)

按阶段分类：

**阶段1**: 01, 02  
**阶段2**: 05, 11  
**阶段3**: 03, 13  
**阶段4**: 04  
**阶段5**: 06, 08, 09, 10  
**辅助**: 12, 14, 15, 16, 17, 18  
**废弃**: 07

详细列表见 [第4节](#4-模块列表与阶段分配)

### 11.3 测试文件

- `test_rs485_connection.py` - 阶段1测试
- `test_stage2_integration.py` - 阶段2测试
- `test_stage3_integration.py` - 阶段3测试（待创建）
- `test_stage4_integration.py` - 阶段4测试（待创建）
- `test_stage5_integration.py` - 阶段5测试（待创建）

---

## 📞 遇到问题？

### 常见问题

**Q: 不知道从哪开始？**
A: 阅读 STAGE_PROMPTS.md 的当前阶段提示词

**Q: 前端需要什么接口？**
A: 查看 `src/dialogs/` 和 `src/services/rs485_wrapper.py`

**Q: 原C#项目如何实现的？**
A: 参考 `D:\AI4S\eChemSDL\eChemSDL\` 对应的 `.cs` 文件

**Q: 测试不通过怎么办？**
A: 
1. 检查Mock模式是否启用
2. 查看日志输出
3. 单步调试测试代码

**Q: UI运行报错？**
A: 
1. 确认在正确目录: `D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker`
2. 激活conda环境: `conda activate MicroHySeeker`
3. 检查依赖: `pip list`

---

**祝开发顺利！** 🚀

记住：**边写边测，快速反馈**
