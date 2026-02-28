# AutoHySeeker 前端开发指南

> 2026-02-27 | 状态：规划阶段
> 定位：AutoHySeeker 的 **Web 前端** — React + WebSocket 实时通信
> 关联：[dev_backend.md](dev_backend.md) | [architecture_overview.md](architecture_overview.md)

---

## 一、前端定位

AutoHySeeker 的前端是一个 **轻量 Web 应用**（React），通过 HTTP/WebSocket 与 AutoHySeeker 后端通信。

**为什么不直接扩展 MicroHySeeker 的 PySide6 界面？**

| 维度 | PySide6 扩展 | Web 前端 |
|---|---|---|
| AI 对话界面 | PySide6 做 chat UI 困难、Markdown 渲染差 | 天然适合富文本对话 |
| 图表渲染 | matplotlib 静态图 | ECharts/Plotly 交互图表 |
| 开发效率 | Python UI 开发慢 | React 生态丰富、Hot Reload |
| 部署灵活性 | 绑定桌面 | 局域网内任何设备可访问 |
| 与现有系统关系 | 侵入 MicroHySeeker 代码 | 独立进程，零侵入 |

**结论**：AI 交互用 Web 前端，硬件控制继续用 MicroHySeeker PySide6 桌面端。两者通过后端 API 联通。

```
┌──────────────────────────────────────────────────────┐
│  浏览器 (localhost:3000)                              │
│                                                       │
│  ┌─────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │ Chat    │  │ Experiment │  │ Knowledge        │   │
│  │ Panel   │  │ Dashboard  │  │ Explorer         │   │
│  └────┬────┘  └─────┬──────┘  └────────┬─────────┘   │
│       │              │                  │             │
│  ─────┴──────────────┴──────────────────┴──────────── │
│                WebSocket / REST API                    │
└──────────────────────┬────────────────────────────────┘
                       │
                       ▼
             AutoHySeeker Backend (:8100)
                       │
                       ▼
             MicroHySeeker (PySide6)
```

---

## 二、技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 框架 | React 18 + TypeScript | 类型安全、生态丰富 |
| 构建 | Vite | 极速 HMR |
| UI 库 | Ant Design 5 | 成熟的企业级组件库、中文友好 |
| 图表 | ECharts (via echarts-for-react) | 电化学图表交互性强 |
| 状态管理 | Zustand | 轻量、TypeScript 友好 |
| 路由 | React Router v6 | SPA 路由 |
| HTTP 客户端 | Axios | REST API 调用 |
| WebSocket | 原生 WebSocket + reconnecting-websocket | 流式对话 |
| Markdown 渲染 | react-markdown + rehype-katex | Agent 响应渲染、数学公式 |
| 代码高亮 | react-syntax-highlighter | Python/JSON 代码块 |
| 样式 | CSS Modules / Ant Design token | 主题定制 |

---

## 三、项目目录结构

