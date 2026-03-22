# AutoHySeeker 前端修改指南

> 最后更新：2026-03-22
> 基于对现有代码的完整审计，精确标注每个文件/模块的当前状态。
> 分类：✅ 已完成 | 🔧 需调整 | 🆕 待新增

---

## 一、技术栈确认

| 层面 | 当前选型 | 状态 |
|------|---------|------|
| 框架 | React 18 + TypeScript | ✅ 保留 |
| 构建 | Vite 5 + SWC | ✅ 保留 |
| 路由 | react-router-dom 6 | ✅ 保留 |
| 状态 | zustand 5 | ✅ 保留 |
| 异步 | @tanstack/react-query 5 | ✅ 保留（当前未充分使用，需推广） |
| 表单 | react-hook-form + zod | ✅ 保留 |
| 样式 | Tailwind CSS 3 | ✅ 保留 |
| 图表 | recharts 3 | ✅ 保留 |
| 动画 | framer-motion 12 | ✅ 保留 |
| HTTP | axios（api/client.ts） | ✅ 保留 |
| i18n | react-i18next | ✅ 保留 |
| 图标 | lucide-react | ✅ 保留 |
| Toast | react-hot-toast | ✅ 保留 |

**结论：不需要引入新依赖，现有技术栈完全够用。**

---

## 二、项目结构总览

```
frontend/src/
├── api/              # HTTP 客户端 & 接口封装
├── components/       # 可复用组件
├── hooks/            # 自定义 hooks
├── i18n/             # 国际化
├── pages/            # 页面组件
├── stores/           # zustand stores
├── App.tsx           # 路由 + 布局
├── main.tsx          # 入口
└── index.css         # Tailwind 入口
```

---

## 三、逐文件处置清单

### 3.1 入口 & 配置

| 文件 | 处置 | 说明 |
|------|------|------|
| `main.tsx` | ✅ 保留 | QueryClientProvider + i18n + Router 初始化，结构正确 |
| `App.tsx` | 🔧 调整 | 需要添加新路由（优化循环页、知识库页等），侧边栏菜单项需同步更新 |
| `index.css` | ✅ 保留 | Tailwind directives + 少量自定义样式 |
| `vite.config.ts` | ✅ 保留 | proxy 到 localhost:8100，路径别名 @/ |
| `tailwind.config.js` | ✅ 保留 | |
| `tsconfig.json` | ✅ 保留 | |

### 3.2 API 层 (`src/api/`)

| 文件 | 状态 | 说明 |
|------|------|------|
| `client.ts` | ✅ 已完成 | axios 实例 + 拦截器，从 settingsStore 读 baseURL |
| `types.ts` | ✅ 已完成 | 类型定义 |
| `health.ts` | ✅ 已完成 | GET /api/health |
| `dashboard.ts` | ✅ 已完成 | Dashboard 数据查询 |
| `agents.ts` | ✅ 已完成 | Agent CRUD + 状态查询 |
| `tasks.ts` | ✅ 已完成 | 任务列表查询 |
| `diagnostics.ts` | ✅ 已完成 | 诊断数据查询 |
| `data.ts` | ✅ 已完成 | 数据查询 |
| `context.ts` | ✅ 已完成 | 上下文历史查询 |
| `optimization.ts` | ✅ 已完成 | 优化循环 API 封装 |
| `knowledge.ts` | ✅ 已完成 | 知识库 API（已接入真实后端） |
| `chat.ts` | ✅ 已完成 | Chat API 封装 |
| `monitor.ts` | ✅ 已完成 | 监控 API（已接入真实后端） |
| `experiments.ts` | ✅ 已完成 | 实验管理 API |

### 3.3 Stores (`src/stores/`)

| 文件 | 状态 | 说明 |
|------|------|------|
| `settingsStore.ts` | ✅ 已完成 | 通用设置，persist 到 localStorage |
| `agentStore.ts` | ✅ 已完成 | Agent 配置（纯本地 store，无 API 调用） |
| `optimizationStore.ts` | 🔧 **需改：接真实 API** | 全是 MOCK 数据，真实 API 调用已注释（见任务 W-02） |
| `chatStore.ts` | 🔧 **需改：接真实 API** | 全是 MOCK 数据，需调用 POST /api/chat（见任务 W-01） |

### 3.4 Hooks (`src/hooks/`)

| 文件 | 状态 | 说明 |
|------|------|------|
| `usePolling.ts` | ✅ 已完成 | 通用轮询 hook |

### 3.5 Components (`src/components/`)

