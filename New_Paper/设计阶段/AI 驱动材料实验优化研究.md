# **AI 驱动的闭环材料实验优化算法：LLM 与 RL 的前沿协同架构解析**

自驱式实验室（Self-Driving Laboratories, SDLs）的崛起正在从根本上重塑材料科学与化学合成的研发范式。传统的材料发现依赖于领域专家的直觉与高昂的试错成本，而现代闭环实验系统通过集成高通量自动化合成设备、原位表征技术以及由人工智能驱动的决策算法，能够在庞大的化学空间中实现自主导航与迭代寻优 1。在这一进程中，优化算法的设计是决定整个闭环系统发现效率的核心。

长期以来，贝叶斯优化（Bayesian Optimization, BO）因其严谨的不确定性量化能力和卓越的样本效率，被广泛作为这些闭环系统的主力计算引擎 4。然而，随着优化的目标体系向多维、多目标且包含复杂离散变量（如催化剂配体选择、溶剂种类）的方向演进，传统基于高斯过程（Gaussian Processes, GPs）的贝叶斯优化逐渐暴露出“冷启动”困难、高维空间扩展性差以及缺乏物理化学先验直觉等致命瓶颈 5。与此同时，强化学习（Reinforcement Learning, RL）作为序贯决策和连续控制的强大工具，在工业控制领域展现了巨大潜力，但其在物理科学中的应用却受制于极端的数据贪婪性（Sample Inefficiency）和与真实物理环境交互的巨大成本 8。

进入 2024 年下半年至 2026 年初，闭环材料优化算法领域经历了一次深刻的架构演进。具有强大语义理解与逻辑推理能力的大语言模型（Large Language Models, LLMs）开始被深度嵌入到主动学习循环中。通过将 LLM 的常识推理、基于文献的先验知识与 BO 的统计严谨性，或是与 RL 的底层策略执行能力相融合，研究人员开发出了一系列全新的协同与交替优化框架 11。这些混合架构不仅有效打破了单一算法的局限性，更为完全自主的科学发现铺平了道路。

本报告将系统性地深度剖析 2024 年中期以来的前沿文献与应用案例，围绕三大核心子方向展开论述：其一，探讨 LLM 嵌入贝叶斯优化循环在材料与化学参数寻优中的最新机制；其二，分析强化学习在直接优化化学组分配比与反应条件中的独立应用及与 BO 的性能对比；其三，深入解构 LLM 与 RL 协同、交替与分层规划的混合式前沿架构，揭示这些技术如何联合驱动下一代智能科学探索。

## **1\. LLM 嵌入贝叶斯优化循环：从冷启动到动态假设生成**

在材料科学的优化任务中，目标函数往往是一个评估成本极高的“黑盒”（例如一种新合金的电催化活性或特定反应的产率）。贝叶斯优化通过构建代理模型并最大化采集函数（Acquisition Function）来权衡探索（Exploration）与利用（Exploitation）14。然而，标准 BO 算法在初始阶段缺乏引导，且对化学语义一无所知。LLM 的引入，通过“语言输入-统计输出”的映射，为 BO 赋予了化学直觉与上下文感知能力 15。

### **1.1 突破冷启动困境：Warm-Start 机制与多任务知识迁移**

在传统的贝叶斯优化中，初始候选点的选择通常依赖于随机采样或拉丁超立方抽样（Latin Hypercube Sampling）。在包含数十个连续和分类变量的高维化学空间中，这种盲目的均匀采样往往导致大量昂贵的实验资源被浪费在无意义的非活性区域 17。

近期的研究成功地将 LLM 转化为高效的候选点生成器，以实现 BO 的“热启动”（Warm-Start）。例如，LILO（Large Language Models in the Loop）框架在优化初期摒弃了均匀采样，转而将先验领域知识以文本形式输入 LLM。LLM 凭借其对化学文献的预训练记忆，直接生成一批符合化学逻辑的初始候选点（![][image1]），从而在算法第一步就将优化的起点大幅拉近全局最优点 18。

更为复杂的场景体现在多任务优化中。BOLT（Bayesian Optimization with LLM Transfer）架构提出了一种突破性的多任务迁移机制。传统多任务 BO 需要构建极其复杂的联合代理模型，而 BOLT 另辟蹊径，在完成先前任务的 BO 轨迹后，将这些优化过程的数据用于微调 LLM 19。当面临具有新上下文描述（Context）的抗菌肽设计或相似催化任务时，该 LLM 能够直接在潜在空间中输出极高质量的热启动初始解。实验表明，经过充分微调后，由 BOLT 生成的初始池结合随后的 BO 迭代，其收敛速度和最终性能甚至超越了从零开始的纯 BO 算法 19。

除了初始生成，LLM 在偏好引导和候选点筛选方面也展现了巨大价值。在 LGBO（LLM-Guided Bayesian Optimization）框架中，研究人员引入了“区域提升偏好机制”（Region-Lifted Preference Mechanism）。该机制不再仅仅让 LLM 建议单个点，而是让 LLM 在每次迭代中基于化学直觉输出偏好区域，从而稳定且可控地偏移高斯过程代理模型的均值函数 6。在 Fe-Cr 电池电解液的真实湿法实验室优化中，标准 BO 需要 10 次以上的迭代才能逼近最优点，而 LGBO 仅在 6 次迭代内就达到了最佳观测值的 90%，展现了极为优异的样本效率 6。同时，面对庞大的 BO 提议点，基于生成式或过滤式的 LLM 能够筛选掉那些数学上可能带来高预期收益但化学上不稳定或无法合成的分子结构 2。

