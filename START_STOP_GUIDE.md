# AutoHySeeker + MicroHySeeker 启动 / 关闭指南

## 服务端口一览

| 服务 | 端口 | 说明 |
|------|------|------|
| MHS 后端 | 8100 | MicroHySeeker，控制硬件 |
| AHS 后端 | 8200 | AutoHySeeker FastAPI |
| AHS 前端 | 5173 | Vite，浏览器访问入口 |

---

## 方式一：一键启动（推荐）

在 PowerShell 中执行（工作目录无要求）：

```powershell
Start-Process "cmd.exe" -ArgumentList "/k `"D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\dev.bat`"" -WorkingDirectory "D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker"
```

dev.bat 会自动检查并启动 MHS(8100) + AHS后端(8200) + AHS前端(5173)。

> **注意**：dev.bat 依赖 AHS `.venv` 和 `frontend\node_modules`。
> 首次运行若缺依赖，bat 会自动安装（`uv sync` / `npm install`）。

---

## 方式二：逐个启动（排查问题时用）

### 第 1 步：启动 MHS（如未运行）

```powershell
Start-Process "cmd.exe" -ArgumentList "/k `"cd /d D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker && C:\Users\25922\miniforge3\python.exe run_server.py --port 8100`""
```

### 第 2 步：启动 AHS 后端

```powershell
Start-Process "cmd.exe" -ArgumentList "/k `"cd /d D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker && .venv\Scripts\python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8200`""
```

### 第 3 步：启动 AHS 前端

```powershell
Start-Process "cmd.exe" -ArgumentList "/k `"cd /d D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\frontend && npm run dev`""
```

### 第 4 步：打开浏览器

```
http://localhost:5173
```

> **必须用 `localhost`，不能用 `127.0.0.1:5173`（React Router 路由会失效）**

---

## 验证服务是否就绪

在 PowerShell 中检查端口：

```powershell
netstat -ano | Select-String ":8100|:8200|:5173" | Select-String "LISTENING"
```

三行都有输出则全部就绪。

---

## 关闭服务

### 关闭全部（按端口 kill）

```powershell
# 关闭 AHS 前端 (5173)
Get-Process -Id (netstat -ano | Select-String ":5173 " | Select-String "LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] }) -ErrorAction SilentlyContinue | Stop-Process -Force

# 关闭 AHS 后端 (8200)
Get-Process -Id (netstat -ano | Select-String ":8200 " | Select-String "LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] }) -ErrorAction SilentlyContinue | Stop-Process -Force

# 关闭 MHS (8100)  ← 通常不需要关，除非要重启
Get-Process -Id (netstat -ano | Select-String ":8100 " | Select-String "LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] }) -ErrorAction SilentlyContinue | Stop-Process -Force
```

也可以直接关掉对应的 cmd 窗口（标题分别是 `AHS-Backend [:8200]`、`AHS-Frontend [:5173]`、`MHS-Server [:8100]`）。

---

## 常见问题

| 现象 | 原因 | 解法 |
|------|------|------|
| 8200 端口已占用，后端启动失败 | 上次的进程还在 | 先 kill 8200 再重新启动 |
| 前端显示「后端离线」 | AHS 后端未启动 | 补启动第 2 步 |
| OpenViking 警告 | 未配置 `ov.conf` | 无影响，使用 fallback store，忽略即可 |
| 页面空白/路由 404 | 用了 `127.0.0.1` | 改用 `localhost:5173` |
