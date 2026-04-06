# **自主驱动实验室在电催化材料发现中的前沿进展与算法架构创新路径**

在当前的材料科学与化学工程交叉领域，传统的“试错法”实验模式正经历着一场根本性的范式转变。随着人工智能（AI）、机器人技术和高通量表征技术的深度融合，完全自主的闭环实验系统——即自主驱动实验室（Self-Driving Laboratories, SDLs）——正成为加速新材料发现的核心引擎 1。在电催化领域，特别是针对析氢反应（Hydrogen Evolution Reaction, HER）催化剂的研发中，寻找能够兼顾高催化活性（如低过电位、高电流密度）与卓越的抗反向电流稳定性的最优元素配比（如Fe、Co、Ni的多元混合），面临着组合空间庞大、多目标相互制约的巨大挑战 4。

在缺乏基于第一性原理计算（如密度泛函理论，DFT）先验数据支持，且不依赖当前流行的生成式结构模型（如Diffusion扩散模型）的硬性约束下，构建一个纯粹由经验数据、文献知识检索和智能算法驱动的闭环自动化实验平台，成为了破局的关键 7。本报告旨在深度剖析当前自主驱动实验室的前沿文献与主流创新范式，系统拆解高影响力闭环实验室学术论文的论述逻辑与结构特征，详述多智能体（Multi-Agent）在材料实验中的物理控制与协调机制，并从计算机底层算法架构的角度，为无先验计算介入条件下的系统知识检索、模型改造与自愈诊断提供深度的架构演进路径。

## **领域前沿文献分类与主流创新范式梳理**

在当前材料发现与化学自动化的研究前沿，科研创新的核心已不再局限于某一特定材料的性能突破，而是转向了对“科学发现过程”本身的重构 10。通过对近年来发表在《Nature》、《Science》、《JACS》等顶级期刊上的权威文献进行系统梳理，可以看出，主流的创新范式正从单一的“机械自动化”向“认知与推理驱动”的智能体协同演进 12。基于无需材料计算和生成式空间结构的约束，当前的前沿研究可归纳为以下三个核心象限：

| 文献聚焦领域与创新范式 | 核心机制与代表性系统 | 对纯经验/数据驱动研究的启示 | 支撑文献 |
| :---- | :---- | :---- | :---- |
| **大语言模型与多智能体协同实验调度** | 将实验任务分解为多个专职Agent（如文献阅读、方案设计、硬件执行、数据分析）。代表系统：ChemAgents, Coscientist。 | 证明了LLM可以直接将自然语言意图转化为可执行的硬件脚本（如Python代码），并在无物理建模的情况下通过逻辑推理完成复杂的化学合成与表征闭环。 | 14 |
| **高通量电化学与多目标贝叶斯优化 (MOBO)** | 结合流动化学或自动化工作站，利用高斯过程回归和主动学习策略在多维元素空间中寻找帕累托前沿。代表系统：FastCat, ACE Platform。 | 在无需DFT计算的条件下，仅依靠在线测试的电化学数据（如极化曲线特征）驱动贝叶斯优化，快速锁定Ni-Fe-Co-Cr等多元素最优配比，平衡催化活性与稳定性。 | 5 |
| **硬件抽象层与实验室中间件架构** | 开发标准化、解耦的软硬件通信框架，实现异步并发控制与仪器级的状态机管理。代表平台：PyLabRobot, HELAO-async。 | 强调了构建如同MicroHySeeker般的底层硬件控制中间件的必要性，通过标准的API接口（如RESTful/FastAPI）将底层串口通信（RS485）与上层AI推理完全隔离。 | 20 |

上述文献分类揭示了一个明确的行业趋势：未来的科研壁垒不再是单纯的算力堆叠或材料表征的精度，而是如何构建一个能够将“人类科学直觉”、“历史失败经验”以及“实时仪器反馈”无缝融合的复杂软件工程架构 22。例如，FastCat系统在极短的时间内合成了数百种Ni基多元素层状双氢氧化物（LDH）OER催化剂，其核心创新点不在于发现了某种神奇的晶体结构，而在于其利用AI编排的闭环系统，在没有人类干预的情况下，每天能够合成并电化学测试75种材料组合，并依靠趋势分析自主验证其耐久性 19。这种剥离了复杂材料计算、纯粹依靠实验数据驱动的数据飞轮，正是当前无计算基础条件下的最优解 25。

## **闭环实验室学术论文的结构范式与论述逻辑**

对于试图在顶级学术期刊上发表闭环实验室（SDL）成果的研究者而言，理解此类论文特有的叙事结构至关重要。传统的材料科学论文通常遵循“提出材料设计思路—表征物理结构—测试电化学性能—解释催化机理”的线性逻辑 26。然而，闭环实验室的论文在本质上是“系统工程与人工智能”的交叉验证报告，其主角不再是某种特定的催化剂（如最优的Fe-Co-Ni配比），而是**这个能够自主发现该催化剂的智能系统** 1。

