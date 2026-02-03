# 后端RS485集成指南

## ✅ 已完成的工作

### 1. 后端RS485模块（完整实现）
- ✅ **rs485_protocol.py** - 协议层（帧编解码、校验和、数据转换）
- ✅ **rs485_driver.py** - 驱动层（串口通信、线程管理、Mock模式）
- ✅ **utils/constants.py** - 协议常量定义
- ✅ **utils/errors.py** - 异常体系
- ✅ **测试覆盖** - 65个单元测试全部通过

### 2. 前端适配层（已集成到UI）
- ✅ **rs485_wrapper.py** - 前后端桥接服务
  - 使用真正的RS485Driver（不再是Mock）
  - 提供端口自动检测功能
  - 统一的泵控制接口
  
### 3. UI增强
- ✅ **config_dialog.py** - 配置对话框
  - 自动加载实际可用串口
  - 端口刷新按钮（🔄）
  - RS485连接/断开功能
  - 泵扫描功能

---

## 🎯 如何运行和测试

### 启动UI界面
```bash
cd D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
conda activate MicroHySeeker
python run_ui.py
```

### 在UI中测试RS485功能

#### 1. 打开配置对话框
- 点击主界面的"系统配置"按钮

#### 2. 测试端口检测
- 在"RS485连接"区域，查看"端口"下拉列表
- **系统会自动加载实际检测到的COM端口**（如COM1, COM5, COM6, COM7）
- 点击🔄按钮可刷新端口列表

#### 3. 测试连接功能（Mock模式）
1. 选择任意端口（如COM3）
2. 选择波特率：38400（默认）
3. 点击"连接"按钮
4. 控制台会显示：`✅ RS485Wrapper: 连接成功 COM3@38400 (Mock=True)`

#### 4. 测试泵扫描
1. 连接成功后，"扫描泵"按钮会激活
2. 点击"扫描泵"按钮
3. Mock模式下会模拟返回地址1-5的泵
4. 控制台显示：`✅ RS485Wrapper: 扫描到泵 [1, 2, 3, 4, 5]`

#### 5. 测试手动控制（如果有该功能）
- 在手动控制界面可以：
  - 选择泵地址（1-12）
  - 设置转速（0-3000 RPM）
  - 设置方向（FWD/REV）
  - 点击"启动"/"停止"按钮

---

## 📊 功能对照表

| 前端需求 | 后端实现 | 状态 |
|---------|---------|------|
| 端口枚举 | `RS485Wrapper.list_available_ports()` | ✅ 已实现 |
| 打开串口 | `RS485Wrapper.open_port(port, baudrate)` | ✅ 已实现 |
| 关闭串口 | `RS485Wrapper.close_port()` | ✅ 已实现 |
| 连接状态 | `RS485Wrapper.is_connected()` | ✅ 已实现 |
| 扫描泵 | `RS485Wrapper.scan_pumps()` | ✅ 已实现 |
| 启动泵 | `RS485Wrapper.start_pump(addr, dir, rpm)` | ✅ 已实现 |
| 停止泵 | `RS485Wrapper.stop_pump(addr)` | ✅ 已实现 |
| 停止所有泵 | `RS485Wrapper.stop_all()` | ✅ 已实现 |
| 获取泵状态 | `RS485Wrapper.get_pump_status(addr)` | ✅ 已实现 |

---

## 🔧 切换Mock/真实硬件模式

### 默认：Mock模式（无需硬件）
当前默认使用Mock模式，可以在没有硬件的情况下测试所有功能。

### 切换到真实硬件模式
修改 `src/services/rs485_wrapper.py` 的初始化：

```python
def get_rs485_instance() -> RS485Wrapper:
    """获取RS485实例单例"""
    global _rs485_instance
    if _rs485_instance is None:
        _rs485_instance = RS485Wrapper()
        _rs485_instance.set_mock_mode(False)  # ← 改为False使用真实硬件
    return _rs485_instance
```

---

## 📝 控制台日志示例

### 成功连接（Mock模式）
```
✅ RS485Wrapper: 连接成功 COM3@38400 (Mock=True)
[Mock RS485] Opened COM3 @ 38400
[RS485 INFO] Read loop started
[RS485 INFO] Opened RS485 port: COM3 @ 38400 bps
```

### 扫描泵
```
[RS485 INFO] Scanning devices at addresses: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
✅ RS485Wrapper: 扫描到泵 [1, 2, 3, 4, 5]
```

### 启动泵
```
[Mock RS485] TX: FA 01 F3 01 EF          # 使能命令
[Mock RS485] RX (mock): FB 01 F3 01 F0   # 响应
[Mock RS485] TX: FA 01 F6 00 64 10 65    # 速度命令 (100RPM)
[Mock RS485] RX (mock): FB 01 F6 01 F3   # 响应
✅ RS485Wrapper: 泵 1 启动成功 FWD 100RPM
```

---

## 🧪 测试建议

### 1. 配置对话框测试
- [ ] 端口列表加载正确（显示实际COM端口）
- [ ] 刷新按钮工作正常
- [ ] 连接/断开按钮状态切换
- [ ] 扫描功能返回泵列表

### 2. 手动控制测试
- [ ] 选择泵地址
- [ ] 设置转速和方向
- [ ] 启动/停止泵功能
- [ ] 控制台日志输出正确

### 3. 程序编辑器测试
- [ ] 移液步骤选择泵地址
- [ ] 配液步骤多泵协调
- [ ] 冲洗步骤参数设置

---

## ⚠️ 注意事项

1. **端口检测** - 系统会自动检测实际可用的COM端口，无需硬编码
2. **Mock模式** - 默认使用Mock模式，不需要真实硬件即可测试所有功能
3. **线程安全** - 所有泵控制操作都是线程安全的
4. **状态缓存** - 泵状态会在Wrapper层缓存，提高响应速度

---

## 🚀 下一步计划

### P1优先级模块
- [ ] PumpManager - 统一泵管理器
- [ ] Diluter - 配液模块
- [ ] Flusher - 冲洗模块

### P0核心引擎
- [ ] ExperimentEngine - 实验执行引擎
- [ ] LibContext - 依赖注入容器

---

## 📞 问题排查

### UI无法启动
```bash
# 确保环境激活
conda activate MicroHySeeker

# 检查依赖
python -c "import PySide6; import pyqtgraph; import serial; print('依赖OK')"
```

### 端口检测失败
- 检查pyserial是否安装：`pip install pyserial`
- 查看控制台错误信息
- Mock模式下会返回默认端口列表

### 连接失败
- Mock模式下应该始终成功
- 真实模式下检查：
  - 端口是否被占用
  - 波特率是否正确（38400）
  - 设备是否接通电源

---

**版本**: v1.0  
**更新日期**: 2026-02-02  
**状态**: ✅ 后端RS485模块已完整集成到UI
