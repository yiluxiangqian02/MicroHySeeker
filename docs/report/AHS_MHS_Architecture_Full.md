# AutoHySeeker 系统架构汇报
## ——引入 AHS 智能层及其与 MHS 的协作关系

> **汇报背景**：MicroHySeeker (MHS) 硬件控制平台已完成并稳定运行。本文档介绍在 MHS 基础上新建立的 AutoHySeeker (AHS) 智能自动化层，重点说明两者的定位分工与协作机制。

---

## 1. 整体定位

| 系统 | 定位 | 核心职责 |
|------|------|---------|
| **MicroHySeeker (MHS)** | 硬件控制层 | 直接驱动 RS485 硬件设备（蠕动泵、电化学工作站），执行实验程序，管理数据存储 |
| **AutoHySeeker (AHS)** | 智能决策层 | 理解实验目标，自主规划实验方案，调度 MHS 执行，分析结果，闭环迭代优化 |

**一句话总结**：MHS 是"手"，负责精确执行物理操作；AHS 是"大脑"，负责思考做什么实验、怎么优化。

---

## 2. MHS 对外提供的 API 接口（供 AHS 调用）

MHS 在本机 **8100 端口** 启动无界面 HTTP 服务，向 AHS 暴露以下 5 类 REST API：

### 2.1 实验控制 `/api/experiment/*`
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/experiment/start` | 提交实验方案并启动执行 |
| POST | `/api/experiment/stop` | 停止当前实验 |
| POST | `/api/experiment/pause` | 暂停实验 |
| POST | `/api/experiment/resume` | 恢复暂停的实验 |
| GET  | `/api/experiment/status` | 查询实验运行状态 |

### 2.2 系统监控 `/api/system/*`
| 方法 | 路径 | 功能 |
|------|------|------|
| GET  | `/api/system/health` | 健康检查（引擎状态、进程信息、启动时长） |
| GET  | `/api/system/logs` | 获取近期运行日志（按级别过滤：info/warning/error） |
| POST | `/api/system/restart` | 重启 MHS 进程 |

### 2.3 数据查询 `/api/data/*`
| 方法 | 路径 | 功能 |
|------|------|------|
| GET  | `/api/data/runs` | 列出所有历史实验运行 |
| GET  | `/api/data/runs/{run_id}` | 获取单次运行详情 |
| GET  | `/api/data/runs/{run_id}/files/{filename}` | 下载原始数据文件（CSV 等） |

### 2.4 硬件直控 `/api/device/*`（用于 Agent 诊断/调试）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/device/pump/start` | 启动单个泵 |
| POST | `/api/device/pump/stop` | 停止单个泵 |
| POST | `/api/device/pump/stop-all` | 紧急停止所有泵 |
| GET  | `/api/device/pump/status` | 查询全部泵状态 |
| POST | `/api/device/flusher/start` | 启动清洗循环 |
| POST | `/api/device/diluter/start` | 启动配液 |
| POST | `/api/device/emergency-stop` | 全设备紧急停止 |
| GET  | `/api/device/connection` | 查询 RS485 连接状态 |

### 2.5 模板与配置 `/api/template/*`、`/api/config/*`
| 方法 | 路径 | 功能 |
|------|------|------|
| GET  | `/api/template/list` | 列出所有实验模板 |
| POST | `/api/template/{id}/instantiate` | 从模板实例化并运行实验 |
| POST | `/api/template/validate` | 验证实验参数合法性 |
| GET  | `/api/config/system` | 查询泵/通道/标定等系统配置 |
| GET  | `/api/config/capabilities` | 查询系统能力摘要 |
| GET  | `/api/config/dilution-channels` | 查询配液通道列表 |

---

## 3. AHS 内部结构

AHS 运行在本机 **8200 端口**，对外（前端）提供人机交互接口，对内驱动多 Agent 协作。

### 3.1 核心 Agent 分工

```
┌──────────────────────────────────────────────────────────┐
│                     AutoHySeeker (AHS)                    │
│  ┌─────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │ Orchestrator│  │ ExpDesigner   │  │ ExpExecutor    │  │
│  │  总调度 Agent│→ │  参数设计 Agent│→ │  执行 Agent    │  │
│  │             │  │               │  │  (唯一操硬件的) │  │
│  └─────────────┘  └───────────────┘  └───────┬────────┘  │
│         ↑                                     │ HTTP      │
│  ┌──────┴──────┐  ┌───────────────┐           ↓           │
│  │DataAnalyst  │  │KnowledgeManager│    MHS :8100         │
│  │  数据分析    │  │   知识归档     │                      │
│  └─────────────┘  └───────────────┘                      │
└──────────────────────────────────────────────────────────┘
```

| Agent | 职责 |
|-------|------|
| **Orchestrator** | 全局决策：分析优化趋势，决定"继续/停止/重试/调整策略"，协调其他 Agent |
| **Experiment Designer** | 设计下一组实验参数（支持初始网格、LLM 推理、贝叶斯优化三种策略） |
| **Experiment Executor** | 唯一负责与 MHS 通信的 Agent：预检查 → 提交实验 → 监控进度 → 收集数据 |
| **Data Analyst** | 解读电化学数据（CV、EIS、LSV），提取过电位、Tafel 斜率等关键指标 |
| **Knowledge Manager** | 归档实验结果，供后续优化参考 |

---

## 4. AHS 与 MHS 协作流程

```
用户下达目标
    │
    ▼
[AHS Orchestrator]
 分析历史 → 制定优化策略
    │
    ▼
[AHS ExpDesigner]
 生成实验参数（元素配比等）
    │
    ▼
[AHS ExpExecutor]
 ① 调用 MHS /api/system/health 预检查
 ② 调用 MHS /api/experiment/start 提交实验
 ③ 轮询 MHS /api/experiment/status 监控进度
 ④ 异常时调用 MHS /api/device/emergency-stop
 ⑤ 完成后从共享 data/ 目录读取数据
    │
    ▼
[AHS DataAnalyst]
 解析 CSV 数据 → 提取性能指标
    │
    ▼
[AHS Orchestrator]
 评估结果 → 决定下一步 → 循环或终止
```

### 实际调用代码示例

**AHS 提交实验到 MHS：**
```python
# AutoHySeeker/src/api/routes/experiments.py
async with httpx.AsyncClient(transport=_mhs_transport(), timeout=300) as client:
    resp = await client.post(
        "http://127.0.0.1:8100/api/experiment/start",
        json={"plan": experiment_plan}
    )
```

**AHS 轮询 MHS 实验状态：**
```python
resp = await client.get("http://127.0.0.1:8100/api/experiment/status")
state = resp.json()  # {"state": "running", "step": 3, "total": 32, ...}
```

---

## 5. 共享资源

AHS 与 MHS 除 HTTP 接口外，还通过以下共享资源协作：

| 共享内容 | 位置 | 权限 |
|---------|------|------|
| **系统配置文件** | `MicroHySeeker/config/system.json` | MHS 写 / AHS 只读 |
| **实验数据目录** | `data/{日期}/` | MHS 写入采集数据；AHS 写入执行日志，读取分析 |

> `system.json` 包含所有泵的标定参数、配液通道、清洗通道配置。AHS 通过 mtime 检测文件变更，MHS 修改配置后 AHS 自动重新加载。

---

## 6. 进程管理关系

```
dev.bat 启动脚本
    ├── 启动 AHS 后端 (uvicorn :8200)
    │       └── AHS 启动时自动检测 MHS 是否运行
    │               ├── 已运行 → 直接使用
    │               └── 未运行 → 自动拉起 MHS headless 进程 (:8100)
    └── 启动前端开发服务器 (Vite :5173)
            └── 代理 /api/* → AHS :8200
```

**关键设计**：AHS 是 MHS 的"上游管理者"，AHS 启动时会自动确保 MHS 在线。同时新版 `dev.bat` 会检测 MHS 代码是否已更新，提示是否需要重启 MHS。

---

## 7. DrawIO 架构图 XML

将以下 XML 内容粘贴到 [draw.io](https://draw.io) → 「Extras → Edit Diagram」即可还原完整架构图。

```xml
<mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1654" pageHeight="1169" math="0" shadow="0">
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />

    <!-- ===== 标题 ===== -->
    <mxCell id="title" value="MicroHySeeker (MHS) × AutoHySeeker (AHS) 协作架构" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=18;fontStyle=1;" vertex="1" parent="1">
      <mxGeometry x="300" y="20" width="900" height="40" as="geometry" />
    </mxCell>

    <!-- ===== 用户/前端区域 ===== -->
    <mxCell id="user_bg" value="用户界面层" style="swimlane;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=13;fontStyle=1;startSize=30;" vertex="1" parent="1">
      <mxGeometry x="30" y="80" width="220" height="120" as="geometry" />
    </mxCell>
    <mxCell id="browser" value="🌐 Web 浏览器&#xa;localhost:5173" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="user_bg">
      <mxGeometry x="20" y="45" width="180" height="50" as="geometry" />
    </mxCell>

    <!-- ===== AHS 区域 ===== -->
    <mxCell id="ahs_bg" value="AutoHySeeker — 智能决策层 (:8200)" style="swimlane;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=13;fontStyle=1;startSize=30;" vertex="1" parent="1">
      <mxGeometry x="310" y="80" width="680" height="380" as="geometry" />
    </mxCell>

    <!-- AHS Frontend Proxy -->
    <mxCell id="vite" value="Vite 开发服务器&#xa;/api/* → :8200" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="45" width="160" height="50" as="geometry" />
    </mxCell>

    <!-- AHS API Gateway -->
    <mxCell id="ahs_api" value="FastAPI 网关&#xa;/api/experiments&#xa;/api/system&#xa;/api/tasks" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" vertex="1" parent="ahs_bg">
      <mxGeometry x="230" y="45" width="160" height="70" as="geometry" />
    </mxCell>

    <!-- Orchestrator -->
    <mxCell id="orch" value="🧠 Orchestrator&#xa;总调度 Agent&#xa;(决策 / 循环控制)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="160" width="160" height="70" as="geometry" />
    </mxCell>

    <!-- ExpDesigner -->
    <mxCell id="designer" value="🔬 ExpDesigner&#xa;实验设计 Agent&#xa;(贝叶斯/LLM 参数规划)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="ahs_bg">
      <mxGeometry x="230" y="160" width="160" height="70" as="geometry" />
    </mxCell>

    <!-- ExpExecutor -->
    <mxCell id="executor" value="⚙️ ExpExecutor&#xa;执行 Agent&#xa;(唯一操硬件入口)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1;" vertex="1" parent="ahs_bg">
      <mxGeometry x="440" y="160" width="160" height="70" as="geometry" />
    </mxCell>

    <!-- DataAnalyst -->
    <mxCell id="analyst" value="📊 DataAnalyst&#xa;数据分析 Agent&#xa;(CV/EIS/LSV 解析)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="ahs_bg">
      <mxGeometry x="20" y="285" width="160" height="70" as="geometry" />
    </mxCell>

    <!-- KnowledgeMgr -->
    <mxCell id="knowledge" value="📚 KnowledgeManager&#xa;知识归档 Agent&#xa;(历史结果存储)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="ahs_bg">
      <mxGeometry x="230" y="285" width="160" height="70" as="geometry" />
    </mxCell>

    <!-- ===== MHS 区域 ===== -->
    <mxCell id="mhs_bg" value="MicroHySeeker — 硬件控制层 (:8100)" style="swimlane;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=13;fontStyle=1;startSize=30;" vertex="1" parent="1">
      <mxGeometry x="1050" y="80" width="560" height="380" as="geometry" />
    </mxCell>

    <!-- MHS API -->
    <mxCell id="mhs_api" value="MHS REST API&#xa;/api/experiment/*&#xa;/api/system/*&#xa;/api/data/*&#xa;/api/device/*&#xa;/api/template/*" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;" vertex="1" parent="mhs_bg">
      <mxGeometry x="20" y="45" width="160" height="110" as="geometry" />
    </mxCell>

    <!-- ExperimentRunner -->
    <mxCell id="runner" value="🏃 ExperimentRunner&#xa;实验执行引擎&#xa;(步骤调度 / 批次等待)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;" vertex="1" parent="mhs_bg">
      <mxGeometry x="240" y="45" width="170" height="70" as="geometry" />
    </mxCell>

    <!-- HardwareManager -->
    <mxCell id="hw_mgr" value="🔧 硬件管理器&#xa;泵控制器 / 配液 / 清洗" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;" vertex="1" parent="mhs_bg">
      <mxGeometry x="240" y="160" width="170" height="70" as="geometry" />
    </mxCell>

    <!-- EchemSDL -->
    <mxCell id="echem" value="⚡ eChemSDL&#xa;电化学仪器驱动&#xa;(CV / EIS / LSV 测量)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;" vertex="1" parent="mhs_bg">
      <mxGeometry x="240" y="270" width="170" height="70" as="geometry" />
    </mxCell>

    <!-- RS485 Bus -->
    <mxCell id="rs485" value="RS485 总线&#xa;COM3 @ 38400 baud&#xa;Pump1~Pump12" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;" vertex="1" parent="mhs_bg">
      <mxGeometry x="400" y="160" width="140" height="70" as="geometry" />
    </mxCell>

    <!-- ===== 共享资源区域 ===== -->
    <mxCell id="shared_bg" value="共享资源" style="swimlane;fillColor=#e1d5e7;strokeColor=#9673a6;fontSize=13;fontStyle=1;startSize=30;" vertex="1" parent="1">
      <mxGeometry x="630" y="340" width="360" height="120" as="geometry" />
    </mxCell>

    <mxCell id="system_json" value="📄 config/system.json&#xa;泵标定 / 通道配置&#xa;MHS写 | AHS只读" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" vertex="1" parent="shared_bg">
      <mxGeometry x="20" y="40" width="140" height="60" as="geometry" />
    </mxCell>

    <mxCell id="data_dir" value="📁 data/ 目录&#xa;实验数据 / 日志&#xa;双方均可写入" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;" vertex="1" parent="shared_bg">
      <mxGeometry x="200" y="40" width="140" height="60" as="geometry" />
    </mxCell>

    <!-- ===== 连接线 ===== -->
    <!-- 浏览器 → Vite -->
    <mxCell id="e1" value="HTTP / WebSocket" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="browser" target="vite" parent="1">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Vite → AHS API -->
    <mxCell id="e2" value="代理转发" style="edgeStyle=orthogonalEdgeStyle;dashed=1;" edge="1" source="vite" target="ahs_api" parent="ahs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- AHS API → Orchestrator -->
    <mxCell id="e3" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="ahs_api" target="orch" parent="ahs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Orchestrator → Designer -->
    <mxCell id="e4" value="设计任务" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="orch" target="designer" parent="ahs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Designer → Executor -->
    <mxCell id="e5" value="实验方案" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="designer" target="executor" parent="ahs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Executor → Orchestrator (结果回报) -->
    <mxCell id="e6" value="执行结果" style="edgeStyle=orthogonalEdgeStyle;dashed=1;" edge="1" source="executor" target="orch" parent="ahs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Orchestrator → DataAnalyst -->
    <mxCell id="e7" value="分析请求" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="orch" target="analyst" parent="ahs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Orchestrator → Knowledge -->
    <mxCell id="e8" value="归档" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="orch" target="knowledge" parent="ahs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Executor → MHS API (跨区域) -->
    <mxCell id="e9" value="HTTP REST&#xa;(start/status/stop/logs)" style="edgeStyle=orthogonalEdgeStyle;strokeColor=#b85450;strokeWidth=2;fontColor=#b85450;fontStyle=1;" edge="1" source="executor" target="mhs_api" parent="1">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- MHS API → Runner -->
    <mxCell id="e10" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="mhs_api" target="runner" parent="mhs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Runner → HWMgr -->
    <mxCell id="e11" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="runner" target="hw_mgr" parent="mhs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- HWMgr → RS485 -->
    <mxCell id="e12" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="hw_mgr" target="rs485" parent="mhs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Runner → eChemSDL -->
    <mxCell id="e13" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="runner" target="echem" parent="mhs_bg">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- AHS → shared data (config read) -->
    <mxCell id="e14" value="只读配置" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#9673a6;" edge="1" source="ahs_bg" target="system_json" parent="1">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- MHS → shared data (写) -->
    <mxCell id="e15" value="写入" style="edgeStyle=orthogonalEdgeStyle;strokeColor=#9673a6;" edge="1" source="mhs_bg" target="data_dir" parent="1">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- AHS → shared data (读写日志) -->
    <mxCell id="e16" value="读/写日志" style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#9673a6;" edge="1" source="ahs_bg" target="data_dir" parent="1">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- MHS → config write -->
    <mxCell id="e17" value="写入配置" style="edgeStyle=orthogonalEdgeStyle;strokeColor=#9673a6;" edge="1" source="mhs_bg" target="system_json" parent="1">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

  </root>
</mxGraphModel>
```

---

## 8. 核心价值总结

**MHS 已实现**：精确的硬件控制能力——给定实验程序，MHS 能可靠地完成物理操作并采集数据。

**AHS 带来的新能力**：

1. **自然语言交互**：研究人员可用对话方式描述优化目标，AHS 自动转化为实验方案
2. **闭环自主优化**：AHS 能自主执行"设计→实验→分析→再设计"的完整循环，无需人工介入每一步
3. **智能异常处理**：执行过程中检测到硬件异常，自动触发安全停止并上报
4. **知识积累**：每次实验结果被自动归档，后续优化可利用历史知识

**最终目标**：研究人员只需告诉系统"找到最优的 HER 催化剂配比"，AHS + MHS 联合自主完成从配液、测量到报告生成的全流程。

---

*文档生成时间：2026-04-22*