| 文件 | 状态 | 说明 |
|------|------|------|
| `AppShell.tsx` | ✅ 已完成 | 响应式布局 + 移动端汉堡菜单 + Toaster |
| `Sidebar.tsx` | ✅ 已完成 | 导航菜单（含 Overview/Dashboard/Experiments/Optimization/Chat/Diagnostics/Agents/Knowledge/Templates/Settings） |
| `AgentCard.tsx` | ✅ 已完成 | Agent 状态卡片 |
| `ApiKeyInput.tsx` | ✅ 已完成 | 密码输入 |
| `ModelSelector.tsx` | ✅ 已完成 | 模型下拉选择器 |
| `TemplateCard.tsx` | ✅ 已完成 | 模板卡片 |
| `TemplateDialog.tsx` | ✅ 已完成 | 模板对话框 |
| `StatusBadge.tsx` | ✅ 已完成 | 状态徽章 |
| `dashboard/*` | ✅ 已完成 | OptimizationStatusCard、RecentExperimentsCard、SystemNotificationsCard |
| `chat/*` | ✅ 已完成 | ChatSidebar、ChatInput、ChatMessage（含 Markdown 渲染） |

### 3.6 Pages (`src/pages/`)

| 文件 | 状态 | 说明 |
|------|------|------|
| `Dashboard.tsx` | 🔧 需调整 | 状态卡片使用 mock 数据，需接入 optimizationStore 真实数据（任务 W-04） |
| `Experiments.tsx` | ✅ 已完成 | 实验列表，已迁移到 react-query |
| `ExperimentDetail.tsx` | ✅ 已完成 | 实验详情，已接入 Agent 响应 |
| `Templates.tsx` | ✅ 已完成 | 模板管理 |
| `Settings.tsx` | ✅ 已完成 | 4 Tab 设置页 |
| `Optimization.tsx` | ✅ 已完成 | 三栏布局 + 收敛曲线，**但 store 使用 mock 数据**（任务 W-02） |
| `Chat.tsx` | ✅ 已完成 | 对话界面 + Markdown 渲染，**但 store 使用 mock 数据**（任务 W-01） |
| `KnowledgeHub.tsx` | ✅ 已完成 | 知识库搜索，API 已接真实后端（需端到端验证，任务 W-03） |
| `Diagnostics.tsx` | ✅ 已完成 | 诊断监控，已接入真实 API（react-query 轮询） |
| `Overview.tsx` | ✅ 已完成 | 系统总览页 |

### 3.7 i18n (`src/locales/`)

| 文件 | 状态 | 说明 |
|------|------|------|
| `i18n/index.ts` | ✅ 已完成 | i18next 初始化 |
| `locales/zh-CN.json` | ✅ 已完成 | 含全部页面翻译 key（约 200+ 条目） |
| `locales/en-US.json` | ✅ 已完成 | 同上 |

---

## 四、当前路由结构（已实现）

```tsx
<Route path="/" element={<Overview />} />
<Route path="/dashboard" element={<Dashboard />} />
<Route path="/experiments" element={<Experiments />} />
<Route path="/experiments/:id" element={<ExperimentDetail />} />
<Route path="/optimization" element={<Optimization />} />
<Route path="/chat" element={<Chat />} />
<Route path="/diagnostics" element={<Diagnostics />} />
<Route path="/agents" element={<AgentControl />} />
<Route path="/knowledge" element={<KnowledgeHub />} />
<Route path="/templates" element={<Templates />} />
<Route path="/settings" element={<Settings />} />
```

---

## 五、当前待完成工作

> 所有页面 UI 已实现，以下是前端-后端对接的收尾工作。
> 详见 `PROGRESS_TRACKER.md` 中 W-01 ~ W-04 任务。

| 任务 | 文件 | 说明 |
|------|------|------|
| **W-01** Chat Store 接真实 API | `stores/chatStore.ts` | 移除 MOCK 数据，调用 POST /api/chat |
| **W-02** Optimization Store 接真实 API | `stores/optimizationStore.ts` | 取消注释真实 API 调用，移除 MOCK |
| **W-03** Knowledge 页面验证 | `pages/KnowledgeHub.tsx` | API 已接入，需端到端验证 |
| **W-04** Dashboard 接真实数据 | `pages/Dashboard.tsx` | 状态卡片改用 optimizationStore 数据 |

---

## 六、关键原则

1. **不重写已有代码** — 核心逻辑保持不变
2. **统一风格** — 沿用 Tailwind 类名风格（rounded-2xl border-slate-200 shadow-sm）
3. **统一状态管理** — zustand + persist 模式
4. **统一 API 调用** — 通过 api/client.ts 的 axios 实例
5. **react-query 优先** — 新的数据获取使用 @tanstack/react-query
