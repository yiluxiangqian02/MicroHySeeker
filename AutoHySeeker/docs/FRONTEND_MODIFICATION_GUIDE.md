# AutoHySeeker 前端修改指南

> 基于对现有代码的完整审计，精确标注每个文件/模块的处置方式。
> 分类：✅ 保留 | 🔧 调整 | 🔄 重构 | 🆕 新增 | ❌ 删除

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

| 文件 | 处置 | 说明 |
|------|------|------|
| `client.ts` | ✅ 保留 | axios 实例 + 拦截器，从 settingsStore 读 baseURL |
| `types.ts` | 🔧 调整 | 需补充优化循环、知识库等新接口的类型定义 |
| `health.ts` | ✅ 保留 | GET /api/health |
| `dashboard.ts` | 🔧 调整 | 当前只有 fetchDashboardStats，需补充优化循环状态查询 |
| `agents.ts` | ✅ 保留 | Agent CRUD + 状态查询 |
| `tasks.ts` | ✅ 保留 | 任务列表查询 |
| `diagnostics.ts` | ✅ 保留 | 诊断数据查询 |
| `data.ts` | ✅ 保留 | 数据查询 |
| `context.ts` | ✅ 保留 | 上下文历史查询 |
| 🆕 `optimization.ts` | 🆕 新增 | 优化循环 API：启动/停止/状态/历史 |
| 🆕 `knowledge.ts` | 🆕 新增 | 知识库 API：搜索/上传/标签 |
| 🆕 `chat.ts` | 🆕 新增 | Chat API：发送消息/获取历史/流式响应 |

### 3.3 Stores (`src/stores/`)

| 文件 | 处置 | 说明 |
|------|------|------|
| `settingsStore.ts` | ✅ 保留 | 通用设置，persist 到 localStorage |
| `agentStore.ts` | ✅ 保留 | 7 个 Agent 配置（模型/API Key/启用），结构完善 |
| 🆕 `optimizationStore.ts` | 🆕 新增 | 优化循环运行状态、当前轮次、历史记录 |
| 🆕 `chatStore.ts` | 🆕 新增 | Chat 消息列表、当前会话、流式状态 |

### 3.4 Hooks (`src/hooks/`)

| 文件 | 处置 | 说明 |
|------|------|------|
| `usePolling.ts` | ✅ 保留 | 通用轮询 hook，已被 Dashboard 使用 |
| 🆕 `useOptimizationStatus.ts` | 🆕 新增 | 封装优化循环状态轮询 |
| 🆕 `useStreamChat.ts` | 🆕 新增 | SSE/WebSocket 流式 Chat hook |

### 3.5 Components (`src/components/`)

| 文件 | 处置 | 说明 |
|------|------|------|
| `AgentCard.tsx` | ✅ 保留 | Agent 状态卡片，Dashboard 使用 |
| `ApiKeyInput.tsx` | ✅ 保留 | 密码输入 + 显示/隐藏 |
| `ModelSelector.tsx` | ✅ 保留 | 模型下拉选择器 |
| `TemplateCard.tsx` | ✅ 保留 | 模板卡片 |
| `TemplateDialog.tsx` | ✅ 保留 | 模板创建/编辑对话框 |
| `StatusBadge.tsx` | ✅ 保留 | 状态徽章 |
| 🆕 `OptimizationPanel.tsx` | 🆕 新增 | 优化循环控制面板（启动/停止/参数配置） |
| 🆕 `OptimizationTimeline.tsx` | 🆕 新增 | 优化循环轮次时间线 |
| 🆕 `ChatPanel.tsx` | 🆕 新增 | Agent Chat 面板（消息列表 + 输入框 + 流式显示） |
| 🆕 `ChatMessage.tsx` | 🆕 新增 | 单条 Chat 消息（支持 Markdown 渲染） |
| 🆕 `KnowledgeSearchBar.tsx` | 🆕 新增 | 知识库搜索输入 + 结果列表 |
| 🆕 `ExperimentCompare.tsx` | 🆕 新增 | 实验对比视图（多曲线叠加） |
| 🆕 `StepEditor.tsx` | 🆕 新增 | 实验步骤编辑器（拖拽排序 + 参数表单） |

### 3.6 Pages (`src/pages/`)