### **1.2 动态干预与实时假设生成：BORA 框架剖析**

LLM 与 BO 融合的另一大里程碑是 2025 年提出的基于语言的贝叶斯优化研究助手（BORA, Language-Based Bayesian Optimization Research Assistant）15。早期的方法（如 HypBO）倾向于在优化开始前由人类或 LLM 注入静态的软约束，而 BORA 实现了一种动态的、基于实时上下文的算法交替机制 21。

BORA 框架在底层维持标准 BO 代理模型的运行，但集成了一个自适应的启发式策略模块，持续监控优化的轨迹 22。当 BO 的“预期改进”（Expected Improvement）指标陷入停滞，即算法陷入局部最优（Local Minima）的“平原”时，BORA 会主动触发 LLM 介入 15。此时，LLM 会摄取系统迄今为止探索过的参数轨迹和性能反馈，利用上下文学习（In-Context Learning）进行推理，指出当前优化的盲区，并生成全新的、跳出当前局部区域的探索假设 15。

此外，BORA 还能生成关于优化进度的实时评论，将传统“黑盒”的统计寻优过程转化为人类研究员可读、可解释的透明过程 16。在涵盖 10 维光催化析氢实验（Photocatalytic Hydrogen-Evolution）和合成函数的基准测试中，BORA 的动态假设注入使得系统在搜索早期能够迅速锁定高潜力区域。在与多种基线模型的对比中，搭载 o3 或 gpt-4o-mini 等现代推理模型的 BORA 系统，其优化收敛速度和最终性能均显著超越了单纯的 BO 算法或缺乏统计保障的纯 LLM 算法 11。

### **1.3 开源 LLM 的领域适配与深层特征融合**

在材料与化学发现中，由于数据涉及商业机密或受到严格的版权限制，完全依赖封闭的商业 API（如 GPT-4）存在数据隐私和可重复性方面的巨大隐患。因此，学术界和工业界正加速向开源大语言模型（如 Qwen、LLaMA、Mistral）转移，这些模型不仅支持本地部署，还允许针对特定化学领域进行全参数或参数高效（PEFT）微调 25。

在这一趋势下，Perovskite-R1 成为了利用开源 LLM 驱动闭环材料发现的典范 29。研究团队基于拥有 320 亿参数的 QwQ-32B 开源模型，系统性地挖掘了 1200 多篇钙钛矿太阳能电池（PSC）领域的高质量文献，构建了包含前驱体添加剂知识和思维链（Chain-of-Thought, CoT）推理的指令微调数据集 29。经过微调的 Perovskite-R1 不仅能够智能地综合文献先见，还能自主提出用于缺陷钝化的新型前驱体添加剂组合。在随后的闭环验证实验中，由模型引导发现的配方使得 PSC 的光电转换效率（PCE）突破至 26.95%，极大提升了材料的长期稳定性，证实了领域专精的开源 LLM 在缩短研发周期上的决定性作用 29。

然而，将 LLM 应用于贝叶斯优化并非总是直接有效的。一项名为 *A Sober Look at LLMs for Material Discovery* 的 2024 年系统性研究指出，未经领域特殊处理的现成 LLM（Off-the-shelf LLMs）在分子空间的 BO 任务中，其表现往往不敌简单的统计基线 14。直接通过文本提示让 LLM 输出“不确定性估算”是缺乏数学依据且极易产生幻觉的。真正的突破在于深层特征融合——即不将 LLM 视为单纯的文本生成器，而是将其视为极其强大的特征提取器 32。在 GOLLuM（Gaussian Process Optimized LLMs）等高级框架中，LLM 在潜空间（Latent Space）生成的 Embedding 被直接用作高斯过程的深度核函数（Deep Kernel）。通过联合优化 LLM 的微调参数和 GP 超参数，系统在保留了 LLM 语义表达能力的同时，完美继承了 BO 严格的后验概率计算与不确定性量化能力，从而在极其稀疏的数据空间中实现了对分子结构的高效采样 17。

为了应对实验数据中普遍存在的高噪声问题，研究人员还提出了如 ChemBOMAS 这样的多智能体强化架构 7。该系统包含一个数据驱动的伪数据生成模块（用于提供宽泛的热启动）和一个知识驱动的 LLM 智能体。LLM 的核心作用是对物理化学搜索空间进行逻辑划分与修剪（Space Partitioning）。当热启动生成的伪数据存在噪声时，LLM 的先验规则能够防止 BO 偏离合理的化学流形；反之，当 LLM 的先验存在偏差时，由真实实验返回的密集奖励信号则会覆盖这些约束 7。

| 协同融合机制 | 核心算法与框架 | 在材料/化学闭环实验中的优势体现 | 代表性研究 |
| :---- | :---- | :---- | :---- |
| **智能热启动 (Warm-Start)** | 基于文本提示或多任务微调生成初始候选集 | 替代均匀采样，克服“冷启动”陷阱，显著节省昂贵的早期实验成本 | LILO 18, BOLT 19 |
| **动态交替与假设生成** | 当高斯过程预期改进停滞时触发 LLM 介入 | 破除局部最优困境，在非凸高维表面快速锁定高潜力搜寻区域 | BORA 15 |
| **深层内核特征融合** | 将 LLM 的潜空间表征作为高斯过程的 Deep Kernel | 完美结合文本语义的领域知识与贝叶斯定理的严格不确定性量化 | GOLLuM 17 |
| **物理搜索空间重塑** | 利用领域专精开源 LLM 引导偏好或进行空间修剪 | 避免数学模型探索热力学不稳定或无法合成的荒谬解，抵御数据噪声 | LGBO 6, ChemBOMAS 7, Perovskite-R1 29 |