通过深度解构《Nature》上的Coscientist、《JACS》上的ChemAgents以及近期预印本中的FastCat等权威工作，可以归纳出此类高影响力论文的核心结构范式与论述逻辑 14。

### **系统架构与层级解耦的定义**

论文的开篇与核心图表通常致力于展示硬件与软件的解耦架构。高水平的论述会明确界定系统的认知层（AI决策与规划）与执行层（硬件驱动与传感反馈）22。例如，研究会详细阐述类似AutoHySeeker的决策中心如何通过工作流编排多个Agent（如任务管理器、文献阅读器、计算执行器和机器人操作员），以及这些Agent如何通过API与类似MicroHySeeker的底层硬件系统通信 14。这种架构的展示不仅证明了系统的模块化与可扩展性，也向同行展示了底层协议（如RS485、TCP/IP）如何被抽象为高阶的科学指令 21。

### **自主性等级的声明与人机边界的划定**

顶级期刊极其看重系统自主性（Autonomy Level）的严谨界定。文献中通常将实验室自动化分为多个等级，从基础的机器辅助（Level 1）到能够在异常情况下自主调整假设并恢复的高级自主（Level 4）1。在论文的论述中，必须清晰地剥离“Human-in-the-Loop”（人类在环）的具体节点 21。例如，在ACE平台的早期报告中，作者坦诚地记录了由于专有软件的限制，人类研究员仍需手动转移FTIR光谱数据文件给AI处理，而在后续版本中实现了全流程接管 8。详细记录系统在“定义初始约束（如注入总体积、溶液浓度上限）”后的完全接管过程，是建立学术可信度的关键 8。

### **任务复杂度的阶梯式验证 (Progressive Validation)**

闭环系统论文不会仅仅给出一个最终的最优结果，而是通过设计一系列复杂度递增的实验任务来多维度验证AI的能力 14。

1. **基础指令执行与基础合成**：证明系统能够无误地解析常规化学协议并控制泵与电化学工作站完成基础的溶液配制与CV测试 14。  
2. **多参数空间探索与屏蔽筛选**：证明算法（如贝叶斯优化）能够在庞大的元素比例矩阵中，通过获取过电位或Tafel斜率，有效跳出局部最优解，描绘出合理的性能趋势 14。  
3. **多目标权衡与新知识生成**：这是论文的价值制高点。证明系统能够在不可调和的矛盾中（如HER高活性与抗反向电流高稳定性）找到帕累托前沿（Pareto Front），并基于累积的失效数据自我迭代，最终锁定人类未曾预料的最佳配比 7。

### **异常处理、容错机制与物理世界的鲁棒性**

与纯计算机算法论文不同，物理世界充满着不可控的摩擦（如蠕动泵的流速偏差、管路气泡、串口通信超时）。高水平的SDL论文会专门开辟章节，详述系统的诊断与自愈（Self-healing）能力 32。例如，论文会论述底层代码级监控（L1监控）如何处理硬件级的紧急停机，以及智能体级心跳监控（L2监控）如何防止多Agent陷入无限的推理死循环 7。系统如何通过自我反思（Reflexion）机制识别出电化学工作站反馈的异常噪音，并自主调用清洗泵（Flusher）进行管路冲洗后重试，是证明系统具备“科研级鲁棒性”的加分项 34。

## **Agent驱动的材料类型实验的物理执行与协同逻辑**

在微观执行层面，将大型语言模型（LLM）的抽象推理转化为电化学实验台上的具体物理动作，需要构建一个极其精密的双向数据总线。以当前最前沿的架构为参考，多智能体框架在电化学闭环实验中的运作逻辑呈现出高度的非线性和异步交互特征 7。

### **多智能体协作的内部工作流**

在缺乏DFT计算辅助的前提下，材料探索完全依赖于智能体对已有知识的重组和对实时数据的数学拟合 8。这一过程通常由四类核心Agent组成，它们在LangGraph等图路由框架下协同运作 7：

