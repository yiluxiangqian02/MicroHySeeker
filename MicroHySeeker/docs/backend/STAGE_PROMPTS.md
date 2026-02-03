# MicroHySeeker 分阶段开发提示词

> **版本**: v2.0
> **更新日期**: 2026-02-02
> **用途**: 为每个开发阶段提供独立的、可复制粘贴的提示词

---

## 📖 使用说明

每个阶段都有一个独立的提示词，包含：

1. 📚 需要阅读的文档清单
2. 🔍 需要查看的源代码
3. 🎯 前端对接要求
4. ✅ Mock测试 → 硬件测试（两步验证）
5. ✅ 实现检查清单

**使用方法**:

1. 找到当前阶段
2. 复制整个提示词块（```之间的内容）
3. 粘贴给AI助手
4. AI会自动完成该阶段的开发

**⚠️ 重要：Mock优先原则**

- 所有模块必须先通过Mock模式测试
- Mock测试通过后，才能测试真实硬件
- Mock模式可在UI中切换：`wrapper.set_mock_mode(True/False)`

---

## 1️⃣ 阶段1：RS485基础（✅ 已完成）

<details>
<summary>点击展开阶段1提示词（已完成，仅供参考）</summary>

```
你好！我正在开发 MicroHySeeker 项目的阶段1：RS485基础通信。

### 背景信息
- 项目路径: D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
- Conda环境: MicroHySeeker
- 当前阶段: 阶段1 - RS485基础

### 请按以下顺序工作：

#### 1. 阅读文档（30分钟）
请依次阅读：
- docs/backend/MASTER_PLAN.md - 了解整体规划
- docs/backend/01_RS485_DRIVER.md - RS485驱动规范
- docs/backend/02_RS485_PROTOCOL.md - RS485协议规范

#### 2. 参考源项目（30分钟）
查看原C#实现：
- D:\AI4S\eChemSDL\eChemSDL\MotorRS485.cs
重点关注：
- 串口通信逻辑
- 帧格式和校验
- 异步读取机制

#### 3. 实现模块（2小时）
实现以下文件：
- src/echem_sdl/hardware/rs485_driver.py
- src/echem_sdl/hardware/rs485_protocol.py

关键要求：
- 必须支持 mock_mode=True（无需真实串口）
- 实现线程安全的读写
- 正确的帧解析和校验

#### 4. 创建测试（1小时）
创建测试文件：
- test_rs485_connection.py

测试内容：
- 打开/关闭串口（Mock模式）
- 发送/接收帧
- 帧校验
- 设备扫描

#### 5. 验证（30分钟）
运行测试：
```bash
conda activate MicroHySeeker
cd D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
python test_rs485_connection.py
```

预期结果：

- 所有测试通过
- Mock模式下能模拟通信

### 完成标志

- [ ] RS485Driver 实现完成
- [ ] RS485Protocol 实现完成
- [ ] test_rs485_connection.py 通过
- [ ] Mock模式工作正常

请开始工作！

```

</details>

---

## 2️⃣ 阶段2：泵管理（✅ 已完成）

<details>
<summary>点击展开阶段2提示词（已完成，仅供参考）</summary>

```

你好！我正在开发 MicroHySeeker 项目的阶段2：泵管理系统。

### 背景信息

- 项目路径: D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
- Conda环境: MicroHySeeker
- 当前阶段: 阶段2 - 泵管理
- 前置条件: 阶段1已完成（RS485Driver, RS485Protocol）

### 请按以下顺序工作：

#### 1. 阅读文档（30分钟）

请依次阅读：

- docs/backend/MASTER_PLAN.md - 确认整体规划
- docs/backend/05_PUMP_MANAGER.md - 泵管理器规范
- docs/backend/11_LIB_CONTEXT.md - 依赖注入规范

#### 2. 前端需求分析

查看前端代码，了解需要什么接口：

- src/dialogs/manual_control_dialog.py - 手动控制对话框
- src/services/rs485_wrapper.py - 前端适配器（需要完善）
- src/models.py - 数据模型

关键问题：