```
AutoHySeeker/
├── frontend/                      # Web 前端项目
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   │
│   ├── public/
│   │   └── favicon.svg
│   │
│   └── src/
│       ├── main.tsx               # React 入口
│       ├── App.tsx                # 根组件 + 路由配置
│       ├── vite-env.d.ts
│       │
│       ├── api/                   # ★ API 层
│       │   ├── client.ts          # Axios 实例（baseURL, interceptors）
│       │   ├── chat.ts            # POST /api/chat
│       │   ├── agents.ts          # 直接调用 Agent
│       │   ├── experiments.ts     # 实验 CRUD
│       │   ├── knowledge.ts       # 知识库操作
│       │   └── sessions.ts        # Session CRUD
│       │
│       ├── ws/                    # ★ WebSocket 层
│       │   ├── chatSocket.ts      # WebSocket 连接管理 + 重连
│       │   └── types.ts           # WS 消息类型定义
│       │
│       ├── stores/                # ★ Zustand 状态管理
│       │   ├── chatStore.ts       # 对话历史、当前 session
│       │   ├── experimentStore.ts # 实验列表、当前选中
│       │   ├── knowledgeStore.ts  # 知识库树
│       │   └── uiStore.ts        # 侧边栏/主题/布局
│       │
│       ├── pages/                 # 页面组件
│       │   ├── ChatPage.tsx       # 主对话页面
│       │   ├── ExperimentsPage.tsx # 实验 Dashboard
│       │   ├── KnowledgePage.tsx  # 知识库浏览
│       │   └── SettingsPage.tsx   # 设置
│       │
│       ├── components/            # 可复用组件
│       │   ├── layout/
│       │   │   ├── AppLayout.tsx  # 全局布局（侧边栏 + 内容区）
│       │   │   ├── Sidebar.tsx    # 左侧导航
│       │   │   └── Header.tsx     # 顶栏
│       │   │
│       │   ├── chat/
│       │   │   ├── ChatWindow.tsx      # 对话窗口
│       │   │   ├── MessageBubble.tsx   # 单条消息（支持 Markdown/图表）
│       │   │   ├── InputBar.tsx        # 输入栏
│       │   │   ├── AgentBadge.tsx      # Agent 标识（颜色 + 图标）
│       │   │   ├── ThinkingIndicator.tsx # Agent 思考中动画
│       │   │   └── SessionList.tsx     # 对话列表
│       │   │
│       │   ├── experiment/
│       │   │   ├── ExperimentList.tsx  # 实验列表卡片
│       │   │   ├── ExperimentDetail.tsx # 实验详情
│       │   │   ├── CVPlot.tsx         # CV 图表（ECharts）
│       │   │   ├── EISPlot.tsx        # EIS 图表（Nyquist/Bode）
│       │   │   └── PumpTimeline.tsx   # 泵操作时间线
│       │   │
│       │   ├── knowledge/
│       │   │   ├── KnowledgeTree.tsx  # OpenViking 目录树
│       │   │   ├── ResourceCard.tsx   # 资源卡片
│       │   │   └── SearchResults.tsx  # 搜索结果
│       │   │
│       │   └── common/
│       │       ├── MarkdownRenderer.tsx # Markdown 渲染（含 KaTeX）
│       │       ├── CodeBlock.tsx       # 代码块
│       │       └── ErrorBoundary.tsx   # 错误边界
│       │
│       ├── hooks/                 # 自定义 Hooks
│       │   ├── useChat.ts         # 对话逻辑封装
│       │   ├── useWebSocket.ts    # WebSocket 连接 Hook
│       │   └── useExperiment.ts   # 实验数据加载
│       │
│       ├── types/                 # TypeScript 类型定义
│       │   ├── chat.ts            # ChatMessage, ChatResponse, ...
│       │   ├── experiment.ts      # ExperimentRun, ECData, ...
│       │   └── knowledge.ts       # Resource, SearchResult, ...
│       │
│       └── utils/
│           ├── format.ts          # 日期/数字格式化
│           └── echem.ts           # 电化学数据处理辅助
```

---

## 四、核心页面设计

### 4.1 对话页面 (ChatPage)

这是最核心的页面，用户通过自然语言与 Agent 交互。

```
┌─────────────────────────────────────────────────────────┐
│  🧪 AutoHySeeker                   ⚙️ Settings         │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Sessions │  💬 Agent: DiagnosticsExpert                 │
│          │  ─────────────────────────────────────────── │
│ ● 今天   │  👤 帮我诊断今天下午的CV实验为什么电流偏低     │
│ ○ 昨天   │                                              │
│ ○ 2/13  │  🤖 [Diagnostics] ⏳ 正在分析...              │
│          │     ├─ 读取实验数据...                        │
│          │     ├─ 检查泵操作日志...                      │
│          │     └─ 对比历史数据...                        │
│          │                                              │
│          │  🤖 ## 诊断报告                               │
│          │     ### 问题：溶液浓度不足                     │
│          │     根据泵操作记录，Step 3 的注入量             │
│          │     仅为预期的 60%。                           │
│          │                                              │
│          │     [📊 CV对比图]  [📊 泵操作时间线]           │
│          │                                              │
│          │  ──────────────────────────────────────────── │
│          │  [输入消息...]                     [发送 ▶]   │
└──────────┴──────────────────────────────────────────────┘
```

