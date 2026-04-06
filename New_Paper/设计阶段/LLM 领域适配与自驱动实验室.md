# **大语言模型化学与材料领域适配及自驱动实验室容错机制深度研究报告**

## **1\. 大语言模型在化学与材料科学领域的持续预训练（CPT）范式演进**

在材料科学与化学发现的前沿交叉领域，大语言模型（LLM）的应用正经历从“通用文本生成”向“专业物理化学规律深度推理”的底层范式转变。由于通用大语言模型在初始的预训练阶段极少接触复杂的分子图谱、SMILES 表达式、晶体结构参数以及复杂的反应机理，其在处理具备高度专业性与严格语法约束的化学材料任务时，往往表现出显著的认知局限。自 2024 年下半年起，学术界与工业界开始密集且系统地采用持续预训练（Continual Pre-training, CPT）技术，将通用基座模型（尤其是 Qwen2/Qwen2.5、最新架构的 Qwen3 与 LLaMA-3 系列）深度适配于化学合成预测、电催化机理分析及自驱动实验室（SDL）的复杂逻辑规划等下游科学场景。

持续预训练的核心挑战在于如何在将化学分子实体、材料相变规律等高密度领域知识注入模型权重的过程中，最大限度地抑制对通用常识和逻辑推理能力的“灾难性遗忘”（Catastrophic Forgetting）。近期的前沿实践揭示了语料规模、领域/通用数据混合比例、词表扩展（Vocabulary Extension）以及基座模型架构（如混合专家架构 MoE）对 CPT 最终效果的决定性影响。

### **1.1 Qwen 系列的深度科学领域适配与多模态扩展**

Qwen2.5 与最新发布的 Qwen3 架构构成了当前科学领域 CPT 的核心基座族群。Qwen3 引入了高度复杂的混合专家（MoE）架构与“思考预算”（Thinking Budget）机制，其最高参数规模达到 235B，并支持高达 262k 的超长上下文窗口，同时能够处理多达 119 种语言与方言 1。Qwen3 的核心创新在于将“思考模式”（用于复杂多步科学推理）与“非思考模式”（用于快速上下文响应）集成在统一的框架内，模型能够根据任务复杂度动态分配算力，这在处理包含繁杂计算与机理推演的化学任务时展现出了对计算资源的极高利用率 2。在数学与科学基准测试中，基于 Qwen3 的适配模型不仅优于其前代 Qwen2.5，甚至在特定代码与数理推理基准上超越了部分闭源模型 1。

在专门针对科学研究场景的 Innovator-VL 模型中，研究团队以 Qwen2.5-7B 为基础，构建了一个高度透明且可复现的端到端科学预训练流水线。该模型使用了高达 300B Tokens 的三级质量控制科学语料进行 CPT 5。其架构设计极为独特：在总计 53.3B 的参数中，激活参数为 13.3B，模型包含一个共享的通用专家模块与 64 个专业的科学专家模块（每次激活其中 8 个）5。这种设计确保了科学法则的垂直灌输不会冲刷通用语言能力。量化评估结果显示，Innovator 在 30 项严苛的科学任务中，平均性能提升幅度高达 25%，胜率达到 70%，更为关键的是，其在通用视觉与语言任务上的性能保留率高达 99% 5。经过后续强化推理微调的 Innovator-Reason 模型，在解决复杂科学问题上的能力进一步跃升了 30% 5。这明确表明，通过精确的语料质量控制与专家路由机制，中等规模激活参数的通用模型完全可以通过 CPT 达到甚至超越超大规模模型的专业领域推理能力。

此外，针对特定科研文献解析与理解的挑战，研究者提出了 SciLitLLM 框架，该框架同样采用了基于 Qwen2.5（包括 7B 全参数与 14B QLoRA 变体）的 CPT 与监督微调（SFT）联合策略 8。传统上，仅使用 SFT 往往无法为模型提供足够的深层科学知识，因此 SciLitLLM 提出了一种双管齐下的方案。首先，在通用基座上应用科学语料进行 CPT，夯实知识底座；随后，研究团队利用大模型辅助生成技术（LLM-based synthesis）构建了一个包含多样化且高质量科学指令的全新数据集 SciLitIns，进行 SFT 对齐 8。通过这种 CPT-SFT 级联策略，SciLitLLM 在评估科学文献理解能力的 SciAssess 评测集上准确率提升了 4.0%，在涵盖更广泛指令的 SciRIFF 基准上提升了 10.1%，显著优于同等参数规模的其他开源模型 8。这证明了在 CPT 之后紧跟高质量、领域特定的 SFT，能够将深层注入的无结构科学知识有效转化为精准遵循复杂任务指令的能力。

| 论文标题、作者及发表时间 | 基座模型类型 / 算法名称 | 具体应用任务 (CPT 下游任务) | 核心创新点及量化效果 |
| :---- | :---- | :---- | :---- |
| **Innovator-VL** (Qwen Team 等, 2025\) 5 | 基座：Qwen2.5-7B 算法：基于 MoE 架构的三级质量控制 CPT 与 RL 推理强化 | 解决 30 项科学领域通用任务（涵盖多模态科学推理、复杂逻辑推演与视觉理解） | **创新点**：构建了共享通用专家与 64 个专业科学专家组合的混合架构，实现算力与知识的高效解耦。 **量化效果**：使用 300B Tokens 科学数据。在 30 个科学任务上平均准确率提升 25%，胜率 70%，保留 99% 通用任务性能。 |
| **SciLitLLM: How to Adapt LLMs for Scientific Literature Understanding** (Huang 等, 2024.08/ICLR 2025\) 8 | 基座：Qwen2.5-7B / 14B 算法：CPT 与 SFT 混合流水线，结合 LLM 驱动的合成数据生成 | 科学文献深度理解（多学科内容解析、学术实体提取、机理推理与长文本问答） | **创新点**：首创域指令合成数据集 SciLitIns，串联无监督预训练与指令对齐，解决小众学科指令数据匮乏问题。 **量化效果**：相比全通用参数，CPT+SFT 在 SciAssess 任务上准确率提升 4.0%，SciRIFF 评测基准提升 10.1%。 |

### **1.2 LLaMA-3 系列的词表扩展与化学/材料结构化知识适配**

针对化学领域的独特语法体系（如长串 SMILES 结构、复杂的有机物命名法则 IUPAC 等），单纯依赖文本维度的 CPT 往往面临分词器（Tokenizer）严重碎片化的问题。当通用分词器强行切分化学式时，会破坏分子的结构语义完整性，导致模型推理效率低下且容易产生化学幻觉。

一项于 2025 年公布的基于 LLaMA3-8B 的前沿研究展示了通过结合“词表扩展”（Vocabulary Extension）与 CPT 彻底解决该瓶颈的卓越方案 11。在该研究中，研究团队不仅采用了 LLaMA-3 架构以利用其优异的初始表征能力，更对其底层分词器进行了重构，将原始的 128k 词表扩展了 17,795 个新分子与结构专属 Token 11。为确保新旧词元表示空间的平滑过渡，新 Token 的嵌入向量被初始化为模型原有嵌入的均值。在 CPT 数据配比上，该模型使用了总计 16.37B Tokens 的高度混合调配语料 11。为了最大限度地抑制领域适应过程中的灾难性遗忘，语料库中包含了 10B Tokens 的 FineWeb 通用语料（占 50% 的训练权重），其余部分由 5B Tokens 的 USPTO 化学专利文本（其中 SMILES 字符串被特定标签包裹）、0.94B Tokens 的高质 S2ORC 学术论文，以及 0.43B 的 SMolInstruct 与 L+M-24 分子-文本对构成 11。

