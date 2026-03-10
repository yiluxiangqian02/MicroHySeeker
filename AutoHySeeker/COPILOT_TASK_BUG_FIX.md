# Copilot Task: 修复 Settings 无限循环 + 实验监控连接错误

## 目标
修复两个严重 Bug，确保基础功能可用

## Task 1: 修复 Settings 页面无限循环

### 问题
点击设置页面报错：`Maximum update depth exceeded`

### 排查方向
1. 检查 `frontend/src/stores/settingsStore.ts` 和 `agentStore.ts`
2. 查找所有 `useEffect` 中订阅 store 的地方
3. 检查是否有循环依赖：store 更新 → 组件重渲染 → store 更新

### 修复策略
- 使用 `useEffect` 时确保依赖数组正确
- 避免在 render 过程中调用 store 的 set 方法
- 使用 `useRef` 或 `useMemo` 避免不必要的重渲染
- 可能需要重构 store 的选择器，避免每次返回新对象

### 验证
在浏览器中点击"设置"，页面正常显示，无报错

---

## Task 2: 修复实验监控连接错误

### 问题
实验监控页面显示：`Connection error: AutoHySeeker API is unreachable`

### 排查方向
1. 检查 `src/api/routes/experiments.py` 是否正确注册
2. 检查 `src/api/main.py` 中是否包含 `experiments_router`
3. 验证 CORS 配置是否生效
4. 测试 API 端点：`http://localhost:8100/api/v1/experiments`

### 修复策略
- 确保 `experiments_router` 在 `main.py` 中正确注册
- 检查路由前缀是否正确
- 添加健康检查端点：`GET /api/v1/experiments/status`
- 前端添加更详细的错误信息

### 验证
1. 后端：`curl http://localhost:8100/api/v1/experiments/status` 返回 200
2. 前端：实验监控页面正常显示，无连接错误

---

## 注意事项
- 修改前先 `git status` 查看当前状态
- 每个修复完成后立即测试
- 不要修改其他无关文件
- 保持代码风格一致

## 文件路径
- 前端：`D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\frontend\`
- 后端：`D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\src\`
