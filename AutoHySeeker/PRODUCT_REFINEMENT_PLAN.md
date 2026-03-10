# AutoHySeeker 产品完善计划 - 2026-03-10

## 测试发现的问题

### P0 - 严重 Bug（必须立即修复）

1. **Settings 页面无限循环未解决** ❌
   - 现象：点击设置仍然报 "Maximum update depth exceeded"
   - 原因：可能是其他 store 或组件触发了无限循环
   - 修复：彻底排查所有 useEffect 和 store 订阅

2. **实验监控连接错误** ❌
   - 现象：显示 "Connection error: AutoHySeeker API is unreachable"
   - 原因：API 路由或 CORS 配置问题
   - 修复：检查 `/api/v1/experiments` 路由是否正确注册

3. **创建实验缺少泵控制参数** ❌
   - 现象：只有电化学参数，没有泵、溶液配制、冲洗等步骤
   - 原因：没有参考 MicroHySeeker 的完整实验格式
   - 修复：按照 `last_experiment.json` 格式重新设计，支持多步骤实验

4. **分享最近实验无法选择** ❌
   - 现象：不能选择具体的实验
   - 原因：UI 未实现选择功能
   - 修复：添加实验列表选择器

5. **数据加载路径未定义** ❌
   - 现象：不清楚从哪里加载实验数据
   - 原因：数据路径配置缺失
   - 修复：定义数据目录结构和加载逻辑

### P1 - 功能缺失（影响产品完整性）

6. **Agent 职责不清晰** ⚠️
   - 问题：各 Agent 的工作边界、触发条件、协作流程不明确
   - 需要：梳理完整的 Agent 架构文档

7. **缺少聊天问答功能** ⚠️
   - 问题：用户无法随时提问
   - 需要：添加 Chat 窗口，调用知识管理和数据分析 Agent

8. **"获取实验建议"功能不明确** ⚠️
   - 问题：不清楚调用哪个 Agent，如何工作
   - 需要：明确实验设计 Agent 的触发逻辑

---

## 完整的实验格式定义

根据 `MicroHySeeker/config/last_experiment.json`，实验包含：

### 实验结构
```json
{
  "exp_id": "实验ID",
  "exp_name": "实验名称",
  "description": "描述",
  "tags": ["标签"],
  "operator": "操作员",
  "steps": [
    {
      "step_id": "步骤ID",
      "step_type": "echem | prep_sol | pump | flush",
      // 根据 step_type 不同，包含不同参数
    }
  ]
}
```

### Step Types

#### 1. echem（电化学实验）
- `ec_settings.technique`: CV/EIS/CA/CP/LSV/DPV/SWV
- 电化学参数：e0, eh, el, ef, scan_rate, sample_interval_ms, sensitivity, quiet_time_s, seg_num, scan_dir
- EIS 参数：freq_low, freq_high, amplitude, bias_mode
- ADT 参数：adt_enabled, adt_num_cycles, adt_cathodic_current_mA, ...
- IR 补偿：ir_compensation_enabled, ir_compensation_ohm

#### 2. prep_sol（溶液配制）
- `prep_sol_params`:
  - `target_concentrations`: {溶液名: 浓度}
  - `solvent_flags`: {溶液名: 是否为溶剂}
  - `selected_solutions`: {溶液名: 是否选中}
  - `injection_order`: [溶液名列表]
  - `total_volume_ul`: 总体积

#### 3. pump（泵操作）
- `pump_address`: 泵地址
- `pump_direction`: 方向
- `pump_rpm`: 转速
- `volume_ul`: 体积
- `duration_s`: 持续时间

#### 4. flush（冲洗）
- `flush_channel_id`: 通道ID
- `flush_rpm`: 转速
- `flush_cycle_duration_s`: 单次冲洗时长
- `flush_cycles`: 冲洗次数

---

## Agent 架构定义

### 1. 实验监控 Agent（exp_supervisor）
- **职责**：实时监控实验执行状态，协调其他 Agent
- **运行模式**：常驻运行
- **触发条件**：实验开始时自动启动
- **工作流程**：
  1. 监听实验状态变化
  2. 检测异常情况，触发故障诊断 Agent
  3. 实验完成后，触发数据分析 Agent
  4. 记录实验日志

### 2. 数据分析 Agent（data_analyst）
- **职责**：分析 CV/EIS/CA 实验数据，提取特征
- **运行模式**：按需启动
- **触发条件**：
  - 实验完成后自动分析
  - 用户在 Chat 中请求分析
  - 用户点击"分析数据"按钮
