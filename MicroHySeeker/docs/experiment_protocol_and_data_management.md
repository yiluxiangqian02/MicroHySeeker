# MicroHySeeker 实验协议 & 数据管理规范

## 一、实验 JSON 协议 (v2.0)

### 1.1 目录结构

```
MicroHySeeker/
├── config/
│   ├── system.json              # 系统硬件配置
│   └── last_experiment.json     # 上次打开的实验（自动保存）
├── experiments/                 # 用户保存的实验模板
│   ├── CV_NiFe_test.json
│   ├── LSV_screening.json
│   └── ...
├── data/                        # 实验运行数据（按日期自动组织）
│   ├── 2026-02-13/
│   │   ├── 2026-02-13_14-30-25_CV_NiFe/
│   │   │   ├── experiment.json       # 实验方案副本
│   │   │   ├── run_log.log           # 完整运行日志
│   │   │   ├── run_summary.json      # 运行结果摘要
│   │   │   ├── echem/
│   │   │   │   ├── step_3_CV.csv     # 电化学原始数据
│   │   │   │   └── step_3_CV.png     # 电化学图表
│   │   │   └── pump/
│   │   │       └── pump_operations.csv  # 泵操作记录
│   │   └── 2026-02-13_15-10-00_LSV_screen/
│   │       └── ...
│   └── 2026-02-14/
│       └── ...
└── logs/                        # 应用级日志（非实验）
    ├── app_2026-02-13.log
    └── app_2026-02-14.log
```

### 1.2 实验 JSON 格式 (experiment.json)

```json
{
  "_protocol_version": "2.0",
  "_created_at": "2026-02-13T14:30:00",
  "_modified_at": "2026-02-13T14:35:00",
  "_software_version": "1.0.0",

  "exp_id": "exp_20260213_143000",
  "exp_name": "CV_NiFe_催化剂筛选",
  "description": "不同比例NiFe(OH)2的CV性能测试",
  "tags": ["NiFe", "CV", "催化剂筛选"],
  "operator": "张三",

  "steps": [
    {
      "step_id": "step_001",
      "step_type": "prep_sol",
      "pump_address": null,
      "pump_direction": null,
      "pump_rpm": null,
      "volume_ul": null,
      "duration_s": null,
      "transfer_duration": null,
      "transfer_duration_unit": "s",
      "prep_sol_params": {
        "injection_order": ["Ni(OH)2", "Fe(OH)2", "H2O"],
        "total_volume_ul": 100000.0,
        "target_concentrations": {
          "Ni(OH)2": 0.5,
          "Fe(OH)2": 0.3,
          "H2O": 0.0
        },
        "solvent_flags": {
          "Ni(OH)2": false,
          "Fe(OH)2": false,
          "H2O": true
        },
        "selected_solutions": {
          "Ni(OH)2": true,
          "Fe(OH)2": true,
          "H2O": true
        },
        "injection_order_numbers": {
          "Ni(OH)2": 1,
          "Fe(OH)2": 1,
          "H2O": 2
        }
      },
      "notes": "配制 Ni:Fe = 5:3 溶液"
    },
    {
      "step_id": "step_002",
      "step_type": "transfer",
      "pump_address": 10,
      "pump_direction": "FWD",
      "pump_rpm": 150,
      "transfer_duration": 30.0,
      "transfer_duration_unit": "s",
      "notes": "Transfer 泵将混合液输送到反应烧杯"
    },
    {
      "step_id": "step_003",
      "step_type": "echem",
      "ec_settings": {
        "technique": "CV",
        "e0": 0.0,
        "eh": 0.8,
        "el": -0.2,
        "ef": 0.0,
        "scan_rate": 0.05,
        "sample_interval_ms": 1,
        "seg_num": 3,
        "scan_dir": "FWD",
        "quiet_time_s": 2.0,
        "sensitivity": null,
        "autosensitivity": true,
        "use_dummy_cell": false,
        "ocpt_enabled": false
      },
      "notes": "三段CV扫描"
    },
    {
      "step_id": "step_004",
      "step_type": "flush",
      "pump_address": 9,
      "pump_direction": "FWD",
      "flush_rpm": 200,
      "flush_cycle_duration_s": 30,
      "flush_cycles": 3,
      "notes": "Inlet泵注水冲洗3次"
    },
    {
      "step_id": "step_005",
      "step_type": "evacuate",
      "pump_address": 11,
      "pump_direction": "FWD",
      "pump_rpm": 200,
      "transfer_duration": 60.0,
      "flush_cycles": 1,
      "notes": "Outlet泵排空"
    },
    {
      "step_id": "step_006",
      "step_type": "blank",
      "duration_s": 10.0,
      "notes": "静置10秒"
    }
  ],

  "notes": "第一批次NiFe催化剂电化学筛选实验"
}
```