- 前端如何调用泵控制？
- 需要哪些方法？(start_pump, stop_pump, scan_pumps等)
- 参数格式是什么？

#### 3. 参考源项目

查看原C#实现：

- D:\AI4S\eChemSDL\eChemSDL\MotorRS485.cs
  重点关注：
- 泵地址管理（1-12号泵）
- 速度控制逻辑
- 状态查询机制

#### 4. 实现模块

实现/完善以下文件：

- src/echem_sdl/hardware/pump_manager.py
- src/echem_sdl/lib_context.py（添加RS485DriverAdapter）
- src/services/rs485_wrapper.py（完善前端接口）

关键要求：

- PumpManager 统一管理所有泵（1-12号）
- LibContext 提供依赖注入
- RS485Wrapper 提供前端友好的接口
- 支持Mock模式

#### 5. 创建测试

创建测试文件：

- test_stage2_integration.py

测试内容：

- PumpManager 初始化
- 启动/停止泵（Mock模式）
- 设置速度和方向
- 扫描泵地址
- LibContext 集成

#### 6. 前端验证

运行前端UI测试：

```bash
conda activate MicroHySeeker
cd D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
python run_ui.py
```

验证功能：

- 打开"手动控制"对话框
- Mock模式下启动/停止泵
- 查看日志输出

### 完成标志

- [ ] PumpManager 实现完成
- [ ] LibContext 实现完成
- [ ] RS485Wrapper 前端接口完善
- [ ] test_stage2_integration.py 通过
- [ ] 前端"手动控制"对话框工作正常

请开始工作！

```

</details>

---

## 3️⃣ 阶段3：配液功能（⭐ 当前阶段）

```

你好！我正在开发 MicroHySeeker 项目的阶段3：配液功能。

### 背景信息

- 项目路径: D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
- Conda环境: MicroHySeeker
- 当前阶段: 阶段3 - 配液功能
- 前置条件: 阶段1和2已完成（RS485, PumpManager, LibContext）

### 请按以下顺序工作：

#### 1. 阅读文档

请依次阅读：

- docs/backend/MASTER_PLAN.md 第3-7节 - 确认渐进式开发策略
- docs/backend/03_DILUTER.md - Diluter模块规范
- docs/backend/13_LOGGER_SERVICE.md - 日志服务规范（基础版即可）

重点关注03_DILUTER.md中的：

- ⚠️ 架构变更说明（统一泵管理）
- 前端对接要求（第X节 - 待添加）
- Mock模式实现

#### 2. 前端需求分析  **这是最重要的一步！**

查看前端代码，确认接口需求：

**2.1 数据模型**
文件: src/models.py

```python
@dataclass
class DilutionChannel:
    pump_address: int       # ← Diluter需要接收
    solution_name: str      # ← Diluter需要接收
    stock_concentration: float  # ← Diluter需要接收
    target_concentration: float  # ← 用于计算体积
    ...
```

**2.2 配置对话框**
文件: src/dialogs/config_dialog.py
查看：

- 如何构建 DilutionChannel 对象？
- 点击"应用"按钮后调用什么？
- 需要什么回调函数？

**2.3 RS485Wrapper**
文件: src/services/rs485_wrapper.py
需要添加的方法：

- `configure_dilution_channels(channels: List[DilutionChannel])` - 配置通道
- `start_dilution(channel_id: int, volume_ul: float)` - 开始配液
- `get_dilution_progress(channel_id: int)` - 查询进度

**问题清单**（必须回答）：

- [ ] 前端传递什么数据结构给后端？
- [ ] 后端需要返回什么数据？
- [ ] 配液过程如何通知前端进度？
- [ ] 错误如何传递给前端？

#### 3. 参考源项目（45分钟）

查看原C#实现：

- D:\AI4S\eChemSDL\eChemSDL\Diluter.cs

重点关注：

- InfuseVolume() 方法的实现逻辑
- 体积到分度的转换公式
- 状态机设计（IDLE → INFUSING → COMPLETED）
- 错误处理

**注意差异**：

- C#有单独的DilutionPump类
- Python版本使用PumpManager统一管理
- 需要适配这个架构差异

