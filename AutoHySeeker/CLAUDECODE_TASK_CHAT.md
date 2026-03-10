# Claude Code Task: 实现 Chat 问答功能 + 实验选择器

## 目标
添加 Chat 窗口，让用户可以随时提问，调用知识管理和数据分析 Agent

## Task 1: 实现 Chat 问答功能

### 功能需求
- 用户可以在界面中打开 Chat 窗口
- 输入问题，系统调用对应的 Agent 回答
- 支持问答历史记录
- 可以引用最近的实验数据

### Chat 类型
1. **通用问答**：调用知识管理 Agent
   - 例如："CV 实验的扫描速率如何选择？"
   - 例如："什么是 EIS 实验？"

2. **数据分析**：调用数据分析 Agent
   - 例如："分析最近一次 CV 实验的数据"
   - 例如："对比最近 3 次实验的峰电流"

3. **实验建议**：调用实验设计 Agent
   - 例如："我想检测葡萄糖，推荐什么实验参数？"
   - 例如："如何优化 EIS 实验的频率范围？"

### 界面设计
```
Chat 窗口（可折叠侧边栏或浮动窗口）
├── 消息列表
│   ├── 用户消息
│   ├── Agent 回复
│   └── 系统提示（正在思考...）
├── 输入框
│   ├── 文本输入
│   ├── [附加实验数据]（可选）
│   └── [发送]
└── 快捷操作
    ├── [分析最近实验]
    ├── [获取实验建议]
    └── [清空历史]
```

### 后端 API
需要添加以下端点：

```python
# src/api/routes/chat.py

@router.post("/api/v1/chat/ask")
async def ask_question(request: ChatRequest):
    """
    处理用户问题，路由到对应的 Agent
    """
    # 1. 分析问题类型
    # 2. 调用对应的 Agent
    # 3. 返回回答
    pass

@router.get("/api/v1/chat/history")
async def get_chat_history(limit: int = 50):
    """
    获取聊天历史
    """
    pass
```

### Agent 调用逻辑
```python
# 根据问题类型路由到不同的 Agent
if "分析" in question or "数据" in question:
    # 调用数据分析 Agent
    agent = DataAnalystAgent()
elif "建议" in question or "推荐" in question:
    # 调用实验设计 Agent
    agent = ExperimentDesignerAgent()
else:
    # 调用知识管理 Agent
    agent = KnowledgeManagerAgent()

response = await agent.process(question, context)
```

---

## Task 2: 实现实验选择器

### 功能需求
- 在"分享最近实验"功能中，用户可以选择具体的实验
- 显示实验列表（最近 N 次）
- 可以预览实验详情
- 可以加载实验到创建界面

### 界面设计
```
实验选择对话框
├── 实验列表
│   ├── 实验 1
│   │   ├── 实验名称
│   │   ├── 时间
│   │   ├── 步骤数
│   │   └── [预览] [选择]
│   ├── 实验 2 ...
│   └── ...
├── 预览面板（选中时显示）
│   ├── 实验详情
│   ├── 步骤列表
│   └── 参数摘要
└── 操作按钮
    ├── [取消]
    └── [加载实验]
```

### 数据加载
- 数据目录：`D:\AI4S\MicroHySeeker\MicroHySeeker\data\YYYY-MM-DD\`
- 实验文件：`experiment_*.json`
- 按时间倒序排列

### 后端 API
```python
# src/api/routes/experiments.py

@router.get("/api/v1/experiments/recent")
async def get_recent_experiments(limit: int = 20):
    """
    获取最近的实验列表
    """
    pass

@router.get("/api/v1/experiments/{exp_id}")
async def get_experiment_detail(exp_id: str):
    """
    获取实验详情
    """
    pass
```

---

## 实现要点

### 前端组件
```
frontend/src/components/
├── ChatWindow.tsx（Chat 窗口）
├── ChatMessage.tsx（消息组件）
├── ExperimentSelector.tsx（实验选择器）
└── ExperimentPreview.tsx（实验预览）
```

### 状态管理
```typescript
// chatStore.ts
interface ChatStore {
  messages: ChatMessage[];
  isLoading: boolean;
  sendMessage: (text: string, context?: any) => Promise<void>;
  clearHistory: () => void;
}

// experimentStore.ts
interface ExperimentStore {
  recentExperiments: Experiment[];
  selectedExperiment: Experiment | null;
  loadRecentExperiments: () => Promise<void>;
  selectExperiment: (expId: string) => void;
}
```

### 用户体验
- Chat 窗口可以最小化/展开
- 消息支持 Markdown 渲染
- 正在思考时显示加载动画
- 实验选择器支持搜索和过滤
- 预览面板显示完整的实验信息

---

## 验证标准
1. Chat 窗口可以正常打开/关闭
2. 可以发送问题并收到回复
3. 实验选择器可以显示最近的实验
4. 可以预览和加载实验
5. 在浏览器中实际测试通过

---

## 注意事项
- Chat 功能需要前后端配合
- Agent 调用逻辑需要简单清晰
- 实验数据路径需要配置化
- 保持代码结构清晰
- 使用 TypeScript 类型确保类型安全

## 文件路径
- 前端：`D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\frontend\`
- 后端：`D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\src\`
- 数据目录：`D:\AI4S\MicroHySeeker\MicroHySeeker\data\`
