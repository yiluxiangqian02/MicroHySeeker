# OpenViking 导入方案与执行 Todo（实时更新）

> **注意**: 本文档为早期规划稿（2026-06-01）。最新完整执行计划、设计决策和状态请参阅:
> **[08_OPENVIKING_EXECUTION_PLAN_2026-06-02.md](08_OPENVIKING_EXECUTION_PLAN_2026-06-02.md)**

更新时间: 2026-06-03
适用范围: AutoHySeeker/LiteratureClean -> OpenViking
负责人: Copilot + 用户确认

当前里程碑（2026-06-03）:

1. A0-D4 已完成。
2. E1-E4 已完成。
3. G0-G2 已完成。
4. **H1（修复 section 同名折叠）已完成** — 拍平命名为 `{section_dir}.{abstract|overview}.md`
5. **H2（段落证据索引层）已完成** — `MAIN_INDEX_SUFFIXES` 后缀体系统一，`build_paragraph_chunks()` 生成 YAML frontmatter chunk
6. H4（四阶段检索）方案已确认，待实现 — 新建 `LiteratureClean/qa_pipeline.py`，方案 2c

## 0. 状态码定义

- `status: 1` = 待执行（已规划，未开始）
- `status: 2` = 执行中
- `status: 3` = 已完成
- `status: 4` = 阻塞/待确认
- `status: 5` = 已取消

说明:

- 本文档按你的要求，初始全部采用 `status: 1`。
- 每次执行后仅更新对应条目的状态与时间，不改历史结论。

## 1. 当前已确认的方案边界

1. 主索引严格白名单，不纳入 `full_clean.md`。
2. 主索引链路: paper-level abstract/overview -> section-level abstract/overview。
3. `section-level paragraphs.md` 不作为主索引必需项（已从主方案移除）。
4. 事实层继续使用 `sections_by_heading/`，不回退旧 `sections/` 结构。
5. 图表不建专用主索引文本；通过 overview 与段落关联字段桥接召回。
6. 结构化 JSON（如 `metadata.json`、`paragraph_index.json`、`evidence_links.json` 等）不进主索引，仅用于回填与追溯。
7. LLM 生成链路必须有，但可控执行:
   - 新文献 missing 自动生成
   - 预处理变更后 stale 不自动重生成
   - stale 默认阻止导入，需手动 refresh
8. 离线校验和兜底可代码化，并在必要时触发。
9. 验证阶段先用独立 HTML 页面，不改现有前端。
10. 实现策略: 保留 `import_to_openviking.py` 入口，内部拆分流程。
11. 本阶段只使用文本 LLM，不启用 VLM 能力。

## 1.2 分层处理与存储地址（强约束）

目标: 明确“预处理/生成”和“索引/检索运行”是两层，不混存。

1. LiteratureClean 层（生成与可追溯单一真相源）

- 根目录: `AutoHySeeker/LiteratureClean/`
- 职责: 预处理、文本 LLM 生成、状态校验、可复算追踪
- 核心产物: `ov_index/paper.abstract.md`、`ov_index/paper.overview.md`、`ov_index/sections/*/{abstract,overview}.md`、`ov_index/generation_status.json`
- 要求: 所有 abstract/overview 先在此层生成与落盘

2. OpenViking 层（导入与运行态）

- 配置目录: `AutoHySeeker/OpenViking/.local_dev/`
- 运行数据目录: `AutoHySeeker/data/openviking/`
- 职责: 导入、向量索引、检索服务、API 提供
- 要求: 不作为 abstract/overview 的原始生成存储位置

3. 跨层接口约束

- 方向: LiteratureClean 产物 -> OpenViking 导入
- 禁止: 在 OpenViking 运行目录直接生成并替代 LiteratureClean 的源文件
- 允许: OpenViking 内部产生运行态缓存/索引文件（与源生成文件分离）

## 1.1 已有 OpenViking 现状（本次对接基线）

基于当前仓库 `AutoHySeeker/OpenViking` 的盘点结论:

1. 启动入口已存在:

