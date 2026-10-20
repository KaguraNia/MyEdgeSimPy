# 相关论文调查与研究盲点分析

> 目标：搞清楚这个方向"哪些研究点已经做烂、哪些是盲点"，避免把力气花在别人已经做完的地方，
> 尤其是避免在论文里做出**无法成立的新颖性声明**。

---

## 0. 这份调查是怎么做的（以及它的局限）

环境里没有通用网页搜索，但文献检索本来更适合走学术 API。用本仓库的
[`scripts/litsearch.py`](../scripts/litsearch.py) 查了 **OpenAlex + Crossref + arXiv + DBLP**，
共 30 余个检索式，原始返回全部留存在 `results/litreview/`（含每个检索式的逐条结果），
可复现：

```bash
python scripts/litsearch.py title "Live Service Migration in Mobile Edge Clouds" --abstract
python scripts/litsearch.py topic "trajectory inference from service migration observations" --limit 12
python scripts/litsearch.py digest results/litreview --limit 12 --authors --doi
```

检索式分三类：(a) 逐篇核实你给的 6 篇；(b) 扫领域全貌（迁移决策 / 迁移执行 / 有状态应用 /
安全隐私 / 元数据侧信道）；(c) **专门用来打自己脸的"盲点反证"检索**——如果某个想法已经被做过，
大概率能搜出来。

**局限（请据此打折使用）**：

1. 我只读了**元数据 + 摘要**，没有读全文。凡是摘要看不出来的细节都不能算数。
2. OpenAlex 覆盖不全（例如 SSRN 预印本没有摘要，我拿不到那篇的内容）。
3. **"没搜到"不等于"不存在"**。下面的盲点结论是"在我这些检索式下没有出现对口工作"，
   是**初步证据**，不是证明。投稿前必须再做一轮（Google Scholar 全文检索 + 反向引用追踪）。
4. Semantic Scholar 接口限流（HTTP 429），本次没用上，补检索时可以再试。

---

## 1. 你给的 6 篇：逐篇定性

| 论文（bib key） | 发表 | 属于哪一层 | 和你的重合度 | 该怎么用 |
|---|---|---|---|---|
| **Portkey** `p06portkey`/SoCC'21 | 顶会 | 移动性下的**数据放置** | 中 | 借它的核心思想，不是竞品 |
| **MoSEEC** `p01moseec`/TMC'25 | 顶刊 | 隐私 + 资源管理 | **高** | 阶段二最需要提防的邻居 |
| **Multi-Objective 5G-MEC Relocation** `p02multiobj`/SSRN'25 | 预印本 | 性能/可用性/隐私三方权衡 | **最高** | **必须拿到全文** |
| **StateProc** `p03stateproc`/Access'26 | 期刊 | NF 状态与状态传输 | 中 | 提供"状态迁移是瓶颈"的论据 |
| **Optimizing Security in Dynamic Service Migration** `p04optsec`/VTC'25 | 会议 | 迁移通道安全等级调节 | **高** | 安全-延迟权衡的直接对照 |
| **Live Service Migration** `p05live`/WCM'17 | 期刊（250 引） | 分层迁移框架、降 downtime | 高 | **你 pre-copy 的经典源头，必引** |

逐条：

**① Portkey（SoCC'21，Noor / Srivastava / Netravali）** — 分布式 KV 存储在边缘的动态放置，
面向自动驾驶数据集，平均/尾时延降 21–82%。它的核心 insight 值得你直接借用：
*"lean into the inherent mobility and prioritize rapid but approximate placement decisions
over delayed optimal ones"*（与其等一个延迟到达的最优决策，不如做一个快速近似的决策）。
这句话几乎就是"迁移决策要快于用户移动"的另一半表述。**但它不做服务状态迁移，也不碰安全**，
所以是灵感来源，不是竞品。

**② MoSEEC（TMC'25）** — 面向 MEC 的资源管理，用"用户自适应差分地理混淆"保护轨迹隐私，
同时兼顾可持续性（能耗）。它和你的阶段二重合度**高**：同样的 MEC + 移动 + 轨迹隐私。
差异点在于：它的隐私威胁是"资源分配需要精确位置 → 位置泄露"，保护手段是**模糊位置本身**；
你要做的是**隐藏迁移事件这一可观测信号**。这个差异能不能站住，取决于第 4 节。

