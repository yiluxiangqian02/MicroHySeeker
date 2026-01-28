# MicroHySeeker - 微流体电化学实验控制系统

一个功能强大的 Python/PySide6 应用，用于控制微流体设备和电化学仪器的实验程序管理。

## 功能特性

- **程序编辑器**：支持五类实验操作（配液、电化学、冲洗、移液、空白）
- **组合实验编辑器**：设计和管理组合实验流程
- **配置管理**：RS485 端口、通道设置、冲洗参数、显示选项
- **手动控制**：支持注射泵和 RS485 蠕动泵的实时控制
- **RS485 测试**：低级命令发送/接收和设备扫描
- **电化学数据采集**：实时曲线显示和数据表记录
- **JSON 导入/导出**：程序数据格式严格校验，支持版本控制
- **OCPT 支持**：开路电位测量的启用/禁用和持久化
- **多语言支持**：中文和英文用户界面

## 项目结构

```
MicroHySeeker/
├── src/
│   ├── core/              # 核心数据模型
│   │   ├── exp_program.py # 实验程序和步骤
│   │   └── schemas.py     # JSON Schema 定义
│   ├── services/          # 应用服务层
│   │   ├── settings_service.py      # 配置管理
│   │   ├── logger_service.py        # 日志服务
│   │   └── translator_service.py    # 多语言翻译
│   ├── hardware/          # 硬件驱动层（mock + 真实）
│   │   ├── pumps.py           # 注射泵和蠕动泵驱动
│   │   ├── rs485_driver.py    # RS485 通讯驱动
│   │   ├── flusher.py         # 冲洗设备驱动
│   │   └── chi.py             # CHI 电化学仪器驱动
│   └── ui/                # 用户界面
│       ├── main_window.py
│       └── dialogs/
│           ├── program_editor.py
│           ├── combo_editor.py
│           ├── config_dialog.py
│           ├── manual_dialog.py    # 注射泵 + RS485 蠕动泵
│           ├── rs485_test.py
│           ├── echem_view.py
│           └── about_dialog.py
├── examples/              # 示例程序和配置
│   ├── programs/
│   └── configs/
├── tests/                 # 单元和集成测试
├── run_ui.py             # 应用启动器
├── requirements.txt      # Python 依赖
└── README.md
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
cd F:\BaiduSyncdisk\micro1229\MicroHySeeker
python run_ui.py
```

## 核心功能详解

### 1. 程序编辑器 (ProgramEditorDialog)

支持五类操作类型的完整编辑：
- **配液**：溶液种类、浓度、体积、泵地址、转速
- **电化学**：电位、电流限制、时间、OCPT 开关
- **冲洗**：泵选择、体积、循环数、方向
- **移液**：源位置、目标位置、体积、速度
- **空白**：延时时间

功能：
- 添加/删除/上移/下移步骤
- JSON 导入/导出（严格 schema 校验）
- OCPT 全局开关（持久化到 Settings）
- 单步运行和完整程序运行

### 2. 手动控制面板 (ManualDialog)

#### 注射泵控制
- 泵选择（可扩展支持多个泵）
- 转速设置 (mL/min)
- 体积/方向设置
- 启动、停止、步进、复位操作
- 实时位置显示

#### RS485 蠕动泵控制
- 端口/地址选择（自动扫描）
- 转速设置 (RPM)
- 方向选择（正向/反向）
- 体积和周期设置
- 脉冲模式支持
- 实时命令日志

#### 紧急停止
- 红色按钮，停止所有设备

### 3. 配置对话框 (ConfigDialog)

- **General**: 语言、RS485 端口、波特率、数据路径、错误停止
- **Channel**: 通道名称、浓度、泵转速、设备地址、颜色映射
- **Flush**: 冲洗泵配置（角色、RPM、方向、周期）
- **Display**: 溶液颜色映射

端口选择变化时自动刷新设备地址列表。

### 4. RS485 测试工具

- 低级命令发送/接收（十六进制）
- 设备扫描和地址列表
- 数据格式转换（十六进制/文本）

### 5. 电化学数据视图

- 实时曲线显示占位符（使用 pyqtgraph）
- 数据表显示（时间、电位、电流、状态）
- 测量启动/停止控制
- 数据导出功能

## 技术架构

### 设计模式

- **服务注入**：所有对话框通过构造函数接收 services 和 hardware 对象
- **信号/槽**：Qt 信号用于跨线程通讯
- **模型-视图分离**：数据模型与 UI 分离（`core/` 与 `ui/`）
- **驱动抽象**：通过接口定义泵操作，支持 mock 和真实实现切换

### 数据序列化

使用 JSON 格式存储实验程序：

```json
{
  "program_id": "prog_001",
  "program_name": "Example Program",
  "ocpt_enabled": true,
  "steps": [
    {
      "step_id": 1,
      "step_type": "配液",
      "step_name": "初始配液",
      "solution_type": "溶液A",
      "high_concentration": 1.0,
      "target_volume": 10.0,
      "volume_unit": "mL",
      "pump_address": 1,
      "pump_speed": 10.0,
      "enabled": true
    }
  ]
}
```

使用 `jsonschema` 进行严格验证，确保数据完整性。

## 与硬件集成

### Mock 驱动（开发模式）

所有硬件驱动在 `use_mock=True` 模式下模拟响应，无需真实设备即可开发和测试：

```python
rs485 = RS485Driver(port="COM1", use_mock=True)
pump_mgr = PumpManager()
pump = pump_mgr.add_syringe_pump(1)
pump.start()
```

### 接入真实硬件

1. **RS485 设备**: 修改 `hardware/rs485_driver.py` 的 `use_mock=False`
2. **注射泵**: 实现厂商 SDK 的 `SyringePumpDriver` 子类
3. **蠕动泵**: 使用 `485test/通讯` 中的协议实现
4. **CHI 仪器**: 对接厂商 DLL 或网络接口

### 从 C# 项目迁移

如需与原 eChemSDL 项目互操作：

1. 导出现有程序为 JSON
2. 使用相同的 JSON 格式定义（schema 兼容）
3. 通过 RS485 或网络接口进行硬件通讯

## 开发指南

### 添加新的操作类型

编辑 `src/ui/dialogs/program_editor.py`:

```python
OPERATION_TYPES = {
    "新类型": {"icon": "📌", "color": "#AABBCC"}
}

def _create_custom_params(self, step):
    # 添加自定义参数控件
    pass
```

### 扩展硬件支持

在 `src/hardware/` 下创建新驱动模块，实现 `PumpInterface` 接口：

```python
class CustomPumpDriver(PumpInterface):
    def start(self): pass
    def stop(self): pass
    def set_speed(self, speed): pass
    def move_volume(self, volume): pass
    def get_status(self): pass
```

### 自定义翻译

编辑 `src/services/translator_service.py` 的 `TRANSLATIONS` 字典。

## 测试

基础 smoke 测试已在 `tests/` 目录中准备：

```bash
python -m pytest tests/ -v
```

## 许可证

MIT License - 详见 LICENSE 文件

## 联系方式

AI4S Team  
Email: support@ai4s.example.com

---

**更新日期**: 2026年1月28日  
**版本**: 1.0.0