* **调度智能体 (Orchestrator)**：作为整个系统的“大脑”，调度智能体接收来自人类的宏观意图（如“在1000µL的总体积约束下，寻找HER抗反向电流的最优Fe-Co-Ni混合浓度”）。它不直接参与计算或控制，而是维护实验的全局状态机，判断当前处于文献检索阶段、参数设计阶段还是数据验证阶段，并将任务分发给相应的子Agent 7。  
* **设计智能体 (Designer)**：该智能体承担了传统的理论化学家的角色。它首先通过外挂的向量知识库（如OpenViking）检索关于Fe、Co、Ni在HER中的已有文献，划定一个合理的初始浓度探索边界 7。随后，它利用机器学习算法（如贝叶斯优化引擎）生成下一批次的高潜参数组合矩阵。  
* **执行智能体 (Executor)**：这是连接数字世界与物理世界的翻译官。执行智能体将设计智能体输出的相对比例或浓度，结合流体力学约束，精确计算出每台RS485蠕动泵需要分配的脉冲数或运行时间 7。随后，它通过RESTful API向底层的硬件控制层发送JSON格式的指令包，并实时监听硬件层返回的执行状态码（如0xFB响应）7。在液体混合完成后，执行智能体调用电化学工作站的动态链接库（如CHI的libec.dll），触发复杂的测试序列，如初始的循环伏安法（CV）活化、随后的线性扫描伏安法（LSV）测量活性，以及长时间的计时电流法（i-t）或特定波形来模拟反向电流冲击 7。  
* **诊断与分析智能体 (Diagnostics/Analyst)**：由于视觉大模型（VLM）在直接读取和理解复杂的电化学图谱（如多条交织的极化曲线）时往往存在严重的幻觉和数值提取不精确的问题 39，现代系统倾向于让诊断智能体直接处理底层硬件生成的原始数据数组（如CSV格式的电压-电流时间序列）41。该智能体利用内置的Python数据处理脚本（如SciPy、NumPy），精确提取出电流密度达到10 mA/cm²时的过电位、Tafel斜率，以及反向电流冲击后的性能衰减率 8。提取的KPI数据随后被回传给设计智能体，用于更新贝叶斯优化的代理模型 8。

### **硬件通信的降维与安全隔离**

在实验执行过程中，AI的概率生成特性与实验室仪器的精确控制要求存在本质冲突 32。前沿文献表明，成功的SDL必然包含一个坚固的硬件抽象层 21。类似于MicroHySeeker模块，硬件控制层被设计为一个“被动执行且高度自卫”的沙盒 7。

底层系统使用PySide6建立本地守护进程，独占串行端口（COM ports）资源 7。对于液路系统，硬件驱动严格遵循RS485的总线协议，通过特定的帧头（0xFA）和校验和机制，确保由AI下发的任何泵送命令在物理电路上是完整且未被篡改的 7。对于CHI电化学工作站，系统避免了模拟鼠标点击官方GUI的脆弱方案，而是直接将控制宏指令封装通过DLL下发，实现了测试序列的毫秒级时序控制 20。这种软硬件隔离确保了即使顶层的Qwen或Gemini模型发生逻辑崩溃或幻觉，底层的硬件引擎仍能依据硬编码的安全规则（如流速超限、通信断联超过设定阈值）触发紧急停止机制，从而保证了物理实验室的安全 7。

## **计算机算法角度的创新突破路径：无先验计算下的AI进化**

在明确放弃第一性原理计算（DFT）和复杂的生成式结构扩散模型（Diffusion Models）的框架下，系统必须完全依赖于对人类既有文献的深度挖掘、经验数据的统计优化以及大型语言模型本体逻辑的改造 7。从计算机算法的底层逻辑出发，要提升此类闭环实验室的创新能力，必须在知识检索架构、多目标寻优范式、模型架构微调以及自愈诊断算法四个维度进行深度的技术重构。

### **1\. 突破基础RAG架构：构建高阶化学领域知识检索系统**

基础的检索增强生成（RAG）技术——即简单地将文档切片、向量化，并通过余弦相似度将Top-K文档塞入Prompt中——在面对高度专业化、充满隐性变量和术语壁垒的材料科学时，往往会遭遇上下文截断和语义匹配失效的问题 9。为了在缺乏计算模拟支撑的情况下准确指导实验，必须引入高阶的检索架构。

#### **双源异构知识检索 (Dual-Source RAG / MDSK-RAG)**

材料研发的知识本质上分为两类：被广泛认可的理论规律（存在于海量PDF格式的学术期刊中）与本地实验室特有的实践约束（存在于CSV/JSON格式的本地仪器日志和失败记录中）41。前沿的算法架构（如MDSK-RAG）主张对向量数据库（如基于baai/bge-m3模型的OpenViking）进行严格的区域划分 7。在设计智能体查询HER稳定性的文献时，系统不仅会通过语义搜索提取顶级期刊中关于Co掺杂抑制金属溶解的理论机制，同时也会并行检索本地数据库中过去数十次失败的泵送记录和电化学极化曲线特征 41。将结构化表格数据通过模板转化为自然语言后，与非结构化的文献语料在嵌入空间中进行融合映射，从而使AI生成的实验参数既具备科学的合理性，又符合当前硬件的物理极限 7。

#### **多级混合检索与重排序交叉编码 (Hybrid Retrieval & Cross-Encoders)**

