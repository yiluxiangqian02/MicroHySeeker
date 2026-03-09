# Task 8: 端到端集成测试

## 目标
实现完整的系统集成测试，验证 AutoHySeeker + MicroHySeeker 闭环工作流

## 核心功能

### 1. 测试脚本
- 启动 MicroHySeeker API 服务器
- AutoHySeeker 通过 API 启动实验
- 实时监控实验进度
- 故障注入测试（模拟设备故障）
- 验证自动恢复机制

### 2. 测试场景
- 正常实验流程（CV 扫描）
- 设备故障恢复
- Agent 协调测试
- 数据分析验证

## 实现要求

### 1. 创建 AutoHySeeker/tests/integration/test_e2e.py
- 测试类：TestEndToEnd
- 测试方法：
  - test_normal_experiment() - 正常流程
  - test_device_failure_recovery() - 故障恢复
  - test_agent_coordination() - Agent 协调
  - test_data_analysis() - 数据分析

### 2. 创建 AutoHySeeker/tests/integration/conftest.py
- pytest fixtures
- 启动/停止 MicroHySeeker API
- 清理测试数据

### 3. 创建测试辅助工具
- AutoHySeeker/tests/utils/mock_device.py - 模拟设备
- AutoHySeeker/tests/utils/api_client.py - API 客户端

## 技术栈
- pytest
- pytest-asyncio
- httpx（异步 HTTP 客户端）
- 现有代码：AutoHySeeker/src/agents/

## 注意事项
- 使用 pytest fixtures 管理资源
- 异步测试（async/await）
- 超时控制（避免测试卡死）
- 详细的断言和日志
- 测试隔离（每个测试独立）