**关键交互**：
- **流式输出**：WebSocket 推送 Agent 思考过程的每个步骤
- **Agent 标识**：不同 Agent 用不同颜色标记（D=红, A=蓝, B=绿, C=橙, E=紫）
- **图表内嵌**：Agent 返回的图表直接在消息中渲染
- **操作按钮**：诊断结果附带"重新实验"、"修改参数"等操作按钮

### 4.2 实验 Dashboard (ExperimentsPage)

```
┌──────────────────────────────────────────────────────────┐
│  📊 实验 Dashboard                                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  日期筛选: [2026-02-13 ▾]  状态: [全部 ▾]               │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ CV_Fe_gradient   │  │ EIS_solution_A   │             │
│  │ 15:30  ✅ 完成    │  │ 16:45  ❌ 失败    │             │
│  │ Steps: 8/8       │  │ Steps: 5/8       │             │
│  │ [查看] [诊断]     │  │ [查看] [诊断]     │             │
│  └──────────────────┘  └──────────────────┘             │
│                                                          │
│  ─── 选中实验：CV_Fe_gradient ──────────────────────────  │
│                                                          │
│  ┌──────────────────────────┐  ┌─────────────────────┐  │
│  │                          │  │ 实验参数             │  │
│  │    [CV 循环伏安图]        │  │ 电极: GCE          │  │
│  │    (ECharts 交互式)      │  │ 扫速: 50 mV/s     │  │
│  │                          │  │ 范围: -0.5~0.8V   │  │
│  └──────────────────────────┘  └─────────────────────┘  │
│                                                          │
│  [💬 让 AI 分析此实验]  [📋 生成报告]  [🔍 对比其他]      │
└──────────────────────────────────────────────────────────┘
```

### 4.3 知识库页面 (KnowledgePage)

```
┌──────────────────────────────────────────────────────────┐
│  📚 知识库 (OpenViking)                                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  🔍 [搜索知识库...]                                       │
│                                                          │
│  ┌─── 目录树 ──────────────┬── 资源详情 ────────────────┐ │
│  │ 📁 viking://            │                            │ │
│  │  ├─📁 resources/       │  📄 CV_basics.pdf          │ │
│  │  │  ├─📁 experiments/  │  Level: L0 (Abstract)      │ │
│  │  │  ├─📁 literature/   │  ──────────────────────     │ │
│  │  │  │  ├─📄 CV_basic..│  循环伏安法是一种常用的     │ │
│  │  │  │  └─📄 EIS_rev.. │  电化学测量方法...           │ │
│  │  │  └─📁 manuals/      │                            │ │
│  │  └─📁 agent/           │  [L1 概览] [L2 全文]       │ │
│  │     ├─📁 shared/       │  [相关资源] [引用图谱]      │ │
│  │     └─📁 memories/     │                            │ │
│  └──────────────────────────┴────────────────────────────┘ │
│                                                          │
│  [+上传文档] [+导入实验数据] [导出 OVPack]                  │
└──────────────────────────────────────────────────────────┘
```

---

## 五、WebSocket 流式通信

### 5.1 连接管理