#### 4. 实现模块

**4.1 实现 Diluter** (2小时)
文件: src/echem_sdl/hardware/diluter.py

必须实现的接口：

```python
class Diluter:
    def __init__(
        self,
        address: int,              # 泵地址
        name: str,                 # 溶液名称
        stock_concentration: float,  # 储备浓度
        pump_manager: PumpManager,   # 泵管理器
        logger: LoggerService,       # 日志服务
        mock_mode: bool = False
    ):
        ...
  
    def infuse_volume(
        self,
        volume_ul: float,          # 体积（微升）
        callback: Optional[Callable] = None
    ) -> bool:
        """开始注液"""
        ...
  
    def get_progress(self) -> float:
        """获取进度（0-100%）"""
        ...
  
    def stop(self) -> bool:
        """停止注液"""
        ...
  
    @property
    def state(self) -> DiluterState:
        """获取当前状态"""
        ...
```

关键实现点：

- 通过 PumpManager 获取泵实例：`self.pump = pump_manager.get_pump(address)`
- 体积转换：`divisions = volume_ul / self.ul_per_division`
- 进度跟踪：监听泵的位置反馈
- Mock模式：模拟注液过程

**4.2 实现 LoggerService**
文件: src/echem_sdl/services/logger_service.py

基础版即可（参考13_LOGGER_SERVICE.md）：

```python
class LoggerService:
    def info(self, message: str):
        print(f"[INFO] {message}")
  
    def error(self, message: str):
        print(f"[ERROR] {message}")
  
    def warning(self, message: str):
        print(f"[WARNING] {message}")
```

**4.3 完善 RS485Wrapper**
文件: src/services/rs485_wrapper.py

添加配液相关方法：

```python
class RS485Wrapper:
    def __init__(self):
        self.diluters: Dict[int, Diluter] = {}
        ...
  
    def configure_dilution_channels(self, channels: List[DilutionChannel]):
        """配置配液通道"""
        for ch in channels:
            diluter = Diluter(
                address=ch.pump_address,
                name=ch.solution_name,
                stock_concentration=ch.stock_concentration,
                pump_manager=self.ctx.pump_manager,
                logger=self.ctx.logger
            )
            self.diluters[ch.pump_address] = diluter
  
    def start_dilution(self, channel_id: int, volume_ul: float) -> bool:
        """开始配液"""
        diluter = self.diluters.get(channel_id)
        if diluter:
            return diluter.infuse_volume(volume_ul)
        return False
```

#### 5. 创建测试

**5.1 单元测试**
文件: tests/test_diluter.py

```python
def test_diluter_basic():
    """测试Diluter基本功能"""
    ...

def test_volume_conversion():
    """测试体积转换"""
    ...

def test_mock_mode():
    """测试Mock模式"""
    ...
```

**5.2 集成测试**
文件: test_stage3_integration.py

```python
def test_diluter_with_pump_manager():
    """测试Diluter与PumpManager集成"""
    # 1. 初始化LibContext（Mock模式）
    ctx = LibContext(mock_mode=True)
  
    # 2. 创建Diluter
    diluter = Diluter(
        address=1,
        name="H2SO4",
        stock_concentration=1.0,
        pump_manager=ctx.pump_manager,
        logger=ctx.logger,
        mock_mode=True
    )
  
    # 3. 测试配液
    assert diluter.infuse_volume(100) == True
    time.sleep(2)  # 等待模拟完成
  
    # 4. 验证状态
    assert diluter.state == DiluterState.COMPLETED

def test_rs485_wrapper_dilution():
    """测试RS485Wrapper配液接口"""
    wrapper = RS485Wrapper()
    wrapper.set_mock_mode(True)
  
    # 配置通道
    channels = [
        DilutionChannel(
            pump_address=1,
            solution_name="H2SO4",
            stock_concentration=1.0,
            target_concentration=0.1
        )
    ]
    wrapper.configure_dilution_channels(channels)
  
    # 开始配液
    assert wrapper.start_dilution(1, 100) == True
```

#### 6. 验证

⚠️ **重要：必须先Mock后硬件**

