Section Positioning: This section (“2. Experimental”) details the construction, operational protocols, electrode fabrication, and modeling framework of a 4-cell bipolar plate alkaline water electrolyzer (AWE) system, with a focus on characterizing the reverse current phenomenon during shutdown.

Paragraph Index:
P001: Introduces subsection 2.1, outlining the general setup of the alkaline water electrolyzer system.  
P002: Describes the overall AWE system architecture, including electrolyte circulation loops, gas separation, temperature control, and instrumentation for current and potential measurements.  
P003: Presents Figure 1, a schematic of the 4-cell bipolar plate AWE system.  
P004: Details measurement tools (clamp meters, RHE, potentiostat, data loggers) and their roles in monitoring ionic current, potentials, and system parameters.  
P005: Introduces subsection 2.2, focusing on the physical design of the bipolar plate stack and manifold assembly.  
P006: Explains the zero-gap cell configuration, separator type (Zirfon™ PERL), chamber volumes, electrical series connection via bipolar plates, and current collector design.  
P007: Provides geometric and hydraulic specifications of the PTFE manifold system, emphasizing symmetry and uniform ionic resistance across branches.  
P008: Introduces subsection 2.3, which explains the physical origin of the reverse current phenomenon and its circuit representation.  
P009: Describes charge accumulation on electrodes during electrolysis due to electrochemical reactions.  
P010: Explains how bipolar plates behave as charged batteries post-shutdown, driving reverse ionic current through manifolds and separators, and introduces the equivalent electrical circuit.  
P011: Simplifies the equivalent circuit by exploiting symmetry, reducing it to three parallel branches representing each bipolar plate’s discharge path.  
P012: Introduces subsection 2.4, specifying electrolysis and shutdown experimental conditions.  
P013: Lists the four distinct steady-state electrolysis operating conditions tested.  
P014: Enumerates specific combinations of current density, duration, and temperature for each electrolysis test case.  
P015: Shows Figure 2, comparing the physical AWE stack/manifold layout (a) with its post-shutdown equivalent circuit (b).  
P016: Describes the shutdown protocol: power disconnection, circuit breaker opening, and natural cooling of electrolyte.  
P017: Introduces additional shutdown-phase variables related to electrolyte circulation and nitrogen bubbling.  
P018: Lists three distinct shutdown conditions involving pump operation and nitrogen sparging in gas separators.  
P019: Introduces subsection 2.5, concerning electrode fabrication methods and materials.  
P020: Details the composition, deposition method, and naming conventions for two anode (OER) catalysts (AN-1: NiCoOₓ; AN-2: LiNiOₓ/Ir-Co-Ni oxides) and one cathode (HER) catalyst (CA-1: Ru-Ln oxides on Ni mesh).  
P021: Introduces subsection 2.6, describing the computational modeling approach for reverse current.  
P022: Frames reverse current as a battery discharge process and references the circuit model (Fig. S5) and experimental E–Q_rev data.  
P023: Links the emf of each bipolar plate to measured electrode potentials and introduces continuity equations for ionic current.  
P024: Presents the governing equation for electronic potential (φ_S) in solid conductors.  
P025: Presents the governing equation for ionic potential (φ_E) in electrolyte, labeled as Equation (1).  
P026: Defines symbols in the potential equations, including conductivities (σ_S, σ_E) and material domains.  
P027: Gives the reaction current expression (Equation 2) based on potential difference, internal resistance, and emf.  
P028: Defines i_reac as the redox-driven reaction current.  
P029: Clarifies that R_int is the cell’s internal resistance and E is the experimentally measured electrode potential difference during shutdown.  
P030: Introduces the time-dependent relationship between charge and current.  
P031: States the charge evolution equation (Equation 3).  
P032: Defines Q as the cumulative reverse charge derived from measured shutdown current.  
P033: Introduces boundary condition specifications for the model.  
P034: States continuity of internal boundaries and zero source terms for current flux.  
P035: Provides the Neumann boundary condition for electronic current (Equation 4).  
P036: Provides the Neumann boundary condition for ionic current (Equation 5).  
P037: Sets the cathode-side end plate as electrical ground (φ_S = 0).  
P038: Summarizes the modeled components and notes geometric simplifications for manifolds; mentions COMSOL 5.6 as the solver.

Key Entities: alkaline water electrolyzer (AWE), bipolar plate (BP), reverse current, KOH electrolyte, Zirfon™ PERL separator, NiCoOₓ, LiNiOₓ, Ru-Ln oxides, equivalent electrical circuit, COMSOL model