```typescript
// ws/chatSocket.ts
import ReconnectingWebSocket from "reconnecting-websocket";

class ChatSocket {
  private ws: ReconnectingWebSocket | null = null;
  private listeners: Map<string, ((data: any) => void)[]> = new Map();

  connect(url: string = "ws://localhost:8100/ws/chat") {
    this.ws = new ReconnectingWebSocket(url);
    
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      // msg.type: "on_chain_start" | "on_chain_end" | "on_tool_start" | ...
      // msg.node: "router" | "analyst" | "diagnostics" | ...
      // msg.data: { ... }
      this.emit(msg.type, msg);
    };
  }

  send(message: string, threadId?: string) {
    this.ws?.send(JSON.stringify({ message, thread_id: threadId }));
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) this.listeners.set(event, []);
    this.listeners.get(event)!.push(callback);
  }

  private emit(event: string, data: any) {
    this.listeners.get(event)?.forEach((cb) => cb(data));
    this.listeners.get("*")?.forEach((cb) => cb(data)); // wildcard
  }
}

export const chatSocket = new ChatSocket();
```

### 5.2 useChat Hook

```typescript
// hooks/useChat.ts
import { useEffect, useCallback } from "react";
import { useChatStore } from "../stores/chatStore";
import { chatSocket } from "../ws/chatSocket";

export function useChat() {
  const { messages, addMessage, updateLastMessage, setThinking } = useChatStore();

  useEffect(() => {
    chatSocket.connect();

    chatSocket.on("on_chain_start", (msg) => {
      if (msg.node === "router") {
        setThinking(true, "正在分析您的问题...");
      }
    });

    chatSocket.on("on_tool_start", (msg) => {
      setThinking(true, `正在调用 ${msg.data.tool_name}...`);
    });

    chatSocket.on("on_chain_end", (msg) => {
      if (msg.data?.final_response) {
        setThinking(false);
        addMessage({
          role: "assistant",
          content: msg.data.final_response,
          agent: msg.data.agent_used,
          figures: msg.data.figures || [],
        });
      }
    });

    return () => chatSocket.disconnect();
  }, []);

  const sendMessage = useCallback((text: string) => {
    addMessage({ role: "user", content: text });
    chatSocket.send(text);
  }, []);

  return { messages, sendMessage };
}
```

---

## 六、状态管理

### 6.1 Chat Store

```typescript
// stores/chatStore.ts
import { create } from "zustand";

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  agent?: string;        // "diagnostics" | "analyst" | ...
  figures?: string[];     // 图表 URL
  timestamp: Date;
}

interface ChatState {
  sessions: { id: string; title: string; updatedAt: Date }[];
  currentSessionId: string | null;
  messages: ChatMessage[];
  isThinking: boolean;
  thinkingText: string;
  
  addMessage: (msg: Omit<ChatMessage, "id" | "timestamp">) => void;
  setThinking: (val: boolean, text?: string) => void;
  switchSession: (id: string) => void;
  createSession: () => string;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  isThinking: false,
  thinkingText: "",

  addMessage: (msg) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { ...msg, id: crypto.randomUUID(), timestamp: new Date() },
      ],
    })),

  setThinking: (val, text = "") =>
    set({ isThinking: val, thinkingText: text }),

  switchSession: (id) =>
    set({ currentSessionId: id, messages: [] }), // 从 API 加载

  createSession: () => {
    const id = crypto.randomUUID();
    set((state) => ({
      sessions: [
        { id, title: "新对话", updatedAt: new Date() },
        ...state.sessions,
      ],
      currentSessionId: id,
      messages: [],
    }));
    return id;
  },
}));
```

---

## 七、电化学图表组件

### 7.1 CV 图表