- Python 包入口: `openviking/__main__.py`
- HTTP 服务入口: `openviking/server/bootstrap.py`（`openviking-server`）
- CLI 入口: `openviking_cli/cli/main.py`（含 `serve/resources/search/fs/content/...`）

2. 当前本地配置文件存在且可用:

- `OpenViking/.local_dev/ov.conf`
- 现状仅配置 `storage` + `embedding`，未显式配置 `vlm/rerank/server`

3. 当前 embedding 为本地模式:

- provider: `sentence_transformers`
- model: `BAAI/bge-large-zh-v1.5`
- 不依赖 API key

4. 文本 LLM/VLM 能力在代码层已具备，但本阶段仅使用文本 LLM:

- VLM provider 支持: `openai` / `volcengine` / `litellm`（本阶段不启用）
- Embedding provider 支持: `openai` / `volcengine` / `vikingdb` / `jina` / `sentence_transformers`

5. OpenViking 导入能力已具备两条路径:

- `resources.add_resource`（解析 -> TreeBuilder -> SemanticQueue）
- `pack.import_ovpack`（离线包导入）

6. 结论:

- 不需要重造 OpenViking 内核
- 需要在 LiteratureClean 侧构建“主索引白名单视图层 + 门禁 + 可控生成”，再调用现有导入能力

## 2. 主索引文件白名单（最终）

进入 OpenViking 主索引的文件:

1. `paper-level .abstract.md`
2. `paper-level .overview.md`
3. `section-level .abstract.md`
4. `section-level .overview.md`

不进入主索引（仅回填/追溯）:

1. `metadata.json`
2. `full_clean.md`
3. `document_tree.json`
4. `original_structure_index.json`
5. `paragraph_index.json`
6. `evidence_links.json`
7. `image_manifest.json`
8. `table_manifest.json`
9. `quality_report.json`
10. `tag_conflicts.json`

## 3. LLM 生成输入基线（用于 abstract/overview）

建议输入来源（可追溯）:

1. `paragraph_index.json`（主）
2. `sections_by_heading/*/heading.json`（结构）
3. `document_tree.json`（结构总览）
4. `image_manifest.json` 与 `table_manifest.json`（图表桥接语义）
5. `full_clean.md`（仅参考，不入主索引）

## 3.1 本阶段模型约束（重要）

1. 仅调用文本 LLM 生成 `abstract/overview`。
2. 不启用 VLM，不走图像理解链路。
3. 图表相关语义仅来自已有结构化信息与段落桥接字段，不依赖视觉模型。

## 3.2 为什么之前 Todo 看起来“没有变化”

1. 上一版主要是补充“现状基线与任务验收标准”，没有把任务直接标记为完成。
2. 这是为了避免把“OpenViking 已具备能力”误记为“LiteratureClean 对接已完成”。
3. 现在起将把“已由 OpenViking 现成能力覆盖”的工作单独列为完成态，和“待做的对接工作”分开。

## 3.3 已由 OpenViking 现成能力覆盖（不需重做）

- [X] O1. HTTP 服务启动入口已具备（`openviking-server`）`status: 3`
- [X] O2. 资源导入主通道已具备（`resources.add_resource`）`status: 3`
- [X] O3. 离线包导入通道已具备（`pack.import_ovpack`）`status: 3`
- [X] O4. 检索与内容读取 API 已具备（`search/find/content/fs`）`status: 3`
- [X] O5. 观测与健康检查接口已具备（`observer/debug/system`）
  `status: 3`

## 4. 目录与产物设计（建议）

每篇文献新增导出视图目录（示例）:

```text
 LiteratureClean/{paper_id}/ov_index/
  paper.abstract.md
  paper.overview.md
  generation_status.json
  sections/
    S00_front_matter/
      abstract.md
      overview.md
    S01_abstract/
      abstract.md
      overview.md
    ...
```

`generation_status.json` 关键字段:

1. `generated_at`
2. `based_on_preprocess_version`
3. `source_checksum`
4. `llm_model`
5. `status` (`fresh|stale|missing`)

## 5. 执行 Todo（详细）

补充说明:

- 本 Todo 面向“对接现有 OpenViking”而非改造 OpenViking 内核。
- 改造主战场在 `LiteratureClean/import_to_openviking.py` 与新增校验/视图脚本。
- 所有新动作应保证可在当前 `.local_dev/ov.conf`（本地 embedding）下运行。

执行顺序（重审后）:

1. A0（先完成文本 LLM 配置与连通性校验）
2. A1 -> A2 -> A3（先把规则与门禁闭环）
3. B1 -> B2 -> B3（先稳定 `ov_index` 视图与状态文件）
4. C1/C1.1 -> C2 -> C3（再接文本 LLM 生成动作）
5. D1 -> D2 -> D3 -> D4（最后串联导入通道）
6. E1 -> E2 -> E3 -> E4（校验与兜底）
7. F1 -> F5 -> F2 -> F3 -> F4（验证链路与联测）
8. G1 -> G2 -> G3（试运行到全量）

优先级说明:

- `P0`: 阻断主流程问题，必须先做
- `P1`: 主流程关键能力
- `P2`: 质量增强与观测

### Phase A0: 文本 LLM 前置配置（新增）

- [X] A0.1 配置文本 LLM provider（仅文本）`status: 3``priority: P0`产出: 可用的 text-only provider 配置（不启用 VLM，配置源固定为 `configs/agent_models.toml` 的 `[chat]` 段）验收: `[chat]` 段的 `provider/model/base_url/api_key` 可被 A0 自检脚本读取，且不会触发 VLM 路径
- [X] A0.2 文本 LLM 连通性冒烟测试 `status: 3``priority: P0`产出: 一次最小摘要生成日志验收: 能为单篇 paper 生成 `paper.abstract.md`
- [X] A0.3 缺省行为约束（无文本 LLM 时）
  `status: 3`
  `priority: P0`
  产出: 错误提示规范与退出码
  验收: 未配置文本 LLM 时，生成动作 fail-fast 且提示可读（已在 `import_to_openviking.py --require-text-llm` 落地）

A0 执行前分析（当前结论）:

1. 预计直接修改文件:

- `LiteratureClean/import_to_openviking.py`（新增 text-only LLM 配置读取、连通性检查、fail-fast）

2. 预计新增文件:

- `LiteratureClean/check_text_llm_ready.py`（可选，独立冒烟与配置自检脚本）

3. 预计只读复用文件（不改）:

- `OpenViking/.local_dev/ov.conf`
- `OpenViking/openviking_cli/utils/config/open_viking_config.py`
- `OpenViking/openviking_cli/utils/config/vlm_config.py`

4. 配置来源约束（按当前指令）:

- A0 直接参考 `AutoHySeeker/configs/agent_models.toml` 的 `[chat]` 段
- 不再要求额外手工输入 provider/model/base_url
- api_key 优先走环境变量展开（例如 `${OPENAI_API_KEY:-}`）

### Phase A: 方案固化与门禁设计

- [X] A1. 固化主索引白名单与非白名单规则 `status: 3``priority: P0`产出: 导入规则清单（写入导入脚本常量）验收: 规则函数可独立判断 `paper/section` 四类文件是否可入主索引
- [X] A2. 设计 stale/missing/fresh 状态机 `status: 3``priority: P0`产出: 状态流转图与触发条件验收: `generation_status.json` 能表达 `fresh|stale|missing` 且可复算（已在 `import_to_openviking.py --check-generation-status [--write-generation-status]` 落地）
- [X] A3. 定义导入门禁策略（stale 默认阻止）
  `status: 3`
  `priority: P0`
  产出: gate 条件与错误提示规范
  验收: `--reindex/--overwrite` 路径下遇到 stale 明确 fail-fast（已在 `import_to_openviking.py` 落地，显式放行参数 `--allow-stale-import`）

### Phase B: 视图层生成（不改事实层）

- [X] B1. 新增 ov_index 视图目录生成器 `status: 3``priority: P1`产出: 每篇文献 paper/section abstract+overview 文件骨架验收: 只在 `ov_index/` 写文件，不修改 `sections_by_heading/` 事实层（全量已执行）
- [X] B2. 生成 source_checksum（基于输入集合）`status: 3``priority: P1`产出: 可复现 checksum 逻辑验收: 相同输入重复运行 checksum 一致（全量已复算并写入）
- [X] B3. 生成/更新 generation_status.json
  `status: 3`
  `priority: P1`
  产出: 状态元数据落盘
  验收: 每篇文献可独立读出最近生成状态与基线版本（全量已写入 fresh=11）