电催化领域存在大量的分子式、合金缩写与专有名词。仅仅依赖密集向量检索（Dense Retrieval）容易丢失对特定化学式的精确匹配 46。从算法层面，应实施多级混合检索策略：首先利用稀疏检索（如BM25算法）进行关键词和化学式的精确硬匹配，结合向量检索获取语义相关的段落 46。随后，引入专门在科学文献上训练过的交叉编码器（Cross-Encoder Re-ranking model），根据检索片段与当前优化目标的实际逻辑关联度重新打分 46。这种机制能够极大程度地过滤掉噪声数据，防止大模型在生成元素配比时产生学术幻觉 9。此外，结合图检索增强（GraphRAG），通过构建文献间的知识图谱（Knowledge Graph），算法可以实现多跳推理（Multi-hop reasoning），隐式地推导出未被直接文献报道的元素协同效应 37。

### **2\. 纯数据驱动的寻优机制：多目标贝叶斯优化与“Learning Advance”范式**

由于排除了材料计算，系统无法预先通过量子力学计算得知某一种配比的理论过电位。因此，算法的核心落在了如何最经济地利用实际实验数据探索未知的化学空间 6。

#### **约束空间下的多目标贝叶斯优化 (MOBO)**

HER催化剂在实际应用中，高活性与抗反向电流稳定性往往是一对矛盾体 4。单纯的梯度下降或网格搜索在面对这种高维且昂贵的黑盒函数时效率极低 5。算法层面应深度集成多目标贝叶斯优化（Multi-Objective Bayesian Optimization, MOBO）框架 5。 在每个实验闭环中，诊断智能体提取的过电位（活性指标）和电流衰减率（稳定性指标）被送入高斯过程（Gaussian Process, GP）代理模型 8。代理模型不仅预测未知配比的性能，更关键的是输出预测的不确定性 31。随后，通过设计复杂的采集函数（如期望超体积改进，Expected Hypervolume Improvement, EHVI），算法能够在“利用（Exploitation，在已知好结果附近微调）”和“探索（Exploration，测试完全未知的元素配比）”之间做出数学上的最优权衡，最终逼近描绘出活性与稳定性的帕累托最优前沿（Pareto Front）3。

#### **“Learning Advance”：基于LLM的文献驱动假设生成**

贝叶斯优化虽然强大，但其本质是统计拟合，当面临材料体系的非线性突变（如相变、溶解限）时极易陷入局部最优的平台期 52。为了突破这一瓶颈，前沿算法引入了“Learning Advance”范式 52。当MOBO算法检测到连续几个迭代周期性能不再提升时，算法主动中止统计寻优，将累积的经验数据特征（如特定Co浓度区间的电流阶跃现象）转换为结构化提示词输入给大语言模型 52。 LLM作为一个拥有庞大学术语料库的“超级专家”，能够对这些纯数字的关联矩阵进行物理意义上的反思，并用自然语言输出一个新的科学假设（例如：“数据表明，当Ni含量超过X%时，反向电流引发的表面氧化层可能阻碍了电子转移，建议引入微量Fe来稳定晶格”）52。随后，这一由AI生成的物理假设被转化为新的搜索空间约束条件，重新初始化贝叶斯引擎 52。这种将底层统计拟合与顶层语义推理深度结合的算法逻辑，是系统从“盲目优化工具”向“科学研究伙伴”跨越的核心路径 7。

### **3\. 模型架构底层的微调与改造**

依赖通用的API模型（如原生的Qwen或Gemini）进行长周期的科学实验，会面临领域专业度不足和长上下文推理遗忘的挑战 7。从计算机算法工程师的角度，必须对大模型的底层架构进行适配与微调。

#### **参数高效微调 (PEFT) 与适配器 (Adapters) 注入**

由于全面预训练成本高昂，采用参数高效微调（如LoRA）是首选策略 56。通过收集电化学领域的专有数据集——包括大量的实验操作日志、电化学参数解析规则以及仪器的异常报错代码——对模型注入领域适配器（Domain Adapters）56。这种微调并不旨在让模型记住所有的化学方程式，而是让其掌握“电化学实验的直觉”54。例如，经过微调的模型在解析诊断Agent传来的极化曲线斜率变化时，能够比通用模型更稳定地判断出这是析氢副反应还是电极表面的钝化现象，从而提供更具确定性的决策输出，这对于保障物理硬件实验的安全性至关重要 54。

#### **混合专家架构 (Mixture of Experts, MoE) 的部署**

一个闭环实验系统包含多种截然不同的任务：生成控制泵的Python/JSON代码、理解多维化学空间、以及解析复杂的异常日志 7。使用单一的密集模型处理所有任务效率低下且容易发生任务间的知识干扰。引入混合专家架构（MoE）可以将底层神经网络划分为多个专注于特定领域的子网络（Experts）58。 在推理时，门控路由机制（Routing Mechanism）会根据当前的Prompt性质，将生成硬件指令的请求路由给“代码专家”，将分析HER机制的请求路由给“化学推理专家” 58。在资源受限的本地部署环境（如边缘计算节点）中，MoE架构能够在保持极高专业推理能力的同时，大幅降低系统的推理延迟和显存占用，从而实现对底层硬件事件的毫秒级响应 58。