这种将通用语料与领域高密度语料进行精确均衡配比的策略，结合词表扩容，产生了极具震撼性的下游任务提升。量化评测显示，在 SMolInstruct 基准中：针对预测反应产物的正向合成任务（Forward Synthesis），基线模型的精确匹配数仅为 2，且生成了 612 个无效预测；而经过 CPT 与词表扩展的模型，其精确匹配数飙升至 2507，无效预测降至仅 8 个，Morgan 指纹相似度（FPS）从 0.44 大幅跃升至 0.84 11。在逆合成（Retrosynthesis）任务中，精确匹配从 0 激增至 1366 11。在复杂的化合物命名转换任务中（如 IUPAC 到 SMILES），精确匹配量更是从 1 提升到 1695 11。此外，在血脑屏障通透性（BBBP）等物理化学属性预测上，F1 分数从基线的 0.11 飙升至 0.88 11。这有力地证明了，对于化学这种具有“类代码”严谨语法的学科，词表扩展配合包含重放机制（Replay）的大规模 CPT，是实现大跨度推理能力飞跃的基石。

在材料科学方向，传统的 CPT 方法同样受限于通用语料预训练造成的表征偏差，尤其是在处理高熵合金、金属有机框架（MOF）等实体时。MELT（Materials-aware Continued Pre-training）架构提出了一种基于语义图谱扩展材料知识库的革命性 CPT 策略 13。研究团队首先提取了涵盖 150,000 篇材料科学顶刊文章与专利的语料库，并利用 ChemDataExtractor 与 Mat2Vec 等工具，将提取的化学实体映射到涵盖“结构-处理-性能-表现”全生命周期的知识关联图谱中 13。

MELT 摒弃了传统的随机掩码语言建模（Random Masking Language Modeling），转而创新性地采用了材料感知实体掩码（MEM）与基于课程表学习的实体学习（CEL）机制 13。这意味着模型在 CPT 阶段被迫专注于重构材料科学中最核心、低频但信息密度极高的化学式与工艺参数，而非简单的冠词或动词。在极具挑战的 MatSciNLP 下游任务评测中，经过仅仅 40,000 步的针对性预训练，MELT 在关系分类（RC）得分达到 86.0（超越随机掩码基线的 85.1），在槽位填充（SF）任务上更是达到 95.7 分的优异表现 13。消融实验进一步证实，如果在处理此类专业文本时缺乏图谱扩展与实体课程学习机制，其模型性能甚至会劣于普通的随机掩码策略。MELT 显著增强了模型对结构化科学概念的捕捉能力，使得其在支撑材料类别的分类准确率上获得了 25% 的相对跃升 13。

| 论文标题、作者及发表时间 | 基座模型类型 / 算法名称 | 具体应用任务 (CPT 下游任务) | 核心创新点及量化效果 |
| :---- | :---- | :---- | :---- |
| **Llama 3 8B Chemistry Domain Adaptation** (\[匿名团队\], 2025.11) 11 | 基座：LLaMA3-8B 算法：基于词表扩容的 CPT 与恒定学习率调控策略 | 化学合成反应预测（正向合成与逆合成推演）、化合物命名精确转换、物理化学性质预测 | **创新点**：针对 SMILES 扩展 17,795 个新化学专属 Token，并采用 50% 通用常识文本混合的严密策略防止模型逻辑崩溃。 **量化效果**：使用 16.37B Tokens。正向合成精确匹配从 2 跃升至 2507，Morgan 相似度由 0.44 飙升至 0.84，BBBP F1 指标从 0.11 增至 0.88。 |
| **MELT: Materials-aware Continued Pre-training...** (Junho Kim 等, 2024.10) 13 | 基座：通用预训练语言模型 (PLMs) 算法：材料感知实体掩码 (MEM) 与基于图谱的课程实体学习 (CEL) | 材料科学前沿文本挖掘（复杂命名实体识别 NER、实体关系分类 RC、工艺参数槽位填充 SF） | **创新点**：利用语义知识图谱覆盖材料范式，彻底放弃低效随机 Mask，强制模型学习高密度低频专业词汇。 **量化效果**：使用 150,000 篇材料专业文献。槽位填充达 95.7 分（超越基线），支撑材料分类准确率实现 25% 的相对提升。 |

## **2\. 小规模语料（50M-100M Tokens）CPT 的边界效应与电催化垂直领域破局策略**

在宏大的化学与材料科学版图中，尽管整体学术语料库庞大，但当研究焦点深入到高度细分的垂直子领域（如单一反应路径的电催化、特定晶体表面的析氢析氧机制等）时，高质量、无噪点的数据规模呈现断崖式下跌。通常，一个垂直方向的穷尽文献总量能够清洗出的有效语料仅维持在 50M 至 100M Tokens 的量级 17。前沿研究数据确凿地表明，在此等极其受限的数据规模下，直接套用传统的通用大模型 CPT 范式将遭遇严重的“边界效应”陷阱，甚至导致模型原有的通用逻辑与指令遵循能力发生严重退化。

### **2.1 小语料 CPT 的“稀疏表征干扰”与灾难性遗忘理论机理**

探究小语料 CPT 失效的底层机理，需要深入至大语言模型隐空间（Latent Space）的特征表达层面。一项运用稀疏自编码器（Sparse Autoencoders, SAE）追踪大模型在领域适应过程中特征演变的重磅研究指出：当用于领域特征训练的 Token 数量低于 100M 时，残差 SAE 学到的特征质量极差且未能充分收敛 19。这种未收敛的、夹杂大量噪声的“半成品”特征会直接侵入并扰乱预训练模型原本高度正交的通用语义特征空间。量化数据显示，在这种欠训练（Undertraining）状态下，模型在通用领域性能的解释方差（Explained Variance, EV）最高可发生 31% 的断崖式下降 19。只有当领域特定的训练语料规模跨越 200M Tokens 的“临界质量”点后，网络内部的残差特征才开始变得清晰，并与预训练特征形成良好的互补关系，此时对通用能力的干扰才逐渐回落至 1% 的安全阈值以下 19。

这一理论在针对 Qwen2.5 模型的实证研究中得到了印证。一项针对 Qwen2.5-32B-Instruct 模型在模拟电路领域（仅拥有 7.26M 极小规模领域语料）的研究明确指出：纯粹的极小语料 CPT 几乎无法提供有效收益，其在领域评测集上的性能提升微乎其微（仅 1.83%）21。更为关键的是，在经历了后续必要的 SFT（使用了约 16 倍于 CPT 数据的 112.65M Tokens）之后，由前期 CPT 带来的那点微弱优势被彻底抹平（相差仅为可以忽略的 0.4%）21。这深刻表明，在 50M-100M Tokens 级别的极小垂直域，常规的 CPT 不仅性价比极低，其引发的权重震荡反而增加了训练的不稳定风险。根据有关模型与数据规模配置（Scaling Laws for Hyperparameters）的研究结论，在总体算力预算受限且数据质量极高但规模较小的情况下，将算力向模型规模（增加非嵌入 FLOPs/Token，即 ![][image1]）倾斜，并结合精细的学习率预热调度，是比强行扩充劣质 CPT 数据更优的策略 22。

