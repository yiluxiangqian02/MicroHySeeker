# Task: 重新设计实验创建界面

## 问题
当前实验创建界面只有电化学参数，缺少完整的实验步骤支持。

## 目标
重新设计 `ExperimentCreateDialog.tsx`，支持完整的实验流程：
1. 电化学参数（echem）
2. 溶液配制（prep_sol）
3. 泵操作（pump）
4. 冲洗步骤（flush）

## 参考格式
参考 MicroHySeeker 的实验格式：`D:\AI4S\MicroHySeeker\MicroHySeeker\config\last_experiment.json`

## 要求
1. **多步骤界面**：使用 Stepper 或 Tabs 组织步骤
2. **每个步骤独立配置**：
   - echem: 实验类型、电位范围、扫描速率等
   - prep_sol: 溶液名称、体积、浓度
   - pump: 泵编号、流速、体积
   - flush: 冲洗液、体积、重复次数
3. **步骤可选**：用户可以选择需要的步骤
4. **实时验证**：参数范围检查、必填项检查
5. **预估时长**：计算总实验时长
6. **保存为模板**：可以保存常用配置

## 注意事项
- 保持 TypeScript 类型安全
- 使用 React Hook Form 管理表单
- UI 清晰简洁，避免信息过载
- 移动端友好（响应式设计）

## 文件位置
- 主文件：`frontend/src/components/ExperimentCreateDialog.tsx`
- 可能需要新增：`frontend/src/components/StepEditor.tsx`（各步骤编辑器）
