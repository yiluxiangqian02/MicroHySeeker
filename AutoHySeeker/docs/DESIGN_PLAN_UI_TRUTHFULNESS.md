# AutoHySeeker 前端可靠性 & 一键启动 设计方案

> 创建日期: 2026-03-26  
> 优先级: 高  
> 范围: 前端 UI 真实性修复 + 开发体验优化

---

## 一、问题总览

### 1.1 用户反馈

1. **前端启动不便** — 不知道如何启动前端服务，缺少一键启动脚本
2. **UI 不真实** — Dashboard 在没有运行实验时也显示"正在运行"状态，没有明确的开关控件；界面"不靠谱"

### 1.2 根因分析（代码审计结论）

经过对 `frontend/src/hooks/useDashboardPolling.ts`、`Dashboard.tsx`、`OptimizationStatusCard.tsx`、后端 `routes/optimization.py` 的完整审计，发现以下 **6 个核心问题**：

| # | 问题 | 严重度 | 所在文件 |
|---|------|--------|---------|
| P1 | `useDashboardPolling` 生成**伪造数据**：`generateEchemPoint()` 用 Math.random 产生假电压/电流；`generateLogEntry()` 生成假日志；`deriveAgentStates()` 用随机数伪造 Agent 任务 | **严重** | `hooks/useDashboardPolling.ts` |
| P2 | `isRunning` 判定逻辑错误：`isHealthy && !!latestName` — 只要曾有过实验名称就判定为运行中，而非检查实际运行状态 | **严重** | `hooks/useDashboardPolling.ts` L218 |
| P3 | `OptimizationStatusCard` 的 Start/Stop 按钮**未绑定事件处理器**，点击无反应 | **高** | `components/dashboard/OptimizationStatusCard.tsx` L59-67 |
| P4 | Dashboard 存在**双数据源冲突**：`useDashboardPolling`（假数据）和 `useOptimizationStore`（真数据）同时驱动 UI，语义矛盾 | **高** | `pages/Dashboard.tsx` |
| P5 | Vite Proxy 目标端口 `8101` 与后端实际端口 `8200`（config.py 默认值）不匹配，也与 `.env.example` 中 `8100` 不匹配 | **中** | `frontend/vite.config.ts` L14 |
| P6 | 缺少 MicroHySeeker（硬件控制器）在线/离线状态的**明确提示**。当硬件离线时，Executor 返回 stub 响应，loop 会走完但无实际实验 | **中** | 后端 `routes/control.py` |

---

## 二、端口统一方案（P5 前置修复）

**当前混乱状态**：

| 位置 | 端口 |
|------|------|
| `src/common/config.py` 默认值 | 8200 |
| `.env.example` | 8100 |
| `vite.config.ts` proxy | 8101 |
| MicroHySeeker 桌面端 | 8100 |

**决策**：
- AutoHySeeker API 后端统一用 **8200**（避免与 MicroHySeeker 桌面端 8100 冲突）
- `vite.config.ts` proxy 目标改为 `http://127.0.0.1:8200`
- `.env.example` 中 `API_PORT` 改为 `8200`
- 如果用户有 `.env` 文件自定义了端口，以 `.env` 为准

---

## 三、任务拆分

### Task D-01: 一键启动脚本
**目标**: 创建 `dev.bat`（Windows）一键启动后端 + 前端  
**文件变更**:
- 新建 `AutoHySeeker/dev.bat`
- 修改 `AutoHySeeker/frontend/vite.config.ts`（proxy 端口 → 8200）
- 修改 `AutoHySeeker/.env.example`（API_PORT → 8200）

**脚本逻辑**:
```bat
@echo off
echo [AutoHySeeker] Starting Backend (port 8200)...
start "AutoHySeeker-Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8200"

echo [AutoHySeeker] Starting Frontend (port 5173)...
start "AutoHySeeker-Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo   Backend: http://localhost:8200/docs
echo   Frontend: http://localhost:5173
echo.
```

**验收**: 双击 `dev.bat` 后，后端 `/health` 可访问，前端页面可打开。

---

### Task D-02: 消除 useDashboardPolling 中的伪造数据（P1 + P2）
**目标**: 将 Dashboard 的实验进度、Agent 状态、电化学图表、日志全部基于**真实 API 数据**

**当前问题详解**:

`useDashboardPolling.ts` 中的 4 个虚假数据生成器：

1. `generateEchemPoint()` — 用 `Math.sin() + Math.random()` 生成假电压/电流
2. `deriveAgentStates()` — 用 `Math.random()` 伪造 Agent 当前任务
3. `generateLogEntry()` — 硬编码 `"CPU 42%, Mem 58%"` 等假日志
4. `isRunning` — 仅检查 `!!latestName`，只要有历史实验名就认为"运行中"

**改造方案**:

#### 2a. 实验进度 → 完全从 optimizationStore 获取
- 删除 `useDashboardPolling` 中的 `ExperimentProgressState` 构建逻辑
- Dashboard 的 `<ExperimentProgress>` 组件直接从 `optimizationStore.state` 派生：
  - `status`: 取自 `optimizationState.status`（idle/running/paused/completed/error）
  - `progressPercent`: `(currentIteration / maxIterations) * 100`
  - `currentStep`: 取自 `optimizationState.status`（如 "designing", "executing", "analyzing"）
  - `runName`: 取自 `optimizationConfig.goal`

#### 2b. Agent 状态 → 新增后端 Agent 状态端点 或 从 optimization status 派生
- **方案 A（简单）**: 从 optimization status 中的 `status` 字段派生：
  - `status === "designing"` → Designer Agent working
  - `status === "executing"` → Executor Agent working  
  - `status === "analyzing"` → Diagnostics Agent working
  - 其他 → 所有 Agent idle
- **方案 B（后续）**: 后端新增 `/api/agents/status` 端点报告真实 Agent 状态
- **本轮选择方案 A**，后续如需更精细再升级

#### 2c. 电化学图表 → 暂不展示或标记 "无实时数据"
- 真实电化学数据来自 MicroHySeeker 桌面端，当前 AutoHySeeker 后端无此数据源
- **方案**: 当 `optimizationState.status !== "running"` 时，图表区域显示空状态占位 "暂无实时电化学数据"
- 当正在运行时，如后端有数据则展示，无数据则显示 "等待硬件数据..."

#### 2d. 日志 → 从后端 API 获取或仅显示 optimization 事件
- 日志目前完全伪造
- **方案**: 用 optimization store 中的 `errors` 数组 + 状态变化事件 作为"系统日志"
- `SystemNotificationsCard` 已经基于真实数据实现，可复用其逻辑

**文件变更**:
- 重构 `hooks/useDashboardPolling.ts` — 移除所有 generate* 函数，改为真实 API 数据
- 修改 `pages/Dashboard.tsx` — 统一数据源到 optimizationStore

**验收**: 
- 未启动优化时，Dashboard 所有卡片显示 idle/空状态
- 启动优化后，Dashboard 实时反映真实状态
- 不再出现任何 `Math.random()` 生成的数据

---

### Task D-03: 绑定 OptimizationStatusCard 的 Start/Stop 功能（P3）
**目标**: Start/Stop 按钮可实际控制优化循环

**当前问题**: 按钮是纯视觉元素，无 onClick 

**改造方案**:
- `OptimizationStatusCard` 接收 `onStart` / `onStop` 回调 props
- `Dashboard.tsx` 中将 `optimizationStore.startLoop` / `stopLoop` 传入
- Stop 按钮增加确认（防止误触）
- 按钮状态与 `isLoading` 联动，操作中显示 loading 态

**文件变更**:
- 修改 `components/dashboard/OptimizationStatusCard.tsx` — 增加 onClick props
- 修改 `pages/Dashboard.tsx` — 传入 store 方法

**验收**: 点击 Start → 后端 POST /api/optimization/start → 状态变为 running；点击 Stop → 后端 POST /api/optimization/stop → 状态变为 stopped

---

### Task D-04: 统一 Dashboard 数据源，消除双数据流（P4）
**目标**: Dashboard 只有一个数据真相来源

**当前问题**: 
- `useDashboardPolling` 轮询 `/health` + `/api/data/latest` → 生成 snapshot
- `useOptimizationStore` 轮询 `/api/optimization/status` + `/history` → 生成 optimizationState
- 两者各自独立，语义冲突

**改造方案**:
- **保留** `useDashboardPolling` 作为轻量级健康检查（只保留 health check 和紧急停止功能）
- **保留** `useOptimizationStore` 作为优化循环的唯一真相来源
- Dashboard 上的 5 个卡片数据源归属：

