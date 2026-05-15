# MicroHySeeker 为 AutoHySeeker 提供的控制接口
## ——基于 MHS REST API 的自动化实验协作方案

> **汇报背景**：MicroHySeeker (MHS) 硬件控制平台已完成开发并稳定运行。在此基础上，我们提出了 **AutoHySeeker (AHS)** 的概念——一个运行在 MHS 之上的智能自动化调度层。本文档重点说明 MHS 已为 AHS 准备好了哪些 API 接口、每个接口的用途，以及 AHS 如何借助这些接口实现**闭环迭代实验**。

---

## 1. 两者定位（一页纸）

```
┌──────────────────────────────────────────┐
│          AutoHySeeker (AHS)              │
│   智能决策层：理解目标 → 设计实验 →        │
│   分析结果 → 自主决策下一步              │
│                                          │
│   ← 调用 MHS REST API →                 │
└──────────────────────────────────────────┘
              ↕ HTTP :8100
┌──────────────────────────────────────────┐
│          MicroHySeeker (MHS)             │
│   硬件控制层：执行实验步骤 →              │
│   驱动泵/电化学仪 → 存储数据             │
└──────────────────────────────────────────┘
              ↕ RS485
         12 路蠕动泵 + 电化学工作站
```

**MHS 的角色**：忠实执行者，只负责"怎么做"  
**AHS 的角色**：智能决策者，负责"做什么、做几次、怎么优化"

---

## 2. MHS 提供的 API 接口总览

MHS 在 `8100` 端口运行 HTTP 服务，向 AHS 暴露 **5 类共 28 个接口**：

| 类别 | 前缀 | 接口数 | 核心用途 |
|------|------|--------|---------|
| 实验控制 | `/api/experiment` | 5 | 启动、停止、暂停、恢复、查询实验状态 |
| 系统监控 | `/api/system` | 3 | 健康检查、运行日志、进程重启 |
| 数据查询 | `/api/data` | 3 | 列出历史运行、获取详情、下载数据文件 |
| 硬件直控 | `/api/device` | 11 | 控制单个泵、清洗、配液、紧急停止 |
| 模板配置 | `/api/template` `/api/config` | 6 | 实验模板管理、系统配置读取 |

---

## 3. 各类接口详解

### 3.1 实验控制接口 `/api/experiment/*`

这是 AHS 最核心的调用入口，**每次自动化实验都必须经过这里**。

| 方法 | 路径 | 功能说明 |
|------|------|---------|
| `POST` | `/api/experiment/start` | **启动实验**。AHS 将实验方案（步骤列表、参数）以 JSON 格式提交给 MHS，MHS 立即开始执行 |
| `GET`  | `/api/experiment/status` | **查询实验状态**。返回当前步骤、总步骤数、运行时长、引擎状态（running/idle/error），AHS 通过轮询此接口监控进度 |
| `POST` | `/api/experiment/stop` | **停止实验**。AHS 可在任意时刻中止当前实验（如检测到异常时） |
| `POST` | `/api/experiment/pause` | **暂停实验**。暂停步骤执行，保留当前状态 |
| `POST` | `/api/experiment/resume` | **恢复实验**。从暂停点继续执行 |

**启动实验的请求格式示例：**
```json
POST /api/experiment/start
{
  "plan": {
    "name": "HER-Fe60Co25Ni15",
    "description": "测试 Fe:Co:Ni = 0.60:0.25:0.15 配比催化性能",
    "steps": [
      { "step_type": "prep_sol",  "params": { "Fe": 0.60, "Co": 0.25, "Ni": 0.15 } },
      { "step_type": "flush",     "params": { "duration_s": 30 } },
      { "step_type": "echem_cv",  "params": { "v_start": -0.5, "v_end": 0.5 } }
    ]
  }
}
```

**状态查询返回示例：**
```json
GET /api/experiment/status  →  200 OK
{
  "state":        "running",
  "current_step": 2,
  "total_steps":  32,
  "elapsed_s":    87.3,
  "step_type":    "echem_cv",
  "run_id":       "20260423_102015_HER-test"
}
```