| 文件 | 处置 | 说明 |
|------|------|------|
| `Dashboard.tsx` | 🔧 调整 | 需增加优化循环状态卡片、最近实验快捷入口 |
| `Experiments.tsx` | 🔧 调整 | 列表页基本完善，需补充筛选/排序/批量操作 |
| `ExperimentDetail.tsx` | 🔧 调整 | 已有完整的工作页框架，需接入真实 Agent 响应和实时数据刷新 |
| `Templates.tsx` | ✅ 保留 | 模板管理页，结构完整 |
| `Settings.tsx` | ✅ 保留 | 4 Tab 设置页（通用/Agent/界面/通知），功能完善 |
| 🆕 `Optimization.tsx` | 🆕 新增 | 优化循环主页：配置 → 运行 → 结果三阶段视图 |
| 🆕 `OptimizationDetail.tsx` | 🆕 新增 | 单次优化循环详情：每轮实验 + 参数演化 + 收敛曲线 |
| 🆕 `Knowledge.tsx` | 🆕 新增 | 知识库浏览/搜索/上传页 |
| 🆕 `Chat.tsx` | 🆕 新增 | Agent Chat 页面（独立全屏 Chat 或嵌入侧边栏） |
| 🆕 `Diagnostics.tsx` | 🆕 新增 | 诊断专家页面（设备状态 + 故障排查） |

### 3.7 i18n (`src/i18n/`)

| 文件 | 处置 | 说明 |
|------|------|------|
| `index.ts` | ✅ 保留 | i18next 初始化 |
| `zh-CN.json` | 🔧 调整 | 需补充新页面的翻译 key |
| `en-US.json` | 🔧 调整 | 同上 |

---

## 四、App.tsx 路由修改方案

当前路由：
```tsx
// 已有
<Route path="/" element={<Dashboard />} />
<Route path="/experiments" element={<Experiments />} />
<Route path="/experiments/:id" element={<ExperimentDetail />} />
<Route path="/templates" element={<Templates />} />
<Route path="/settings" element={<Settings />} />
```

需新增：
```tsx
// 新增路由
<Route path="/optimization" element={<Optimization />} />
<Route path="/optimization/:id" element={<OptimizationDetail />} />
<Route path="/knowledge" element={<Knowledge />} />
<Route path="/chat" element={<Chat />} />
<Route path="/diagnostics" element={<Diagnostics />} />
```

侧边栏菜单项需同步添加：优化循环、知识库、Chat、诊断。

---

## 五、各页面详细修改说明

### 5.1 Dashboard.tsx — 🔧 调整

**当前状态：** 已有 Agent 状态卡片网格 + 系统健康检查 + 最近任务列表。使用 usePolling 轮询 /api/health。

**需要调整：**
1. 顶部增加「优化循环状态」摘要卡片（当前是否有运行中的循环、进度百分比）
2. 增加「最近实验」快捷入口（最近 3 个实验的 name + status + 点击跳转）
3. Agent 卡片区域保持不变，但需要从后端拉取真实状态（当前是静态 mock）
4. 底部增加「系统通知」区域（最近的错误/警告）

**不需要改的：**
- AgentCard 组件本身
- usePolling hook
- 整体布局结构（grid layout）

### 5.2 Experiments.tsx — 🔧 调整

**当前状态：** 实验列表 + 创建对话框 + 搜索/标签筛选。使用 fetch 直接调用 /api/experiments。

**需要调整：**
1. 将 fetch 替换为 react-query 的 useQuery（统一异步管理）
2. 增加排序功能（按时间/状态/名称）
3. 增加批量操作（批量删除/批量导出）
4. 创建实验对话框需要支持从模板创建（当前只有空白创建）

**不需要改的：**
- 列表卡片的视觉样式
- 搜索/标签筛选逻辑
- 路由跳转到 ExperimentDetail

### 5.3 ExperimentDetail.tsx — 🔧 调整

**当前状态：** 最完善的页面。已有：实验目标推断、状态时间线、步骤链展示、结果摘要、AI 解读占位、下一步建议、数据图表（recharts）。