### **2.2 电催化垂直领域的创新适配与微调策略**

针对语料库约在 50M-100M Tokens 量级的电催化等小众高精领域，研究者们放弃了高风险的全局 CPT，转而采用“高比例知识提纯指令化”、“领域双阶段渐进微调”以及“极低秩自适应”等创新解法，成功破局。

**CataLM：电催化语料的知识提取与双阶段融合** CataLM 模型的研发旨在解决电催化文献中极其复杂的催化剂组成、测试条件（如过电位、电流密度、电解池设置）提取困难的问题 24。该模型以 Vicuna-13B 为基础，并未将有限的电催化文献直接倒进模型进行掩码重构，而是采用了严密设计的高强度知识提炼与“双阶段学习”机制：首先进行针对性且被严格限制的领域预训练（Domain Pre-training），随后利用由领域专家人工精标的高质量测试数据进行指令微调（Instruction Tuning）24。这种以指令形式注入领域专业认知的方法，成功绕过了特征未收敛陷阱。评估结果显示，对于电催化文献中的复杂实体（如催化体系电流密度、过电位提取），未微调的基线 LLM 准确率仅有可怜的 36.88%，而 CataLM 借由这种混合提纯策略，将修改后的准确率大幅提升至 68.75% 24。该模型被证明是探索复杂 CO2 还原等电催化工艺条件的得力助手。

**ChatHEA：直接基于结构化语料的低秩指导发现** 在更为尖端的高熵合金（HEA）电催化设计中，由于此类材料具有庞大的元素组合空间（如百万级的多组分可能）与极其错综复杂的电化学构效关系，依靠传统的统计模型收效甚微 27。研究团队构建了基于 LLaMA-3-8B 的 ChatHEA 助手，其突破点在于：完全放弃耗时且低效的无监督小语料 CPT，而是通过直接梳理出一条包含高通量实验平台真实数据的结构化电催化 ORR（氧还原反应）性能数据库，运用低秩自适应（LoRA）技术对 LLaMA-3 进行深度参数高效微调 27。得益于 LLM 强大的内在逻辑组合与机理生成能力，ChatHEA 展现出了远超普通机器学习（仅能学习简单映射）的领域规则运用能力。在其严格的条件枚举与约束指导下，团队通过旋转环盘电极（RRDE）系统地合成并评估了新材料，成功鉴定出了具有卓越 ORR 活性的 FeCoCuPtIr 催化剂，其性能在 E1/2 势和 Tafel 斜率双核心指标上全面超越了商业的 Pt/C 催化剂 27。这充分说明，在垂直科研前沿，基于高质量结构化实验数据的 PEFT（参数高效微调）比盲目使用原始文本进行 CPT 具有更高的产业化落地价值。

| 论文标题、作者及发表时间 | 基座模型类型 / 算法名称 | 具体应用任务 (电催化垂直场景) | 核心创新点及量化效果 |
| :---- | :---- | :---- | :---- |
| **CataLM: Empowering Catalyst Design through Large Language Models** (Chen 等, 2024.11) 24 | 基座：Vicuna-13B 算法：基于有限文献集的高强度双阶段学习 (Domain Pre-training 结合 Instruction Tuning) | 电催化前沿文献的复杂工艺参数（过电位、测试条件、催化指标）高精实体解析与知识图谱构建 | **创新点**：针对电催化小语料特征稀疏痛点，将非结构化文献转化为人机协作的强制指令集进行对齐调优。 **量化效果**：成功跨越小数据集陷阱，核心电催化命名实体的提取精度达到 68.75%（大幅超越基线 36.88% 表现）。 |
| **A Collaborative Framework Integrating LLMs with High-Throughput... (ChatHEA)** (Xing 等, 2025/Advance Article) 27 | 基座：LLaMA-3-8B 算法：直接构建高密度结构化数据集融合 LoRA 微调机制 | 高熵合金（HEA）电催化氧还原反应（ORR）的组分条件枚举、活性构效关系推理与新催化剂发现指导 | **创新点**：打破机器学习仅能统计映射的局限，利用 LLM 进行化学规则层面的物理组合演绎推理。 **量化效果**：利用微调后 LLM 的辅助分析，成功定向合成 FeCoCuPtIr HEA 催化剂，其 ORR 性能显著击败商业化 Pt/C 标准件。 |

## **3\. LoRA 与 PEFT 微调在化学推理、参数生成与工业催化中的深度应用**

在确立了领域适应的基本盘之后，如何以极低的算力成本，将极其复杂多变的化学合成配方、设备操作控制语言以及工业催化机理模块化地赋能给大模型，成为了工程落地的核心议题。参数高效微调（PEFT），尤其是低秩自适应（LoRA）及其衍生变体（如 rsLoRA、QLoRA 等），凭借其能够冻结基座模型深层权重，仅更新旁路低秩矩阵的特性，完美规避了全参数微调导致的底层表征空间异化与常识坍塌风险，已成为化学 QA、反应参数自动生成以及合成路线规划的工业级标配范式。

### **3.1 模块化 LoRA 机制在化学反应预测中的冲突消解**

化学研究中的任务往往彼此关联却又遵循不同的子规则，例如正向产率预测需要极度关注反应物的电子效应，而逆合成推演则需要宏观上的断键逻辑认知。传统的全参数微调在同时学习这些异构任务时，极易陷入灾难性遗忘或“任务间负迁移”（Task Interference）。

一项前瞻性的模块化多任务化学反应预测研究（Modular Multi-Task Learning for Chemical Reaction Prediction）通过在 Qwen2.5-7B-Instruct 等系列基座模型上部署独立且可拔插的 LoRA-Chem 模块，成功化解了这一矛盾 29。该架构将极其微量（仅占基座总参数的 0.05% 至 0.09%，约数兆字节）的特定训练参数注入模型的 Attention（注意力）或 MLP（多层感知机）层中 31。在极其复杂的 o-烷基芳基酮的大位阻间位 C-H 键选择性功能化（SHC-oAK）反应测试集中，加载了 LoRA-Chem 的 Qwen2.5-7B 能够精确捕捉底物的细微反应性差异，将产率预测的决定系数（R2）从基线水平 0.748 稳步提升至 0.77 31。

研究进一步揭示，由于 LoRA 强制网络在低维流形空间中逼近目标任务的梯度更新，它保留了基座原本更为庞大的泛化生成能力 29。因此，在面临未知试剂参数生成与多重连环预测需求时，系统可按需动态调用不同的 LoRA 权重矩阵。这种灵活性不仅实现了与全参数微调相当的高准度，还有效抵御了单一任务偏好导致的多任务表现退化，为构建能够应对千变万化的实验环境的通用型自驱动化学大脑打下了架构基础 29。

### **3.2 历史文本挖掘到自动化执行指令：ReactionSeek**

不仅在反应预测，大模型在打通从陈旧历史文本至可执行实验指令闭环的领域同样硕果累累。由于传统的化学实验记录往往以非结构化的杂乱文本、交错的分子图片体系存在，极难转化为可供机器人解析的标准化数据集。ReactionSeek 框架巧妙利用大模型及其视觉感知组件，建立了一套全覆盖的文本挖掘流水线 33。