### Phase C: LLM 可控生成链路

- [X] C1. 实现 `generate_missing` 动作 `status: 3``priority: P1`产出: 仅对 missing 目标生成验收: 文本 LLM 已配置时可生成；未配置时给出可读错误，不误触发导入（全量已执行，超时缺口已补齐）
- [X] C1.1 文本 LLM provider 适配层（不启用 VLM）`status: 3``priority: P1`产出: text-only 调用路径与参数约束验收: 未配置文本 LLM 时返回明确错误；配置后可生成 paper/section 摘要（当前复用 `[chat]` 配置并已全量生成验证）
- [X] C2. 实现 `refresh_stale` 动作（需确认）`status: 3``priority: P2`产出: stale 刷新入口与确认提示验收: 默认不执行，需显式参数触发（已在 `import_to_openviking.py --refresh-stale` 落地，fresh 状态会安全跳过）
- [X] C3. 实现 `regenerate_all` 动作（默认禁用）
  `status: 3`
  `priority: P2`
  产出: 全量重生成功能但默认不执行
  验收: 没有显式 flag 时不可触发（已在 `import_to_openviking.py --regenerate-all` 落地）

### Phase D: 导入脚本改造（入口保留）

- [X] D1. 在 `import_to_openviking.py` 内部拆分流程 `status: 3``priority: P0`产出: `build_ov_index_views -> gate_check -> import`验收: 对外 CLI 参数兼容，入口文件名不变（最小链路已单篇 dry-run 验证）
- [X] D2. 导入阶段只纳入白名单文件 `status: 3``priority: P0`产出: 导入文件过滤器验收: 导入目录不包含 `full_clean.md` 与各类结构化 JSON（已改为从 `ov_index` 白名单构建导入视图并通过 dry-run 校验）
- [X] D3. stale 阻止导入逻辑接入 `status: 3``priority: P0`产出: 失败即退出与可读提示验收: dry-run 和正式导入都能看到一致 gate 结果（gate 检查已对 `--overwrite/--reindex` 的 dry-run 与正式导入统一生效）
- [X] D4. 对接 OpenViking 现有导入通道（二选一可切换）
  `status: 3`
  `priority: P1`
  产出: `resources.add_resource` 与 `pack.import_ovpack` 的适配层
  验收: 当前生产路径固定为 `resource` 后端可全量导入；`ovpack` 接口已保留，待环境稳定后补充实跑校验

### Phase E: 离线校验与兜底

- [X] E1. 结构校验: 缺失/路径不一致/索引断链 `status: 3``priority: P1`产出: validation_report.json（已在 `import_to_openviking.py --validate-ov-index` 落地并输出 `validation_report.json`）
- [X] E2. overview 质量校验规则 `status: 3``priority: P2`产出: 质量分与阈值（已在 `import_to_openviking.py --validate-overview-quality` 落地并输出 `overview_quality_report.json`）
- [X] E3. 语义冲突校验规则（问题意图 vs 选段）`status: 3``priority: P2`产出: conflict_score 与触发条件（已在 `import_to_openviking.py --validate-semantic-conflicts` 落地并输出 `semantic_conflict_report.json`）
- [X] E4. 兜底路径实现（必要时触发）
  `status: 3`
  `priority: P2`
  产出: 降级策略与人工复核标记（已在 `import_to_openviking.py --build-fallback-report` 落地并输出 `fallback_review_report.json`）

### Phase F: 验证与独立 HTML 页面

