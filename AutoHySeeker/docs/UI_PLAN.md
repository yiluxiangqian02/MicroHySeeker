# AutoHySeeker Web Interface UI Plan

Date: 2026-03-06  
Scope: Review current backend API routes in `src/api/routes/`, design web UI pages/components, and define frontend-backend integration specs for implementation.

## 1. Goals

1. Provide a practical web interface for experiment monitoring, diagnostics, contextual analysis, and next-experiment planning.
2. Use existing backend routes as the integration baseline, while explicitly documenting gaps that block a polished UI.
3. Define concrete page-level and component-level requirements so implementation can start immediately.

## 2. Backend API Route Review

### 2.1 Route Inventory

| Domain | Method | Path | Purpose | Request Shape | Response Shape |
|---|---|---|---|---|---|
| system | GET | `/health` | service health check | none | `{status, service}` |
| tasks | POST | `/tasks/create` | create task record | `{task_type?, payload?}` | `{task_id, status, task_type, payload, created_at}` |
| tasks | GET | `/tasks/{task_id}/status` | fetch one task | path param | task record or 404 |
| data | GET | `/data/experiments` | list recent experiments | `limit` query (1..200, default 10) | `{count, items[]}` |
| data | GET | `/data/latest` | fetch latest experiment with details | none | `{latest, details}` or 404 |
| agents | POST | `/agents/invoke` | invoke orchestrator router + specialist agent | `{task?, context?, messages?, current_agent?}` | `{ok, result, state}` |
| diagnostics | POST | `/diagnostics/invoke` | invoke diagnostics graph (D1 or D2) | `{action, run_dir, data_dir, recent_n, context}` | `{ok, action, result, error}` |
| diagnostics | POST | `/diagnostics/analyze-failure` | shortcut for D1 | query `run_dir` | same as invoke |
| diagnostics | POST | `/diagnostics/check-health` | shortcut for D2 | query `data_dir`, `recent_n` | same as invoke |
| context | POST | `/context/invoke` | invoke context graph C1/C2 | `ContextRequest` body | `{ok, action, result, error}` |
| context | POST | `/context/contextualize` | shortcut for C1 | query `run_dir`, `history_dir`, `threshold_sigma`, `max_history` | same as invoke |
| context | POST | `/context/suggest-next` | shortcut for C2 | query `goal`, `name` | same as invoke |
| settings | GET | `/settings/models/config` | get current LLM model configuration | none | `{version, active_preset, api, presets, custom}` |
| settings | POST | `/settings/models/config` | update LLM model configuration | `{active_preset, custom?}` | `{success: true}` |
| settings | GET | `/settings/models/metadata` | get model metadata (pricing, capabilities) | none | `{models: {[model_id]: ModelMetadata}}` |
| settings | GET | `/settings/models/usage` | get monthly usage statistics | none | `{month, total_cost, budget, agents: [{agent, calls, cost}]}` |
| settings | POST | `/settings/models/test-connection` | test API key validity | `{api_key}` | `{success: boolean, error?: string}` |

### 2.2 Important Contract Details for UI

1. `/data/experiments` uses `limit`, not `n`.
2. `/data/latest` returns full details only for the latest run; there is no route to fetch arbitrary run details by `run_dir`.
3. `/tasks` is in-memory only (`TASK_STORE`), so data resets on API restart.
4. Diagnostics/context shortcut endpoints are query-param based, not JSON-body based.
5. `/agents/invoke` may return heterogeneous `result` payloads depending on routed agent.
6. Error responses are not normalized across routes (HTTPException detail vs. `{ok:false,error:...}` patterns).
7. CORS middleware is not currently configured in `src/api/main.py`.

### 2.3 Known Output Structures Used by UI

1. Diagnostics report (`/diagnostics/invoke` result):  
`{action, total_findings, severity_counts, findings[]}`
2. Contextualize result (`/context/invoke`, `action=contextualize`):  
`{success, data:{comparison, trend, anomalies, literature, knowledge_chunks, n_history, summary}, message}`
3. Suggest-next result (`/context/invoke`, `action=suggest`):  
`{success, data:{intent, rationale, plan, valid}, message}`
4. Agent invoke result (`/agents/invoke`):  
`{agent, model?, content, ok, error?}` (with full graph `state` also returned by route wrapper).

## 3. UX Information Architecture

