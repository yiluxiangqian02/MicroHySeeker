# Section: 2. Experimental

- **S03-P001** (PRAW-000023): # 2.1. Construction of the alkaline water electrolyzer system
- **S03-P002** (PRAW-000024): Fig. 1 shows a schematic diagram of the AWE system used in this study. A 4-cell stack was connected to an external plumbing system which enabled the circulation of the electrolyte and the evacuation o
- **S03-P003** (PRAW-000025): ![](figures/FIG001/image_001.jpg)
Fig. 1. Schematic diagram of the utilized 4-cell stack bipolar plate alkaline water electrolysis system.
- **S03-P004** (PRAW-000026): inlet and the outlet of the manifold tubes. The DC milliampere clamp meter can measure the ionic current flowing through the KOH electrolyte inside the PTFE tubes. A reversible hydrogen electrode (RHE
- **S03-P005** (PRAW-000027): # 2.2. The bipolar plate stack and the associated manifold assembly
- **S03-P006** (PRAW-000028): Fig. S1 shows a schematic diagram of the first two cells of the utilized bipolar plate AWE stack. The cells were grouped based on the zero-gap configuration, in which the anode and cathode of each cel
- **S03-P007** (PRAW-000029): Fig. S2 shows a detailed schematic diagram of the 4-cell AWE stack and the connected manifold assembly. The manifold tubes are made of PTFE with an inner diameter of $4\mathrm{mm}$ . The manifold syst
- **S03-P008** (PRAW-000030): # 2.3. Basics of the reverse current phenomenon and the equivalent electrical circuit
- **S03-P009** (PRAW-000031): During the electrolysis time, positive charges were accumulated on the surface of the anode electrodes, and negative charges were accumulated on the surface of the cathode electrodes due to the water 
- **S03-P010** (PRAW-000032): cathode side to the anode side. Immediately after shutting down the electrolyzer, the BP acts as a charged battery having a certain emf. The emf of each BP is equal to the potential difference between
- **S03-P011** (PRAW-000033): Since the four circuit branches connected across each emf are identical, the equivalent circuit can be simplified to the equivalent circuit shown in Fig. S5. The simplified circuit contains three bran
- **S03-P012** (PRAW-000034): # 2.4. Electrolysis and shutdown conditions
- **S03-P013** (PRAW-000035): The following electrolysis conditions were applied separately during the operating mode:
- **S03-P014** (PRAW-000036): 1 DC current density of $0.4\mathrm{Acm}^{-2}$ for $1.0\mathrm{h}$ at $30^{\circ}\mathrm{C}$ .
2 DC current density of $0.6\mathrm{Acm}^{-2}$ for $1.0\mathrm{h}$ at $30^{\circ}\mathrm{C}$ .
3 DC curre
- **S03-P015** (PRAW-000037): ![](figures/FIG002/image_002.jpg)
Fig. 2. a) A schematic diagram of the 4-cell stack alkaline water electrolyzer and the attached manifold assembly. B) The corresponding equivalent electrical circuit 
- **S03-P016** (PRAW-000038): After $1.0\mathrm{h}$ of steady-state operation, the power supply was turned off and the circuit breaker was physically opened to prevent any external influence on the electrodes' potentials during th
- **S03-P017** (PRAW-000039): In addition, effects of the electrolyte circulation, with and without the nitrogen bubbling in the electrolyte, on the reverse current and the electrodes' potentials during the shutdown time were stud
- **S03-P018** (PRAW-000040): 1 With KOH electrolyte circulation (pumps ON).
2 Without KOH electrolyte circulation (pumps OFF).
3 Feeding of vigorous nitrogen gas bubbles to the KOH electrolyte inside the gas separators. In this c
- **S03-P019** (PRAW-000041): # 2.5. Fabrication of the electrodes
- **S03-P020** (PRAW-000042): In this study, two different OER electrocatalysts were individually utilized with the same HER electrocatalyst. The first OER electrocatalyst is $\mathrm{NiCoO_x}$ electrocatalyst that was deposited o
- **S03-P021** (PRAW-000043): # 2.6. Modeling approach
- **S03-P022** (PRAW-000044): In this model, the reverse current phenomenon is considered as a battery discharge. The reactions are expressed based on the electrical circuit model shown in Fig. S5. The simulator was fed with the n
- **S03-P023** (PRAW-000045): charge flowing in the circuit branch of that BP. The $E - Q_{\mathrm{rev}}$ plot, shown in Fig. S6, was obtained based on the results of the actual experiment of the present 4-cell AWE system. For eac
- **S03-P024** (PRAW-000046): $$
\nabla \quad (- \sigma_ {S} \cdot \nabla \varnothing_ {S}) = 0
$$
- **S03-P025** (PRAW-000047): $$
\nabla (- \sigma_ {\mathrm {E}} \cdot \nabla \varnothing_ {\mathrm {E}}) = 0 \tag {1}
$$
- **S03-P026** (PRAW-000048): where, $\varphi_{E}$ is the potential of any point inside the KOH electrolyte through the cells and the manifolds. In addition, $\varphi_{S}$ is the potential of metallic parts including the associate
- **S03-P027** (PRAW-000049): $$
i _ {\text {r e a c}} = \frac {1}{R _ {\text {i n t}}} \left(\varnothing_ {\mathrm {S}} - \varnothing_ {\mathrm {E}} - E\right) \tag {2}
$$
- **S03-P028** (PRAW-000050): where, $i_{\text{reac}}$ is the reaction current that resulted from the redox reactions of the electrodes.
- **S03-P029** (PRAW-000051): $R_{int}$ is the internal resistance of each cell. $E$ is the potential of the associated anode and cathode that experimentally measured during the shutdown time of the electrolyzer.
- **S03-P030** (PRAW-000052): For the time development, the relationship between the flowing charges and the reaction current becomes:
- **S03-P031** (PRAW-000053): $$
\frac {\partial Q}{\partial t} = i _ {\text {r e a c}} \tag {3}
$$
- **S03-P032** (PRAW-000054): where, $Q$ is the cumulative reverse charge associated with the experimentally measured reverse current during the shutdown time of the electrolyzer.
- **S03-P033** (PRAW-000055): The boundary conditions are set as follows:
- **S03-P034** (PRAW-000056): - All internal boundaries are continuous. Inside the definition area of $\varphi_{\mathrm{S}}$ and $\varphi_{\mathrm{E}}$ , the source term of ionic current flux is always equal to zero. Thus, the fol
- **S03-P035** (PRAW-000057): $$
- \boldsymbol {n} \cdot \left(- \sigma_ {\mathrm {S}} \nabla \varphi_ {\mathrm {S}}\right) = 0 \tag {4}
$$
- **S03-P036** (PRAW-000058): $$
- \boldsymbol {n} \cdot \left(- \sigma_ {\mathrm {E}} \nabla \varphi_ {\mathrm {E}}\right) = 0 \tag {5}
$$
- **S03-P037** (PRAW-000059): - The end plate on the cathode side of the cells stack is set to ground, $\varphi_{\mathrm{S}} = 0$
- **S03-P038** (PRAW-000060): The reverse current model of the 4-cell stack considers the anode compartments, anode manifolds, the cathode compartments, cathode manifolds, bipolar plates, end plates, and the separators. In this mo