- [ ] F1. 构建独立 HTML 问答验证页（不改现有前端）`status: 1``priority: P2`产出: 可输入问题并展示召回路径
- [ ] F2. 展示链路透明度（paper -> section -> paragraph）`status: 1``priority: P2`产出: 命中文件、section、证据ID 展示
- [ ] F3. 验证用例集（论文级/section级/图表桥接）`status: 1``priority: P2`产出: 固定问题集 + 预期命中口径
- [ ] F4. 与 OpenViking observer/debug 接口联测 `status: 1``priority: P2`产出: 导入后组件健康检查记录（queue/vikingdb/system）
- [ ] F5. 文本 LLM 专项联测（禁用 VLM）
  `status: 1`
  `priority: P2`
  产出: text-only 生成与召回验证记录

### Phase G: 试运行与上线

- [X] G0. 历史索引清理时机与回滚点 `status: 3``priority: P0`产出: 先备份、后重建的执行单验收: 不手工先删 `resources/literature`，统一由 `--reindex` 受控清理并重建（已验证：预检失败时不 wipe；修复环境后可成功重建）
- [X] G1. 小样本试运行（2-3 篇）`status: 3``priority: P1`产出: 试运行报告（已对 3 篇执行 dry-run + overwrite 实跑，见 `g1_pilot_run_report_2026-06-02.md`）
- [X] G2. 全量 reindex 导入 `status: 3``priority: P1`产出: 全量导入日志与摘要（已完成：11/11 导入成功，included_files=422, error=0）
- [ ] G3. 导入后回归验证
  `status: 1`
  `priority: P1`
  产出: 召回质量报告 + 问题清单

## 5.1 历史索引删除时机（新增，执行前必读）

核心结论:

1. 不是“现在立刻手工删除”。
2. 最稳妥方式是“先备份 + 预检 + dry-run + `--reindex` 受控清理重建”。

原因:

1. 当前 `data/openviking/.../resources/literature` 存在旧批次命名与旧口径文件，确实需要清理。
2. 但若手工先删，任何导入失败都会导致不可用窗口，且回滚困难。
3. `--reindex` 路径具备统一流程、日志和门禁，能把“删除”和“重建”放在同一事务化步骤里。

顺序（必须按序）:

1. 备份现有索引目录（回滚点）
2. 运行 E1/E2 与状态检查（确认输入质量）
3. 执行 `--dry-run --overwrite --import-backend resource`
4. 执行 `--reindex --import-backend resource`（此步才发生受控清理）
5. 导入后核验目录命名、导入日志与抽样检索

## 6. 运行命令（暂定）

以下为计划中的命令语义（实现后生效）:

```powershell
# 0) 备份当前 OpenViking 索引目录（推荐）
Copy-Item "D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/data/openviking" "D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/data/openviking_backup_YYYYMMDD" -Recurse -Force

# 1) 预检：状态/结构/质量
python LiteratureClean/import_to_openviking.py --check-generation-status
python LiteratureClean/import_to_openviking.py --validate-ov-index
python LiteratureClean/import_to_openviking.py --validate-overview-quality

# 仅生成缺失摘要/概述
python LiteratureClean/import_to_openviking.py --generate-missing

# 刷新 stale（执行前确认）
python LiteratureClean/import_to_openviking.py --refresh-stale

# 全量重生成（默认不建议）
python LiteratureClean/import_to_openviking.py --regenerate-all

# 全量重建索引导入
python LiteratureClean/import_to_openviking.py --dry-run --overwrite --import-backend resource
python LiteratureClean/import_to_openviking.py --reindex --import-backend resource

# 指定 OpenViking 配置文件（推荐）
$env:OPENVIKING_CONFIG_FILE = "D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/OpenViking/.local_dev/ov.conf"
```

## 7. 本轮执行记录