**需要调整：**
1. AI 解读区域：从占位文本改为真实调用后端 `/api/chat` 接口，展示 Agent 分析结果
2. 「数据处理/分析助手」和「知识管理/知识库 Chat」按钮：点击后跳转到 Chat 页面并携带当前实验上下文
3. 数据图表：增加实时刷新（running 状态时轮询 /api/experiments/detail/:id/data）
4. 步骤链：增加当前执行到哪一步的高亮标记（需后端返回 current_step_index）

**不需要改的：**
- STATUS_CONFIG / STEP_TYPE_META 常量
- inferGoal / buildResultSummary / buildNextActions 等辅助函数
- 整体三栏布局
- 步骤参数展示逻辑（summarizeStep / getStepKeyFacts）

### 5.4 Settings.tsx — ✅ 保留

**当前状态：** 4 Tab 完整设置页。通用设置用 react-hook-form + zod 验证。Agent 配置支持导入/导出/重置。界面设置支持主题/语言/字号/紧凑模式。通知设置支持桌面通知/实验完成/错误告警。

**不需要改。** 这是目前最完善的页面，代码质量高。

### 5.5 Templates.tsx — ✅ 保留

**当前状态：** 模板列表 + 搜索/标签筛选 + 创建对话框。

**不需要改。** 后续如果需要「从模板创建实验」的功能，改动在 Experiments.tsx 的创建对话框里，不在这里。

---

## 六、新增页面设计要点

### 6.1 🆕 Optimization.tsx — 优化循环主页

**功能：**
- 配置优化目标（目标函数、参数空间、约束条件）
- 启动/停止优化循环
- 实时显示当前轮次、最优结果、收敛趋势
- 历史优化记录列表

**对应后端：** `/api/optimization/*` 路由组

**布局参考：** 类似 ExperimentDetail 的三栏布局
- 左栏：优化配置 + 参数空间
- 中栏：收敛曲线 + 当前轮次详情
- 右栏：最优结果 + 下一步建议

### 6.2 🆕 Knowledge.tsx — 知识库页

**功能：**
- 搜索知识库（全文检索 + 向量检索）
- 浏览知识条目（按标签/类型分类）
- 上传新知识（文档/实验记录/笔记）
- 知识条目详情查看

**对应后端：** `/api/knowledge/*`（待建）

### 6.3 🆕 Chat.tsx — Agent Chat 页

**功能：**
- 与 Agent 对话（支持流式响应）
- 可携带实验上下文进入（从 ExperimentDetail 跳转）
- 消息历史
- 支持选择不同 Agent（数据分析师/知识管理/诊断专家）

**对应后端：** `/api/chat/*` 路由组

### 6.4 🆕 Diagnostics.tsx — 诊断页

**功能：**
- 设备连接状态
- 实时诊断数据展示
- 故障排查向导
- 历史诊断记录

**对应后端：** `/api/diagnostics/*` 路由组（已有部分）

---

## 七、实施优先级

| 优先级 | 任务 | 依赖 |
|--------|------|------|
| P0 | App.tsx 添加新路由 + 侧边栏菜单 | 无 |
| P0 | Dashboard.tsx 增加优化循环状态卡片 | optimization API |
| P1 | Optimization.tsx 新页面 | optimization API + store |
| P1 | ExperimentDetail.tsx 接入真实 Agent 响应 | chat API |
| P1 | Chat.tsx 新页面 | chat API + store |
| P2 | Knowledge.tsx 新页面 | knowledge API（待建） |
| P2 | Diagnostics.tsx 新页面 | diagnostics API（已有部分） |
| P2 | Experiments.tsx 改用 react-query | 无 |
| P3 | i18n 补充新页面翻译 | 新页面完成后 |

---

## 八、关键原则

1. **不重写已有代码** — Settings、Templates、ExperimentDetail 的核心逻辑保持不变
2. **增量添加** — 新功能通过新文件 + App.tsx 路由注册的方式加入
3. **统一风格** — 新组件沿用现有的 Tailwind 类名风格（rounded-2xl border-slate-200 shadow-sm）
4. **统一状态管理** — 新 store 沿用 zustand + persist 模式
5. **统一 API 调用** — 新接口沿用 api/client.ts 的 axios 实例
6. **逐步迁移 fetch → react-query** — 不一次性重构，优先在新页面使用 useQuery，旧页面按需迁移