该框架的实施分为三个高度协同的闭环阶段：首先利用图像挖掘技术拆解反应方案图与分子式；其次，依托经过精细 Prompt 工程优化的 LLM 对大段冗长且包含歧义的实验操作步骤文本进行实验级信息提取；最后进行实体标准化以消除命名歧义 35。当该流水线被应用至长达一个世纪的宏伟文库《有机合成》（Organic Syntheses）全集时，系统展现了卓越的解析能力，对关键反应参数（如催化剂配比、控温时间、分离提纯试剂等）的提取查准率（Precision）与查全率（Recall）双双超越 95% 33。

此外，为了便于人类科学家检索并辅助生成后续的自动化实验参数，该研究还开发了交互式分析引擎 SynChat 34。不仅实现了自然语言到复杂化学反应数据的映射，其强大的多轮迭代追问能力与“引文溯源”保证了自动化参数生成时数据链条的绝对可靠性 35。这一系统本质上清除了化学科学大范围拥抱人工智能过程中的“数据整理”瓶颈。

### **3.3 检索增强与秩稳定微调：PeiYang 工业催化大模型**

工业催化过程由于直接面向放大生产线，其知识包含着密集的工程术语、极具挑战的动力学边界条件以及庞大的关联规则，这使得通用模型在面对这类“冷门高深”提问时经常胡言乱语。天津大学领衔发布的 PeiYang（北洋微显）领域大系统完美展示了如何通过 rsLoRA（秩稳定低秩自适应）技术与 RAG（检索增强生成）构筑领域护城河 25。

研究人员没有盲目追求数百亿参数的巨型网络，而是选择了具有优异性价比的 Yi-1.5-6B 模型。为了训练出这套系统，团队精心调制了总计 2.3B Tokens 的高质混合语料（采用严谨的 1:1 配比，即 1.1B 极致专业的催化域 Token 搭配 1.2B 的广泛常识 Token），在保障专业深度的前提下严防常识认知缩水 25。区别于普通的 LoRA 在面对复杂长序列或极不规则分布时的放缩震荡问题，rsLoRA 引入了稳定的归一化因子，使得模型梯度的传递极为平滑，极大地增强了深层次特征的抽取能力。

为了彻底消除工业级参数生成的“幻觉”，该系统更进一步构建了包含 337 万对专业文献段落的庞大向量检索库，并利用俄罗斯套娃表征学习（Matryoshka Representation Learning, MRL）技术深度打磨 Embedding 提取层，这让检索系统的 Recall@3 召回精度在原有基础上硬核拔高了 2.87% 25。在严苛的工业催化领域基准评测中，经过 rsLoRA 微调加上双路径一致性验证检索流的加持，参数量仅为 6B 的 PeiYang 系统，打出了高达 76.81 分的耀眼成绩，在专业深度的较量上，彻底碾压了参数规模比它大足足十二倍的 Qwen2.5-72B-Instruct（65.45分）25。这组量化数据成为了“小模型+高质量数据配比+改良型 PEFT+专业知识库外挂”能够对大模型实现“越级反杀”的教科书级铁证。

| 论文标题、作者及发表时间 | 基座模型类型 / 算法名称 | 具体应用任务 (PEFT 下游场景) | 核心创新点及量化效果 |
| :---- | :---- | :---- | :---- |
| **Modular Multi-Task Learning for Chemical Reaction Prediction** (Han 等, 2024/2025) 29 | 基座：Qwen2.5-7B-Instruct 等 算法：LoRA-Chem 模块化微调与按需动态权重路由机制 | 多任务有机化学预测（涵盖正向复杂产量预测、逆向合成推演、最佳反应试剂推荐及 C-H 键特异性功能化分析） | **创新点**：开创性地针对细分化学反应构建极其轻量化、独立且可插拔的 LoRA 模块，彻底化解多化学任务联合训练的底层参数冲突弊端。 **量化效果**：可训练参数仅占总量的 0.05%-0.09%。在难度极高的 SHC-oAK 测试集上，将核心产率预测 R2 从 0.748 稳步升至 0.77。 |
| **ReactionSeek: LLM-Powered Literature Data Mining and Knowledge Discovery** (Jiawei Li 等, 2025.08) 33 | 基座：大规模语言模型联合前沿多模态视觉解析器 算法：基于强 Prompt 工程的图像-文本交叉精细抽取流水线 | 百年级复杂有机合成图谱、文献长文本的机理参数抽取与大语言模型驱动的自适应知识挖掘问答平台 (SynChat) | **创新点**：从无序古籍图文中打通流体控制与试剂参数化提取的闭环，实现机器向大模型的无缝对接。 **量化效果**：针对整个百年《有机合成》文献的极高难度萃取，其核心反应参数提取精度与召回率双双突破 95%，实现零错乱引文溯源。 |
| **PeiYang Micro-Emergence Domain Specific System** (天津大学联合团队, 2025.03) 25 | 基座：Yi-1.5-6B 算法：rsLoRA（秩稳定低秩自适应微调）结合 MRL 优化深度检索的双路一致性生成架构 | 工业级催化工程机理深度问答、极限工艺条件精准生成及多重专业一致性文献比对论证 | **创新点**：采用绝对的 1:1（常识-专业）微调数据平衡策略，辅以秩稳定梯度优化，并以外挂大纵深向量检索库根除机理幻觉。 **量化效果**：使用 2.3B 混合同比 Tokens 进行 rsLoRA。系统专业评分高达 76.81，在专业上直接超越超大规模通用基座 Qwen2.5-72B (65.45分)。 |

## **4\. 自驱动实验室（SDL）中的多模态物理异常自动检测体系**

自驱动实验室（Self-Driving Labs, SDL）通过将自动化流体机械手、高通量高精度的表征分析设备与作为决策“大脑”的大语言/机器学习模型无缝融合，正在颠覆延续了上百年的依靠试错的手工实验范式。然而，在追求 24/7 全天候无休运行的工程化道路上，最大的一道天堑并非配方生成的准确率，而是由于物理世界的不可逆与不确定性（如玻璃器皿破碎、机械臂抓取偏移、管路气泡堵塞、试剂溢漏等）带来的灾难性后果。建立一套兼具高敏感度物理感知与深厚领域常识推理能力的异常检测体系，是系统实现自适应与全闭环控制的首要前提。

### **4.1 从刚性统计阈值向多模态 AI 语境感知的演变**

在早期的 SDL 或自动化产线中，针对安全隐患的异常检测几乎完全依赖于硬编码的物理与化学边界阈值。工程师们通过在反应釜、导管网络和机械臂末端加装各种单一功能的传感器（例如针对超压报警的压力计、针对沸腾监控的热电偶等）来构建防线 36。尽管这种系统响应快速，但其由于缺乏对“实验上下文”的理解，极度容易漏报那些处于物理阈值以内，但在化学意义上已经宣告失败的隐性错误。例如，溶液在添加某种催化剂后应当呈现特定颜色变化，但在发生试剂污染或副反应时出现了极其微妙的颜色渐变，或是密封垫圈在发生灾难性喷射泄漏前展现出肉眼难以辨别的细微形变 36。