### **4\. 诊断与自愈算法机制的深度构建**

自主实验室在物理世界的执行中极易遭遇不可抗力的硬件故障。算法层面必须构建超越简单的try-catch逻辑的认知型诊断与自我反思框架 7。

#### **L2层级的逻辑心跳与状态重置**

在类似AutoHySeeker的AI决策层（L2层），系统算法需引入严格的图状态机监控 7。针对多Agent协作容易引发的“幻觉死循环”（例如两个Agent相互推诿任务或反复生成无法解析的浓度参数），算法需设定逻辑心跳（Logical Heartbeat）机制 7。一旦监测到多轮对话未推进物理实验状态，仲裁算法将强制中断当前图路由，调用清空上下文记忆的“重置接口”，并基于备用安全配置重新发起任务流 32。

#### **Reflexion（反思）与链式思考 (CoT) 在纠错中的应用**

当硬件层（MicroHySeeker）反馈了一个非致命的执行异常（如CV曲线噪声过大、反向电流测试未能收敛）时，系统需利用基于Reflexion（自我反思）框架的诊断算法进行干预 7。诊断Agent会将失败的电化学结果与历史成功数据进行对比，结合CoT（链式思考）生成多步的假设归因 23。 例如，算法推理出“当前流速配比导致了反应池内气泡积聚，干扰了工作电极的欧姆降补偿（iR drop compensation）”8。随后，诊断Agent不仅会修正下一个批次的泵送策略，更会生成一个“自愈动作”（如向硬件层发送清洗流路和排气的特定RS485指令），在恢复系统物理状态后，自主规划复测流程 7。这种闭环内的数据-逻辑双重校验与自愈能力的算法实现，标志着实验室从简单的自动化控制跨越到了真正的Level 4高度自主化阶段 1。

## **结语**

在现代材料科学的研究中，特别是在摒弃了传统材料计算和生成式微观结构模型的前提下，自主驱动实验室代表了纯经验与数据驱动发现的最高形态。从基础的闭环控制（Phase 1）走向真正的科学创新伙伴（Phase 2），其核心已不在于烧杯中的化学反应，而在于驱动这些反应的庞大且精密的算法工程。

通过在底层建立高度抽象且安全隔离的硬件通信总线，在中层利用多智能体编排网络进行角色的细分与协作，并在顶层通过双源高阶RAG检索、多目标贝叶斯优化、模型局部微调（PEFT/MoE）以及反思自愈框架进行认知强化，系统得以在庞杂的多元素组合空间中，以超越人类直觉的维度刻画出电催化活性与抗反向电流稳定性的帕累托前沿。这种基于计算机算法底层解构与重组的研究范式，不仅正在重塑顶级学术期刊的叙事逻辑，更将引领电催化等新能源材料发现走向一个真正智能、高效且充满未知惊喜的新纪元。

#### **引用的著作**

