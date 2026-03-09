# AutoHySeeker Web UI 开发任务

## 背景

基于 `AutoHySeeker/UI_PLAN.md` 的详细规划，开发 React + TypeScript 前端界面。

## 技术栈

- **框架**：React 18 + TypeScript + Vite
- **状态管理**：TanStack Query (服务端状态) + Zustand (本地 UI 状态)
- **HTTP 客户端**：Axios
- **表单**：React Hook Form + Zod
- **UI 组件库**：Ant Design 或 shadcn/ui（推荐 shadcn/ui，更轻量）
- **图表**：ECharts 或 Recharts
- **样式**：Tailwind CSS

## 项目结构

```
AutoHySeeker/frontend/
├── src/
│   ├── api/                    # API 客户端层
│   │   ├── client.ts           # Axios 实例 + 错误处理
│   │   ├── health.ts
│   │   ├── tasks.ts
│   │   ├── data.ts
│   │   ├── diagnostics.ts
│   │   ├── context.ts
│   │   ├── agents.ts
│   │   └── types.ts            # TypeScript 类型定义
│   ├── components/             # 可复用组件
│   │   ├── AppShell.tsx
│   │   ├── StatusPill.tsx
│   │   ├── JsonEditor.tsx
│   │   ├── ApiErrorBanner.tsx
│   │   ├── DataTable.tsx
│   │   └── ...
│   ├── pages/                  # 页面组件
│   │   ├── Overview.tsx
│   │   ├── Experiments.tsx
│   │   ├── Context.tsx
│   │   ├── Diagnostics.tsx
│   │   ├── Agents.tsx
│   │   ├── Tasks.tsx
│   │   └── Settings.tsx
│   ├── hooks/                  # 自定义 Hooks
│   │   ├── useHealthQuery.ts
│   │   ├── useExperimentsQuery.ts
│   │   └── ...
│   ├── stores/                 # Zustand stores
│   │   ├── settingsStore.ts
│   │   └── uiStore.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── router.tsx
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## 页面实现优先级

### Phase 1：基础框架 + Overview（1-2天）
1. 项目脚手架（Vite + React + TypeScript）
2. API 客户端层（`src/api/`）
3. AppShell 布局（侧边栏导航 + 顶栏）
4. Overview 页面（健康检查 + 最近实验列表 + 最新实验详情）
5. Settings 页面（API base URL 配置）

### Phase 2：实验浏览 + 诊断（2-3天）
1. Experiments 页面（实验列表 + 过滤 + 详情面板）
2. Diagnostics 页面（失败分析 + 健康检查）
3. 共享组件（DataTable, StatusPill, ApiErrorBanner）

### Phase 3：上下文分析 + Agent 控制台（2-3天）
1. Context 页面（两步工作流：Contextualize → Suggest）
2. Agents 页面（Agent 调用控制台）
3. Tasks 页面（任务队列监控）

## API 集成规范

### 基础配置

```typescript
// src/api/client.ts
import axios from 'axios';
import { useSettingsStore } from '@/stores/settingsStore';

export const apiClient = axios.create({
  baseURL: useSettingsStore.getState().apiBaseUrl || 'http://localhost:8100',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 错误拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNREFUSED') {
      throw new NetworkError('AutoHySeeker API 不可达');
    }
    if (error.response?.status === 422) {
      throw new ValidationError(error.response.data.detail);
    }
    throw new HttpError(error.response?.status, error.response?.data?.detail);
  }
);
```

### TanStack Query 配置

```typescript
// src/hooks/useHealthQuery.ts
import { useQuery } from '@tanstack/react-query';
import { healthApi } from '@/api/health';