为了填补这一监控空白，自 2024 年下半年起，尖端的 SDL 开始大规模引入 AI 驱动的动态多模态情境感知网络（Situational Awareness）。除了传统的计算机视觉框架，新一代的系统进一步整合了高敏气体质谱流分析、全谱面声学监控与高帧率热成像轮廓扫描 36。通过将这种多维传感数据实时映射输入进大语言模型或专门优化的机器学习分类器中，AI 代理能够在不断比较“当前动态流”与基线正常规律中，实现从“事后报警”向“事前预判与机理解释”的跨越。

### **4.2 LIRA 框架：视觉-语言大模型驱动的闭环诊断革命**

在向这种自主环境感知迈进的历程中，LIRA（Localization, Inspection, and Reasoning）模块的提出具有革命性意义 37。由于传统的纯视觉分类器需要极大的标注成本以穷尽所有异常形态，而实验室的操作环境千变万化，LIRA 另辟蹊径，将经过特定微调的视觉语言模型（VLM）作为核心的物理检验器（Inspector），深度嵌入至搭载于移动底盘的机械臂高级任务调度引擎之中 37。

LIRA 彻底摒弃了传统机器人基于固定预设坐标盲目运动的操作逻辑。在抓取与执行前，系统会利用高度结构化、具有强大引导约束能力的自然语言 Prompt（例如系统会自主询问：“白色的 8 孔试管架是否正确放置在支架槽口上？”、“试剂瓶帽是否处于开启状态？”、“工作台面是否存在试剂泼溅的化学沾染？”）触发 VLM 对当前物理空间进行深度扫描与逻辑诊断 37。

更为惊艳的是，LIRA 不仅仅执行异常报警，它具备强大的逻辑推理转化能力。当 VLM 判断出存在异常（如发生轻微的试管倾斜或机械臂初次抓取位置发生数厘米的偏差）时，其输出的是包含明确偏移距离的纠正坐标或具体的补救子流程参数 37。这种结构化的容错指令被迅速解析并反哺给底层控制环路。量化实验数据显示，在一系列高度模拟真实环境的复杂固态工作流中，面对诸如未盖帽试管、被碰倒而溢出的化学药剂以及碎玻璃等混合突发事件时，LIRA 的现场检测与推理修正成功率达到惊人的 97.5%，在保留测试集上的识别准确率甚至达到了 100% 38。由于 LIRA 在发生不可控失误前就能以极高精度提前纠偏，它将原本那些因为细小误差导致失败重试而浪费的冗余无效操控时间彻底消除，使得全系统的物理臂操作总时长缩减了 34% 至 36.14%，显著提升了自动化合成工序的鲁棒性与节拍效率 38。

### **4.3 超越报错：基于互信息惊喜度（MIS）的认知型过程监控**

如果说 LIRA 是解决“物理执行是否出错”的纠偏神器，那么当大模型驱动的 SDL 进行未知的探索性化学试验时，“当前怪异的产物参数是否意味着实验彻底失败？”则是一个更为深刻的认知论难题。传统的统计学指标如香农熵（Shannon Entropy）或贝叶斯惊喜（Bayesian Surprise），由于只能计算单次信号偏离历史均值的离散程度，往往会将所有打破常规的观测数据简单粗暴地判定为“失控异常（Anomalies）”，从而草率地触发停机重置 43。然而，在科学探索中，那些违背常识的离群点，极有可能正是引出重大新发现的转折所在。

为此，佐治亚理工等机构提出了一种震撼性的全新异常检测与决策引导框架：互信息惊喜度（Mutual Information Surprise, MIS）43。该框架在底层重构了惊喜（Surprise）的定义，将其从单纯的偏离度，进化为衡量“该新观测值能为系统底层预测模型的参数不确定性缩减做出多大贡献”的认知增长（Epistemic Growth）信号 43。

在由机器人化学家主导的动态催化剂空间搜索任务中，系统实时计算并跟踪 MIS 的演变。当实验传感数据发生严重的非预期偏离时，统计检验模块会评估这种偏离是否带来了互信息量上的突破。如果计算判定这是一种能够颠覆现有反应机制认知的“高价值异常”，系统绝不执行死板的报警停机动作。相反，互信息惊喜反射策略（MISRP）会自主接管，通过即时调整系统的概率采样权重，并果断在决策树上执行进程分支（Process Forking），投入额外的高精度分析手段去深挖这一偏离区间 43。这一具备高度自我意识（Self-aware）的检控理论，直接促使 SDL 的错误处理从僵化的“反应性停机”（Reactive）跨升为高度智能的“反射性探索”（Reflective），在维持整个平台极高物理稳定性的同时，实现了更卓越的模型收敛精度与机理探明效率 43。

## **5\. 跨越失控边界：神经符号学系统自主修复与全天候无人运行**

在大语言模型体系中，反思机制（Reflexion）早已被证实是提升长程推理准确率的核心利器：模型在生成错误答案后，通过重新审视中间步骤并加入自我批判反馈，能不断逼近正确结论。然而，面对化学湿实验室（Wet-Labs）中真实且无可挽回的物理损耗——一次微小概率的大模型“幻觉”，就会引发机械臂折断玻璃器皿引发火灾，或将互斥试剂错误注入导致反应体系爆炸——直接将这种完全由概率和自回归生成的纯文本反馈作为物理控制命令，无异于一场灾难 44。

### **5.1 BioProAgent 与基于确定性有限状态机（FSM）的容错修复长城**

针对 LLM 在不可逆物理环境中因概率性幻觉带来的灾难性执行风险，研究团队在 2026 年提出了基于神经符号学（Neuro-Symbolic）理念打造的 BioProAgent 容错控制框架，从根本上为自驱动实验室的自主故障修复树立了极高标准的安全壁垒 44。

有别于传统的 ReAct 或 Reflexion 等仅在聊天窗口中自我批评的代理框架，BioProAgent 最深刻的革新在于：它使用了一个高度刚性、确定性的有限状态机（Deterministic Finite State Machine, FSM）作为限制大模型发散思维的物理与安全“护城河” 44。在这一框架下，模型从异常发生到执行修复必须经历极其苛刻的“设计-验证-纠正（Design-Verify-Rectify, DVR）”循环逻辑 44。

**底层机理与长程记忆纠正流程：**

1. **层次化严格双重验证**：任何试图向底部硬件发送的包含机械动作或液体分配的修复指令，首先被拦截并强行塞入双层验证函数。第一层是基于科学原理的验证器（Ks），审核诸如化学相容性、试剂加入的时间序列以及热力学极限等实验设计要素；第二层是至关重要的物理合规验证器（Kp），审核机械臂的可达空间边界、当前器皿的容量占用上限等不可逾越的物理限制 44。  
2. **状态强制干预与自我矫正（RECTIFY）**：当复杂的连续化学实验遭遇堵塞或液体残留异常时，一旦 Ks 或 Kp 捕获到 LLM 生成的带有隐患的补救指令（如未经清洗就试图插入下一根试管），FSM 会果断切断概率推理流的向下传导，并发生刚性状态跳变，强制将整个系统拉入专职进行错误化解的 RECTIFY（纠正）状态 44。在这个相对安全的沙盒空间内，大模型代理才可以调用传统的 Reflexion 与历史工作日志，冷静分析冲突发生点，进而自主生成一系列挽救预案。这套预案可能包括触发 wash\_pipette() 清洗函数进行污染阻断，或是重新标定液体存量信息。这些补救动作必须在重新生成后再次经受双重验证，直至通过后，系统才会从 RECTIFY 状态切出，恢复到正常的实验序列 44。  
3. **消除认知漂移的“语义符号接地”技术**：在处理包含成百上千步的复杂 SDL 工作流纠错排查时，庞大的 Prompt 上下文（大量的仪器状态读数与试剂 UUID 编号）极易淹没大模型的注意力机制，导致系统在重试过程中发生灾难性的“认知漂移（Cognitive Drift）”，例如错把甲醇的剩余量读成乙醇。为了应对这一致命弱点，BioProAgent 采用了先进的语义符号接地（Semantic Symbol Grounding）技术，将高维海量的物理环境载荷数据统统解耦，转化为轻量化的符号指针进行传递。这极大地缓解了内存负担，使得令牌（Token）消耗量惊人地骤降了 6 倍，并百分之百地保持了错误恢复长周期循环中多步资源状态的一致性 44。