---

### 3.2 系统监控接口 `/api/system/*`

AHS 在**每次实验启动前**必须调用健康检查，确认 MHS 在线且硬件连接正常。

| 方法 | 路径 | 功能说明 |
|------|------|---------|
| `GET`  | `/api/system/health` | **健康检查**。返回 MHS 进程状态、引擎状态（idle/running）、RS485 连接状态、进程已运行时长 |
| `GET`  | `/api/system/logs`   | **获取运行日志**。支持按级别过滤（info/warning/error），AHS 通过读取 error 级日志检测异常 |
| `POST` | `/api/system/restart`| **重启 MHS**。当 MHS 出现不可恢复错误时，AHS 可主动触发重启 |

**健康检查返回示例：**
```json
GET /api/system/health  →  200 OK
{
  "status":        "ok",
  "engine_state":  "idle",
  "uptime_seconds": 1823.4,
  "pid":           10504
}
```

---

### 3.3 数据查询接口 `/api/data/*`

实验结束后，AHS 通过这里获取原始数据，交给分析模块处理。

| 方法 | 路径 | 功能说明 |
|------|------|---------|
| `GET` | `/api/data/runs` | **列出所有历史运行**。返回按时间排序的运行列表，包含运行 ID、名称、完成状态 |
| `GET` | `/api/data/runs/{run_id}` | **获取单次运行详情**。包含每个步骤的执行结果、时间戳、异常记录 |
| `GET` | `/api/data/runs/{run_id}/files/{filename}` | **下载数据文件**。下载实验产生的 CSV 原始数据（电流-电压曲线等）供 AHS 分析 |

---

### 3.4 硬件直控接口 `/api/device/*`

主要供 AHS 在**诊断或应急场景**下直接控制硬件，常规流程不调用。

| 方法 | 路径 | 功能说明 |
|------|------|---------|
| `POST` | `/api/device/pump/start`     | 启动指定编号的泵（转速、方向可设） |
| `POST` | `/api/device/pump/stop`      | 停止指定泵 |
| `POST` | `/api/device/pump/stop-all`  | **紧急停止所有泵**（安全兜底） |
| `GET`  | `/api/device/pump/status`    | 查询全部 12 路泵的实时状态（运行中/停止/故障） |
| `POST` | `/api/device/flusher/start`  | 启动清洗循环 |
| `POST` | `/api/device/diluter/start`  | 启动配液通道 |
| `POST` | `/api/device/emergency-stop` | **全设备紧急停止**（最高优先级，立即中断一切动作） |
| `GET`  | `/api/device/connection`     | 查询 RS485 总线连接状态 |

---

### 3.5 模板与配置接口 `/api/template/*` `/api/config/*`

AHS 在**初始化阶段**通过这里了解 MHS 的能力和当前配置。

| 方法 | 路径 | 功能说明 |
|------|------|---------|
| `GET`  | `/api/template/list`            | 列出 MHS 中保存的所有实验模板 |
| `POST` | `/api/template/{id}/instantiate` | 用指定参数实例化模板并立即运行 |
| `POST` | `/api/template/validate`         | 参数合法性验证（dry-run，不实际执行） |
| `GET`  | `/api/config/system`             | 读取系统配置（泵数量、通道映射、标定参数） |
| `GET`  | `/api/config/capabilities`       | 读取系统能力摘要（支持哪些步骤类型、最大转速等） |
| `GET`  | `/api/config/dilution-channels`  | 读取各配液通道详情（溶液名称、剩余量） |

---

## 4. AHS 如何利用这些 API 实现闭环迭代

AHS 的核心价值在于：**通过上述 API 自主驱动 MHS 完成多轮实验，每轮结果影响下一轮参数**。

### 迭代实验流程图（文字版）