1. Autonomous 'self-driving' laboratories: a review of technology and policy implications \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12368842/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12368842/)  
2. Self-Driving Laboratories for Chemistry and Materials Science | Chemical Reviews, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acs.chemrev.4c00055](https://pubs.acs.org/doi/10.1021/acs.chemrev.4c00055)  
3. Self-Driving Laboratory Optimizes the Lower Critical Solution Temperature of Thermoresponsive Polymers \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2509.05351v1](https://arxiv.org/html/2509.05351v1)  
4. Smart design of Rh-based hydrogen evolution electrocatalysts: integrating DFT, machine learning, and structural optimization for sustainable hydrogen energy \- OAE Publishing, 访问时间为 四月 2, 2026， [https://www.oaepublish.com/articles/energymater.2025.148](https://www.oaepublish.com/articles/energymater.2025.148)  
5. Navigating the unknown with AI: multiobjective Bayesian optimization of non-noble acidic OER catalysts \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/377050370\_Navigating\_the\_unknown\_with\_AI\_multiobjective\_Bayesian\_optimization\_of\_non-noble\_acidic\_OER\_catalysts](https://www.researchgate.net/publication/377050370_Navigating_the_unknown_with_AI_multiobjective_Bayesian_optimization_of_non-noble_acidic_OER_catalysts)  
6. Accelerating Multimetallic Catalyst Discovery with Robotics and Agentic AI \- ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-13n3f](https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-13n3f)  
7. PROJECT\_OVERVIEW.md  
8. Autonomous Flow Electrochemistry for Accelerated Catalyst Discovery \- Pacific Northwest National Laboratory, 访问时间为 四月 2, 2026， [https://www.pnnl.gov/main/publications/external/technical\_reports/PNNL-38463.pdf](https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-38463.pdf)  
9. Nanostructured Material Design via a Retrieval-Augmented Generation (RAG) Approach: Bridging Laboratory Practice and Scientific Literature | Journal of Chemical Information and Modeling \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acs.jcim.5c01897](https://pubs.acs.org/doi/10.1021/acs.jcim.5c01897)  
10. Toward self-driving laboratory 2.0 for chemistry and materials discovery \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/401539971\_Toward\_Self-Driving\_Laboratory\_20\_for\_Chemistry\_and\_Materials\_Discovery](https://www.researchgate.net/publication/401539971_Toward_Self-Driving_Laboratory_20_for_Chemistry_and_Materials_Discovery)  
11. AI, agentic models and lab automation for scientific discovery — the beginning of scAInce, 访问时间为 四月 2, 2026， [https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1649155/full](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1649155/full)  
12. From large language models to AI agents in energy materials research: enabling discovery, design, and automation \- OAE Publishing Inc., 访问时间为 四月 2, 2026， [https://www.oaepublish.com/articles/aiagent.2025.03](https://www.oaepublish.com/articles/aiagent.2025.03)  
13. LLM-Based Scientific Agents \- Emergent Mind, 访问时间为 四月 2, 2026， [https://www.emergentmind.com/topics/llm-based-scientific-agents](https://www.emergentmind.com/topics/llm-based-scientific-agents)  
14. A Multiagent-Driven Robotic AI Chemist Enabling Autonomous Chemical Research On Demand | Journal of the American Chemical Society, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/abs/10.1021/jacs.4c17738](https://pubs.acs.org/doi/abs/10.1021/jacs.4c17738)  
15. Coscientist: AI in Chemical Research | PDF \- Scribd, 访问时间为 四月 2, 2026， [https://www.scribd.com/document/694391486/s41586-023-06792](https://www.scribd.com/document/694391486/s41586-023-06792)  
16. Autonomous chemical research with large language models \- PubMed, 访问时间为 四月 2, 2026， [https://pubmed.ncbi.nlm.nih.gov/38123806/](https://pubmed.ncbi.nlm.nih.gov/38123806/)  
17. Multi-objective Bayesian optimization: a case study in material extrusion \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/387762130\_Multi-objective\_Bayesian\_optimization\_a\_case\_study\_in\_material\_extrusion](https://www.researchgate.net/publication/387762130_Multi-objective_Bayesian_optimization_a_case_study_in_material_extrusion)  
18. Autonomous Flow Electrochemistry for Accelerated Catalyst Discovery \- OSTI, 访问时间为 四月 2, 2026， [https://www.osti.gov/biblio/2998432](https://www.osti.gov/biblio/2998432)  
19. FastCat: Autonomous Discovery of Multielement Layered Double Hydroxide Alloy Catalysts for Alkaline Oxygen Evolution Reaction \- ResearchGate, 访问时间为 四月 2, 2026， [https://www.researchgate.net/publication/398434848\_FastCat\_Autonomous\_Discovery\_of\_Multielement\_Layered\_Double\_Hydroxide\_Alloy\_Catalysts\_for\_Alkaline\_Oxygen\_Evolution\_Reaction](https://www.researchgate.net/publication/398434848_FastCat_Autonomous_Discovery_of_Multielement_Layered_Double_Hydroxide_Alloy_Catalysts_for_Alkaline_Oxygen_Evolution_Reaction)  
20. Hard Potato: A Python Library to Control Commercial Potentiostats and to Automate Electrochemical Experiments | Analytical Chemistry \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acs.analchem.2c04862](https://pubs.acs.org/doi/10.1021/acs.analchem.2c04862)  
21. The future of self-driving laboratories: from human in the loop interactive AI to gamification, 访问时间为 四月 2, 2026， [https://pubs.rsc.org/en/content/articlehtml/2024/dd/d4dd00040d](https://pubs.rsc.org/en/content/articlehtml/2024/dd/d4dd00040d)  
22. How a Closed-Loop Autonomous Materials Discovery System Is Transforming AI-Driven Laboratory Automation | Lab Manager, 访问时间为 四月 2, 2026， [https://www.labmanager.com/closed-loop-autonomous-materials-discovery-system-advances-lab-innovation-34949](https://www.labmanager.com/closed-loop-autonomous-materials-discovery-system-advances-lab-innovation-34949)  
23. Autonomous Agents for Scientific Discovery: Orchestrating Scientists, Language, Code, and Physics \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2510.09901v1](https://arxiv.org/html/2510.09901v1)  
24. Autonomous Discovery of Multielement LDH Alloy Catalysts for Alkaline OER \- ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/doi/10.26434/chemrxiv-2025-w8bkg](https://chemrxiv.org/doi/10.26434/chemrxiv-2025-w8bkg)  
25. Engineering principles for self-driving laboratories \- NSF PAR, 访问时间为 四月 2, 2026， [https://par.nsf.gov/servlets/purl/10599254](https://par.nsf.gov/servlets/purl/10599254)  
26. Self-Driving Laboratories for Chemistry and Materials Science \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC11363023/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11363023/)  
27. Self-Driving Laboratories for Development of New Functional Materials and Optimizing Known Reactions \- MDPI, 访问时间为 四月 2, 2026， [https://www.mdpi.com/2079-4991/11/3/619](https://www.mdpi.com/2079-4991/11/3/619)  
28. Self-Driving Laboratories for Chemistry and Materials Science \- ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2024-rj946-v2](https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2024-rj946-v2)  
29. FastCat \- Autonomous Discovery of Multielement LDH Alloy Catalysts for Alkaline OER \- ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/6862ec211a8f9bdab5d6be25/original/fast-cat-autonomous-discovery-of-multielement-ldh-alloy-catalysts-for-alkaline-oer.pdf](https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/6862ec211a8f9bdab5d6be25/original/fast-cat-autonomous-discovery-of-multielement-ldh-alloy-catalysts-for-alkaline-oer.pdf)  
30. CH Instruments CHI660E Series Datasheet | ArtisanTG, 访问时间为 四月 2, 2026， [https://www.artisantg.com/info/CH\_Instruments\_CHI660E\_Datasheet\_2023414112124.pdf](https://www.artisantg.com/info/CH_Instruments_CHI660E_Datasheet_2023414112124.pdf)  
31. \[2006.06141\] On-the-fly Closed-loop Autonomous Materials Discovery via Bayesian Active Learning \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/abs/2006.06141](https://arxiv.org/abs/2006.06141)  
32. 10 Multi-Agent Coordination Strategies to Prevent System Failures \- Galileo AI, 访问时间为 四月 2, 2026， [https://galileo.ai/blog/multi-agent-coordination-strategies](https://galileo.ai/blog/multi-agent-coordination-strategies)  
33. The Orchestration of Multi-Agent Systems: Architectures, Protocols, and Enterprise Adoption, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2601.13671v1](https://arxiv.org/html/2601.13671v1)  
34. Electrochemical Workstation Automation Using Scripts，base on Macrocommand CHI electrochemical workstation. Use the same principle for other brands of electrochemical workstations \- GitHub, 访问时间为 四月 2, 2026， [https://github.com/chuanyaoliu/Electrochemical-Workstation-Automation-Using-Scripts](https://github.com/chuanyaoliu/Electrochemical-Workstation-Automation-Using-Scripts)  
35. From AI for Science to Agentic Science: A Survey on Autonomous Scientific Discovery \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2508.14111v2](https://arxiv.org/html/2508.14111v2)  
36. How AI Agents Are Transforming Solid Electrolyte Discovery \- Asia Research News |, 访问时间为 四月 2, 2026， [https://www.asiaresearchnews.com/content/how-ai-agents-are-transforming-solid-electrolyte-discovery](https://www.asiaresearchnews.com/content/how-ai-agents-are-transforming-solid-electrolyte-discovery)  
37. Agentic material science \- OAE Publishing Inc., 访问时间为 四月 2, 2026， [https://www.oaepublish.com/articles/jmi.2025.87](https://www.oaepublish.com/articles/jmi.2025.87)  
38. Full article: Perspective on utilizing foundation models for laboratory automation in materials research \- Taylor & Francis, 访问时间为 四月 2, 2026， [https://www.tandfonline.com/doi/full/10.1080/27660400.2025.2582379](https://www.tandfonline.com/doi/full/10.1080/27660400.2025.2582379)  
39. Can Multimodal LLMs See Materials Clearly? A Multimodal ..., 访问时间为 四月 2, 2026， [https://aclanthology.org/2025.findings-emnlp.235/](https://aclanthology.org/2025.findings-emnlp.235/)  
40. \[2509.09307\] Can Multimodal LLMs See Materials Clearly? A Multimodal Benchmark on Materials Characterization \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/abs/2509.09307](https://arxiv.org/abs/2509.09307)  
41. Materials Dual-Source Knowledge Retrieval-Augmented Generation for Local Large Language Models in Photocatalysts \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acs.jcim.5c01941](https://pubs.acs.org/doi/10.1021/acs.jcim.5c01941)  
42. Enhancing diagnostic capability with multi-agents conversational large language models, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC11906805/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11906805/)  
43. BioTrouble: A Multi-Agent Workflow for Troubleshooting Molecular Biology Techniques, 访问时间为 四月 2, 2026， [https://www.biorxiv.org/content/10.64898/2025.12.30.697016v1.full-text](https://www.biorxiv.org/content/10.64898/2025.12.30.697016v1.full-text)  
44. nodesign/electripy: Hardware Abstraction Layer Library for Python \- GitHub, 访问时间为 四月 2, 2026， [https://github.com/nodesign/electripy](https://github.com/nodesign/electripy)  
45. Standard Operation Procedure: CHI 660 Electrochemistry Station, 访问时间为 四月 2, 2026， [https://tanglab.hku.hk/wp-content/uploads/2022/01/Electrochemistry-CHI660e-SOP-2021.pdf](https://tanglab.hku.hk/wp-content/uploads/2022/01/Electrochemistry-CHI660e-SOP-2021.pdf)  
46. Beyond Basic RAG: Exploring Advanced Retrieval-Augmented Generation (RAG) in 2025, 访问时间为 四月 2, 2026， [https://medium.com/@bravekjh/beyond-basic-rag-exploring-advanced-retrieval-augmented-generation-rag-in-2025-08dbb3df5ca3](https://medium.com/@bravekjh/beyond-basic-rag-exploring-advanced-retrieval-augmented-generation-rag-in-2025-08dbb3df5ca3)  
47. Large language models in materials science: assessing RAG evaluation frameworks through graphene synthesis \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12947896/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12947896/)  
48. Materials Dual-Source Knowledge Retrieval-Augmented Generation for Local Large Language Models in Photocatalysts | ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/doi/10.26434/chemrxiv-2025-bjq11](https://chemrxiv.org/doi/10.26434/chemrxiv-2025-bjq11)  
49. Changes to the RAG in 2025 – Better LLM Integration \- Dataforest, 访问时间为 四月 2, 2026， [https://dataforest.ai/blog/rag-in-2025-smarter-retrieval-and-real-time-responses](https://dataforest.ai/blog/rag-in-2025-smarter-retrieval-and-real-time-responses)  
50. NeurIPS Poster Can Knowledge-Graph-based Retrieval Augmented Generation Really Retrieve What You Need?, 访问时间为 四月 2, 2026， [https://neurips.cc/virtual/2025/poster/115922](https://neurips.cc/virtual/2025/poster/115922)  
51. AI-Accelerated Discovery of Electrocatalyst Materials \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acsmaterialsau.5c00135](https://pubs.acs.org/doi/10.1021/acsmaterialsau.5c00135)  
52. Learning Advance: Robotics-LLM Guided Hypotheses ... \- ChemRxiv, 访问时间为 四月 2, 2026， [https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-n1b4l](https://chemrxiv.org/doi/pdf/10.26434/chemrxiv-2025-n1b4l)  
53. Embracing Foundation Models for Advancing Scientific Discovery \- PMC, 访问时间为 四月 2, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC11923747/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11923747/)  
54. From prompt engineering to fine‑tuning: Transforming document validation \- IBM Developer, 访问时间为 四月 2, 2026， [https://developer.ibm.com/articles/fine-tuned-slm-llm-doc-validation/](https://developer.ibm.com/articles/fine-tuned-slm-llm-doc-validation/)  
55. Role of Large Language Models and Retrieval-Augmented Generation for Accelerating Crystalline Material Discovery: A Systematic Review \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2508.06691v1](https://arxiv.org/html/2508.06691v1)  
56. Enhancing Large Language Models for Specialized Domains: A Two-Stage Framework with Parameter-Sensitive LoRA Fine-Tuning and Chain-of-Thought RAG \- MDPI, 访问时间为 四月 2, 2026， [https://www.mdpi.com/2079-9292/14/10/1961](https://www.mdpi.com/2079-9292/14/10/1961)  
57. ICLR Poster Pre-training of Foundation Adapters for LLM Fine-tuning, 访问时间为 四月 2, 2026， [https://iclr.cc/virtual/2025/poster/31361](https://iclr.cc/virtual/2025/poster/31361)  
58. General-Purpose Models for the Chemical Sciences: LLMs and Beyond \- ACS Publications, 访问时间为 四月 2, 2026， [https://pubs.acs.org/doi/10.1021/acs.chemrev.5c00583](https://pubs.acs.org/doi/10.1021/acs.chemrev.5c00583)  
59. A Survey of AI for Materials Science: Foundation Models, LLM Agents, Datasets, and Tools, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2506.20743v1](https://arxiv.org/html/2506.20743v1)  
60. \[2407.06204\] A Survey on Mixture of Experts in Large Language Models \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/abs/2407.06204](https://arxiv.org/abs/2407.06204)  
61. Mimosa Framework: Toward Evolving Multi-Agent Systems for Scientific Research \- arXiv, 访问时间为 四月 2, 2026， [https://arxiv.org/html/2603.28986v1](https://arxiv.org/html/2603.28986v1)