| 卡片 | 数据源 | 
|------|--------|
| OptimizationStatusCard | `optimizationStore` ✅ 已是 |
| RecentExperimentsCard | `optimizationStore` ✅ 已是 |
| SystemNotificationsCard | `optimizationStore` ✅ 已是 |
| ExperimentProgress | `optimizationStore` ⬅ 改为 |
| AgentStatusPanel | `optimizationStore` ⬅ 改为 |
| RealtimeChart | `optimizationStore` or 空状态 ⬅ 改为 |
| ExperimentLog | `optimizationStore.errors` ⬅ 改为 |

- `useDashboardPolling` 精简为：
  - 健康检查（isHealthy）
  - 紧急停止（requestEmergencyStop） 
  - 连接错误提示（pollError）
  - 不再生成 snapshot.experiment / snapshot.agents / snapshot.chartData / snapshot.logs

**文件变更**:
- 重构 `hooks/useDashboardPolling.ts`
- 修改 `pages/Dashboard.tsx`

> **注意**: Task D-02 和 D-04 有重叠，建议合并实施。

---

### Task D-05: 添加 MicroHySeeker 连接状态指示器（P6）
**目标**: 用户能明确看到硬件控制器是否在线

**改造方案**:
- 后端已有 `/api/control/status` 或类似端点检查 MicroHySeeker 可达性
- 前端 Dashboard header 区域增加一个连接状态标签：
  - 🟢 "MicroHySeeker 在线" — 硬件可控
  - 🔴 "MicroHySeeker 离线" — 仅模拟运行
- 可复用 useDashboardPolling 中的 healthCheck，额外请求 MicroHySeeker 状态

**后端新增（如需要）**:
- 在 `/api/optimization/status` 响应中增加 `hardware_available: bool` 字段
- 由后端主动 ping MicroHySeeker 的 `/health` 端点

**文件变更**:
- 修改后端 `routes/optimization.py` — status 响应增加 `hardware_available`
- 新建前端 `components/dashboard/HardwareStatusBadge.tsx`
- 修改 `pages/Dashboard.tsx` — header 区域展示

**验收**: MicroHySeeker 桌面端启动时显示绿色，关闭时显示红色

---

## 四、实施顺序 & 依赖

```
D-01（一键启动） → 独立，最先做
    ↓
D-02 + D-04（合并：消除假数据 + 统一数据源） → 核心改造
    ↓
D-03（Start/Stop 按钮绑定） → 依赖 D-04 完成后的数据流
    ↓
D-05（硬件状态指示） → 独立，但建议在 D-04 之后
```

**预估文件变更量**:

| Task | 新建 | 修改 | 删除 |
|------|------|------|------|
| D-01 | 1 (dev.bat) | 2 (vite.config.ts, .env.example) | 0 |
| D-02+D-04 | 0 | 2 (useDashboardPolling.ts, Dashboard.tsx) | 0 |
| D-03 | 0 | 2 (OptimizationStatusCard.tsx, Dashboard.tsx) | 0 |
| D-05 | 1 (HardwareStatusBadge.tsx) | 3 (optimization.py, Dashboard.tsx, optimization.ts) | 0 |

---

## 五、不做的事情（明确范围）

- **不做**数据库持久化（Phase 2 范畴）
- **不做**多会话聊天（Phase 2 F2 范畴）
- **不做**文献管理/科研分析/论文辅助页面（Phase 2 F2-01~F2-03）
- **不做**前端 E2E 测试补充（后续独立任务）
- **不改**后端 optimization_loop.py 的核心逻辑
- **不改**现有已通过的 757 个测试用例

---

## 六、验收标准

1. ✅ 双击 `dev.bat` 可同时启动前后端，无需手动输入命令
2. ✅ 未启动实验时，Dashboard 全部卡片显示 idle/空状态，无假数据
3. ✅ 点击 Start 按钮 → 实际调用后端 `/api/optimization/start`
4. ✅ 点击 Stop 按钮 → 实际调用后端 `/api/optimization/stop`
5. ✅ Dashboard 不再出现 Math.random 生成的伪造电压/电流/日志
6. ✅ MicroHySeeker 离线时有明确视觉提示
7. ✅ 所有 757 个现有测试仍然通过