```
第 N 轮
   ①  调用 /api/system/health          ← 确认 MHS 在线
   ②  调用 /api/template/validate      ← 验证参数合法
   ③  调用 /api/experiment/start       ← 提交本轮实验方案
   ④  循环调用 /api/experiment/status  ← 监控进度（每 5s 轮询）
         ├─ 发现 error → 调用 /api/device/emergency-stop → 上报
         └─ 完成 → 继续
   ⑤  调用 /api/data/runs/{id}/files   ← 下载 CV/EIS 原始数据
   ⑥  [AHS 内部] 分析数据，提取过电位等指标
   ⑦  [AHS 内部] 决策：继续优化 or 停止
         └─ 继续 → 生成第 N+1 轮参数 → 回到 ①
```

### 一个完整轮次的 API 调用序列（代码视角）

```python
# AHS 执行单轮实验的核心逻辑（伪代码）

# 步骤 1：预检查
health = GET("http://mhs:8100/api/system/health")
assert health["engine_state"] == "idle"

# 步骤 2：参数验证
POST("http://mhs:8100/api/template/validate", json={"steps": next_params})

# 步骤 3：启动实验
result = POST("http://mhs:8100/api/experiment/start", json={"plan": experiment_plan})
run_id = result["run_id"]

# 步骤 4：监控进度
while True:
    status = GET("http://mhs:8100/api/experiment/status")
    if status["state"] == "idle":       # 完成
        break
    if "error" in status["state"]:      # 异常
        POST("http://mhs:8100/api/device/emergency-stop")
        raise ExperimentError(...)
    time.sleep(5)

# 步骤 5：获取数据
logs = GET(f"http://mhs:8100/api/system/logs?n=200&level=info")
data = GET(f"http://mhs:8100/api/data/runs/{run_id}/files/cv_data.csv")

# 步骤 6：分析 + 决策（AHS 内部）
metrics = analyze(data)
next_params = optimize(history + [metrics])
# → 进入下一轮循环
```

---

## 5. DrawIO 架构图

