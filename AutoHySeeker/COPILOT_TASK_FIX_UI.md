# Copilot Task: 修复 Web UI 问题

## 问题 1: 设置页面无限循环错误 🔴 P0

**文件**: `frontend/src/pages/Settings.tsx`

**错误信息**:
```
Maximum update depth exceeded. This can happen when a component repeatedly calls setState inside componentWillUpdate or componentDidUpdate. React limits the number of nested updates to prevent infinite loops.
```

**原因**: 
```tsx
useEffect(() => {
  reset(settings);
}, [settings]);
```
`settings` 是一个对象，每次 zustand store 更新都会创建新对象引用，导致 useEffect 无限触发。

**修复方案**:
```tsx
// 方案 1: 只在组件挂载时 reset 一次
useEffect(() => {
  reset(settings);
}, []); // 空依赖数组

// 方案 2: 使用 useRef 追踪是否已初始化
const isInitialized = useRef(false);
useEffect(() => {
  if (!isInitialized.current) {
    reset(settings);
    isInitialized.current = true;
  }
}, [settings, reset]);

// 方案 3: 深度比较（需要安装 use-deep-compare-effect）
// 或者手动比较每个字段
```

**推荐**: 使用方案 1（最简单）或方案 2（更安全）。

---

## 问题 2: 实验创建界面用户体验差 🔴 P0

**文件**: `frontend/src/components/ExperimentCreateDialog.tsx`

**当前问题**:
- 点击 CV 后不知道怎么填参数
- 没有参数说明、单位、示例值
- 没有参数验证（范围检查）

**需求**: 参考 MicroHySeeker 的单次实验编辑界面

**MicroHySeeker 参数编辑器特点**:
1. 每个参数有清晰的标签和单位
2. 有默认值和示例值
3. 有参数范围验证
4. 分组显示（基础参数、高级参数）
5. 实时预览（可选）

**实现方案**:

### CV 参数模板
```typescript
interface CVParams {
  // 基础参数
  startVoltage: number;      // 起始电压 (V), 范围: -10 ~ 10, 默认: 0
  endVoltage: number;        // 终止电压 (V), 范围: -10 ~ 10, 默认: 1
  scanRate: number;          // 扫描速率 (mV/s), 范围: 1 ~ 10000, 默认: 50
  cycles: number;            // 循环次数, 范围: 1 ~ 100, 默认: 1
  
  // 高级参数
  stepVoltage?: number;      // 步进电压 (mV), 范围: 0.1 ~ 100, 默认: 5
  quietTime?: number;        // 静置时间 (s), 范围: 0 ~ 3600, 默认: 2
  sensitivity?: number;      // 灵敏度 (μA), 范围: 1 ~ 1000, 默认: 100
}
```

### EIS 参数模板
```typescript
interface EISParams {
  // 基础参数
  startFreq: number;         // 起始频率 (Hz), 范围: 0.01 ~ 1000000, 默认: 100000
  endFreq: number;           // 终止频率 (Hz), 范围: 0.01 ~ 1000000, 默认: 0.1
  amplitude: number;         // 振幅 (mV), 范围: 1 ~ 100, 默认: 10
  dcVoltage: number;         // 直流偏压 (V), 范围: -10 ~ 10, 默认: 0
  
  // 高级参数
  pointsPerDecade?: number;  // 每十倍频点数, 范围: 5 ~ 20, 默认: 10
  integrationTime?: number;  // 积分时间 (s), 范围: 0.1 ~ 10, 默认: 1
}
```

### CA 参数模板
```typescript
interface CAParams {
  // 基础参数
  voltage: number;           // 电压 (V), 范围: -10 ~ 10, 默认: 0.5
  duration: number;          // 持续时间 (s), 范围: 1 ~ 36000, 默认: 60
  sampleInterval: number;    // 采样间隔 (s), 范围: 0.01 ~ 60, 默认: 0.1
  
  // 高级参数
  quietTime?: number;        // 静置时间 (s), 范围: 0 ~ 3600, 默认: 2
  sensitivity?: number;      // 灵敏度 (μA), 范围: 1 ~ 1000, 默认: 100
}
```

**UI 设计要求**:
1. 使用 Ant Design 的 Form 组件
2. 每个输入框显示：标签 + 单位 + 占位符（示例值）
3. 使用 InputNumber 组件，配置 min/max/step
4. 分组显示：基础参数（默认展开）+ 高级参数（可折叠）
5. 实时验证，错误提示
6. 底部显示预估实验时间

**参考代码结构**:
```tsx
<Form form={form} layout="vertical">
  {/* 基础参数 */}
  <div className="mb-4">
    <h4 className="font-semibold mb-2">基础参数</h4>
    <Form.Item
      label="起始电压 (V)"
      name="startVoltage"
      rules={[
        { required: true, message: '请输入起始电压' },
        { type: 'number', min: -10, max: 10, message: '范围: -10 ~ 10 V' }
      ]}
    >
      <InputNumber
        placeholder="0"
        step={0.1}
        min={-10}
        max={10}
        className="w-full"
      />
    </Form.Item>
    {/* 其他基础参数... */}
  </div>

  {/* 高级参数 */}
  <Collapse>
    <Panel header="高级参数" key="advanced">
      {/* 高级参数表单项... */}
    </Panel>
  </Collapse>

  {/* 预估时间 */}
  <Alert
    message={`预估实验时间: ${estimatedTime} 分钟`}
    type="info"
    className="mt-4"
  />
</Form>
```

---

## 问题 3: 后端状态显示异常 🔴 P0

**现象**: Web 界面显示"后端异常"

**需要检查**:
1. 浏览器控制台是否有 API 请求错误
2. 后端 API `/api/v1/system/status` 是否正常返回
3. 前端是否正确解析响应数据

**检查步骤**:
1. 打开浏览器开发者工具 (F12)
2. 切换到 Network 标签
3. 刷新页面，查看 `/api/v1/system/status` 请求
4. 检查响应状态码和数据格式

**可能的问题**:
- CORS 配置错误
- API 路由未正确注册
- 前端 API 调用路径错误
- 数据格式不匹配

**修复方向**:
- 检查 `frontend/src/api/system.ts` 中的 API 调用
- 检查 `src/api/routes/system.py` 中的响应格式
- 确保 vite.config.ts 中的 proxy 配置正确

---

## 执行要求

1. **按优先级修复**: P0 问题 1 → P0 问题 2 → P0 问题 3
2. **测试验证**: 每个修复后在浏览器中实际测试
3. **代码质量**: 
   - TypeScript 类型安全
   - 组件可复用
   - 代码注释清晰
4. **提交信息**: `fix: 修复设置页面无限循环 + 重新设计实验创建界面`

---

## 参考文件

- MicroHySeeker 参数编辑器: `D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker\src\ui\experiment_editor.py`
- 当前实验创建对话框: `frontend/src/components/ExperimentCreateDialog.tsx`
- 设置页面: `frontend/src/pages/Settings.tsx`
- 系统 API: `src/api/routes/system.py`