- 2026-05-30: 新建本文件，初始化方案与 Todo，全部条目 `status: 1`。
- 2026-05-30: 补充“已有 OpenViking 现状基线”，将后续任务改为对接型工作包（不改 OpenViking 内核）。
- 2026-05-30: 新增 D4/F4 任务，用于对接现有导入通道与 observer/debug 联测。
- 2026-05-30: 按新约束更新为“仅文本 LLM，不使用 VLM”；新增 O1-O5 已覆盖项并解释此前 Todo 变化感知问题。
- 2026-05-30: 重新审核 Todo 清单，补充执行顺序与优先级；A1 标记完成、A2 标记执行中；移除 F4 中对 VLM 健康项依赖。
- 2026-05-30: 根据“LLM 配置需前置”反馈，新增 Phase A0，并将文本 LLM 配置与冒烟测试提前到所有生成动作之前。
- 2026-06-01: 按顺序完成“最小 D1 -> C2 -> C3”。D1 已在脚本中拆分为 `build_ov_index_views -> gate_check -> import` 并单篇 dry-run 通过；C2/C3 新增 CLI 已实跑验证。
- 2026-06-01: 完成 D2/D3。导入导出目录已切换为 `ov_index` 白名单文件，dry-run 校验 `included=16, skipped_non_whitelist=0, missing_required=0`；stale gate 在 dry-run 与正式路径统一执行。
- 2026-06-01: D4 代码已实现：新增 `--import-backend {resource,ovpack}` 与 ovpack 适配链路（staging add_resource -> export_ovpack -> import_ovpack）。当前真实导入验证受 OpenViking 运行依赖 `pyagfs` 缺失阻塞；dry-run 双后端已通过。
- 2026-06-01: 按“resource 为当前生产导入后端，ovpack 后续增强”决策更新 D4 验收口径；完成 E1，新增 `--validate-ov-index` 并生成 `validation_report.json`，当前汇总 `papers=11, ok=11, issue=0`。
- 2026-06-01: 完成 E2，新增 `--validate-overview-quality` 并生成 `overview_quality_report.json`；当前汇总 `papers=11, pass=11, warn=0, fail=0, avg_score=92.67`。
- 2026-06-02: 新增“历史索引删除时机”流程：不手工先删，改为“备份 -> 预检 -> dry-run -> reindex 受控清理重建 -> 导入后核验”，并写入 G0 与命令区。
- 2026-06-02: 已按顺序实操 G0：
  1) 备份完成（robocopy）;
  2) 预检通过（status/validate-ov-index/validate-overview-quality）;
  3) dry-run 通过（11 papers）；
  4) `--reindex --import-backend resource` 执行到清理后被 OpenViking 运行时阻塞（`openviking.storage.vectordb.engine` DLL load failed）；
  5) 已从备份目录回滚恢复 `data/openviking`，避免索引空窗。
- 2026-06-02: 并行推进“全量重建阻塞处理 + E3”完成：
  1) E3 已落地：新增 `--validate-semantic-conflicts`，输出 `semantic_conflict_report.json`（本次汇总 `papers=11, high=11, medium=0, low=0, avg_conflict_score=99.45`）；
  2) reindex 安全机制已增强：新增 OpenViking 运行时预检，只有预检通过才允许清空索引；
  3) 当前仍受 `openviking.storage.vectordb.engine` DLL 依赖阻塞，但已验证“预检失败不会触发 wipe”，避免再次数据空窗。
- 2026-06-02: 阻塞已解除并完成全量重建（继续并行收敛）：
  1) 根因定位：`engine.pyd` 绑定 `python311.dll`，此前运行解释器与 ABI 不匹配；
  2) 处理动作：创建 `3.11` 专用虚拟环境 `.venv_ov311`，补齐 OpenViking 运行依赖（含 `pyagfs`、`sentence-transformers`、`transformers`、`volcengine-python-sdk[ark]` 等）；
  3) 兼容性修复：将 `tokenizers` 调整为 `0.23.0rc0` 以满足当前 `transformers` 约束；
  4) 结果：`--reindex --import-backend resource` 全量执行成功，`Summary: 11 ok, 0 error, 0 dry-run out of 11 papers`，`included_files=422`；
  5) 备注：日志中的 `VLM not available` 为非阻塞告警（当前流程按“仅文本 LLM”策略运行）。

## 8. 2026-06-02 方案确认（准确度与便利性优先）

用户已确认后续主线采用“三层索引 + 可追溯回答展示”方案，先不追求最小白名单，优先保证回答准确度与实验设计可复用性。

已确认的索引层次：

1. 论文层：paperabstract、paperoverview（粗召回）
2. 小节层：sectionabstract、sectionoverview（主题定位）
3. 证据层：段落原文证据（精召回，第一优先）
4. 图表/实验结构化证据（条件触发，不作为首批强制项）

