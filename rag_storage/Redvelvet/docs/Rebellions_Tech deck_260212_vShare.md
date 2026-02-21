### [파일명: Rebellions_Tech deck_260212_vShare.pdf]
© 2026 Rebellions Inc. Confidential and Proprietary
1
Technology
SF4X (Samsung)
Structure
4 ASIC + 4 HBM3E + 4 ISC*
Single Die and Interposer Size
(Approximate) 
320 sqmm / 2200 sqmm
Package/Interposer Technology
ICube-S (CoWoS-S type)
HBM Bandwith and Capacity 
4x HBM3E (12H)
4.8 TB/s, 144 GB
Peak Dense Compute 
FP8 : 2 PFLOPS
FP16 : 1 PFLOPS
On-chip SRAM
512 MB
PCIe Interface
2x PCIe Gen5 16 x
256 GB/s
UCIe Interface
4 TB/s UCIe-A
3x 1TB/s channel per chiplet
Chip TDP
600 Watt
*ISC = Integrated Silicon Capacitor
© 2026 Rebellions Inc. Confidential and Proprietary
REBELTM-Quad: the world’s first UCIe-A based, peta-scale chiplet AI accelerator


Roadmap
PCIe
GDDR6
Neural 
Core
Neural
Neural
Neural 
Core
Core
Core
SRAM
SRAM
SRAM
SRAM
Tile
Tile
Tile
Tile
Neural
Neural
Neural
Neural 
Core
Core
Core
Core
eLSU
eLSU
eLSU
eLSU
4MB SRAM Buffer
iLSU
iLSU
iLSU
iLSU
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
PE
HPE
HPE
HPE
HPE
HPE
HPE
HPE
HPE
1st silicon proven core architecture
128 TFLOPS (FP16) 
GDDR6 16GB (256GB/s) 
PCIe Gen5 x16
2,048 TFLOPS (FP8) 
HBM3E 144GB (4.8TB/s) 
PCIe Gen5 x32
© 2026 Rebellions Inc. Confidential and Proprietary
Rebellions’ roadmap demonstrates continuous architectural evolution,              
scaling from single neural core to multi-chiplet accelerators (1/2)
2
2022
   2024
2026
IONTM
(TSMC 7nm)
Extremely low latency      
for high-frequency trading
ATOMTM
(Samsung 5nm)
Power efficient 
GDDR6-based ML SoC
REBELTM-Quad
(Samsung 4nm)
UCIe-Advanced based chiplet
for enterprise-grade AI systems


Roadmap
REBELTM-IO
(IO Die: TSMC 7nm)
Ethernet based chiplet
for multi-rack AI solution
REBELTM-CPU                
(CPU Die: Samsung 2nm)
CPU+NPU chiplet 
for accelerated compute node
REBELTM-Next
(TBD)
AI inference for MoE at scale; 
designed for heterogenous compute
REBEL + 2x IO Die
6.4 Tbps ETH
REBEL + 2x CPU Die
64x Arm Neoverse V3 / LPDDR5x
32 PFLOPS (FP4) / HBM4E 288GB (32TB/s)
HBF 4TB (4.8TB/s) / 57.6 Tbps Optical C2C
2Q 2027
3Q 2027
2028
Rebellions’ roadmap demonstrates continuous architectural evolution,              
scaling from single neural core to multi-chiplet accelerators (2/2)
3
© 2026 Rebellions Inc. Confidential and Proprietary
IO Die
Card-to-Card & 
Host Interface
ARM Neoverse 
V3
ARM Neoverse 
V3
CPU Die


4
© 2026 Rebellions Inc. Confidential and Proprietary
Design Philosophy
Multi-chiplet dataflow architecture with high-degree flexibility and scalability 
Neural Core
Neural Core Cluster
Chiplet
Chiplet-based Scale-up
Full-chip Scale Interconnect (FSI)
Chiplet 0
Chiplet 2
Chiplet 1
Chiplet 3
Chiplet
Chiplet
•
Programmable compute and 
LSUs with custom ISA
•
Native mixed-precision for FP16 
/ FP8-4 / NF4 / MXFP4 etc.
• Scale-up clustering based on 
system-level dataflow
(over 256 packages)
• Holistic design for multi-chiplet
performance optimization
Shared Memory Array (SHM) 
•
SoC-level scheduling of 
memory and compute with 
2-D mesh and FSI
•
Dataflow and control paths 
with a HW-supported cross-
chiplet synchronization
•
Scalable memory and DMA 
architectures


5
© 2026 Rebellions Inc. Confidential and Proprietary
Multi-chiplet Dataflow
Flexible dataflow configuration on custom multi-chiplet mesh enables high 
system utilization at full-chip scale
RebelConnectTM based Mesh Expansion 
without Data Congestion at the Chiplet Boundary 
Multi-chiplet level logical 2D mesh 
All units can access other chiplets with load-store semantics 
without boundary awareness 
SW-defined NoC to enable Extended 
Programmability from Flexible Cores to SoC 
Full-chip Scale Interconnect (FSI)
NoC Configuration
Traffic priority control for any type of AI workloads
Dynamic bottleneck-aware routing, scheduling and runtime
parameter tuning


© 2026 Rebellions Inc. Confidential and Proprietary
6
REBELTM-IO
System-level integration of multi-chip clusters with UCIe-A based custom IO die
2x IO Die 
ETH-based scale-up/out controller 
•
Scale Up: Latency-optimized custom protocol
•
Scale Out: RoCE V2 
Per-die scale-up/out BW
•
Scale Up: Up to 4 x 800Gbe 
•
Scale Out: Up to 1x 800Gbe
IO Die Logic 
Diagram
REBELTM-Quad
REBELTM-IO : 6.4 Tbps ETH-based Scale-up Fabric Enables REBELTM Inference Cluster 
Note: ISC = Integrated Silicon Capacitor


7
© 2026 Rebellions Inc. Confidential and Proprietary
Rack Solution
OAI-Universal Base Board w/ OAMs
IO die’s on-chip router for
faster data transfer
Minimized latency 
over P2P connection
Easy to scale up to 256
Variable latency 
but single-hop over ETH SW
REBEL -IO based scale-up clusters for rack-scale efficient inference to meet 
diverse custom AI workload demands
No Need
x64 Connection
Direct P2P-based Topology
ETH SW-based Topology
Scale-up
ETH Switch
R
R
R
R
R
R
R
R
OAI-Universal Base Board w/ OAMs
x8
x8
x8
x8
x8
x8
x8
x8


© 2026 Rebellions Inc. Confidential and Proprietary
8
REBELTM-CPU
Accelerated compute node in heterogenous systems for large-scale E2E serving
REBELTM-CPU : UCIe-D2D based Integration of REBELTM-Quad and Arm Neoverse V3 CPU
Note: ISC = Integrated Silicon Capacitor
2x CPU Die 
REBELTM-Quad
1:1 CPU – NPU in a single package via UCIe-A interface 
•
>500GB near AI compute (KV cache, context cache)
Coherency for efficient AI compute  
•
IO (REBELTM-Quad) to Full/IO coherency (REBELTM-Next)
•
CPUs to local command processors in NPU