**③ Multi-Objective 5G-MEC Service Relocation（SSRN'25）** — 从标题看，它把
**性能、可用性、隐私三方联合优化**，这和你第二阶段"安全-连续性-成本"三维是同构的。
**这是最可能吃掉你新颖性的一篇**。OpenAlex 里是 SSRN 预印本（两个版本号：5208772 / 5190306），
**没有摘要，我读不到内容**。你必须去拿全文，确认它：(a) 隐私威胁模型是什么？
(b) 有没有考虑迁移元数据侧信道？(c) 有没有把车速当变量？如果三个都是"没有"，你的空间还在。

**④ StateProc（IEEE Access 2026）** — 让有状态网络功能支持自定义处理能力，
核心难点落在"NF 状态及其传输"上，动机是移动性、容错、扩展性、低时延。
对你的价值：这是 2026 年的工作在复述"状态迁移很痛"，可以作为你系统层动机的近期引证。
另外 OpenAlex 里有个 Zenodo 版本（`10.5281/zenodo.20612378`，作者 Mahdi Attawna），
写 related work 时留意别重复计数。

**⑤ Optimizing Security in Dynamic Service Migration Scenarios of MEC（VTC-Fall'25）** —
提出一个面向 MEC gNodeB 的安全框架，**根据实时带宽利用率动态调整迁移通道的安全等级**，
动机正是"安全机制与 SLG（服务等级保证）互相拉扯：更强的安全带来开销、处理时延和加密时延"。
这几乎就是你"安全开销"那一维的直接对照物。它调的是**加密强度**，你调的是**可观测的迁移模式**，
差异清楚，但**必须引**，否则会被指"重复劳动"。

**⑥ Live Service Migration in Mobile Edge Clouds（WCM'17，250 引）** —
VM/容器分层迁移框架，核心卖点是**大幅降低 service downtime**。这是你 `proactive`+pre-copy
那条思路的经典源头，也是"低中断迁移"的必引基线。注意它的"分层（layering）"指的是
VM/容器镜像分层，和 EdgeSimPy 的 container layer 是同一条技术脉络，
正好接上 `a03containerlay`（TMC'18）。

### 一个必须指出的阅读缺口

你列的 6 篇里，最老的是 2017 年的 Live Service Migration，其余集中在 2025–2026。
**真正会威胁你新颖性的三篇老工作，你的列表里一篇都没有**：

| 漏掉的 | 为什么危险 |
|---|---|
| `a15chaff` **Location Privacy in Mobile Edge Clouds: A Chaff-Based Approach**（JSAC'17，64 引） | 它**已经**指出"观测迁移 = 定位用户"，并且**已经**用诱饵迁移（chaff）防御。见第 4 节。 |
| `a03containerlay` **Efficient Live Migration of Edge Services Leveraging Container Layered Storage**（TMC'18，175 引） | 容器分层存储降低迁移开销的鼻祖，你的"搬什么"那一层的老祖宗。 |
| `a01mdpton` **Dynamic Service Migration in MEC Based on MDP**（ToN'19，272 引） | 迁移决策的经典形式化，所有 DRL 工作的对照基准。 |

---

## 2. 领域地图：五个簇

**簇 A：迁移决策（何时迁 / 迁到哪）—— 极其拥挤**
`a01mdpton` MDP 形式化（ToN'19, 272 引）→ `a06segue` QoS 感知迁移（CloudCom'16）
→ `a11premigration` 车联网按优先级**预迁移**（Access'18）→ `a12multitier` 基于移动性预测的
多层迁移（WCMC'21）→ DRL 大爆发（`availability-relocation` 检索式下 7 篇以上）
→ 综述 `a13realtimesurvey`（JSAN'25, 19 引）、`a14mlsurvey`（COMST'23, 42 引）。

**簇 B：迁移执行 / 底层传输（怎么搬）—— 你的主战场，但 2017–2019 已被犁过一遍**
`a07fastvm` 边缘云中的快速透明 VM 迁移（SEC'17, 51 引）→ `a03containerlay` 容器分层存储
（TMC'18, 175 引）→ `a04differential` 差异化服务/数据迁移（Access'19, 64 引）
→ `a05warping` Warping the Edge：5G 瞬时移动性与有状态应用（arXiv'24）
→ `p03stateproc` 有状态 NF（Access'26）。
**注意：这个簇里"降低迁移字节"的机制性工作集中在 2017–2019**，近几年偏"框架/平台"
而非"传输机制"。这对你既是机会（机制层有空位）也是警告（容易被说"炒冷饭"）。

**簇 C：有状态应用与 5G/ETSI 标准化**
`a08etsistateful` 把 ETSI MEC 扩展到基于容器迁移的有状态应用重定位（WoWMoM'22, 13 引）
→ `a05warping`（arXiv'24）→ `state-migration-stateful` 检索式下还有 serverless 有状态迁移等。