export const useHealthQuery = () => {
  return useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    staleTime: 15000,
    refetchInterval: 30000,
  });
};
```

## 关键组件设计

### 1. AppShell（应用外壳）

```tsx
// src/components/AppShell.tsx
export const AppShell = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Topbar />
        <main className="flex-1 overflow-auto p-6 bg-gray-50">
          {children}
        </main>
      </div>
    </div>
  );
};
```

### 2. Overview 页面

```tsx
// src/pages/Overview.tsx
export const Overview = () => {
  const { data: health } = useHealthQuery();
  const { data: experiments } = useExperimentsQuery({ limit: 10 });
  const { data: latest } = useLatestExperimentQuery();

  return (
    <div className="space-y-6">
      <ServiceHealthCard health={health} />
      <RecentRunsTable experiments={experiments?.items} />
      <LatestRunDetailCard latest={latest} />
      <QuickActionsPanel />
    </div>
  );
};
```

### 3. Diagnostics 页面

```tsx
// src/pages/Diagnostics.tsx
export const Diagnostics = () => {
  const [activeTab, setActiveTab] = useState<'failure' | 'health'>('failure');
  const diagnoseMutation = useInvokeDiagnosticsMutation();

  const handleAnalyzeFailure = (runDir: string) => {
    diagnoseMutation.mutate({
      action: 'analyze_failure',
      run_dir: runDir,
    });
  };

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab}>
      <TabsList>
        <TabsTrigger value="failure">失败分析</TabsTrigger>
        <TabsTrigger value="health">健康检查</TabsTrigger>
      </TabsList>
      <TabsContent value="failure">
        <AnalyzeFailureForm onSubmit={handleAnalyzeFailure} />
        {diagnoseMutation.data && (
          <DiagnosticsReport report={diagnoseMutation.data.result} />
        )}
      </TabsContent>
      <TabsContent value="health">
        <CheckHealthForm />
      </TabsContent>
    </Tabs>
  );
};
```

## 样式规范

### 颜色系统

```css
/* tailwind.config.js */
module.exports = {
  theme: {
    extend: {
      colors: {
        status: {
          ok: '#1f8a4d',
          warning: '#b7791f',
          error: '#c53030',
          unknown: '#4a5568',
        },
      },
    },
  },
};
```

### 字体

- UI 文本：`font-sans`（系统默认）
- 代码/技术内容：`font-mono`（IBM Plex Mono 或 JetBrains Mono）

## 任务输出要求

生成完整的前端项目，包括：

1. **项目配置文件**：
   - `package.json`（依赖清单）
   - `vite.config.ts`
   - `tsconfig.json`
   - `tailwind.config.js`

2. **API 客户端层**（`src/api/`）：
   - `client.ts` — Axios 实例 + 错误处理
   - `health.ts` — 健康检查 API
   - `data.ts` — 实验数据 API
   - `diagnostics.ts` — 诊断 API
   - `context.ts` — 上下文分析 API
   - `agents.ts` — Agent 调用 API
   - `tasks.ts` — 任务队列 API
   - `types.ts` — TypeScript 类型定义

3. **核心组件**（`src/components/`）：
   - `AppShell.tsx`
   - `Sidebar.tsx`
   - `Topbar.tsx`
   - `StatusPill.tsx`
   - `DataTable.tsx`
   - `ApiErrorBanner.tsx`
   - `JsonEditor.tsx`

4. **页面组件**（`src/pages/`）：
   - `Overview.tsx` — 仪表盘
   - `Experiments.tsx` — 实验浏览器
   - `Diagnostics.tsx` — 诊断工具
   - `Context.tsx` — 上下文分析工作流
   - `Agents.tsx` — Agent 控制台
   - `Tasks.tsx` — 任务监控
   - `Settings.tsx` — 设置页面

5. **路由配置**（`src/router.tsx`）

6. **入口文件**（`src/main.tsx`, `src/App.tsx`）

## 技术约束

- **Node.js**：v18+
- **包管理器**：pnpm（推荐）或 npm
- **TypeScript**：严格模式
- **代码风格**：ESLint + Prettier
- **浏览器兼容**：现代浏览器（Chrome/Edge/Firefox 最新版）

## 参考文档

- `AutoHySeeker/UI_PLAN.md` — 完整 UI 规划
- `AutoHySeeker/src/api/routes/` — 后端 API 路由实现
- `AutoHySeeker/VALIDATION.md` — 后端功能清单

---

**注意**：
1. 所有 API 调用需要处理 AutoHySeeker 后端不可达的情况
2. 表单验证使用 Zod schema
3. 所有异步操作显示 loading 状态
4. 错误信息需要用户友好（不直接显示技术错误栈）