### **5.2 容错量化指标的跃升与 24/7 无人干预连续运行的里程碑**

引入了这类深层确证反馈与容错安全墙设计的 SDL，彻底改变了以往“自动化只是辅助，依然离不开人类监控”的尴尬局面，极大地推高了系统稳定性的量化极限，标志着 AI 驱动的自主科学发现真正迈入全天候无人值守时代。

在针对极具挑战的具有长序列硬件控制特征的 BioProBench 环境评估中，BioProAgent 在处理各种报错中断时展现了惊人的修复统筹能力：面对人为设置的包含各种错配与阻碍的纠错特化测试集（Subset D），传统的单纯基于 LLM 推理的基线代理模型（如通用 ReAct）发生逻辑雪崩崩溃，错误恢复率惨跌至无可救药的 0% 44。反观由于在架构上强制挂载了神经符号学验证层与 FSM 跳变机制，BioProAgent 不仅做到了 95.6% 的完美物理安全合规性执行，更创下了高达 88.7% 的极高异常自动恢复成功率记录 44。消融实验一锤定音：一旦拆除这层基于 FSM 物理边界与 Ks/Kp 的确定性验证框架，整个高容错网络瞬间崩塌，物理合规评分立刻下挫，修复成功率直接跌回冰点 44。

可靠性的突破带来的是无人工干预运行时长的现象级增长。在最新的生物物理相互作用与大规模受体筛选分析领域，配有完备排队自动评估与故障屏蔽诊断能力的平台，已能做到让研发人员安心下班，轻松支撑长达 60 个小时毫不间断的高负荷平行扫描，并在错峰期间自动分类高低亲和力分子 47。

在更为宏大的加速材料发现探索中，其效果更加震撼。著名的伯克利国家实验室主导建立的 A-Lab（智能机械辅助合成网络），便是这一理念的巅峰展示 48。A-Lab 集成了先进的决策推断机器学习层、庞大的知识图谱与高速机器人，在搜寻合成全新的无机粉末晶体试验进程中，凭借着极其稳健的闭环决策流与底层硬件自我保护重置控制策略，成功实现了长达 17 天（超过 400 小时）毫无任何研究人员物理干预的极限式连续运行。在此期间不仅克服了多次物料与合成反馈异常，更在这 17 天的连续轰炸下成功筛选、鉴定出 41 种前所未见的全新结构化合物体系 48。而在更关注工艺稳健性的电催化持久试验台站中，这种具备自动异常反馈并进行参数自校准的自驱动系统，能够实现超越 500 小时且性能衰减不到 2% 的绝对稳定连续监控操作 49。这一系列振奋人心的指标预示着，在确立了高鲁棒容错的自驱动实验室赛道上，科研效率已突破人类的生理与计算极限。

| 论文标题、作者及发表时间 | 架构机制 / 传感器算法感知流 | 具体应用任务 (自驱实验室 SDL 场景) | 核心创新点及量化效果（异常恢复率与运行时长） |
| :---- | :---- | :---- | :---- |
| **BioProAgent: Neuro-Symbolic Grounding for Constrained Scientific Planning** (Liu 等, 2026.03) 44 | 核心架构：确定性有限状态机 (FSM) 结合大模型 Reflexion 核心算法：基于解耦载荷的语义符号接地技术与 DVR 层次化多代理逻辑验证循环 | 高通量生化湿实验室的复杂、不可逆的液处理机器人序列调度、污染截断洗涤与合规防撞控制体系 | **创新点**：首创在纯概率推理的大模型中外挂物理安全验证边界（Ks/Kp），拦截致命错误并强制引入 RECTIFY（纠正）自我修复重算循环。 **量化指标**：相比纯文本生成彻底崩溃的 0%，该架构错误恢复成功率暴涨至 88.7%，维持了 95.6% 的物理合规底线，通过符号转换将 Token 内存开销极致压缩了 6 倍。 |
| **LIRA: Localization, Inspection, and Reasoning Module for Autonomous Workflows** (Fakhruldeen 等, 2025.02) 37 | 核心架构：微调 VLM（视觉语言模型）驱动的高机动视-语混合检验层 核心算法：基于自然语言 Prompt 反馈的物理空间扫描检验网络 | 固态材料自动称重与转移等高精度机械操作流中（例如试管倒伏、溢漏沾染、机械位移偏差）的异常实时监测与主动物理坐标干预矫正 | **创新点**：彻底击碎了传统单一固定传感器报警但无法纠正的壁垒，通过高级语义判断场景对错，并将错误情况直接换算成具有执行参数的结构化操作序列交由调度中心排障。 **量化指标**：真实复杂场景全覆盖测试识别成功率高达 97.5%。系统闭环的纠偏机制让机械臂避开了无休止的卡顿或错抓报错，直接将无效操作执行总时长生生抹去 34% \- 36.14%。 |
| **Mutual Information Surprise for Anomaly Detection in Autonomous Experimentation** (Wang 等, 2025.08) 43 | 核心架构：高度动态信息流反馈智能评估环路 核心算法：基于 MISRP（互信息惊喜反射控制策略）进行即时重采样概率分配调整 | 探寻前所未有且完全未知的高阶新型机器人化学家光催化试验参数追踪评估，以及面临剧烈偏离期望动态时的系统进程反射决策 | **创新点**：彻底革新了对“异常错误”的古板认知。利用底层参数的统计模型收敛增益重塑评判标准，通过“惊喜度”分析主动派生探索分支（Process Forking）。 **量化指标**：在极大非预期扰动的物理实测评估中，展现了比被动香农熵算法更为优异的系统重稳态表现及预测捕捉精度。 |
| **Autonomous Mobile Robots for Exploratory Synthetic Chemistry (A-Lab)** (Dai 等, 2024\) 48 | 核心架构：横跨算力枢纽机器学习、庞杂物理数据历史图谱寻优与硬件机器人底层自主控制调度的集大成系统 核心算法：封闭数据迭代推演的循环寻路闭环 | 复杂多元的全新无机晶体粉末大规模探索穷举合成流水线 | **创新点**：突破了大量硬件堆砌带来的故障级联崩溃，依靠自身完善的阻碍侦测逻辑配合系统重置循环执行，真正抹除了“人在回路”的物理依赖。 **量化指标**：创立了不可思议的连续 17 个日夜（超越 400 小时极限界限）的完全无人值守不间断稳定自主运作巅峰，在此严酷连续周期中硬核生成鉴定了 41 种全新结构化合物族群。 |

#### **引用的著作**

