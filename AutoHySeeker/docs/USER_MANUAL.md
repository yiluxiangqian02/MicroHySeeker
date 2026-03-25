# AutoHySeeker 使用说明书

> 更新日期：2026-03-23
> 适用范围：基于当前仓库代码状态整理，重点说明“现在能怎么用”以及“哪些地方还不能完全当成成品来用”。

## 1. AutoHySeeker 是什么

AutoHySeeker 是 `MicroHySeeker` 旁边的一套 AI 多智能体科研辅助系统，主要负责这些事情：

- 管理实验草案、实验步骤和实验记录
- 提供 Web 端总览、实验详情、设置与聊天入口
- 连接知识库、诊断逻辑、优化循环和多 Agent 编排
- 在能连上 `MicroHySeeker` 时，把实验执行请求转发给硬件控制层

一句话区分：

- `MicroHySeeker` 负责硬件、泵、电化学仪、桌面控制
- `AutoHySeeker` 负责 AI、Web 面板、知识检索、实验计划和辅助分析

## 2. 使用前先看这一页

当前版本不是所有页面都已经完全打通。为了避免你一上来就踩坑，可以按下面理解：

| 模块 | 当前状态 | 说明 |
| --- | --- | --- |
| `Overview` 总览页 | 可用 | 已接入系统状态、统计、活动、最近实验，并可从这里新建实验 |
| `Experiments` 实验列表 | 可用 | 可查看已创建实验并进入详情页 |
| `Experiment Detail` 实验详情 | 基本可用 | 可查看步骤、状态，并发起“执行实验”；AI 分析入口已接后端聊天接口，但展示仍偏粗糙 |
| 浮动 `ChatWindow` / 总览里的知识库 Chat | 可试用 | 能调用 `/api/chat`，后端不可用时会自动降级到本地 fallback 对话 |
| `Settings` 设置页 | 可用 | 主要是前端本地设置，保存在浏览器 `localStorage` |
| `Dashboard` 运行监控页 | 半成品 | 一部分基于真实健康检查和数据目录，一部分仍是模拟数据 |
| `Diagnostics` 诊断页 | 半成品 | 心跳开关已接入监控接口，但页面展示字段与后端返回结构还没有完全对齐 |
| `Templates` 模板页 | 后端有、前端未完全对齐 | 模板后端接口存在，但前端当前请求路径与后端前缀不一致 |
| `Knowledge Hub` 页面 | 演示态 | 当前搜索结果主要是 mock 数据；真正知识检索能力更多体现在后端 API 和浮动 Chat |
| `Chat` 独立聊天页 | 演示态 | 整页聊天使用 mock store，不是当前最可靠的聊天入口 |
| `Optimization` 优化页 | 演示态 | 页面和 store 主要使用 mock 数据 |
| `Agent Control` Agent 控制页 | 演示态 | 当前状态、日志、按钮逻辑主要是 mock，未与后端正式打通 |

如果你想先真正把系统跑起来并体验现有主流程，建议优先使用：

1. `Settings`
2. `Overview`
3. `Experiments`
4. `Experiment Detail`
5. 浮动聊天窗 / 总览里的知识库 Chat

## 3. 启动前准备

### 3.1 依赖

- Python `3.11` 到 `<3.14`
- `uv`
- Node.js `18+`
- `npm`

### 3.2 安装后端依赖

```bash
cd AutoHySeeker
uv sync
```

### 3.3 配置环境变量

先复制：

```bash
cp .env.example .env
```

至少需要确认：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `DEFAULT_MODEL`
- `API_PORT`

## 4. 端口必须先统一

这是当前最容易把人绕晕的地方。代码里有几套不同的默认值：

- 后端配置默认端口：`8200`
- `.env.example` 里写的是：`8100`
- 前端设置页默认 API 地址：`http://localhost:8100`
- Vite dev proxy 当前指向：`http://127.0.0.1:8101`

推荐你统一成下面这一套：

### 推荐端口方案

- `AutoHySeeker` 后端：`8200`
- `MicroHySeeker` 后端：`8100`