## **2\. 强化学习在化学组分与反应条件直接优化中的前沿应用**

贝叶斯优化在处理低通量、静态批次的实验设计中表现优异，但面对具有高度时间相关性的连续动态过程，或面临需要对分子和催化剂结构进行离散拼接的组合爆炸问题时，BO 的代理模型训练复杂度和计算开销将呈指数级增加 5。为此，深度强化学习（Deep Reinforcement Learning, DRL）通过将优化任务建模为马尔可夫决策过程（MDP），赋予了智能体在复杂环境中通过试错学习和价值累积来逼近全局最优策略的能力 10。

### **2.1 连续动作空间的动态反应条件控制**

在流动化学（Flow Chemistry）和工业合成中，反应器的温度、压力、停留时间、试剂流速和底物浓度构成了一个高度非线性的连续控制系统。传统的 PID 控制器缺乏全局优化能力，而早期的离散动作强化学习（如 DQN 或 Q-Learning）由于动作空间切分导致的量化误差，难以在连续反应环境中实现精细控制 36。

为解决这一问题，深度确定性策略梯度（Deep Deterministic Policy Gradient, DDPG）和软演员-评论家（Soft Actor-Critic, SAC）等面向连续动作空间的离线策略（Off-policy）算法被广泛应用 36。在一项关于甲烷部分氧化（POX）制氢的反应条件优化研究中，研究人员部署了 DDPG 智能体以最大化氢气产率。研究发现，相较于在复杂模拟环境中表现挣扎的 Q-learning 智能体，DDPG 智能体能够精准地动态调整多维连续参数（如流速和温度配比），成功在非线性的反应动力学约束下锁定了产率极值点 36。

### **2.2 催化剂结构与组分配比的全局拓扑优化**

强化学习不仅在反应条件的动态调整上大放异彩，更被直接深入应用于催化剂的微观结构设计。纳米合金催化剂（如双金属合金纳米颗粒）的活性高度依赖于其元素的空间排布和比例。寻找最优的原子构型是一个极其庞大的组合优化难题，传统的遗传算法（GA）或密度泛函理论（DFT）暴力搜索在此类任务中显得无能为力 35。

在一项 2024 年的研究中，研究者构建了一个直接操作催化剂组分的 RL 智能体。该智能体将双金属合金纳米颗粒抽象为几何图表示（Geometric Graph Representation），并通过实施保持整体组分比例不变的“原子交换”（Atomic Swap）动作来进行拓扑变异 35。为了捕捉原子的三维空间关系，该系统引入了预训练的等变图神经网络（Equivariant GNN）作为状态编码器。经过在随机初始化的 Ag-Au 纳米颗粒上进行训练，该 RL 策略不仅自主发现了已知的能量基态结构，还能出色地将习得的优化策略外推至未见过尺寸的纳米颗粒中，大幅降低了重复独立搜索的计算成本 35。

### **2.3 奖励工程与探索崩溃的破局：RE-EXPLORE 框架**

将 RL 用于生成式化学空间探索时，最棘手的问题之一是“奖励黑客行为”（Reward Hacking）与模式崩溃（Mode Collapse）。智能体为了最大化短期内的反应产率奖励，往往会退化为反复生成同一种极易合成但缺乏新颖性的分子结构，完全丧失对广阔化学空间的探索能力 34。

针对这一顽疾，《美国化学会志》（JACS）在 2024 年报道的 RE-EXPLORE 框架提供了一个巧妙的解决方案 34。该框架集成了一个基于循环神经网络（RNN）的深度生成模型和一个用于预测产率与对映体过量（%ee）的回归器。在策略梯度的训练循环中，研究人员对 RL 的奖励函数进行了根本性的重塑：在反应产率和选择性得分的基础上，强制叠加了基于 Tanimoto 相似度的“唯一性惩罚因子”（Uniqueness Factor）34。这一经过精心设计的环境奖励机制迫使智能体在利用高分结构的同时，必须保持向多样化的化学空间延展。在使用 ChEMBL 和 ZINC 数据库的百万级无标签分子进行预训练后，结合这种探索-利用平衡的奖励机制，RE-EXPLORE 成功发现了具有极高对映选择性的新型手性催化剂和高产率底物，证明了 RL 在逆向合成和药物先导化合物设计中的巨大潜力 34。

### **2.4 离线强化学习与基于模型的强化学习：打破样本效率瓶颈**

尽管在线强化学习（Online RL）理论上可以寻找最优解，但在化学实验室中执行数以万计的试错动作是极其昂贵、耗时且具有安全风险的 9。为了打破“数据贪婪”带来的样本效率瓶颈，离线强化学习（Offline RL）和基于模型的强化学习（Model-Based RL, MBRL）成为了 2024 年以来的核心研究热点 40。

