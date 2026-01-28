# 泵通讯测试 UI（独立工具）

该工具是 `MicroHySeeker` 的独立测试界面，用于验证实体泵 RS485 通讯，不依赖主程序 UI。

## 运行

在 PowerShell：

```powershell
cd f:\BaiduSyncdisk\micro1229\MicroHySeeker\tools\pump_comm_test_ui
pip install -r requirements.txt
python app.py
```

## 说明

- 通讯核心来自 `MicroHySeeker/src/echem_sdl/hardware/`（`PumpManager`/`RS485Driver`/协议解析）。
- 本目录仅包含测试 UI，不应复制/修改核心通讯实现。