将以下 XML 粘贴到 [draw.io](https://draw.io) → **Extras → Edit Diagram** 即可还原。

> 接口测试验证结果数据来自 **2026-05-09 01:44** 对运行中 MHS（PID 10628）的真实查询。

```xml
<mxGraphModel dx="2893" dy="1209" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />
    <mxCell id="title" parent="1" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=16;fontStyle=1;" value="MicroHySeeker 控制接口说明与测试验证" vertex="1">
      <mxGeometry height="30" width="1300" x="30" y="20" as="geometry" />
    </mxCell>
    <mxCell id="ahs_bg" parent="1" style="swimlane;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;fontStyle=1;startSize=28;" value="AutoHySeeker（编排层 · 规划中）" vertex="1">
      <mxGeometry height="680" width="380" x="-30" y="70" as="geometry" />
    </mxCell>
    <mxCell id="uh21avQCfOiOk18pWu93-4" edge="1" parent="ahs_bg" source="ahs_goal" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" target="ahs_design">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="ahs_goal" parent="ahs_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" value="① 接收优化目标&#xa;（如：找最优 Fe:Co:Ni 配比）" vertex="1">
      <mxGeometry height="50" width="280" x="50" y="40" as="geometry" />
    </mxCell>
    <mxCell id="ahs_design" parent="ahs_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" value="② 设计实验参数&#xa;（贝叶斯优化 / LLM 推理）" vertex="1">
      <mxGeometry height="50" width="280" x="50" y="133" as="geometry" />
    </mxCell>
    <mxCell id="uh21avQCfOiOk18pWu93-6" edge="1" parent="ahs_bg" source="ahs_exec" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="190.16666666666697" y="320" as="targetPoint" />
      </mxGeometry>
    </mxCell>
    <mxCell id="ahs_exec" parent="ahs_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1;" value="③ 调用 MHS API 执行实验" vertex="1">
      <mxGeometry height="50" width="280" x="50" y="227" as="geometry" />
    </mxCell>
    <mxCell id="uh21avQCfOiOk18pWu93-7" edge="1" parent="ahs_bg" source="ahs_monitor" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" target="ahs_data">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="ahs_monitor" parent="ahs_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" value="④ 轮询状态 / 异常处理&#xa;GET /api/experiment/status" vertex="1">
      <mxGeometry height="50" width="280" x="50" y="320" as="geometry" />
    </mxCell>
    <mxCell id="ahs_data" parent="ahs_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" value="⑤ 获取实验数据&#xa;GET /api/data/runs/{id}/files" vertex="1">
      <mxGeometry height="50" width="280" x="50" y="413" as="geometry" />
    </mxCell>
    <mxCell id="uh21avQCfOiOk18pWu93-9" edge="1" parent="ahs_bg" source="ahs_analyze" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" target="ahs_decide">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="ahs_analyze" parent="ahs_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" value="⑥ 分析数据 · 提取指标&#xa;（过电位 / Tafel 斜率等）" vertex="1">
      <mxGeometry height="50" width="280" x="50" y="507" as="geometry" />
    </mxCell>
    <mxCell id="ahs_decide" parent="ahs_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontStyle=1;" value="⑦ 决策：继续优化 or 停止&#xa;→ 返回 ② 开始下一轮" vertex="1">
      <mxGeometry height="50" width="280" x="50" y="600" as="geometry" />
    </mxCell>
    <mxCell id="loop_arrow" edge="1" parent="ahs_bg" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#d6b656;fontColor=#d6b656;fontStyle=1;" value="循环迭代">
      <mxGeometry relative="1" as="geometry">
        <Array as="points">
          <mxPoint x="40" y="545" />
          <mxPoint x="40" y="145" />
        </Array>
        <mxPoint x="50" y="545" as="sourcePoint" />
        <mxPoint x="50" y="145" as="targetPoint" />
      </mxGeometry>
    </mxCell>
    <mxCell id="uh21avQCfOiOk18pWu93-5" edge="1" parent="ahs_bg" source="ahs_design" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="190" y="230" as="targetPoint" />
      </mxGeometry>
    </mxCell>
    <mxCell id="uh21avQCfOiOk18pWu93-8" edge="1" parent="ahs_bg" source="ahs_data" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;">
      <mxGeometry relative="1" as="geometry">
        <mxPoint x="190" y="510" as="targetPoint" />
      </mxGeometry>
    </mxCell>
    <mxCell id="mhs_bg" parent="1" style="swimlane;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=12;fontStyle=1;startSize=28;" value="MicroHySeeker API 层（:8100）" vertex="1">
      <mxGeometry height="680" width="380" x="430" y="70" as="geometry" />
    </mxCell>
    <mxCell id="grp_sys" parent="mhs_bg" style="swimlane;fillColor=#d5e8d4;strokeColor=#82b366;startSize=24;fontSize=11;fontStyle=1;" value="系统监控 /api/system/*" vertex="1">
      <mxGeometry height="110" width="340" x="20" y="40" as="geometry" />
    </mxCell>
    <mxCell id="api_health" parent="grp_sys" style="text;html=1;align=left;" value="GET  /health   健康检查（引擎状态 / RS485）" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="28" as="geometry" />
    </mxCell>
    <mxCell id="api_logs" parent="grp_sys" style="text;html=1;align=left;" value="GET  /logs     运行日志（按级别过滤）" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="50" as="geometry" />
    </mxCell>
    <mxCell id="api_restart" parent="grp_sys" style="text;html=1;align=left;" value="POST /restart  重启 MHS 进程" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="72" as="geometry" />
    </mxCell>
    <mxCell id="grp_exp" parent="mhs_bg" style="swimlane;fillColor=#fff2cc;strokeColor=#d6b656;startSize=24;fontSize=11;fontStyle=1;" value="实验控制 /api/experiment/*" vertex="1">
      <mxGeometry height="150" width="340" x="20" y="183" as="geometry" />
    </mxCell>
    <mxCell id="api_start" parent="grp_exp" style="text;html=1;align=left;" value="POST /start   启动实验" vertex="1">
      <mxGeometry height="20" width="300" x="10" y="28" as="geometry" />
    </mxCell>
    <mxCell id="api_status" parent="grp_exp" style="text;html=1;align=left;" value="GET  /status  查询进度（step / state）" vertex="1">
      <mxGeometry height="20" width="300" x="10" y="50" as="geometry" />
    </mxCell>
    <mxCell id="api_stop" parent="grp_exp" style="text;html=1;align=left;" value="POST /stop    停止实验" vertex="1">
      <mxGeometry height="20" width="300" x="10" y="72" as="geometry" />
    </mxCell>
    <mxCell id="api_pause" parent="grp_exp" style="text;html=1;align=left;" value="POST /pause   暂停实验" vertex="1">
      <mxGeometry height="20" width="300" x="10" y="94" as="geometry" />
    </mxCell>
    <mxCell id="api_resume" parent="grp_exp" style="text;html=1;align=left;" value="POST /resume  恢复实验" vertex="1">
      <mxGeometry height="20" width="300" x="10" y="116" as="geometry" />
    </mxCell>
    <mxCell id="grp_data" parent="mhs_bg" style="swimlane;fillColor=#e1d5e7;strokeColor=#9673a6;startSize=24;fontSize=11;fontStyle=1;" value="数据查询 /api/data/*" vertex="1">
      <mxGeometry height="110" width="340" x="20" y="367" as="geometry" />
    </mxCell>
    <mxCell id="api_runs" parent="grp_data" style="text;html=1;align=left;" value="GET  /runs               历史运行列表" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="28" as="geometry" />
    </mxCell>
    <mxCell id="api_run_id" parent="grp_data" style="text;html=1;align=left;" value="GET  /runs/{id}          单次运行详情" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="50" as="geometry" />
    </mxCell>
    <mxCell id="api_files" parent="grp_data" style="text;html=1;align=left;" value="GET  /runs/{id}/files     下载原始数据文件" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="72" as="geometry" />
    </mxCell>
    <mxCell id="grp_dev" parent="mhs_bg" style="swimlane;fillColor=#f8cecc;strokeColor=#b85450;startSize=24;fontSize=11;fontStyle=1;" value="硬件直控 /api/device/*（应急 / 诊断用）" vertex="1">
      <mxGeometry height="130" width="340" x="20" y="520" as="geometry" />
    </mxCell>
    <mxCell id="api_pump_start" parent="grp_dev" style="text;html=1;align=left;" value="POST /pump/start        启动单个泵" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="28" as="geometry" />
    </mxCell>
    <mxCell id="api_pump_status" parent="grp_dev" style="text;html=1;align=left;" value="GET  /pump/status       所有泵实时状态" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="50" as="geometry" />
    </mxCell>
    <mxCell id="api_estop" parent="grp_dev" style="text;html=1;align=left;fontStyle=1;fontColor=#b85450;" value="POST /emergency-stop    全设备紧急停止" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="72" as="geometry" />
    </mxCell>
    <mxCell id="api_conn" parent="grp_dev" style="text;html=1;align=left;" value="GET  /connection        RS485 连接状态" vertex="1">
      <mxGeometry height="20" width="310" x="10" y="94" as="geometry" />
    </mxCell>
    <mxCell id="hw_bg" parent="1" style="swimlane;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;fontSize=12;fontStyle=1;startSize=28;" value="MicroHySeeker 执行层" vertex="1">
      <mxGeometry height="680" width="249" x="1340" y="70" as="geometry" />
    </mxCell>
    <mxCell id="hw_engine" parent="hw_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" value="实验执行引擎&#xa;步骤调度器" vertex="1">
      <mxGeometry height="60" width="209" x="20" y="60" as="geometry" />
    </mxCell>
    <mxCell id="HoSgM7X_wwUFVYjlYAt--2" edge="1" parent="hw_bg" source="hw_pump" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;" target="hw_echem" value="">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="hw_pump" parent="hw_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" value="蠕动泵驱动&#xa;RS485 / COM3&#xa;Pump 1~12" vertex="1">
      <mxGeometry height="70" width="209" x="20" y="200" as="geometry" />
    </mxCell>
    <mxCell id="hw_echem" parent="hw_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" value="电化学工作站&#xa;CV / EIS / LSV&#xa;数据采集" vertex="1">
      <mxGeometry height="70" width="209" x="20" y="360" as="geometry" />
    </mxCell>
    <mxCell id="hw_store" parent="hw_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" value="实验数据存储&#xa;data/{日期}/{run_id}/" vertex="1">
      <mxGeometry height="60" width="209" x="20" y="520" as="geometry" />
    </mxCell>
    <mxCell id="e6" edge="1" parent="hw_bg" source="hw_engine" style="edgeStyle=orthogonalEdgeStyle;" target="hw_pump" value="">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e7" edge="1" parent="hw_bg" source="hw_engine" style="edgeStyle=orthogonalEdgeStyle;" target="hw_echem" value="">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e8" edge="1" parent="hw_bg" source="hw_echem" style="edgeStyle=orthogonalEdgeStyle;dashed=1;" target="hw_store" value="写入数据">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e1" edge="1" parent="1" source="ahs_exec" style="edgeStyle=orthogonalEdgeStyle;strokeColor=#b85450;strokeWidth=2;fontColor=#b85450;fontStyle=1;entryX=0;entryY=0.5;entryDx=0;entryDy=0;" target="grp_exp" value="HTTP POST&#xa;提交实验方案">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e2" edge="1" parent="1" source="ahs_monitor" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#6c8ebf;entryX=0;entryY=0.75;entryDx=0;entryDy=0;" target="grp_exp" value="HTTP GET 轮询">
      <mxGeometry relative="1" x="0.3004" as="geometry">
        <mxPoint as="offset" />
        <Array as="points">
          <mxPoint x="160" y="366" />
        </Array>
      </mxGeometry>
    </mxCell>
    <mxCell id="e3" edge="1" parent="1" source="ahs_data" style="edgeStyle=orthogonalEdgeStyle;strokeColor=#9673a6;" target="grp_data" value="HTTP GET&#xa;下载数据">
      <mxGeometry relative="1" x="0.0004" y="-5" as="geometry">
        <mxPoint as="offset" />
      </mxGeometry>
    </mxCell>
    <mxCell id="e4" edge="1" parent="1" source="ahs_goal" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#82b366;" target="grp_sys" value="预检查">
      <mxGeometry relative="1" as="geometry">
        <Array as="points">
          <mxPoint x="620" y="135" />
        </Array>
      </mxGeometry>
    </mxCell>
    <mxCell id="e5" edge="1" parent="1" source="test_bg" style="edgeStyle=orthogonalEdgeStyle;entryX=0;entryY=0.5;entryDx=0;entryDy=0;exitX=1;exitY=0.5;exitDx=0;exitDy=0;" target="hw_bg" value="">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="e9" edge="1" parent="1" source="grp_data" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#9673a6;entryX=0;entryY=0.5;entryDx=0;entryDy=0;" target="hw_store" value="读取">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="test_bg" parent="1" style="swimlane;fillColor=#e8f5e9;strokeColor=#388e3c;fontSize=12;fontStyle=1;startSize=28;" value="接口测试验证结果（实际返回）" vertex="1">
      <mxGeometry height="680" width="390" x="860" y="70" as="geometry" />
    </mxCell>
    <mxCell id="test_sys" parent="test_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f1f8e9;strokeColor=#7cb342;align=left;fontSize=10;spacingLeft=8;fontFamily=Courier New;" value="✓ GET /api/system/health  →  HTTP 200&#xa;─────────────────────────────&#xa;{&#xa;  &quot;status&quot;:        &quot;ok&quot;,&#xa;  &quot;engine_state&quot;:  &quot;idle&quot;,&#xa;  &quot;uptime_seconds&quot;: 10.6,&#xa;  &quot;pid&quot;:            10628,&#xa;  &quot;timestamp&quot;: &quot;2026-05-09T01:44:37Z&quot;&#xa;}" vertex="1">
      <mxGeometry height="120" width="360" x="15" y="40" as="geometry" />
    </mxCell>
    <mxCell id="test_exp" parent="test_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f1f8e9;strokeColor=#7cb342;align=left;fontSize=10;spacingLeft=8;fontFamily=Courier New;" value="✓ GET /api/experiment/status  →  HTTP 200&#xa;─────────────────────────────&#xa;{&#xa;  &quot;state&quot;:        &quot;idle&quot;,&#xa;  &quot;run_id&quot;:       null,&#xa;  &quot;is_running&quot;:   false,&#xa;  &quot;is_paused&quot;:    false,&#xa;  &quot;total_steps&quot;:  0,&#xa;  &quot;current_step&quot;: null&#xa;}&#xa;（历史最多完成 32 步闭环实验）" vertex="1">
      <mxGeometry height="160" width="360" x="15" y="195" as="geometry" />
    </mxCell>
    <mxCell id="test_data_r" parent="test_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f1f8e9;strokeColor=#7cb342;align=left;fontSize=10;spacingLeft=8;fontFamily=Courier New;" value="✓ GET /api/data/runs  →  HTTP 200&#xa;─────────────────────────────&#xa;{&#xa;  &quot;total&quot;: 50,&#xa;  &quot;runs&quot;: [{&#xa;    &quot;run_id&quot;: &quot;2026-04-21_21-43-16_...step_0&quot;,&#xa;    &quot;status&quot;: &quot;has_data&quot;,&#xa;    &quot;date&quot;:   &quot;2026-04-21&quot;&#xa;  }, ...（共50条历史记录）]&#xa;}" vertex="1">
      <mxGeometry height="120" width="360" x="15" y="390" as="geometry" />
    </mxCell>
    <mxCell id="test_dev_r" parent="test_bg" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f1f8e9;strokeColor=#7cb342;align=left;fontSize=10;spacingLeft=8;fontFamily=Courier New;" value="✓ GET /api/device/pump/status  →  HTTP 200&#xa;{ &quot;pumps&quot;: [&#xa;  {&quot;address&quot;:1, &quot;online&quot;:true, &quot;speed&quot;:0, &quot;fault&quot;:null},&#xa;  ... (Pump 1~12 全部在线，无故障)&#xa;]}&#xa;─────────────────────────────&#xa;✓ GET /api/device/connection  →  HTTP 200&#xa;{ &quot;connected&quot;: true, &quot;mock_mode&quot;: false, &quot;port&quot;: &quot;COM3&quot; }" vertex="1">
      <mxGeometry height="120" width="360" x="15" y="545" as="geometry" />
    </mxCell>
    <mxCell id="te1" edge="1" parent="1" source="grp_sys" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#388e3c;strokeWidth=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;" target="test_sys" value="">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="te2" edge="1" parent="1" source="grp_exp" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#388e3c;strokeWidth=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;" target="test_exp" value="">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="te3" edge="1" parent="1" source="grp_data" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#388e3c;strokeWidth=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;" target="test_data_r" value="">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="te4" edge="1" parent="1" source="grp_dev" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#388e3c;strokeWidth=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;" target="test_dev_r" value="">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
  </root>
</mxGraphModel>
```

---

## 6. 汇报要点提炼（三句话版）

1. **MHS 已完成**，并对外暴露了 5 类 28 个标准 HTTP 接口，覆盖实验控制、状态监控、数据获取、硬件诊断全流程。

2. **AHS 是在 MHS 之上提出的智能调度层**，它不需要了解硬件细节，只需通过调用这些接口即可驱动 MHS 完成任意复杂的实验程序。

3. **最终目标**：研究员只需输入优化方向，AHS 自主调用 MHS API 完成"设计→执行→分析→再设计"的全自动闭环，将人工优化实验的周期从数天缩短到数小时。

---

*文档路径：`docs/report/`  |  生成时间：2026-04-23*