```typescript
// components/experiment/CVPlot.tsx
import ReactECharts from "echarts-for-react";

interface CVPlotProps {
  data: {
    potential: number[];   // V
    current: number[];     // μA
    peaks?: { potential: number; current: number; type: "oxidation" | "reduction" }[];
  };
  title?: string;
}

export function CVPlot({ data, title = "循环伏安图" }: CVPlotProps) {
  const option = {
    title: { text: title },
    tooltip: {
      trigger: "axis",
      formatter: (params: any) =>
        `E = ${params[0].value[0].toFixed(3)} V<br/>I = ${params[0].value[1].toFixed(2)} μA`,
    },
    xAxis: {
      name: "Potential (V vs. Ag/AgCl)",
      nameLocation: "middle",
      nameGap: 30,
    },
    yAxis: {
      name: "Current (μA)",
      nameLocation: "middle",
      nameGap: 50,
    },
    series: [
      {
        type: "line",
        data: data.potential.map((e, i) => [e, data.current[i]]),
        smooth: true,
        lineStyle: { width: 2 },
      },
      // 标注峰值
      ...(data.peaks
        ? [
            {
              type: "scatter",
              data: data.peaks.map((p) => [p.potential, p.current]),
              symbolSize: 12,
              itemStyle: { color: "#ff4d4f" },
              label: {
                show: true,
                formatter: (p: any) =>
                  `${p.value[0].toFixed(3)}V, ${p.value[1].toFixed(1)}μA`,
              },
            },
          ]
        : []),
    ],
    toolbox: {
      feature: {
        dataZoom: {},
        saveAsImage: {},
      },
    },
  };

  return <ReactECharts option={option} style={{ height: 400 }} />;
}
```

### 7.2 EIS Nyquist 图

```typescript
// components/experiment/EISPlot.tsx
export function EISPlot({ data }: { data: { zReal: number[]; zImag: number[] } }) {
  const option = {
    title: { text: "Nyquist Plot" },
    xAxis: { name: "Z' (Ω)", min: 0 },
    yAxis: { name: "-Z'' (Ω)", min: 0, inverse: false },
    series: [
      {
        type: "scatter",
        data: data.zReal.map((r, i) => [r, -data.zImag[i]]),
        symbolSize: 6,
      },
    ],
    tooltip: {
      formatter: (p: any) => `Z' = ${p.value[0].toFixed(1)} Ω<br/>-Z'' = ${p.value[1].toFixed(1)} Ω`,
    },
  };

  return <ReactECharts option={option} style={{ height: 400 }} />;
}
```

---

## 八、API 层

```typescript
// api/client.ts
import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8100/api",
  timeout: 30000,
});

// 统一错误处理
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    console.error("[API Error]", error.response?.data || error.message);
    return Promise.reject(error);
  }
);
```

```typescript
// api/chat.ts
import { apiClient } from "./client";

export interface ChatRequest {
  message: string;
  session_id?: string;
  thread_id?: string;
}

export interface ChatResponse {
  response: string;
  agent_used: string;
  session_id: string;
  figures: string[];
  metadata: Record<string, unknown>;
}

/** 同步对话（非流式 — 用于简单查询） */
export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>("/chat", req);
  return data;
}
```

```typescript
// api/experiments.ts
import { apiClient } from "./client";

export interface ExperimentRun {
  id: string;
  date: string;
  name: string;
  status: "completed" | "failed" | "running";
  steps_total: number;
  steps_completed: number;
}

export async function listExperiments(date?: string, limit = 20): Promise<ExperimentRun[]> {
  const { data } = await apiClient.get("/experiments", { params: { date, limit } });
  return data;
}

export async function getExperiment(runId: string) {
  const { data } = await apiClient.get(`/experiments/${runId}`);
  return data;
}

export async function diagnoseExperiment(runId: string) {
  const { data } = await apiClient.post(`/experiments/${runId}/diagnose`);
  return data;
}
```

---

## 九、前端 ↔ 后端数据流

```
用户输入 "帮我分析今天的CV实验"
     │
     ▼
