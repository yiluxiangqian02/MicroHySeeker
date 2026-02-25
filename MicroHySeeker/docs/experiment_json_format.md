# MicroHySeeker 实验 JSON 格式说明 (v2.0 协议)

## 概述

实验方案以 JSON 格式保存/载入，文件扩展名 `.json`，编码 UTF-8。

- **保存位置**：`./experiments/` 目录
- **自动备份**：每次启动时自动载入 `config/last_experiment.json`
- **运行数据**：每次运行自动保存到 `data/YYYY-MM-DD/时间戳_实验名/experiment.json`

## JSON 完整结构

```json
{
  "_protocol_version": "2.0",
  "_created_at": "2026-02-13T19:51:47.123456",
  "_modified_at": "2026-02-13T20:00:00.000000",
  "_software_version": "1.0.0",
  
  "exp_id": "single_001",
  "exp_name": "CV扫描-pH7缓冲液",
  "description": "在0.1M PBS缓冲液中进行CV扫描，电位范围-0.2~0.8V",
  "tags": ["CV", "pH=7", "PBS", "0.1M"],
  "operator": "张三",
  "notes": "使用玻碳电极，面积0.07cm²",
  
  "steps": [
    { "...步骤对象..." }
  ]
}
```

## 字段说明

### 元数据字段（下划线开头）

| 字段 | 类型 | 说明 |
|------|------|------|
| `_protocol_version` | string | 协议版本，当前 "2.0" |
| `_created_at` | string | 创建时间 ISO8601 |
| `_modified_at` | string | 最后修改时间 ISO8601 |
| `_software_version` | string | 软件版本 |

### 实验信息字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `exp_id` | string | ✅ | 实验唯一标识 |
| `exp_name` | string | ✅ | 实验名称 |
| `description` | string | 否 | 实验目的/条件描述 |
| `tags` | string[] | 否 | 标签，用于分类检索 |
| `operator` | string | 否 | 操作员姓名 |
| `notes` | string | 否 | 备注 |
| `steps` | ProgStep[] | ✅ | 实验步骤列表 |

## 步骤类型（ProgStep）

每个步骤必须包含 `step_id`、`step_type`，其余字段取决于类型。

### 通用字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `step_id` | string | 步骤唯一ID (如 "step_0") |
| `step_type` | string | 类型：`transfer` / `prep_sol` / `flush` / `echem` / `blank` / `evacuate` |
| `notes` | string | 步骤备注 |

### 1. 移液 (`transfer`)