### 3.1 Top-Level Navigation

1. `Overview`
2. `Experiments`
3. `Context & Planning`
4. `Diagnostics`
5. `Agent Console`
6. `Tasks`
7. `Settings`

### 3.2 Route Map

| Frontend Route | Page | Primary APIs |
|---|---|---|
| `/` | Overview | `/health`, `/data/experiments`, `/data/latest` |
| `/experiments` | Experiments Explorer | `/data/experiments`, `/data/latest`, optional `/context/invoke`, `/diagnostics/invoke` |
| `/context` | Contextualize + Suggest Workflow | `/context/invoke`, `/context/contextualize`, `/context/suggest-next` |
| `/diagnostics` | Failure Analysis + Health Check | `/diagnostics/invoke`, shortcuts |
| `/agents` | Multi-agent Invoke Console | `/agents/invoke` |
| `/tasks` | Task Queue Monitor | `/tasks/create`, `/tasks/{id}/status` |
| `/settings` | API and defaults configuration + LLM model management | `/settings/models/config`, `/settings/models/metadata`, `/settings/models/usage`, `/settings/models/test-connection` |

## 4. Page Specifications

### 4.1 Overview Page (`/`)

Purpose: Immediate system snapshot and latest experiment status.

Required modules:
1. `ServiceHealthCard` (from `/health`)
2. `RecentRunsTable` (from `/data/experiments?limit=10`)
3. `LatestRunDetailCard` (from `/data/latest`)
4. `QuickActionsPanel` (`Contextualize latest`, `Diagnose latest`, `Suggest next`)

States:
1. loading skeleton cards
2. partial load fallback (health available, latest missing)
3. empty experiments state with guidance text
4. error toast + retry action

### 4.2 Experiments Page (`/experiments`)

Purpose: Browse runs, inspect metadata, and trigger analysis actions.

Required modules:
1. `ExperimentFiltersBar` (`limit`, text filter by run name/day)
2. `ExperimentListTable` (`name`, `day`, `csv_count`, `has_echem_dir`, `run_dir`)
3. `ExperimentSidePanel` with selected row summary (from list item)
4. latest details view when selected run equals latest run
5. action buttons:
6. `Contextualize` -> opens prefilled context form
7. `Analyze Failure` -> opens diagnostics form with `run_dir`

Note: full details for non-latest run are blocked by missing backend endpoint.

### 4.3 Context & Planning Page (`/context`)

Purpose: Run C1 contextualization, then C2 suggestion in a guided workflow.

Layout: two-step workflow with persisted intermediate data.

Step 1: Contextualize form
1. `run_dir` (required)
2. `history_dir`
3. `metrics[]`
4. `threshold_sigma`
5. `max_history`
6. optional `previous_results` JSON editor

Step 1 result view:
1. `ContextSummaryBanner` (`success`, `message`, `summary`)
2. `MetricComparisonTable` (`current`, `historical_mean`, `delta`, `z_score`)
3. `TrendChipsRow`
4. `AnomalyList`
5. `KnowledgePanel` (`literature`, `knowledge_chunks`)

Step 2: Suggest-next form
1. consumes stored C1 `data` as `context_data`
2. fields: `goal`, `name`, `description`, `tags[]`

Step 2 result view:
1. `IntentBadge` (`diagnostic_run`, `stability_run`, etc.)
2. `RationaleBlock`
3. `ExperimentPlanViewer`
4. `PlanValidationStatus`
5. `ExportPlanJsonButton`

### 4.4 Diagnostics Page (`/diagnostics`)

Purpose: Diagnose failed runs and run system health checks.

Tabs:
1. `Analyze Failure`
2. `Check Health`

Analyze Failure form:
1. `run_dir` required
2. submit to `/diagnostics/invoke` with `action=analyze_failure`

Check Health form:
1. `data_dir` required
2. `recent_n` (default 10)
3. submit to `/diagnostics/invoke` with `action=check_health`

Result modules:
1. `SeveritySummaryCard` from `severity_counts`
2. `FindingsTable` (`severity/status`, `category/component`, `message`)
3. `EvidenceAccordion` for each finding
4. `RawJsonDrawer`

### 4.5 Agent Console (`/agents`)

Purpose: Power-user playground for direct orchestrator invocation.