### 推荐操作

1. 把 `AutoHySeeker/.env` 里的 `API_PORT` 改成 `8200`
2. 把 `AutoHySeeker/frontend/vite.config.ts` 里的 `/api` 代理目标改成 `http://127.0.0.1:8200`
3. 打开前端后，在 `Settings -> General` 里把 `API Base URL` 改成 `http://localhost:8200`

如果这三处不统一，会出现这些现象：

- 总览页、实验页、详情页请求不到后端
- 设置页里 axios 请求和页面里的原生 `fetch('/api/...')` 指向不同端口
- 有些页面能打开，有些页面会报网络错误

## 5. 启动方式

### 5.1 启动 AutoHySeeker 后端

推荐：

```bash
cd AutoHySeeker
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8200 --reload
```

启动后检查：

- API 文档：`http://localhost:8200/docs`
- 健康检查：`http://localhost:8200/health`

### 5.2 启动前端

```bash
cd AutoHySeeker/frontend
npm install
npm run dev
```

默认前端地址通常是：

- `http://localhost:5173`

### 5.3 如果还要联动 MicroHySeeker

要让“执行实验”真的往硬件层转发，还需要：

- `MicroHySeeker` 自己的后端在线
- 默认地址为 `http://localhost:8100`

否则 AutoHySeeker 会进入本地 stub 行为：实验状态会被标记为 `running`，但不代表硬件真的开始执行。

## 6. 第一次使用建议顺序

### 第一步：先进 Settings

建议先打开 `Settings -> General`，检查：

- `API Base URL`
- `Polling Interval`
- `Request Timeout`
- `Diagnostics` 默认目录
- `Context History` 默认目录

说明：

- 这些设置主要保存在浏览器本地
- 它们影响前端请求行为，不会自动改后端 `.env`

### 第二步：打开 Overview

`Overview` 是当前最适合作为入口的页面。你会在这里看到：

- AutoHySeeker / MicroHySeeker / 数据库 / Agents 状态
- 实验总数、今日实验数、成功率、平均耗时
- 最近活动
- 系统健康图
- 快速入口

你最应该用的两个按钮：

- `开始一个新实验`
- `打开知识库 Chat`

### 第三步：用真实 Step Editor 创建实验

从 `Overview` 打开实验创建框后，当前推荐按照真实步骤来建实验，而不是只写一个笼统“做 CV”。

当前支持的步骤类型：

| step_type | 用途 |
| --- | --- |
| `prep_sol` | 配液 / 混液 |
| `transfer` | 移液 / 转移 |
| `flush` | 冲洗 |
| `echem` | 电化学测试 |
| `blank` | 空白 / 占位 |
| `evacuate` | 排空 |

各步骤大致这样填：

- `prep_sol`：总液量、选中哪些溶液、目标浓度、是否溶剂、注液顺序
- `transfer`：泵地址、方向、转速、体积模式或时长模式
- `flush`：flush 通道、转速、单轮时长、循环次数
- `echem`：选择 `CV / LSV / i-t / EIS / ADT`，再填对应参数
- `blank`：现在主要就是备注和占位
- `evacuate`：本质上是更明确的排空步骤

建议：

1. 先写实验目标，再排步骤
2. 每一步都写清楚备注
3. 尽量不要把多个动作揉成一个步骤

### 第四步：到 Experiments 页查看清单

创建完成后，去 `Experiments` 页面可以：

- 搜索实验
- 按卡片查看状态、描述、当前步骤摘要
- 点进详情页

### 第五步：在 Experiment Detail 页执行实验

详情页里你能看到：

- 状态标签
- 创建 / 开始 / 完成时间
- 当前步骤
- 全部步骤链
- 结果摘要
- AI 解读区

如果实验状态还是 `created`，页面上会出现执行按钮。

它的行为是：

1. AutoHySeeker 把实验状态改成 `running`
2. 尝试把请求转发到 `http://localhost:8100/api/experiment/start`
3. 如果 MicroHySeeker 不在线，则回退为本地模式