**簇 D：安全与隐私 —— 已经很拥挤，且在快速升温**
`a10secprivsurvey` MEC 安全隐私综述（COMST'21, 354 引）
→ `a15chaff` chaff 防御（JSAC'17, 64 引）→ `a22presloc` MEC 位置隐私（ICC'19）
→ `a21locleak5g` 5G 位置隐私泄露（Sensors'21）→ `a205ghandover` 5G 切换安全隐私综述
（IoT-J'21, 40 引）→ `p01moseec` MoSEEC（TMC'25）→ `a16sapmove` SAPMOVE 面向 6G 自动驾驶的
隐私保护移动感知安全迁移框架（TechRxiv'25）→ `p02multiobj` 三方联合优化（SSRN'25）。

**簇 E：元数据 / 侧信道推断（攻击方法论来源）**
`a18encdns` Encrypted DNS 的流量分析（NDSS'20, 110 引）
→ `a19deepmend` 从基站位置做网络元数据地理定位（SECON'24）
→ 以及 `metadata-side-channel` / `gap-mobility-inference-meta` 检索式下的
加密流量指纹、地理推断、时序元数据行为推断等 2026 年新作。
**关键：这些方法论成熟，但都不在 MEC 迁移场景下做。**

---

## 3. 已经被做烂的：只能当 baseline 引用，不能当贡献

1. **MDP / DRL 迁移决策** —— 从 ToN'19 到 2025–2026 每年都有，红海。
2. **"预测式 vs 反应式"迁移的对比** —— `a17reactpred` **Reactive vs Predictive Live Migration
   in Edge Cloud**（ICC'24）已经做了。你仓库里的 `proactive` vs `reactive` 对比
   **不能作为贡献**，只能作为你已经内建好的基线维度来引用。
3. **容器分层镜像降低迁移成本** —— `a03containerlay`（TMC'18, 175 引）8 年前的事。
4. **"用诱饵迁移隐藏真实迁移"** —— `a15chaff`（JSAC'17）已经做过（见第 4 节）。
5. **ETSI MEC 有状态应用重定位的标准化** —— `a08etsistateful`（WoWMoM'22）。
6. **位置模糊 / 差分隐私保护 MEC 轨迹** —— `p01moseec` + `a22presloc` + `a21locleak5g`。

---

## 4. ⚠️ 最重要的一条更正：你的安全想法有个前提已经被做掉了

你原话里的威胁模型是：*"外部攻击者能观测状态迁移的发生时间，以及在哪两个节点之间迁移，
可以推测终端的移动轨迹"*。

看 `a15chaff`（JSAC 2017）的摘要原文：

> "Co-location of a user and his service, however, implies that a **cyber eavesdropper
> observing service migrations between MECs can localize the user**... many solutions have
> been proposed to maximize service locality by **migrating services to follow their users**."

也就是说：

- **"观测 MEC 之间的服务迁移可以定位用户"这个前提，2017 年就已明确发表**，而且它连
  "follow-me 迁移"这个说法都先用了。
- **"用诱饵（chaff）迁移来对抗它"这个防御，也已经在同一篇里做了**。

所以下面三句话你**不能**写：

1. ❌ "我们首次发现服务迁移会泄露位置/轨迹信息。"
2. ❌ "我们首次提出用诱饵/虚假迁移来掩盖真实迁移。"
3. ❌ "现有工作忽略了迁移元数据这一泄露面。"

正确写法是：