ChatPage → useChat().sendMessage(text)
     │
     ├─── chatStore.addMessage({ role: "user", ... })   // 立即更新 UI
     │
     └─── chatSocket.send(text)                          // 发送到后端
              │
              ▼
         WS /ws/chat → FastAPI → Orchestrator
              │
         后端流式推送事件 ──────────────────
              │                              │
    "on_chain_start"                   "on_chain_end"
    → setThinking(true, "...")          → setThinking(false)
                                        → addMessage({ role: "assistant", ... })
                                        │
                                        ▼
                                  MessageBubble 渲染：
                                  ├─ MarkdownRenderer → 文本
                                  ├─ CVPlot → ECharts 图表
                                  └─ AgentBadge → Agent 标识
```

---

## 十、开发分阶段计划

### Phase 1（Week 4）— 与后端 Phase 1 同步

```
☐ Vite + React + TypeScript 项目初始化
☐ Ant Design 5 配置（暗色主题）
☐ AppLayout + Sidebar + 路由
☐ ChatPage 基础版（REST 模式，非流式）
☐ api/client.ts + api/chat.ts
☐ chatStore 基础版
☐ MarkdownRenderer（react-markdown + rehype-katex）
☐ AgentBadge 组件
```

### Phase 2（Week 5-6）— 流式 + 实验 Dashboard

```
☐ WebSocket 流式对话
☐ ThinkingIndicator 组件
☐ useChat Hook 完整版
☐ ExperimentsPage 基础版（列表 + 详情）
☐ CVPlot + EISPlot 组件
☐ PumpTimeline 组件
☐ api/experiments.ts
```

### Phase 3（Week 7-9）— 知识库 + 完善

```
☐ KnowledgePage（目录树 + 搜索 + 资源详情）
☐ api/knowledge.ts
☐ 文件上传功能（拖拽入库到 OpenViking）
☐ SessionList（对话历史切换）
☐ SettingsPage（LLM 模型切换、主题设置）
☐ 响应式布局优化
```

### Phase 4（Week 10-12）— 实时控制面板

```
☐ 实时实验状态展示（通过后端 IPC 桥接获取）
☐ 实验控制按钮（启动/停止/暂停 — 通过 Agent）
☐ 自适应实验进度可视化
```

---

## 十一、开发环境搭建

```bash
cd AutoHySeeker/frontend

# 初始化项目
npm create vite@latest . -- --template react-ts

# 安装依赖
npm install antd @ant-design/icons zustand axios react-router-dom \
  echarts echarts-for-react \
  react-markdown rehype-katex remark-math \
  react-syntax-highlighter reconnecting-websocket

# 开发类型
npm install -D @types/react-syntax-highlighter

# 配置: vite.config.ts
# → proxy /api → localhost:8100
# → proxy /ws  → localhost:8100

# 启动
npm run dev   # → localhost:3000
```

### Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8100",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:8100",
        ws: true,
      },
    },
  },
});
```

---

## 十二、与 MicroHySeeker PySide6 的关系

| 功能 | MicroHySeeker (PySide6) | AutoHySeeker Web 前端 |
|---|---|---|
| 硬件控制 | ✅ 直接控制泵/定位器/电化学工作站 | ❌ 不直接控制 |
| 实验编排 | ✅ 程序编辑器 | 🔄 Phase 4 通过 Agent 控制 |
| 数据查看 | ✅ 基础查看 | ✅ 交互式图表 + AI 分析 |
| AI 对话 | ❌ 无 | ✅ 核心功能 |
| 知识管理 | ❌ 无 | ✅ OpenViking 可视化 |
| 日志查看 | ✅ 日志窗口 | ✅ AI 日志分析 |

**两者互补，不替代**。用户的典型工作流：
1. 在 MicroHySeeker 桌面端设计/运行实验
2. 打开浏览器（localhost:3000）让 AI 分析实验结果
3. AI 诊断问题、建议优化方案
4. (Phase 4) AI 直接控制 MicroHySeeker 执行下一轮实验

---

*此文档是 AutoHySeeker Web 前端的完整开发参考。后端 API 定义见 [dev_backend.md](dev_backend.md)。完整文档导航见 [README.md](README.md)。*
