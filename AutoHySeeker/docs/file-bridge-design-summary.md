# AutoHySeeker ↔ MicroHySeeker 文件通信桥接设计方案

**版本**：v1.0  
**日期**：2026-03-06  
**状态**：Copilot 已完成完整设计，待实施

---

## 设计概览

Copilot 已生成完整的文件通信桥接方案，包含：

### 1. 文件协议规范

**共享目录**：`D:\AI4S\bridge\`

```
bridge/
├── cmd/command.json          # AutoHySeeker → MicroHySeeker 命令
├── status/status.json        # MicroHySeeker → AutoHySeeker 状态（1秒更新）
├── results/{run_id}/         # 实验结果目录
│   ├── summary.json
│   └── data/*.csv
└── .heartbeat                # MicroHySeeker 心跳（5秒更新）
```

**命令类型**：`start`, `stop`, `pause`, `resume`

**状态枚举**：`idle`, `loading`, `ready`, `running`, `step_executing`, `paused`, `stopping`, `completed`, `error`

---

### 2. AutoHySeeker 端实现

**文件**：`AutoHySeeker/src/tools/experiment_ctrl.py`（完整重写，~300行）

**核心函数**：
- `start_experiment(payload)` — 写命令文件，返回 run_id
- `stop_experiment(payload)` — 写停止命令
- `get_experiment_status()` — 读状态文件
- `get_experiment_result(run_id)` — 读 summary.json + CSV 列表
- `poll_until_done(run_id, timeout)` — 阻塞轮询直到完成/失败/超时
- `plan_to_exp_program(plan, run_id)` — 数据格式转换

**心跳检测**：
- 启动实验前检查 `.heartbeat` 文件 mtime < 15秒
- 轮询中检测心跳超时 → 返回 `{state:"failed", message:"心跳超时"}`

---

### 3. MicroHySeeker 端实现

**新增文件**：`MicroHySeeker/src/services/file_bridge.py`（~250行）

**类设计**：`FileBridge(QObject)`

**职责**：
- 监听 `command.json` 变化（`QFileSystemWatcher`）
- 解析命令 → 调用 `ExperimentEngine` API
- 每 1 秒写入 `status.json`（`QTimer`）
- 每 5 秒更新 `.heartbeat`（`QTimer`）
- 实验完成后写入 `summary.json`

**集成点**：
- `src/ui/main_window.py` 的 `__init__` 中初始化 `FileBridge`
- `closeEvent` 中调用 `FileBridge.stop()`

---

### 4. 数据格式映射（41项）

**步骤类型映射**：

| AutoHySeeker | MicroHySeeker | 说明 |
|--------------|---------------|------|
| `prep_sol` | `配液` | 溶液配制 |
| `cv/lsv/eis/ca` | `电化学` | 所有电化学技术统一映射 |
| `flush` | `冲洗` | 管路清洗 |
| `transfer` | `移液` | 样品转移 |
| `blank/evacuate` | `空白` | 延时/抽真空 |

**参数映射示例**（配液）：
- `stock_concentration_M` → `high_concentration`
- `total_volume_ml` → `target_volume`
- `pump_speed_ml_min` → `pump_speed`

---

### 5. 错误处理（6类场景）

1. **MicroHySeeker 未启动** — 检查心跳，立即返回 error
2. **命令文件损坏** — JSON 解析失败，记录警告，跳过
3. **状态文件损坏** — 返回 None，下次轮询重试
4. **实验超时** — `poll_until_done` 到期返回 timeout
5. **引擎错误** — 读 `error_message`，返回失败结果
6. **MicroHySeeker 崩溃** — 心跳超时检测，返回失败

**原子写入**：所有写操作先写 `.tmp`，再 `os.replace()` 避免读到半成品

---

### 6. 测试用例（27项）

**单元测试**：
- AutoHySeeker: 12 个（格式转换、心跳检测、状态映射）
- MicroHySeeker: 7 个（命令分发、状态写入、清理逻辑）

**集成测试**：8 个（完整流程、stop/pause/resume、心跳超时、并发写入）

---

## 实施清单

### AutoHySeeker 端

1. ✅ 设计完成
2. ⬜ 重写 `src/tools/experiment_ctrl.py`
3. ⬜ 添加 `configs/bridge.toml` 配置
4. ⬜ 编写单元测试 `tests/test_experiment_ctrl.py`

### MicroHySeeker 端

1. ✅ 设计完成
2. ⬜ 创建 `src/services/file_bridge.py`
3. ⬜ 修改 `src/ui/main_window.py` 集成 FileBridge
4. ⬜ 编写单元测试 `tests/test_file_bridge.py`

### 集成验证

1. ⬜ 初始化 `D:\AI4S\bridge\` 目录
2. ⬜ 启动 MicroHySeeker（心跳开始）
3. ⬜ AutoHySeeker 发送 start 命令
4. ⬜ 验证状态文件实时更新
5. ⬜ 验证实验完成后 summary.json 生成
6. ⬜ 运行 27 个测试用例

---

## 完整代码位置

Copilot 已在终端输出中生成完整代码（session rapid-canyon），包含：
- `experiment_ctrl.py` 完整实现（~300行）
- `file_bridge.py` 完整实现（~250行）
- 所有辅助函数和错误处理逻辑

**下一步**：
1. 老板确认设计方案
2. 我将完整代码写入对应文件
3. 运行测试验证
4. 集成到主分支

---

**文档生成**：Copilot (Claude Sonnet 4.6) + Pi 整理  
**预计实施时间**：2-3 小时（代码已生成，主要是测试验证）