Required modules:
1. `AgentInvokeForm`
2. `task` JSON editor
3. `context` JSON editor
4. `messages` JSON editor
5. `current_agent` select (`auto`, `data_analyst`, `exp_designer`, `exp_supervisor`, `diagnostics`, `knowledge_mgr`)
6. `AgentResultPanel` (`agent`, `model`, `content`, `ok/error`)
7. `GraphStateInspector` (expandable `state` object)

### 4.6 Tasks Page (`/tasks`)

Purpose: Track backend task records and validate queue interactions.

Required modules:
1. `CreateTaskForm` (`task_type`, `payload JSON`)
2. `TaskWatchList` (local list of created `task_id`s)
3. `TaskStatusPoller` (poll `/tasks/{id}/status` every 5s)

Note: because tasks are in-memory and currently static (`queued`), the UI should mark this page as "basic queue stub".

### 4.7 Settings Page (`/settings`)

Purpose: Client-side configuration, defaults, and LLM model management.

Tabs:
1. `General` - API and defaults
2. `Models` - LLM model configuration

#### 4.7.1 General Tab

Fields:
1. API base URL (default `http://localhost:8100`)
2. default diagnostics data dir
3. default contextualize history dir
4. default polling interval
5. request timeout

Persistence: `localStorage`.

#### 4.7.2 Models Tab

Purpose: Configure LLM models for each Agent, switch presets, monitor usage and costs.

Required modules:

1. **PresetSelector**
   - Radio buttons: `极致省钱` / `性价比平衡` / `质量优先` / `自定义`
   - Display monthly cost estimate for each preset
   - One-click switch with confirmation dialog

2. **AgentModelConfigCards** (5 cards, one per agent)
   - Card header: Agent name + icon + description
   - Fields per card:
     - Primary model dropdown (with price display)
     - Fallback model dropdown (with price display)
     - Temperature slider (0-1, step 0.1)
     - Max tokens input (number)
   - Model dropdown options from `/settings/models/metadata`
   - Show pricing: `¥X/M input, ¥Y/M output`

3. **APIConfigSection**
   - Shengsuanyun API Base URL (readonly: `https://router.shengsuanyun.com/api/v1`)
   - API Key input (password type, with show/hide toggle)
   - Timeout input (seconds)
   - `Test Connection` button → calls `/settings/models/test-connection`

4. **UsageMonitorPanel**
   - Current month cost: `¥X.XX / Budget: ¥Y.YY`
   - Progress bar visualization
   - Breakdown by agent (table):
     - Agent name
     - Call count
     - Total cost
     - Percentage of budget
   - Data from `/settings/models/usage`

5. **ModelMetadataDrawer** (optional, triggered by info icon)
   - Model full name
   - Provider
   - Context window
   - Capabilities tags
   - Recommended use cases
   - Pricing details

Agent configuration structure:
```typescript
interface AgentConfig {
  name: string;
  display_name: string;
  icon: string;
  description: string;
  model: string;
  fallback: string;
  temperature: number;
  max_tokens: number;
}

const agents: AgentConfig[] = [
  {
    name: "data_analyst",
    display_name: "数据分析",
    icon: "📊",
    description: "CV/EIS 信号解读、不确定性分析",
    model: "zhipu/glm-4.6",
    fallback: "deepseek/deepseek-v3.2",
    temperature: 0.1,
    max_tokens: 2000
  },
  // ... 4 more agents
];
```

States:
1. Loading skeleton for usage stats
2. Unsaved changes warning when switching presets
3. API key validation (show green checkmark or red error)
4. Cost alert when approaching budget (>80%)

Persistence: 
- Model config: backend `/settings/models/config` (POST to save)
- API key: backend (encrypted storage)
- Budget: `localStorage` (client-side preference)

## 5. Reusable Component Catalog

| Component | Responsibility | Inputs | Outputs |
|---|---|---|---|
| `AppShell` | sidebar + topbar layout | nav items, page title | route changes |
| `StatusPill` | show `ok/warning/error/unknown` | status string | none |
| `JsonEditor` | structured JSON entry | initial value, schema hint | validated object |
| `ApiErrorBanner` | consistent error rendering | HTTP status + message | retry event |
| `DataTable` | shared tabular rendering | columns, rows | sort/filter events |
| `MetricDeltaCell` | visual metric delta | `delta`, `z_score` | none |
| `FindingCard` | diagnostics finding display | finding object | expand/collapse |
| `PlanStepTimeline` | render experiment steps | plan steps | step select |
| `RawPayloadDrawer` | show raw request/response | payload | copy event |