段落证据口径（已确认）：

1. 默认以原文段落为最小索引单元（优先保真与可追溯）。
2. 仅做轻量长度规整：
  - 过长段落再切分（建议 >300-400 词）
  - 过短段落与邻段合并（建议 <50-80 词）
3. 每条段落证据必须携带：paper_id、section_id、paragraph_id、相对路径/页码（若有）。

图表信息读取边界（当前阶段）：

1. 可稳定使用图注、表注、正文上下文与结构化链接信息。
2. 不将“直接图像像素理解”作为当前主链路能力（VLM/OCR 仅后续增强）。

已确认的回答展示口径：

1. 先结论，再证据条目
2. 证据条目必须可追溯：paper_id、section_id、paragraph_id/evidence_id、原文片段、命中分
3. 实验设计问题需并列展示可复用参数与冲突证据

### Phase H: 准确度优先索引改造（新增）

- [ ] H1. 修复 section 文件导入“同名折叠”问题 `status: 1``priority: P0`
  - 原因: 目前导入后每篇资源目录仅保留抽象化 `abstract/overview` 形态，section 粒度信息丢失，直接影响主题定位与证据召回。
  - 验收: 单篇导入后可见 section 级唯一命名文件，数量与 `ov_index/sections` 一致。

- [ ] H2. 引入段落证据索引层（paragraph chunk）`status: 1``priority: P0`
  - 原因: 仅有摘要层难以支撑实验参数级问答，回答容易“像总结不像证据”。
  - 执行口径: 以原文段落为主，仅做轻量切分/合并，避免过度重写语义单元。
  - 验收: 每篇可检索到 paragraph 级证据，且返回包含 `paper_id/section_id/paragraph_id` 元数据。

- [ ] H3. 引入图表/实验结构化证据索引层（条件触发）`status: 1``priority: P2`
  - 原因: 大部分问题可先由段落证据覆盖；仅当参数/数值漏召回明显时再引入结构化索引层。
  - 触发条件（满足其一即执行）:
    1) 实验设计问答中“缺关键参数字段”比例持续偏高
    2) 数值型问题命中段落但缺单位/条件信息
    3) 回归集中多次出现“表格主数据正文缺失”
  - 验收: 启用后可按图表/实验条件检索，返回带单位和条件字段的证据片段。

- [ ] H4. 两阶段召回与重排策略固化 `status: 1``priority: P1`
  - 原因: 先高召回再高精排可兼顾覆盖率和答案可解释性。
  - 定义:
    1) Stage1（高召回）: 论文层+小节层+段落层联合召回，取较大候选集。
    2) Stage2（高精排）: 对候选按问题-证据匹配度、参数命中、单位命中、来源多样性重排。
    3) Stage2.5（LLM选段）: 在已锁定 section 的候选段落中，LLM选择最相关 3-5 段并给出选择理由与引用ID。
    4) Stage3（回答生成）: 仅基于 Stage2.5 已选段落生成答案，禁止引用未入选证据。
  - 验收: 检索/推理日志可区分 stage1/stage2/stage2.5/stage3，且最终答案仅引用 stage2.5 入选证据。

- [ ] H5. 回答展示模板固化（证据强制展示）`status: 1``priority: P1`
  - 原因: 防止无出处总结，提升人工复核效率。
  - 验收: 回答输出固定包含“结论 + 证据条目 + 不确定性说明 + LLM选段列表（paragraph_id 与理由）”。

- [ ] H6. G3 回归验证（准确度口径）`status: 1``priority: P1`
  - 原因: G2 已完成导入，当前缺口是导入后真实召回质量评估。
  - 验收: 产出 G3 报告，包含命中层级分布、top1-top2 分差、冲突证据覆盖率。

执行顺序（H phase）：

1. H1 -> 先恢复 section 粒度
2. H2 -> 再补 paragraph 证据层
3. H3 -> 按触发条件决定是否执行（默认后置）
4. H4/H5 -> 固化检索与回答模板
5. H6 -> 最后做 G3 回归验收