所以这里一定要记住：

- 页面显示“开始执行”不等于硬件已经真正开始
- 真正的硬件执行，以 `MicroHySeeker` 是否在线为准

### 第六步：使用知识库 Chat

当前更推荐用这两个聊天入口：

- 右下角浮动聊天窗
- `Overview` 里的知识库 Chat

它们的特点：

- 能尝试读取后端聊天历史
- 能把问题发给 `/api/chat`
- 后端不可用时不会完全瘫掉，会自动转到本地 fallback

适合问的问题：

- 当前 step 为什么这么设计
- 下一轮实验优先该改哪个变量
- `transfer` / `flush` / `echem` 异常怎么排查
- 某种 technique 该怎么选

不太建议优先使用的入口：

- `/chat` 独立聊天页

原因很简单：它现在主要还是 mock 会话和 mock 消息流。

## 7. 各页面怎么理解

### 7.1 Overview

适合做：

- 看全局状态
- 新建实验
- 打开知识库 Chat
- 看最近运行中的实验

注意：

- 部分按钮只是触发后端占位能力
- “方案设计建议”当前还没有接入真正智能建议，只会返回开发中提示

### 7.2 Experiments

适合做：

- 浏览全部已创建实验
- 搜索实验
- 进入详情

注意：

- 这里列出的实验来自 AutoHySeeker 进程内存
- 后端重启后，这些通过 UI 创建的实验记录会丢失

### 7.3 Experiment Detail

适合做：

- 看步骤链和当前步骤
- 发起执行
- 发起一次针对该实验的聊天分析

注意：

- AI 分析区已经连了聊天接口
- 但前端展示仍不算完全打磨好，返回内容可能比较粗

### 7.4 Dashboard

适合做：

- 粗看系统健康和最近数据目录

注意：

- 这里的实验进度图、优化状态、通知等有明显模拟成分
- `Emergency Stop` 相关接口目前也不是完整打通状态

### 7.5 Diagnostics

适合做：

- 开关 heartbeat monitoring
- 观察监控页是否能拉到状态

注意：

- 后端真实诊断能力更接近 `/diagnostics/invoke`
- 诊断页展示结构和监控后端返回结构仍有未完全对齐的地方

### 7.6 Templates

后端能力现状：

- 支持列出、创建、更新、删除模板
- 支持模板实例化

但当前前端页面需要特别注意：

- 前端请求的是 `/api/templates`
- 后端实际暴露的是 `/templates`

也就是说，模板页面目前不能视为已经稳定可用。

另外，模板“一键使用”还有两个现实问题：

- 前端期待返回字段 `experiment_id`
- 后端当前返回的是 `exp_id`

所以当前更稳妥的理解是：

- 模板后端已经有基础能力
- 前端模板页仍在对接中

### 7.7 Knowledge Hub

它更像产品展示页，而不是当前最可靠的知识检索入口。

现状：

- 页面搜索结果主要是 mock 数据
- 右侧嵌入聊天窗更值得参考
- 真正的知识检索能力主要体现在后端 `/api/knowledge/*` 路由

### 7.8 Optimization

当前页面以 mock 配置、mock 状态和 mock 历史为主。

后端其实已经有优化 API：

- `/api/optimization/status`
- `/api/optimization/start`
- `/api/optimization/stop`
- `/api/optimization/history`
- `/api/optimization/reset`

但前端这个页面还没有按当前后端接口完全接好。

### 7.9 Agent Control

当前更适合拿来理解产品概念，不适合当成真实运维面板。

因为：

- 状态卡片是 mock
- 日志是 mock
- 启停按钮也还是占位

### 7.10 Settings

这里是当前最实用的辅助页面之一。

能做的事：

- 改前端 API Base URL
- 改轮询间隔和超时
- 配置本地 Agent 模型偏好
- 导出 / 导入 Agent 配置
- 切换语言、主题、字体大小、紧凑模式

注意：

- 这些主要是前端本地配置
- 改这里，不等于自动改后端真实模型配置