## 6. Frontend-Backend Integration Design

### 6.1 Frontend Stack (Implementation Recommendation)

1. React 18 + TypeScript + Vite
2. TanStack Query for server-state fetching/caching
3. Zustand for local UI state (filters, workflow draft, panel state)
4. Axios for API transport
5. React Hook Form + Zod for form validation
6. ECharts for metric/diagnostics visualizations

### 6.2 API Client Layer

Proposed structure:

```text
frontend/src/api/
  client.ts
  health.ts
  tasks.ts
  data.ts
  diagnostics.ts
  context.ts
  agents.ts
  settings.ts
  types.ts
```

`client.ts` requirements:
1. baseURL from settings store
2. timeout (default 30s)
3. typed error normalization:
4. `NetworkError`
5. `HttpError(status, detail)`
6. `ValidationError(422)`

### 6.3 Type Contracts (TypeScript)

```ts
export interface HealthResponse {
  status: "ok";
  service: string;
}

export interface ExperimentListItem {
  run_dir: string;
  day: string;
  name: string;
  has_echem_dir: boolean;
  csv_count: number;
}

export interface ExperimentsResponse {
  count: number;
  items: ExperimentListItem[];
}

export interface DiagnosticsReport {
  action: string;
  total_findings: number;
  severity_counts: Record<string, number>;
  findings: Array<Record<string, unknown>>;
}

export interface ContextSkillResult<T = Record<string, unknown>> {
  success: boolean;
  data: T;
  message: string;
  artifacts: unknown[];
}

export interface ModelMetadata {
  provider: string;
  display_name: string;
  pricing: {
    input: number;
    output: number;
    currency: string;
    unit: string;
  };
  context_window: number;
  capabilities: string[];
  recommended_for: string[];
}

export interface AgentModelConfig {
  model: string;
  fallback: string;
  temperature: number;
  max_tokens: number;
}

export interface ModelConfigResponse {
  version: string;
  active_preset: string;
  api: {
    base_url: string;
    api_key: string;
    timeout: number;
  };
  presets: Record<string, {
    name: string;
    description: string;
    monthly_cost_estimate: string;
    agents: Record<string, AgentModelConfig>;
  }>;
  custom: {
    enabled: boolean;
    agents: Record<string, AgentModelConfig>;
  };
}

export interface UsageStats {
  month: string;
  total_cost: number;
  budget: number;
  agents: Array<{
    agent_name: string;
    call_count: number;
    total_cost: number;
    percentage: number;
  }>;
}
```

### 6.4 Query and Mutation Strategy

1. `useHealthQuery`: staleTime 15s, refetchInterval 30s
2. `useExperimentsQuery(limit)`: staleTime 10s
3. `useLatestExperimentQuery`: staleTime 10s
4. `useInvokeContextMutation`
5. `useInvokeDiagnosticsMutation`
6. `useInvokeAgentMutation`
7. `useCreateTaskMutation`
8. `useTaskStatusQuery(taskId)`: polling 5s when active
9. `useModelConfigQuery`: staleTime 60s
10. `useModelMetadataQuery`: staleTime 300s (5 min, rarely changes)
11. `useUsageStatsQuery`: staleTime 30s, refetchInterval 60s
12. `useUpdateModelConfigMutation`
13. `useTestConnectionMutation`

### 6.5 Error Handling and UX Rules

1. 404 from `/data/latest`: show empty-state card, not fatal page error.
2. 422 validation errors: map field-level messages to form controls.
3. 500 errors: show operation-level banner + expandable raw payload.
4. Mutations must capture and display request/response payload for reproducibility.

### 6.6 Frontend Action -> API Mapping

