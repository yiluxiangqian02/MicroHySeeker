## 1. 模块定位与职责
- 文件：`src/echem_sdl/utils/constants.py`
- 作用：集中定义全局常量、枚举、默认值（RS485 协议、电化学技术编号、默认语言/路径/端口等），为硬件层与核心层提供统一引用，避免魔法数字和重复定义。

## 2. 文件与结构
- 通信常量（示例）：
  - `RS485_START_REQUEST = 0xFA`
  - `RS485_START_RESPONSE = 0xFB`
  - 命令号：`CMD_SPEED = 0xF6`, `CMD_POSITION = 0xF4`, `CMD_RUN_STATUS = 0xF1`, `CMD_VERSION = 0x40`, `CMD_SETTINGS = 0x47`, `CMD_STATUS = 0x48`
  - 默认参数：`DEFAULT_RS485_BAUD = 38400`, `DEFAULT_RS485_PORT = ""`, `DEFAULT_TIMEOUT = 2.0`
- 电化学技术映射：
  - `ECTechs: dict[int, str]`，如 `{1: "CV", 2: "LSV", 11: "i-t"}`（可按需扩展，保持与 CHI/ECTechs.cs 对应）。
- 枚举（使用 `enum.Enum` 或 `enum.IntEnum`）：
  - `class OperationType(Enum)`: `PREP_SOL = "prep_sol"`, `FLUSH = "flush"`, `ECHEM = "echem"`, `TRANSFER = "transfer"`, `CHANGE = "change"`, `BLANK = "blank"`, `MOVE = "move"`, `WAIT = "wait"`
  - `class StepState(Enum)`: `IDLE = "idle"`, `RUNNING = "running"`, `DONE = "done"`, `FAILED = "failed"`
  - `class Lang(Enum)`: `ZH = "zh"`, `EN = "en"`
  - 可选 `class ErrorCode(Enum)`: `SUCCESS = 0`, `TIMEOUT = 1`, `PORT_ERROR = 2`, `INVALID_FRAME = 3`
- 默认配置常量：
  - `DEFAULT_LOCALE = "zh"`
  - `DEFAULT_DATA_PATH = "data/"`
  - `DEFAULT_CONFIG_DIR = "config/"`
  - `DEFAULT_LOG_DIR = "logs/"`
  - `DEFAULT_EXPORT_DIR = "exports/"`
  - `DEFAULT_HEARTBEAT_MS = 1000`
- 路径与文件名模板：
  - `CONFIG_DIR = Path(DEFAULT_CONFIG_DIR)`
  - `LOG_DIR = Path(DEFAULT_LOG_DIR)`
  - `DATA_DIR = Path(DEFAULT_DATA_PATH)`
  - `EXPORT_DIR = Path(DEFAULT_EXPORT_DIR)`
  - `DEFAULT_SETTINGS_FILE = CONFIG_DIR / "settings.json"`
  - `DEFAULT_DEFAULTS_FILE = CONFIG_DIR / "defaults.json"`

## 3. 依赖说明
- 标准库：`enum`, `pathlib.Path`, `typing`（类型别名）。
- 内部依赖：无，模块应独立可导入。

## 4. 使用策略与线程安全
- 常量与枚举为只读；不应在运行时修改。
- 路径常量可用于构建具体文件路径；调用方负责创建目录（或在模块初始化时可选择性确保目录存在）。
- 线程安全：常量与枚举为不可变对象，可在多线程环境安全使用。

## 5. 错误与日志处理机制
- 模块本身不产生运行时错误；可选在加载时检查/创建路径并打印 warning（或由调用方处理）。
- 不依赖 logger。

## 6. 测试要求
- 常量与枚举可导入且类型正确。
- RS485 常量与协议描述一致；命令号数值匹配。
- 枚举值符合预期（如 `OperationType.FLUSH.value == "flush"`）。
- 路径常量为 `Path` 类型，若需要可创建目录验证可写性。
- `ECTechs` 包含核心技术（CV, LSV, i-t）。

## 7. 文档与注释要求
- 模块 docstring：说明用途、主要常量与枚举。
- 枚举与关键常量行内注释简述用途。
- 类型注解齐全；可在 README/文档中提供主要常量表。

## 8. 验收标准
- 常量/枚举定义完整、命名规范，覆盖协议/默认值/路径。
- 模块可独立加载，无运行错误。
- 能被硬件与核心模块直接导入使用；类型/注释/docstring 完整。
- 测试通过：导入、值校验、映射完整性、路径可用性（如测试目录创建）。 