**第一步：Mock模式测试**

**6.1 运行UI（Mock模式）**

```bash
conda activate MicroHySeeker
cd D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
python run_ui.py
```

**6.2 测试流程**

1. 点击"配置溶液"按钮
2. **确认处于Mock模式**（UI上应有指示）
3. 配置一个通道：
   - 泵地址: 1
   - 溶液名称: H2SO4
   - 储备浓度: 1.0 M
   - 目标浓度: 0.1 M
   - 标定因子: 0.1 µL/div
4. 点击"应用"按钮
5. 点击"开始配液"按钮
6. 观察：
   - 控制台是否有日志输出？
   - UI是否显示进度？
   - 是否有错误？

**6.3 Mock验证预期结果**

- ✅ 后端正确接收配置
- ✅ Mock模式下打印配液日志
- ✅ UI显示进度（如果实现了）
- ✅ 配液完成后停止
- ✅ 无异常抛出

**第二步：真实硬件测试** (30分钟)

⚠️ **前提：Mock测试必顾全部通过**

**6.4 切换到硬件模式**

1. 连接真实的RS485设备
2. 在UI中切换到硬件模式（取消勾选Mock）
3. 选择正确的COM口（如COM3）
4. 点击"连接"

**6.5 硬件测试流程**

1. 重复上述Mock测试流程
2. 观察真实泵是否运转
3. 检查注液量是否准确

**6.6 硬件验证预期结果**

- ✅ 真实泵启动并运转
- ✅ 注液量符合预期
- ✅ UI显示真实进度
- ✅ 配液完成后泵停止
- ✅ 无通信错误

#### 7. 问题排查

如果遇到问题：

**问题1: 导入错误**

```bash
# 检查模块是否存在
python -c "from src.echem_sdl.hardware.diluter import Diluter; print('OK')"
```

**问题2: PumpManager未找到泵**

- 检查是否调用了 `pump_manager.add_pump(address)`
- 确认 LibContext 初始化正确

**问题3: Mock模式不工作**

- 确认所有组件都设置了 `mock_mode=True`
- 检查 RS485Driver 是否在Mock模式

**问题4: UI无响应**

- 检查是否有异常抛出（查看控制台）
- 确认 RS485Wrapper 方法名正确
- 使用调试打印追踪调用流程

### 完成标志

- [ ] Diluter 类实现完成
- [ ] LoggerService 基础版完成
- [ ] RS485Wrapper 添加配液接口
- [ ] test_stage3_integration.py 所有测试通过
- [ ] **Mock测试**: 前端"配置溶液"功能工作正常
- [ ] **Mock测试**: 能模拟完整配液流程
- [ ] **硬件测试**: 真实泵能正常启动和注液
- [ ] **硬件测试**: 注液量准确
- [ ] 代码符合类型注解规范
- [ ] 添加了充分的文档字符串

### 预计时间

总计：约 6-8 小时

- 文档阅读：1.5小时
- 前端分析：1小时
- C#参考：0.75小时
- 实现：3小时
- 测试：1.5小时
- 验证：1小时
- 问题修复：预留1小时

请开始工作，遇到问题随时询问！

```

---

## 4️⃣ 阶段4：冲洗功能

```

你好！我正在开发 MicroHySeeker 项目的阶段4：冲洗功能。

### 背景信息

- 项目路径: D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
- Conda环境: MicroHySeeker
- 当前阶段: 阶段4 - 冲洗功能
- 前置条件: 阶段1-3已完成

### 请按以下顺序工作：

#### 1. 阅读文档（30分钟）

请依次阅读：

- docs/backend/MASTER_PLAN.md - 确认架构
- docs/backend/04_FLUSHER.md - Flusher模块规范

#### 2. 前端需求分析（45分钟）

查看前端代码：

**2.1 数据模型**
文件: src/models.py

```python
@dataclass
class FlushChannel:
    pump_address: int  # 冲洗泵地址
    duration_s: float  # 冲洗时长（秒）
    ...
```

**2.2 冲洗对话框**
文件: src/dialogs/flusher_dialog.py
查看：

- 如何配置冲洗参数？
- 需要什么接口？