| UI Action | API Call | Method | Payload Strategy |
|---|---|---|---|
| load dashboard | `/health`, `/data/experiments`, `/data/latest` | GET | parallel queries |
| run contextualize | `/context/invoke` | POST | JSON body with `action=contextualize` |
| run suggest-next | `/context/invoke` | POST | JSON body with `action=suggest` and `context_data` |
| diagnose failure | `/diagnostics/invoke` | POST | JSON body with `action=analyze_failure` |
| check system health | `/diagnostics/invoke` | POST | JSON body with `action=check_health` |
| invoke agent | `/agents/invoke` | POST | JSON body from editors |
| create task | `/tasks/create` | POST | JSON body |
| refresh task status | `/tasks/{task_id}/status` | GET | path param |
| load model config | `/settings/models/config` | GET | none |
| update model config | `/settings/models/config` | POST | JSON body with `active_preset` or `custom` |
| load model metadata | `/settings/models/metadata` | GET | none |
| load usage stats | `/settings/models/usage` | GET | none |
| test API connection | `/settings/models/test-connection` | POST | JSON body with `api_key` |

Integration rule: prefer `/context/invoke` and `/diagnostics/invoke` instead of shortcut endpoints to avoid query-param mismatch and keep payloads typed.

## 7. Visual and Interaction Direction

1. Visual theme: lab-console style, light base with high-contrast status colors.
2. Typography: `IBM Plex Sans` for UI + `IBM Plex Mono` for technical payloads.
3. Motion:
4. staggered card reveal on page load
5. step transition animation in context workflow
6. severity-count bars animate on diagnostics result update
7. Status color map:
8. ok `#1f8a4d`
9. warning `#b7791f`
10. error `#c53030`
11. unknown/info `#4a5568`

## 8. Backend Gaps and Required Follow-ups

### 8.1 P0 (Should add for production UI)

1. Add CORS middleware in API app.
2. Add `GET /data/run-details?run_dir=...` for non-latest run detail retrieval.
3. Normalize error envelope shape across all routes.
4. Add `GET /tasks` list endpoint for task dashboard bootstrap.
5. **Add `/settings/models/*` endpoints for LLM model configuration:**
   - `GET /settings/models/config` - get current model config
   - `POST /settings/models/config` - update model config
   - `GET /settings/models/metadata` - get model metadata (pricing, capabilities)
   - `GET /settings/models/usage` - get monthly usage statistics
   - `POST /settings/models/test-connection` - test API key validity
6. **Create backend config files:**
   - `configs/llm_models.json` - model configuration with presets
   - `configs/model_metadata.json` - model metadata (pricing, capabilities)
7. **Add usage tracking:**
   - SQLite table `llm_usage` for tracking API calls
   - Middleware to log token usage and costs
   - Monthly aggregation queries

### 8.2 P1 (Improves UX significantly)

1. Add streaming endpoint (SSE/WebSocket) for agent invocation progress.
2. Persist task store (sqlite/redis) instead of in-memory dict.
3. Add pagination and sorting controls to `/data/experiments`.

## 9. Delivery Plan

### Phase 1: Foundation (2-3 days)
1. scaffold frontend project, app shell, settings store, API client
2. implement Overview + basic Experiments list
3. wire health/data endpoints

### Phase 2: Analysis Workflows (3-4 days)
1. implement Context workflow page
2. implement Diagnostics page with report rendering
3. add shared JSON editor and result inspector components

### Phase 3: Expert Tools and Hardening (2-3 days)
1. implement Agent Console and Tasks page
2. add robust error handling, retry, and request logs
3. add integration tests with mocked API responses

### Phase 4: Settings and Model Management (2-3 days)
1. implement Settings page General tab
2. implement Settings page Models tab with:
   - Preset selector
   - Agent model config cards
   - API config section
   - Usage monitor panel
3. wire `/settings/models/*` endpoints

### Phase 5: Backend Alignment (parallel)
1. deliver P0 backend endpoints/middleware
2. implement `/settings/models/*` routes
3. create config files and usage tracking
4. update UI to consume new run-details and task-list routes

## 10. Acceptance Criteria

1. User can view service health and recent experiments on landing page.
2. User can run contextualization and suggestion end-to-end from UI, with result interpretation components populated.
3. User can run both diagnostics modes and inspect findings/evidence.
4. User can invoke arbitrary agent tasks and inspect routed result/state.
5. UI handles 404/422/500 responses without blank pages or crashes.
6. All API integrations are typed and covered by component/integration tests.
7. **User can configure LLM models for each Agent:**
   - Switch between presets (极致省钱/性价比平衡/质量优先)
   - Customize individual agent models
   - View real-time pricing information
   - Test API key validity
8. **User can monitor LLM usage and costs:**
   - View monthly total cost and budget progress
   - See per-agent breakdown of calls and costs
   - Receive alerts when approaching budget limit