> 迁移事件泄露位置这一风险自 [chaff, JSAC'17] 起已被认识，其防御以诱饵迁移为代表。
> 我们在此基础上把问题从**单点定位**推进到**整条轨迹重构与下一跳预测**，
> 在真实出租车轨迹上以学习型攻击者量化攻击成功率，并把**车速**作为自变量刻画
> "侧信道密度 vs 防御预算"的耦合，最后把防御开销与**传输层优化节省的带宽**联合求解。

### 那还剩什么可以做的？（四个真正开放的点）

| # | 开放点 | 为什么还算开放 | 证据 |
|---|---|---|---|
| **G1** | **从"定位"升级到"整条轨迹重构 + 下一跳预测"**，用真实出租车数据 + 学习型攻击者 | 2017 年那篇解决的是"用户在哪个区"；当时没有 mobility-prediction/序列模型这一套，也没有真实轨迹数据集可评 | `gap-trajectory-from-migration` 检索式**零篇对口**（返回的全是鸟类迁徙、旗鱼迁徙等无关文献 + 服务迁移综述） |
| **G2** | **车速作为一等变量**：速度↑ → 迁移事件更密 → 侧信道更强、攻击更易；但同时每 cell 停留更短 → 防御可用的时间/带宽预算更紧 | 没有任何工作把速度同时放进"攻击难度"和"防御预算"两侧；现有 IoV 工作只把速度当背景参数 | `gap-speed-effect` 检索式下只有 IoV 综述与"按优先级预迁移"，**无速度敏感性研究** |
| **G3** | **防御预算来自传输层节省**：如果 delta+压缩把状态传输压到原来的 1/10，省下的字节能不能"买回"隐私？ | 现有工作都把隐私当性能的**代价**（展示 degradation）；反过来用系统优化**补贴**隐私，并画安全-连续性-成本三维 Pareto，没人这么写过 | `p01moseec` / `p02multiobj` / `p04optsec` 都是"隐私/安全 vs 性能"的权衡，方向是单向的 |
| **G4** | **"隐私友好的传输设计"**：delta、批量、压缩这些传输层选择本身会改变可观测事件的模式（次数、时刻、字节分布） | 现有工作把传输层当成本问题、把隐私当加密/诱饵问题，**没人研究传输层设计对侧信道强度的影响** | 簇 B 与簇 D 之间没有交叉引用式的机制工作 |

G4 是 G3 的机制基础，而 G3 是你两个阶段之间最自然的桥梁——
**它把你已经建好的传输层优化从"省钱"变成"买隐私的预算来源"**。

---

## 5. 建议的研究点（按风险/回报排序）

**选项 A（低风险，够毕业，不够亮）—— 传输层三层归因优化**
把"搬什么 / 什么时候搬 / 怎么搬得快"逐层量化，给出中断-字节-时延 Pareto。
基础你已经有了（框架 + 指标 + 三层表 + 现有扫描结果）。
风险：容易被评审说成"工程调参"；建议作为**论文的系统部分**，而不是唯一贡献。
参考坐标：`a03containerlay`、`a04differential`、`p05live`。

**选项 B（高风险高回报）—— 迁移元数据的轨迹重构攻击 + 速度维度（= G1 + G2）**
把 2017 年的"定位"升级为"轨迹重构/下一跳预测"，在 Rome/SF 真实轨迹上训练攻击者，
把车速扫成自变量。你的 `observable_migration_trace.json` 已经是攻击者视角的 ground truth，
工程量比想象的小。
风险：**前提不新**（第 4 节），必须先做 novelty check 并引用 `a15chaff`。

**选项 C（最值得做）—— 用传输层的节省给防御买单（= G3 + G4，含 A 和 B）**
核心问题一句话：
> **把状态传输优化到原来的十分之一之后，省下来的带宽能不能买回隐私？**

做法：`delta + 压缩` 省字节 → 省下的预算用于诱饵迁移 / 时序抖动 / 字节填充
→ 画三维 Pareto（攻击成功率 × 中断比例 × 迁移开销）。
为什么好：它把阶段一（系统优化）和阶段二（安全）**绑成一个故事**，
而且结论方向是反直觉的（系统优化补贴隐私），比"再刷一个 DRL"有意思得多。
答辩时也最好讲：一条主线，两个阶段，互为因果。

> 我的建议：**以 C 为主线，把 A 当作已经完成的前置工作，把 B 当作 C 里必须交付的
> 攻击评估部分。** 这样你现有的仓库几乎不用推倒，只需要在 `myedgesimpy/security/` 下
> 补攻击与防御两层（骨架见 `docs/research_roadmap.md` 第 2 节）。

---

## 6. 立刻要做的三件事（按顺序）

1. **拿到 `p02multiobj`（SSRN 5208772 / 5190306）和 `p01moseec` 的全文**。
   这两篇决定你新颖性的边界，尤其前者——它的标题和你的三维目标完全同构，
   而我现在读不到它的摘要。**在读完之前不要写任何"首次"。**
2. **拿到 `a15chaff`（JSAC'17）全文**，逐条列出它做了什么、没做什么（用了什么移动模型？
   单节点还是全局观测者？度量是定位误差还是轨迹重构？有没有成本模型？）。
   这张对照表就是你 related work 里差异化那一段的骨架。
3. **补两篇综述**：`a13realtimesurvey`（Real-Time Service Migration in Edge Networks, JSAN'25）
   和 `a14mlsurvey`（Machine Learning for Service Migration, COMST'23），
   用它们的参考文献列表做反向查缺，确认没有漏掉关键工作。

---

## 7. 引用清单（`docs/refs_related_work.bib`，27 条，均已核验 DOI）

**你给的 6 篇**：`p01moseec` `p02multiobj` `p03stateproc` `p04optsec` `p05live` `p06portkey`

**你漏掉的危险老工作**：`a15chaff` `a03containerlay` `a01mdpton`

**迁移决策**：`a06segue` `a11premigration` `a12multitier` `a02survey` `a13realtimesurvey` `a14mlsurvey` `a17reactpred`

**迁移执行 / 传输**：`a07fastvm` `a04differential` `a05warping` `a08etsistateful`

**安全隐私**：`a10secprivsurvey` `a22presloc` `a21locleak5g` `a205ghandover` `a16sapmove`

**元数据/侧信道方法论**：`a18encdns` `a19deepmend`

> 注：`p02multiobj` 是 SSRN 预印本，`a16sapmove` 是 TechRxiv 预印本，
> bib 条目里已按预印本记录；正式引用前请确认是否已有正式发表版本。

---

## 8. 补充核查（2026-10）：上一版有三处结论说过头了

读完你提供的全文、又补做了"隐私 × 传输优化"的交叉检索之后，必须更正：

**更正 1：「没人优化怎么搬」是错的。**
`z1fast` **FAST: Flexible and Low-Latency State Transfer in MEC**（IEEE Access 2021, 49 引）
就是专门研究"MEC 状态传输优化"的：快速、无中断地迁状态，同时最小化传输成本。
更早还有 `a03containerlay`（TMC'18，容器分层存储）和 `a04differential`（Access'19，差异化
服务/数据迁移）；2024 年还有 `z4layeraware`（层感知的主动/被动容器迁移）。
`a02survey`（Access'18）甚至有一整节 **"Reducing Data Size"**：变更追踪、delta 编码、
去重、压缩。**所以"增量 / 压缩 / 预拷贝"本身不是新东西，是成熟技术。**

**更正 2：「没人研究车速」不准确。**
速度/velocity 确实被一些迁移策略当作输入：例如 MyiFogSim 用"位置 + 速度 + 方向"决定
何时迁移；2025 年综述（`a13realtimesurvey` §6.5）也提到 Gao 等人的 DRL 方法联合考虑
"车辆位置、速度、时延约束"。**更准确的说法是**：把速度当作**受控实验变量**、
系统扫描它对"成本 + 隐私"两侧影响的工作，我没有找到；但这比上一版的说法弱得多。

**更正 3：「迁移泄露轨迹」的邻居比我说的还多。**
除了第 4 节的 `a15chaff`（JSAC'17）和 `p01moseec`（TMC'26），还有：
`z2dtprivacy` **Privacy Attacks and Defenses for Digital Twin Migrations in Vehicular
Metaverses**（IEEE Network 2023, 50 引）——车辆数字孪生在 RSU 间迁移导致身份/位置隐私泄露；
`w1tscmetaverse` **Privacy-Preserving Service Migration for Multi-User Metaverse
Environments**（IEEE TSC 2026）——多用户服务迁移 + 差分隐私 + MAPPO；
以及你文件夹里的 IoT-J 2024（熵度量 + MASAC）。

### 修正后的结论

能站住的只剩一个**很窄的交集**，而不是一个大空白：

> **"传输机制的选择"（全量 / 增量 / 压缩 / 预取 / 预拷贝）是否会改变攻击者看到的
> 可观测模式，以及这种影响如何随车速变化。**

我在这轮检索里**没有找到直接做这件事的论文**，但：

1. 这是"没搜到"，不是"不存在"。置信度：**低到中**。
2. 相邻工作很密，审稿人很可能拿出一篇我没检索到的。
3. 因此**不能**把论文押在"首次发现/首次提出"上。

### 更稳妥的选题方式

放弃"抢一个新问题"，改成 **复现 + 扩展**：

1. **复现 `p02multiobj`（MORA）**。它用的正是 EdgeSimPy + DATA7，和你导师要求的栈完全一致，
   而你的原型已经覆盖了大部分基础设施。
2. **扩展它最弱的一环**：MORA 把"迁移中断"当成一个给定的代价项，没有真正建模
   "怎么搬"。把它替换成你已有的全量 / 增量 / pre-copy 传输模型。
3. **加入速度作为自变量**，看传输方式如何改变"时延–隐私"的 Pareto 前沿。

这是硕士论文里很稳的形态：**不是宣称新问题，而是把一个已发表方法放到更真实的传输模型下
重新检验，并给出新发现。** 不需要 GPU，也不依赖抢首发。

**动手前必须读全文的三篇**：`z1fast`（传输优化做到什么程度）、`z2dtprivacy`（迁移隐私攻击
怎么建模）、`p02multiobj`（MORA 的 disruption 与 privacy 两项具体怎么算）。
