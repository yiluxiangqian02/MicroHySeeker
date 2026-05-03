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

```xml
<mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827" math="0" shadow="0">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>

    <!-- 标题 -->
    <mxCell id="title" value="MicroHySeeker 为 AutoHySeeker 提供的控制接口" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=16;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="150" y="20" width="869" height="30" as="geometry"/>
    </mxCell>

    <!-- ====== AHS 区域 ====== -->
    <mxCell id="ahs_bg" value="AutoHySeeker（智能决策层）" style="swimlane;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;fontStyle=1;startSize=28;" vertex="1" parent="1">
      <mxGeometry x="30" y="70" width="320" height="680" as="geometry"/>
    </mxCell>

    <mxCell id="ahs_goal" value="① 接收优化目标&#xa;（如：找最优 Fe:Co:Ni 配比）" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="40" width="280" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="ahs_design" value="② 设计实验参数&#xa;（贝叶斯优化 / LLM 推理）" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="120" width="280" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="ahs_exec" value="③ 调用 MHS API 执行实验&#xa;（本文档重点）" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="200" width="280" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="ahs_monitor" value="④ 轮询状态 / 异常处理&#xa;GET /api/experiment/status" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="280" width="280" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="ahs_data" value="⑤ 获取实验数据&#xa;GET /api/data/runs/{id}/files" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="360" width="280" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="ahs_analyze" value="⑥ 分析数据 · 提取指标&#xa;（过电位 / Tafel 斜率等）" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="440" width="280" height="50" as="geometry"/>
    </mxCell>
    <mxCell id="ahs_decide" value="⑦ 决策：继续优化 or 停止&#xa;→ 返回 ② 开始下一轮" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontStyle=1;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="520" width="280" height="50" as="geometry"/>
    </mxCell>

    <!-- 循环箭头 -->
    <mxCell id="loop_arrow" value="循环迭代" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#d6b656;fontColor=#d6b656;fontStyle=1;" edge="1" source="ahs_decide" target="ahs_design" parent="ahs_bg">
      <mxGeometry relative="1" as="geometry">
        <Array as="points">
          <mxPoint x="310" y="545"/>
          <mxPoint x="310" y="145"/>
        </Array>
      </mxGeometry>
    </mxCell>

    <!-- ====== MHS API 区域 ====== -->
    <mxCell id="mhs_bg" value="MicroHySeeker API 层（:8100）" style="swimlane;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=12;fontStyle=1;startSize=28;" vertex="1" parent="1">
      <mxGeometry x="430" y="70" width="380" height="680" as="geometry"/>
    </mxCell>

    <!-- API 分组：实验控制 -->
    <mxCell id="grp_exp" value="实验控制 /api/experiment/*" style="swimlane;fillColor=#fff2cc;strokeColor=#d6b656;startSize=24;fontSize=11;fontStyle=1;" vertex="1" parent="mhs_bg">
      <mxGeometry x="20" y="40" width="340" height="150" as="geometry"/>
    </mxCell>
    <mxCell id="api_start"  value="POST /start   启动实验" style="text;html=1;align=left;" vertex="1" parent="grp_exp"><mxGeometry x="10" y="28" width="300" height="20" as="geometry"/></mxCell>
    <mxCell id="api_status" value="GET  /status  查询进度（step / state）" style="text;html=1;align=left;" vertex="1" parent="grp_exp"><mxGeometry x="10" y="50" width="300" height="20" as="geometry"/></mxCell>
    <mxCell id="api_stop"   value="POST /stop    停止实验" style="text;html=1;align=left;" vertex="1" parent="grp_exp"><mxGeometry x="10" y="72" width="300" height="20" as="geometry"/></mxCell>
    <mxCell id="api_pause"  value="POST /pause   暂停实验" style="text;html=1;align=left;" vertex="1" parent="grp_exp"><mxGeometry x="10" y="94" width="300" height="20" as="geometry"/></mxCell>
    <mxCell id="api_resume" value="POST /resume  恢复实验" style="text;html=1;align=left;" vertex="1" parent="grp_exp"><mxGeometry x="10" y="116" width="300" height="20" as="geometry"/></mxCell>

    <!-- API 分组：系统监控 -->
    <mxCell id="grp_sys" value="系统监控 /api/system/*" style="swimlane;fillColor=#d5e8d4;strokeColor=#82b366;startSize=24;fontSize=11;fontStyle=1;" vertex="1" parent="mhs_bg">
      <mxGeometry x="20" y="210" width="340" height="110" as="geometry"/>
    </mxCell>
    <mxCell id="api_health"  value="GET  /health   健康检查（引擎状态 / RS485）" style="text;html=1;align=left;" vertex="1" parent="grp_sys"><mxGeometry x="10" y="28" width="310" height="20" as="geometry"/></mxCell>
    <mxCell id="api_logs"    value="GET  /logs     运行日志（按级别过滤）" style="text;html=1;align=left;" vertex="1" parent="grp_sys"><mxGeometry x="10" y="50" width="310" height="20" as="geometry"/></mxCell>
    <mxCell id="api_restart" value="POST /restart  重启 MHS 进程" style="text;html=1;align=left;" vertex="1" parent="grp_sys"><mxGeometry x="10" y="72" width="310" height="20" as="geometry"/></mxCell>

    <!-- API 分组：数据查询 -->
    <mxCell id="grp_data" value="数据查询 /api/data/*" style="swimlane;fillColor=#e1d5e7;strokeColor=#9673a6;startSize=24;fontSize=11;fontStyle=1;" vertex="1" parent="mhs_bg">
      <mxGeometry x="20" y="340" width="340" height="110" as="geometry"/>
    </mxCell>
    <mxCell id="api_runs"     value="GET  /runs               历史运行列表" style="text;html=1;align=left;" vertex="1" parent="grp_data"><mxGeometry x="10" y="28" width="310" height="20" as="geometry"/></mxCell>
    <mxCell id="api_run_id"   value="GET  /runs/{id}          单次运行详情" style="text;html=1;align=left;" vertex="1" parent="grp_data"><mxGeometry x="10" y="50" width="310" height="20" as="geometry"/></mxCell>
    <mxCell id="api_files"    value="GET  /runs/{id}/files     下载原始数据文件" style="text;html=1;align=left;" vertex="1" parent="grp_data"><mxGeometry x="10" y="72" width="310" height="20" as="geometry"/></mxCell>

    <!-- API 分组：硬件直控 -->
    <mxCell id="grp_dev" value="硬件直控 /api/device/*（应急 / 诊断用）" style="swimlane;fillColor=#f8cecc;strokeColor=#b85450;startSize=24;fontSize=11;fontStyle=1;" vertex="1" parent="mhs_bg">
      <mxGeometry x="20" y="470" width="340" height="130" as="geometry"/>
    </mxCell>
    <mxCell id="api_pump_start"  value="POST /pump/start        启动单个泵" style="text;html=1;align=left;" vertex="1" parent="grp_dev"><mxGeometry x="10" y="28" width="310" height="20" as="geometry"/></mxCell>
    <mxCell id="api_pump_status" value="GET  /pump/status       所有泵实时状态" style="text;html=1;align=left;" vertex="1" parent="grp_dev"><mxGeometry x="10" y="50" width="310" height="20" as="geometry"/></mxCell>
    <mxCell id="api_estop"       value="POST /emergency-stop    全设备紧急停止" style="text;html=1;align=left;fontStyle=1;fontColor=#b85450;" vertex="1" parent="grp_dev"><mxGeometry x="10" y="72" width="310" height="20" as="geometry"/></mxCell>
    <mxCell id="api_conn"        value="GET  /connection        RS485 连接状态" style="text;html=1;align=left;" vertex="1" parent="grp_dev"><mxGeometry x="10" y="94" width="310" height="20" as="geometry"/></mxCell>

    <!-- ====== MHS 执行层 ====== -->
    <mxCell id="hw_bg" value="MicroHySeeker 执行层" style="swimlane;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;fontSize=12;fontStyle=1;startSize=28;" vertex="1" parent="1">
      <mxGeometry x="890" y="70" width="249" height="680" as="geometry"/>
    </mxCell>
    <mxCell id="hw_engine" value="实验执行引擎&#xa;步骤调度器" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" vertex="1" parent="hw_bg">
      <mxGeometry x="20" y="60" width="209" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="hw_pump" value="蠕动泵驱动&#xa;RS485 / COM3&#xa;Pump 1~12" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" vertex="1" parent="hw_bg">
      <mxGeometry x="20" y="200" width="209" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="hw_echem" value="电化学工作站&#xa;CV / EIS / LSV&#xa;数据采集" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" vertex="1" parent="hw_bg">
      <mxGeometry x="20" y="360" width="209" height="70" as="geometry"/>
    </mxCell>
    <mxCell id="hw_store" value="实验数据存储&#xa;data/{日期}/{run_id}/" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" vertex="1" parent="hw_bg">
      <mxGeometry x="20" y="520" width="209" height="60" as="geometry"/>
    </mxCell>

    <!-- ====== 调用连线 ====== -->
    <!-- AHS exec → MHS exp group -->
    <mxCell id="e1" value="HTTP POST&#xa;提交实验方案" style="edgeStyle=orthogonalEdgeStyle;strokeColor=#b85450;strokeWidth=2;fontColor=#b85450;fontStyle=1;" edge="1" source="ahs_exec" target="grp_exp" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- AHS monitor → MHS status -->
    <mxCell id="e2" value="HTTP GET 轮询" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#6c8ebf;" edge="1" source="ahs_monitor" target="grp_exp" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- AHS data → MHS data group -->
    <mxCell id="e3" value="HTTP GET&#xa;下载数据" style="edgeStyle=orthogonalEdgeStyle;strokeColor=#9673a6;" edge="1" source="ahs_data" target="grp_data" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- AHS goal → MHS health (预检查) -->
    <mxCell id="e4" value="预检查" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#82b366;" edge="1" source="ahs_goal" target="grp_sys" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- MHS API → Engine -->
    <mxCell id="e5" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="grp_exp" target="hw_engine" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- Engine → Pump -->
    <mxCell id="e6" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="hw_engine" target="hw_pump" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- Engine → Echem -->
    <mxCell id="e7" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="hw_engine" target="hw_echem" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- Echem → Store -->
    <mxCell id="e8" value="写入数据" style="edgeStyle=orthogonalEdgeStyle;dashed=1;" edge="1" source="hw_echem" target="hw_store" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
    <!-- Data API → Store -->
    <mxCell id="e9" value="读取" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#9673a6;" edge="1" source="grp_data" target="hw_store" parent="1">
      <mxGeometry relative="1" as="geometry"/>
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
