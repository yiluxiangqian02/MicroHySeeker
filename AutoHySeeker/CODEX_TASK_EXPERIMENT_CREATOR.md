# Codex Task: 重新设计实验创建界面（多步骤支持）

## 目标
参考 MicroHySeeker 单次实验编辑器，重新设计实验创建界面，支持完整的多步骤实验

## 背景

### MicroHySeeker 实验格式
实验包含多个步骤，每个步骤有不同类型：

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
- ADT 参数：adt_enabled, adt_num_cycles, ...
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
- `pump_direction`: 方向（"forward" | "reverse"）
- `pump_rpm`: 转速
- `volume_ul`: 体积（微升）
- `duration_s`: 持续时间（秒）

#### 4. flush（冲洗）
- `flush_channel_id`: 通道ID
- `flush_rpm`: 转速
- `flush_cycle_duration_s`: 单次冲洗时长
- `flush_cycles`: 冲洗次数

---

## 设计要求

### 界面结构
```
实验创建对话框
├── 实验元数据
│   ├── 实验名称 *
│   ├── 描述
│   ├── 标签（多选）
│   └── 操作员
├── 步骤列表
│   ├── 步骤 1 [类型选择器] [删除] [上移] [下移]
│   │   └── 参数编辑器（根据类型动态显示）
│   ├── 步骤 2 ...
│   └── [+ 添加步骤]
└── 操作按钮
    ├── [保存为模板]
    ├── [取消]
    └── [创建实验]
```

### 步骤类型选择器
- 下拉菜单：电化学实验 / 溶液配制 / 泵操作 / 冲洗
- 切换类型时清空当前步骤参数

### 参数编辑器（根据步骤类型）

#### 电化学实验编辑器
- 技术选择：CV/EIS/CA/CP/LSV/DPV/SWV（单选）
- 根据技术显示对应参数（参考之前的设计）
- 参数分组：基础参数 / 高级参数（可折叠）
- 实时验证：范围检查、必填项检查
- 预估时长显示

#### 溶液配制编辑器
- 溶液列表（从配置加载）
- 每个溶液：
  - 选择框（是否使用）
  - 浓度输入（数字 + 单位）
  - 溶剂标记（复选框）
- 注射顺序（拖拽排序）
- 总体积输入

#### 泵操作编辑器
- 泵地址（下拉选择）
- 方向（前进/后退）
- 转速（数字输入 + 单位 rpm）
- 体积（数字输入 + 单位 μL）
- 持续时间（数字输入 + 单位 s）

#### 冲洗编辑器
- 通道ID（下拉选择）
- 转速（数字输入 + 单位 rpm）
- 单次时长（数字输入 + 单位 s）
- 冲洗次数（数字输入）

---

## 实现要点

### 组件结构
```
ExperimentCreateDialog.tsx
├── ExperimentMetadataForm（实验元数据）
├── StepList（步骤列表）
│   └── StepEditor（步骤编辑器）
│       ├── EchemStepEditor
│       ├── PrepSolStepEditor
│       ├── PumpStepEditor
│       └── FlushStepEditor
└── ActionButtons
```

### 状态管理
```typescript
interface ExperimentForm {
  exp_name: string;
  description: string;
  tags: string[];
  operator: string;
  steps: Step[];
}

interface Step {
  step_id: string;
  step_type: 'echem' | 'prep_sol' | 'pump' | 'flush';
  // 根据类型包含不同参数
}
```

### 验证规则
- 实验名称：必填，1-100 字符
- 步骤列表：至少 1 个步骤
- 每个步骤：根据类型验证必填参数和范围

### 用户体验
- 步骤可拖拽排序
- 删除步骤需确认
- 切换步骤类型需确认（会清空参数）
- 保存为模板：弹出命名对话框
- 创建实验：验证通过后调用 API

---

## 参考文件
- 实验格式示例：`D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker\config\last_experiment.json`
- 现有实验创建对话框：`frontend/src/components/ExperimentCreateDialog.tsx`（需要完全重写）

---

## 验证标准
1. 可以创建包含多个步骤的实验
2. 每种步骤类型的参数编辑器完整可用
3. 步骤可以添加、删除、排序
4. 参数验证正确
5. 生成的 JSON 格式与 MicroHySeeker 兼容
6. 在浏览器中实际测试通过

---

## 注意事项
- 这是一个大型重构，需要完全重写 `ExperimentCreateDialog.tsx`
- 保持代码结构清晰，组件职责单一
- 使用 TypeScript 类型确保类型安全
- 参考 MicroHySeeker 的 UI 设计风格
- 不要修改后端代码

## 文件路径
- 前端：`D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\frontend\`