### 1.3 运行结果摘要 (run_summary.json)

```json
{
  "exp_id": "exp_20260213_143000",
  "exp_name": "CV_NiFe_催化剂筛选",
  "run_id": "run_20260213_143025",
  "started_at": "2026-02-13T14:30:25",
  "finished_at": "2026-02-13T14:45:10",
  "elapsed_seconds": 885.0,
  "success": true,
  "operator": "张三",

  "step_results": [
    {
      "step_index": 0,
      "step_id": "step_001",
      "step_type": "prep_sol",
      "started_at": "2026-02-13T14:30:25",
      "finished_at": "2026-02-13T14:32:00",
      "success": true,
      "details": "配液完成: Ni(OH)2 25000uL, Fe(OH)2 30000uL, H2O 45000uL"
    },
    {
      "step_index": 2,
      "step_id": "step_003",
      "step_type": "echem",
      "started_at": "2026-02-13T14:33:00",
      "finished_at": "2026-02-13T14:40:00",
      "success": true,
      "data_file": "echem/step_3_CV.csv",
      "data_points_count": 2048,
      "details": "CV完成, 采集2048点"
    }
  ],

  "system_snapshot": {
    "rs485_port": "COM7",
    "mock_mode": false,
    "calibration_data": { "1": {"slope_k": 5.2, "intercept_b": 0.3} }
  },

  "errors": [],
  "warnings": ["泵1响应不稳定，使用fire_and_forget模式"]
}
```

### 1.4 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `_protocol_version` | string | 是 | 协议版本号，当前 "2.0" |
| `exp_id` | string | 是 | 实验唯一ID，格式 `exp_YYYYMMDD_HHMMSS` |
| `exp_name` | string | 是 | 实验名称 |
| `description` | string | 否 | 详细描述 |
| `tags` | string[] | 否 | 标签，方便检索 |
| `operator` | string | 否 | 操作员 |
| `steps` | ProgStep[] | 是 | 步骤列表 |
| `steps[].step_type` | enum | 是 | `transfer`/`prep_sol`/`flush`/`echem`/`blank`/`evacuate` |

---

## 二、日志管理体系

### 2.1 分层日志架构

```
┌──────────────────────────────────────────────────┐
│           应用级日志 (app_YYYY-MM-DD.log)          │
│   Python logging → RotatingFileHandler            │
│   记录：启动/关闭/配置变更/异常/硬件事件             │
└──────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────┐
│       实验运行日志 (data/.../run_log.log)          │
│   每次实验独立文件，时间戳精确到毫秒                 │
│   记录：每个步骤开始/结束/参数/泵操作/测量结果        │
└──────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────┐
│          UI 日志面板 (实时显示)                     │
│   通过 Signal 实时推送到 QTextEdit                 │
│   带颜色分类                                      │
└──────────────────────────────────────────────────┘
```

### 2.2 日志格式

```
[2026-02-13 14:30:25.123] [INFO] [RUNNER] 步骤0开始: prep_sol
[2026-02-13 14:30:25.456] [DEBUG] [RS485] 泵1: CMD_POSITION_REL 发送 16384 counts @100RPM
[2026-02-13 14:30:26.789] [INFO] [RUNNER] 配液: Ni(OH)2 25000uL, Fe(OH)2 30000uL
[2026-02-13 14:30:50.000] [ERROR] [RS485] 泵3: 通信超时
```

### 2.3 应用日志特性
- **按天轮换**: `logs/app_2026-02-13.log`
- **大小限制**: 单文件最大 10MB，自动轮换保留 30 天
- **级别控制**: DEBUG/INFO/WARNING/ERROR/CRITICAL
- **统一入口**: 所有模块通过 `get_app_logger(name)` 获取 logger

---

## 三、数据管理体系

### 3.1 核心原则
1. **按日期组织**: `data/YYYY-MM-DD/` 每天一个目录
2. **实验隔离**: 每次运行创建独立目录 `YYYY-MM-DD_HH-MM-SS_实验名/`
3. **完整快照**: 实验目录包含方案副本+日志+数据+图表
4. **可追溯**: run_summary.json 包含系统快照（校准数据、端口等）

### 3.2 数据文件
| 文件 | 格式 | 内容 |
|------|------|------|
| `experiment.json` | JSON | 实验方案完整副本 |
| `run_log.log` | 文本 | 精确到毫秒的运行日志 |
| `run_summary.json` | JSON | 运行结果+系统快照 |
| `echem/step_N_技术.csv` | CSV | 电化学原始数据 |
| `echem/step_N_技术.png` | PNG | 电化学图表 |
| `pump/pump_operations.csv` | CSV | 泵操作时序记录 |