**离线强化学习 (Offline RL)** 允许智能体完全基于历史遗留的、静态的次优实验数据集进行策略学习，无需与真实环境发生任何在线交互 9。例如，在针对逆向合成反应条件搜索或晶体带隙设计的任务中，Offline RL 模型可以通过学习过去失败或低产率的数据，提炼出潜在的化学规律。在 MolStitch 框架中，研究人员采用了“轨迹拼接”（Trajectory Stitching）技术，将历史数据中不同分子的成功局部片段重新组合，结合条件扩散模型（Conditional Diffusion Model）生成满足多目标属性的全新分子 40。然而，Offline RL 极易遭遇分布外（OOD）的外推误差。为保证生成的反应条件物理可行，研究者通常引入凸神经网络约束（Convex Neural Networks）或控制障碍函数（Control Barrier Functions, CBFs），并应用重加权策略（Sample Reweighting）来滤除历史数据中的劣质干扰 9。

**基于模型的强化学习 (Model-Based RL)** 则采用另一种思路：利用已有的物理化学知识或有限的实验数据，训练一个深度神经网络（如物理信息神经网络 PINN 或深度算子网络 DeepONet）作为真实实验室环境的高精度代理模拟器 43。智能体在这一模拟器内进行数百万次的低成本交互和规划（Planning），待策略收敛后，再进行“Zero-Shot”迁移至真实实验室。这种方法在纳米金属簇几何优化、控制反应-扩散偏微分方程（PDE）等任务中，展现出了比无模型（Model-Free）RL 高出几个数量级的采样效率，为应对高昂实验成本提供了最切实可行的方案 37。

### **2.5 强化学习与贝叶斯优化的对比研究验证**

随着这两大算法在化学过程中的深度应用，研究人员在同一平台上对它们进行了严密的对比。在流动化学中针对亚胺合成（Imine Synthesis）的闭环优化实验中，基于 DDPG 的深度强化学习在自优化性能上显著优于传统的免梯度方法（如 Nelder-Mead）和贝叶斯优化（搭配 SnobFit）45。对比数据显示，DDPG 智能体能够更敏锐地捕捉全局非线性动态，在极少的调整步骤中追踪到全局最优解，相比传统的 BO 探索流程，将达到最佳产率所需的实验轮数大幅削减了 50% 至 75% 45。这进一步确立了在连续、动态且状态空间相互耦合的化学工程领域，强化学习相对于贝叶斯优化的比较优势。

## **3\. LLM 与 RL 协同、交替的混合规划架构：通向自主科学代理**

随着自驱式实验室朝着更高自动化程度演进，单一算法的固有缺陷愈发明显：大语言模型（LLMs）虽然拥有浩瀚的化学先验知识和卓越的语义规划能力，但缺乏对物理规则的精确数值优化能力，且极易在无约束生成中产生“幻觉”；而强化学习（RL）虽然擅长底层的数值控制和连续动作寻优，但极度缺乏“常识”，面对奖励稀疏（Sparse Reward）的高维任务往往陷入毫无头绪的随机探索 8。

在 2024 年中期至 2026 年的前沿探索中，学术界实现了范式的跃迁，将 LLM 与 RL 进行深度融合，构建出分层、交替、闭环共进化的混合式架构（LLM-RL Hybrid Frameworks）。在这种架构中，LLM 扮演高层认知与规划大脑，而 RL 充当底层的运动神经与数值执行器 8。

### **3.1 LLM 驱动的奖励重塑与搜索空间定义 (LLM-Guided Reward Shaping)**

在复杂的科学发现（如新型药物分子的靶点亲和力或反应路线的经济性）中，为强化学习设计一个精确的数学奖励函数几乎是不可能的。细微的化学基团改变可能导致性质的剧变，这很难用简单的欧氏距离或单一目标函数来衡量。

LLM 引导的强化学习（LLM-guided RL）通过让大语言模型充当“虚拟奖励评判器”，实现了语义目标向密集数值信号的转化 47。在 GPRS（Group Preference Reward Shaping）和 Logic-RL 框架中，LLM 基于预先注入的化学规则和人类偏好指令，对 RL 智能体生成的复杂分子序列或反应条件进行评估 49。LLM 的自然语言理解能力不仅能识别出化学上不合理的“坏点”，还能判断反应路线的新颖性和可行性。通过这种方式，原本对 RL 而言是延迟且稀疏的成败反馈，被 LLM 转化为细粒度的、步骤级别的密集奖励（Dense Rewards），从而规避了 RL 无效的盲目探索时间，极大加速了其在化学空间中的策略收敛 46。

### **3.2 认知-执行的层次化分层架构 (Hierarchical LLM-RL Planning)**

人类科学家在进行实验时，通常遵循“高层战略规划——底层操作执行”的逻辑。现代分层 RL-LLM 混合架构（如 LGRL 框架和 GLIDER 系统）完全复刻了这一认知模式 8。

在 LGRL 架构中，大语言模型被定义为元优化器（Meta-optimizer）。面对一个宏观的科学目标（例如“在特定溶剂中合成具备特定光吸收光谱的纳米材料”），LLM 利用思维链（Chain of Thought, CoT）能力，将这个长视距（Long-horizon）任务分解为一系列具有语义连续性的小目标（Subgoals）8。这些子目标随后被传递给底层的强化学习智能体。RL 智能体不再需要理解宏大的合成使命，它只需专注于如何执行具体的低级控制动作（如“在 5 分钟内将反应器温度从 25°C 升至 120°C 并在给定压力下维持”）来满足当前子目标。

这种“解耦”机制至关重要。它使得顶层 LLM 在推理时不涉及高昂的在线权重更新，同时使得底层 RL 智能体的探索空间被严格限制在符合物理逻辑的微观状态内，彻底解决了大规模动作空间带来的数据低效问题，在动态和未知的仿真环境中表现出非凡的鲁棒性与泛化能力 8。

### **3.3 “Think Twice, Act Once”：交替接力与共进化机制**