## 8. 数据保存在哪里

这个部分非常重要。

### 8.1 会持久化到磁盘的

- 模板：仓库根目录下的 `templates/*.json`
- 运行日志：`AutoHySeeker/logs/autohyseeker.log`
- `MicroHySeeker` 风格实验数据目录：仓库根目录下的 `data/YYYY-MM-DD/...`

### 8.2 只保存在进程内存的

- `Overview` / `Experiments` 里通过 `/api/experiments/create` 创建的实验记录
- 系统活动日志
- 后端聊天历史

这意味着：

- AutoHySeeker 后端一重启，内存里的实验和活动记录会清空

### 8.3 只保存在浏览器本地的

- Settings 页面里的系统设置
- Agent 配置页设置
- 一部分聊天 fallback 历史

## 9. 如果你想直接走 API

当前比较实用的几个接口如下。

### 9.1 基础检查

```bash
curl http://localhost:8200/health
curl http://localhost:8200/api/system/status
curl http://localhost:8200/api/system/health
```

### 9.2 创建并查看实验

```bash
curl -X POST http://localhost:8200/api/experiments/create -H "Content-Type: application/json" -d "{\"name\":\"Fe3+ CV test\",\"description\":\"manual run\",\"tags\":[\"cv\"],\"steps\":[{\"step_type\":\"echem\",\"description\":\"CV baseline\",\"params\":{\"ec_settings\":{\"technique\":\"CV\"}}}]}"
```

```bash
curl http://localhost:8200/api/experiments
curl http://localhost:8200/api/experiments/recent?limit=10
```

### 9.3 执行实验

```bash
curl -X POST http://localhost:8200/api/experiments/detail/exp_xxx/execute
```

### 9.4 聊天分析

```bash
curl -X POST http://localhost:8200/api/chat -H "Content-Type: application/json" -d "{\"message\":\"请分析这个实验的关键风险\",\"experiment_id\":\"exp_xxx\"}"
```

### 9.5 知识检索

```bash
curl "http://localhost:8200/api/knowledge/search?query=CV%20noise&top_k=5"
curl "http://localhost:8200/api/knowledge/faults?fault_type=communication_timeout&top_k=5"
```

### 9.6 诊断

```bash
curl -X POST "http://localhost:8200/diagnostics/check-health?data_dir=data&recent_n=10"
```

## 10. 当前最值得你真的去用的主流程

如果你今天就想把 AutoHySeeker 用起来，建议只走下面这条线：

1. 统一端口到 `8200`
2. 启动后端和前端
3. `Settings` 里确认 `API Base URL`
4. 在 `Overview` 新建实验
5. 到 `Experiments` 看实验卡片
6. 进入 `Experiment Detail`
7. 需要时点“开始执行”
8. 用浮动聊天窗追问设计理由、异常和下一轮建议

这条线是当前代码里最接近“真实可用”的路径。

## 11. 当前已知限制

- 实验记录目前是内存存储，不是数据库存储
- 前端端口和代理配置默认值不统一，首次使用前必须手动统一
- 模板前端与后端接口前缀未完全对齐
- 知识库页面、独立聊天页、优化页、Agent 控制页仍有明显 mock 成分
- 实验执行在 MicroHySeeker 不在线时会退化成本地 stub
- 设置页里的 Agent 模型偏好主要是前端本地状态，不代表真实后端模型调度已经全接好

## 12. 你可以把它当成什么

现阶段更合适的定位是：

- 一套“AI 实验工作台”
- 一个正在成型的 Web 控制面板
- 一个比纯后端 API 更好用的实验组织入口

但还不能把它完全当成：

- 已经全链路打通的正式生产系统
- 所有页面都已完成联调的最终版产品

如果你后面要继续补这个系统，建议优先补的不是页面样式，而是：

1. 端口与代理统一
2. 模板页前后端对齐
3. Chat / Knowledge / Optimization 去 mock
4. 实验记录持久化
5. Dashboard / Diagnostics 字段对齐