1. Qwen2.5 72B Instruct vs Qwen3 Max \- Pricing & Benchmark Comparison 2026, 访问时间为 四月 2, 2026， [https://pricepertoken.com/compare/qwen-qwen-2.5-72b-instruct-vs-qwen-qwen3-max](https://pricepertoken.com/compare/qwen-qwen-2.5-72b-instruct-vs-qwen-qwen3-max)  
2. arXiv:2505.09388v1 \[cs.CL\] 14 May 2025, 访问时间为 四月 2, 2026， [https://arxiv.org/pdf/2505.09388](https://arxiv.org/pdf/2505.09388)  
3. Qwen3 Technical Report \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2505.09388v1](https://arxiv.org/html/2505.09388v1)  
4. Qwen3 30B A3B 2507 Instruct vs Qwen2.5 Coder Instruct 32B: Model Comparison \- Artificial Analysis, 访问时间为 四月 2, 2026， [https://artificialanalysis.ai/models/comparisons/qwen3-30b-a3b-2507-vs-qwen2-5-coder-32b-instruct](https://artificialanalysis.ai/models/comparisons/qwen3-30b-a3b-2507-vs-qwen2-5-coder-32b-instruct)  
5. Innovator: Scientific Continued Pretraining with Fine-grained MoE Upcycling \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2507.18671v1](https://arxiv.org/html/2507.18671v1)  
6. Daily Papers \- Hugging Face, 访问时间为 四月 2, 2026， [https://huggingface.co/papers?q=Scientific%20Skills](https://huggingface.co/papers?q=Scientific+Skills)  
7. Daily Papers \- Hugging Face, 访问时间为 四月 2, 2026， [https://huggingface.co/papers?q=end-to-end%20reproducible%20training%20pipeline](https://huggingface.co/papers?q=end-to-end+reproducible+training+pipeline)  
8. SCILITLLM: HOW TO ADAPT LLMS FOR SCIENTIFIC LITERATURE UNDERSTANDING \- ICLR Proceedings, 访问时间为 四月 2, 2026， [https://proceedings.iclr.cc/paper\_files/paper/2025/file/8cb240de90aa20207db944c6c88a7cc0-Paper-Conference.pdf](https://proceedings.iclr.cc/paper_files/paper/2025/file/8cb240de90aa20207db944c6c88a7cc0-Paper-Conference.pdf)  
9. SciLitLLM: How to Adapt LLMs for Scientific Literature Understanding \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2408.15545v2](https://arxiv.org/html/2408.15545v2)  
10. SciLitLLM: How to Adapt LLMs for Scientific Literature Understanding \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/383495127\_SciLitLLM\_How\_to\_Adapt\_LLMs\_for\_Scientific\_Literature\_Understanding](https://www.researchgate.net/publication/383495127_SciLitLLM_How_to_Adapt_LLMs_for_Scientific_Literature_Understanding)  
11. The Tokenization Bottleneck: How Vocabulary Extension ... \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/abs/2511.14365](https://arxiv.org/abs/2511.14365)  
12. The Tokenization Bottleneck: How Vocabulary Extension Improves Chemistry Representation Learning in Pretrained Language Models \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2511.14365v1](https://arxiv.org/html/2511.14365v1)  
13. MELT: Materials-aware Continued Pre-training for Language Model ..., 访问时间为 四月 2, 2026， [https://arxiv.org/abs/2410.15126](https://arxiv.org/abs/2410.15126)  
14. Revision History for MELT: Materials-aware Continued, 访问时间为 四月 2, 2026， [https://openreview.net/revisions?id=gDYGjoTmdg](https://openreview.net/revisions?id=gDYGjoTmdg)  
15. (PDF) MELT: Materials-aware Continued Pre-training for Language, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/385108126\_MELT\_Materials-aware\_Continued\_Pre-training\_for\_Language\_Model\_Adaptation\_to\_Materials\_Science](https://www.researchgate.net/publication/385108126_MELT_Materials-aware_Continued_Pre-training_for_Language_Model_Adaptation_to_Materials_Science)  
16. Aligning Reasoning LLMs for Materials Discovery with Physics-aware Rejection Sampling, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2509.00768v1](https://arxiv.org/html/2509.00768v1)  
17. Models \- OpenRouter, 访问时间为 四月 2, 2026， [https://openrouter.ai/models](https://openrouter.ai/models)  
18. (PDF) A corpus of CO2 electrocatalytic reduction process extracted from the scientific literature \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/369624134\_A\_corpus\_of\_CO2\_electrocatalytic\_reduction\_process\_extracted\_from\_the\_scientific\_literature](https://www.researchgate.net/publication/369624134_A_corpus_of_CO2_electrocatalytic_reduction_process_extracted_from_the_scientific_literature)  
19. Teach Old SAEs New Domain Tricks with Boosting \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2507.12990v1](https://arxiv.org/html/2507.12990v1)  
20. Teach Old SAEs New Domain Tricks with Boosting \- OpenReview, 访问时间为 四月 2, 2026， [https://openreview.net/pdf?id=d4XXFVAlV7](https://openreview.net/pdf?id=d4XXFVAlV7)  
21. AnalogSeeker: An Open-source Foundation Language Model for Analog Circuit Design, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2508.10409v1](https://arxiv.org/html/2508.10409v1)  
22. DeepSeek LLM Scaling Open-Source Language Models with Longtermism \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2401.02954v1](https://arxiv.org/html/2401.02954v1)  
23. Scaling Laws for Optimal Data Mixtures \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2507.09404v1](https://arxiv.org/html/2507.09404v1)  
24. CataLM: Empowering Catalyst Design Through Large Language Models \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2405.17440](https://arxiv.org/html/2405.17440)  
25. Domain-Specific Fine-tuning of Large Language Models and Intelligent Question-Answering System for Industrial Catalysis, 访问时间为 四月 2, 2026， [https://media.sciltp.com/articles/2603003207/2603003207.pdf](https://media.sciltp.com/articles/2603003207/2603003207.pdf)  
26. CataLM: empowering catalyst design through large language models \- Semantic Scholar, 访问时间为 四月 2, 2026， [https://www.semanticscholar.org/paper/CataLM%3A-Empowering-Catalyst-Design-Through-Large-Wang-Chen/c6fd64c657a9f821e84d733a0314ebb51bdb8076](https://www.semanticscholar.org/paper/CataLM%3A-Empowering-Catalyst-Design-Through-Large-Wang-Chen/c6fd64c657a9f821e84d733a0314ebb51bdb8076)  
27. ORIGINAL UNEDITED MANUSCRIPT \- Oxford Academic, 访问时间为 四月 2, 2026， [https://academic.oup.com/nsr/advance-article-pdf/doi/10.1093/nsr/nwag161/67357324/nwag161.pdf](https://academic.oup.com/nsr/advance-article-pdf/doi/10.1093/nsr/nwag161/67357324/nwag161.pdf)  
28. ChemReactLLM: A Multimodal Large Language Model for Catalyst-Driven Organic Reaction Prediction and Optimization \- ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-vhvgh](https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-vhvgh)  
29. Modular Multi-Task Learning for Chemical Reaction Prediction \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2602.10404v1](https://arxiv.org/html/2602.10404v1)  
30. (PDF) Modular Multi-Task Learning for Chemical Reaction Prediction \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/400705244\_Modular\_Multi-Task\_Learning\_for\_Chemical\_Reaction\_Prediction](https://www.researchgate.net/publication/400705244_Modular_Multi-Task_Learning_for_Chemical_Reaction_Prediction)  
31. LoRA-Chem: Modular Machine Learning for Multitask Prediction in Organic Reactions | CCS Chemistry \- Chinese Chemical Society, 访问时间为 四月 2, 2026， [https://www.chinesechemsoc.org/doi/full/10.31635/ccschem.025.202506542](https://www.chinesechemsoc.org/doi/full/10.31635/ccschem.025.202506542)  
32. Leveraging large language models for enzymatic reaction prediction and characterization, 访问时间为 四月 2, 2026， [https://pubs.rsc.org/en/content/articlehtml/2025/dd/d5dd00187k](https://pubs.rsc.org/en/content/articlehtml/2025/dd/d5dd00187k)  
33. ReactionSeek: LLM-powered literature data mining and knowledge discovery in organic synthesis \- PubMed, 访问时间为 四月 2, 2026， [https://pubmed.ncbi.nlm.nih.gov/41771908/](https://pubmed.ncbi.nlm.nih.gov/41771908/)  
34. ReactionSeek: LLM-Powered Literature Data Mining and Knowledge Discovery in Organic Synthesis \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/394681783\_ReactionSeek\_LLM-Powered\_Literature\_Data\_Mining\_and\_Knowledge\_Discovery\_in\_Organic\_Synthesis](https://www.researchgate.net/publication/394681783_ReactionSeek_LLM-Powered_Literature_Data_Mining_and_Knowledge_Discovery_in_Organic_Synthesis)  
35. ReactionSeek: LLM-Powered Literature Data Mining and Knowledge Discovery in Organic Synthesis \- ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/689328e223be8e43d6f494d3/original/reaction-seek-llm-powered-literature-data-mining-and-knowledge-discovery-in-organic-synthesis.pdf](https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/689328e223be8e43d6f494d3/original/reaction-seek-llm-powered-literature-data-mining-and-knowledge-discovery-in-organic-synthesis.pdf)  
36. Toward self-driving laboratory 2.0 for chemistry and materials discovery \- RSC Publishing, 访问时间为 四月 2, 2026， [https://pubs.rsc.org/en/content/articlehtml/2026/mh/d5mh01984b](https://pubs.rsc.org/en/content/articlehtml/2026/mh/d5mh01984b)  
37. Localization, inspection, and reasoning (LIRA) module for ..., 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12663431/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12663431/)  
38. LIRA: Localization, Inspection, and Reasoning Module for Autonomous Workflows in Self-Driving Labs \- Research Square, 访问时间为 四月 2, 2026， [https://assets-eu.researchsquare.com/files/rs-6148048/v1/7ac35f65a875ad3940858123.pdf](https://assets-eu.researchsquare.com/files/rs-6148048/v1/7ac35f65a875ad3940858123.pdf)  
39. Localization, inspection, and reasoning (LIRA) module for autonomous workflows in self-driving laboratories \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/398090164\_Localization\_inspection\_and\_reasoning\_LIRA\_module\_for\_autonomous\_workflows\_in\_self-driving\_laboratories](https://www.researchgate.net/publication/398090164_Localization_inspection_and_reasoning_LIRA_module_for_autonomous_workflows_in_self-driving_laboratories)  
40. (PDF) LIRA: Localization, Inspection, and Reasoning Module for Autonomous Workflows in Self-Driving Labs \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/390063669\_LIRA\_Localization\_Inspection\_and\_Reasoning\_Module\_for\_Autonomous\_Workflows\_in\_Self-Driving\_Labs](https://www.researchgate.net/publication/390063669_LIRA_Localization_Inspection_and_Reasoning_Module_for_Autonomous_Workflows_in_Self-Driving_Labs)  
41. BioMARS: A Multi-Agent Robotic System for Autonomous Biological Experiments \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2507.01485v1](https://arxiv.org/html/2507.01485v1)  
42. PREVENT: Proactive Risk Evaluation and Vigilant Execution of Tasks for Mobile Robotic Chemists using Multi-Modal Behavior Trees \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2510.21438v1](https://arxiv.org/html/2510.21438v1)  
43. Mutual Information Surprise: Rethinking Unexpectedness in Autonomous Systems \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2508.17403v2](https://arxiv.org/html/2508.17403v2)  
44. BioProAgent: Neuro-Symbolic Grounding for Constrained ... \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/abs/2603.00876](https://arxiv.org/abs/2603.00876)  
45. BioProAgent: Neuro-Symbolic Grounding for Constrained Scientific Planning \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/pdf/2603.00876](https://arxiv.org/pdf/2603.00876)  
46. Autonomous Control Leveraging LLMs: An Agentic Framework for Next-Generation Industrial Automation \- arXiv.org, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2507.07115v1](https://arxiv.org/html/2507.07115v1)  
47. Annual Meeting May 24-26, 2017 Université du Québec à Montréal \- Biophysical Society of Canada, 访问时间为 四月 2, 2026， [https://biophysicalsociety.ca/wp-content/uploads/2023/05/BSC2017\_ProgramFinal.pdf](https://biophysicalsociety.ca/wp-content/uploads/2023/05/BSC2017_ProgramFinal.pdf)  
48. A generalized platform for artificial intelligence-powered autonomous enzyme engineering \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12215622/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12215622/)  
49. A Multiagent-Driven Robotic AI Chemist Enabling Autonomous Chemical Research On Demand \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/jacs.4c17738](https://pubs.acs.org/doi/10.1021/jacs.4c17738)  
50. Accelerated Materials Experimentation Enabled by the Autonomous Materials Innovation Infrastructure (AMII) A Workshop Report, 访问时间为 四月 2, 2026， [https://www.mgi.gov/sites/mgi/files/MGI\_Autonomous\_Materials\_Innovation\_Infrastructure\_Workshop\_Report.pdf](https://www.mgi.gov/sites/mgi/files/MGI_Autonomous_Materials_Innovation_Infrastructure_Workshop_Report.pdf)  
51. BENCHMARKING LARGE LANGUAGE MODELS AS AI RESEARCH AGENTS \- OpenReview, 访问时间为 四月 2, 2026， [https://openreview.net/pdf?id=N9wD4RFWY0](https://openreview.net/pdf?id=N9wD4RFWY0)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABL0lEQVR4Xu2SMUsDQRCFn6ASIWJjI/EPWFukCVZaaqGllTZJn0Kwtw+BWIj+Axv7EAJWYu0PUATBxsrSJO9lbr3dzXn7A7wPHne3b2ZvZneAigrHKjWNVEYPYWw3tEMeqQnSm77BYj5jo4gv6hWWsBx5jg51Bou5iLwFlqh7aghL2ArtOQNYq8/UO7Ud2ovsUi3qErbpfmhjgzrI3uUrLskp1aDasKTj0J5X6I6k6KeFqCWhir+pW89bgZ2l2IFtWsvtv/nInpvUC2wSHCPvvY/0dPyiCxJ1agybAqEL1FyKddjPXAGlqKUj7/sKNq9r1IO3rhhVKT+JWlKFjkNY8hPV9NbH2bqKKOWE+onWNH9KjudQa8nzvEYeqDbdJroste84p+6Qx95Qe55f8e+ZAUdpQ7lf2E8cAAAAAElFTkSuQmCC>