- **工作流程**：
  1. 读取实验数据文件
  2. 提取电化学特征（峰电流、峰电位、阻抗等）
  3. 生成分析报告
  4. 更新知识库

### 3. 实验设计 Agent（exp_designer）
- **职责**：根据目标提出实验方案
- **运行模式**：按需启动
- **触发条件**：
  - 用户点击"获取实验建议"
  - 用户在 Chat 中询问实验方案
- **工作流程**：
  1. 理解用户目标（检测物质、优化参数等）
  2. 查询知识库中的相似实验
  3. 生成实验参数建议
  4. 返回可直接加载的实验配置

### 4. 故障诊断 Agent（diagnostics）
- **职责**：识别实验失败原因，提出解决方案
- **运行模式**：按需启动
- **触发条件**：
  - 实验监控 Agent 检测到异常
  - 用户报告问题
- **工作流程**：
  1. 收集错误日志和实验数据
  2. 分析失败模式（电极污染、连接问题、参数错误等）
  3. 提出解决方案
  4. 更新故障知识库

### 5. 知识管理 Agent（knowledge_mgr）
- **职责**：管理实验知识库，回答用户问题
- **运行模式**：按需启动
- **触发条件**：
  - 用户在 Chat 中提问
  - 其他 Agent 请求知识查询
- **工作流程**：
  1. 理解用户问题
  2. 检索知识库（实验记录、文献、最佳实践）
  3. 生成回答
  4. 学习新知识

---

## 完整的修复计划

### Phase 1: 修复严重 Bug（P0）

#### Task 1.1: 彻底修复 Settings 无限循环
- 排查所有 store 订阅和 useEffect
- 检查 agentStore、settingsStore 是否有循环依赖
- 添加调试日志定位问题

#### Task 1.2: 修复实验监控连接错误
- 检查 `/api/v1/experiments` 路由注册
- 验证 CORS 配置
- 测试 API 端点可用性

#### Task 1.3: 重新设计实验创建界面
- **参考 MicroHySeeker 单次实验编辑器**
- 支持多步骤实验：
  1. 步骤列表（可添加、删除、排序）
  2. 每个步骤选择类型：echem / prep_sol / pump / flush
  3. 根据类型显示对应参数编辑器
- 电化学步骤：
  - 技术选择：CV/EIS/CA/CP/LSV/DPV/SWV
  - 参数编辑器（参考之前的设计，但作为步骤的一部分）
- 溶液配制步骤：
  - 溶液选择器
  - 浓度配置
  - 注射顺序
- 泵操作步骤：
  - 泵地址、方向、转速、体积、时长
- 冲洗步骤：
  - 通道、转速、时长、次数
- 实验元数据：
  - 实验名称、描述、标签、操作员
- 保存为模板功能
- 加载模板功能

#### Task 1.4: 实现实验选择器
- 最近实验列表（从数据目录加载）
- 可选择、预览、加载

#### Task 1.5: 定义数据路径配置
- 数据目录：`D:\AI4S\MicroHySeeker\MicroHySeeker\data\YYYY-MM-DD\`
- 实验文件命名规则
- 配置文件路径

### Phase 2: 完善核心功能（P1）

#### Task 2.1: 实现 Chat 问答功能
- 添加 Chat 窗口组件
- 集成知识管理 Agent
- 支持问答历史
- 支持引用最近实验数据

#### Task 2.2: 完善 Agent 协作流程
- 编写 Agent 架构文档
- 实现 Agent 间消息传递
- 添加 Agent 状态监控面板

#### Task 2.3: 实现"获取实验建议"功能
- 连接实验设计 Agent
- 显示建议的实验参数
- 一键加载建议到创建界面

---

## 开发策略

### 并行开发
- **Copilot**：Task 1.1 + 1.2（修复 Bug）
- **Codex**：Task 1.3（重新设计实验创建界面）
- **Claude Code**：Task 2.1（Chat 功能）

### 验证标准
每个功能必须：
1. 在浏览器中实际测试通过
2. 用户体验流畅、清晰
3. 功能完整、无半成品

---

## 下一步行动

1. 创建详细的任务文档（COPILOT_TASK_*.md）
2. 同时启动 3 个 Coding Agents 并行开发
3. 逐个验证功能
4. 提交代码
5. 进入 Phase 2

---

## 反思

**我的问题**：
- 没有从产品角度全面思考
- 只关注单个功能，忽略了整体流程
- 没有参考 MicroHySeeker 的完整实验格式
- 没有明确 Agent 的职责和协作流程

**改进方向**：
- 每次开发前先梳理完整的产品需求
- 参考现有系统的设计
- 从用户角度验证功能完整性
- 主动发现问题，而不是等待指令
