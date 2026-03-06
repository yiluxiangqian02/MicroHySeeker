# AutoHySeeker 待办配置清单

> 最后更新：2026-03-06  
> 状态：持续维护

---

## 🔴 必需配置（阻塞功能）

### 1. LLM API 配置

**用途：** C1 ContextualizeExperiment Skill 智能分析实验数据 + 文献上下文合成

**配置项：**
- `OPENAI_API_KEY` - API 密钥（当前为空）
- `OPENAI_BASE_URL` - API 地址（当前默认 `https://api.mcxhm.cn`）
- `DEFAULT_MODEL` - 默认模型（当前 `anthropic/claude-sonnet-4-6`）
- `FALLBACK_MODEL` - 降级模型（当前 `anthropic/claude-opus-4-6`）

**配置方式：** 在 `AutoHySeeker/.env` 文件中设置环境变量

**时机：** 后续实际使用 C1 Skill 时配置

**状态：** ⏳ 待配置

---

## 🟡 可选配置（增强功能）

### 2. OpenViking 知识库

**用途：** 存储和检索历史实验数据、学术文献，辅助 C1 Skill 上下文分析

**部署方式：** 本地部署（已确定）

**配置项：**
- 向量化模型（需选择，如 `text-embedding-ada-002` 或开源模型 `bge-large-zh`）
- OpenViking 服务地址
- 知识库存储路径

**当前行为：** 如果 OpenViking 不可用，系统会跳过知识库检索，不影响其他功能

**时机：** 需要知识库功能时配置

**状态：** ⏳ 待配置

---

## 🟢 已有默认值（可按需调整）

### 3. 数据路径配置

- `DATA_ROOT` - 实验数据目录（默认 `../data`）
- `LOG_ROOT` - 日志目录（默认 `./logs`）

**状态：** ✅ 已配置默认值

### 4. API 服务配置

- `API_HOST` - 服务监听地址（默认 `0.0.0.0`）
- `API_PORT` - 服务端口（默认 `8100`）
- `OPENAI_TIMEOUT_SECONDS` - LLM 请求超时（默认 `60` 秒）

**状态：** ✅ 已配置默认值

---

## 📋 降级逻辑确认

以下降级逻辑已实现，需确认是否符合预期：

1. **LangGraph 不可用** → 使用 `_FallbackGraph` 降级图
2. **OpenViking 不可用** → 跳过知识库检索
3. **LLM API 失败** → 重试 3 次，最后一次使用 `FALLBACK_MODEL`
4. **LLM API 未配置** → C1 Skill 返回原始数据块（无智能分析）

**决策：** 第 4 项需要在配置 LLM API 后移除降级逻辑

---

## 🔧 配置文件位置

- 环境变量：`AutoHySeeker/.env`
- TOML 配置：`AutoHySeeker/configs/*.toml`
- 代码配置：`AutoHySeeker/src/common/config.py`

---

## 📝 变更记录

| 日期 | 变更内容 | 操作人 |
|------|---------|--------|
| 2026-03-06 | 初始创建待办清单 | Pi |