**2.3 RS485Wrapper**
需要添加：

- `configure_flush_channels(channels)`
- `start_flush(channel_id, duration)`
- `stop_flush(channel_id)`

#### 3. 参考源项目（30分钟）

查看原C#实现：

- D:\AI4S\eChemSDL\eChemSDL\Flusher.cs

重点：

- 冲洗逻辑（启动→计时→停止）
- 与Diluter的异同

#### 4. 实现模块（2小时）

**4.1 实现 Flusher**
文件: src/echem_sdl/hardware/flusher.py

关键接口：

```python
class Flusher:
    def __init__(
        self,
        address: int,
        pump_manager: PumpManager,
        logger: LoggerService,
        mock_mode: bool = False
    ):
        ...
  
    def start_flush(self, duration_s: float) -> bool:
        """开始冲洗"""
        ...
  
    def stop_flush(self) -> bool:
        """停止冲洗"""
        ...
```

**4.2 完善 RS485Wrapper**
添加冲洗相关方法

#### 5. 创建测试（1小时）

文件: test_stage4_integration.py

测试：

- Flusher基本功能
- 与PumpManager集成
- RS485Wrapper冲洗接口

#### 6. 验证（1小时）

⚠️ **重要：必须先Mock后硬件**

**第一步：Mock模式测试** (30分钟)

1. 运行UI（Mock模式）
2. 点击"冲洗"按钮
3. 配置冲洗参数：
   - 泵地址: 1
   - 冲洗时长: 10秒
   - 流速: 100 RPM
4. 点击"开始冲洗"
5. 验证：
   - ✅ Mock模式下控制台输出冲洗日志
   - ✅ 倒计时显示
   - ✅ 冲洗完成后自动停止

**第二步：硬件测试** (30分钟)

1. 切换到硬件模式
2. 连接真实泵
3. 重复Mock测试流程
4. 验证：
   - ✅ 真实泵运转指定时长
   - ✅ 时间准确
   - ✅ 自动停止

### 完成标志

- [ ] Flusher 实现完成
- [ ] RS485Wrapper 添加冲洗接口
- [ ] test_stage4_integration.py 通过
- [ ] **Mock测试**: 前端"冲洗"功能工作正常
- [ ] **硬件测试**: 真实泵冲洗功能正常

请开始工作！

```

---

## 5️⃣ 阶段5：实验引擎

```

你好！我正在开发 MicroHySeeker 项目的阶段5：实验引擎（最后阶段）。

### 背景信息

- 项目路径: D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
- Conda环境: MicroHySeeker
- 当前阶段: 阶段5 - 实验引擎
- 前置条件: 阶段1-4已完成

### 请按以下顺序工作：

#### 1. 阅读文档（1.5小时）

请依次阅读：

- docs/backend/MASTER_PLAN.md - 确认整体架构
- docs/backend/08_PROG_STEP.md - 程序步骤规范
- docs/backend/09_EXP_PROGRAM.md - 实验程序规范
- docs/backend/10_EXPERIMENT_ENGINE.md - 实验引擎规范
- docs/backend/06_CHI_INSTRUMENT.md - CHI仪器规范

#### 2. 前端需求分析（1小时）

查看前端代码：

**2.1 数据模型**
文件: src/models.py, src/core/schemas.py
查看：

- ProgStep 结构
- ExpProgram 结构
- 步骤类型（配液、冲洗、电化学测量等）

**2.2 主窗口**
文件: src/ui/main_window.py
查看：

- 如何加载实验程序？
- 如何启动/停止实验？
- 如何显示进度？

**2.3 程序编辑器**
文件: src/dialogs/program_editor_dialog.py
查看：

- 如何构建实验步骤？
- 需要什么接口？

#### 3. 参考源项目（1小时）

查看原C#实现：

- D:\AI4S\eChemSDL\eChemSDL\Program.cs
- D:\AI4S\eChemSDL\eChemSDL\ExperimentEngine.cs
- D:\AI4S\eChemSDL\eChemSDL\CHInstrument.cs

重点：

- 实验状态机
- 步骤执行逻辑
- CHI通信协议

