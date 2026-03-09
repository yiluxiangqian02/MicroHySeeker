# AutoHySeeker ↔ MicroHySeeker 文件通信桥接方案

## 背景

**AutoHySeeker** (AI 后端) 需要控制 **MicroHySeeker** (PySide6 GUI 前端) 执行电化学实验。

**约束**：
- 不使用 HTTP API（避免增加前端复杂度）
- 采用**文件通信**方式（本地共享目录）
- MicroHySeeker 已有完整的实验执行引擎（`ExperimentEngine`）和程序模型（`ExpProgram`）

## MicroHySeeker 现有能力

### 核心组件
- `src/echem_sdl/core/experiment_engine.py` — 实验执行引擎（状态机 + 线程驱动）
- `src/core/exp_program.py` — 实验程序数据模型（`ExpProgram` / `ProgStep`）
- `src/echem_sdl/hardware/` — 硬件驱动层（泵、电化学仪器、RS485）

### 引擎状态
```python
class EngineState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    RUNNING = "running"
    STEP_EXECUTING = "step_executing"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"
```

### 实验程序格式（JSON）
```json
{
  "program_id": "prog_001",
  "program_name": "HER Optimization",
  "ocpt_enabled": true,
  "adt_enabled": false,
  "steps": [
    {
      "step_id": 1,
      "step_type": "配液",
      "step_name": "配制 0.5M H2SO4",
      "solution_type": "H2SO4",
      "high_concentration": 1.0,
      "target_volume": 10.0,
      "volume_unit": "mL",
      "pump_address": 1,
      "pump_speed": 5.0,
      "enabled": true
    },
    {
      "step_id": 2,
      "step_type": "电化学",
      "step_name": "LSV 扫描",
      "potential": -0.5,
      "current_limit": 0.01,
      "duration": 300.0,
      "ocpt_enabled": true,
      "enabled": true
    }
  ]
}
```

### 步骤类型
- `配液` — 溶液配制（泵控制）
- `电化学` — CV/LSV/EIS/CA 测量
- `冲洗` — 管路清洗
- `移液` — 样品转移
- `空白` — 延时等待

## AutoHySeeker 需求

### 当前桩函数
`AutoHySeeker/src/tools/experiment_ctrl.py`:
```python
def start_experiment(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    # 当前返回 stub 消息
    return {"status": "stub", "message": "Hardware execution is not implemented"}

def stop_experiment(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    # 当前返回 stub 消息
    return {"status": "stub", "message": "Hardware execution is not implemented"}
```

### 需要的功能
1. **启动实验** — 传入 `ExperimentPlan`（AutoHySeeker 格式），转换为 MicroHySeeker 的 `ExpProgram` 格式，触发执行
2. **停止实验** — 中断当前运行的实验
3. **查询状态** — 获取实验进度（当前步骤、百分比、状态）
4. **获取结果** — 实验完成后读取数据文件（CSV/JSON）

## 任务目标

设计并实现**文件通信桥接方案**，包括：

### 1. 文件协议设计
- **共享目录结构**（如 `D:/AI4S/bridge/`）
- **命令文件格式**（JSON）
- **状态文件格式**（JSON）
- **数据文件约定**（CSV 路径规则）

### 2. AutoHySeeker 端实现
- 修改 `src/tools/experiment_ctrl.py`，实现：
  - `start_experiment()` — 写命令文件 + 轮询状态
  - `stop_experiment()` — 写停止命令
  - `get_experiment_status()` — 读状态文件
  - `get_experiment_result()` — 读数据文件
- 数据格式转换：`AutoHySeeker.ExperimentPlan` → `MicroHySeeker.ExpProgram`

### 3. MicroHySeeker 端实现
- 新增文件监听模块（`src/services/file_bridge.py`）：
  - 监听命令文件（`watchdog` 或 `QFileSystemWatcher`）
  - 解析命令 → 调用 `ExperimentEngine`
  - 更新状态文件（实时写入引擎状态）
  - 实验完成后写结果文件
- 集成到主窗口（`src/ui/main_window.py` 或 `src/echem_sdl/ui/main_window.py`）

### 4. 错误处理
- 文件锁冲突处理
- 超时检测（命令无响应）
- 异常状态恢复（崩溃后清理）

### 5. 测试验证
- 单元测试（文件读写、格式转换）
- 集成测试（AutoHySeeker 发命令 → MicroHySeeker 执行 → 读结果）

## 技术约束

- **Python 版本**：3.11
- **MicroHySeeker 依赖**：PySide6, 已有 `ExperimentEngine`
- **AutoHySeeker 依赖**：FastAPI, LangGraph, 已有 `experiment_ctrl.py` 桩
- **文件格式**：JSON（命令/状态），CSV（数据）
- **并发安全**：文件锁 + 原子写入（临时文件 + rename）

## 输出要求

生成 `file-bridge-design.md`，包含：
1. 文件协议详细规范（目录结构、文件命名、JSON schema）
2. AutoHySeeker 端代码修改清单（文件路径 + 函数签名）
3. MicroHySeeker 端新增模块设计（类图 + 接口定义）
4. 数据格式映射表（AutoHySeeker ↔ MicroHySeeker）
5. 错误场景处理流程图
6. 测试用例清单

## 参考文件

- `D:/AI4S/MicroHySeeker/MicroHySeeker/MicroHySeeker/src/core/exp_program.py`
- `D:/AI4S/MicroHySeeker/MicroHySeeker/MicroHySeeker/src/echem_sdl/core/experiment_engine.py`
- `D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/src/tools/experiment_ctrl.py`
- `D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/src/common/types.py` (ExperimentPlan / ProgStep)

---

**注意**：方案需要考虑 MicroHySeeker 可能未运行的情况（优雅降级或明确报错）。