在 LLM 与 RL 的融合中，最极致的形态当属“代理共进化”（Agents Co-Evolution, ACE）框架，即所谓的“三思而后行”（Think Twice, Act Once）闭环机制 12。在此架构下，LLM 与 RL 不再是单向的指令下发，而是形成了一个 LLM \-\> RL \-\> LLM 的双向交替、共进化的智能反馈环 57。

以 ACE 框架在超大规模动作空间（大于 60,000 种可能动作）的复杂决策场景为例，LLM 在 RL 的训练过程中同时扮演了“策略行动者”（Policy Actor）和“价值评论家”（Value Critic）的双重身份：

1. **Actor 角色的轨迹重精炼 (Trajectory Refinement)：** 在探索过程中，当 RL 智能体在环境中采取了导致低奖励的次优化学行动时（这在初期极其常见），该状态-动作对（State-Action pair）会被提取并转化为自然语言文本。LLM 随后介入，执行“坏案推理”（Bad Case Reasoning）。基于其化学知识，LLM 分析失败的原因，并在仿真环境验证下生成一个优化后的高质量动作，替换掉 RL 原本的错误决策 56。  
2. **Critic 角色的长期信用分配 (Temporal Credit Assignment)：** 面对多步连贯的长视距化学反应，LLM 通过审视整个实验轨迹，识别出究竟是哪一个关键的步骤（Pivot Action）决定了最终的高产率。这种基于语义的轨迹级奖励重塑，远比传统的时间差分（TD）更新来得准确 55。

作为反哺，RL 智能体在无数次的物理环境交互中，积累了大量高质量的、经过试错筛选的边缘案例（Edge Cases）数据。系统通过优先级经验回放（Prioritized Experience Replay），将这些宝贵的领域数据反向用于对 LLM 进行在线微调（采用 DPO 或 LoRA 技术）55。这种互相纠错、双向微调的交替接力（Alternating decision-making），使得系统在解决工业级材料优化难题时，其收敛准确度对纯 LLM 方案和纯 RL 方案形成了碾压级的降维打击 55。

### **3.4 迈向全自动科学闭环的多智能体系统 (Multi-Agent End-to-End Discovery)**

当混合了强化学习反馈的专精 LLM 演化为多智能体群落（Multi-Agent Systems, MAS）时，化学实验室迎来了真正意义上的全自动“AI 科学家”。

在 2025 年发布的 *Robin* 多智能体系统中，科研流程中耗费脑力的环节被完全解构 61。文献检索智能体首先在开源数据库中遍历数百万篇文献，利用 RAG（检索增强生成）技术构建化学合成先验网络。随后，由融合了 RL 策略规划的实验设计智能体接管，制定出精细的反应拓扑路径。实验通过云端接入的物理或虚拟实验室执行后，数据分析智能体会自动提取质谱或光谱反馈。最后，主导决策的 LLM 会根据 RL 传回的评价分数，运用底层规则更新其贝叶斯先验信念，并据此提出迭代后的新科学假设 13。尽管此类系统在面对长文本生成时仍存在隐蔽“学术幻觉”的风险（例如捏造高深但不存在的物理常数），但在严谨的 RL 物理规则和数学奖励函数的紧密锚定下，多智能体网络已成功实现了针对干性年龄相关性黄斑变性（dAMD）等领域新型先导化合物的半自主闭环发现 62。

## **结语**

从 2024 年至 2026 年初的文献与应用演进中可以清晰地看到，AI 驱动的闭环材料实验优化算法已经从单模态、单机制的“统计学游戏”，迈向了多模态融合、认知与执行高度协同的“系统工程”。

贝叶斯优化在应对高维度、高噪声的材料筛选时，借助 LLM 实现了由冷启到热启的飞跃。诸如 BORA 与 ChemBOMAS 等框架证明，LLM 不仅能作为高效的特征核，其基于上下文推理的动态干预机制更是破除高维非凸搜索空间局部最优解的利器。另一方面，强化学习凭借在连续参数控制与图结构变异上的优势，正重塑流体反应与催化剂微观结构的设计范式。辅以 Tanimoto 唯一性等奖励重构以及 Offline/Model-based RL 技术，RL 的样本低效困局正在被彻底瓦解。

最终，所有路径都汇聚于 LLM 与 RL 的深度交替与分层混合架构。通过“Think Twice, Act Once”的共进化接力，将语言模型在高语义空间的降维规划与强化学习在低熵数值空间的精准试错完美啮合，不仅补齐了 LLM 脱离物理法则的短板，更为复杂的长视距科学探索赋予了人类级别的战略纵深。这一协同架构，正无可阻挡地成为驱动下一代自驱式实验室自动化化学合成与智能材料发现的核心大脑。

#### **引用的著作**