```json
{
  "step_id": "step_0",
  "step_type": "transfer",
  "pump_address": 5,
  "pump_direction": "FWD",
  "pump_rpm": 100,
  "transfer_duration": 30.0,
  "transfer_duration_unit": "s"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `pump_address` | int | 泵地址 1-12 |
| `pump_direction` | string | 方向 "FWD"(正转) / "REV"(反转) |
| `pump_rpm` | int | 转速 RPM |
| `transfer_duration` | float | 持续时间 |
| `transfer_duration_unit` | string | 时间单位: ms, s, min, hr |

### 2. 配液 (`prep_sol`)

```json
{
  "step_id": "step_1",
  "step_type": "prep_sol",
  "prep_sol_params": {
    "total_volume_ul": 100000.0,
    "injection_order": ["fe", "cu", "H2O"],
    "target_concentrations": {
      "fe": 0.5,
      "cu": 0.1,
      "H2O": 0.0
    },
    "solvent_flags": {
      "fe": false,
      "cu": false,
      "H2O": true
    },
    "selected_solutions": {
      "fe": true,
      "cu": true,
      "H2O": true
    },
    "injection_order_numbers": {
      "fe": 1,
      "cu": 1,
      "H2O": 2
    }
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_volume_ul` | float | 总体积 (μL)，100mL = 100000 |
| `injection_order` | string[] | 注液顺序列表（溶液名） |
| `target_concentrations` | dict | {溶液名: 目标浓度(M)} |
| `solvent_flags` | dict | {溶液名: 是否溶剂} |
| `selected_solutions` | dict | {溶液名: 是否选中} |
| `injection_order_numbers` | dict | {溶液名: 顺序号}，相同号同时注入 |

### 3. 冲洗 (`flush`)

```json
{
  "step_id": "step_2",
  "step_type": "flush",
  "pump_address": 5,
  "pump_direction": "FWD",
  "flush_rpm": 150,
  "flush_cycle_duration_s": 30.0,
  "flush_cycles": 3
}
```

### 4. 电化学 (`echem`)

```json
{
  "step_id": "step_3",
  "step_type": "echem",
  "ec_settings": {
    "technique": "CV",
    "e0": 0.0,
    "eh": 0.8,
    "el": -0.2,
    "scan_rate": 0.1,
    "seg_num": 4,
    "sample_interval_ms": 1,
    "quiet_time_s": 2,
    "sensitivity_index": 4,
    "use_dummy_cell": false,
    "run_time_s": 0,
    "ocpt_enabled": false,
    "ocpt_threshold_uA": 0.0,
    "ocpt_action": "stop_echem"
  }
}
```

**technique 取值**：
- `CV` — 循环伏安法 (需要 e0, eh, el, scan_rate, seg_num)
- `LSV` — 线性扫描伏安法 (需要 e0, eh, el, scan_rate)
- `i-t` — 安培-时间曲线 (需要 e0, run_time_s)
- `OCPT` — 开路电位 (需要 run_time_s)

### 5. 空白 (`blank`)

```json
{
  "step_id": "step_4",
  "step_type": "blank",
  "duration_s": 10.0
}
```

### 6. 排空 (`evacuate`)

```json
{
  "step_id": "step_5",
  "step_type": "evacuate",
  "pump_address": 6,
  "pump_direction": "FWD",
  "pump_rpm": 150,
  "transfer_duration": 60.0,
  "flush_cycles": 2
}
```

## 完整示例

```json
{
  "_protocol_version": "2.0",
  "_created_at": "2026-02-13T19:00:00",
  "_modified_at": "2026-02-13T19:30:00",
  "_software_version": "1.0.0",
  "exp_id": "single_001",
  "exp_name": "Fe-Cu浓度梯度CV扫描",
  "description": "在混合Fe/Cu溶液中进行CV扫描，测试不同浓度比对电化学响应的影响",
  "tags": ["CV", "Fe", "Cu", "浓度梯度"],
  "operator": "张三",
  "notes": "玻碳电极，0.1M KCl支持电解质",
  "steps": [
    {
      "step_id": "step_0",
      "step_type": "prep_sol",
      "prep_sol_params": {
        "total_volume_ul": 100000.0,
        "injection_order": ["fe", "cu", "H2O"],
        "target_concentrations": {"fe": 0.5, "cu": 0.1, "H2O": 0.0},
        "solvent_flags": {"fe": false, "cu": false, "H2O": true},
        "selected_solutions": {"fe": true, "cu": true, "H2O": true},
        "injection_order_numbers": {"fe": 1, "cu": 1, "H2O": 2}
      }
    },
    {
      "step_id": "step_1",
      "step_type": "echem",
      "ec_settings": {
        "technique": "CV",
        "e0": 0.0,
        "eh": 0.8,
        "el": -0.2,
        "scan_rate": 0.1,
        "seg_num": 4,
        "sample_interval_ms": 1,
        "quiet_time_s": 2,
        "sensitivity_index": 4,
        "use_dummy_cell": true
      }
    }
  ]
}
```

## 向后兼容

- v1.0 格式（无 `_protocol_version` 字段）可正常载入
- 缺失的 v2.0 字段会使用默认值
- `tags` 缺失 → `[]`
- `description`/`operator` 缺失 → `""`

## 运行数据目录结构

每次实验运行会自动在 `data/` 下创建独立目录：

```
data/
  2026-02-13/
    2026-02-13_19-51-47_Fe-Cu浓度梯度CV扫描/
      experiment.json       ← 实验方案副本
      run_summary.json      ← 运行结果摘要（成功/失败、耗时、步骤结果）
      run_log.log           ← 运行日志（毫秒级时间戳）
      echem/
        step_1_CV.csv       ← 电化学原始数据
        step_1_CV.png       ← 电化学图表截图
      pump/
        pump_operations.csv ← 泵操作时序记录
```

### run_summary.json 格式

```json
{
  "run_id": "run_20260213_195147",
  "exp_id": "single_001",
  "exp_name": "Fe-Cu浓度梯度CV扫描",
  "started_at": "2026-02-13T19:51:47.123456",
  "finished_at": "2026-02-13T19:55:30.654321",
  "elapsed_seconds": 223.5,
  "success": true,
  "operator": "张三",
  "step_results": [
    {
      "step_index": 0,
      "step_id": "step_0",
      "step_type": "prep_sol",
      "started_at": "2026-02-13T19:51:48",
      "finished_at": "2026-02-13T19:53:00",
      "success": true,
      "details": ""
    },
    {
      "step_index": 1,
      "step_id": "step_1",
      "step_type": "echem",
      "started_at": "2026-02-13T19:53:01",
      "finished_at": "2026-02-13T19:55:30",
      "success": true,
      "data_file": "echem/step_1_CV.csv",
      "data_points_count": 3500
    }
  ],
  "system_snapshot": { "...系统配置快照..." },
  "errors": [],
  "warnings": []
}
```
