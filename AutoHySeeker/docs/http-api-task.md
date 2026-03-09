# MicroHySeeker HTTP API 控制方案设计任务

## 背景

AutoHySeeker（AI 后端）需要**全权控制** MicroHySeeker（PySide6 GUI 前端）。

**需求**：
- AutoHySeeker 可以启动/停止/暂停/恢复实验
- AutoHySeeker 可以查询实验状态和进度
- AutoHySeeker 可以重启/调试 MicroHySeeker
- AutoHySeeker 可以读取实验结果数据
- 监控 Agent 可以执行系统级操作（重启、健康检查）
- 规划优化 Agent 可以启动新实验

## 技术方案

在 MicroHySeeker 中内嵌 **FastAPI** 服务，提供 RESTful API。

### 架构设计

```
MicroHySeeker (PySide6 GUI)
├── src/ui/main_window.py          # Qt 主窗口（主线程）
├── src/echem_sdl/core/experiment_engine.py  # 实验引擎（工作线程）
└── src/api/                        # 新增：FastAPI 服务
    ├── server.py                   # FastAPI app + uvicorn 启动
    ├── routes/
    │   ├── experiment.py           # 实验控制路由
    │   ├── system.py               # 系统控制路由
    │   └── data.py                 # 数据查询路由
    └── bridge.py                   # Qt ↔ FastAPI 桥接（线程安全）
```

### API 端点设计

#### 1. 实验控制

| 方法 | 路径 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/experiment/start` | 启动实验 | `{"program": ExpProgram}` | `{"run_id": "...", "status": "started"}` |
| POST | `/api/experiment/stop` | 停止实验 | `{"run_id": "..."}` | `{"status": "stopped"}` |
| POST | `/api/experiment/pause` | 暂停实验 | `{"run_id": "..."}` | `{"status": "paused"}` |
| POST | `/api/experiment/resume` | 恢复实验 | `{"run_id": "..."}` | `{"status": "resumed"}` |
| GET | `/api/experiment/status` | 查询状态 | — | `{"state": "running", "progress": 45.2, ...}` |

#### 2. 数据查询

| 方法 | 路径 | 功能 | 响应 |
|------|------|------|------|
| GET | `/api/data/runs` | 列出所有实验 | `[{"run_id": "...", "name": "...", "status": "..."}]` |
| GET | `/api/data/runs/{run_id}` | 获取实验详情 | `{"summary": {...}, "data_files": [...]}` |
| GET | `/api/data/runs/{run_id}/files/{filename}` | 下载数据文件 | CSV 文件流 |

#### 3. 系统控制

| 方法 | 路径 | 功能 | 响应 |
|------|------|------|------|
| GET | `/api/system/health` | 健康检查 | `{"status": "ok", "uptime": 3600, ...}` |
| POST | `/api/system/restart` | 重启 MicroHySeeker | `{"status": "restarting"}` |
| GET | `/api/system/logs` | 获取日志 | `{"logs": [...]}` |

### 数据格式转换

AutoHySeeker 的 `ExperimentPlan` 需要转换为 MicroHySeeker 的 `ExpProgram`。

**转换函数**：在 `src/api/bridge.py` 中实现 `plan_to_exp_program()`，映射规则：
- `ExperimentPlan.name` → `ExpProgram.program_name`
- `ExperimentPlan.steps` → `ExpProgram.steps`（字段映射见之前的 41 项映射表）

### 线程安全设计

**问题**：FastAPI 运行在独立线程，Qt GUI 运行在主线程，不能直接跨线程调用。

**解决方案**：使用 Qt 信号/槽机制

```python
# src/api/bridge.py
class APIBridge(QObject):
    # 信号（FastAPI 线程 emit）
    start_experiment_signal = Signal(dict)
    stop_experiment_signal = Signal()
    
    def __init__(self, engine: ExperimentEngine):
        self.engine = engine
        # 连接信号到引擎方法（在 Qt 主线程执行）
        self.start_experiment_signal.connect(self._on_start_experiment)
        self.stop_experiment_signal.connect(self.engine.stop)
    
    @Slot(dict)
    def _on_start_experiment(self, program_dict):
        program = ExpProgram.from_dict(program_dict)
        self.engine.load_program(program)
        self.engine.start()
    
    # FastAPI 路由调用这些方法
    def start_experiment(self, program_dict):
        self.start_experiment_signal.emit(program_dict)
        return {"status": "accepted"}
```

### FastAPI 服务启动

在 `src/ui/main_window.py` 的 `__init__` 中启动：

```python
from ..api.server import start_api_server

self.api_thread = threading.Thread(
    target=start_api_server,
    args=(self._engine, 8100),  # 端口 8100
    daemon=True
)
self.api_thread.start()
```

## AutoHySeeker 端实现

修改 `AutoHySeeker/src/tools/experiment_ctrl.py`：

```python
import httpx

MICROHYSEEKER_API = "http://localhost:8100/api"

def start_experiment(payload: dict) -> dict:
    plan = payload["plan"]
    program = plan_to_exp_program(plan)
    
    response = httpx.post(
        f"{MICROHYSEEKER_API}/experiment/start",
        json={"program": program},
        timeout=10.0
    )
    return response.json()

def get_experiment_status() -> dict:
    response = httpx.get(f"{MICROHYSEEKER_API}/experiment/status")
    return response.json()
```

## 任务输出要求

生成以下文件的完整代码：

1. `MicroHySeeker/src/api/server.py` — FastAPI app + uvicorn 启动
2. `MicroHySeeker/src/api/bridge.py` — Qt ↔ FastAPI 线程安全桥接
3. `MicroHySeeker/src/api/routes/experiment.py` — 实验控制路由
4. `MicroHySeeker/src/api/routes/system.py` — 系统控制路由
5. `MicroHySeeker/src/api/routes/data.py` — 数据查询路由
6. `AutoHySeeker/src/tools/experiment_ctrl.py` — HTTP 客户端实现
7. 集成代码片段（修改 `main_window.py`）

## 技术约束

- **MicroHySeeker**：Python 3.11, PySide6, 已有 ExperimentEngine
- **AutoHySeeker**：Python 3.11, FastAPI, httpx
- **端口**：8100（可配置）
- **线程安全**：必须使用 Qt 信号/槽，不能直接跨线程调用 Qt 对象

## 参考文件

- `D:/AI4S/MicroHySeeker/MicroHySeeker/MicroHySeeker/src/echem_sdl/core/experiment_engine.py`
- `D:/AI4S/MicroHySeeker/MicroHySeeker/MicroHySeeker/src/core/exp_program.py`
- `D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/src/common/types.py`
- 之前的字段映射表（41 项）

---

**注意**：方案需要考虑 MicroHySeeker 未启动的情况（AutoHySeeker 调用 API 失败时的处理）。
