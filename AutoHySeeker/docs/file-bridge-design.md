# AutoHySeeker ↔ MicroHySeeker 文件通信桥接设计方案

**版本**：v1.0  
**日期**：2026-03-06  
**作者**：Copilot + Pi 设计评审

---

## 目录

1. [文件协议规范](#1-文件协议规范)
2. [AutoHySeeker 端实现方案](#2-autohyseeker-端实现方案)
3. [MicroHySeeker 端实现方案](#3-microhyseeker-端实现方案)
4. [ExperimentPlan 到 ExpProgram 字段映射表](#4-字段映射表)
5. [错误处理流程](#5-错误处理流程)
6. [测试用例清单](#6-测试用例清单)

---

## 1. 文件协议规范

### 1.1 共享目录结构

`
D:\AI4S\bridge\
├── cmd\                        # 命令目录（AutoHySeeker 写，MicroHySeeker 读）
│   ├── command.json            # 当前活跃命令（单文件，覆盖写）
│   └── command.json.lock       # 写锁标志（存在即锁定）
├── status\                     # 状态目录（MicroHySeeker 写，AutoHySeeker 读）
│   └── status.json             # 引擎实时状态（心跳更新，~1s 周期）
├── results\                    # 结果目录（MicroHySeeker 写，AutoHySeeker 读）
│   └── {run_id}\
│       ├── summary.json        # 实验汇总
│       └── data\
│           ├── step_{n}_{technique}.csv   # 电化学数据
│           └── step_{n}_meta.json         # 步骤元数据
└── .heartbeat                  # MicroHySeeker 心跳文件（存活检测，每 5s 更新 mtime）
`

**约定**：
- 所有写操作使用**原子写入**：先写 *.tmp，再 os.replace() 为目标路径
- 路径中 
un_id 格式：
un_{timestamp}_{plan_name_slug}，如 
un_20260306_143022_her_opt
- 所有 JSON 文件使用 UTF-8 编码，indent=2，ensure_ascii=False