#### 4. 实现模块（6小时）

**4.1 实现 ProgStep** (1小时)
文件: src/echem_sdl/core/prog_step.py

**4.2 实现 ExpProgram** (1小时)
文件: src/echem_sdl/core/exp_program.py

**4.3 实现 CHInstrument** (2小时)
文件: src/echem_sdl/hardware/chi_instrument.py
注意：Mock模式实现

**4.4 实现 ExperimentEngine** (2小时)
文件: src/echem_sdl/engine/experiment_engine.py

关键接口：

```python
class ExperimentEngine:
    def load_program(self, program: ExpProgram):
        ...
  
    def start(self):
        """开始实验"""
        ...
  
    def pause(self):
        ...
  
    def stop(self):
        ...
  
    def get_status(self) -> EngineStatus:
        ...
```

#### 5. 实现辅助服务（2小时）

**5.1 TranslatorService**
文件: src/echem_sdl/services/translator_service.py
（参考 14_TRANSLATOR_SERVICE.md）

**5.2 DataExporter**
文件: src/echem_sdl/services/data_exporter.py
（参考 15_DATA_EXPORTER.md）

#### 6. 创建测试（2小时）

文件: test_stage5_integration.py

测试：

- 单步执行
- 完整程序执行
- 暂停/停止
- CHI Mock模式
- 数据导出

#### 7. 验证（2小时）

⚠️ **重要：必须先Mock后硬件**

**第一步：Mock模式完整测试** (1.5小时)

**完整流程测试**：

1. 运行 UI（Mock模式）
2. 创建新程序（程序编辑器）
3. 添加步骤：
   - 配液步骤
   - 冲洗步骤
   - 电化学测量步骤
4. 保存程序
5. 运行程序
6. 观察：
   - ✅ 每个步骤是否正确执行？
   - ✅ 进度显示是否正确？
   - ✅ 数据是否正确保存？
   - ✅ CHI Mock模式是否工作？

**第二步：硬件集成测试** (30分钟)

1. 切换到硬件模式
2. 连接所有真实设备：
   - RS485泵
   - CHI工作站（如有）
3. 运行简单程序
4. 验证：
   - ✅ 泵和CHI通信正常
   - ✅ 实验流程正确执行
   - ✅ 数据采集正确

### 完成标志

- [ ] ProgStep 实现完成
- [ ] ExpProgram 实现完成
- [ ] CHInstrument 实现完成（Mock）
- [ ] ExperimentEngine 实现完成
- [ ] TranslatorService 实现完成
- [ ] DataExporter 实现完成
- [ ] test_stage5_integration.py 通过
- [ ] **Mock测试**: 前端能运行完整实验流程
- [ ] **Mock测试**: CHI Mock模式工作正常
- [ ] **硬件测试**: 所有设备通信正常
- [ ] **硬件测试**: 实验流程正确执行

### 预计时间

总计：约 12-15 小时

恭喜你即将完成整个项目！请开始工作！

```

---

## 📌 提示词使用技巧

### 如何高效使用

1. **复制整个阶段提示词** - 包含所有必要信息
2. **不要跳阶段** - 必须按顺序完成
3. **先看前端再写后端** - 避免接口不匹配
4. **Mock模式优先** - 无需真实硬件
5. **边写边测** - 不要等全部写完才测试

### 自定义提示词

如果需要，可以在提示词中添加：
- 特定的实现要求
- 额外的测试用例
- 性能优化要求
- 代码风格偏好

### 问题排查模板

```

当前问题：[描述问题]
所在阶段：阶段X
已完成：[列出已完成的步骤]
测试结果：[粘贴错误信息或测试输出]
相关文件：[列出相关文件路径]

请帮我分析问题并提供解决方案。

```

---

## 📞 需要帮助？

如果提示词不够清晰或需要补充，请：
1. 检查 MASTER_PLAN.md 第9节（重要注意事项）
2. 查看对应的 01-18 模块文档
3. 查看已完成阶段的代码实现

---

**祝开发顺利！** 🚀

记住：**先看前端需求，再写后端实现**
```
