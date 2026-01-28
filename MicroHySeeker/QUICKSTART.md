# 🚀 MicroHySeeker UI - 快速开始

## 一行启动命令

```bash
cd f:\BaiduSyncdisk\micro1229\MicroHySeeker && python run_ui.py
```

## 核心功能菜单

| 菜单 | 功能 | 快捷操作 |
|-----|------|---------|
| **工具** → 系统配置 | 配置 RS485 端口、配液/冲洗通道 | 添加/删除通道、保存配置 |
| **工具** → 手动控制 | 实时控制单个泵的启停方向转速 | 选泵 → 输入转速 → 按钮控制 |
| **工具** → 泵校准 | 测量泵流量、计算标定因子 | 输入体积 → 点击计算 → 保存 |
| **实验** → 编辑程序 | 创建多步骤实验序列 | 添加步骤 → 编辑参数 → 保存程序 |

## 五分钟快速测试

### 步骤 1：验证 UI 启动
```bash
python run_ui.py
```
✅ 看到窗口 → 继续

### 步骤 2：创建第一个程序
1. 点击 **实验** → **编辑程序**
2. 点击 **添加步骤**（默认 Transfer）
3. 在右侧设置：
   - 泵地址：`1`
   - 流向：`FWD`
   - 转速：`500` RPM
   - 体积：`100` μL
4. 点击 **保存程序**
5. 查看日志区显示保存信息 ✅

### 步骤 3：添加更多步骤
1. 再次点击 **添加步骤**
2. 在步骤编辑器顶部改为 **Flush**
3. 设置：
   - 泵地址：`1`
   - RPM：`500`
   - 周期：`30` 秒
   - 循环数：`2`
4. 保存 ✅

## 文件位置

- 📁 项目根：`f:\BaiduSyncdisk\micro1229\MicroHySeeker\`
- 📄 配置文件：`./config/system.json`（自动生成）
- 📊 程序保存：`./experiments/` （JSON 格式）
- 📖 完整指南：`./GUIDE_RUN_AND_TEST.md`
- ✅ 完成总结：`./IMPLEMENTATION_COMPLETE.md`

## 三个测试场景

### 方案 A：配液 + 冲洗（简单）
- 2 步程序
- 验证泵命令日志
- 预期耗时：5 分钟

### 方案 B：电化学 + OCPT（中等）
- 1 步 EChem + OCPT 触发
- 观察曲线绘制和反向电流检测
- 预期耗时：10 分钟

### 方案 C：多步完整流程（复杂）
- 4 步程序：PrepSol → Transfer → Flush → LSV
- 验证 UI 响应和步骤高亮
- 预期耗时：15 分钟

详见 `GUIDE_RUN_AND_TEST.md` 第三部分

## 常见快速操作

### 创建新配置
```
工具 → 系统配置 → 
添加配液通道 → 
设置 SolutionName, StockConcentration, PumpAddress → 
保存 → ./config/system.json 自动更新
```

### 测试泵连接
```
工具 → 手动控制 → 
选择泵地址 1 → 
输入 500 RPM → 
点击 FWD → 
日志显示 "启动 FWD 500RPM"
```

### 保存和加载程序
```
实验 → 编辑程序 → [编辑] → 保存程序 →
程序保存至 ./experiments/*.json →
后续可从文件菜单打开
```

## 快速故障排除

| 问题 | 解决方案 |
|------|---------|
| "ModuleNotFoundError: No module named 'PySide6'" | `pip install -r requirements.txt` |
| 配置文件找不到 | 自动创建于 `./config/system.json`，可忽略 |
| 程序编辑器空白 | 点击列表中的步骤激活编辑器 |
| RS485 扫描失败 | 正常模式，需真实硬件；可手动添加泵 |

## 项目统计

- **总代码行数**：3000+ 行
- **Python 文件**：11 个
- **数据模型**：15+ 个 dataclass
- **UI 对话框**：5 个
- **支持的步骤类型**：5 (Transfer/PrepSol/Flush/EChem/Blank)
- **EC 技术支持**：3 (CV/LSV/i-t)
- **OCPT 动作**：3 (log/pause/abort)

## 下一步

1. ✅ 运行 UI 并验证基本功能
2. ✅ 创建并执行测试程序（选一个方案）
3. ✅ 连接真实硬件进行端到端测试（可选）

---

**立即开始**：
```bash
cd f:\BaiduSyncdisk\micro1229\MicroHySeeker && python run_ui.py
```

祝您使用愉快！🎉