1. ChemBOMAS: Accelerated BO in Chemistry with LLM-Enhanced Multi-Agent System \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2509.08736v1](https://arxiv.org/html/2509.08736v1)  
2. LLMs for Bayesian Optimization in Scientific Domains: Are We There Yet? \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2509.21403v1](https://arxiv.org/html/2509.21403v1)  
3. AI-Accelerated Materials Discovery in 2026: How Generative Models, Graph Neural Networks, and Autonomous Labs Are Transforming R\&D | Cypris, 访问时间为 四月 2, 2026， [https://www.cypris.ai/insights/ai-accelerated-materials-discovery-in-2025-how-generative-models-graph-neural-networks-and-autonomous-labs-are-transforming-r-d](https://www.cypris.ai/insights/ai-accelerated-materials-discovery-in-2025-how-generative-models-graph-neural-networks-and-autonomous-labs-are-transforming-r-d)  
4. A Guide to Bayesian Optimization in Bioprocess Engineering \- PMC \- NIH, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC13003447/](https://pmc.ncbi.nlm.nih.gov/articles/PMC13003447/)  
5. Enhancing Bayesian Optimization with the Long-Context Reasoning Power of LLMs \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2505.12833v2](https://arxiv.org/html/2505.12833v2)  
6. Unleashing LLMs in Bayesian Optimization: Preference-Guided Framework for Scientific Discovery \- ICLR 2026, 访问时间为 四月 2, 2026， [https://iclr.cc/virtual/2026/poster/10010010](https://iclr.cc/virtual/2026/poster/10010010)  
7. ChemBOMAS: Accelerated Bayesian Optimization for Scientific Discovery in Chemistry with LLM-Enhanced Multi-Agent System | OpenReview, 访问时间为 四月 2, 2026， [https://openreview.net/forum?id=XEkQu1ZWGN](https://openreview.net/forum?id=XEkQu1ZWGN)  
8. LLM-Guided Reinforcement Learning for Interactive Environments \- MDPI, 访问时间为 四月 2, 2026， [https://www.mdpi.com/2227-7390/13/12/1932](https://www.mdpi.com/2227-7390/13/12/1932)  
9. Generative Discovery via Reinforcement Learning \- DSpace@MIT, 访问时间为 四月 2, 2026， [https://dspace.mit.edu/bitstream/handle/1721.1/159135/hong-zwhong-phd-eecs-2025-thesis.pdf?sequence=-1\&isAllowed=y](https://dspace.mit.edu/bitstream/handle/1721.1/159135/hong-zwhong-phd-eecs-2025-thesis.pdf?sequence=-1&isAllowed=y)  
10. Materials discovery through reinforcement learning: a comprehensive review \- ELSP, 访问时间为 四月 2, 2026， [https://www.elspub.com/papers/j/1911766509499953152.html](https://www.elspub.com/papers/j/1911766509499953152.html)  
11. Can We Automate Scientific Reasoning in Closed-Loop Experiments using Large Language Models? | ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/doi/10.26434/chemrxiv.10001632](https://chemrxiv.org/doi/10.26434/chemrxiv.10001632)  
12. Poster Session 2 West \- ICML 2026, 访问时间为 四月 2, 2026， [https://icml.cc/virtual/2025/session/50258](https://icml.cc/virtual/2025/session/50258)  
13. Large language models for reticular chemistry \- Omar Yaghi, 访问时间为 四月 2, 2026， [https://yaghi.berkeley.edu/pdfPublications/25LLMRetChem.pdf](https://yaghi.berkeley.edu/pdfPublications/25LLMRetChem.pdf)  
14. Bayesian Optimization for Biochemical Discovery with LLMs \- ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-w1wsh](https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-w1wsh)  
15. Language-Based Bayesian Optimization Research Assistant (BORA) \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2501.16224v1](https://arxiv.org/html/2501.16224v1)  
16. LLM-Guided Bayesian Optimization \- Emergent Mind, 访问时间为 四月 2, 2026， [https://www.emergentmind.com/topics/llm-guided-bayesian-optimization-llm-guided-bo](https://www.emergentmind.com/topics/llm-guided-bayesian-optimization-llm-guided-bo)  
17. LLM-Guided Bayesian Optimization \- Emergent Mind, 访问时间为 四月 2, 2026， [https://www.emergentmind.com/topics/llm-guided-bayesian-optimization](https://www.emergentmind.com/topics/llm-guided-bayesian-optimization)  
18. LILO: Bayesian Optimization with Interactive Natural Language Feedback \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2510.17671v1](https://arxiv.org/html/2510.17671v1)  
19. Large Scale Multi-Task Bayesian Optimization with Large Language Models \- arXiv.org, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2503.08131v2](https://arxiv.org/html/2503.08131v2)  
20. Large Scale Multi-Task Bayesian Optimization with Large Language Models \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/pdf/2503.08131](https://arxiv.org/pdf/2503.08131)  
21. Language-Based Bayesian Optimization Research Assistant (BORA) \- IJCAI, 访问时间为 四月 2, 2026， [https://www.ijcai.org/proceedings/2025/0553.pdf](https://www.ijcai.org/proceedings/2025/0553.pdf)  
22. General-Purpose Models for the Chemical Sciences: LLMs and Beyond \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acs.chemrev.5c00583](https://pubs.acs.org/doi/10.1021/acs.chemrev.5c00583)  
23. Effect of LLM choice on hybrid LLM/BO optimisation (BORA) for a... \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/figure/Effect-of-LLM-choice-on-hybrid-LLM-BO-optimisation-BORA-for-a-10-dimensional\_fig1\_401074479](https://www.researchgate.net/figure/Effect-of-LLM-choice-on-hybrid-LLM-BO-optimisation-BORA-for-a-10-dimensional_fig1_401074479)  
24. Ablatif6c/bora-the-explorer \- GitHub, 访问时间为 四月 2, 2026， [https://github.com/Ablatif6c/bora-the-explorer](https://github.com/Ablatif6c/bora-the-explorer)  
25. LLMs for Bayesian Optimization in Scientific Domains: Are We There Yet? \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/pdf/2509.21403](https://arxiv.org/pdf/2509.21403)  
26. Large Language Models for Combinatorial Optimization: A Systematic Review \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2507.03637v1](https://arxiv.org/html/2507.03637v1)  
27. Implementing generative artificial intelligence in precision oncology: safety, governance, and significance \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12896320/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12896320/)  
28. The 2025 Conference on Empirical Methods in Natural Language Processing, 访问时间为 四月 2, 2026， [https://aclanthology.org/events/emnlp-2025/](https://aclanthology.org/events/emnlp-2025/)  
29. Perovskite-R1: A Domain-Specialized LLM for Intelligent Discovery of Precursor Additives and Experimental Design | Request PDF \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/393923553\_Perovskite-R1\_A\_Domain-Specialized\_LLM\_for\_Intelligent\_Discovery\_of\_Precursor\_Additives\_and\_Experimental\_Design](https://www.researchgate.net/publication/393923553_Perovskite-R1_A_Domain-Specialized_LLM_for_Intelligent_Discovery_of_Precursor_Additives_and_Experimental_Design)  
30. Perovskite-R1: A Domain-Specialized LLM for Intelligent Discovery of Precursor Additives and Experimental Design \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2507.16307v1](https://arxiv.org/html/2507.16307v1)  
31. Perovskite-R1: A Domain-Specialized LLM for Intelligent Discovery of Precursor Additives and Experimental Design \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/pdf/2507.16307](https://arxiv.org/pdf/2507.16307)  
32. A Sober Look at LLMs for Material Discovery: Are They Actually Good for Bayesian Optimization Over Molecules?, 访问时间为 四月 2, 2026， [https://proceedings.mlr.press/v235/kristiadi24a.html](https://proceedings.mlr.press/v235/kristiadi24a.html)  
33. ChemBOMAS: Accelerated BO for Scientific Discovery in Chemistry with LLM-Enhanced Multi-Agent System \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2509.08736v2](https://arxiv.org/html/2509.08736v2)  
34. Reinforcement Learning for Improving Chemical Reaction Performance \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/jacs.4c08866](https://pubs.acs.org/doi/10.1021/jacs.4c08866)  
35. Reinforcement Learning for Chemical Ordering in Alloy Nanoparticles \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2511.12260v2](https://arxiv.org/html/2511.12260v2)  
36. Reinforcement Learning Approaches for the Optimization of the Partial Oxidation Reaction of Methane | Industrial & Engineering Chemistry Research \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acs.iecr.1c04622](https://pubs.acs.org/doi/10.1021/acs.iecr.1c04622)  
37. (PDF) Materials discovery through reinforcement learning: a comprehensive review, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/392578066\_Materials\_discovery\_through\_reinforcement\_learning\_a\_comprehensive\_review](https://www.researchgate.net/publication/392578066_Materials_discovery_through_reinforcement_learning_a_comprehensive_review)  
38. Reinforcement Learning for Improving Chemical Reaction Performance \- PubMed, 访问时间为 四月 2, 2026， [https://pubmed.ncbi.nlm.nih.gov/39356950/](https://pubmed.ncbi.nlm.nih.gov/39356950/)  
39. Safe Deployment of Offline Reinforcement Learning via Input Convex Action Correction, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2507.22640v1](https://arxiv.org/html/2507.22640v1)  
40. Offline Model-based Optimization for Real-World Molecular Discovery | OpenReview, 访问时间为 四月 2, 2026， [https://openreview.net/forum?id=erbRHt0XgI](https://openreview.net/forum?id=erbRHt0XgI)  
41. ICLR 2025 Spotlights, 访问时间为 四月 2, 2026， [https://iclr.cc/virtual/2025/events/spotlight-posters](https://iclr.cc/virtual/2025/events/spotlight-posters)  
42. ICML Poster Offline Model-based Optimization for Real-World Molecular Discovery, 访问时间为 四月 2, 2026， [https://icml.cc/virtual/2025/poster/44562](https://icml.cc/virtual/2025/poster/44562)  
43. Control-Informed Reinforcement Learning for Chemical Processes | Industrial & Engineering Chemistry Research \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acs.iecr.4c03233](https://pubs.acs.org/doi/10.1021/acs.iecr.4c03233)  
44. Reinforcement Operator Learning (ROL): A hybrid DeepONet-guided reinforcement learning framework for stabilizing the Kuramoto–Sivashinsky equation \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12858074/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12858074/)  
45. Deep Reinforcement Learning-Based Self-Optimization of Flow Chemistry \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12183679/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12183679/)  
46. Novelty Adaptation Through Hybrid Large Language Model (LLM)-Symbolic Planning and LLM-guided Reinforcement Learning \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/pdf/2603.11351](https://arxiv.org/pdf/2603.11351)  
47. Integrating Large Language Models into Traffic Systems: Integration Levels, Capability Boundaries, and an Information-Theoretic Perspective \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12939955/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12939955/)  
48. Emergent Hierarchical Reasoning in LLMs through Reinforcement Learning \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2509.03646v3](https://arxiv.org/html/2509.03646v3)  
49. Enhancing Bayesian Optimization with the Long-Context Reasoning Power of LLMs \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2505.12833v1](https://arxiv.org/html/2505.12833v1)  
50. Reinforcement Learning for Large Language Models via Group Preference Reward Shaping \- ACL Anthology, 访问时间为 四月 2, 2026， [https://aclanthology.org/2025.emnlp-main.1085.pdf](https://aclanthology.org/2025.emnlp-main.1085.pdf)  
51. Reward Modeling for Reinforcement Learning-Based LLM Reasoning: Design, Challenges, and Evaluation \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/pdf/2602.09305](https://arxiv.org/pdf/2602.09305)  
52. Divide and Conquer: Grounding LLMs as Efficient Decision-Making Agents via Offline Hierarchical Reinforcement Learning \- ICML 2026, 访问时间为 四月 2, 2026， [https://icml.cc/virtual/2025/poster/43989](https://icml.cc/virtual/2025/poster/43989)  
53. NeurIPS Poster Hierarchical Optimization via LLM-Guided Objective Evolution for Mobility-on-Demand Systems, 访问时间为 四月 2, 2026， [https://neurips.cc/virtual/2025/poster/117702](https://neurips.cc/virtual/2025/poster/117702)  
54. Tutorial on Large Language Model-Enhanced Reinforcement Learning for Wireless Networks \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2512.03722v1](https://arxiv.org/html/2512.03722v1)  
55. ICML Poster Think Twice, Act Once: A Co-Evolution Framework of LLM and RL for Large-Scale Decision Making, 访问时间为 四月 2, 2026， [https://icml.cc/virtual/2025/poster/43534](https://icml.cc/virtual/2025/poster/43534)  
56. Think Twice, Act Once: A Co-Evolution Framework of LLM and RL for Large-Scale Decision Making \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2506.02522v1](https://arxiv.org/html/2506.02522v1)  
57. Stronger-MAS: Multi-Agent Reinforcement Learning for Collaborative LLMs \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2510.11062v5](https://arxiv.org/html/2510.11062v5)  
58. Integrating Large Language Models with Reinforcement Learning: A Survey of LLM-RL Synergistic Recommendation \- TechRxiv, 访问时间为 四月 2, 2026， [https://www.techrxiv.org/users/1027900/articles/1387604/master/file/data/Integrating%20Large%20Language%20Models%20with%20Reinforcement%20Learning-%20A%20Survey%20of%20LLM-RL%20Synergistic%20Recommendation/Integrating%20Large%20Language%20Models%20with%20Reinforcement%20Learning-%20A%20Survey%20of%20LLM-RL%20Synergistic%20Recommendation.pdf?inline=true](https://www.techrxiv.org/users/1027900/articles/1387604/master/file/data/Integrating%20Large%20Language%20Models%20with%20Reinforcement%20Learning-%20A%20Survey%20of%20LLM-RL%20Synergistic%20Recommendation/Integrating%20Large%20Language%20Models%20with%20Reinforcement%20Learning-%20A%20Survey%20of%20LLM-RL%20Synergistic%20Recommendation.pdf?inline=true)  
59. \[Literature Review\] Think Twice, Act Once: A Co-Evolution Framework of LLM and RL for Large-Scale Decision Making \- Moonlight, 访问时间为 四月 2, 2026， [https://www.themoonlight.io/en/review/think-twice-act-once-a-co-evolution-framework-of-llm-and-rl-for-large-scale-decision-making](https://www.themoonlight.io/en/review/think-twice-act-once-a-co-evolution-framework-of-llm-and-rl-for-large-scale-decision-making)  
60. (PDF) Think Twice, Act Once: A Co-Evolution Framework of LLM and RL for Large-Scale Decision Making \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/392371293\_Think\_Twice\_Act\_Once\_A\_Co-Evolution\_Framework\_of\_LLM\_and\_RL\_for\_Large-Scale\_Decision\_Making](https://www.researchgate.net/publication/392371293_Think_Twice_Act_Once_A_Co-Evolution_Framework_of_LLM_and_RL_for_Large-Scale_Decision_Making)  
61. June, 2025 — The CoVar Zeitgeist 1.0.0 documentation, 访问时间为 四月 2, 2026， [https://zeitgeist.covar.com/issues/2025-06.html](https://zeitgeist.covar.com/issues/2025-06.html)  
62. AI-Driven Scientific Research: The Revolution Has Begun | by evoailabs | Medium, 访问时间为 四月 2, 2026， [https://evoailabs.medium.com/ai-driven-scientific-research-the-revolution-has-begun-ff95e285cc1c](https://evoailabs.medium.com/ai-driven-scientific-research-the-revolution-has-begun-ff95e285cc1c)  
63. Can AI Conduct Autonomous Scientific Research? Case Studies on Two Real-World Tasks, 访问时间为 四月 2, 2026， [https://www.biorxiv.org/content/10.64898/2026.01.05.697809.full](https://www.biorxiv.org/content/10.64898/2026.01.05.697809.full)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABIUlEQVR4XmNgGAWjgNpgMhD/JwLLwDSQC7YyQAzCBrwZIHLy6BKkgN9AfBpdEAk8B+IH6ILEAhYGiAuj0SWQwAEG3D4kCMQZIJqN0SWQwAEGCiwoYoBoZkSXQAKfGMi0AOT6u0D8FV0CCYAsBhn+AE2cKABz/Xx0CSTgwgBRY4kkthqIHYC4gwGSAHCCNQz4Ixjk+ikMEDWsSOLvoTQogcxhwJNPQMkTpFkQXQIKNjNA5IORxDyBeCkSH+RDkEMxAAcDRDOuyOtjgMgVo4lXAfFCJD4o9T1E4oPBLCA+zgAx4CeUD8N7oOKgYgQbABlO0AJKQDoDpgX4SgGSgQ0DpOyCAV8GHHFACQAlDhDgB+JDQCyMJEc1EMAACR5mdImhDQDvyUUVZFtiFgAAAABJRU5ErkJggg==>