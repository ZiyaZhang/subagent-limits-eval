# 解盲前的泄漏人工关

共 30 次运行：得分最高的 20 次，加上文字重合检查标出来的 10 次，顺序已打乱。每条只判断一件事：这份报告有没有照抄题目禁用的那篇来源文章，或者明显用了它。不显示组别、运行编号和分数。
在 leak-answers-template.csv 里填 没有 / 有 / 拿不准，另存为 leak-answers.csv。

## 条目 1

**题目**：Investigation of Hydroforming Technology（Industrial）

**禁用的来源文章**：A review of emerging hydroforming technologies: design considerations, parametric studies, and recent innovations

- https://jeas.springeropen.com/articles/10.1186/s44147-024-00546-z
- https://www.researchgate.net/publication/385401108_A_review_of_emerging_hydroforming_technologies_design_considerations_parametric_studies_and_recent_innovations
- https://ui.adsabs.harvard.edu/abs/2024JEAS...71..205C/abstract

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 264 个地址，最多的站点**：api.crossref.org 27，api.semanticscholar.org 18，sciencedirect.com 10，en.wikipedia.org 9，ahssinsights.org 9，mdpi.com 8，thefabricator.com 7，koreascience.kr 6，ouci.dntb.gov.ua 6，schulergroup.com 6，patents.google.com 5，jstage.jst.go.jp 5

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 液压成形（Hydroforming）技术调研报告
    ## ——材料选择与常见制造缺陷
    ## 执行摘要
    ## 目录
    # 第一部分　常用材料分析
    ## 1.0 四种材料总览对比
    ## 1.1　高强度钢（High-Strength Steel, HSS）
    ### 材料特性
    #### 1. 类别与典型牌号
    #### 2. 力学性能典型数值
    #### 3. 应变硬化指数（n 值）与塑性应变比（r 值）
    #### 4. 焊管特性（激光焊管与高频焊管）
    #### 5. 与低碳钢的对比
    ### 成形挑战
    #### 1. 高流动应力与所需内压／设备吨位
    #### 2. 延性耗竭与非线性应变路径
    #### 3. 失效模式：屈曲、起皱与破裂
    #### 4. 焊缝与热影响区（HAZ）开裂
    #### 5. 回弹（springback）与形状畸变
    #### 6. 模具磨损与表面处理
    #### 7. 润滑与摩擦
    #### 8. 氢脆与延迟开裂（delayed cracking / hydrogen embrittlement）
    #### 9. 热处理与涂镀的影响
    ### 主要应用（含具体汽车部件实例）
    #### 1. 液压成形件的通用部件谱系
    #### 2. 可查证的车型/厂商案例
    #### 3. 材料升级与"以成形换强度"的工程策略
    #### 4. 板料液压成形（sheet hydroforming）中的高强度钢
    #### 5. 空心轴类与其他液压成形应用
    ### 参考来源
    ## 1.2　高强度铝合金（High-Strength Aluminium Alloys）
    ### 材料特性
    ### 成形挑战
    ### 主要应用（含具体汽车部件实例）
    ### 参考来源
    ## 1.3　镁合金（Magnesium Alloys）
    ### 材料特性
    ### 成形挑战
    ### 主要应用（含具体部件实例）
    ### 参考来源

**报告开头**：

> # 液压成形（Hydroforming）技术调研报告
> 
> ## ——材料选择与常见制造缺陷
> 
> > **调研方式**：本报告将课题拆分为 **8 个互不重叠的调研单元**（4 种代表性材料 + 4 组制造缺陷，其中"变薄与撕裂"因机理同源而合并为一个调研单元、在报告中分列为两节），由 8 个独立子代理分别检索与撰写，再由主分析师统一结构、术语、交叉引用与结论。
> >
> > **编制日期**：2026-10-08
> >
> > **合规声明**：本报告严格遵守委托方设定的来源限制。委托方明确禁止访问与引用的那篇 2024 年液压成形综述及其指定 URL、转载页与摘要页，全程未被打开、未被引用，也未作为任何二手引用的中介；报告全部结论均来自各调研单元独立检索的公开可核查来源。
> 
> ---
> 
> ## 执行摘要
> 
> **材料侧**：液压成形用材的选择是"比强度—室温/高温成形性—成本—产业化成熟度"的权衡。高强度钢（HSS）凭借成熟的焊管供应、最高的承载能力与最低的材料成本，仍是量产结构件的主力（DP600 级 Rm≈640 MPa，热成形硼钢 22MnB5 淬火后可达 1300–1650 MPa）；高强度铝合金以 5xxx/6xxx 为主力，密度约 2.7 g/cm³，但弹性模量仅约 70 GPa、回弹约为钢的 2–3 倍，7xxx（7075-T6 约 510–540 MPa）须依赖温成形；镁合金密度最低（约 1.74 g/cm³），室温塑性极差，管材液压成形须在 200–400 °C 进行，目前量产仍以压铸/触变为主、液压成形处于样件与研发阶段；钛合金比强度与耐蚀性突出（Ti-6Al-4V 抗拉 897–1000 MPa），但通常需 500–900 °C 热/温成形并需处理硬脆 α 层，成本最高，主要面向航空航天、医疗与高端消费件。
> 
> **缺陷侧**：五类缺陷可按发生的物理阶段归类——**起皱**属压缩失稳（内压不足而轴向补料过大时最典型）；**变薄**属拉伸减薄，**撕裂/爆裂**是变薄发展到局部颈缩后的断裂事件（内压过高、膨胀率超限或补料不足时最典型）；**回弹**发生在卸载阶段，是弹性恢复导致的尺寸/形状偏差；**表面缺陷**发生在制件—模具表界面，由摩擦、粘着磨损、模具状态与介质污染控制。五类缺陷的共同杠杆是**内压—轴向进给加载路径**：路径过低先起皱、过高则局部减薄乃至爆裂，二者之间存在较窄的无失效工艺窗口；因此对策主线是"加载路径优化 + 模具几何与润滑 + FEA/成形极限图预测 + 在线监测"，并辅以脉动液压成形、温/热成形、预成形与多步成形等工艺手段。
> 
> ---
> 
> ## 目录
> 
> - 第一部分　常用材料分析
>   - 1.1　高强度钢（HSS）
>   - 1.2　高强度铝合金
>   - 1.3　镁合金
>   - 1.4　钛合金
> - 第二部分　常见缺陷、成因及对策
>   - 2.1　表面缺陷（Surface Defects）
>   - 2.2　回弹（Springback）
>   - 2.3　起皱（Wrinkling）
>   - 2.4　变薄（Thinning）
>   - 2.5　撕裂（Tearing）
> - 第三部分　结论与综合建议
> - 附录 A　调研分工与合规说明
> 
> ---
> 
> # 第一部分　常用材料分析
> 
> > 本部分覆盖液压成形中四种代表性金属材料：高强度钢（HSS）、高强度铝合金、镁合金与钛合金。每种材料均按"**材料特性 → 成形挑战 → 主要应用（含具体部件实例）**"展开，实例尽量落到可查证的汽车/航空部件与车型、厂商案例上。各小节来源编号独立，见每节末尾《参考来

**报告结尾（含参考文献）**：

> 2. **几何与摩擦协同设计**：避免过小的 r/t 比与过渡圆角；通过模具表面处理（PVD/CVD 涂层等）、分区差异润滑与强制润滑控制材料流动，兼顾防拉毛与防起皱/减薄。
> 3. **焊管必须按焊缝区性能单独设计**：焊管（高频焊/激光焊）的焊缝与热影响区存在性能弱化与残余应力，裂纹常由此起裂，应建立焊管专用的成形极限图（FLC），并控制周向性能均匀性与原始壁厚偏差。
> 4. **预测与监测闭环**：用有限元（FEA）联合 FLD 或路径无关爆裂判据（下限=最大承载能力、上限=总延伸率）预判失效位置与安全裕度；用超声测厚、CMM/三维应变测量、轴向力传感器在线标定工艺窗口。
> 5. **回弹单独治理**：提高整形压力与保压时间、模具型面过弯补偿、基于仿真的迭代补偿，以及温成形与背压控制，是控制回弹的主要手段。
> 
> ## 3.3 技术趋势
> 
> - **脉动液压成形**：以反复"小幅起皱—鼓胀"改变应变路径，提升成形极限并均匀壁厚，是抑制变薄/撕裂与起皱的活跃方向。
> - **温/热液压成形**：铝、镁、钛的工艺窗口普遍依赖温度，非均匀温度场与局部加热控制是工程化关键。
> - **多步/预成形与混合工艺**：多通管多步成形、主动利用"有益皱纹"预成形，以及内高压成形+注塑（如混合式仪表板横梁）等混合工艺，正在扩展液压成形的零件谱系。
> - **数字化**：加载路径的多目标优化（如 NCGA 等）、自适应仿真与在线监测，将工艺开发从试错推向模型驱动。
> 
> ---
> 
> # 附录 A　调研分工与合规说明
> 
> ## A.1 八个互不重叠的调研单元
> 
> | 单元 | 主题 | 产出分册 |
> |---|---|---|
> | 1 | 高强度钢（HSS）材料特性/成形挑战/应用 | `parts/01_hss.md` |
> | 2 | 高强度铝合金材料特性/成形挑战/应用 | `parts/02_aluminum.md` |
> | 3 | 镁合金材料特性/成形挑战/应用 | `parts/03_magnesium.md` |
> | 4 | 钛合金材料特性/成形挑战/应用 | `parts/04_titanium.md` |
> | 5 | 表面缺陷：定义/成因/对策 | `parts/05_surface_defects.md` |
> | 6 | 回弹：定义/成因/对策 | `parts/06_springback.md` |
> | 7 | 起皱：定义/成因/对策 | `parts/07_wrinkling.md` |
> | 8 | 变薄与撕裂：定义/成因/对策 | `parts/08_thinning_tearing.md` |
> 
> 各单元由独立子代理完成检索与撰写，单元之间无内容重叠；主分析师负责统一标题层级、术语、横向对比、结论与合规核查。由于平台并发限制（同时最多 2 个活跃子代理），8 个单元按 4 波、每波 2 个并行执行，但分工仍为 8 个互不重叠单元。
> 
> ## A.2 来源与合规
> 
> - 各分册正文中的方括号编号（如 [1]、[2]）对应该分册末尾的《参考来源》列表；全部来源均为公开可核查的期刊论文、会议论文、专利、厂商/行业资料与教科书。
> - **合规核查结果**：本报告全文（含各部分来源列表）不含委托方禁止的那篇 2024 年液压成形综述的标题、作者、URL 或 DOI；该文献未被访问、未被引用，也未通过其他文献被间接转述引用。核查方式为对全部 8 个分册与最终报告进行关键词全文扫描（标题关键词、作者姓氏、禁用 URL 与 DOI 片段），命中数为 0。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 2

**题目**：A Survey of Population-Based Deep Reinforcement Learning（Software Development）

**禁用的来源文章**：A Survey on Population-Based Deep Reinforcement Learning

- https://www.mdpi.com/2227-7390/11/10/2234
- https://ideas.repec.org/a/gam/jmathe/v11y2023i10p2234-d1143662.html
- https://encyclopedia.pub/entry/44828
- https://www.mdpi.com/2227-7390/11/10/2234/reprints

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里出现了来源文章的标题；与来源正文相同的 12 词片段 5 条；相同的参考文献 0 条。

相同片段举例：`on population-based deep reinforcement learning weifan long taixian hou xiaoyi wei shichao`

**这次运行打开过 25 个地址，最多的站点**：arxiv.org 15，ar5iv.labs.arxiv.org 4，proceedings.mlr.press 3，pmc.ncbi.nlm.nih.gov 1，nature.com 1，davidsilver.uk 1

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 基于群体的深度强化学习（Population-Based Deep Reinforcement Learning, PB-DRL）算法调研报告
    ## 一、五个主要类别：内涵、发展脉络与核心区别
    ### 1.1 朴素自博弈（Naive Self-Play）
    ### 1.2 虚拟自博弈家族（Fictitious Self-Play Family）
    ### 1.3 群体博弈、联盟训练与人机协作（Population Play / League / Human-AI）
    ### 1.4 基于演化的方法（Evolutionary Methods）
    ### 1.5 通用博弈论框架：PSRO 族
    ### 1.6 发展脉络与核心区别（小结）
    ## 二、术语与命名辨析（阅表前必读）
    ### 2.1 PSROηN 即 PSRO_rN（整流纳什响应）
    ### 2.2 ED：两种读法
    ### 2.3 δ-Uniform FSP 的精确参数化
    ### 2.4 PP 是一类训练范式
    ### 2.5 其他缩写
    ## 三、19 个算法详细比较表
    ## 四、横向观察与选型建议
    ### 4.1 按需求场景的简要选型
    ### 4.2 共同瓶颈
    ### 4.3 截至 2023 年初的开放问题
    ## 五、四份草稿的合并与核实记录
    ## 六、参考文献
    ## 七、合规声明

**报告开头**：

> # 基于群体的深度强化学习（Population-Based Deep Reinforcement Learning, PB-DRL）算法调研报告
> 
> **调研范围**：截至 2023 年初，PB-DRL 方向的主要算法与框架，共 19 个，覆盖朴素自博弈、虚拟自博弈、群体博弈、基于演化的方法、通用博弈论框架（PSRO 族）五类。
> 
> **合并说明**：本报告由 `inputs/report-1.md`、`report-2.md`、`report-3.md`、`report-4.md` 四份独立完成的同名报告合并而成。合并原则是：有来源的事实全部保留、重复的只写一次；四份之间不一致之处回溯一手论文重新核实后采用核实结论，核实不到的标注**【待核验】**。本次合并没有重新做一遍完整调研，只在存在分歧或关键细节处查证。核实记录见第五节。
> 
> **合规声明**：调研与撰写全程**没有打开、没有阅读、没有引用**《A Survey on Population-Based Deep Reinforcement Learning》（Weifan Long, Taixian Hou, Xiaoyi Wei, Shichao Yan, Peng Zhai, Lihua Zhang）一文，也没有打开或使用其任何指定网址、镜像、转载页、摘要页或第三方索引页；该文献及其任何转述均不作为本报告的信息来源。
> 
> ---
> 
> ## 一、五个主要类别：内涵、发展脉络与核心区别
> 
> PB-DRL 的核心问题可以用一句话概括：**一个智能体的能力上限，很大程度上取决于它训练时面对的是什么样的对手或伙伴**。从 1951 年的虚拟博弈、2016 年前后的深度自博弈，到 2023 年初的 PSRO 变体，整条技术路线实际上是在不断回答三个问题：
> 
> 1. **对手／伙伴从哪里来**：只用自己最新的策略？用历史策略的平均？从历史池中按窗口或优先级采样？维护一个显式的策略种群？由元博弈均衡混合生成？还是用隐藏效用或形态变异生成？
> 2. **新策略如何产生**：梯度式强化学习（RL）、进化／黑箱搜索，还是"最佳响应 oracle"？
> 3. **优化目标是什么**：当前策略的期望回报、可利用度（exploitability）、稀疏的团队回报、按胜率加权的训练效率、对未见伙伴的协作泛化，还是种群多样性本身？
> 
> 不同类别正是对这三个问题的不同回答，也因此对应着不同的理论保证与工程代价。
> 
> ### 1.1 朴素自博弈（Naive Self-Play）
> 
> 最原始的范式：每个训练轮次只把**自己最新版本的策略**（或其冻结副本）作为对手，对手分布是集中于当前策略上的一个 δ 分布；用当前策略采集数据、更新参数，对手随即同步换成更新后的自己。典型代表是 TD-Gammon、AlphaGo Zero/AlphaZero；OpenAI Five 中"80% 对局打最新自己"的部分、以及竞争性多智能体任务中的朴素自对弈也属于这一范式。
> 
> - **优点**：实现最简单、不需要对手建模、历史策略池或元博弈设施，计算最省，天然适合大规模并行；在近似**传递（transitive/monotonic）**的博弈（围棋、国际象棋等）中会形成"赢了昨天的自己，通常也赢更早的自己"的难度递增课程，能力可持续上升，AlphaZero 系列已验证到超人水平。
> - **缺点**：训练目标随对手漂移（非平稳）；在**非传递（non-transitive）**博弈（猜拳、扑克、许多资源分配与即时战略类博弈）中会出现策略循环、震荡、策略退化／灾难性

**报告结尾（含参考文献）**：

> 13. D. J. Strouse, K. R. McKee, M. Botvinick, E. Hughes, R. Everett. *Collaborating with Humans without Human Data*（FCP；PP 基线的形式化）. NeurIPS 2021 (spotlight); arXiv:2110.08176. <https://arxiv.org/abs/2110.08176>
> 14. C. Yu, J. Gao, W. Liu, B. Xu, H. Tang, J. Yang, Y. Wang, Y. Wu. *Learning Zero-Shot Cooperation with Humans, Assuming Humans Are Biased*（Hidden-Utility Self-Play, HSP）. ICLR 2023; arXiv:2302.01605. <https://arxiv.org/abs/2302.01605>
> 
> **演化 / 群体训练线**
> 
> 15. M. Jaderberg et al. *Population Based Training of Neural Networks.* arXiv:1711.09846, 2017. <https://arxiv.org/abs/1711.09846>
> 16. M. Jaderberg et al. *Human-level Performance in 3D Multiplayer Games with Population-based Reinforcement Learning.* Science 364(6443):859–865, 2019（FTW；PBT 大规模应用）.
> 17. S. Khadka, S. Majumdar, S. Miret, S. McAleer, K. Tumer. *Evolutionary Reinforcement Learning for Sample-Efficient Multiagent Coordination*（MERL）. ICML 2020, PMLR 119; arXiv:1906.07315. <https://arxiv.org/abs/1906.07315>
> 18. S. Khadka, S. Majumdar, T. Nassar, Z. Dwiel, E. Tumer, S. Miret, Y. Liu, K. Tumer. *Collaborative Evolutionary Reinforcement Learning*（CERL）. ICML 2019, PMLR 97:3341–3350; arXiv:1905.00976. <https://proceedings.mlr.press/v97/khadka19a.html>
> 19. A. Gupta, S. Savarese, S. Ganguli, L. Fei-Fei. *Embodied Intelligence via Learning and Evolution*（DERL）. Nature Communications 12:5721, 2021; arXiv:2102.02202. <https://www.nature.com/articles/s41467-021-25874-z>
> 
> **PSRO 线**
> 
> 20. M. Lanctot, V. Zambaldi, A. Gruslys, A. Lazaridou, K. Tuyls, J. Pérolat, D. Silver, T. Graepel. *A Unified Game-Theoretic Approach to Multiagent Reinforcement Learning*（PSRO）. NeurIPS 2017; arXiv:1711.00832. <https://arxiv.org/abs/1711.00832>
> 21. D. Balduzzi, M. Garnelo, Y. Bachrach, W. M. Czarnecki, J. Perolat, M. Jaderberg, T. Graepel. *Open-ended Learning in Symmetric Zero-sum Games*（PSRO_rN；Effective Diversity；gamescape）. ICML 2019; arXiv:1901.08106. <https://arxiv.org/abs/1901.08106>
> 22. N. Perez-Nieves, Y. Yang, O. Slumbers, D. H. Mguni, Y. Wen, J. Wang. *Modelling Behavioural Diversity for Learning in Open-Ended Games*（Diverse PSRO）. ICML 2021, PMLR 139:8514–8524; arXiv:2103.07927. <https://proceedings.mlr.press/v139/perez-nieves21a.html>
> 23. S. McAleer, J. B. Lanier, R. Fox, P. Baldi. *Pipeline PSRO: A Scalable Approach for Finding Approximate Nash Equilibria in Large Games.* NeurIPS 2020; arXiv:2006.08555. <https://arxiv.org/abs/2006.08555>
> 24. P. Muller, S. Omidshafiei, M. Rowland, K. Tuyls, J. Perolat, S. Liu, D. Hennes, L. Marris, M. Lanctot, E. Hughes, Z. Wang, G. Lever, N. Heess, T. Graepel, R. Munos. *A Generalized Training Approach for Multiagent Learning*（α-PSRO；α-Rank + PBR）. ICLR 2020; arXiv:1909.12823. <https://arxiv.org/abs/1909.12823>
> 
> **术语与延伸阅读（超出 2023 年初范围，仅供名称对照/延伸）**
> 
> 25. D. Hernandez, K. Denamganaï, S. Devlin, S. Samothrakis, J. A. Walker. *A Comparison of Self-Play Algorithms Under a Generalized Framework.* IEEE Transactions on Games, 2021; arXiv:2006.04471（自博弈的统一形式化；δ-uniform 等名称对照）. <https://arxiv.org/abs/2006.04471>
> 26. Y. Zhao et al. *AlphaHoldem: High-Performance Artificial Intelligence for Heads-Up No-Limit Texas Hold'em via End-to-End Reinforcement Learning.* AAAI 2022（"Delta-Uniform Self-Play" 命名）.
> 27. R. Zhang, Z. Xu, C. Ma, C. Yu, W.-W. Tu, W. Tang, S. Huang, D. Ye, W. Ding, Y. Yang, Y. Wang. *A Survey on Self-play Methods in Reinforcement Learning.* arXiv:2408.01072, 2024（仅用于 δ-uniform self-play / PFSP 术语对照）.
> 28. F. Lin, S. Huang, T. Pearce, W. Chen, W.-W. Tu. *TiZero: Mastering Multi-Agent Football with Curriculum Learning and Self-Play.* arXiv:2302.07515, 2023（AlphaStar 式 PFSP 采样 `f_hard(x)=(1−x)^2` 的实现）.
> 29. A. Bighashdel, Y. Wang, S. McAleer, R. Savani, F. A. Oliehoek. *Policy Space Response Oracles: A Survey.* arXiv:2403.02227, 2024（PSRO 的 MSS/oracle 变体、多样性度量与收敛性质梳理）.
> 30. OpenDILab DI-engine，league 与 PFSP 实现文档. <https://opendilab.github.io/DI-engine/_modules/ding/league/starcraft_player.html>
> 
> ---
> 
> ## 七、合规声明
> 
> - 本报告在调研、合并与撰写全过程中，**没有打开、没有阅读、没有引用**《A Survey on Population-Based Deep Reinforcement Learning》（Weifan Long, Taixian Hou, Xiaoyi Wei, Shichao Yan, Peng Zhai, Lihua Zhang）一文，也没有打开或使用其任何指定网址、镜像、转载页、摘要页与第三方索引页；该文献及其任何转述均未作为本报告的信息来源。
> - 本报告中的算法机制、优点与局限，均来自第六节列出的原始论文、会议页面、官方文档与作者本人的独立分析；若个别缩写（ED、PSROηN、δ-Uniform FSP、PP）存在多种通行含义，已在第二节明确说明所采用的解释及其依据。
> - 本报告面向 2023 年初的时间截面；2023 年之后出现的后续工作不在本次 19 个算法的比较范围内（仅在第六节"术语与延伸阅读"中列出，供读者自行延伸）。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 3

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 136 条；相同的参考文献 0 条。

相同片段举例：`kim sastry feedback linearization vs adaptive sliding mode control for quadrotor helicopter`

**这次运行打开过 297 个地址，最多的站点**：api.crossref.org 126，api.semanticscholar.org 68，export.arxiv.org 14，api.openalex.org 14，arxiv.org 7，ieeexplore.ieee.org 7，w3.org 6，mendeley.com 5，sciencedirect.com 3，dblp.org 3，ouci.dntb.gov.ua 3，publications.eai.eu 3

**打开过的、和禁用来源同一个站点的地址**：
- https://doi.org/10.4236/ica.2013.43039
- https://ouci.dntb.gov.ua/en/?s=10.1016%2Fj.ast.2016.04.005
- https://ouci.dntb.gov.ua/en/?s=10.1109%2Ftie.2016.2552151
- https://ouci.dntb.gov.ua/en/?s=quadrotor+sliding+mode+H%E2%88%9E+control

**报告的各级标题**：

    # 四旋翼无人机控制方法技术综述（截至 2021 年 5 月）
    ## 摘要
    ## 1. 四旋翼控制问题概述
    ### 1.1 被控对象的固有难点
    ### 1.2 典型级联控制架构
    ### 1.3 评价维度
    ## 2. 控制器分类
    ### 2.1 分类的边界说明
    ### 2.2 三类控制器的总体对比
    ## 3. 各控制器的主要优点与缺点
    ### 3.1 PID（比例—积分—微分控制）
    ### 3.2 LQR（线性二次调节器）
    ### 3.3 H∞（H-无穷鲁棒控制）
    ### 3.4 反馈线性化（Feedback Linearization，含 NDI/INDI 与微分平坦）
    ### 3.5 反步法（Backstepping）
    ### 3.6 SMC（滑模控制）
    ### 3.7 MPC（模型预测控制）
    ### 3.8 自适应控制（Adaptive Control）
    ### 3.9 模糊逻辑（Fuzzy Logic）
    ### 3.10 神经网络（Neural Network，含深度学习与强化学习）
    ## 4. 性能改进策略总表
    ### 4.1 表格说明
    ### 4.2 改进策略表
    ## 5. 综合讨论与选型建议
    ### 5.1 十类控制器的横向比较
    ### 5.2 性能改进策略的共同主线
    ### 5.3 面向任务的选型建议
    ### 5.4 截至 2021 年 5 月的开放问题
    ## 参考文献
    ### 综述、平台与总体
    ### PID
    ### LQR
    ### H∞
    ### 反馈线性化、NDI/INDI 与微分平坦
    ### 反步法
    ### 滑模控制
    ### 模型预测控制
    ### 自适应控制
    ### 模糊逻辑
    ### 神经网络与学习控制

**报告开头**：

> # 四旋翼无人机控制方法技术综述（截至 2021 年 5 月）
> 
> **文档性质**：技术综述（technical survey）
> **时间范围**：截至 2021 年 5 月 31 日公开发表的期刊论文、会议论文、预印本与工程资料
> **引用方式**：正文采用“作者（年份）”标注；完整文献信息见文末“参考文献”
> 
> > **调研范围与排除声明**
> >
> > 1. 本报告只采用 2021 年 5 月 31 日（含）之前公开的文献；在此之后发表的成果（即使主题高度相关）一律未纳入，包括 2021 年 6 月及以后召开的会议论文。
> > 2. 本报告严格遵循委托方给定的文献排除清单。清单所列文献及其任何转载页、镜像页、摘要页、数据库记录页均未被访问、检索、下载或引用；排除清单也未作为任何二次引用的来源。
> > 3. 文中的性能结论均来自所引文献的标题、摘要或正文表述；“报道”“显示”“表明”一类措辞表示该结论来自原作者，而不是本报告的独立复现。
> > 4. 报告力求列举具体方法而不是用概括性词语省略；同一篇文献可能同时出现在“混合策略”和“改进策略”两栏，因为其贡献可能同时涉及两类改进。
> 
> ---
> 
> ## 摘要
> 
> 四旋翼无人机是典型的欠驱动、非线性、强耦合多变量系统：它只有四个独立控制输入（总推力与三轴力矩），却需要控制六个自由度的位置与姿态；平动必须通过姿态倾斜间接实现，气动效应、参数时变、执行器饱和与外部风扰进一步增加了控制难度。截至 2021 年 5 月，学术界与工业界已经发展出数量庞大、谱系复杂的控制方法。
> 
> 本报告按照委托要求分为两大部分：
> 
> - **第一部分**把常见四旋翼控制器划分为**线性控制**（PID、LQR、H∞）、**非线性控制**（反馈线性化、反步法、滑模控制、模型预测控制、自适应控制）与**基于学习的控制**（模糊逻辑、神经网络，包含深度强化学习与模仿学习）三类，并逐一总结每种控制器的主要优点与主要缺点。
> - **第二部分**以三列表格汇总每种控制器的**混合策略举例**（该控制器与其他控制器结合使用的具体案例）与**现有控制器改进策略举例**（通过增加算法、观测器、优化器或结构改造来改进控制器本身的案例）。
> 
> 报告共引用约 460 篇（项）截至 2021 年 5 月的文献，覆盖经典奠基工作、代表性实验验证工作以及较新的混合与改进方案。
> 
> ---
> 
> ## 1. 四旋翼控制问题概述
> 
> ### 1.1 被控对象的固有难点
> 
> 四旋翼已在巡检、测绘、农业、物流与应急救援场景广泛部署（Shakhatreh et al., 2019）。其控制困难来自以下几个方面，它们也是评价任何控制器优劣的基本出发点：
> 
> 1. **欠驱动性**：四个旋翼提供四个独立输入，而刚体有六个自由度（三个位置、三个姿态）。位置与姿态不能独立任意配置，控制器必须处理输入与输出维数不匹配的问题（Mahony et al., 2012；Emran & Najjaran, 2018）。
> 2. **强非线性与通道耦合**：推力方向随姿态旋转，姿态动力学包含陀螺力矩与惯性耦合；位置运动依赖姿态倾斜，形成“位置—姿态”串级耦合（Mahony et al., 2012）。
> 3. **参数不确定与时变**：质量随载荷与电池变化，转动惯量随挂载变化，气动系数随速度、攻角、电池电压变化（Pounds et al., 2012；Liu et al., 2016a）。
> 4. **复杂气动效应**：桨叶挥舞（blade flapping）、转子阻力（rotor drag）、地面效应、阵风与涡环状态都会

**报告结尾（含参考文献）**：

> 434. Pi, C.-H., et al. (2020). Low-level autonomous control and tracking of quadrotor using reinforcement learning. *Control Engineering Practice*, 95, 104222. https://doi.org/10.1016/j.conengprac.2019.104222
> 435. Pi, C.-H., et al. (2021). Robust quadrotor control through reinforcement learning with disturbance compensation. *Applied Sciences*, 11(7), 3257. https://doi.org/10.3390/app11073257
> 436. Song, Y., et al. (2021). Autonomous drone racing with deep reinforcement learning. arXiv:2103.08624. https://arxiv.org/abs/2103.08624
> 437. Yoo, J., et al. (2021). Hybrid reinforcement learning control for a micro quadrotor flight. *IEEE Control Systems Letters*, 5(2), 505–510. https://doi.org/10.1109/LCSYS.2020.3001663
> 438. Wang, Y., et al. (2020c). Deterministic policy gradient with integral compensator for robust quadrotor control. *IEEE Transactions on Systems, Man, and Cybernetics: Systems*, 50(10), 3665–3677. https://doi.org/10.1109/TSMC.2018.2884725
> 439. Hu, H., & Wang, Q. (2020). Proximal policy optimization with an integral compensator for quadrotor control. *Frontiers of Information Technology & Electronic Engineering*, 21(5), 777–795. https://doi.org/10.1631/FITEE.1900641
> 440. Lin, X., et al. (2019). Supplementary reinforcement learning controller designed for quadrotor UAVs. *IEEE Access*, 7, 26464–26474. https://doi.org/10.1109/ACCESS.2019.2901295
> 441. Johannink, T., et al. (2019). Residual reinforcement learning for robot control. *2019 International Conference on Robotics and Automation (ICRA)*. https://doi.org/10.1109/ICRA.2019.8794127（通用机器人）
> 442. Stingu, E., & Lewis, F. (2011). An approximate dynamic programming based controller for an underactuated 6DoF quadrotor. *2011 IEEE Symposium on Adaptive Dynamic Programming and Reinforcement Learning (ADPRL)*. https://doi.org/10.1109/ADPRL.2011.5967394
> 443. Naruta, A., et al. (2019). Continuous state and action Q-learning framework applied to quadrotor UAV control. *AIAA Scitech 2019 Forum*. https://doi.org/10.2514/6.2019-0145
> 444. Sun, D., et al. (2018). Unmanned aerial vehicles control study using deep deterministic policy gradient. *2018 IEEE Chinese Guidance, Navigation and Control Conference (CGNCC)*. https://doi.org/10.1109/GNCC42960.2018.9018682
> 445. Lopes, G. C., et al. (2018). Intelligent control of a quadrotor with proximal policy optimization reinforcement learning. *2018 Latin American Robotic Symposium (LARS/SBR/WRE)*. https://doi.org/10.1109/LARS/SBR/WRE.2018.00094
> 446. Bohn, E., et al. (2019). Deep reinforcement learning attitude control of fixed-wing UAVs using proximal policy optimization. *2019 International Conference on Unmanned Aircraft Systems (ICUAS)*. https://doi.org/10.1109/ICUAS.2019.8798254（固定翼）
> 447. Barros, G., et al. (2020). Using soft actor-critic for low-level UAV control. arXiv:2010.02293. https://arxiv.org/abs/2010.02293
> 448. Molchanov, A., et al. (2019). Sim-to-(multi)-real: Transfer of low-level robust control policies to multiple quadrotors. *2019 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*. https://doi.org/10.1109/IROS40897.2019.8967695
> 449. Loquercio, A., et al. (2020). Deep drone racing: From simulation to reality with domain randomization. *IEEE Transactions on Robotics*, 36(1), 1–14. https://doi.org/10.1109/TRO.2019.2942989
> 450. Kang, K., et al. (2019). Generalization through simulation: Integrating simulated and real data into deep reinforcement learning for vision-based autonomous flight. *2019 International Conference on Robotics and Automation (ICRA)*. https://doi.org/10.1109/ICRA.2019.8793735
> 451. Ross, S., et al. (2013). Learning monocular reactive UAV control in cluttered natural environments. *2013 IEEE International Conference on Robotics and Automation (ICRA)*. https://doi.org/10.1109/ICRA.2013.6630809
> 452. Stevsic, S., et al. (2018). Sample efficient learning of path following and obstacle avoidance behavior for quadrotors. *IEEE Robotics and Automation Letters*, 3(4), 3852–3859. https://doi.org/10.1109/LRA.2018.2856922
> 453. Goecks, V. G., et al. (2019). Efficiently combining human demonstrations and interventions for safe training of autonomous systems in real-time. *Proceedings of the AAAI Conference on Artificial Intelligence*, 33(1), 2462–2470. https://doi.org/10.1609/aaai.v33i01.33012462
> 454. Harris, C. M., et al. (2021). Imitation learning for UAS navigation in cluttered environments. *AIAA Scitech 2021 Forum*. https://doi.org/10.2514/6.2021-0452
> 455. Berkenkamp, F., Schoellig, A. P., & Krause, A. (2016). Safe controller optimization for quadrotors with Gaussian processes. *2016 IEEE International Conference on Robotics and Automation (ICRA)*. https://doi.org/10.1109/ICRA.2016.7487170
> 456. Rubí, B., Morcego, B., & Pérez, R. (2020). Deep reinforcement learning for quadrotor path following with adaptive velocity. *Autonomous Robots*, 44(7), 1337–1351. https://doi.org/10.1007/s10514-020-09951-8
> 457. Singla, A., et al. (2018). Memory-based deep reinforcement learning for obstacle avoidance in UAV with limited environment knowledge. arXiv:1811.03307. https://arxiv.org/abs/1811.03307
> 458. Xu, Y., et al. (2018). Monocular vision based autonomous landing of quadrotor through deep reinforcement learning. *2018 37th Chinese Control Conference (CCC)*. https://doi.org/10.23919/ChiCC.2018.8482830
> 459. Kooi, J. E., et al. (2021). Inclined quadrotor landing using deep reinforcement learning. arXiv:2103.09043. https://arxiv.org/abs/2103.09043
> 460. Polvara, R., et al. (2017). Autonomous quadrotor landing using deep reinforcement learning. arXiv:1709.03339. https://arxiv.org/abs/1709.03339
> 461. Camci, E., et al. (2019). End-to-end motion planning of quadrotors using deep reinforcement learning. arXiv:1909.13599. https://arxiv.org/abs/1909.13599
> 462. Wang, M., et al. (2020d). Fixed-time backstepping control of quadrotor trajectory tracking based on neural network. *IEEE Access*, 8, 177092–177102. https://doi.org/10.1109/ACCESS.2020.3027052
> 
> 
> 
> 
> 
> 

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 4

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 229 条；相同的参考文献 0 条。

相同片段举例：`kim sastry feedback linearization vs adaptive sliding mode control for quadrotor helicopter`

**这次运行打开过 269 个地址，最多的站点**：api.crossref.org 138，api.semanticscholar.org 37，doi.org 17，export.arxiv.org 15，api.openalex.org 15，w3.org 4，arxiv.org 3，core.ac.uk 2，ar5iv.labs.arxiv.org 2，repository.uaeh.edu.mx 2，mdpi.com 2，research-collection.ethz.ch 2

**打开过的、和禁用来源同一个站点的地址**：
- https://doi.org/$d
- https://doi.org/10.1007/978-3-642-15220-7_16
- https://doi.org/10.1016/0005-1098%2869%2990071-5
- https://doi.org/10.1016/0005-1098(69
- https://doi.org/10.1016/S0020-7373%2875%2980002-2
- https://doi.org/10.1016/S0020-7373(75
- https://doi.org/10.1016/S0165-0114%2898%2900159-6
- https://doi.org/10.1109/saci.2009.5136311
- https://doi.org/10.17667/riim.2015.1-2/10
- https://doi.org/10.17667/riim.2015.1-2/10.
- https://doi.org/{doi}
- https://doi.org/{ex[
- https://doi.org/{it[
- https://www.mdpi.com/2076-3417/9/23/5184
- https://www.mdpi.com/2079-9292/9/10/1735

**报告的各级标题**：

    # 四旋翼无人机（Quadrotor）控制方法技术综述（覆盖至 2021 年 5 月）
    ## 目录
    # 第一部分　控制器分类与主要优缺点总结
    ## 1.1 分类框架与总体对比
    ### 1.1.1 为什么按“线性 / 非线性 / 基于学习”三分
    #### 三点边界说明
    ### 1.1.2 十类控制器一览（分类、模型依赖、典型稳定性工具、典型验证层级）
    ### 1.1.3 十类控制器横向对比（截至 2021 年 5 月的总体判断）
    ### 1.1.4 报告阅读指南
    ### 1.1.5 通用参考（分类与建模背景，均发表于 2021 年 5 月之前）
    ## 1.2 PID（比例-积分-微分）控制
    ### 1.2.1 主要优点
    ### 1.2.2 主要缺点
    ## 1.3 LQR（线性二次调节器）
    ### 1.3.1 主要优点
    ### 1.3.2 主要缺点
    ## 1.4 H∞（H-无穷）控制
    ### 1.4.1 主要优点
    ### 1.4.2 主要缺点
    ## 1.5 Feedback Linearization（反馈线性化，含动态逆 NDI）
    ### 1.5.1 主要优点
    ### 1.5.2 主要缺点
    ## 1.6 Backstepping（反步法）
    ### 1.6.1 主要优点
    ### 1.6.2 主要缺点
    ## 1.7 SMC（滑模控制）
    ### 1.7.1 主要优点
    ### 1.7.2 主要缺点
    ## 1.8 MPC（模型预测控制）
    ### 1.8.1 主要优点
    ### 1.8.2 主要缺点
    ## 1.9 Adaptive Control（自适应控制）
    ### 1.9.1 主要优点
    ### 1.9.2 主要缺点
    ## 1.10 Fuzzy Logic（模糊逻辑控制）
    ### 1.10.1 主要优点
    ### 1.10.2 主要缺点
    ## 1.11 Neural Network（神经网络）与学习型控制
    ### 1.11.1 主要优点
    ### 1.11.2 主要缺点

**报告开头**：

> # 四旋翼无人机（Quadrotor）控制方法技术综述（覆盖至 2021 年 5 月）
> 
> > **调研范围与方法说明**：本报告覆盖截至 **2021 年 5 月（含）** 公开发表的四旋翼控制文献与工业实践，按“线性控制 / 非线性控制 / 基于学习控制”三大类组织，逐一总结 PID、LQR、H∞、Feedback Linearization、Backstepping、SMC、MPC、Adaptive Control、Fuzzy Logic、Neural Network 十类控制器的主要优点与主要缺点，并给出“控制器混合策略”与“现有控制器改进策略”两类性能改进路径。
> >
> > 调研由 8 个相互独立、互不重叠的子任务并行完成，各子任务的文献均经 Crossref / Semantic Scholar / 出版方页面核实；报告中的每条策略均标注代表文献（作者、年份、出处与链接），并尽可能注明该文献属于仿真验证还是实机飞行验证。
> >
> > **排除声明**：本次调研全程未打开、未阅读、未引用、未转述委托方明确排除的任何文献及其转载页、摘要页、镜像页、预印本页与 DOI 落地页；被排除文献的清单与禁令已完整记录在项目规则文件中，其任何结论均不构成本报告任何陈述的依据。
> 
> 
> ## 目录
> 
> - **第一部分　控制器分类与主要优缺点总结**
>   - 1.1 分类框架与总体对比（三大类划分依据、边界说明、十类控制器一览与横向对比）
>   - 1.2 PID（比例-积分-微分）控制
>   - 1.3 LQR（线性二次调节器）
>   - 1.4 H∞（H-无穷）控制
>   - 1.5 Feedback Linearization（反馈线性化，含动态逆 NDI）
>   - 1.6 Backstepping（反步法）
>   - 1.7 SMC（滑模控制）
>   - 1.8 MPC（模型预测控制）
>   - 1.9 Adaptive Control（自适应控制）
>   - 1.10 Fuzzy Logic（模糊逻辑控制）
>   - 1.11 Neural Network（神经网络）与学习型控制
> - **第二部分　性能改进策略**
>   - 2.1 性能改进策略总表（三列：控制器 / 控制器混合策略举例 / 现有控制器改进策略举例）
>   - 2.2 分控制器详细策略表（2.2 PID 至 2.11 Neural Network，每节含混合策略表、改进策略表与参考文献）
>   - 2.12 元启发式优化器横向专题（用于控制器整定与结构优化）
> 
> ---
> 
> # 第一部分　控制器分类与主要优缺点总结
> 
> ## 1.1 分类框架与总体对比
> 
> ### 1.1.1 为什么按“线性 / 非线性 / 基于学习”三分
> 
> 四旋翼（quadrotor）是欠驱动、强耦合、非线性的六自由度系统：4 个控制输入（4 个旋翼转速）要驱动 6 个自由度（三轴位置与三轴姿态），
> 俯仰与滚转力矩必须通过姿态倾斜来间接产生水平加速度。因此控制器的分类通常沿“对模型的依赖方式”与“稳定性论证工具”两条线索展开：
> 
> 1. **线性控制（Linear control）**：在悬停或小扰动平衡点附近把非线性模型线性化，用线性系统理论设计控制器。
>    代表：**PID**、**LQR**（以及同族的 LQG、极点配置、增益调度）。核心假设是“工作点附近线性模型足够准”。
> 2. **非线性控制（Nonlinear control）**：直接基于非线性模型（或直接在非线性模型上论证稳定性），使用 Lyapunov 方法、滑模面方法与滚动时域优化方法

**报告结尾（含参考文献）**：

> 97. Clavera, I., Nagabandi, A., Liu, S., Fearing, R. S., Abbeel, P., Levine, S., & Finn, C. (2019). *Learning to Adapt in Dynamic, Real-World Environments through Meta-Reinforcement Learning*. ICLR 2019；arXiv:1803.11347. https://arxiv.org/abs/1803.11347
> 98. Aswani, A., Gonzalez, H., Sastry, S. S., & Tomlin, C. (2013). *Provably safe and robust learning-based model predictive control*. Automatica, 49(5), 1216–1226. https://doi.org/10.1016/j.automatica.2013.02.003
> 99. Bouffard, P., Aswani, A., & Tomlin, C. (2012). *Learning-based model predictive control on a quadrotor: Onboard implementation and experimental results*. 2012 IEEE International Conference on Robotics and Automation (ICRA). https://doi.org/10.1109/ICRA.2012.6225035
> 100. Hewing, L., Wabersich, K. P., Menner, M., & Zeilinger, M. N. (2020). *Learning-Based Model Predictive Control: Toward Safe Learning in Control*. Annual Review of Control, Robotics, and Autonomous Systems, 3, 269–296. https://doi.org/10.1146/annurev-control-090419-075625
> 101. Ostafew, C. J., Schoellig, A. P., Barfoot, T. D., & Collier, J. (2015). *Learning-based nonlinear model predictive control to improve vision-based mobile robot path tracking*. Journal of Field Robotics, 33(1), 133–152. https://doi.org/10.1002/rob.21587
> 102. Li, S., Wang, Y., Tan, J., & Zheng, Y. (2016). *Adaptive RBFNNs/integral sliding mode control for a quadrotor aircraft*. Neurocomputing, 216, 126–134. https://doi.org/10.1016/j.neucom.2016.07.033
> 103. Shen, W., & Li, Z. (2019). *Backstepping Sliding Mode RBF Network Adaptive Control for Quadrotor UAV*. 2019 Chinese Automation Congress (CAC). https://doi.org/10.1109/CAC48633.2019.8996354
> 104. Mohd Basri, M. A. (2018). *Trajectory Tracking Control of Autonomous Quadrotor Helicopter Using Robust Neural Adaptive Backstepping Approach*. Journal of Aerospace Engineering, 31(2). https://doi.org/10.1061/(ASCE)AS.1943-5525.0000804
> 105. Guettal, L., Chelihi, A., Touba, M. M., & Glida, H. E. (2020). *Neural Network-based Adaptive Backstepping Controller for UAV Quadrotor system*. 2020 1st International Conference on Communications, Control Systems and Signal Processing (CCSSP). https://doi.org/10.1109/CCSSP49278.2020.9151813
> 106. Nicol, C., Macnab, C. J. B., & Ramirez-Serrano, A. (2011). *Robust adaptive control of a quadrotor helicopter*. Mechatronics, 21(6), 927–938. https://doi.org/10.1016/j.mechatronics.2011.02.007
> 107. Liu, M., Dong, X., Li, Q., & Ren, Z. (2018). *Model Reference Adaptive Control of a Quadrotor UAV based on RBF Neural Networks*. 2018 IEEE CSAA Guidance, Navigation and Control Conference (GNCC). https://doi.org/10.1109/GNCC42960.2018.9019021
> 108. Bellahcene, Z., Bouhamida, M., Denai, M., & Assali, K. (2020 年 11 月在线发表). *Adaptive Neural Network-Based Robust H∞ Tracking Control of a Quadrotor UAV Under Wind Disturbances*. International Journal of Automation and Control, 15(2). https://doi.org/10.1504/IJAAC.2021.111747
> 109. Rezazadeh, S., Ardestani, M. A., & Sadeghi, P. (2013). *Optimal attitude control of a quadrotor UAV using Adaptive Neuro-Fuzzy Inference System (ANFIS)*. 2013 3rd International Conference on Control, Instrumentation, and Automation (ICCIA). https://doi.org/10.1109/ICCIAutom.2013.6912838
> 110. Housny, H., Chater, E., & El Fadil, H. (2020). *PSO-based ANFIS for quadrotor system trajectory-tracking control*. 2020 1st International Conference on Innovative Research in Applied Science, Engineering and Technology (IRASET). https://doi.org/10.1109/IRASET48871.2020.9092015
> 111. Housny, H., Chater, E., & El Fadil, H. (2020). *Multi Closed-loop Adaptive Neuro-Fuzzy Inference System for Quadrotor Position Control*. Advances in Science, Technology and Engineering Systems Journal, 5(5), 570–576. https://doi.org/10.25046/aj050565
> 112. Lin, Q., Cai, Z., Wang, Y., & Yang, J. (2013). *Adaptive Flight Control Design for Quadrotor UAV Based on Dynamic Inversion and Neural Networks*. 2013 Third International Conference on Instrumentation, Measurement, Computer, Communication and Control (IMCCC). https://doi.org/10.1109/IMCCC.2013.326
> 113. Wang, Y., Zhang, H., & Han, D. (2016). *Neural network adaptive inverse model control method for quadrotor UAV*. 2016 35th Chinese Control Conference (CCC). https://doi.org/10.1109/CHICC.2016.7553921
> 114. Lee, B., Lee, H., & Tahk, M. (2013). *Analysis of adaptive control using on-line neural networks for a quadrotor UAV*. 2013 13th International Conference on Control, Automation and Systems (ICCAS). https://doi.org/10.1109/ICCAS.2013.6704240
> 115. Boudjedir, H., Bouhali, O., & Rizoug, N. (2014). *Adaptive neural network control based on neural observer for quadrotor unmanned aerial vehicle*. Advanced Robotics, 28(17), 1151–1164. https://doi.org/10.1080/01691864.2014.913498
> 116. Doukhi, O., & Lee, D. J. (2019). *Neural Network-based Robust Adaptive Certainty Equivalent Controller for Quadrotor UAV with Unknown Disturbances*. International Journal of Control, Automation and Systems, 17, 2365–2374. https://doi.org/10.1007/s12555-018-0720-7
> 117. Pouilly-Cathelain, M., Feyel, P., Duc, G., & Sandou, G. (2019). *Enhancing Neural Network Prediction against Unknown Disturbances with Neural Network Disturbance Observer*. Proceedings of the 16th International Conference on Informatics in Control, Automation and Robotics (ICINCO). https://doi.org/10.5220/0007831102100219
> 118. Punjani, A., & Abbeel, P. (2015). *Deep learning helicopter dynamics models*. 2015 IEEE International Conference on Robotics and Automation (ICRA). https://doi.org/10.1109/ICRA.2015.7139643
> 119. Panizza, P., Riccardi, F., & Lovera, M. (2015). *Black-box and grey-box identification of the attitude dynamics for a variable-pitch quadrotor*. IFAC-PapersOnLine, 48(9), 187–192. https://doi.org/10.1016/j.ifacol.2015.08.060
> 120. Stingu, E., & Lewis, F. L. (2011). *An approximate Dynamic Programming based controller for an underactuated 6DoF quadrotor*. 2011 IEEE Symposium on Adaptive Dynamic Programming and Reinforcement Learning (ADPRL). https://doi.org/10.1109/ADPRL.2011.5967394
> 121. Nguyen, D. H., & Widrow, B. (1990). *Neural networks for self-learning control systems*. IEEE Control Systems Magazine, 10(3), 18–23. https://doi.org/10.1109/37.55119
> 122. Nguyen, D., & Widrow, B. (1990). *Improving the learning speed of 2-layer neural networks by choosing initial values of the adaptive weights*. 1990 IJCNN International Joint Conference on Neural Networks. https://doi.org/10.1109/IJCNN.1990.137819
> 123. Wolpert, D. H., & Macready, W. G. (1997). *No free lunch theorems for optimization*. IEEE Transactions on Evolutionary Computation, 1(1), 67–82. https://doi.org/10.1109/4235.585893
> 
> **核查说明（避免编造，特此记录）**：
> 
> - 关于「Hwang 及其合作者的工作」：本次检索确认并采用的是 Hwangbo、Sa、Siegwart 与 Hutter（2017，IEEE Robotics and Automation Letters）的四旋翼强化学习控制工作［9］，其链接与元数据已核实；在 2021 年 5 月（含）以前的时间窗内，未检索到可核实的、由姓氏为 Hwang 的作者发表的四旋翼学习型控制专门论文，故未写入任何此类条目。
> - 关于「Tan 与 Kumar 的强化学习姿态控制」：未能核实到符合作者组合与主题的公开文献；时间窗内可核实的四旋翼（无人机）姿态强化学习代表工作是 Hwangbo、Sa、Siegwart 与 Hutter（2017）［9］以及 Koch、Mancuso、West 与 Bestavros（2019，ACM Transactions on Cyber-Physical Systems）［15］，本部分据此撰写，未按未核实线索编造条目。
> - 关于「Nguyen 与 Widrow 的 CMAC/神经网络控制传统」：已核实并引用 Nguyen 与 Widrow（1990，IEEE Control Systems Magazine）［121］与 Nguyen 与 Widrow（1990，IJCNN）［122］，以及 CMAC 的原始文献 Albus（1975）［11］。
> - 关于「Levine 与 Koltun 的引导策略搜索」：已核实并引用 Levine 与 Koltun（2013，ICML，PMLR 28(3):1–9）［75］，用于强化学习与 MPC 结合的引导样本思路。
> - 时间范围：全部条目的公开发表时间均不晚于 2021 年 5 月；其中 Bellahcene、Bouhamida、Denai 与 Assali 的论文按出版方记录于 2020 年 11 月 17 日在线发表；Fessi、Rezk 与 Bouallègue 的论文在 Crossref 的登记时间为 2021 年 4 月 21 日；Shamshirgaran、Javidi 与 Simon 的两篇论文为 2021 年 5 月 arXiv 预印本（会议版在时间窗之后，故按预印本标注）；Song、Steinweg、Kaufmann 与 Scaramuzza 的论文为 2021 年 3 月 arXiv 预印本。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 5

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里出现了来源文章的标题；与来源正文相同的 12 词片段 162 条；相同的参考文献 0 条。

相同片段举例：`kim sastry feedback linearization vs adaptive sliding mode control for quadrotor helicopter`

**这次运行打开过 517 个地址，最多的站点**：api.crossref.org 293，export.arxiv.org 50，api.semanticscholar.org 28，arxiv.org 17，sciencedirect.com 9，ar5iv.labs.arxiv.org 9，semanticscholar.org 7，ieeexplore.ieee.org 7，mdpi.com 6，doi.org 4，api.openalex.org 4，shodhganga.inflibnet.ac.in 3

**打开过的、和禁用来源同一个站点的地址**：
- https://doi.org/
- https://ouci.dntb.gov.ua/en/works/42k3bqml/
- https://ouci.dntb.gov.ua/en/works/735wDNol/
- https://ouci.dntb.gov.ua/en/works/7qwpYrBl/
- https://www.mdpi.com/2076-3417/10/6/2064
- https://www.mdpi.com/2076-3417/9/23/5184
- https://www.mdpi.com/2079-9292/10/18/2218
- https://www.mdpi.com/2218-6581/9/1/8
- https://www.mdpi.com/2504-446X/4/3/42
- https://www.mdpi.com/2504-446X/5/2/37

**报告的各级标题**：

    # 四旋翼无人机（Quadrotor）控制方法技术综述
    ## 执行摘要（Executive Summary）
    ## 第一部分　控制器分类与优缺点总结
    ### 1.1 分类框架
    ### 1.2 PID（比例-积分-微分）
    ### 1.3 LQR（线性二次型调节器）
    ### 1.4 H∞（H-无穷）
    ### 1.5 Feedback Linearization（反馈线性化 / 动态逆）
    ### 1.6 Backstepping（反步法）
    ### 1.7 SMC（滑模控制）
    ### 1.8 MPC（模型预测控制）
    ### 1.9 Adaptive Control（自适应控制）
    ### 1.10 Fuzzy Logic（模糊逻辑控制）
    ### 1.11 Neural Network（神经网络控制）
    ### 1.12 十种控制器横向对比总表
    ## 第二部分　十种控制器性能改进策略总表
    ### 2.1 表格使用说明
    ### 2.2 性能改进策略总表
    ### 2.3 表格要点速览（横向规律）
    ### 2.4 经核验的"研究空白"与"负面结果"清单
    ## 第三部分　参考文献
    ### 3.1 四旋翼建模、平台与总体背景
    ### 3.2 线性控制：PID、LQR、H∞
    ### 3.3 非线性控制：反馈线性化、反步法、滑模控制、MPC
    ### 3.4 自适应控制
    ### 3.5 模糊逻辑控制
    ### 3.6 神经网络与强化学习控制
    ### 3.7 控制理论工具与教科书
    ## 附：报告边界与可靠性说明

**报告开头**：

> # 四旋翼无人机（Quadrotor）控制方法技术综述
> 
> **覆盖时间范围**：公开文献截至 **2021 年 5 月**（部分 2021 年 5 月之后的工作仅在与梳理脉络直接相关时被提及，并会明确标注）。
> 
> **报告结构**
> 
> - **第一部分**：控制器分类（线性控制 / 非线性控制 / 基于学习的控制）与十种控制器的优缺点总结。
> - **第二部分**：十种控制器的性能改进策略总表（三列：控制器 / 控制器混合策略举例 / 现有控制器改进策略举例）。
> 
> **关于本报告的一则声明**：本报告在研究与撰写过程中**未查阅、未引用**文献《A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers》（Rupal Roy、Maidul Islam、Nafiz Sadman、M. A. Parvez Mahmud、Kishor Datta Gupta、Md Manjurul Ahsan）及其任何转载页、摘要页、镜像页与 DOI 落地页。该文献的结论、数据与表述均未进入本报告。本报告的所有内容来自下列独立检索到的公开文献与教科书知识。
> 
> ---
> 
> ## 执行摘要（Executive Summary）
> 
> **一、分类与定位。** 四旋翼是欠驱动、强耦合、静不稳定的非线性系统——4 个旋翼转速要同时决定 6 个自由度，俯仰/滚转力矩同时决定水平加速度。所有控制器的优劣都必须放在这一约束下理解。本报告按控制律的数学基础把常见控制器分为三类：
> 
> - **线性控制**（PID、LQR、H∞）：在悬停点线性化后设计，靠增益调度覆盖包线。**PID 模型依赖最低、LQR 系统性最强、H∞ 鲁棒性有定量保证**；三者共同的短板是硬约束、强非线性与大幅参数摄动。
> - **非线性控制**（反馈线性化、反步法、SMC、MPC、自适应控制）：直接用非线性模型设计，用 Lyapunov 方法或滚动优化构造闭环性质。**SMC 对匹配不确定性具有不变性，MPC 是唯一能系统处理硬约束的方法，自适应控制是唯一能在线适应参数变化且有稳定性证明的方法**；共同代价是模型依赖、计算量与调参复杂度上升。
> - **基于学习的控制**（模糊逻辑、神经网络，含强化学习分支）：不（完全）依赖解析模型。**模糊逻辑可解释、可编码专家经验；神经网络具备万能逼近与端到端感知-控制能力**；两者本体都缺乏稳定性/约束保证，工程落地的主流做法是用它们去补偿一个经典控制器（残差学习、增益整定、未知项逼近），而不是完全取代它。
> 
> **二、十种控制器的核心权衡。** 详见 1.2–1.11 与 1.12 的横向对比总表。一句话概括各自最致命的问题：PID —— 增益固定，无法覆盖全包线且无约束处理；LQR —— 依赖线性模型与全状态反馈，LQG 无自动鲁棒裕度；H∞ —— 保守、控制器阶数高、加权函数依赖专家经验；反馈线性化 —— 模型逆误差被放大，抵消有用非线性并可出现奇异与不稳定零动态；反步法 —— "微分爆炸"且要求严格反馈结构；SMC —— 抖振，且边界层法以牺牲不变性为代价；MPC —— 计算量大、模型敏感、认证困难；自适应控制 —— 参数漂移与持续激励条件，且只能处理"参数未知"而非"结构未知"；模糊逻辑 —— 规则爆炸且无稳定性证明；神经网络 —— 黑箱、需大量数据、分布外无保证、Sim-to-Real 鸿沟。
> 
> **三、改进策略的两条主线与三大

**报告结尾（含参考文献）**：

> 
> - Krstić, M., Kanellakopoulos, I., Kokotović, P. V. *Nonlinear and Adaptive Control Design.* Wiley, 1995.
> - Slotine, J.-J. E., Li, W. *Applied Nonlinear Control.* Prentice Hall, 1991.
> - Khalil, H. K. *Nonlinear Systems* (3rd ed.). Prentice Hall, 2002.
> - Farrell, J. A., Polycarpou, M., Sharma, M., Dong, W. *Command filtered backstepping.* IEEE Transactions on Automatic Control, 54(6), 2009 (ACC 2008).
> - Swaroop, D., Hedrick, J. K., Yip, P. P., Gerdes, J. C. *Dynamic surface control for a class of nonlinear systems.* IEEE Transactions on Automatic Control, 45(10), 2000.
> - Tee, K. P., Ge, S. S., Tay, E. H. *Barrier Lyapunov functions for the control of output-constrained nonlinear systems.* Automatica, 45(4), 2009.
> - Bechlioulis, C. P., Rovithakis, G. A. *Robust adaptive control of feedback linearizable MIMO nonlinear systems with prescribed performance.* IEEE Transactions on Automatic Control, 53(9), 2008.
> - Utkin, V. I. *Sliding Modes in Control and Optimization.* Springer, 1992.
> - Edwards, C., Spurgeon, S. *Sliding Mode Control: Theory and Applications.* Taylor & Francis, 1998.
> - Shtessel, Y., Edwards, C., Fridman, L., Levant, A. *Sliding Mode Control and Observation.* Birkhäuser, 2014.
> - Åström, K. J., Hägglund, T. *PID Controllers: Theory, Design, and Tuning* (2nd ed.). ISA, 1995.
> - Åström, K. J., Hägglund, T. *Automatic Tuning of PID Controllers.* ISA, 1988.
> - Ziegler, J. G., Nichols, N. B. *Optimum settings for automatic controllers.* Transactions of the ASME, 64, 1942.
> - Podlubny, I. *Fractional-order systems and PI^λD^μ controllers.* IEEE Transactions on Automatic Control, 44(1), 1999.
> - Monje, C. A., Chen, Y., Vinagre, B. M., Xue, D., Feliu-Batlle, V. *Fractional-order Systems and Controls: Fundamentals and Applications.* Springer, 2010.
> - Anderson, B. D. O., Moore, J. B. *Optimal Control: Linear Quadratic Methods.* Prentice Hall, 1990.
> - Zhou, K., Doyle, J. C., Glover, K. *Robust and Optimal Control.* Prentice Hall, 1996.
> - Skogestad, S., Postlethwaite, I. *Multivariable Feedback Control: Analysis and Design* (2nd ed.). Wiley, 2005.
> - Rawlings, J. B., Mayne, D. Q., Diehl, M. M. *Model Predictive Control: Theory, Computation, and Design* (2nd ed.). Nob Hill Publishing, 2017.
> - Camacho, E. F., Bordons, C. *Model Predictive Control* (2nd ed.). Springer, 2007.
> - Bhat, S. P., Bernstein, D. S. *Finite-time stability of continuous autonomous systems.* SIAM Journal on Control and Optimization, 38(3), 2000.
> 
> ---
> 
> ## 附：报告边界与可靠性说明
> 
> 1. **时间边界**：报告主体覆盖至 **2021 年 5 月**。为保持叙述完整，个别背景性教科书与经典理论文献不受此限制。
> 2. **来源独立性**：所有文献线索均来自本报告撰写过程中独立执行的公开检索与公开教科书知识。被明确禁止查阅的那篇综述及其全部镜像、摘要与 DOI 页面**从未被打开**，其内容**未被使用**。
> 3. **引用粒度与核验程度**：第二部分表格与第三部分中的文献线索以"可追溯"为目标给出（作者 + 标题 + 年份 + 会议/期刊；标注卷期页码者已核验到卷期页）。其中**少数条目为"仅标题级"线索**（例如 "Neuro-adaptive augmented dynamic inversion controller for quadrotors"（IFAC-PapersOnLine 2016）、"Observer-based adaptive fuzzy backstepping … Li-ion battery"（JIRS 2016）、"Comparison of optimization approaches on LQR design for trajectory tracking of a quadrotor"、"KNODE-MPC"、"Mohajerin & Waslander 2018 的会议出处"），这些条目未能检索到完整作者列表或 DOI，**引用前请自行二次确认**。其余条目均通过 Crossref 元数据、出版方落地页或机构仓储核验。
> 4. **检索环境的客观限制**：在本报告的检索环境中，IEEE Xplore、ScienceDirect、Springer、Wiley、MDPI 与 Hindawi 的正文页面普遍返回 HTTP 403，且抓取工具不接受 PDF。因此绝大多数文献是通过 **Crossref REST API 的出版方存缴元数据**核验的（标题、作者、年份、会议/期刊、DOI 均为权威记录），但**其技术主张并非全部读自原文**；优势/劣势陈述在无原文可读时，来自标准非线性控制理论并锚定到所引文献。这一限制不影响分类、优缺点与方法清单的正确性，但会影响对个别论文具体数值结论的复述精度。
> 5. **"已验证"与"可移植"的区分**：凡标注「**注意**：截至 2021 年 5 月未见四旋翼专门验证」的条目，均属于来自通用控制理论、可移植到四旋翼但当时尚无四旋翼专门成果的方法。第二部分 2.4 节给出了完整的空白清单。
> 6. **研究方法与核验层级**：本报告的文献工作由三路并行的定向检索构成（线性控制族：PID/LQR/H∞；非线性控制族：反馈线性化/反步/SMC/MPC；自适应与学习族：自适应/模糊/神经网络/强化学习）。三路均以 **Crossref REST API 的出版方存缴元数据** 与 **arXiv API** 为主要核验手段，辅以少量可全文获取的开放获取综述（Zulu & John 2014；Idrissi 等（2022）；Abdelmaksoud 等（2020））。每一路都对「看似显然但实际不存在」的组合做了**定向的负面检索**，结果汇总于 2.4 节。三路检索均**未打开**被禁止查阅的那篇综述及其任何镜像。
> 7. **"详尽性"取舍**：本报告刻意避免使用"等"字省略任何一类改进策略；同一思想在不同控制器下的不同实现（例如"自适应"在 PID 上是增益自整定、在反步法上是参数更新律、在滑模上是增益自适应）被分别列出，以便逐条对照。
> 

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 6

**题目**：Legal Research on Traffic Accident Liability for German Autonomous Vehicles（Crime & Law）

**禁用的来源文章**：Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China

- https://www.mdpi.com/2032-6653/15/7/305
- https://www.mdpi.com/2032-6653/15/7/305/pdf
- https://www.mdpi.com/2032-6653/15/7/305/html
- https://www.mdpi.com/2032-6653/15/7/305/xml
- https://www.researchgate.net/publication/382225455_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_of_the_German_Legislation_for_China
- https://www.researchgate.net/publication/382400472_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_from_the_German_Legislation_for_China/download

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里出现了来源文章的标题；与来源正文相同的 12 词片段 11 条；相同的参考文献 0 条。

相同片段举例：`distribution of the burden of proof in autonomous driving tort cases implications`

**这次运行打开过 522 个地址，最多的站点**：buzer.de 77，web.archive.org 51，boe.es 42，dejure.org 41，gesetze-im-internet.de 23，eur-lex.europa.eu 19，bundesrat.de 12，dserver.bundestag.de 11，de.wikipedia.org 10，lorenz.userweb.mwn.de 9，bundesgerichtshof.de 9，europarl.europa.eu 8

**打开过的、和禁用来源同一个站点的地址**：
- https://www.mdpi.com

**报告的各级标题**：

    # 德国 L3 及以上自动驾驶汽车交通事故责任研究报告
    ## 一、结论速览
    ## 二、规范框架与基本概念
    ### 2.1 自动化等级在德国法上的对应概念
    ### 2.2 立法沿革（截至 2024 年中期）
    ### 2.3 责任体系总览
    ## 三、驾驶员（Fahrzeugführer）的责任
    ### 3.1 谁是“驾驶员”：`§ 1a Abs. 4 StVG`
    ### 3.2 法律依据与责任类型
    #### （1）`§ 18 Abs. 1 StVG`：危险责任框架下的“无过错免责”
    #### （2）`§ 823 BGB`：一般过错侵权责任
    #### （3）注意义务的来源：`§ 1b StVG` 与 StVO
    ### 3.3 受害人须证明什么？
    ### 3.4 驾驶员可以通过证明什么来免责？
    ### 3.5 L3 场景中的注意义务标准：几点归纳
    ### 3.6 刑事与秩序法侧面（简要）
    ## 四、车辆持有人（Halter）的责任
    ### 4.1 “持有人”是谁？
    ### 4.2 `§ 7 StVG`：无过错危险责任
    ### 4.3 免责：只有“不可抗力”（höhere Gewalt）
    ### 4.4 与驾驶员责任的区别
    ### 4.5 举证责任规则
    ### 4.6 责任限额：`§ 12 StVG`
    ### 4.7 L4 无人驾驶、技术监督与持有人的加重义务
    #### （1）自主驾驶的基本结构
    #### （2）技术监督（Technische Aufsicht）
    #### （3）持有人的加重义务
    #### （4）数据与受害人的知情权
    ### 4.8 强制保险、直接请求权与追偿
    ## 五、生产者 / 制造商的责任
    ### 5.1 术语澄清：Produzent、Hersteller、Produzentenhaftung、Produkthaftung
    ### 5.2 轨道 A：Produzentenhaftung（生产者侵权责任，`§ 823 BGB`）
    #### （1）法律依据
    #### （2）归责原则：过错责任 + 举证责任倒置
    #### （3）缺陷类型与相应义务
    #### （4）赔偿范围与时效
    #### （5）`§ 831 BGB` 的角色
    ### 5.3 轨道 B：ProdHaftG 产品责任（无过错责任）
    #### （1）沿革与性质
    #### （2）构成要件

**报告开头**：

> # 德国 L3 及以上自动驾驶汽车交通事故责任研究报告
> 
> **信息截止：2024 年中期**
> 
> > **研究说明**
> > 1. 本报告依据德国联邦法律（StVG、BGB、ProdHaftG、PflVG、VVG、AFGBV）、联邦议院立法材料（BT-Drs.）、联邦参议院意见（BT-Drs. 19/28178 等）、法院判例与学术文献整理，供研究参考，不构成法律意见。责任认定高度依赖个案事实（尤其是事故数据、系统状态与接管过程）。
> > 2. 按委托要求，本报告**未访问、未引用**《Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China》（Zhihua Chen、Qianyi Cai、Hanbing Wei）一文及其任何 MDPI / ResearchGate 页面。
> 
> ---
> 
> ## 一、结论速览
> 
> 1. **德国没有为自动驾驶单独创设一套全新的民事责任制度**，而是在既有三层责任体系上作局部调整：
>    - **驾驶员（Fahrzeugführer）**：`§ 18 StVG` 的“危险责任 + 无过错免责”结构（过错被推定，驾驶员须反证自己无过错），以及 `§ 823 BGB` 的一般过错侵权责任；
>    - **车辆持有人（Halter）**：`§ 7 StVG` 的无过错危险责任（Gefährdungshaftung），只有“不可抗力”（höhere Gewalt）才能免责；
>    - **生产者 / 制造商（Produzent / Hersteller）**：两条轨道——`§ 823 BGB` 判例法上的**生产者侵权责任**（Produzentenhaftung，过错责任 + 判例确立的举证责任倒置）与 `ProdHaftG` 的**无过错产品责任**（Produkthaftung）。
> 2. **受害人的第一顺位保护来自持有人责任与强制责任保险**：受害人只需证明“机动车运行（Betrieb）中造成损害 + 因果关系”，无须证明过错；并可直接起诉持有人的责任保险人（`§ 115 VVG`）。保险人赔付后，可依 `§ 86 VVG` 向制造商追偿，从而在“保险人—制造商”之间完成最终风险分配。
> 3. **L3 场景下，激活自动化功能的人仍是“驾驶员”**（`§ 1a Abs. 4 StVG`）。驾驶员的免责核心是证明自己**无过错**（`§ 18 Abs. 1 S. 2 StVG`）：只要其遵守 `§ 1b StVG` 的“保持感知准备（wahrnehmungsbereit）+ 及时接管（unverzüglich übernehmen）”义务，且不存在其他过错，即可免责。若事故完全源于系统故障，通常由持有人（及其保险人）先向受害人赔付，再向制造商追偿。
> 4. **制造商两条责任轨道的核心区别在归责原则与举证责任**：
>    - **Produzentenhaftung（§ 823 BGB）**：本质是过错责任，但德国联邦最高法院（BGH）通过“Hühnerpest”判决（BGHZ 51, 91）把“不存在客观义务违反 + 不存在过错”的**举证责任倒置**给制造商；赔偿**不受** StVG 限额限制，可覆盖产品自身损害（weiterfressender Mangel）与精神损害。
>    - **ProdHaftG 产品责任**：无过错（危险责任），免责事由

**报告结尾（含参考文献）**：

> 
> - BT-Drs. 18/11300（2017 年政府草案及理由）：[dserver.bundestag.de](https://dserver.bundestag.de/btd/18/113/1811300.pdf)（本报告经 [Internet Archive 快照](https://web.archive.org/web/2023id_/https://dserver.bundestag.de/btd/18/113/1811300.pdf) 读取）
> - BT-Drs. 19/27439（2021 年政府草案及理由）：[dserver.bundestag.de](https://dserver.bundestag.de/btd/19/274/1927439.pdf)（本报告经 [Internet Archive 快照](https://web.archive.org/web/2021id_/https://dserver.bundestag.de/btd/19/274/1927439.pdf) 读取）
> - BT-Drs. 19/28178（联邦参议院对 2021 年草案的立场与联邦政府回应）：[PDF](https://www.heise.de/downloads/18/3/0/8/6/4/4/3/1928178.pdf)
> - BT-Drs. 18/11776（2017 年交通委员会 Beschlussempfehlung und Bericht，含各党团声明）
> - BT-Drs. 19/29875（2021 年交通委员会 Beschlussempfehlung und Bericht，含对 `§ 1g Abs. 7` 的说明与少数派决议动议）
> - 2021 年 5 月 3 日联邦议院交通与数字基础设施委员会第 111 次会议听证记录（专家意见，含 VDV、GDV 等）：[bundestag.de](https://www.bundestag.de/resource/blob/842458/eb8d013a6c19c82373e147761c774b74/111-Protokoll-03-05-2021-OeA-data.pdf)
> 
> **判例与研究文献**
> 
> - BGH, Urt. v. 26.11.1968 – VI ZR 212/66 = BGHZ 51, 91（Hühnerpest）：[判决全文（转录）](http://lorenz.userweb.mwn.de/urteile/bghz51_91.htm)
> - BGH, Urt. v. 24.11.1976 – VIII ZR 137/75 = BGHZ 67, 359（Schwimmerschalter）：[判决全文（转录）](http://lorenz.userweb.mwn.de/urteile/bghz67_359.htm)
> - BGH, Urt. v. 02.02.1999 – VI ZR 392/97 = NJW 1999, 1028：[dejure](https://dejure.org/dienste/vernetzung/rechtsprechung?Text=NJW+1999+1028)
> - BGH, Urt. v. 16.06.2009 – VI ZR 107/08 = BGHZ 181, 253（发展风险与倒置的限制）：[判决全文（转录）](http://lorenz.userweb.mwn.de/urteile/vizr107_08.htm)
> - BGH, Urt. v. 25.05.2020 – VI ZR 252/19（柴油案；EG-FGV 非 `§ 823 Abs. 2 BGB` 保护法）
> - BGHZ 99, 167；BGHZ 105, 346（官方检验不产生产品合规推定）
> - OLG Düsseldorf, Urt. v. 12.03.2020 – 5 U 110/19（EG-FGV 非保护法）：[dejure](https://dejure.org/dienste/vernetzung/rechtsprechung?Aktenzeichen=5%20U%20110%2f19&Datum=12.03.2020&Gericht=OLG%20D%fcsseldorf)
> - BMWK/Fraunhofer-Gesellschaft, *Hochautomatisiertes Fahren auf Autobahnen – Industriepolitische Schlussfolgerungen*：[PDF](https://www.bmwk.de/Redaktion/DE/Downloads/H/hochautomatisiertes-fahren-auf-autobahnen.pdf?__blob=publicationFile&v=1)（责任法部分见第 338–350 页）
> - Sabine Gless / Ruth Janal, *Hochautomatisiertes und autonomes Autofahren – Risiko und rechtliche Verantwortung*, JRR 2016, 561 ff.：[PDF](https://ius.unibas.ch/fileadmin/user_upload/ius/09_Upload_Personenprofile/01_Professuren/Gless_Sabine/Gless_Janal_Juristische_Rundschau__Hochautomatisiertes_und_autonomes_Autofahren_-_Risiko_und_rechtliche_Verantwortung.pdf)
> - Prütting/Gehrlein, ZPO-Kommentar, § 286 Rn. 74（Laumen）：[Haufe 摘录](https://www.haufe.de/id/kommentar/pruettinggehrlein-zpo-kommentar-zpo-286-zpo-frei-a-produzentenhaftung-HI17014069.html)
> 
> **欧盟法文件（附官方公报出处；本报告在无法访问 EUR-Lex 时以西班牙官方公报 BOE 转载的官方公报文本核对）**
> 
> - UNECE Regulation No. 157 (ALKS)：OJ L 82, 9.3.2021, p. 75–137；CELEX 42021X0389；[BOE 官方转载](https://www.boe.es/buscar/doc.php?id=DOUE-L-2021-80297)
> - Commission Delegated Regulation (EU) 2022/1398（将 R157/R155 纳入 Reg. 2019/2144 附件二）：OJ L 213, 16.8.2022, p. 1–12；CELEX 32022R1398；[BOE 官方转载](https://www.boe.es/buscar/doc.php?id=DOUE-L-2022-81237)
> - Regulation (EU) 2019/2144（机动车一般安全母法）：OJ L 325, 16.12.2019, p. 1；CELEX 32019R2144；[BOE 官方转载](https://www.boe.es/buscar/doc.php?id=DOUE-L-2019-81951)
> - Commission Delegated Regulation (EU) 2022/545（EDR）：OJ L 107, 6.4.2022, p. 18–23；CELEX 32022R0545；[BOE 官方转载](https://www.boe.es/buscar/doc.php?id=DOUE-L-2022-80544)
> - Commission Implementing Regulation (EU) 2022/1426（ADS 型式批准）：OJ L 221, 26.8.2022, p. 1–64；CELEX 32022R1426；[BOE 官方转载](https://www.boe.es/buscar/doc.php?id=DOUE-L-2022-81263)
> - Regulation (EU) 2024/1689 (AI Act)：OJ L, 12.7.2024, p. 1–144；CELEX 32024R1689；[BOE 官方转载](https://www.boe.es/buscar/doc.php?id=DOUE-L-2024-81079)
> - Directive (EU) 2024/2853（新产品责任指令）：OJ L, 18.11.2024, p. 1–22；CELEX 32024L2853；[BOE 官方转载](https://www.boe.es/buscar/doc.php?id=DOUE-L-2024-81701)
> - Regulation (EU) 2023/2854 (Data Act)：OJ L, 22.12.2023, p. 1–71；CELEX 32023R2854；[BOE 官方转载](https://www.boe.es/buscar/doc.php?id=DOUE-L-2023-81895)
> 
> > **资料可得性说明**：本报告撰写环境无法访问 `gesetze-im-internet.de`、`bundesgerichtshof.de` 与 `eur-lex.europa.eu` 的完整页面，故德国法条文主要经由 buzer.de（tagaktuell konsolidiert）核对，判例主要经由大学网页转录与 dejure.org 核对，立法材料经由 Bundestag dserver 的 Internet Archive 快照核对，欧盟法条文经由 BOE 转载的官方公报文本核对。所有关键条文与判决要旨均在正文中给出德文原文。**2024 年中期之后才通过/生效的欧盟文件（AI Act 的适用期、新产品责任指令）已在正文中明确标注。**
> >
> > **文本版本提示**：buzer.de 展示的是现行（查询时）文本。本报告涉及自动驾驶的 `§§ 1a–1l StVG`、`§ 12 StVG`、`§ 63a StVG` 等，均以 **2017 年第八次 StVG 修改法**与 **2021 年《自动驾驶法》**的条文文本为准（即 2024 年中期有效的版本）；`§§ 7, 17, 18 StVG` 自 2020 年 7 月 17 日以来在实质内容上未变。2024 年中期之后的德国法修改（包括 2026 年第五次 StVG 修改法）不在本报告范围内。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 7

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 163 条；相同的参考文献 0 条。

相同片段举例：`kim sastry feedback linearization vs adaptive sliding mode control for quadrotor helicopter`

**这次运行打开过 876 个地址，最多的站点**：api.crossref.org 426，api.semanticscholar.org 87，api.openalex.org 41，arxiv.org 27，export.arxiv.org 21，mdpi.com 16，ieeexplore.ieee.org 15，ar5iv.labs.arxiv.org 11，semanticscholar.org 10，doi.org 9，onlinelibrary.wiley.com 9，scirp.org 8

**打开过的、和禁用来源同一个站点的地址**：
- https://api.crossref.org/v1/works/http://dx.doi.org/10.1007/s12555-009-0311-8
- https://doi.org/
- https://doi.org/10.1109/access.2020.3037557
- https://doi.org/10.4236/ojapps.2014.414053
- https://doi.org/{it.get(
- https://ouci.dntb.gov.ua/en/works/4koRwQW4/
- https://ouci.dntb.gov.ua/en/works/7nkV6g64/
- https://ouci.dntb.gov.ua/en/works/ldDQGDGl/
- https://www.mdpi.com/1424-8220/19/1/24
- https://www.mdpi.com/2076-0825/8/2/43
- https://www.mdpi.com/2076-3417/10/11/3719
- https://www.mdpi.com/2076-3417/9/13/2723
- https://www.mdpi.com/2076-3417/9/23/5184
- https://www.mdpi.com/2079-3197/14/2/51/pdf|mdpi_computation.pdf
- https://www.mdpi.com/2079-9292/10/9/999

**报告的各级标题**：

    # 四旋翼无人机（Quadrotor）控制方法技术综述
    ## 阅读说明
    # 第一部分　控制器分类与优缺点总结
    ## 1.0 建模基础与共性背景
    ## 1.1 分类框架
    ### 分类边界的几点说明
    ## 1.2 线性控制
    ### 1.2.1 PID（比例-积分-微分控制）
    ### 1.2.2 LQR（线性二次型调节器）
    ### 1.2.3 H∞（H-无穷鲁棒控制）
    ## 1.3 非线性控制
    ### 1.3.1 反馈线性化（Feedback Linearization，含动态逆）
    ### 1.3.2 反步法（Backstepping）
    ### 1.3.3 滑模控制（SMC，Sliding Mode Control）
    ### 1.3.4 模型预测控制（MPC，Model Predictive Control）
    ### 1.3.5 自适应控制（Adaptive Control）
    ## 1.4 基于学习的控制
    ### 1.4.1 模糊逻辑控制（Fuzzy Logic Control）
    ### 1.4.2 神经网络控制（Neural Network Control）
    ### 1.4.3 基于学习的控制的更广范围
    ## 1.5 三类方法的横向对比小结
    ## 1.6 头对头基准对比与文献中的争议
    ### 使用这些结论时必须注意的争议与不确定性
    # 第二部分　性能改进策略汇总表
    ## 第二部分小结：改进策略的五条共性主线
    # 参考文献
    ## A. 综述、对比研究与分类框架
    ## B. PID 控制
    ## C. LQR 控制
    ## D. H∞ 控制
    ## E. 反馈线性化
    ## F. 反步法
    ## G. 滑模控制
    ## H. 模型预测控制
    ## I. 自适应控制
    ## J. 模糊逻辑控制
    ## K. 神经网络与学习型控制
    ## L. 其他被引用的四旋翼控制文献
    ## M. 补充综述与背景来源
    ## N. 滑模控制补充文献

**报告开头**：

> # 四旋翼无人机（Quadrotor）控制方法技术综述
> 
> **文献覆盖范围：截至 2021 年 5 月**
> 
> ---
> 
> ## 阅读说明
> 
> 1. **时间范围**：本综述的目标是梳理截至 **2021 年 5 月** 公开发表的研究成果。个别条目若发表于 2021 年 5 月之后，会显式标注为「窗口外」，仅用于说明技术脉络，不作为主要结论依据。
> 2. **平台说明**：优先采用四旋翼（quadrotor / quadcopter）平台的结果。少量结论来自六旋翼、无人直升机、四倾转旋翼机这三类相近平台，均在正文中标注为「相近平台」。
> 3. **引用格式**：正文与表格中的方括号编号对应文末「参考文献」列表；引用形式为 `[作者 年份]`，并给出 DOI 或 URL 以便核查。
> 4. **完整性约定**：按照要求，本报告在枚举优点、缺点、混合策略与改进策略时**不作省略式概括**：所有条目均逐条列出，不以「以及同类方法」一类的措辞收尾。
> 
> ---
> 
> # 第一部分　控制器分类与优缺点总结
> 
> ## 1.0 建模基础与共性背景
> 
> 所有控制器的设计都建立在同一个被控对象上：一个具有 4 个控制输入（总推力与三轴力矩）和 6 个位姿自由度的欠驱动刚体。四旋翼的动力学建模、气动效应辨识与传感器估计构成了控制设计的共同前提，相关经典工作包括：四旋翼飞行力学与实验辨识 [Hoffmann2007]；基于 SE(3) 的几何建模与跟踪控制 [Lee2010]；多旋翼的建模、估计与控制综述 [Mahony2012]；大型四旋翼的建模与控制 [Pounds2010]；VTOL 四旋翼的姿态镇定 [Tayebi2006]；PD 控制与 VTOL 建模 [Erginer2007]；最小 Snap 轨迹生成与控制 [Mellinger2011]；以及高速多翻滚机动的学习型策略 [Lupashin2010]；低成本开源微型四旋翼平台及其 Linux 控制器 [Desbiez2017]。
> 
> 在方法论层面，本报告的分类框架参考了以下综述：对 PID、LQR、滑模、反步、反馈线性化、自适应、鲁棒、最优、L1、H∞、模糊与神经网络控制「优点与缺点」的系统梳理 [Zulu2014]；非线性与自适应智能控制技术综述 [Mo2019]；自主旋翼飞行器控制策略与新技术综述 [Abdelmaksoud2020]；四旋翼无人机控制算法进展综述 [Li2015]；自主四旋翼控制策略综合调查 [Kim2019b]；面向四旋翼类飞行机器人的反馈控制策略综述（在同一平台上用同一组指标对比 PID、SMC、反步、反馈线性化与模糊控制）[Ozbek2016]；四旋翼应用、结构设计与控制算法综述 [Idrissi2022]；微型飞行器模型预测控制综述 [Nguyen2020]；路径跟随控制策略综述 [Rubi2020]；四旋翼构型、建模辨识、控制、避障与容错综述 [Shraim2018]；四旋翼控制方法与性能评估综述 [Amin2016]；以及基于人工神经网络的无人机模型基飞行控制综述 [Gu2020]。这些综述的共同结论构成本报告的两条主线：**没有单一控制器在所有指标上占优**，以及**性能提升主要来自混合与增强**。
> 
> ## 1.1 分类框架
> 
> 四旋翼是一个**欠驱动、强耦合、非线性、时变**的系统：只有 4 个独立控制输入（总推力 + 三轴力矩），却需要控制 6 个自由度（三轴位置 + 三轴姿态）。其动力学具有典型的**级联/严格反馈结构**——姿态环快、位置环慢，位置运动必须通过姿态倾斜产生的推力分量来间

**报告结尾（含参考文献）**：

> [Benallegue2008] A. Benallegue, A. Mokhtari, L. Fridman. "High-order sliding-mode observer for a quadrotor UAV." *International Journal of Robust and Nonlinear Control*, 18(4–5):427–440, 2008. DOI: 10.1002/rnc.1225.
> 
> [Farrell2009] J. A. Farrell, M. Polycarpou, M. Sharma, W. Dong. "Command filtered backstepping." *IEEE Transactions on Automatic Control*, 54(6):1391–1395, 2009. DOI: 10.1109/TAC.2009.2015562. 「方法学」
> 
> ### R.2 滑模控制的理论与变体
> 
> [UtkinLee2006] V. Utkin, H. Lee. "Chattering problem in sliding mode control systems." *2006 International Workshop on Variable Structure Systems (VSS)*. DOI: 10.1109/VSS.2006.1644542. 「方法学」
> 
> [Boiko2011] I. Boiko. "Analysis of chattering in non-ideal sliding mode control systems with boundary layer." *2011 American Control Conference (ACC)*. DOI: 10.1109/ACC.2011.5990793. 「方法学」
> 
> [Obeid2018] H. Obeid, L. M. Fridman, S. Laghrouche, M. Harmouche, M. A. Golkani. "Barrier function-based adaptive sliding mode control." *Automatica*, 93:540–544, 2018. DOI: 10.1016/j.automatica.2018.03.078. 「方法学」
> 
> [Abaunza2020] H. Abaunza, P. Castillo. "Quaternion-based chattering-free sliding mode control of a quadrotor." *IEEE Transactions on Aerospace and Electronic Systems*, 2020. DOI: 10.1109/TAES.2019.2937663.
> 
> [Zeng2019] 曾 et al. "Event-triggered sliding mode control of a quadrotor." *2019 Chinese Control and Decision Conference (CCDC)*. DOI: 10.1109/CCDC.2019.8833388.
> 
> [Mechali2021] M. Mechali, L. Xu, Y. Huang, M. Shi, X. Xie. "Observer-based fixed-time continuous nonsingular terminal sliding mode control of quadrotor aircraft under uncertainties and disturbances." *Control Engineering Practice*, 2021. DOI: 10.1016/j.conengprac.2021.104806.
> 
> [Izaguirre2019] E. Izaguirre-Espinosa, A. J. Muñoz-Vázquez, A. Sánchez-Orta, V. Parra-Vega, P. Castillo. "Fractional-order control for robust position/yaw tracking of quadrotors with experiments." *IEEE Transactions on Control Systems Technology*, 2019. DOI: 10.1109/TCST.2018.2831175.
> 
> [Khatiwada2018] 卡提瓦达 et al. "PSO-tuned fault-tolerant sliding mode control." *ASME Dynamic Systems and Control Conference (DSCC)*, 2018. DOI: 10.1115/DSCC2018-9078.
> 
> [Orosco2018] 奥罗斯科 et al. "Genetic-algorithm-tuned sliding mode control." *2018 IEEE Ecuador Technical Chapters Meeting (ETCM)*. DOI: 10.1109/ETCM.2018.8580279.
> 
> ### R.3 反步法与动态逆的补充
> 
> [Huang2020b] 黄 et al. "Adaptive backstepping control of a quadrotor with input saturation." *Asian Journal of Control*, 2020. DOI: 10.1002/asjc.2326.
> 
> [Aboudonia2017] A. Aboudonia, A. El-Badawy, R. Rashad. "Disturbance-rejection control for a quadrotor using command-filtered backstepping." *Nonlinear Dynamics*, 2017. DOI: 10.1007/s11071-017-3683-y.
> 
> [Ansari2018b] U. Ansari, A. Bajodah, M. T. Hamayun. "Generalized dynamic inversion based adaptive nonsingular terminal sliding mode control of a quadrotor." *Asian Journal of Control*, 2018. DOI: 10.1002/asjc.1800.
> 
> [Blas2019] L. E. Blas, et al. "Robust feedback linearization for a quadrotor." *2019 European Control Conference (ECC)*. DOI: 10.23919/ECC.2019.8796174.
> 
> [Du2016b] 杜 et al. "Incremental nonlinear dynamic inversion with integral extended state observer." *2016 IEEE Chinese Guidance, Navigation and Control Conference (CGNCC)*. DOI: 10.1109/CGNCC.2016.7829076.

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 8

**题目**：Legal Research on Traffic Accident Liability for German Autonomous Vehicles（Crime & Law）

**禁用的来源文章**：Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China

- https://www.mdpi.com/2032-6653/15/7/305
- https://www.mdpi.com/2032-6653/15/7/305/pdf
- https://www.mdpi.com/2032-6653/15/7/305/html
- https://www.mdpi.com/2032-6653/15/7/305/xml
- https://www.researchgate.net/publication/382225455_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_of_the_German_Legislation_for_China
- https://www.researchgate.net/publication/382400472_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_from_the_German_Legislation_for_China/download

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 492 个地址，最多的站点**：buzer.de 188，dejure.org 34，gesetze-im-internet.de 16，eur-lex.europa.eu 14，de.wikipedia.org 11，gesetze-im-internet.juris.de 10，haufe.de 9，europarl.europa.eu 6，gesetze-im-internet.edge.juris.de 6，dserver.bundestag.de 6，rewis.io 6，bundesrat.de 5

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 德国 L3 级及以上自动驾驶汽车交通事故责任调研报告
    ## 目录
    ## 方法与资料说明
    ## 执行摘要
    ## 第一章 法律框架与角色界定
    ### 1.1 自动化等级与德国法术语
    ### 1.2 2017 年第八次 StVG 修订：为 L3 建立框架
    ### 1.3 2021 年"自动驾驶法"：为 L4 建立框架
    ### 1.4 AFGBV：运行层面的实施条例
    ### 1.5 国际法与欧盟法中的"准入/技术"框架
    ### 1.6 四类责任主体
    ### 1.7 责任体系总览（一句话版）
    ## 第二章 驾驶员（Fahrer）的责任
    ### 2.1 谁是"驾驶员"：L3 与 L4/L5 的分野
    #### 2.1.1 L3：激活系统者仍是驾驶员
    #### 2.1.2 L4/L5：技术监督——立法**有意**未将其等同于驾驶员
    ### 2.2 请求权基础与责任类型
    ### 2.3 L3 驾驶员的注意义务
    ### 2.4 免责与抗辩
    ### 2.5 举证责任（三层结构）
    ### 2.6 刑事与行政责任（简要）
    ## 第三章 车辆持有人（Halter）的责任
    ### 3.1 Halter 的法律概念
    #### 3.1.1 判例定义与双重要素
    #### 3.1.2 与所有权人、驾驶人的区分
    #### 3.1.3 典型场景
    #### 3.1.4 Robotaxi 运营商是否成为 Halter？
    ### 3.2 § 7 Abs. 1 StVG：无过错危险责任
    #### 3.2.1 条文与构成要件
    #### 3.2.2 "bei dem Betrieb"的宽泛解释
    #### 3.2.3 自动驾驶语境下的适用
    ### 3.3 § 7 Abs. 2 不可抗力与 § 7 Abs. 3 Schwarzfahrt
    #### 3.3.1 不可抗力（höhere Gewalt）的四要素
    #### 3.3.2 车辆自身技术缺陷原则上不构成不可抗力
    #### 3.3.3 § 7 Abs. 3：盗用／无权使用（Schwarzfahrt）
    ### 3.4 与驾驶人责任的关系、§ 17 分担、连带与追偿
    #### 3.4.1 § 18 StVG 与两套责任的对照
    #### 3.4.2 § 17 StVG：内部关系中的原因力与过错分担
    #### 3.4.3 内部追偿
    ### 3.5 § 12 StVG 责任限额与赔偿范围

**报告开头**：

> # 德国 L3 级及以上自动驾驶汽车交通事故责任调研报告
> 
> **信息时点：2024 年 6 月 30 日**（此后发展仅在"后续动态"中另行标注）
> **报告语言：中文；德国法术语保留德文原文并附中文释义**
> 
> ---
> 
> ## 目录
> 
> - 方法与资料说明
> - 执行摘要
> - 第一章　法律框架与角色界定
> - 第二章　驾驶员（Fahrer）的责任
> - 第三章　车辆持有人（Halter）的责任
> - 第四章　生产者的侵权责任：Produzentenhaftung（§ 823 BGB 路径）
> - 第五章　制造商产品责任：ProdHaftG（无过错严格责任）
> - 第六章　Produzentenhaftung 与 ProdHaftG 的系统对比
> - 第七章　数据、证据与举证机制
> - 第八章　保险与责任实现
> - 第九章　改革动态、EU 框架与评估（截至 2024 年中期）
> - 第十章　总体结论
> - 附录 A　关键条文清单
> - 附录 B　主要来源清单
> - 附录 C　不确定性与时效说明
> 
> ---
> 
> ## 方法与资料说明
> 
> 1. **规范基准**：本报告以 2024 年 6 月 30 日当时有效的德国联邦法律（尤其是 StVG、BGB、ProdHaftG、PflVG、VVG、ZPO、AFGBV）、欧盟法（尤其是 RL 85/374/EWG、VO (EU) 2019/2144、RL 2009/103/EG 及 (EU) 2021/2118）和当时可查的判例（尤其 BGH）为准。
> 2. **资料层级**：优先使用条文原文、联邦法律公报（BGBl.）、EUR-Lex、法院裁判与部委官方文件；二手文献仅用于学理归纳，并已尽量交叉核对。
> 3. **标注规则**：凡未能以一手来源核实者标注【待核实】；学理或判例尚无定论者标注【争议未决】。金额、条文号、案号均经核对后写入。
> 4. **重要提醒（避免常见误传）**：
>    - § 12 StVG 的责任限额不是 120 万/30 万欧元，而是**人身损害 500 万欧元**（使用高/全自动化或自主功能时 **1000 万欧元**）、**物损 100 万欧元**（相应自动化情形 **200 万欧元**）。
>    - ProdHaftG 的责任上限为 **8500 万欧元**（§ 10），物损自担额为 **500 欧元**（§ 11）。
>    - PflVG 的最低保险金额（人身 750 万、物损 130 万、纯经济损失 5 万欧元）与 § 12 StVG 的责任限额是两个不同概念。
> 5. **风险提示**：本报告为法律调研，不构成对具体案件的法律意见。
> 
> ---
> 
> ## 执行摘要
> 
> **一、法律框架**。德国没有一部统一的"自动驾驶责任法"，而是在既有责任体系上叠加了两代专门立法：2017 年第八次 StVG 修订（BGBl. 2017 I S. 1648）为 **L3** 建立框架（§§ 1a–1c、63a、63b StVG，并将 § 12 责任限额对自动化功能翻倍）；2021 年"自动驾驶法"（BGBl. 2021 I S. 3108）为**限定运行区域内的 L4** 建立框架（新增 §§ 1d–1l StVG，并修改 PflVG）。**§ 7 StVG 的危险责任在此期间未被实质修改**，仍原封适用于自动驾驶车辆。
> 
> **二、驾驶员（用户问题 1）**。
> - **法律依据**：§ 823 Abs. 1 BGB（一般过错侵权）与 **§ 18 StVG**（驾驶人责任的特别规定）；L3 下的驾驶人地位由 **§ 1a Abs. 4 S

**报告结尾（含参考文献）**：

> - Bird & Bird, "AFGBV in Kraft – Verordnung komplettiert Gesetz zum autonomen Fahren"（2022-11-08）
> - Bird & Bird, "Update: Reform der Produkthaftung beschlossen"（新 PLD 对照）
> - Haufe, Prütting/Wegen/Weinreich 评注（ProdHaftG § 3 举证责任）
> - FGVW 案例评述（BGH VI ZR 82/22）
> - DAV-Stellungnahme Nr. 33/2021（对 § 1g 数据条款的批评）
> - 德国保险业协会（GDV）关于 Kfz-Haftpflicht 技术中立的立场
> 
> ## 附录 C：不确定性与时效说明
> 
> ### C.1 时间基准
> 
> - 本报告主线法律状态截至 **2024 年 6 月 30 日**。
> - 2024 年 7 月 1 日以后发生的事件（例如欧盟新《产品责任指令》(EU) 2024/2853 于 2024 年 10 月 23 日正式通过）只在第九章的"后续发展"中一句提示，不作为本报告的主线结论。
> - 德国 StVG 在 2024 年中期之后多次修改（包括 2024 年 7 月、8 月以及 2025、2026 年的修订）。本报告在引用条文时已尽量通过版本对照回推至 2024 年 6 月 30 日适用的版本；例如 § 1a/§ 1b 的标题在 2026 年被改为"automatisierte Fahrfunktion"、§ 12 在 2026 年被再次修改，本报告均按 2024 年中期版本表述。
> 
> ### C.2 主要不确定性（按主题）
> 
> | 主题 | 不确定内容 | 状态 |
> |---|---|---|
> | 技术监督的责任 | 立法者有意不适用 § 18 StVG 的过错推定（联邦参议院主张纳入被联邦政府拒绝，BT-Drs. 19/28178, S. 10, 24）；其责任依 § 823 BGB，受害人须自证过错 | 【立法选择明确，学理批评】 |
> | 软件的产品适格性 | ProdHaftG § 2 对无载体软件、SaaS、后端地图服务的适用 | 【争议未决】 |
> | 算法缺陷的证明 | 无 BGH 判例；表见证明在技术缺陷领域受限（BGH VI ZR 76/23） | 【争议未决】 |
> | OTA 更新与投入流通 | 更新是否重置 § 13 的十年期间、是否构成新的投入流通 | 【待核实】 |
> | § 1g 数据条款 | 缺乏一般存储期限；§ 63b 的条例授权是否已被行使 | 【待核实】 |
> | § 1f StVG 原文 | 部分义务内容依赖二手核对（buzer.de 间歇性 403） | 【待核实】 |
> | 认证与民事责任 | 无直接针对 EU 2018/858 / UN R157 的"认证不免责"BGH 判决 | 【待核实】 |
> | 开发风险抗辩 | 无 AI/ML 场景下 § 1 Abs. 2 Nr. 5 ProdHaftG 的公开裁判 | 【待核实】 |
> | 举证责任细节 | § 12 是否适用于 § 18 的责任，文义肯定但无直接判例 | 【待核实】 |
> 
> ### C.3 资料与检索限制（诚实记录）
> 
> - 本次调研环境无法访问部分常用法律数据库（gesetze-im-internet.de、dejure.org、jusline.de、bundesgerichtshof.de 等不可达或返回错误）。因此一手条文主要通过 **buzer.de 的单条条文页与版本对照页**、**BGBl**、**EUR-Lex**、部委与律所公开文章核对；判例主要通过其全文/官方摘要在公开来源中的转载核对。
> - buzer.de 的合并条文页默认显示**当前版本**（可能已含 2024 年后的修订），本报告对关键条文（§ 1a、§ 1b、§ 1c、§ 12、§ 18、ProdHaftG §§ 1、2、10、11、PflVG § 4 及 Anlage）均通过版本对照或修改法确定 2024 年中期的适用文本。
> - 凡未能取得一手来源的表述，均已在正文标注【待核实】或【争议未决】；请勿将此类表述作为确定法律结论引用。
> - 本报告为法律调研，不构成对具体案件的法律意见；德国法在相关领域仍在快速演进，引用前请核对最新版本。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 9

**题目**：Investigation of Hydroforming Technology（Industrial）

**禁用的来源文章**：A review of emerging hydroforming technologies: design considerations, parametric studies, and recent innovations

- https://jeas.springeropen.com/articles/10.1186/s44147-024-00546-z
- https://www.researchgate.net/publication/385401108_A_review_of_emerging_hydroforming_technologies_design_considerations_parametric_studies_and_recent_innovations
- https://ui.adsabs.harvard.edu/abs/2024JEAS...71..205C/abstract

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 72 个地址，最多的站点**：ahssinsights.org 9，mdpi.com 8，sciencedirect.com 5，nipponsteel.com 4，doras.dcu.ie 3，beta.iopscience.iop.org 3，mej.aut.ac.ir 2，osti.gov 2，koreascience.kr 2，link.springer.com 2，kci.go.kr 2，api.openalex.org 2

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 液压成形（Hydroforming）技术调研报告：材料选择与常见制造缺陷
    ## 引言：工艺要点速览
    # 第一部分　液压成形常用金属材料分析
    ## 1.0 四类材料横向对比
    ## 1.1 高强度钢（HSS / AHSS）
    ### 1.1.1 材料特性
    ### 1.1.2 成形挑战
    ### 1.1.3 主要应用与具体实例
    ## 1.2 高强度铝合金
    ### 1.2.1 材料特性
    ### 1.2.2 成形挑战
    ### 1.2.3 主要应用与具体实例
    ## 1.3 镁合金
    ### 1.3.1 材料特性
    ### 1.3.2 成形挑战
    ### 1.3.3 主要应用与具体实例
    ## 1.4 钛合金
    ### 1.4.1 材料特性
    ### 1.4.2 成形挑战
    ### 1.4.3 主要应用与具体实例
    ## 1.5 材料选择小结（分析师建议）
    # 第二部分　常见制造缺陷、成因及对策
    ## 2.0 缺陷总览与工艺窗口
    ## 2.1 表面缺陷（Surface defects）
    ### 2.1.1 主要成因
    ### 2.1.2 建议的解决方法
    ## 2.2 回弹（Springback）
    ### 2.2.1 主要成因
    ### 2.2.2 建议的解决方法
    ## 2.3 起皱（Wrinkling）
    ### 2.3.1 主要成因
    ### 2.3.2 建议的解决方法
    ## 2.4 变薄（Thinning）
    ### 2.4.1 主要成因
    ### 2.4.2 建议的解决方法
    ## 2.5 撕裂（Tearing / Bursting / Fracture）
    ### 2.5.1 主要成因
    ### 2.5.2 建议的解决方法
    ## 2.6 缺陷之间的耦合关系与工艺窗口控制
    ## 2.7 缺陷排查速查表

**报告开头**：

> # 液压成形（Hydroforming）技术调研报告：材料选择与常见制造缺陷
> 
> **报告定位**：面向汽车与航空航天制造的行业技术调研
> **覆盖范围**：管材液压成形（Tube Hydroforming, THF；亦称内高压成形 IHU）与板材液压成形（Sheet Hydroforming, SHF）
> **编写日期**：2025 年
> 
> ---
> 
> ## 引言：工艺要点速览
> 
> 液压成形利用高压液体介质使金属坯料贴合模具型腔成形，主要用于制造轻量化、高刚度、闭口截面的整体结构件。理解后文材料与缺陷的前提，是掌握以下工艺要点：
> 
> | 要点 | 说明 |
> |---|---|
> | 管材液压成形（THF） | 管坯置于下模→合模→两端密封→充液加压，同时由端部冲头施加**轴向进给（axial feeding / end-feed）**补料，使管壁胀形贴模。内压可达数百 MPa 量级。 |
> | 板材液压成形（SHF） | 以高压液体替代凸模或凹模，包括充液拉深（hydro-mechanical deep drawing）、柔性成形（flexforming，带隔膜）、液压胀形等；充液拉深压力可高达约 100 MPa（15,000 psi）。 |
> | 高压 vs. 压力顺序 THF | 高压 THF 合模后加压，压力高、尺寸精度好、可成形小圆角；压力顺序 THF（低压路线）先充入略小于终态周长的管坯再合模，靠截面形状改变成形，**特别适合先进高强钢（AHSS）等低成形性材料**（[AHSS Guidelines – Hydroforming](https://ahssinsights.org/forming/hydroforming/hydroforming/)）。 |
> | 膨胀率 η | η = 成形后截面周长 L₁ / 管坯周长 L₀。传统 THF 约为 1.0–1.1，最高约 1.4；日本制铁开发的大膨胀工艺可达 η≈2.8–3.0（[Nippon Steel Technical Report No. 107](https://www.nipponsteel.com/en/tech/report/nssmc/pdf/107-15.pdf)）。 |
> | 应变路径 | 管长不变、仅局部胀形时以**平面应变**为主，是成形极限曲线（FLC）上的最低点，最易开裂；轴向进给可将应变状态向压缩侧移动，显著提高可成形性（[AHSS Guidelines – Hydroforming](https://ahssinsights.org/forming/hydroforming/hydroforming/)）。 |
> | 主要失效模式 | 起皱、变薄、撕裂/爆裂、回弹、表面缺陷——五者通过"内压—进给—摩擦—温度"的加载路径相互耦合。 |
> 
> > **典型应用分布**：汽车领域占绝对主导（副车架/发动机托架、仪表板横梁、车架纵梁、顶盖纵梁、A/B 柱、侧碰梁、散热器支架、排气歧管、桥壳等）；航空航天领域主要用于铝合金导管、钛合金液压管路与 SPF/DB 结构件；此外还有自行车车架、轮椅车架等（[Wikipedia – Hydroforming](https://en.wikipedia.org/wiki/Hydroforming)）。
> 
> ---
> 
> # 第一部分　液压成形常用金属材料分析
> 
> ## 1.0 四类材料横向对比
> 
> | 维度 | 高强度钢（HSS/AHSS） | 高强度铝合金 | 镁合金 | 钛合金 |
> |---|---|---|---|---|
> | 密度（g/cm³） | 

**报告结尾（含参考文献）**：

> 10. SAE 2000-01-2670 — Automotive Tube Bending and Tubular Hydroforming with Extruded Aluminium Profiles：https://doi.org/10.4271/2000-01-2670
> 11. SAE 970373 — Hydroforming High Strength Steel Tube for Automotive Structural Applications Using Expansion：https://doi.org/10.4271/970373
> 12. Materials Science Forum — Deformation Behaviors of 6061 and 7075 Aluminum Tubes at Elevated Temperatures for Warm Hydroforming：https://doi.org/10.4028/0-87849-960-1.373
> 13. ScienceDirect — Effects of pre-treatment conditions on warm hydroformability of 7075 aluminum tubes：https://www.sciencedirect.com/science/article/abs/pii/S0924013604005953
> 15. SAE 2023-28-1304 — Aluminium Hot Forming: Opportunities and Challenges in Automotive Light Weighting：https://doi.org/10.4271/2023-28-1304
> 
> **镁合金与温热成形**
> 
> 15. Metals 11(6):901 — Warm Hydroforming Process under Non-Uniform Temperature Field for Magnesium Alloy Tubes：https://doi.org/10.3390/met11060901
> 16. MSEC2013-1084 — Simulation and Experiment on Warm Hydroforming of AZ31 Magnesium Alloy Tube：https://doi.org/10.1115/msec2013-1084
> 17. Materials Science Forum 654-656.739 — Warm Hydroforming Process with Non-Uniform Heating for AZ31 Magnesium Alloy Tube：https://doi.org/10.4028/www.scientific.net/msf.654-656.739
> 
> **钛合金**
> 
> 18. NIST / IIT Madras — A study of the influence of stress relaxation on ductility improvement of Ti-6Al-4V alloys：https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=932902
> 19. Materials Science Forum 783-786.2456 — Progress on High Pressure Pneumatic Forming and Warm Hydroforming of Titanium and Magnesium Alloy Tubular Components：https://doi.org/10.4028/www.scientific.net/msf.783-786.2456
> 20. Encyclopedia of Aerospace Engineering — Superplastic Forming and Diffusion Bonding of Titanium Alloys：https://doi.org/10.1002/9780470686652.eae223
> 
> **缺陷与控制**
> 
> 21. OSTI / SAE 2018-01-0803 — Residual Stress Distribution in a Hydroformed Advanced High Strength Steel Component：https://www.osti.gov/servlets/purl/3682582
> 22. MSF 762.621 — Effect of Friction and Lubrication on Formability of AA5182 Alloy in Hydroforming of Square Cups：https://doi.org/10.4028/www.scientific.net/msf.762.621
> 23. KEM 622-623.739 — Research on Wrinkling Behavior in Tube Hydroforming with Axial Feeding：https://doi.org/10.4028/www.scientific.net/kem.622-623.739
> 24. J. Strain Analysis 2020 — Investigation on wrinkling behaviors of metal thin-walled tube in pulsating hydroforming with axial feeding：https://doi.org/10.1177/0309324720949062
> 25. JMPT 2007 — Analytical modeling of wall thinning during corner filling in structural tube hydroforming：https://doi.org/10.1016/j.jmatprotec.2007.03.112
> 26. IJMS 2008 — Analytical model for planar tube hydroforming: Prediction of formed shape, corner fill, wall thinning, and forming pressure：https://doi.org/10.1016/j.ijmecsci.2008.05.006
> 27. IJMS 2002 — Bursting failure prediction in tube hydroforming processes by using rigid–plastic FEM combined with ductile fracture criterion：https://doi.org/10.1016/s0020-7403%2802%2900045-0
> 28. IJAMT 2003 — A prediction of bursting failure in tube hydroforming processes based on ductile fracture criterion：https://doi.org/10.1007/s00170-002-1489-6
> 29. SAE 2002-01-0794 — A Bursting Failure Criterion for Tube Hydroforming：https://doi.org/10.4271/2002-01-0794
> 30. IJAMT 2016 — Springback and compensation of bending for hydroforming of advanced high-strength steel welded tubes：https://doi.org/10.1007/s00170-016-9319-4
> 31. SAE 2007-01-1687 — On Improving the Accuracy of Springback Prediction and Die Compensation：https://doi.org/10.4271/2007-01-1687
> 32. KEM 549.141 — Tube Hydroforming (THF): Process Optimization of an Automotive Component：https://doi.org/10.4028/www.scientific.net/kem.549.141
> 33. Research Square preprint — Multi-step Hydroforming Process and Wall Thickness Optimization of 5A02 Aluminum Alloy Five-Way Tube：https://doi.org/10.21203/rs.3.rs-1027514/v1
> 
> > **说明**：本报告基于公开技术文献、行业指南与企业技术报告编写；文中数值为文献报道值或行业经验区间，实际产品设计应以具体材料牌号、管坯状态、模具条件与主机厂标准为准。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 10

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 154 条；相同的参考文献 0 条。

相同片段举例：`kim sastry feedback linearization vs adaptive sliding mode control for quadrotor helicopter`

**这次运行打开过 233 个地址，最多的站点**：api.crossref.org 134，arxiv.org 9，ardupilot.org 9，api.semanticscholar.org 9，export.arxiv.org 7，web.archive.org 7，api.openalex.org 6，docs.px4.io 6，ar5iv.labs.arxiv.org 4，raw.githubusercontent.com 4，doi.org 3，infoscience.epfl.ch 3

**打开过的、和禁用来源同一个站点的地址**：
- https://doi.org/
- https://doi.org/{doi}
- https://www.mdpi.com/2076-3417/9/18/3873

**报告的各级标题**：

    # 四旋翼无人机控制方法技术综述
    ## 0. 范围、方法与阅读指南
    ### 0.1 覆盖范围与时间边界
    ### 0.2 调研与核实方法
    ### 0.3 合规说明
    ### 0.4 报告结构
    ## 1. 控制器特性总结
    ### 1.1 控制器三分类框架与归类判定
    #### 控制器逐个归类、归类理由与边界情形
    #### 归类总表
    #### 逐条归类理由（展开）
    #### 边界情形专题讨论（10 类）
    ### 1.2 PID（比例-积分-微分，Proportional–Integral–Derivative）
    #### 一句话工作原理（结合四旋翼串级回路）
    #### 主要优点（12 条，每条附依据）
    #### 主要缺点（12 条，每条附依据）
    #### 典型适用场景与不适用场景
    #### 工程实现注意事项（12 条）
    #### 该控制器在四旋翼上的代表性真实文献（7 篇，元数据均经 Crossref 核验）
    ### 1.3 LQR（线性二次调节器，Linear Quadratic Regulator）
    #### 一句话工作原理（结合四旋翼串级回路）
    #### 主要优点（11 条，每条附依据）
    #### 主要缺点（11 条，每条附依据）
    #### 典型适用场景与不适用场景
    #### 工程实现注意事项（9 条）
    #### 该控制器在四旋翼上的代表性真实文献（7 篇，元数据均经 Crossref 核验）
    ### 1.4 H∞（H-无穷，H-infinity）鲁棒控制
    #### 一句话工作原理
    #### 四旋翼中常见的 H∞ 设计形式与应用位置
    #### 主要优点（逐条附依据）
    #### 主要缺点（逐条附依据）
    #### 典型适用场景与不适用场景
    #### 工程实现注意事项
    #### 四旋翼 H∞ 的代表性真实文献
    ### 1.5 反馈线性化（Feedback Linearization）
    #### 一句话工作原理
    #### 主要优点（12 条，逐条附依据）
    #### 主要缺点（13 条，逐条附依据）
    #### 典型适用场景 / 不适用场景
    #### 工程实现注意事项（11 条）

**报告开头**：

> # 四旋翼无人机控制方法技术综述
> 
> > **信息覆盖范围：截至 2021 年 5 月（含 2021-05）的公开文献与工业实践。**
> > 本报告由 8 个互不重叠的专题调研并行完成，再统一汇总、去重与结构化。
> 
> ## 0. 范围、方法与阅读指南
> 
> ### 0.1 覆盖范围与时间边界
> 
> 本报告覆盖四旋翼（quadrotor / quadcopter）控制方法的下列内容：
> 
> 1. **控制器特性总结**：把常见控制器分为**线性控制**、**非线性控制**、**基于学习的控制**三类，并逐一总结 PID、LQR、H∞、反馈线性化、反步法、SMC、MPC、自适应控制、模糊逻辑、神经网络的主要优点与主要缺点。
> 2. **性能改进策略**：针对上述每一种控制器，梳理「与其他控制器混合使用」与「对控制器自身进行改进」两类策略，整理为「控制器 | 控制器混合策略举例 | 现有控制器改进策略举例」三列表格。
> 3. **性能评估方法学与基准**：指标、测试场景、实验平台、公开对比研究，以及「跨论文数字不可直接比较」的方法学讨论。
> 4. **跨控制器通用改进使能技术**：扰动观测器、系统辨识、元启发式整定、控制分配、抗饱和、容错、事件触发、代码生成、安全监督、能效优化、气动建模、多机协同、数字孪生、数据驱动残差补偿。
> 
> **时间边界**：仅收录 **2021 年 5 月及以前**公开发表的文献与公开工程实践。个别发表于 2021 年 5 月之后的擦边文献，均在原专题报告中被显式标注并排除在结论之外；本报告不把它们作为论断依据。
> 
> **行文约定**：专业术语首次出现时以「中文（English）」形式给出。文中「X 等（年份）」是英文 "et al." 的中文缩写，**不是**对列举条目的省略；本报告在枚举处不使用「等」「等等」来跳过应列条目。
> 
> ### 0.2 调研与核实方法
> 
> - **检索渠道**：IEEE Xplore、ScienceDirect、SpringerLink、MDPI、arXiv、Wiley、Taylor & Francis、Google Scholar 摘要页，以及 PX4 / ArduPilot / MathWorks 等官方工程文档。
> - **元数据核实**：所有带 DOI 的文献条目均通过 **Crossref REST API**（`https://api.crossref.org/works/<DOI>`）逐条查询题名、作者、年份、期刊/会议、卷期页码；部分条目辅以 OpenAlex、arXiv API 与出版社页面交叉印证。各专题的核实统计见附录 B。
> - **量化数据纪律**：**只在原文摘要或可公开获取的全文中明确给出数字时才引用数字**。绝大多数 pre-2021 四旋翼控制文献只给时域响应曲线，因此本报告以定性机制描述为主，凡未核实原文数值之处均保留「未核实」标注，未做任何数字外推或编造。
> - **可复现性**：专题报告中保留了核实脚本与检索记录，便于复核。
> 
> ### 0.3 合规说明
> 
> 本报告严格遵守项目规则中关于**禁止来源**的最高优先级要求：被列为本项目禁止来源的文献及其任何转载页、摘要页、镜像页、聚合页、DOI 页面与机构仓储页面，在整个检索、分析与撰写流程中均未被访问、未被引用、未被转述；本报告正文、表格、脚注与参考文献中均不含该来源的任何标题、作者、期刊名、DOI 或 URL（包括不出现「排除声明」本身）。
> 
> 此外，本报告不使用任何无法溯源的条目：凡未能通过 DOI 接口或官方文档核实的条目，均在其出现处标注「元数

**报告结尾（含参考文献）**：

> 6. **1 处页码未核实**（Crossref 未给出文章号），已在文件中标注。
> 
> ### A.7 模糊逻辑 / 神经网络
> 
> 1. 本主题（尤其 IEEE 会议论文）**摘要普遍不给百分比**，统一量化对比表需另抓开放获取全文，本报告已一律标注「未见量化指标」，未做任何数字外推。
> 2. **未检索到「神经网络 + 显式 H∞ 综合」的四旋翼专用文献**（等价形式为鲁棒项 / 屏障证书）；「模糊 + H∞」的主流表述为 T-S 模糊 + LMI。
> 3. 截至 2021-05，**无 PPO / TRPO、LSTM / GRU / Transformer、贝叶斯 / 集成网络、课程学习的四旋翼专用验证文献**；元学习仅 1 篇（Meta-TD3）。
> 4. **工业实践缺少厂商一手文档**：「主流飞控以 PID 为主」只能引学术表述 + 开源飞控公开框图页。
> 5. 一条专著章节 Crossref 仅记录年份 2021，**出版月份未核实**，若晚于 2021-05 应剔除。
> 
> ### A.8 分类框架与基准
> 
> 1. **GWO / WOA / ACO / FA 未检索到 2021-05 前专门用于四旋翼整定的可核实论文**（属负结果，非穷尽性结论）。
> 2. **四旋翼专用 anti-windup 对比研究、模型降阶研究、UAV 专属数字孪生论文**均很少或未检索到。
> 3. AscTec Hummingbird / Firefly 的具体论文使用实例未核实（仅 Pelican 有可核实实例）。
> 4. **「抖振指标」无公认标准化定义。**
> 5. 八字形 / 螺旋轨迹的具体论文使用实例未逐篇核实。
> 6. 两条经典非线性控制教科书未找到 Crossref 记录，已刻意不引用以免出现不可溯源条目。
> 
> ## 附录 B：来源与核实统计
> 
> | 专题 | 覆盖控制器 | 主要产出规模 | 来源与核实 | 合规自检 |
> |---|---|---|---|---|
> | 第 1 部分 | PID、LQR | 优点 12+11 条、缺点 12+11 条；PID 混合 31 条 + 自身改进 26 条；LQR 混合 18 条 + 自身改进 21 条 | 106 个去重 DOI + 9 个官方文档 URL + 1 个期刊条目；全部论文条目经 Crossref 逐条核对 | 通过；禁止来源零命中 |
> | 第 2 部分 | H∞ | 优点 12 条、缺点 12 条；混合策略 14 条 + 自身改进 15 条；核心文献 16 篇 + 奠基理论 11 篇 | 55 个唯一 DOI（全部 Crossref 核对）+ 6 个非 DOI URL | 通过；禁止来源零命中 |
> | 第 3 部分 | 反馈线性化、反步法 | 优点 12+12 条、缺点 13+14 条；各 16 条混合 + 16 条自身改进；120 条编号参考文献 | 123 个 DOI 全部经 CrossRef / OpenAlex 解析成功（0 失败） | 通过；禁止来源零命中 |
> | 第 4 部分 | SMC | 优点 12 条、缺点 13 条；混合策略 16 条 + 自身改进 20 条 + 附加 1 条；代表性文献 10 篇；理论文献 40 条 | 175 条独立 DOI（全部 Crossref 核对） | 通过；禁止来源零命中 |
> | 第 5 部分 | MPC | 优点 14 条、缺点 14+1 条；16 种 MPC 形式；混合 18 条 + 自身改进 18 条 | 97 条来源，其中 94 条 Crossref 核实，3 条标注「元数据未核实」 | 通过；禁止来源零命中 |
> | 第 6 部分 | 自适应控制 | 12 类自适应形式；优点 16 条、缺点 15 条；混合 18 类 + 自身改进 22 条；代表文献 12 篇 | 221 个唯一 DOI、205 条参考文献（全部 Crossref 核对，修正 8 处页码错误） | 通过；禁止来源零命中 |
> | 第 7 部分 | 模糊逻辑、神经网络 | 优点 11+12 条、缺点 11+12 条；模糊混合 16 + 改进 15 条；神经混合 15 + 改进 18 条 | 120 条文献（119 条 Crossref 核实、1 条 arXiv API 核实）+ 1 条官方文档 | 通过；禁止来源零命中 |
> | 第 8 部分 | 分类框架、评估方法、通用使能技术 | 10 类边界情形；16 个指标；15 个平台；13 篇对比研究；24 项使能技术 | 约 211 个 DOI（211/211 Crossref 验证通过）+ 7 个非 DOI 来源（HTTP 200 验证） | 通过；禁止来源零命中 |
> 
> **总来源规模**：去重前约 **1000 条**文献与工程文档条目，去重后**数百条独立 DOI** 与官方文档链接，全部可溯源。
> 
> **核实纪律**：凡未通过 DOI 接口或官方文档核实的条目，均在其出现处标注「元数据未核实」；凡未逐篇获取全文的量化结论，均标注「未核实原文数值」，不做数字外推。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 11

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 160 条；相同的参考文献 0 条。

相同片段举例：`kim sastry feedback linearization vs adaptive sliding mode control for quadrotor helicopter`

**这次运行打开过 204 个地址，最多的站点**：api.crossref.org 152，api.semanticscholar.org 16，api.openalex.org 8，arxiv.org 5，export.arxiv.org 3，semanticscholar.org 2，dblp.org 2，atlantis-press.com 2，w3.org 2，jcta.ijournals.cn 1，inderscience.com 1，ijra.iaescore.com 1

**打开过的、和禁用来源同一个站点的地址**：
- https://api.openalex.org/works/https://doi.org/
- https://ouci.dntb.gov.ua/en/works/4bD6zJN9/

**报告的各级标题**：

    # 四旋翼无人机（Quadrotor）控制方法技术综述
    ## 范围与方法说明
    ## 目录
    # 第一部分　控制器分类与特性总结
    ## 1.1　三类划分的判据与总体特征
    ### 1.1.1　被控对象特征与建模基础
    ### 1.1.2　三类划分的判据
    ### 1.1.3　三类控制的总体特征
    ### 1.1.4　边界情形的归类说明
    ### 1.1.5　评价维度
    ## 1.2　PID（比例-积分-微分）控制
    ### 1.2.1　主要优点
    ### 1.2.2　主要缺点
    ## 1.3　LQR（线性二次调节器）
    ### 1.3.1　主要优点
    ### 1.3.2　主要缺点
    ## 1.4　H∞（H-无穷）控制
    ### 1.4.1　主要优点
    ### 1.4.2　主要缺点
    ## 1.5　反馈线性化（Feedback Linearization）
    ### 1.5.1　主要优点
    ### 1.5.2　主要缺点
    ## 1.6　反步法（Backstepping）
    ### 1.6.1　主要优点
    ### 1.6.2　主要缺点
    ## 1.7　滑模控制（SMC）
    ### 1.7.1　主要优点
    ### 1.7.2　主要缺点
    ## 1.8　模型预测控制（MPC）
    ### 1.8.1　主要优点
    ### 1.8.2　主要缺点
    ## 1.9　自适应控制（Adaptive Control）
    ### 1.9.1　主要优点
    ### 1.9.2　主要缺点
    ## 1.10　模糊逻辑控制（Fuzzy Logic）
    ### 1.10.1　主要优点
    ### 1.10.2　主要缺点
    ## 1.11　神经网络控制（Neural Network）
    ### 1.11.1　主要优点
    ### 1.11.2　主要缺点

**报告开头**：

> # 四旋翼无人机（Quadrotor）控制方法技术综述
> 
> **文献覆盖范围：截至 2021 年 5 月（含 2021 年 5 月发表的成果）**
> 
> ## 范围与方法说明
> 
> 1. **时间范围**：本综述只纳入 2021 年 5 月及以前公开发表的论文、综述与工程资料；2021 年 6 月及以后出现的成果不在覆盖范围内。
> 2. **对象**：以欠驱动六自由度四旋翼（quadrotor）为被控对象，围绕姿态控制、位置/轨迹跟踪、抗扰与容错四类任务，考察控制器的结构特性与性能改进手段。
> 3. **组织方式**：
>    - **第一部分**给出控制器的三类划分（线性控制、非线性控制、基于学习的控制），并逐一对 PID、LQR、H∞、反馈线性化、反步法、SMC、MPC、自适应控制、模糊逻辑、神经网络共 10 种控制器总结主要优点与缺点，末尾给出 10 种控制器在 9 个工程维度上的横向对比矩阵。
>    - **第二部分**以三列表格给出每一种控制器的两类工程改进路径：与其它控制器结合使用的"控制器混合策略举例"，以及通过增加算法、优化器、观测器或结构改造来强化控制器本身的"现有控制器改进策略举例"。
> 4. **调研方式**：本综述由 8 个互不重叠的专题调研单元并行完成，分别负责 PID、LQR、H∞、反馈线性化与反步法、SMC、MPC、自适应控制、模糊逻辑与神经网络，再由统一口径汇总、去重与交叉核验。全部条目均给出可核查的文献来源，来源年份均不晚于 2021 年 5 月。
> 5. **计量口径**：第一部分每种控制器的优点与缺点各列出 9 条；第二部分每种控制器分别列出 15 条以上混合策略与 15 条以上改进策略，全表合计 393 条，条目不做省略式合并。
> 
> ## 目录
> 
> - 第一部分　控制器分类与特性总结
>   - 1.1　三类划分的判据与总体特征
>   - 1.2　PID（比例-积分-微分）控制
>   - 1.3　LQR（线性二次调节器）
>   - 1.4　H∞（H-无穷）控制
>   - 1.5　反馈线性化（Feedback Linearization）
>   - 1.6　反步法（Backstepping）
>   - 1.7　滑模控制（SMC）
>   - 1.8　模型预测控制（MPC）
>   - 1.9　自适应控制（Adaptive Control）
>   - 1.10　模糊逻辑控制（Fuzzy Logic）
>   - 1.11　神经网络控制（Neural Network）
>   - 1.12　十种控制器横向对比矩阵
> - 第二部分　性能改进策略汇总表
> - 参考文献
> 
> # 第一部分　控制器分类与特性总结
> 
> ## 1.1　三类划分的判据与总体特征
> 
> ### 1.1.1　被控对象特征与建模基础
> 
> 四旋翼是典型的欠驱动非线性系统：6 个自由度（三轴位置与三轴姿态）只由 4 个旋翼转速产生的 4 个独立控制输入驱动，俯仰与滚转力矩通过总推力方向的改变间接影响水平位置，因此位置通道与姿态通道之间存在强耦合。常用的建模路线是牛顿-欧拉方程或拉格朗日方程，得到含非线性惯性项、陀螺力矩、气动阻力与未知扰动的六自由度模型；工程实现中通常再做时标分离（time-scale separation），把系统拆成"位置外环 + 姿态内环"的级联结构，内环带宽显著高于外环。模型不确定性的主要来源包括：质量、惯量与气动系数随载荷和环境变化，旋翼桨叶挥舞与地面效应，电池电压下降引起的推力增益漂移，风扰与近壁面效应，以及传感器噪声、执行器饱和与传输延迟（Kim, Gadsden & Wilkerson, 20

**报告结尾（含参考文献）**：

> [635] Zeng, J., Zhang, B., & Sreenath, K. (2020). Safety-Critical Model Predictive Control with Discrete-Time Control Barrier Function. *arXiv:2007.11718*（v1: 2020-07-22; v3: 2021-03-23；亦见 2021 American Control Conference）. https://arxiv.org/abs/2007.11718
> [636] Zhang B, Furukawa S, Lim H. **Study on automatic PID gain adjustment for a four-rotor flying robot using neural network**. *2019 4th Asia-Pacific Conference on Intelligent Robot Systems (ACIRS)*, 2019. DOI: https://doi.org/10.1109/ACIRS.2019.8936012
> [637] Zhang R., Ji H. (2020). Robust adaptive trajectory tracking control for uncertain quadrotor unmanned aerial vehicles in the presence of actuator saturation. *2020 5th International Conference on Control and Robotics Engineering (ICCRE)*. DOI: [10.1109/ICCRE49379.2020.9096442](https://doi.org/10.1109/ICCRE49379.2020.9096442)
> [638] Zhang T., Ge S.S., Hang C.C. Adaptive neural network control for strict-feedback nonlinear systems using backstepping design. *Automatica*, 2000. DOI: 10.1016/S0005-1098(00)00116-3
> [639] Zhang, B., Sun, X., Liu, S., & Deng, X. (2019). Recurrent Neural Network-Based Model Predictive Control for Multiple Unmanned Quadrotor Formation Flight. *International Journal of Aerospace Engineering*, 2019, 7272387. DOI: 10.1155/2019/7272387
> [640] Zhang, B., Sun, X., Liu, S., & Deng, X. (2020). Adaptive model predictive control with extended state observer for multi-UAV formation flight. *International Journal of Adaptive Control and Signal Processing*, 34(10). DOI: 10.1002/acs.3145
> [641] Zhang, J.; Li, Y.; Fei, W.; et al. (2020). *Neural Network-Based Nonlinear Fixed-Time Adaptive Practical Tracking Control for Quadrotor Unmanned Aerial Vehicles.* Complexity, 2020, 8828453. DOI: 10.1155/2020/8828453
> [642] Zhang, T., Kahn, G., Levine, S., & Abbeel, P. (2016). Learning deep control policies for autonomous aerial vehicles with MPC-guided policy search. In *2016 IEEE International Conference on Robotics and Automation (ICRA)*. DOI: 10.1109/ICRA.2016.7487175
> [643] Zhao B., Xian B., Zhang Y., et al. Immersion and invariance based adaptive attitude tracking control of a quadrotor UAV in the presence of parametric uncertainty. *33rd Chinese Control Conference (CCC)*, 2014. DOI: 10.1109/chicc.2014.6896925
> [644] Zhao Y, Cao Y, Fan Y. **Disturbance observer-based attitude control for a quadrotor**. *2017 4th International Conference on Information, Cybernetics and Computational Social Systems (ICCSS)*, 2017. DOI: https://doi.org/10.1109/ICCSS.2017.8091439
> [645] Zhao, L., Dai, L., Xia, Y., Li, P. *Attitude control for quadrotors subjected to wind disturbances via active disturbance rejection control and integral sliding mode control.* Mechanical Systems and Signal Processing, 2019, 129: 531–545. DOI: 10.1016/j.ymssp.2019.04.040
> [646] Zhao, S., An, H., Zhang, D., & Shen, L. (2014). A new feedback linearization LQR control for attitude of quadrotor. *13th International Conference on Control Automation Robotics & Vision (ICARCV)*. DOI: 10.1109/ICARCV.2014.7064553
> [647] Zhao, W.; Queralta, J. P.; Westerlund, T. (2020). *Sim-to-Real Transfer in Deep Reinforcement Learning for Robotics: a Survey.* 2020 IEEE Symposium Series on Computational Intelligence (SSCI), 737–744. DOI: 10.1109/SSCI47803.2020.9308468
> [648] Zhou H., Pei H., Zhao Y. Trajectory tracking control of a small unmanned helicopter using MPC and backstepping. *American Control Conference (ACC)*, 2011. DOI: 10.1109/acc.2011.5991230
> [649] Zhou J, Deng R, Shi Z, Zhong Y. **Robust cascade PID attitude control of quadrotor helicopters subject to wind disturbance**. *2017 36th Chinese Control Conference (CCC)*, 2017. DOI: https://doi.org/10.23919/ChiCC.2017.8028397
> [650] Zhou L., Zhang B. Quadrotor UAV flight control using backstepping adaptive controller. *IEEE 6th International Conference on Control Science and Systems Engineering (ICCSSE)*, 2020. DOI: 10.1109/iccsse50399.2020.9171967
> [651] Zhou L., Zhang J., Dou J., et al. A fuzzy adaptive backstepping control based on mass observer for trajectory tracking of a quadrotor UAV. *International Journal of Adaptive Control and Signal Processing*, 2018. DOI: 10.1002/acs.2937
> [652] Zhou L., Zhang J., Dou J., Wen B. (2018). A fuzzy adaptive backstepping control based on mass observer for trajectory tracking of a quadrotor UAV. *International Journal of Adaptive Control and Signal Processing*, 32(12). DOI: [10.1002/acs.2937](https://doi.org/10.1002/acs.2937)
> [653] Zhu G., Wang S., Sun L., Ge W. (2020). Output feedback adaptive dynamic surface sliding-mode control for quadrotor UAVs with tracking error constraints. *Complexity*, 2020. DOI: [10.1155/2020/8537198](https://doi.org/10.1155/2020/8537198)
> [654] Zhu, B., & Huo, W. (2010). Trajectory linearization control for a quadrotor helicopter. *IEEE ICCA 2010*. DOI: 10.1109/ICCA.2010.5524293
> [655] Zhu, B., Chen, M., & Li, T. (2020). Robust Constrained Trajectory Tracking Control for Quadrotor Unmanned Aerial Vehicle Based on Disturbance Observers. *ASME Journal of Dynamic Systems, Measurement, and Control*, 142(12), 121004. DOI: 10.1115/1.4047692
> [656] Ziegler J G, Nichols N B. **Optimum settings for automatic controllers**. *Transactions of the ASME*, 1942. DOI: https://doi.org/10.1115/1.4019264
> [657] Zietkiewicz J. Feedback linearization and LQ based constrained predictive control. In: *Frontiers of Model Predictive Control*, InTech, 2012. DOI: 10.5772/38788
> [658] Zou, Y. *Nonlinear robust adaptive hierarchical sliding mode control approach for quadrotors.* International Journal of Robust and Nonlinear Control, 2017, 27(6): 925–941. DOI: 10.1002/rnc.3607
> [659] Zulu A, John S. **A review of control algorithms for autonomous quadrotors**. *Open Journal of Applied Sciences*, 2014. DOI: https://doi.org/10.4236/ojapps.2014.414053
> [660] Zuo Z. (2012). Adaptive trajectory tracking control design with command filtered compensation for a quadrotor. *Journal of Vibration and Control*, 19(1). DOI: [10.1177/1077546311431270](https://doi.org/10.1177/1077546311431270)
> [661] Zuo Z. Adaptive trajectory tracking control design with command filtered compensation for a quadrotor. *Journal of Vibration and Control*, 2012. DOI: 10.1177/1077546311431270
> [662] Åström K J, Hägglund T. **Advanced PID Control**. *ISA – Instrumentation, Systems and Automation Society*, 2006. ISBN 978-1-55617-942-6；OCLC: https://search.worldcat.org/title/60557376
> [663] Åström K J, Hägglund T. **Revisiting the Ziegler–Nichols step response method for PID control**. *Journal of Process Control*, 2004. DOI: https://doi.org/10.1016/j.jprocont.2004.01.002
> [664] Åström K.J. (1983). Theory and applications of adaptive control—A survey. *Automatica*, 19(5). DOI: [10.1016/0005-1098(83)90002-X](https://doi.org/10.1016/0005-1098(83)90002-X)
> [665] Çimen, T. (2008). State-dependent Riccati equation (SDRE) control: A survey. *IFAC Proceedings Volumes*. DOI: 10.3182/20080706-5-KR-1001.00635
> [666] Çimen, T. (2010). Systematic and effective design of nonlinear feedback controllers via the state-dependent Riccati equation (SDRE) method. *Annual Reviews in Control*. DOI: 10.1016/j.arcontrol.2010.03.001
> [667] Özbek, N. S.; Önkol, M.; Efe, M. Ö. *Feedback control strategies for quadrotor-type aerial robots: a survey.* Transactions of the Institute of Measurement and Control, 2016, 38(5). DOI: 10.1177/0142331215608427
> [668] Şen M A, Kalyoncu M. **Optimal tuning of PID controller using grey wolf optimizer algorithm for quadruped robot**. *Balkan Journal of Electrical and Computer Engineering*, 2018.（算法层面代表文献，非四旋翼专用）DOI: https://doi.org/10.17694/bajece.401992
> [669] 李蒙; 石泳; 刘莉. *基于鲁棒 H∞ 的无人机飞行控制系统设计及实现.* 北京理工大学学报, 2016, 36(8). DOI: 10.15918/j.tbit1001-0645.2016.08.007

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 12

**题目**：A Review of the Application of Artificial Intelligence (AI) in Government Decision-Making（Finance & Business）

**禁用的来源文章**：Navigating Governmental Choices: A Comprehensive Review of Artificial Intelligence's Impact on Decision-Making

- https://www.mdpi.com/2227-9709/11/3/64
- https://doi.org/10.3390/informatics11030064
- https://text2fa.ir/wp-content/uploads/Text2fa.ir-Navigating-Governmental-Choices-A-Comprehensive-R.pdf
- https://pure.ups.edu.ec/en/publications/navigating-governmental-choices-a-comprehensive-review-of-artific
- https://www.semanticscholar.org/paper/Navigating-Governmental-Choices%3A-A-Comprehensive-of-Caiza-Sangu%C3%B1a/ef838c9723caeba6042168ec17c02358b5a50721
- https://ouci.dntb.gov.ua/en/works/lxdPJKEl/

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 66 个地址，最多的站点**：digital-strategy.ec.europa.eu 7，eur-lex.europa.eu 4，bidenwhitehouse.archives.gov 4，cac.gov.cn 4，oecd.ai 4，nist.gov 3，gao.gov 3，unesco.org 2，nao.org.uk 2，trumpwhitehouse.archives.gov 2，federalregister.gov 2，tech.gov.sg 2

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 人工智能在政府决策中的应用：2019–2023 年综合综述
    ## 摘要
    ## 1. 引言：范围、方法与分析框架
    ### 1.1 范围
    ### 1.2 方法
    ### 1.3 分析框架
    ## 2. 人工智能在政府运作中的作用
    ### 2.1 提升效率：数据处理、文档处理与欺诈侦测
    ### 2.2 改善服务供给：聊天机器人、智能助理与一站式服务
    ### 2.3 支撑政策制定与决策：预测分析、模拟与证据合成
    ### 2.4 三个标志性应用领域
    #### 2.4.1 公共服务聊天机器人
    #### 2.4.2 安防领域的面部识别
    #### 2.4.3 公共交通中的自动驾驶
    ### 2.5 成效评估：证据、差距与局限
    ### 2.6 小结
    ## 3. 政府中人工智能的监管框架：欧盟、美国与中国的比较
    ### 3.1 欧盟：以基本权利为锚的风险分级统一立法
    ### 3.2 美国：部门化、轻触式与"政府自身使用"的双轨路径
    ### 3.3 中国：国家主导、安全可控与算法备案
    ### 3.4 三地比较
    ### 3.5 跨辖区张力与趋同
    ## 4. 挑战与伦理考量
    ### 4.1 技术挑战
    ### 4.2 社会挑战
    ### 4.3 伦理挑战
    ### 4.4 缓解措施与治理实践
    ### 4.5 小结
    ## 5. 结论与建议
    ### 5.1 主要结论
    ### 5.2 对政策制定者的建议
    ### 5.3 展望（超出本报告窗口的简短说明）
    ## 参考文献
    ### 欧盟
    ### 美国
    ### 中国
    ### 国际组织与软法
    ### 政府实践、案例与评估
    ### 案例、调查与学术文献

**报告开头**：

> # 人工智能在政府决策中的应用：2019–2023 年综合综述
> 
> **报告范围**：2019 年 1 月至 2023 年 12 月（部分 2024 年后的制度性发展仅作为背景注明）
> **结构**：第一，人工智能在政府运作中的作用；第二，欧盟、美国、中国的监管框架比较；第三，技术、社会与伦理三类挑战。
> 
> ---
> 
> ## 摘要
> 
> 2019–2023 年，人工智能（AI）从政府数字化的边缘试验走向公共管理的核心议题。三股力量同时推进：**技术可用性**（机器学习成熟化与 2022 年底生成式 AI 的爆发）、**行政需求**（财政压力、公共服务需求上升、疫情冲击）与**地缘政治竞争**（美、中、欧围绕算力、标准与治理话语权的竞争）。本报告的核心发现是：
> 
> 1. **在运作层面**，AI 已广泛应用于数据处理与欺诈侦测、公共服务聊天机器人、政策分析、安防与交通等场景，并产生了可观的效率收益；但独立、可核验的量化证据仍然稀缺，多数"成功案例"来自供应商或政府自述，且政府整体采用率仍低于宣传水平。例如，美国联邦机构报告的 AI 用例从 2020 年的 571 个增至 2023 年的约 1200 个，但真正投入生产的只是少数[18][19]；英国国家审计署（NAO）对 2023 年状况的调查显示，AI 尚未在政府中广泛使用，约 70% 的机构处于试点或规划阶段[45]。
> 2. **在监管层面**，三大辖区形成了三种不同的治理逻辑：欧盟采取**基于风险、以基本权利为锚的事前统一立法**（《人工智能法案》2021 年提案、2023 年 12 月政治协议）[4][6][7]；美国采取**部门化、轻触式、事后执法**的路径，辅以针对联邦政府自身用 AI 的行政命令与清单制度[10][11][13][14][15]；中国采取**国家主导、发展与安全并重、算法备案与内容治理**的路径[25][26][27][28]。三者在"风险管理、文档留痕、人类监督"上趋同，但在监管时机、价值锚点以及"政府自身使用 AI 是否受规制"上显著分化。
> 3. **在挑战层面**，技术瓶颈（遗留系统、数据质量、采购锁定、人才短缺）、社会张力（岗位替代、信任赤字、数字鸿沟、监控担忧）与伦理风险（黑箱、算法偏见、问责真空、正当程序）相互交织。荷兰 SyRI 与儿童福利补贴丑闻、澳大利亚 Robodebt、英国 A-level 评分算法、美国底特律面部识别误捕等案例表明：**AI 在公共决策中的失败往往不是技术故障，而是治理失败**[73][75][76][78][81]。
> 
> ---
> 
> ## 1. 引言：范围、方法与分析框架
> 
> ### 1.1 范围
> 
> 本综述聚焦 2019–2023 年。选择这一窗口的理由是：2019 年是 AI 治理"制度化元年"——OECD AI 原则、欧盟《可信 AI 伦理指南》、中国《新一代人工智能治理原则》均在这一年出台；2023 年则是生成式 AI 冲击与欧盟《人工智能法案》政治协议之年。此后的立法生效与执法（如欧盟 AI 法案 2024 年生效、美国第 14110 号行政命令 2025 年被撤销）只在必要处作为背景提及[9][15][43][44]。
> 
> ### 1.2 方法
> 
> 本报告基于公开可得的政府文件、国际组织报告、监管文本、学术论文与主流媒体报道，优先采用一手来源（欧盟委员会、欧洲议会、美国联邦公报与白宫档案、NIST、GAO、中国国家网信办、OECD、UNESCO、国际劳工组织、世界银行等）。对存在争议或仅由供应方报告的数据，均在文中标明来源与不确定性。
> 
> ##

**报告结尾（含参考文献）**：

> [80] MIT Technology Review, *Amazon ditched AI recruitment software because it was biased against women*, 2018. https://www.technologyreview.com/2018/10/10/139858/amazon-ditched-ai-recruitment-software-because-it-was-biased-against-women
> [81] Politics.co.uk, *Government U-turns on A-level results, scraps algorithm for teacher grades*, 2020. https://www.politics.co.uk/history/government-u-turns-on-a-level-results-scraps-algorithm-for-teacher-grades/
> [82] The Guardian, *Ofqual head Sally Collier resigns over exams fiasco*, August 2020. https://www.theguardian.com/education/2020/aug/25/ofqual-head-sally-collier-resigns-over-exams-fiasco
> [83] U.S. District Court (E.D. Michigan), *Opinion in litigation concerning Michigan's MiDAS unemployment fraud detection system*. https://www.mied.uscourts.gov/PDFFIles/17-10657OPN.pdf
> [84] Michigan Public, *State says it will pay $20 million to people wrongly accused of unemployment fraud*, October 2022. https://www.michiganpublic.org/criminal-justice-legal-system/2022-10-20/state-says-it-will-pay-20-million-to-people-wrongly-accused-of-unemployment-fraud
> [85] *State v. Loomis*, Wisconsin Supreme Court, 2016 (via FindLaw). https://caselaw.findlaw.com/court/wi-supreme-court/1742124.html
> [86] GDPR Article 22, *Automated individual decision-making, including profiling*. https://gdpr-info.eu/art-22-gdpr/
> [87] NASCIO & McKinsey, *Generative AI and Its Impact on State IT Workforces*, 2024. https://www.nascio.org/wp-content/uploads/2024/04/NASCIO_McKinsey_GenAI-and-Impact-on-State-IT-Workforces_2024.pdf
> [88] Pew Research Center, *Growing Public Concern About the Role of Artificial Intelligence in Daily Life*, August 2023. https://www.pewresearch.org/short-reads/2023/08/28/growing-public-concern-about-the-role-of-artificial-intelligence-in-daily-life/
> [89] Edelman, *2022 Special Report: Trust in Technology*, 2022. https://www.edelman.com/uk/2022-special-report-trust-technology
> [90] *The Problem of Many Hands in Public Administration*. https://philarchive.org/archive/GRITPO-51
> [91] Mittelstadt et al., *The ethics of algorithms: Mapping the debate*, Turing Institute. https://www.turing.ac.uk/news/publications/ethics-algorithms-mapping-debate
> [92] Ada Lovelace Institute, *Examining the Black Box: Tools for Assessing Algorithmic Systems*, 2020. https://www.adalovelaceinstitute.org/report/examining-the-black-box-tools-for-assessing-algorithmic-systems/
> [93] Cobbe, Lee & Singh, *Reviewable Automated Decision-Making*, ACM FAccT, 2021. https://dl.acm.org/doi/pdf/10.1145/3442188.3445921
> [94] Ada Lovelace Institute / AI Now Institute / Open Government Partnership, *Algorithmic Accountability for the Public Sector*, 2021. https://www.adalovelaceinstitute.org/report/algorithmic-accountability-public-sector/
> [95] UK Government, *Guidelines for AI Procurement*, 2020. https://www.gov.uk/government/publications/guidelines-for-ai-procurement
> [96] ENISA, *AI Cybersecurity Challenges*, December 2020. https://www.europarl.europa.eu/cmsdata/222223/ENISA%20AI%20Cybersecurity_AIDA_22012021.pdf
> [97] CEDMO, *How AI-generated content influenced parliamentary elections in Slovakia*, 2023. https://cedmohub.eu/how-ai-generated-content-influenced-parliamentary-elections-in-slovakia-the-slovak-police-will-investigate-the-recording-for-a-third-time/
> [98] Privacy International, *Submission to UN OHCHR on privacy and AI*. https://www.ohchr.org/sites/default/files/Documents/Issues/DigitalAge/Submissions/CSOs/Privacy-International.pdf
> [99] Biometric Update, *Clearview AI faces more legal uncertainty in UK and US*. https://www.biometricupdate.com/202506/clearview-ai-faces-more-legal-uncertainty-in-uk-and-us
> [100] Biometric Update, *UK police claim study support to resume live facial recognition deployments*, April 2023. https://www.biometricupdate.com/202304/uk-police-claim-study-support-to-resume-live-facial-recognition-deployments
> [101] Richardson, Schultz & Crawford, *Dirty Data, Bad Predictions: How Civil Rights Violations Impact Police Data, Predictive Policing Systems, and Justice*, FAT* 2019（学术论文，正文引用）.
> [102] Hunton Andrews Kurth, *Swedish Data Protection Authority Issues First Fine Under GDPR*（Trelleborg 市学校面部识别案，2019）. https://www.hunton.com/privacy-and-cybersecurity-law-blog/swedish-data-protection-authority-issues-first-fine-under-gdpr
> [103] ECNS (China News Service), *Beijing's first autonomous minibusses make maiden test voyage*, May 2022. http://www.ecns.cn/m/news/cns-wire/2022-05-11/detail-ihayhruk0766708.shtml
> [104] 成都轨道集团，关于 9 号线全自动运行（GoA4）的官方介绍. https://mall.chengdurail.com/info/1151/34802.htm
> 
> ---
> 
> **说明与局限**
> 
> 1. **时间窗口**：本综述聚焦 2019–2023 年。少数来源（NAO 2024 年报告、AI Index 2024、SHOW 项目 2024 年总结、2024 年通过的欧洲委员会 AI 框架公约与联合国大会决议）发布于 2024 年，但分别评估 2023 年状况或构成 2022–2023 年谈判的结果，已在文中注明。
> 2. **数据可信度**：墨西哥 SAT 的 21.4%、新加坡 OneService 的 80/85/85%、拉脱维亚 UNA 的 44%、多哥 Novissi 的覆盖数字等，均来自项目方、供应商或媒体报道；除 Novissi 有世界银行相对详细的记录外，多数缺乏独立审计。**本报告不提供任何"AI 为政府节省 X%"的总体数字，因为不存在可信的 2019–2023 年全政府口径数据。**
> 3. **案例时间**：COMPAS（2016 年起）、亚马逊招聘工具（2014–2018）、密歇根 MiDAS（2013–2015）早于本报告窗口，但作为算法问责的经典案例纳入，并已标注年份。
> 4. **中国政策文本**以官方中文原文为准，英文译名可能存在差异；其中《算法推荐管理规定》《深度合成管理规定》《生成式人工智能服务管理暂行办法》的公布与施行日期均已核对。
> 5. **Robodebt 数字**（约 43.3 万人、约 17.6 亿澳元非法债务）来自皇家调查委员会最终报告及其报道；荷兰儿童福利补贴丑闻的"约 2.6 万家庭"为广泛报道数字，不同来源口径略有差异。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 13

**题目**：Investigation of Hydroforming Technology（Industrial）

**禁用的来源文章**：A review of emerging hydroforming technologies: design considerations, parametric studies, and recent innovations

- https://jeas.springeropen.com/articles/10.1186/s44147-024-00546-z
- https://www.researchgate.net/publication/385401108_A_review_of_emerging_hydroforming_technologies_design_considerations_parametric_studies_and_recent_innovations
- https://ui.adsabs.harvard.edu/abs/2024JEAS...71..205C/abstract

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 134 个地址，最多的站点**：pmc.ncbi.nlm.nih.gov 14，ebi.ac.uk 11，api.crossref.org 9，thefabricator.com 5，ahssinsights.org 5，api.semanticscholar.org 5，jstage.jst.go.jp 5，sciencedirect.com 4，mdpi.com 4，strathprints.strath.ac.uk 4，api.openalex.org 3，oerlikon.com 3

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 液压成形（Hydroforming）技术资料汇编
    ## 材料选择与常见制造缺陷分析
    # 第一部分　常用材料分析
    ## 1.0 四种材料横向对比（速览）
    ## 1.1 高强度钢（HSS / AHSS）
    ### 材料特性
    ### 成形挑战
    ### 主要应用（含具体实例）
    ### 关键验证数据与量化案例
    ## 1.2 高强度铝合金
    ### 材料特性
    ### 成形挑战
    ### 主要应用（含具体实例）
    ### 关键验证数据与量化案例
    ## 1.3 镁合金
    ### 材料特性
    ### 成形挑战
    ### 主要应用（含具体实例）
    ### 关键验证数据与量化案例
    ## 1.4 钛合金
    ### 材料特性
    ### 成形挑战
    ### 主要应用（含具体实例）
    ### 关键验证数据与量化案例
    ## 1.5 选材决策要点（小结）
    # 第二部分　常见缺陷、成因及对策
    ## 2.1 表面缺陷（Surface defects）
    ### 主要成因
    ### 建议的解决方法
    ### 关键数据与量化判据
    ## 2.2 回弹（Springback）
    ### 主要成因
    ### 建议的解决方法
    ### 关键数据与量化判据
    ## 2.3 起皱（Wrinkling）
    ### 主要成因
    ### 建议的解决方法
    ### 关键数据与量化判据
    ## 2.4 变薄（Thinning）
    ### 主要成因

**报告开头**：

> # 液压成形（Hydroforming）技术资料汇编
> ## 材料选择与常见制造缺陷分析
> 
> ---
> 
> **报告性质与范围说明**
> 
> - 本报告面向工艺选型与供应商技术评估，覆盖**管材液压成形（Tube Hydroforming, THF）**与**板材液压成形（Sheet Hydroforming, SHF，含柔性成形/Flexform、液压机械拉深）**两类主流工艺。
> - 液压成形的基本原理：以高压液体（通常为水+防锈剂+润滑剂的乳化液）作为传力介质，使管坯或板坯贴合模具型腔成形。管材液压成形的两个核心控制变量是**内压（internal pressure）**与**轴向进给/轴压（axial feed / axial force）**，二者随时间的组合称为**加载路径（loading path）**，它几乎决定了所有缺陷的走向。
> - 报告中力学性能为**典型文献/手册值**，用于量级比较；实际选材必须以钢厂/铝厂质保书与试模数据为准。
> - 全文引用来源见文末「参考来源」，正文中以 `[n]` 标注。
> 
> ---
> 
> # 第一部分　常用材料分析
> 
> ## 1.0 四种材料横向对比（速览）
> 
> | 维度 | 高强度钢 HSS/AHSS | 高强度铝合金 | 镁合金 | 钛合金 |
> |---|---|---|---|---|
> | 典型牌号 | DP600/DP780/DP980、CP800、TRIP、22MnB5 | 5083、5754、6061、6082、7075 | AZ31B、AZ61、AZ80、ZK60 | CP-Ti Gr2、Ti-3Al-2.5V、Ti-6Al-4V |
> | 密度 (g/cm³) | ≈7.85 | ≈2.66–2.81 | ≈1.74–1.77 | ≈4.43 |
> | 弹性模量 E (GPa) | ≈210 | ≈68–72 | ≈45 | ≈110–114 |
> | 典型抗拉强度 (MPa) | 600–1500 | 290–570 | 260–330 | 345–950 |
> | 室温成形性 | 中～好（DP 较好，MS/PHS 差） | 5xxx 尚可；6xxx/7xxx 差 | 差（必须温热） | 差（通常需热成形） |
> | 回弹倾向 | 中（强度高但 E 高） | 高（E 仅钢的 1/3） | 很高（E 最低） | 高（强度高、加工硬化强） |
> | 液压成形温度 | 室温为主，可温热 | 室温 / 温热 200–300 °C（已验证至 300 °C） | 温热 250 °C（管材/板材试验）；拉伸表征 300–450 °C | 热成形：Ti-3Al-2.5V 超塑性窗口 820–900 °C（最优 870 °C） |
> | 相对成本 | 低（最低） | 中 | 中高（管坯供应少） | 很高 |
> | 量产成熟度 | 最高 | 高（欧美、中国均在扩产） | 低（研发/小批量为主） | 低（航空航天小批量） |
> 
> ---
> 
> ## 1.1 高强度钢（HSS / AHSS）
> 
> ### 材料特性
> 
> - **组织与牌号体系**：先进高强钢（AHSS）通过多相组织获得强度，主要包括双相钢（DP，铁素体+马氏体）、相变诱导塑性钢（TRIP，含残余奥氏体）、复相钢（CP）、马氏体钢（MS）以及热成形/冲压硬化钢（PHS，典型 22MnB5）。液压成形管材最常用的是 **DP600、DP780**，近年向 **DP980、CP800、MS 级**延伸。[1][5][6]
> - **典型力学性能**：DP780 屈服强度约 500–600 MPa、

**报告结尾（含参考文献）**：

> 32. Mizumura & Kuriyama, 塑性と加工 (JSTP) 53(614):225 (2012)（50% 膨胀率弯管矩形截面液压成形工艺窗口） — https://www.jstage.jst.go.jp/article/sosei/53/614/53_614_225/_article/-char/en
> 33. Chen et al. (2024)（THPC 预成形+压扁、低压液压成形 LPTH、爆破压力） — https://pmc.ncbi.nlm.nih.gov/articles/PMC10971789/
> 34. Pham et al. (2025)（管材 FLD：MMFC2 vs MK、无管材 FLD 国际标准） — https://pmc.ncbi.nlm.nih.gov/articles/PMC12072830/
> 35. Oerlikon Balzers, BALINIT FORMERA（CrN 基 PVD 液压成形模具涂层，**供应商数据**） — https://www.oerlikon.com/balzers/global/en/portfolio/balzers-surface-solutions/pvd-and-pacvd-based-coating-solutions/balinit/crn-based/balinit-formera/
> 36. ISO 12004-2:2021, *Metallic materials — Determination of forming-limit curves for sheet and strip* — https://www.boutique.afnor.org/en-gb/standard/iso-1200422021/metallic-materials-determination-of-forminglimit-curves-for-sheet-and-strip/xs134801/240086
> 37. ASTM E2218-23, *Standard Test Method for Determining Forming Limit Curves* — https://www.dinmedia.de/en/standard/astm-e-2218/368327281
> 38. *FE bursting-failure prediction in bulge forming of a seamed tube*, Finite Elements in Analysis and Design — https://www.sciencedirect.com/science/article/abs/pii/S0168874X03001227
> 
> **材料：补充量化来源**
> 39. Bhadeshia, Cambridge DoITPoMS, *Hydroforming*（管材液压成形内压典型 80–450 MPa） — http://www.phase-trans.msm.cam.ac.uk/2006/hydroforming.html
> 40. Chen et al., *Materials* 15(19):6820 (2022)（B650CL 高强钢轮辋、HIEP 双面加压液压成形） — https://pmc.ncbi.nlm.nih.gov/articles/PMC9572992/
> 41. *Dual Phase Steel Characterization for Tube Bending and Hydroforming Applications*, Materials Science Forum 706-709:2066 (2012)（DP600/780/980 弯曲+压力序列液压成形） — https://doi.org/10.4028/www.scientific.net/msf.706-709.2066
> 42. WardsAuto, *Ford Using Hydroforming to Cut Weight, Costs*（2013 Fusion A/B 柱与车顶纵梁、废料率对比、压力序列液压成形） — https://www.wardsauto.com/news/archive-wards-ford-using-hydroforming-to-cut-weight-costs/781388/
> 43. Talebi-Anaraki et al., *Materials* 15(4):1322 (2022)（UHSS 低压热气体成形 + 模内淬火） — https://pmc.ncbi.nlm.nih.gov/articles/PMC8874987/
> 44. Lee et al., *Trans. Mater. Process.* 13(5):403 (2004)（6061/7075 铝管温热液压成形，室温–300 °C） — https://koreascience.kr/article/JAKO200411922373548.pub?&lang=en
> 45. *Mater. Sci. Forum* 475-479:373 (2005)（6061/7075 铝管高温变形行为，T6-6061 例外） — https://doi.org/10.4028/www.scientific.net/msf.475-479.373
> 46. Zhu et al., *Materials* 16(4):1647 (2023)（AA6061 挤压管成形极限的路径依赖性、PEPS-FLD） — https://pmc.ncbi.nlm.nih.gov/articles/PMC9966077/
> 47. SAE 2004-01-0835（AlMg3.5Mn 管弯曲+液压成形的 Gurson 损伤模型与损伤历史映射） — https://doi.org/10.4271/2004-01-0835
> 48. *Mater. Sci. Eng. A* (2014)（旋压对搅拌摩擦焊铝管成形性的影响） — https://doi.org/10.1016/j.msea.2014.03.125
> 49. Alcoa（via The Auto Channel）, *Audi A8 aluminium space frame*（部分液压成形挤压件，334→267 件） — https://www.theautochannel.com/news/2003/10/30/171755.html
> 50. MotorTrend, *Corvette C6 chassis*（Z06/ZR1 的 4 mm 铝合金液压成形侧梁；铝车架 392 lb vs 502 lb） — https://www.motortrend.com/features/1812-corvette-chassis-dave-hills-superior-evolutionary-c6
> 51. Masood Chaudry et al., *Materials* 11(11):2201 (2018)（AZ31 / AZ31-0.5Ca 室温力学性能、n/r 值、Erichsen、织构与孪晶机制） — https://pmc.ncbi.nlm.nih.gov/articles/PMC6265964/
> 52. SAE 2006-01-0258（AZ31 在 300–450 °C、不同应变速率下的 r 值与失效模式） — https://doi.org/10.4271/2006-01-0258
> 53. *Metals* 10(5):674 (2020)（ZM21 小直径镁管 250 °C 温热液压成形、起皱用作预成形） — https://doi.org/10.3390/met10050674
> 54. *Metals* 11(6):901 (2021)（AZ31B 温热 T 形管液压成形、非均匀温度场优化） — https://doi.org/10.3390/met11060901
> 55. ASME MSEC2013-1084（AZ31 温热液压成形起皱机制、50% 膨胀率） — https://doi.org/10.1115/msec2013-1084
> 56. TRID / SAE 2004-01-1261（2005 福特 GT 镁合金仪表板结构：**AM60 压铸，非液压成形**） — https://trid.trb.org/View/2307235
> 57. Li et al., *Materials* 15(16):5586 (2022)（钛合金板材室温成形性与回弹、高应变速率液压成形） — https://pmc.ncbi.nlm.nih.gov/articles/PMC9414495/
> 58. Yoo & Lee, *Trans. Mater. Process.* 28(1):15 (2019)（Ti-3Al-2.5V 超塑性液压成形+扩散连接、820–900 °C 窗口、自行车车架） — https://koreascience.kr/article/JAKO201910537995885.pub?&lang=en
> 59. Kwame et al., *MATEC Web Conf.* 321:04027 (2020)（工业纯钛 Gr2 边缘成形性：EDM > AWJ ≈ 激光） — https://strathprints.strath.ac.uk/68661/
> 60. Bell et al., ESAFORM 2017（纯钛 Ti35A 液压成形：冯·米塞斯应变与减薄约 3:1 关系） — https://strathprints.strath.ac.uk/63122/
> 
> ---
> 
> *报告完*

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 14

**题目**：Quantitative analysis of the relationship between US stocks, gold, and crude oil within a 10-year period.（Finance & Business）

**禁用的来源文章**：Is this time really different? Flight-to-safety and the COVID-19 crisis

- https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0251752
- https://pubmed.ncbi.nlm.nih.gov/34038444/
- https://scienceon.kisti.re.kr/srch/selectPORSrchArticle.do?cn=NART113997358

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 7 个地址，最多的站点**：cdn.cboe.com 4，fred.stlouisfed.org 2，en.wikipedia.org 1

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 新冠疫情初期美股、黄金与原油市场的波动率关系研究
    ## 摘要
    ## 一、名词解释：VIX、GVZ 与 OVX
    ### 表 1　三个关键波动率指数一览
    ### 1.1 详细说明
    ### 1.2 使用这三个指数时需要注意
    ## 二、数据汇总与描述性统计
    ### 2.1 数据来源与样本构建
    ### 2.2 表 2　全样本日收盘价描述性统计（2010-03-12 至 2021-02-26，N = 2,756）
    ### 2.3 描述性统计解读
    ## 三、三个市场波动率之间的关系
    ### 3.1 水平值相关性矩阵
    ### 3.2 全样本因果关系分析
    ## 四、新冠危机期间的专门分析（2020年2月14日 – 2020年8月6日）
    ### 4.1 危机阶段特征与描述性统计
    ### 4.2 相关性变化：水平值共同运动显著增强
    ### 4.3 VIX 对 GVZ、OVX 的影响是否发生变化？
    ### 4.4 flight-to-safety（逃向安全资产）效应如何体现
    ## 五、结论
    ## 六、数据、方法与可复现性
    ## 七、参考资料

**报告开头**：

> # 新冠疫情初期美股、黄金与原油市场的波动率关系研究
> 
> **——基于 VIX、GVZ、OVX 指数（2010年3月12日 – 2021年2月26日）**
> 
> ---
> 
> ## 摘要
> 
> 本报告使用 Cboe 官方发布的三个波动率指数——**VIX（美股）**、**GVZ（黄金）**、**OVX（原油）**——的日收盘价，研究 2010年3月12日至2021年2月26日（共 2,756 个交易日）三个市场预期波动率之间的水平相关性、因果关系，并专门考察 2020年2月14日至2020年8月6日新冠危机窗口内的变化。主要结论如下：
> 
> 1. **描述性统计**：样本期内 OVX 均值最高（36.16）、波动最大（标准差 19.04），VIX 次之（均值 18.02、标准差 7.48），GVZ 最平稳（均值 17.36、标准差 5.13）。三者均呈右偏、尖峰厚尾分布，OVX 的偏度（5.42）和峰度（50.57）最为极端，且三者的历史最高点全部出现在新冠危机期间（VIX 82.69、GVZ 48.98、OVX 325.15）。
> 2. **全样本相关性**：水平值相关系数为 VIX–GVZ **0.678**、VIX–OVX **0.677**、GVZ–OVX **0.445**；VIX 与两个商品波动率指数的相关程度几乎相同。
> 3. **全样本因果关系（Granger 因果检验）**：方向以 **VIX → GVZ、VIX → OVX** 为主，且在各滞后阶数（1/2/5/10 日）上稳健；GVZ、OVX 基本不能预测 VIX。此外存在 **OVX → GVZ** 的显著传导（尤其在危机前样本），即原油波动率会向黄金波动率溢出，但黄金波动率对原油波动率的反向影响较弱。
> 4. **新冠危机的变化**：三个指数水平值的共同运动显著增强——VIX–GVZ 相关由 0.618 升至 **0.852**，GVZ–OVX 由 0.304 升至 **0.704**，VIX–OVX 由 0.495 升至 **0.660**（Fisher z 检验均在 1% 水平显著）；但日收益率相关性几乎不变，说明变化主要来自"持续性的恐慌水平共同抬升"，而非日内反应函数改变。VIX 对 OVX 的同期冲击敏感度由 0.271 升至 **0.484**（近乎翻倍），对 GVZ 的同期敏感度基本稳定（0.283 → 0.307）；在控制原油波动后，黄金波动率对 VIX 的标准化敏感度保持约 0.34，而原油波动率对 VIX 的敏感度明显上升。
> 5. **flight-to-safety（逃向安全资产）效应的体现**：危机期间黄金波动率与美股恐慌的联系达到样本内最高水平，黄金 ETF 出现创纪录流入（2020年一季度 +298 吨，总持仓创 3,185 吨纪录），金价创历史新高；在 VIX 与 OVX 都已大幅回落后，GVZ 仍保持相对高位（2020年8月6日 GVZ 27.36 > VIX 22.65），说明黄金的避险/对冲需求具有持续性。原油则相反：OVX 因需求崩塌与沙特-俄罗斯价格战升至 325.15 的历史极值，WTI 一度出现负价格——原油是被抛售的风险资产，而非避险资产。危机期间 VIX 上行冲击对 GVZ、OVX 的传导明显强于 VIX 下行冲击，符合"恐慌时逃向安全资产"的非对称特征。
> 
> > **合规说明**：按研究要求，本报告全程未访问、未引用研究任务中指定排除的文献及其任何转载/摘要页面；所有数据与结论均来自本研究独立下载的公开数据与可核验的公开资料。
> 
> ---
> 
> ## 一

**报告结尾（含参考文献）**：

> 18. Bloomberg/Mining.com, *Gold volatility surges to most since 2008 on global market spasm*, 2020-03-18：https://www.mining.com/web/gold-volatility-surges-to-most-since-2008-on-global-market-spasm/
> 19. World Gold Council, *Gold Demand Trends Q1 2020*：https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-q1-2020
> 20. World Gold Council, *Gold Demand Trends Q2 2020*：https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-q2-2020
> 21. World Gold Council, *The gold price rallies with record ETF inflows while COVID-19 hits consumer demand in H1*：https://www.gold.org/news-and-events/press-releases/gold-price-rallies-record-etf-inflows-while-covid-19-hits-consumer
> 22. Reuters/Financial Post, *Gold falls as cash dash, strong dollar override stimulus*：https://financialpost.com/pmn/business-pmn/gold-falls-as-cash-dash-strong-dollar-override-stimulus-3
> 23. CNBC, *Gold falls below $1,500 as it is dragged into the global market rout*, 2020-03-16：https://www.cnbc.com/2020/03/16/gold-falls-below-1500-as-it-is-dragged-into-the-global-market-rout.html
> 24. BBC News, *Coronavirus: How the pandemic has changed the world economy*：https://www.bbc.com/news/business-51706225
> 25. World Energy, *Oil Prices Dive as Saudi Arabia Takes Aim at Russian Production*：https://www.world-energy.org/article/7250.html
> 26. AFR, *Gold's record-breaking run a boon for ETFs*, 2020-08-07：https://www.afr.com/markets/equity-markets/gold-s-record-breaking-run-a-boon-for-etfs-20200807-p55jhd
> 27. Federal Reserve, FOMC 声明（2020-03-15 降息至零并重启 QE）：https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm
> 28. Federal Reserve, 无限量量化宽松声明（2020-03-23）：https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323a.htm
> 29. Federal Reserve, *Monetary Policy since the Onset of the COVID-19 Pandemic*（会议材料）：https://www.federalreserve.gov/monetarypolicy/files/monetary20200315a1.pdf
> 30. New York Fed, *The Federal Reserve and U.S. Treasury Did Not Intervene in FX Markets During the First Quarter*（2020-05-14）：https://www.newyorkfed.org/newsevents/news/markets/2020/20200514
> 31. BIS, *Working Paper No. 856*：https://www.bis.org/publ/work856.htm
> 32. BIS, *Quarterly Review*, March 2020：https://www.bis.org/publ/qtrpdf/r_qt2003.htm
> 
> **学术文献与背景资料（均已打开核对）**
> 
> 33. NBER Working Paper w19095, *Flight-to-Safety 事件与黄金对冲作用*：https://www.nber.org/system/files/working_papers/w19095/revisions/w19095.rev1.pdf
> 34. New York Fed Staff Report No. 1026：https://resources.newyorkfed.org/medialibrary/media/research/staff_reports/sr1026.pdf
> 35. Chen, He & Yu, *The Information Content of OVX for Crude Oil Returns Analysis and Risk Measurement*, Annals of Data Science (2015)：https://rd.springer.com/article/10.1007/s40745-015-0058-4
> 36. *Does the COVID-19 pandemic affect the asset allocation performance?*, Humanities and Social Sciences Communications (2025)：https://www.nature.com/articles/s41599-025-05258-0
> 37. RePEc/IDEAS 作者页（含 Troster, Bouri & Roubaud, *A quantile regression analysis of flights-to-safety with implied volatilities*, Resources Policy, 2019 等文献条目）：https://ideas.repec.org/f/c/pro1069.html
> 38. NBER Working Paper w27122（新冠疫情经济影响）：https://www.nber.org/papers/w27122
> 
> **百科与背景条目（均已打开核对）**
> 
> 39. Wikipedia, *VIX*：https://en.wikipedia.org/wiki/VIX
> 40. Wikipedia, *Flight-to-quality*：https://en.wikipedia.org/wiki/Flight-to-quality
> 41. Wikipedia, *2020 stock market crash*：https://en.wikipedia.org/wiki/2020_stock_market_crash
> 42. Wikipedia, *2020 Russia–Saudi Arabia oil price war*：https://en.wikipedia.org/wiki/2020_Russia%E2%80%93Saudi_Arabia_oil_price_war
> 43. Wikipedia, *COVID-19 recession*：https://en.wikipedia.org/wiki/COVID-19_recession
> 44. Wikipedia, *Volatility index*：https://en.wikipedia.org/wiki/Volatility_index
> 
> > 说明：上述链接均为本研究实际抓取并通过正文关键词核对（HTTP 200 且可提取正文）的页面；部分媒体网站（Reuters、Bloomberg、ScienceDirect 等）对自动抓取返回 403/401，其内容仅作为检索线索，未在报告中作为唯一依据引用。全部结论以 Cboe 官方数据与本研究计算结果为准。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 15

**题目**：A Survey of Population-Based Deep Reinforcement Learning（Software Development）

**禁用的来源文章**：A Survey on Population-Based Deep Reinforcement Learning

- https://www.mdpi.com/2227-7390/11/10/2234
- https://ideas.repec.org/a/gam/jmathe/v11y2023i10p2234-d1143662.html
- https://encyclopedia.pub/entry/44828
- https://www.mdpi.com/2227-7390/11/10/2234/reprints

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 13 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 263 个地址，最多的站点**：arxiv.org 70，ar5iv.labs.arxiv.org 32，proceedings.mlr.press 16，api.semanticscholar.org 16，api.crossref.org 11，export.arxiv.org 10，nature.com 7，html.duckduckgo.com 7，raw.githubusercontent.com 6，proceedings.neurips.cc 5，dblp.org 5，static-content.springer.com 5

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 基于群体的深度强化学习（PB-DRL）算法调研报告
    ## 一、调研范围、方法与阅读说明
    ### 1.1 调研对象
    ### 1.2 方法与来源
    ### 1.3 阅读提示
    ## 二、类别介绍与发展脉络
    ### 2.1 朴素自博弈（Naive Self-Play）
    ### 2.2 虚拟自博弈（Fictitious Self-Play）与均衡求解
    ### 2.3 群体博弈与对手采样（Population Play / Opponent Sampling）
    ### 2.4 基于种群的训练与进化方法（Population-Based / Evolutionary RL）
    ### 2.5 通用框架：PSRO 家族（Policy Space Response Oracles）
    ### 2.6 发展脉络小结
    ## 三、算法比较表
    ## 四、横向对比与选型建议
    ### 4.1 四条主轴上的快速定位
    ### 4.2 选型建议
    ## 五、名称考证与重要更正（必读）
    ## 六、参考文献（按算法分组）
    ### 朴素自博弈
    ### 虚拟自博弈（FP / FSP / NFSP）
    ### ED（Exploitability Descent）
    ### δ-Uniform FSP / Prioritized FSP / PP
    ### FCP / Hidden-Utility Self-Play
    ### PBT / MERL / CERL / DERL
    ### PSRO 家族

**报告开头**：

> # 基于群体的深度强化学习（PB-DRL）算法调研报告
> 
> **范围：截至 2023 年初的主要算法与框架 | 覆盖 19 个算法 | 全部结论回溯一手文献**
> 
> ---
> 
> ## 一、调研范围、方法与阅读说明
> 
> ### 1.1 调研对象
> 
> 本报告对以下 19 个算法逐一给出「所属类别 / 核心思想与机制 / 主要优点 / 主要缺点与局限」，并在报告开头对它们所属的 5 大类方法（朴素自博弈、虚拟自博弈及其均衡求解、群体博弈与对手采样、基于种群的训练与进化方法、PSRO 通用框架）作系统介绍：
> 
> > Naive SP、Fictitious Play、FSP、NFSP、ED、δ-Uniform FSP、Prioritized FSP、PP、FCP、Hidden-Utility Self-Play、PBT、MERL、CERL、DERL、PSRO、PSROηN、Diverse PSRO、Pipeline PSRO、α-PSRO
> 
> ### 1.2 方法与来源
> 
> - **时间边界**：核心内容截至 2023 年初；个别用于名称考证、机制补全或说明后续发展的文献会在正文中标注年份（如 2024 年的 PSRO 综述、2025 年的 ApproxED），不改变本报告的时间边界。
> - **来源要求**：所有机制、结论与实验数字均来自一手来源（原始论文的 arXiv / OpenReview / PMLR / NeurIPS / ICML / ICLR / IJCAI / Nature 官方页面、官方代码库或官方文档），并经逐条打开核对标题、作者、年份、发表处；无法直接核实的内容明确标注「待核实」，不编造实验数据。
> - **来源排除**：按本次调研要求，全程未访问、未阅读、未引用被指定排除的那篇二手综述及其任何镜像、转载或摘要页面；检索结果中出现相关条目时一律跳过，报告结论不依赖其任何内容。
> - **分工与交叉核验**：调研被拆成 8 个互不重叠的部分并行完成，再统一汇总、去重与核验：
>   1. Naive SP / Fictitious Play / FSP；
>   2. NFSP / ED；
>   3. δ-Uniform FSP / Prioritized FSP / PP；
>   4. FCP / Hidden-Utility Self-Play；
>   5. PBT / MERL；
>   6. CERL / DERL；
>   7. PSRO / PSROηN / Diverse PSRO；
>   8. Pipeline PSRO / α-PSRO。
> - **命名约定**：表中括号内给出英文全称与缩写；对「PSROηN / ED / δ-Uniform FSP / PP / DERL」等存在命名歧义或非标准写法的条目，正文给出考证与置信度，详见第五节。
> 
> ### 1.3 阅读提示
> 
> - **类别不等于实现**：同一算法可能横跨多类。例如 FSP/NFSP 既是虚拟自博弈，也常被 PSRO 用作近似最佳响应 oracle；PBT 既是超参优化方法，也是 AlphaStar 联赛训练的基础设施。
> - **「优点/缺点」是相对其定位而言**：例如 PBT 的「贵」在拥有大规模并行资源时并不构成短板；Exploitability Descent 的「model-based」在小型可建模博弈中是优点，在深度 RL 大域中则是硬伤。
> - **收敛与均衡保证高度依赖博弈类型**：两人零和、完全信息/不完美信息、一般和、多人博弈，是理解每个算法适用边界的四条主轴。
> 
> ---
> 
> ## 二、类

**报告结尾（含参考文献）**：

> - Jaderberg, M., et al. (2019). *Human-level performance in 3D multiplayer games with population-based reinforcement learning*. Science 364(6443):859–865. [arXiv:1807.01281](https://arxiv.org/abs/1807.01281)（种群并行互为队友/对手的代表性一手工作）
> - Zhang, R., Xu, Z., Ma, C., et al. (2024). *A Survey on Self-play Methods in Reinforcement Learning*. [arXiv:2408.01072](https://arxiv.org/abs/2408.01072)（仅用于 δ-uniform / PFSP 公式与术语的二手交叉核对，不是本报告结论的唯一依据）
> 
> ### FCP / Hidden-Utility Self-Play
> - Strouse, D. J., et al. (2021). *Collaborating with Humans without Human Data*. NeurIPS 2021. [arXiv:2110.08176](https://arxiv.org/abs/2110.08176)
> - Hu, H., Lerer, A., Peysakhovich, A., Foerster, J. (2020). *“Other-Play” for Zero-Shot Coordination*. ICML 2020. [arXiv:2003.02979](https://arxiv.org/abs/2003.02979)
> - Zhao, R., et al. (2021/2022). *Maximum Entropy Population-Based Training for Zero-Shot Human-AI Coordination*. [arXiv:2112.11701](https://arxiv.org/abs/2112.11701)
> - Yu, C., Gao, J., Liu, W., Xu, B., Tang, H., Yang, J., Wang, Y., Wu, Y. (2023). *Learning Zero-Shot Cooperation with Humans, Assuming Humans Are Biased*. ICLR 2023. [arXiv:2302.01605](https://arxiv.org/abs/2302.01605)
> 
> ### PBT / MERL / CERL / DERL
> - Jaderberg, M., et al. (2017). *Population Based Training of Neural Networks*. [arXiv:1711.09846](https://arxiv.org/abs/1711.09846)
> - Jaderberg, M., et al. (2019). *Human-level performance in 3D multiplayer games with population-based reinforcement learning*. Science 364(6443):859–865. [arXiv:1807.01281](https://arxiv.org/abs/1807.01281)
> - Parker-Holder, J., Pacchiano, A., Choromanski, K., Roberts, S. (2020). *Effective Diversity in Population Based Reinforcement Learning*. NeurIPS 2020. [NeurIPS 官方页](https://proceedings.neurips.cc/paper/2020/hash/d1dc3a8270a6f9394f88847d7f0050cf-Abstract.html)
> - Majumdar, S., Khadka, S., Miret, S., McAleer, S., Tumer, K. (2020). *Evolutionary Reinforcement Learning for Sample-Efficient Multiagent Coordination*（MERL）. ICML 2020, PMLR 119:6651–6660. [PMLR](https://proceedings.mlr.press/v119/majumdar20a.html)｜[arXiv:1906.07315](https://arxiv.org/abs/1906.07315)
> - Khadka, S., Tumer, K. (2018). *Evolution-Guided Policy Gradient in Reinforcement Learning*（ERL）. NeurIPS 2018. [arXiv:1805.07917](https://arxiv.org/abs/1805.07917)
> - Khadka, S., Majumdar, S., Nassar, T., Dwiel, Z., Tumer, E., Miret, S., Liu, Y., Tumer, K. (2019). *Collaborative Evolutionary Reinforcement Learning*（CERL）. ICML 2019, PMLR 97:3341–3350. [PMLR](https://proceedings.mlr.press/v97/khadka19a.html)｜[arXiv:1905.00976](https://arxiv.org/abs/1905.00976)
> - Bodnar, C., Day, B., Lió, P. (2020). *Proximal Distilled Evolutionary Reinforcement Learning*（PDERL）. AAAI 34(04):3283–3290. [arXiv:1906.09807](https://arxiv.org/abs/1906.09807)
> - Zheng, B., Cheng, R. (2023). *Rethinking Population-assisted Off-policy Reinforcement Learning*. GECCO 2023. [arXiv:2305.02949](https://arxiv.org/abs/2305.02949)
> - Hao, J., et al. (2023). *ERL-Re²: Efficient Evolutionary Reinforcement Learning with Shared State Representation and Individual Policy Representation*. ICLR 2023. [arXiv:2210.17375](https://arxiv.org/abs/2210.17375)
> - Gupta, A., Savarese, S., Ganguli, S., Fei-Fei, L. (2021). *Embodied Intelligence via Learning and Evolution*（DERL）. Nature Communications 12:5721. [arXiv:2102.02202](https://arxiv.org/abs/2102.02202)｜[DOI:10.1038/s41467-021-25874-z](https://doi.org/10.1038/s41467-021-25874-z)
> 
> ### PSRO 家族
> - Lanctot, M., et al. (2017). *A Unified Game-Theoretic Approach to Multiagent Reinforcement Learning*. NeurIPS 2017. [arXiv:1711.00832](https://arxiv.org/abs/1711.00832)
> - Balduzzi, D., Garnelo, M., Bachrach, Y., Czarnecki, W., Pérolat, J., Jaderberg, M., Graepel, T. (2019). *Open-ended Learning in Symmetric Zero-sum Games*（PSRO_N / PSRO_U / PSRO_rN）. ICML 2019, PMLR 97:434–443. [PMLR](https://proceedings.mlr.press/v97/balduzzi19a.html)｜[arXiv:1901.08106](https://arxiv.org/abs/1901.08106)
> - Perez-Nieves, N., Yang, Y., Slumbers, O., Mguni, D. H., Wen, Y., Wang, J. (2021). *Modelling Behavioural Diversity for Learning in Open-Ended Games*（Diverse PSRO / DPP-PSRO）. ICML 2021, PMLR 139:8514–8524. [PMLR](https://proceedings.mlr.press/v139/perez-nieves21a.html)｜[arXiv:2103.07927](https://arxiv.org/abs/2103.07927)
> - McAleer, S., Lanier, J. B., Fox, R., Baldi, P. (2020). *Pipeline PSRO: A Scalable Approach for Finding Approximate Nash Equilibria in Large Games*. NeurIPS 2020. [NeurIPS 官方页](https://proceedings.neurips.cc/paper_files/paper/2020/hash/e9bcd1b063077573285ae1a41025f5dc-Abstract.html)｜[arXiv:2006.08555](https://arxiv.org/abs/2006.08555)
> - Muller, P., Omidshafiei, S., Rowland, M., Tuyls, K., Pérolat, J., Liu, S., Hennes, D., Marris, L., Lanctot, M., Hughes, E., Wang, Z., Lever, G., Heess, N., Graepel, T., Munos, R. (2020). *A Generalized Training Approach for Multiagent Learning*（α-PSRO）. ICLR 2020. [ICLR 官方 poster](https://www.iclr.cc/virtual/2020/poster/2035)｜[arXiv:1909.12823](https://arxiv.org/abs/1909.12823)
> - Omidshafiei, S., Papadimitriou, C., Piliouras, G., Tuyls, K., Rowland, M., Lespiau, J.-B., Czarnecki, W. M., Lanctot, M., Pérolat, J., Munos, R. (2019). *α-Rank: Multi-Agent Evaluation by Evolution*. Scientific Reports 9:9937. [DOI:10.1038/s41598-019-45619-9](https://doi.org/10.1038/s41598-019-45619-9)｜[arXiv:1903.01373](https://arxiv.org/abs/1903.01373)
> - Marris, L., Muller, P., Lanctot, M., Tuyls, K., Graepel, T. (2021). *Multi-Agent Training beyond Zero-Sum with Correlated Equilibrium Meta-Solvers*（JPSRO）. ICML 2021, PMLR 139:7480–7491. [PMLR](https://proceedings.mlr.press/v139/marris21a.html)
> - McAleer, S., Wang, K., Lanier, J., Lanctot, M., Baldi, P., Sandholm, T., Fox, R. (2022). *Anytime PSRO for Two-Player Zero-Sum Games*. [arXiv:2201.07700](https://arxiv.org/abs/2201.07700)
> - Bighashdel, A., Wang, Y., McAleer, S., Savani, R., Oliehoek, F. A. (2024). *Policy Space Response Oracles: A Survey*. IJCAI-24 Survey Track, pp. 7951–7961. [IJCAI 官方页](https://www.ijcai.org/proceedings/2024/880)｜[arXiv:2403.02227](https://arxiv.org/abs/2403.02227)（用于机制分类与停止准则的补充核对）
> 
> ---
> 
> *本报告由 8 个互不重叠的调研单元并行完成后汇总核验；所有链接均经打开核对，标注「待核实」处为调研时无法直接访问的内容（如部分 GitHub 仓库）。报告未使用、未引用任何被指定排除的二手来源。*

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 16

**题目**：Investigation of Hydroforming Technology（Industrial）

**禁用的来源文章**：A review of emerging hydroforming technologies: design considerations, parametric studies, and recent innovations

- https://jeas.springeropen.com/articles/10.1186/s44147-024-00546-z
- https://www.researchgate.net/publication/385401108_A_review_of_emerging_hydroforming_technologies_design_considerations_parametric_studies_and_recent_innovations
- https://ui.adsabs.harvard.edu/abs/2024JEAS...71..205C/abstract

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 345 个地址，最多的站点**：mdpi.com 18，ahssinsights.org 14，sciencedirect.com 13，qikan.cmes.org 13，link.springer.com 11，doi.org 11，patents.google.com 10，azom.com 9，api.semanticscholar.org 7，iopscience.iop.org 7，osti.gov 7，doaj.org 6

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 液压成形（Hydroforming）技术调研报告：材料选择与常见制造缺陷
    ## 报告说明与方法
    ## 0. 工艺背景速览（引子）
    ## 第一部分　常用材料分析
    ### 1.1 高强度钢（HSS）
    ### 1.2 高强度铝合金
    ### 1.3 镁合金（Magnesium Alloys）
    ### 1.4 钛合金
    ## 第二部分　常见制造缺陷、成因及对策
    ### 2.1 表面缺陷（Surface defects）
    ### 2.2 回弹（Springback）
    ### 2.3 起皱（Wrinkling）
    ### 2.4 变薄（Thinning）
    ### 2.5 撕裂（Tearing）
    ## 结语：选材—缺陷—工艺路线的交叉控制

**报告开头**：

> # 液压成形（Hydroforming）技术调研报告：材料选择与常见制造缺陷
> 
> **报告类型**：行业技术分析  
> **技术范围**：管材液压成形（Tube Hydroforming, THF）、板料液压成形（Sheet Hydroforming, SHF）及温热/热态液压成形  
> **覆盖内容**：四类代表性金属材料（高强度钢、高强度铝合金、镁合金、钛合金）；五类常见制造缺陷（表面缺陷、回弹、起皱、变薄、撕裂）
> 
> ---
> 
> ## 报告说明与方法
> 
> 1. **研究组织方式**：本报告将调研任务拆分为 8 个互不重叠的模块，分别由 8 个独立研究单元并行完成，再由本报告统一汇总、去重与校验。模块划分为：材料 4 个（HSS、高强铝合金、镁合金、钛合金）+ 缺陷 4 个（表面缺陷、回弹、起皱、变薄与撕裂，其中变薄与撕裂因机理上互为因果而合并为一个模块、分两节呈现）。
> 2. **证据标准**：优先采用同行评审期刊、行业媒体及整车厂/一级供应商（OEM/Tier-1）技术资料；所引数据均给出处，无法确证的数字标注为“约/区间”。
> 3. **排除声明**：按委托方明确要求，本次调研全程未打开、未检索、未引用一篇 2024 年发表的液压成形综述文章及其任何转载页、镜像页与摘要页（含 SpringerOpen、ResearchGate、ADS 页面），其内容未以任何形式进入本报告。报告中所有结论均来自下列独立来源。
> 4. **阅读提示**：材料章节按“材料特性—成形挑战—主要应用”统一结构展开；缺陷章节按“定义与表现形式—主要成因—建议的解决方法—成因对策表”统一结构展开。
> 5. **报告结构**：
>    - 第一部分　常用材料分析：1.1 高强度钢（HSS）｜1.2 高强度铝合金｜1.3 镁合金｜1.4 钛合金
>    - 第二部分　常见制造缺陷、成因及对策：2.1 表面缺陷｜2.2 回弹｜2.3 起皱｜2.4 变薄｜2.5 撕裂
>    - 结语：选材—缺陷—工艺路线的交叉控制
> 6. **引用规模**：全文合计引用 88 条去重后的真实链接（含期刊论文、学位论文、专利、OEM/供应商技术页与行业媒体），各章末尾均附独立来源列表，便于逐条核验。
> 
> ---
> 
> ## 0. 工艺背景速览（引子）
> 
> 液压成形是一种以高压液体（通常为水基乳化液）作为传力介质、使金属坯料贴合模具型腔而成形的柔性成形工艺，主要分为两大类：
> 
> - **管材液压成形（THF）**：将直管或预弯/预成形管坯放入闭合模腔，两端密封后充液加压，管材在内压作用下向外膨胀贴合型腔；同时通常对管端施加**轴向补料（axial feeding）**，向内推送材料以补偿壁厚减薄。THF 是目前汽车行业最成熟、量产规模最大的液压成形路线。
> - **板料液压成形（SHF）**：以高压液体替代凸模（或作为背压），使板料贴靠凹模成形，包括液压深拉深、双板料液压成形（double blank hydroforming）等变体，多用于样件试制与中小批量生产。
> 
> THF 的核心价值在于**减重、零件整合、降低模具数量，以及提高构件刚度与尺寸稳定性**：一个液压成形管件常可替代由多个冲压件焊接而成的总成，典型应用包括副车架/发动机托架（engine cradle）、纵梁（side rail）、空间框架（space frame）、悬架结构件、动力总成件与排气系统件等。其主要局限是**模具成本高、节拍慢于传统冲压，且工艺参数对最终零件质量的影响尚缺乏完整知识库**，因此对稳健的工艺仿真、材料建模与摩擦系数标定依赖较强。
> 
> 为突破材

**报告结尾（含参考文献）**：

> 
> | 类别 | 成因 | 对策 |
> | --- | --- | --- |
> | 材料 | 延伸率/n 值低、FLD 上限低 | 高 n、高延伸率材料；中间退火恢复塑性 |
> | 材料/焊缝 | 焊缝与 HAZ 塑性低；枝晶组织与马氏体促进裂纹 | 焊后热处理；焊缝避开高应变区；金相与硬度检验 |
> | 工艺 | 内压过高或升压过快 | 分段升压与限压；以 FEM 标定压力曲线 |
> | 工艺 | 轴向补料不足，膨胀区被"拉空" | 增大并前置轴向补料；保证 P–s 匹配 |
> | 工艺 | 加载路径穿越 FLD 失稳区 | 用 FLD/成形窗口校核路径；脉动加压 |
> | 工艺 | 膨胀率过大 | 降低单步膨胀比；两阶段/多步成形 |
> | 模具 | 圆角过小（t/r > 0.5）、过渡剧烈 | 增大圆角与过渡半径；优化模具间隙 |
> | 模具/工艺 | 摩擦大、应变集中 | 区域润滑；模具抛光与涂层 |
> | 管坯 | 壁厚不均、椭圆度、D/t 不当 | 收紧来料公差；选择合适 D/t |
> | 控制 | 爆裂突发、模具与设备损失大 | 压力—位移在线监测；压力骤降报警与自动卸压；分段限压 |
> 
> **本节参考来源**
> 
> 1. 刘钢, 苑世剑, 滕步刚. 内高压成形矩形断面圆角应力分析[J]. 机械工程学报, 2006, 42(6): 150-155. http://www.cjmenet.com.cn/CN/abstract/abstract9469.shtml
> 2. Tomizawa A., Kurokawa H., Kubota H., Kojima M. Development of Vertical Double-Action Forming in Tube Hydroforming[J]. Journal of the Japan Society for Technology of Plasticity, 2012, 53(614): 236-240. https://www.jstage.jst.go.jp/article/sosei/53/614/53_614_236/_article/-char/en
> 3. Johnson K.I., Nguyen B.N., Davies R.W., Grant G.J., Khaleel M.A. A Numerical Process Control Method for Circular-Tube Hydroforming Prediction[J]. International Journal of Plasticity, 2004, 20(6). https://www.osti.gov/biblio/15007893
> 4. 陈晓华, 赵长财, 国庆波, 李建超. 波纹管内高压成形焊接区变形特征研究[J]. 材料导报, 2017, 31(8): 140-144. https://www.mater-rep.com/CN/Y2017/V31/I8/140
> 5. Jaber A.Sh., Mohammed A.I., Younis K.M. Experimental Investigation of Process Parameters in the Hydrostatic Forming to Enhance a Square Steel Cup Formability[J]. Tikrit Journal of Engineering Sciences, 2025, 32(2): 1-13. https://tj-es.com/ojs/index.php/tjes/article/view/1332
> 
> ## 结语：选材—缺陷—工艺路线的交叉控制
> 
> 把四类材料与五类缺陷放在同一张图上看，可以得出三条对工程实践最有价值的判断：
> 
> **第一，材料的弹性模量与屈强比，和材料的室温塑性同样重要。** 前者决定回弹与尺寸精度（铝合金约 70 GPa、镁合金约 45 GPa，仅为钢约 200 GPa 的 1/3–1/4；钛合金屈强比可达约 0.93），后者决定工艺路线（钢与 5xxx/6xxx 铝可冷态液压成形；镁合金几乎必须 150–300 ℃ 温热成形；7xxx 铝需约 380–470 ℃ 热成形并模内淬火；钛合金需热气胀 650–750 ℃ 或超塑成形约 850–950 ℃）。选材阶段若只比较强度与密度、忽略这两项，回弹补偿与设备投资会在量产阶段形成隐性成本。
> 
> **第二，五类缺陷并非彼此独立，而是共享同一组控制变量。** 内压—轴向补料加载路径、摩擦与润滑、模具圆角与间隙、管坯壁厚/椭圆度与焊缝质量，同时决定表面质量、起皱、变薄与撕裂的边界；起皱与破裂分别构成工艺窗口的下限与上限，变薄—颈缩—撕裂则是同一条失效链的三个阶段。因此“逐缺陷对症下药”必须让位于“工艺窗口整体设计”：以成形极限图（FLD/FLC）与有限元标定加载路径，把回弹补偿与校形压力纳入同一套仿真—试模迭代，并把压力—位移曲线的斜率变化作为颈缩与破裂的在线报警信号。
> 
> **第三，模具与润滑应当被当作一等工艺变量，而不是辅助条件。** 表面缺陷章节的证据表明，高压接触下真实接触面积增大、油膜在边界/极压条件下破裂，是铝、镁件拉毛与模具磨损的直接原因；而摩擦系数又反过来改变临界起皱内压与壁厚分布（如干摩擦 μ≈0.09 与 MoS₂ 润滑 μ≈0.018 的差别足以改变所需内压水平）。模具硬度与表面处理（如 HRC≥50、Ra≤2.0 μm、镀铬/TD/PVD/DLC）、与润滑剂匹配的涂层选择、蜡基可水洗固体膜以及区域润滑，往往比单纯提高设备吨位更经济。
> 
> **趋势判断**：温热/热态液压成形（含电辅助加热）、脉动与冲击加载、液压锻造/液压校形复合、区域润滑与在线自适应控制，是当前扩大液压成形材料适用范围、压缩缺陷窗口的主要技术方向；对高强钢、铝合金与镁合金而言，这些路线的成熟度差异，将直接决定未来五年各材料在车身与底盘结构件中的渗透速度。
> 
> ---

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 17

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里出现了来源文章的标题；与来源正文相同的 12 词片段 148 条；相同的参考文献 2 条。

相同片段举例：`kim sastry feedback linearization vs adaptive sliding mode control for quadrotor helicopter`

**这次运行打开过 272 个地址，最多的站点**：api.crossref.org 67，api.semanticscholar.org 30，export.arxiv.org 19，ebi.ac.uk 15，api.openalex.org 13，doi.org 12，arxiv.org 10，mdpi.com 8，ar5iv.labs.arxiv.org 7，ieeexplore.ieee.org 6，res.mdpi.com 6，api.unpaywall.org 4

**打开过的、和禁用来源同一个站点的地址**：
- https://api.openalex.org/works/https://doi.org/10.3390/act13100392
- https://doi.org/
- https://doi.org/$d
- https://doi.org/10.1109/access.2018.2851223
- https://doi.org/10.1155/2019/7272387
- https://doi.org/{d[
- https://doi.org/{it[
- https://ouci.dntb.gov.ua/works/ldV8rRq7/
- https://res.mdpi.com/d_attachment/aerospace/aerospace-10-00512/article_deploy/aerospace-10-00512.pdf
- https://res.mdpi.com/d_attachment/applsci/applsci-09-03873/article_deploy/applsci-09-03873.pdf
- https://res.mdpi.com/d_attachment/applsci/applsci-12-11637/article_deploy/applsci-12-11637.pdf
- https://res.mdpi.com/d_attachment/drones/drones-08-00599/article_deploy/drones-08-00599.pdf
- https://res.mdpi.com/d_attachment/drones/drones-08-00614/article_deploy/drones-08-00614.pdf
- https://res.mdpi.com/d_attachment/processes/processes-09-01951/article_deploy/processes-09-01951.pdf
- https://www.mdpi.com/1424-8220/19/1/24

**报告的各级标题**：

    # 四旋翼无人机控制方法技术综述
    ## 目录
    ## 0. 范围、方法与分类框架
    ### 0.1 综述范围与文献截止时间
    ### 0.2 四旋翼被控对象的关键特性
    ### 0.3 控制器分类框架
    ### 0.4 典型控制架构：级联双环结构
    ### 0.5 术语与引用说明
    ## 1. 第一部分：控制器特性总结
    ### 1.1 线性控制（Linear Control）
    #### 1.1.1 PID（比例-积分-微分控制）
    #### 1.1.2 LQR（线性二次调节器）
    #### 1.1.3 H∞（H-无穷鲁棒控制）
    ### 1.2 非线性控制（Nonlinear Control）
    #### 1.2.1 Feedback Linearization（反馈线性化）
    #### 1.2.2 Backstepping（反步法）
    #### 1.2.3 SMC（滑模控制）
    #### 1.2.4 MPC（模型预测控制）
    #### 1.2.5 Adaptive Control（自适应控制）
    ### 1.3 基于学习的控制（Learning-Based Control）
    #### 1.3.1 Fuzzy Logic（模糊逻辑控制）
    #### 1.3.2 Neural Network（神经网络控制）
    ### 1.4 十种控制器特性横向对比总表
    ## 2. 第二部分：性能改进策略表格
    ### 2.1 表格使用说明
    ### 2.2 控制器混合策略与控制器改进策略总表
    ### 2.3 改进策略的横向观察
    ## 3. 参考文献
    # 参考文献汇编（截至 2021 年 5 月）
    ### 补充文献（正文与表格引用、未包含在自动汇编中的条目）
    ## 附录 A：文献合规声明

**报告开头**：

> # 四旋翼无人机控制方法技术综述
> 
> **文献覆盖范围：截至 2021 年 5 月**
> **文档类型：技术综述（控制器特性总结 + 性能改进策略梳理）**
> 
> ---
> 
> ## 目录
> 
> - [0. 范围、方法与分类框架](#0-范围方法与分类框架)
>   - [0.1 综述范围与文献截止时间](#01-综述范围与文献截止时间)
>   - [0.2 四旋翼被控对象的关键特性](#02-四旋翼被控对象的关键特性)
>   - [0.3 控制器分类框架](#03-控制器分类框架)
>   - [0.4 典型控制架构：级联双环结构](#04-典型控制架构级联双环结构)
>   - [0.5 术语与引用说明](#05-术语与引用说明)
> - [1. 第一部分：控制器特性总结](#1-第一部分控制器特性总结)
>   - [1.1 线性控制（Linear Control）](#11-线性控制linear-control)
>     - [1.1.1 PID（比例-积分-微分控制）](#111-pid比例-积分-微分控制)
>     - [1.1.2 LQR（线性二次调节器）](#112-lqr线性二次调节器)
>     - [1.1.3 H∞（H-无穷鲁棒控制）](#113-hh-无穷鲁棒控制)
>   - [1.2 非线性控制（Nonlinear Control）](#12-非线性控制nonlinear-control)
>     - [1.2.1 Feedback Linearization（反馈线性化）](#121-feedback-linearization反馈线性化)
>     - [1.2.2 Backstepping（反步法）](#122-backstepping反步法)
>     - [1.2.3 SMC（滑模控制）](#123-smc滑模控制)
>     - [1.2.4 MPC（模型预测控制）](#124-mpc模型预测控制)
>     - [1.2.5 Adaptive Control（自适应控制）](#125-adaptive-control自适应控制)
>   - [1.3 基于学习的控制（Learning-Based Control）](#13-基于学习的控制learning-based-control)
>     - [1.3.1 Fuzzy Logic（模糊逻辑控制）](#131-fuzzy-logic模糊逻辑控制)
>     - [1.3.2 Neural Network（神经网络控制）](#132-neural-network神经网络控制)
>   - [1.4 十种控制器特性横向对比总表](#14-十种控制器特性横向对比总表)
> - [2. 第二部分：性能改进策略表格](#2-第二部分性能改进策略表格)
>   - [2.1 表格使用说明](#21-表格使用说明)
>   - [2.2 控制器混合策略与控制器改进策略总表](#22-控制器混合策略与控制器改进策略总表)
>   - [2.3 改进策略的横向观察](#23-改进策略的横向观察)
> - [3. 参考文献](#3-参考文献)
> - [附录 A：文献合规声明](#附录-a文献合规声明)
> 
> ---
> 
> ## 0. 范围、方法与分类框架
> 
> ### 0.1 综述范围与文献截止时间
> 
> 本综述面向四旋翼（quadrotor / quadcopter）飞行控制方法，系统梳理截至 **2021 年 5 月** 公开发表的学术研究与具有代表性的工业实践。综述覆盖十种控制器：PID、LQR、H∞、Feedback Linearization、Backstepp

**报告结尾（含参考文献）**：

> - Torres, F., Rabhi, A., Lara, D., Pegard, C. & Romero, G. (2016). *Fuzzy State Feedback for Attitude Stabilization of Quadrotor*. International Journal of Advanced Robotic Systems, 13(1). DOI: 10.5772/61934
> - Tripathi, V. K., Behera, L. & Verma, N. (2015). *Design of sliding mode and backstepping controllers for a quadcopter*. 2015 39th National Systems Conference (NSC). DOI: 10.1109/NATSYS.2015.7489097
> - Xiang, T., Jiang, F., Hao, Q. & Cong, W. (2016). *Adaptive flight control for quadrotor UAVs with dynamic inversion and neural networks*. 2016 IEEE International Conference on Multisensor Fusion and Integration for Intelligent Systems (MFI). DOI: 10.1109/MFI.2016.7849485
> - Xu, D., Whidborne, J. F. & Cooke, A. (2016). *Fault tolerant control of a quadrotor using L1 adaptive control*. International Journal of Intelligent Unmanned Systems, 4(4). [元数据待核实，DOI 未核实]
> - Xu, R. & Ozguner, U. (2006). *Sliding Mode Control of a Quadrotor Helicopter*. Proceedings of the 45th IEEE Conference on Decision and Control, 4957–4962. DOI: 10.1109/CDC.2006.377588
> - Xu et al. (2017). *Robust guaranteed cost tracking control of quadrotor UAV with uncertainties*. ISA Transactions, 69, 157–165. DOI: 10.1016/j.isatra.2017.03.023
> - Yazid, E., Garratt, M. & Santoso, F. (2019). *Position control of a quadcopter drone using evolutionary algorithms-based self-tuning for first-order Takagi–Sugeno–Kang fuzzy logic autopilots*. Applied Soft Computing, 78, 373–392. DOI: 10.1016/j.asoc.2019.02.023
> - Zaccarian, L. & Teel, A. R. (2011). *Modern Anti-windup Synthesis: Control Augmentation for Actuator Saturation*. Princeton University Press. DOI: 10.23943/princeton/9780691147321.001.0001
> - Zanelli, A., Horn, G., Frison, G. & Diehl, M. (2018). *Nonlinear Model Predictive Control of a Human-sized Quadrotor*. 2018 European Control Conference (ECC). DOI: 10.23919/ECC.2018.8550530
> - Zare, M., Sadeghi, J., Farahat, S. & Zakeri, E. (2014). *Regulating and Helix Path Tracking for Unmanned Aerial Vehicle (UAV) Using Fuzzy Logic Controllers*. Journal of Mathematics and Computer Science, 13(1), 71–89. DOI: 10.22436/jmcs.013.01.07
> - Zeghlache, S., Saigaa, D., Kara, K., Harrag, A. & Bouguerra, A. (2012). *Backstepping Sliding Mode Controller Improved with Fuzzy Logic: Application to the Quadrotor Helicopter*. Archives of Control Sciences, 22(3), 315–342. DOI: 10.2478/v10170-011-0027-x
> - Zeghlache, S., Djerioui, A., Benyettou, L. & Benslimane, T. (2019). *Fault tolerant control for modified quadrotor via adaptive type-2 fuzzy backstepping subject to actuator faults*. ISA Transactions, 95, 330–345. DOI: 10.1016/j.isatra.2019.04.034
> - Zheng, F. & Weinan, G. (2012). *Adaptive Backstepping Control of an Indoor Micro-Quadrotor*. Research Journal of Applied Sciences, Engineering and Technology, 4(21), 4216–4226. [no DOI found]
> - Zhi, Y., Li, G., Song, Q., Yu, K. & Zhang, J. (2017). *Flight control law of unmanned aerial vehicles based on robust servo linear quadratic regulator and Kalman filtering*. International Journal of Advanced Robotic Systems, 14(1). DOI: 10.1177/1729881416686952
> - Zulu, A. & John, S. (2014). *A Review of Control Algorithms for Autonomous Quadrotors*. Open Journal of Applied Sciences, 4(14), 547–556. DOI: 10.4236/ojapps.2014.414053
> 
> 
> ---
> 
> ## 附录 A：文献合规声明
> 
> 本综述在研究与写作过程中严格遵守以下约束：
> 
> 1. **明确排除的文献**：题为 "A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers"（作者 Rupal Roy、Maidul Islam、Nafiz Sadman、M. A. Parvez Mahmud、Kishor Datta Gupta、Md Manjurul Ahsan）的论文及其全部转载页、摘要页、镜像页与 DOI 页面，均未被打开、抓取、阅读、引用或转述。
> 2. **明确排除的网址**：以下网址在本项目全程未被访问：
>    - https://www.mdpi.com/2227-7080/9/2/37
>    - https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
>    - https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
>    - https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
>    - https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
>    - https://doi.org/10.3390/TECHNOLOGIES9020037
> 3. **检索过程中的处理**：在若干次网络检索的结果列表中曾出现该文献或其镜像的标题与链接。按照约束，这些结果被直接跳过，未打开、未读取、未引用。
> 4. **合规核验**：本报告与四份底层研究档案在合并前后，均以程序化方式检索上述标题、作者姓名、URL 片段与 DOI 字符串，确认在正文与参考文献中零出现（本附录中为说明排除范围而列出的字符串除外）。
> 5. **引用完整性**：正文与表格中的全部引用均来自实际检索到的公开记录（期刊页面、会议页面、arXiv、Crossref 元数据或开放获取全文 PDF）。凡元数据无法完整核实者，均在参考文献中标明；不存在虚构引用。
> 

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 18

**题目**：Legal Research on Traffic Accident Liability for German Autonomous Vehicles（Crime & Law）

**禁用的来源文章**：Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China

- https://www.mdpi.com/2032-6653/15/7/305
- https://www.mdpi.com/2032-6653/15/7/305/pdf
- https://www.mdpi.com/2032-6653/15/7/305/html
- https://www.mdpi.com/2032-6653/15/7/305/xml
- https://www.researchgate.net/publication/382225455_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_of_the_German_Legislation_for_China
- https://www.researchgate.net/publication/382400472_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_from_the_German_Legislation_for_China/download

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里出现了来源文章的标题；与来源正文相同的 12 词片段 11 条；相同的参考文献 0 条。

相同片段举例：`distribution of the burden of proof in autonomous driving tort cases implications`

**这次运行打开过 76 个地址，最多的站点**：web.archive.org 29，de.wikipedia.org 10，gesetze-im-internet.de 7，dejure.org 3，en.wikipedia.org 3，kba.de 3，eur-lex.europa.eu 2，buzer.de 1，bmwk.de 1，jurion.de 1，bmj.de 1，bundesregierung.de 1

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 德国 L3 级及以上自动驾驶汽车交通事故责任分配调研报告
    ## 0. 核心结论（摘要）
    ## 1. 规范框架：德国法如何把 SAE 等级"翻译"成法律概念
    ### 1.1 两条并行的轨道
    ### 1.2 相关的配套规范（截至 2024 年中期）
    ## 2. 驾驶员（Driver / Fahrzeugführer）的责任
    ### 2.1 法律依据
    ### 2.2 责任类型：**过错责任，但过错被推定（举证责任倒置）**
    ### 2.3 受害人对驾驶员需要证明什么？
    ### 2.4 驾驶员可以通过证明什么来免责？
    ### 2.5 轨道 B（L4/L5）下没有"驾驶员"，§ 18 StVG 不适用
    ### 2.6 证据与数据：免责举证的前提
    ## 3. 车辆持有人（Halter）的责任
    ### 3.1 "持有人"是谁？——与车主、登记人、驾驶员均不必然同一
    ### 3.2 法律依据
    ### 3.3 责任类型：**无过错的危险责任（Gefährdungshaftung）**
    ### 3.4 与驾驶员责任的区别（对照表）
    ### 3.5 举证责任：规则与实务后果
    ### 3.6 强制保险与受害人的直接请求权
    ## 4. 生产者责任与制造商产品责任
    ### 4.1 首先必须澄清术语：德国法上"Produzentenhaftung"与"Produkthaftung"是**两套不同制度**
    ### 4.2 Produzentenhaftung：§ 823 BGB 的过错责任（判例法）
    ### 4.3 Produkthaftung：ProdHaftG 的无过错危险责任（制定法）
    ### 4.4 两条路径的总对照
    ### 4.5 软件、AI 与自动驾驶的特殊争点（截至 2024 年中期）
    ## 5. 三方责任的交互：受害人、持有人（保险人）与制造商
    ### 5.1 请求权路径（示意）
    ### 5.2 几个实务要点
    ## 6. 立法与监管状况（截至 2024 年中期）
    ### 6.1 德国国内
    ### 6.2 技术与证据规则
    ### 6.3 超出截止点（2024 年中期之后）但方向性重要的两项欧盟立法
    ## 7. 要点回顾（对应提问的三问）
    ### 7.1 驾驶员责任
    ### 7.2 持有人责任
    ### 7.3 生产者/制造商责任
    ## 8. 本报告的方法与合规说明
    ## 附录：主要规范文本与来源
    ### A. 一手规范（德国法）
    ### B. 判例（本报告引用的经典裁判）

**报告开头**：

> # 德国 L3 级及以上自动驾驶汽车交通事故责任分配调研报告
> 
> **信息截止日期：2024 年中期**（个别在此之后才发生的发展，均在文中明确标注为"超出截止点"）
> **法律依据版本：** 以 2024 年 5–7 月联邦法律公报（BGBl.）现行文本为准（详见文末"主要规范文本"）
> **报告性质：** 法律信息整理，不构成法律意见
> 
> ---
> 
> ## 0. 核心结论（摘要）
> 
> 1. **德国没有为自动驾驶另建一套责任法体系**，而是坚持既有的"三支柱"结构，并通过 2017 年《自动化驾驶法》（Gesetz zum automatisierten Fahren, BGBl. 2017 I S. 1648）和 2021 年《自动驾驶法》（Gesetz zum autonomen Fahren, BGBl. 2021 I S. 3108）把自动驾驶"嵌入"其中。德国保险业协会（GDV）明确表述：两部法律的核心决定就是"**维持现有且经证明有效的责任体系**"（[GDV, Dossier Automatisiertes und Autonomes Fahren](https://www.gdv.de/gdv/themen/mobilitaet/autonomes-fahren)）。
> 
> 2. 三支柱及其归责原则截然不同：
> 
>    | 角色 | 核心请求权基础 | 归责原则 | 举证责任的关键 |
>    |---|---|---|---|
>    | 驾驶员（Fahrzeugführer） | § 18 Abs. 1 StVG；另加 § 823 BGB | **过错责任，但过错被推定**（举证责任倒置） | 受害人证明客观要件；**驾驶员须证明自己无过错**（Exkulpation） |
>    | 持有人（Halter） | § 7 Abs. 1 StVG | **危险责任**（Gefährdungshaftung），完全不以过错、违法性为要件 | 受害人证明运营关联与因果关系；**持有人须证明"不可抗力"才能免责** |
>    | 生产者/制造商 | ① § 823 BGB（Produzentenhaftung）② ProdHaftG（Produkthaftung） | ① **过错责任**（但就组织过错举证责任倒置）② **无过错危险责任** | ①受害人证明缺陷、损害、因果关系；制造商证明自己无组织过错 ②受害人证明缺陷、损害、因果关系；制造商证明法定免责事由 |
> 
> 3. **对自动驾驶最关键的"杠杆"是举证责任而非归责原则**。由于自动驾驶事故的原因通常只能从车辆数据中查明，德国法在实体法之外专门配置了**数据访问权**（§ 63a Abs. 3、§ 1g Abs. 7 StVG），否则驾驶员的免责举证和受害人对制造商的缺陷举证都将落空。
> 
> 4. **自动化程度越高，"驾驶员免责越容易、持有人免责越难"**。这是本报告最重要的技术性发现：
>    - 系统故障原则上**不可归责于驾驶员**，因此有利于驾驶员依 § 18 Abs. 1 S. 2 StVG 证明"无过错"而免责；
>    - 但系统故障恰恰**落在车辆自身风险领域**，因此不构成 § 7 Abs. 2 StVG 的"不可抗力"；在**内部份额**层面，§ 17 Abs. 3 S. 1 StVG 更明文把"车辆性质上的缺陷"和"其装置的失效"排除在"不可避免事件"之外（§ 17 适用于持有人之间以及依 § 18 Abs. 3 适用于驾驶员与其他持有人/驾驶员之间，**而非**受害人对驾驶员的本

**报告结尾（含参考文献）**：

> > 说明：上表右列为本报告实际读取的 Internet Archive 快照；左列为《联邦法律公报》官方电子版的规范地址。所有条文内容均以快照中的现行文本为准。
> 
> ### B. 判例（本报告引用的经典裁判）
> 
> | 裁判 | 主题 | 引用 |
> |---|---|---|
> | BGH, 26.11.1968 – VI ZR 212/66 | **Produzentenhaftung 的举证责任倒置**（"鸡瘟疫案"） | BGHZ 51, 91 |
> | BGH, 22.3.1983 – VI ZR 108/81 | **持有人（Halter）的定义** | BGHZ 87, 133；NJW 1983, 1492 |
> | BGH, 23.5.1960 – II ZR 132/58 | 短期租车人不构成持有人 | NJW 1960, 1572 |
> | BGH, 10.7.2007 – VI ZR 199/06 | 融资租赁中承租人为持有人 | — |
> | BGH —— | 产品观察义务 | BGHZ 80, 186 |
> | BGH —— | 继续侵蚀型损害（Schwimmschalter） | BGHZ 67, 359 |
> | BGH —— | 不可抗力的标准 | BGHZ 62, 351, 354 |
> | BGH —— | 不可抗力不得来自自身风险领域 | BGHZ 100, 157 |
> | BGH, 20.10.2020 – VI ZR 158/19 | 规范性运营概念的范围（停放车辆内的电子设备起火仍属"运营中"） | — |
> | LG Nürnberg-Fürth, 13.8.2015 – 8 O 9261/14 | 行驶证登记**不**构成持有人身份的表见证明 | BeckRS 2015, 14583 |
> 
> ### C. 机构与学术来源（本报告实际读取全文者）
> 
> - GDV（德国保险业协会）：*Dossier: Automatisiertes und autonomes Fahren* —— https://www.gdv.de/gdv/themen/mobilitaet/autonomes-fahren
> - Mercedes-Benz 新闻稿（2021 年 12 月 9 日）：*Mercedes-Benz erhält weltweit erste international gültige Systemgenehmigung für hochautomatisiertes Fahren* —— https://media.mercedes-benz.be/de/mercedes-benz-erhaelt-weltweit-erste-international-gueltige-systemgenehmigung-fuer-hochautomatisiertes-fahren
> - KBA（联邦机动车运输管理局）：*Automatisiertes und Autonomes Fahren / Fernlenken*（含"国内运营许可""欧盟小系列型式认证""试验许可""事后可激活功能""远程操控"各栏目）—— https://www.kba.de/DE/Themen/Typgenehmigung/Autonomes_automatisiertes_Fahren/autonomes_Fahren_node.html ；欧盟小系列型式认证页 —— https://www.kba.de/DE/Themen/Typgenehmigung/Autonomes_automatisiertes_Fahren/EU_Typgenehmigung/eu_typgenehmigung_node.html
> - BASt（联邦道路事务研究所）：*Rechtsfolgen zunehmender Fahrzeugautomatisierung*（"Forschung kompakt"页）—— https://bast.de/DE/Publikationen/Foko/2013-2012/2012-11.html
> - 德文维基百科（用于体系性概念的定位与判例引注的交叉核对，非一手来源）：[Produzentenhaftung](https://de.wikipedia.org/wiki/Produzentenhaftung)、[Produkthaftung (Deutschland)](https://de.wikipedia.org/wiki/Produkthaftung_(Deutschland))、[Produkthaftungsgesetz (Deutschland)](https://de.wikipedia.org/wiki/Produkthaftungsgesetz_(Deutschland))、[Gefährdungshaftung](https://de.wikipedia.org/wiki/Gef%C3%A4hrdungshaftung)、[Höhere Gewalt](https://de.wikipedia.org/wiki/H%C3%B6here_Gewalt)、[Fahrzeughalter](https://de.wikipedia.org/wiki/Fahrzeughalter)、[Autonomes Fahren](https://de.wikipedia.org/wiki/Autonomes_Fahren)
> - ADAC / VISION mobility：*ADAC test BMW Highway Assistant & Mercedes Drive Pilot: Differently automated*（关于 L2+ 与 L3 在责任归属上的实务差异）—— https://vision-mobility.de/en/news/adac-test-bmw-highway-assistant-mercedes-drive-pilot-differently-automated-388241.html
> - CMS Expert Guide：*Autonomous Vehicles Law and Regulation in Germany* —— https://cms.law/en/int/expert-guides/cms-expert-guide-to-autonomous-vehicles-avs/germany
> 
> ### D. 欧盟与国际规范
> 
> - **UN-R157**（Automated Lane Keeping Systems, ALKS）；UNECE 新闻稿 *"UN Regulation extends automated driving up to 130 km/h in certain conditions"* —— https://unece.org/media/Transport/Vehicle-Regulations/press/368227
> - **Commission Implementing Regulation (EU) 2022/1426**（全自动车辆 ADS 的型式认证程序与技术规范）
> - **Regulation (EU) 2019/2144**（一般安全条例，GSR；含 EDR 时间表）
> - **Regulation (EU) 2024/1689**（《人工智能法案》，2024 年 6 月 13 日通过）
> - **Directive (EU) 2024/2853**（新产品责任指令，2024 年 10 月 23 日通过 —— **超出本报告截止点**）
> - **Directive 85/374/EEC**（旧产品责任指令，ProdHaftG 的上位法）

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 19

**题目**：Investigation of Hydroforming Technology（Industrial）

**禁用的来源文章**：A review of emerging hydroforming technologies: design considerations, parametric studies, and recent innovations

- https://jeas.springeropen.com/articles/10.1186/s44147-024-00546-z
- https://www.researchgate.net/publication/385401108_A_review_of_emerging_hydroforming_technologies_design_considerations_parametric_studies_and_recent_innovations
- https://ui.adsabs.harvard.edu/abs/2024JEAS...71..205C/abstract

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里出现了来源文章的标题；与来源正文相同的 12 词片段 3 条；相同的参考文献 0 条。

相同片段举例：`of emerging hydroforming technologies design considerations parametric studies and recent innovations satish`

**这次运行打开过 460 个地址，最多的站点**：european-aluminium.eu 26，api.crossref.org 15，sciencedirect.com 14，google.com 14，ntrs.nasa.gov 12，mdpi.com 12，ebi.ac.uk 10，patents.google.com 10，ysxbcn.com 9，ahssinsights.org 9，osti.gov 8，api.semanticscholar.org 7

**打开过的、和禁用来源同一个站点的地址**：
- https://ui.adsabs.harvard.edu/abs/2013JMEP...22.3389A/abstract
- https://www.researchgate.net
- https://www.researchgate.net/profile/S_H_Zhang/publication/252689799_Finite_Element_Analysis_on_Warm_Hydroforming_of_Rectangular_Mg_Alloy_Cups_with_a_Step_Cavity/links/540dac590cf2df04e756175a.pdf

**报告的各级标题**：

    # 液压成形（Hydroforming）技术专题报告
    ## 材料选择与常见制造缺陷分析
    ## 引言：工艺背景与技术定位
    ### 关键结论速览（Executive Summary）
    # 第一部分 液压成形常用材料分析
    ## 1.1 高强度钢（HSS / AHSS）
    ### （1）材料特性
    ### （2）成形挑战
    ### （3）主要应用（含具体实例）
    ### （4）选材与工艺建议
    ## 1.2 高强度铝合金
    ### （1）材料特性
    ### （2）成形挑战
    ### （3）主要应用（按零件类型，含具体实例与数字）
    ### （4）⚠️ 常被误认为"铝液压成形"的零件（反例清单）
    ### （5）选材与工艺建议
    ## 1.3 镁合金
    ### （1）材料特性
    ### （2）成形挑战
    ### （3）主要应用（含具体实例）
    ### （4）选材与工艺建议
    ## 1.4 钛合金
    ### （1）材料特性
    ### （2）成形挑战
    ### （3）主要应用（含具体实例）
    ### （4）选材与工艺建议
    ## 1.5 四类材料横向对比
    # 第二部分 常见制造缺陷、成因及对策
    ## 2.1 表面缺陷（Surface defects）
    ### 表现形式
    ### 主要成因
    ### 建议的解决方法
    ## 2.2 回弹（Springback）
    ### 表现形式
    ### 主要成因
    ### 建议的解决方法
    ## 2.3 起皱（Wrinkling）
    ### 表现形式与分类
    ### 主要成因
    ### 建议的解决方法

**报告开头**：

> # 液压成形（Hydroforming）技术专题报告
> ## 材料选择与常见制造缺陷分析
> 
> > **报告性质**：行业分析资料整理
> > **覆盖范围**：管材液压成形（Tube Hydroforming, THF / 内高压成形 IHPF）为主，兼顾板材液压成形（Sheet Hydroforming）
> > **说明**：本报告在调研过程中**未使用**《A review of emerging hydroforming technologies: design considerations, parametric studies, and recent innovations》（Satish Chinchanikar 等，2024）及其任何转载页、摘要页、镜像页，也未引用其内容。
> 
> ---
> 
> ## 引言：工艺背景与技术定位
> 
> 液压成形是利用高压液体介质（水基乳化液或液压油）作为传力介质，使金属坯料贴合模具型腔而获得复杂形状的成形工艺，主要分为两类：
> 
> | 工艺类型 | 坯料形式 | 典型内压范围 | 主要特点 |
> |---|---|---|---|
> | 管材液压成形（THF / IHPF） | 管坯（焊管或无缝管） | 约 30–400 MPa：铝合金常 30–120 MPa，普通钢校准段 80–250 MPa，高强钢可达 300–400 MPa | 两端轴向冲头密封并补料，可一次成形闭合截面复杂构件 |
> | 板材液压成形（SHF） | 板坯 | 约 10–100 MPa | 单侧刚性模 + 液体/橡胶膜，适合小批量、深拉深件 |
> 
> **管材液压成形的典型过程**分为两个阶段：
> 1. **自由胀形阶段（free expansion）**：内压升高，管壁在模具型腔空腔内自由鼓起，同时两端轴向冲头向内进给（end-feed）补充材料；
> 2. **校准阶段（calibration）**：内压升至峰值，将管壁完全压贴模具型腔，成形圆角、筋条与局部特征。
> 
> **三种基本工艺路线**（据 WorldAutoSteel《AHSS Application Guidelines》Section 2.E 的分类）：
> 
> | 路线 | 机理 | 适用场景 |
> |---|---|---|
> | 低压液压成形（low-pressure，合模胀形） | 管坯周长略小于模腔，充入低压后**依靠合模动作**整形，内压主要用于防止屈曲，周向膨胀量极小 | 高强度、低延伸率 AHSS；可成形较小圆角而不破裂 |
> | 高压液压成形（high-pressure） | 管坯置于闭合模腔内，靠内压使材料**拉伸**贴模，圆角与特征处可产生较大应变 | 要求最小回弹与最少皱褶的零件，但受材料延伸率限制 |
> | 端部补料（end feeding） | 端部活塞把材料推入模腔，使膨胀区呈**双向应变状态** | AHSS 管件，用于降低周向膨胀的剧烈程度 |
> 
> **关键工程数值**：管径膨胀量典型为 **3%–30%**（取决于零件设计、材料与可用压力）；量产实例之一是 **Pontiac Solstice / Saturn Sky 的门槛侧梁**——材料 DP350/600，管径 132 mm，壁厚 1.8 mm（D/T = 73），成形长度达 4070 mm。目前 AHSS 管件已在 **DP700/DP1000** 级别实现量产。
> 
> 工艺设计与优化的核心是**加载路径（loading path）**，即"内压–时间"曲线与"轴向进给量–时间"曲线的组合。加载路径直接决定成形窗口（forming 

**报告结尾（含参考文献）**：

> 18. "Study on Hydroforming of Magnesium Alloy Tube under Temperature Condition", *IOP Conference Series: Materials Science and Engineering*：https://iopscience.iop.org/article/10.1088/1757-899X/301/1/012079
> 19. AHSS Guidelines — 回弹与模具补偿（Correcting Springback）：https://ahssinsights.org/forming/springback/correcting-springback/
> 20. European Aluminium《Aluminium Automotive Manual》— Products 3: Automotive Tubes（5xxx/6xxx 供货形态、Audi A2/A8、BMW/Mercedes 副车架案例）：https://european-aluminium.eu/wp-content/uploads/2022/11/aam-products-3-automotive-tubes.pdf
> 21. European Aluminium《Aluminium Automotive Manual》— Applications: Chassis & Suspension, Subframes：https://european-aluminium.eu/wp-content/uploads/2022/11/aam-applications-chassis-suspension-1-subframes.pdf
> 22. Audi 培训资料 SSP 239《Audi A2 Carrosserie》（±0.2 mm 公差、约 1700 bar、约 25 s 节拍、车顶纵梁框一体成形）：https://www.vag-technique.fr/ext_files/ssp/vw/SSP_239_Audi_A2_Carrosserie.pdf
> 23. Koç, M. (2004) — 钢冲压 vs 冷态铝液压成形发动机托架的成本/重量对比（IEEE）：https://ieeexplore.ieee.org/ielx5/5971803/6075716/06075722.pdf
> 24. Cui et al. (2023), *JOM* — 矩形截面管液压成形中钢与铝的压力/尺寸偏差/合模力对比：https://rd.springer.com/content/pdf/10.1007/s11837-023-06089-7.pdf
> 25. Australian Aluminium Council《Aluminium Extrusion Manual》（T4/T6 屈强比、延伸率与最小弯曲半径）：https://aluminium.org.au/wp-content/uploads/2023/12/Aluminium-Extrusion-Manual-Dec23.pdf
> 26. SAE 2001-01-3089（GM，管式液压成形散热器支架总成：6 个液压成形件 / 3 副模具 / 模内冲孔）：https://www.sae.org/publications/technical-papers/content/2001-01-3089/
> 27. SAE 1999-01-3180（GM，变壁厚液压成形铝挤压发动机托架）：https://www.sae.org/publications/technical-papers/content/1999-01-3180/
> 28. 专利 US 9,624,964 B2 / EP 2 917 594 B1（Dana，6061 铝液压成形传动轴：模态频率与壁厚分布）：https://patents.google.com/patent/US9624964B2/en
> 29. 专利 US 5,983,497 A（Dana，扩径铝传动轴管）：https://patents.google.com/patent/US5983497A/en
> 30. 专利 US 6,352,311 B1（Faurecia / Bertrand Faure，液压成形管式座椅靠背结构，模内冲孔装配）：https://patents.google.com/patent/US6352311B1/en
> 31. 专利 US 12,162,058 B2（Magna International，多腔铝挤压件液压成形电池托盘 / 密封界面）：https://patents.google.com/patent/US12162058B2/en
> 32. FISITA F2004F249（Gestamp Automoción，液压成形仪表板横梁）：https://www.fisita.com/
> 33. 《J. Magnesium and Alloys》11 (2023) 15–47（镁在汽车上的应用综述；Jaguar XJ 前上部构件 AM60B 压铸取代液压成形铝管、Voyah FREE 镁 CCB 等）：https://www.jmamg.com/uploadfiles/2024/04/20240407113603820.pdf
> 34. Kong, Lu & Chan, *Materials & Design* 173 (2019) 107761（镁管非等温液压成形：补料区 ≈240 °C / 变形区 ≈330 °C）：https://www.sciencedirect.com/science/article/abs/pii/S0264127519301984
> 35. TIMET / ATI / Smiths Advanced 钛合金数据表（Ti-6Al-4V、Ti-3Al-2.5V、CP 系、Ti-15-3、Beta 21S 的密度、力学性能、弹性模量、β 转变点）：http://www.timet.com/assets/local/documents/datasheets/alphaandbetaalloys/6-4.pdf
> 36. ECSS-E-HB-32-20 Part 6A《Space engineering: Superplastic forming / diffusion bonding》（超塑性数据表、应变速率敏感性 m、SPF 后强度下降、β 合金冷轧经济性）：https://ecss.nl/wp-content/uploads/handbooks/ecss-e-hb-32-20/ECSS-E-HB-32-20_Part6A.pdf
> 37. Quintus / ICAS 2020 & 2022（Ti-6Al-4V 高压温成形 HPWF：270 °C / 140 MPa / <5 min / Ri·t⁻¹ ≈ 1；SPF 对比）：http://www.icas.org/ICAS_ARCHIVE/ICAS2022/data/papers/ICAS2022_0028_paper.pdf
> 38. *Metals* 2020, 10, 1150（Ti-3Al-2.5V 热气胀成形：900 °C / 7 MPa；"高温必须用气体介质"论述）：https://doi.org/10.3390/met10091150
> 39. Fraunhofer IWU/IST（钛排气管 800 °C 单道次热液压成形、镍基模具与抗粘着涂层、粘着磨损机理）：https://www.iwu.fraunhofer.de/
> 40. USGS《Mineral Commodity Summaries — Titanium》（2024 年钛海绵价格约 $13/kg）：https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-titanium.pdf
> 41. European Aluminium《Aluminium Automotive Manual》— Products 1: Rolled Products（§1.6.6 铝的 n 值/r 值/延伸率对比；§1.9.6 AA5454-H18 再结晶软化；§1.9.7 5xxx（Mg>3%）晶间腐蚀敏感性）：https://european-aluminium.eu/wp-content/uploads/2022/11/aam-products-1-rolled-products.pdf
> 42. *Materials* 2023, 16, 1647（AA6061 管材本构拟合 K = 391.7 MPa、n = 0.2636）：https://doi.org/10.3390/ma16041647
> 43. Royne et al., *IOP Conf. Ser.: Mater. Sci. Eng.* 1238 (2022) 012011（铝温成形 150–250 °C 窗口；7075-T6 在 200 °C 仅保持约 10 s；7075-T6 的 K/n 随温度变化）：https://beta.iopscience.iop.org/article/10.1088/1757-899X/1238/1/012011/pdf
> 44. *Materials* 2025, 18, 1694（6016 回弹角随温度变化：200 °C 的 2.474° → 400 °C 的 0.197°）：https://doi.org/10.3390/ma18081694
> 45. ALFED（Aluminium Federation）— 铝成形中的粘着与模具磨损机理、边界润滑剂与 DLC+CrN 涂层建议：https://www.alfed.org.uk/
> 46. Honda R&D Technical Review 13(1) 2001（Honda Goldwing GL1800 车架：7003-T4 挤压 + 弯曲 + 电弧焊，非液压成形）：https://www.honda-ri.com/
> 
> **明确排除的来源**：本报告未使用、未引用《A review of emerging hydroforming technologies: design considerations, parametric studies, and recent innovations》（Satish Chinchanikar, Harsh Mulik, Param Varude, Sameer Atole, Neha Mundada, *Journal of Engineering and Applied Science*, 2024）及其任何转载页、摘要页或镜像页。
> 
> ---
> 
> *报告完*

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 20

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 191 条；相同的参考文献 0 条。

相同片段举例：`attitude control of quadrotors based on fractional sliding modes theory and experiments`

**这次运行打开过 333 个地址，最多的站点**：api.crossref.org 234，export.arxiv.org 28，api.semanticscholar.org 19，api.openalex.org 10，arxiv.org 7，doi.org 5，ieeexplore.ieee.org 5，dblp.org 5，w3.org 4，arc.aiaa.org 2，semanticscholar.org 2，dblp2.uni-trier.de 1

**打开过的、和禁用来源同一个站点的地址**：
- https://api.crossref.org/v1/works/http://dx.doi.org/10.1109/icra.2011.5980409
- https://doi.org/
- https://doi.org/%s

**报告的各级标题**：

    # 四旋翼无人机控制方法技术综述
    ## 0. 研究方法与范围界定
    ### 0.1 检索策略
    ### 0.2 建模基础（作为全部控制器的共同前提）
    ## 1. 第一部分：控制器分类与优缺点总结
    ### 1.1 三类控制器的界定标准
    ### 1.2 PID（比例-积分-微分）控制器
    ### 1.3 LQR（线性二次调节器）
    ### 1.4 H∞（H-无穷）控制器
    ### 1.5 Feedback Linearization（反馈线性化）
    ### 1.6 Backstepping（反步法）
    ### 1.7 SMC（滑模控制）
    ### 1.8 MPC（模型预测控制）
    ### 1.9 Adaptive Control（自适应控制）
    ### 1.10 Fuzzy Logic（模糊逻辑控制）
    ### 1.11 Neural Network（神经网络控制）
    ## 2. 第二部分：性能改进策略汇总表
    ### 2.1 表格使用说明
    ### 2.2 完整策略表
    ### 2.3 参考文献
    ## 附录 A：控制器横向对比速查
    ## 附录 B：性能评价指标清单
    ## 附录 C：常用验证平台
    ## 附录 D：截至 2021 年 5 月的技术演进趋势
    ## 附录 E：扩展文献目录（分会话汇总）
    #### PID 与 LQR
    #### H∞
    #### Feedback Linearization 与 Backstepping
    #### MPC
    #### SMC
    #### 自适应控制
    #### 模糊逻辑控制
    #### 神经网络控制

**报告开头**：

> # 四旋翼无人机控制方法技术综述
> 
> **文献覆盖范围**：截至 2021 年 5 月公开发表的文献与成果
> **对象平台**：四旋翼无人机（quadrotor / quadcopter），含其变体（六旋翼、倾转旋翼在控制律可迁移处一并讨论）
> **报告结构**：第一部分为控制器分类与优缺点总结；第二部分为性能改进策略汇总表
> 
> ---
> 
> ## 0. 研究方法与范围界定
> 
> ### 0.1 检索策略
> 
> 本综述的文献检索围绕以下关键词族展开，检索时限定发表时间不晚于 2021 年 5 月：
> 
> - **控制器名称族**：`quadrotor PID`、`quadrotor LQR`、`quadrotor H-infinity`、`quadrotor feedback linearization`、`quadrotor backstepping`、`quadrotor sliding mode control`、`quadrotor model predictive control`、`quadrotor adaptive control`、`quadrotor fuzzy logic control`、`quadrotor neural network control`。
> - **改进机理族**：`anti-windup`、`gain scheduling`、`fractional order PID`、`iterative LQR`、`mu-synthesis`、`loop shaping`、`command filtered backstepping`、`dynamic surface control`、`super-twisting`、`terminal sliding mode`、`tube MPC`、`real-time iteration`、`L1 adaptive`、`composite adaptation`、`incremental nonlinear dynamic inversion`、`interval type-2 fuzzy`、`ANFIS`、`deep reinforcement learning`、`sim-to-real`、`domain randomization`。
> - **平台与验证族**：`AscTec Hummingbird`、`Crazyflie`、`Parrot Bebop`、`Pixhawk`、`PX4 SITL`、`RotorS`、`Flightmare`、`ROS Gazebo`。
> 
> 文献来源覆盖 arXiv、IEEE Xplore、ScienceDirect、SpringerLink、IFAC-PapersOnLine、Wiley、SAGE、Frontiers、MDPI，以及 ETH Zurich、UPenn GRASP、MIT ACL、NASA 与 DLR 的技术报告与学位论文。
> 
> ### 0.2 建模基础（作为全部控制器的共同前提）
> 
> 四旋翼的通用非线性模型可写成如下形式（12 阶状态）：
> 
> $$
> \begin{aligned}
> \dot{p} &= v \\
> m\dot{v} &= m g e_3 - f R e_3 + d_p \\
> \dot{R} &= R\,\hat{\Omega} \\
> J\dot{\Omega} &= -\Omega \times J\Omega + \tau + d_\Omega
> \end{aligned}
> $$
> 
> 其中 $p\in\mathbb{R}^3$ 为位置，$v

**报告结尾（含参考文献）**：

> 63. D. Gandhi, L. Pinto, A. Gupta. Learning to Fly by Crashing. *2017 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*, 2017. https://arxiv.org/abs/1704.05588
> 64. A. Giusti, J. Guzzi, D. C. Ciresan, F.-L. He, J. P. Rodriguez, F. Fontana, M. Faessler, C. Forster, J. Schmidhuber, G. Di Caro, D. Scaramuzza, L. M. Gambardella. A Machine Learning Approach to Visual Perception of Forest Trails for Mobile Robots. *IEEE Robotics and Automation Letters*, 2016. https://doi.org/10.1109/LRA.2015.2509024
> 65. A. Loquercio, A. I. Maqueda, C. R. del-Blanco, D. Scaramuzza. DroNet: Learning to Fly by Driving. *IEEE Robotics and Automation Letters*, 2018. https://doi.org/10.1109/LRA.2018.2795643
> 66. T. Schaul, J. Quan, I. Antonoglou, D. Silver. Prioritized Experience Replay. *International Conference on Learning Representations (ICLR)*, 2016. https://arxiv.org/abs/1511.05952
> 67. L.-J. Lin. Self-Improving Reactive Agents Based on Reinforcement Learning, Planning and Teaching. *Machine Learning*, 1992. https://doi.org/10.1007/BF00992699
> 68. Y. Bengio, J. Louradour, R. Collobert, J. Weston. Curriculum learning. *Proceedings of the 26th Annual International Conference on Machine Learning (ICML)*, 2009. https://doi.org/10.1145/1553374.1553380
> 69. J. Tobin, R. Fong, A. Ray, J. Schneider, W. Zaremba, P. Abbeel. Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World. *2017 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*, 2017. https://arxiv.org/abs/1703.06907
> 70. X. B. Peng, M. Andrychowicz, W. Zaremba, P. Abbeel. Sim-to-Real Transfer of Robotic Control with Dynamics Randomization. *2018 IEEE International Conference on Robotics and Automation (ICRA)*, 2018. https://doi.org/10.1109/ICRA.2018.8460528
> 71. D. Chen, B. Zhou, V. Koltun, P. Krähenbühl. Learning by Cheating. *Conference on Robot Learning (CoRL)*, 2019. https://arxiv.org/abs/1912.12294
> 72. J. Hwangbo, J. Lee, A. Dosovitskiy, D. Bellicoso, V. Tsounis, V. Koltun, M. Hutter. Learning agile and dynamic motor skills for legged robots. *Science Robotics*, 2019. https://doi.org/10.1126/scirobotics.aau5872
> 73. J. Lee, J. Hwangbo, L. Wellhausen, V. Koltun, M. Hutter. Learning quadrupedal locomotion over challenging terrain. *Science Robotics*, 2020. https://doi.org/10.1126/scirobotics.abc5986
> 74. A. Nagabandi, G. Kahn, R. S. Fearing, S. Levine. Neural Network Dynamics for Model-Based Deep Reinforcement Learning with Model-Free Fine-Tuning. *2018 IEEE International Conference on Robotics and Automation (ICRA)*, 2018. https://arxiv.org/abs/1708.02596
> 75. A. Nagabandi, I. Clavera, S. Liu, R. S. Fearing, P. Abbeel, S. Levine, C. Finn. Learning to Adapt in Dynamic, Real-World Environments Through Meta-Reinforcement Learning. *International Conference on Learning Representations (ICLR)*, 2019. https://arxiv.org/abs/1803.11347
> 76. J. Achiam, D. Held, A. Tamar, P. Abbeel. Constrained Policy Optimization. *Proceedings of the 34th International Conference on Machine Learning (ICML)*, 2017. https://arxiv.org/abs/1705.10528
> 77. G. Dalal, K. Dvijotham, M. Vecerik, T. Hester, C. Paduraru, Y. Tassa. Safe Exploration in Continuous Action Spaces. arXiv:1801.08757, 2018. https://arxiv.org/abs/1801.08757
> 78. M. Alshiekh, R. Bloem, R. Ehlers, B. Könighofer, S. Niekum, U. Topcu. Safe Reinforcement Learning via Shielding. *Proceedings of the AAAI Conference on Artificial Intelligence*, 2018. https://doi.org/10.1609/aaai.v32i1.11797
> 79. J. H. Gillula, C. J. Tomlin. Guaranteed Safe Online Learning via Reachability: tracking a ground target using a quadrotor. *2012 IEEE International Conference on Robotics and Automation (ICRA)*, 2012. https://doi.org/10.1109/ICRA.2012.6225136
> 80. B. Lütjens, M. Everett, J. P. How. Safe Reinforcement Learning With Model Uncertainty Estimates. *2019 International Conference on Robotics and Automation (ICRA)*, 2019. https://doi.org/10.1109/ICRA.2019.8793611
> 81. Y. Gal, Z. Ghahramani. Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning. *Proceedings of the 33rd International Conference on Machine Learning (ICML)*, 2016. https://arxiv.org/abs/1506.02142
> 82. G. Hinton, O. Vinyals, J. Dean. Distilling the Knowledge in a Neural Network. arXiv:1503.02531, 2015. https://arxiv.org/abs/1503.02531
> 83. S. Han, J. Pool, J. Tran, W. J. Dally. Learning both Weights and Connections for Efficient Neural Networks. *Advances in Neural Information Processing Systems (NeurIPS)*, 2015. https://arxiv.org/abs/1506.02626
> 84. S. Han, H. Mao, W. J. Dally. Deep Compression: Compressing Deep Neural Networks with Pruning, Trained Quantization and Huffman Coding. *International Conference on Learning Representations (ICLR)*, 2016. https://arxiv.org/abs/1510.00149
> 85. C. Kyrkou, G. Plastiras, S. Venieris, T. Theocharides, C.-S. Bouganis. DroNet: Efficient convolutional neural network detector for real-time UAV applications. *2018 Design, Automation & Test in Europe Conference & Exhibition (DATE)*, 2018. https://doi.org/10.23919/DATE.2018.8342149
> 86. L. Hewing, K. P. Wabersich, M. Menner, M. N. Zeilinger. Learning-Based Model Predictive Control: Toward Safe Learning in Control. *Annual Review of Control, Robotics, and Autonomous Systems*, 2020. https://doi.org/10.1146/annurev-control-090419-075625
> 87. A. Aswani, H. Gonzalez, S. S. Sastry, C. Tomlin. Provably safe and robust learning-based model predictive control. *Automatica*, 2013. https://doi.org/10.1016/j.automatica.2013.02.003
> 88. C. J. Ostafew, A. P. Schoellig, T. D. Barfoot. Robust Constrained Learning-based NMPC enabling reliable mobile robot path tracking. *The International Journal of Robotics Research*, 2016. https://doi.org/10.1177/0278364916645661
> 89. G. Torrente, E. Kaufmann, P. Foehn, D. Scaramuzza. Data-Driven MPC for Quadrotors. *IEEE Robotics and Automation Letters*, 2021. https://arxiv.org/abs/2102.05773
> 90. D. Jang, J. Yoo, C. Y. Son, H. J. Kim, K. H. Johansson. Networked Operation of a UAV Using Gaussian Process-Based Delay Compensation and Model Predictive Control. *2019 International Conference on Robotics and Automation (ICRA)*, 2019. https://doi.org/10.1109/ICRA.2019.8793472
> 91. J. E. Kooi, R. Babuška. Inclined Quadrotor Landing using Deep Reinforcement Learning. *2021 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*, 2021. https://arxiv.org/abs/2103.09043
> 92. F. Furrer, M. Burri, M. Achtelik, R. Siegwart. RotorS—A Modular Gazebo MAV Simulator Framework. In *Robot Operating System (ROS): The Complete Reference*, Studies in Computational Intelligence, Springer, 2016. https://doi.org/10.1007/978-3-319-26054-9_23
> 93. G. Silano, E. Aucone, L. Iannelli. CrazyS: A Software-In-The-Loop Platform for the Crazyflie 2.0 Nano-Quadcopter. *2018 26th Mediterranean Conference on Control and Automation (MED)*, 2018. https://doi.org/10.1109/MED.2018.8442759
> 94. G. Silano, L. Iannelli. CrazyS: A Software-in-the-Loop Simulation Platform for the Crazyflie 2.0 Nano-Quadcopter. In *Robot Operating System (ROS): The Complete Reference (Volume 4)*, Studies in Computational Intelligence, Springer, 2019. https://doi.org/10.1007/978-3-030-20190-6_4
> 95. L. Meier, D. Honegger, M. Pollefeys. PX4: A node-based multithreaded open source robotics framework for deeply embedded platforms. *2015 IEEE International Conference on Robotics and Automation (ICRA)*, 2015. https://doi.org/10.1109/ICRA.2015.7140074
> 96. N. Michael, D. Mellinger, Q. Lindsey, V. Kumar. The GRASP Multiple Micro-UAV Testbed. *IEEE Robotics & Automation Magazine*, 2010. https://doi.org/10.1109/MRA.2010.937855
> 97. A. Çakır, S. Akpancar. ROS-Based Control of the DJI Matrice 100 Robot with QR Images Obtained from DJI Guidance. *International Journal of Engineering Trends and Technology*, 2020. https://doi.org/10.14445/22315381/IJETT-V68I1P206

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 21

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 126 条；相同的参考文献 0 条。

相同片段举例：`kim sastry feedback linearization vs adaptive sliding mode control for quadrotor helicopter`

**这次运行打开过 40 个地址，最多的站点**：export.arxiv.org 10，api.crossref.org 8，api.openalex.org 5，arxiv.org 5，w3.org 4，ar5iv.labs.arxiv.org 3，api.semanticscholar.org 2，mjee.isfahan.iau.ir 1，doaj.org 1，sic.ici.ro 1

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 四旋翼无人机（Quadrotor）控制方法技术综述
    ## 第一部分　控制器分类与优缺点总结
    ### 1.1 三类控制方法的总体定位
    ### 1.2 PID（比例–积分–微分控制）
    ### 1.3 LQR（线性二次型调节器）
    ### 1.4 H∞（H-无穷鲁棒控制）
    ### 1.5 Feedback Linearization（反馈线性化）
    ### 1.6 Backstepping（反步法）
    ### 1.7 SMC（滑模控制）
    ### 1.8 MPC（模型预测控制）
    ### 1.9 Adaptive Control（自适应控制）
    ### 1.10 Fuzzy Logic（模糊逻辑控制）
    ### 1.11 Neural Network（神经网络控制）
    ## 第二部分　性能改进策略汇总表
    ## 附录 A　参考文献（按控制器归类）
    ### A.1 通用综述与基础建模
    ### A.2 PID
    ### A.3 LQR
    ### A.4 H∞
    ### A.5 反馈线性化（含 INDI）
    ### A.6 反步法
    ### A.7 SMC
    ### A.8 MPC
    ### A.9 自适应控制
    ### A.10 模糊逻辑
    ### A.11 神经网络与强化学习
    ## 附录 A（续）　补充文献（按控制器分组，均经 Crossref 或 arXiv 元数据核实）
    #### A.12.1 PID 补充文献
    #### A.12.2 LQR 补充文献
    #### A.12.3 H∞ 补充文献
    #### A.12.4 反馈线性化补充文献
    #### A.12.5 反步法补充文献
    #### A.12.6 SMC 补充文献
    ## 附录 B　方法学说明与使用限制

**报告开头**：

> # 四旋翼无人机（Quadrotor）控制方法技术综述
> 
> **覆盖范围**：公开文献与工业实践，时间截至 **2021 年 5 月**（少量 2021 年上半年在线发表的工作亦纳入）。
> **组织方式**：第一部分给出控制器分类与逐项优缺点；第二部分给出"控制器混合策略 + 控制器自身改进策略"完整表格。
> **阅读约定**：控制器名称保留英文缩写；"混合（hybridization）"指该控制器与另一种控制器/算法在同一控制回路中协同工作；"改进（improvement）"指不改变控制器主体类别、通过附加算法、观测器、优化器、结构改造这些手段提升其性能。
> 
> ---
> 
> ## 第一部分　控制器分类与优缺点总结
> 
> ### 1.1 三类控制方法的总体定位
> 
> | 类别 | 包含的控制器 | 对模型的依赖 | 核心思想 | 典型适用场景 | 主要短板 |
> |---|---|---|---|---|---|
> | **线性控制**（Linear Control） | PID、LQR、H∞ | 强（需要在工作点附近线性化的模型；PID 可弱化到"误差驱动"） | 在悬停/低速工作点对非线性动力学线性化，用成熟的线性系统理论设计控制器 | 悬停、定点、低速轨迹跟踪、室内/无强扰动环境、算力受限的嵌入式飞控 | 飞行包线变大（大姿态角、高速、大加速度）或强风、负载变化时模型失配严重，性能下降甚至失稳 |
> | **非线性控制**（Nonlinear Control） | 反馈线性化、反步法、滑模控制（SMC）、模型预测控制（MPC）、自适应控制 | 中—强（MPC/反馈线性化强依赖模型；SMC/自适应可容忍部分不确定性） | 直接利用非线性模型结构，或在线估计/补偿不确定性，或滚动求解带约束的优化问题 | 大机动、强扰动、参数时变（负载投送、电池电压下降、执行器故障）、需要显式约束处理的场景 | 设计与稳定性证明复杂、参数多、在线计算量大、对状态估计质量敏感、部分方法（SMC）存在抖振 |
> | **基于学习的控制**（Learning-Based Control） | 模糊逻辑（Fuzzy Logic）、神经网络（Neural Network，含强化学习） | 弱—中（可完全数据驱动，也可只学习残差模型） | 用模糊规则、神经网络或强化学习策略逼近控制律/逆动力学/残差模型，从数据或经验中获取控制能力 | 模型难以精确建模、存在未建模效应（气动干扰、地面效应、负载摆动）、需要端到端感知—控制、复杂机动 | 缺乏通用稳定性/鲁棒性保证、训练数据与算力需求大、可解释性与适航认证困难、仿真到现实的迁移（sim-to-real）差距 |
> 
> **分类边界的三点说明（重要）**：
> 
> 1. **H∞ 属于线性鲁棒控制**。经典 H∞ 综合建立在线性分式变换（LFT）与 Riccati/LMI 求解之上，其"鲁棒"体现在对建模误差与外部扰动的最坏情况抑制，而非对非线性结构的直接处理。非线性 H∞（Hamilton–Jacobi–Isaacs 方程）在四旋翼上有研究，但工程主流仍是线性 H∞。本综述按用户要求将其归入线性控制。
> 2. **MPC 与自适应控制横跨线性/非线性**。线性 MPC（在参考轨迹上逐点线性化 + 二次规划）本质是线性最优控制；非线性 MPC（NMPC）直接使用非线性模型。MRAC 可基于线性模型，而自适应反步、自适应滑模则属于非线性自适应。本文按"主流四旋翼实现"把它们归入非线性控制，并在表格中标注其线性/非线性变体。
> 3. **模糊逻辑与神经网络既可独立成控制器，

**报告结尾（含参考文献）**：

> 219. Wang K., Hua C., Chen J., Cai M. "Dual-loop integral sliding mode control for robust trajectory tracking of a quadrotor". International Journal of Systems Science, 2019. https://doi.org/10.1080/00207721.2019.1622815
> 220. Labbadi M., Cherkaoui M. "Novel robust super twisting integral sliding mode controller for a quadrotor under external disturbances". International Journal of Dynamics and Control, 2019. https://doi.org/10.1007/s40435-019-00599-6
> 221. Labbadi M., Cherkaoui M. "Robust adaptive nonsingular fast terminal sliding-mode tracking control for an uncertain quadrotor UAV subjected to disturbances". ISA Transactions, 2020. https://doi.org/10.1016/j.isatra.2019.10.012
> 222. Labbadi M., Cherkaoui M. "Robust Integral Terminal Sliding Mode Control for Quadrotor UAV with External Disturbances". International Journal of Aerospace Engineering, 2019. https://doi.org/10.1155/2019/2016416
> 223. Zhao G., Chen G., Chen J., Hua C. "Finite-time Control for Image-based Visual Servoing of a Quadrotor Using Nonsingular Fast Terminal Sliding Mode". International Journal of Control, Automation and Systems, 2020. https://doi.org/10.1007/s12555-019-0005-9
> 224. Mechali O., Iqbal J., Xie X., Xu L. et al. "Robust Finite-Time Trajectory Tracking Control of Quadrotor Aircraft via Terminal Sliding Mode-Based Active Antidisturbance Approach: A PIL Experiment". International Journal of Aerospace Engineering, 2021. https://doi.org/10.1155/2021/5522379
> 225. Shang W., Jing G., Zhang D., Chen T. et al. "Adaptive Fixed Time Nonsingular Terminal Sliding-Mode Control for Quadrotor Formation With Obstacle and Inter-Quadrotor Avoidance". IEEE Access, 2021. https://doi.org/10.1109/access.2021.3074316
> 226. Ahmed N., Chen M., Shao S. "Disturbance Observer Based Tracking Control of Quadrotor With High-Order Disturbances". IEEE Access, 2020. https://doi.org/10.1109/access.2020.2964013
> 227. Cai W., She J., Wu M., Ohyama Y. "Disturbance suppression for quadrotor UAV using sliding-mode-observer-based equivalent-input-disturbance approach". ISA Transactions, 2019. https://doi.org/10.1016/j.isatra.2019.02.028
> 228. Nekoukar V., Mahdian Dehkordi N. "Robust path tracking of a quadrotor using adaptive fuzzy terminal sliding mode control". Control Engineering Practice, 2021. https://doi.org/10.1016/j.conengprac.2021.104763
> 229. Ahmed E. "Robust Adaptive Sliding Mode Control Design for Quadrotor Unmanned Aerial Vehicle Trajectory Tracking". International Journal of Computing and Digital Systems, 2020. https://doi.org/10.12785/ijcds/090210
> 230. Xu G., Xia Y., Zhai D.-H., Ma D. "Adaptive prescribed performance terminal sliding mode attitude control for quadrotor under input saturation". IET Control Theory & Applications, 2020. https://doi.org/10.1049/iet-cta.2019.0488
> 231. Ullah S., Iqbal K., Malik F. M. "Fault-Tolerant Sliding Mode Control of a Quadrotor UAV with Delayed Feedback". International Journal of Mechanical Engineering and Robotics Research, 2020. https://doi.org/10.18178/ijmerr.9.1.1-6
> 232. Kim H. S., Hwang S., Joo Y. H. "Interval type-2 fuzzy-model-based fault-tolerant sliding mode tracking control of a quadrotor UAV under actuator saturation". IET Control Theory & Applications, 2020. https://doi.org/10.1049/iet-cta.2020.0521
> 233. Xiong J.-J., Zhang G. "Discrete-time sliding mode control for a quadrotor UAV". Optik, 2016. https://doi.org/10.1016/j.ijleo.2016.01.010
> 234. Pazooki M., Mazinan A. H. "Hybrid fuzzy-based sliding-mode control approach, optimized by genetic algorithm for quadrotor unmanned aerial vehicles". Complex & Intelligent Systems, 2017. https://doi.org/10.1007/s40747-017-0051-y
> 235. Zare M., Pazooki F., Etemadi Haghighi S. "Quadrotor UAV Position and Altitude Tracking Using an Optimized Fuzzy-Sliding Mode Control". IETE Journal of Research, 2020. https://doi.org/10.1080/03772063.2020.1793694
> 236. Maqsood H., Qu Y. "Nonlinear Disturbance Observer Based Sliding Mode Control of Quadrotor Helicopter". Journal of Electrical Engineering & Technology, 2020. https://doi.org/10.1007/s42835-020-00421-w
> 237. Xiao J. "Trajectory planning of quadrotor using sliding mode control with extended state observer". Measurement and Control, 2020. https://doi.org/10.1177/0020294020927419
> 238. Behera A. K., Bandyopadhyay B., Yu X. "Periodic event-triggered sliding mode control". Automatica, 2018（通用理论；四旋翼专用的事件触发滑模在本次检索中未获证实）. https://doi.org/10.1016/j.automatica.2018.06.035
> 239. Van M., Ge S. S., Ren H. "Finite Time Fault Tolerant Control for Robot Manipulators Using Time Delay Estimation and Continuous Nonsingular Fast Terminal Sliding Mode Control". IEEE Transactions on Cybernetics, 2017（机械臂平台；四旋翼上的时延估计滑模在本次检索中未获证实）. https://doi.org/10.1109/tcyb.2016.2555307
> 
> ---
> 
> ## 附录 B　方法学说明与使用限制
> 
> 1. **时间边界**：本综述的文献检索与结论以 2021 年 5 月为截止点。2021 年下半年及以后发表的成果（例如基于 Koopman 算子、扩散策略、端到端视觉—语言—动作模型的控制工作）不在覆盖范围内；个别 2021 年上半年在线发表的工作已纳入。
> 2. **检索与核实方式**：控制器优缺点部分综合了教科书级共识与公开综述；表格中的混合策略与改进策略条目均对应可检索的公开文献、专利或工业实践文档。凡参考文献作者名单无法逐一确认者，仅列出题名、出处与年份，不做推测性署名。
> 3. **未使用的资料声明**：按照任务约束，本报告**没有查阅、没有引用**任务中明确指定的那篇禁引四旋翼控制器综述文献，也没有访问其任何原文页、转载页、摘要页、聚合页或 DOI 页面；附录 A 的参考文献列表中不包含该文献，报告中的任何结论、数据与表述均不依赖该文献。
> 4. **横向比较的注意点**：不同文献的"性能更优"结论往往建立在不同的机型、控制器参数、轨迹、风扰条件与评价指标之上，跨文献直接比较数值意义有限。若需选型，建议在同一仿真/实验平台上复现候选控制器并统一评价指标。
> 5. **工程落地建议**：从工业实践看，最稳妥的路线是"串级 PID（含前馈、抗饱和、滤波与增益调度）作为基线，按需叠加观测器（EKF/UKF/ESO/DOB）与自适应或学习补偿；对约束敏感的任务再引入 MPC"。纯粹替换为非线性或学习型控制器之前，应评估算力、状态估计质量、失效模式与认证要求。
> 6. **证据分级与已标注的空白**：附录 A 与附录 A（续）中的文献均经出版方注册元数据（Crossref）或 arXiv API 核实，题名、作者、出处、年份与 DOI 一致；第二轮补充文献的核实结果同时保存在工作区 `lit/` 目录下，可逐条复核。补充条目绝大多数为四旋翼平台；少数为方法性文献或相邻平台，已在条目中显式标注“非四旋翼平台”“机械臂平台”“通用理论”。以下方向在本次检索中**未能**找到截至 2021 年 5 月的四旋翼专用文献，因此第二部分表格中仅作策略层面描述而未附具体平台文献：四旋翼专用的事件触发滑模控制、四旋翼专用的时延估计（TDE）滑模控制、四旋翼专用的 μ 综合/DK 迭代、四旋翼专用的 H∞ 回路成形、四旋翼专用的 H∞ 控制器降阶。这些空白不代表方法无效，而是说明当时的公开四旋翼验证文献有限，使用者应自行核实后续文献。
> 
> ---
> 

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 22

**题目**：A Literature Review of Systemic Financial Risk（Finance & Business）

**禁用的来源文章**：A Review of Micro-Based Systemic Risk Research from Multiple Perspectives

- https://www.mdpi.com/1099-4300/22/7/711
- https://pubmed.ncbi.nlm.nih.gov/33286483/
- https://www.researchgate.net/publication/342524950_A_Review_of_Micro-Based_Systemic_Risk_Research_from_Multiple_Perspectives
- https://ui.adsabs.harvard.edu/abs/2020Entrp..22..711B/abstract
- https://www.mdpi.com/1099-4300/22/7/711/reprints
- https://researchportal.u-tokai.ac.jp/ja/publications/a-review-of-micro-based-systemic-risk-research-from-multiple-pers

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 309 个地址，最多的站点**：api.crossref.org 83，ideas.repec.org 65，bis.org 15，levyinstitute.org 13，api.semanticscholar.org 13，econpapers.repec.org 12，nber.org 9，fraser.stlouisfed.org 6，digitalcommons.bard.edu 5，web.archive.org 5，aeaweb.org 5，archive.org 4

**打开过的、和禁用来源同一个站点的地址**：
- https://pubmed.ncbi.nlm.nih.gov/11875207/

**报告的各级标题**：

    # 系统性金融风险研究综述：理论传统的对比与微观结构视角
    ## 引言：综述的范围、问题意识与方法说明
    ### 一、问题的提出
    ### 二、综述的组织结构
    ### 三、方法说明与引用规范
    ## 第一部分 理论基础对比：金融加速器与金融不稳定性假说
    ### 1.1 金融加速器（一）：思想渊源、微观基础与核心逻辑
    #### 1.1.1 思想渊源：为什么信贷摩擦重要
    #### 1.1.2 核心因果链：从信息不对称到产出波动
    #### 1.1.3 抵押品分支：Kiyotaki & Moore (1997) 的信贷约束机制
    #### 1.1.4 关键假设及其对系统性风险的含义
    #### 1.1.5 风险的产生与传导：一个关键的限定
    ### 1.2 金融加速器（二）：在量化 DSGE 中的嵌入、扩展与批评
    #### 1.2.1 BGG 合约如何嵌入 DSGE
    #### 1.2.2 量化效果：放大是有界的
    #### 1.2.3 主要扩展：从企业资产负债表到金融中介与住房
    #### 1.2.4 对 2007—2009 年危机的解释与宏观审慎含义
    #### 1.2.5 主要批评
    ### 1.3 明斯基的金融不稳定性假说
    #### 1.3.1 著述脉络
    #### 1.3.2 两价格理论：投资为什么由金融驱动
    #### 1.3.3 三种融资类型：对冲、投机与庞氏
    #### 1.3.4 核心命题："稳定即不稳定"与两个定理
    #### 1.3.5 关键假设
    #### 1.3.6 政策结论："大政府"与"大银行"
    #### 1.3.7 后续发展
    ### 1.4 两种理论的系统比较
    #### 1.4.1 七个维度的对照
    #### 1.4.2 共识与不可通约之处
    #### 1.4.3 形式化与调和尝试
    #### 1.4.4 经验证据
    #### 1.4.5 早期 2020 年的争论状态
    ## 第二部分 微观结构视角下的系统性风险研究
    ### 2.1 金融网络：复杂性、稳健但脆弱与核心-边缘结构
    #### 2.1.1 基础结果：相互债权、共同保险与"风险分担即传染渠道"
    #### 2.1.2 "稳健但脆弱"（robust-yet-fragile）的准确含义
    #### 2.1.3 级联与阈值模型：为什么"更多连接"未必更安全
    #### 2.1.4 核心-边缘结构：经验证据
    #### 2.1.5 网络度量与重构方法：结论对假设高度敏感
    #### 2.1.6 政策含义

**报告开头**：

> # 系统性金融风险研究综述：理论传统的对比与微观结构视角
> 
> **文献覆盖范围：截至 2020 年 3 月（不含 2020 年 3 月以后的研究）**
> 
> ---
> 
> ## 引言：综述的范围、问题意识与方法说明
> 
> ### 一、问题的提出
> 
> 2007—2009 年全球金融危机之后，系统性金融风险（systemic financial risk）从金融监管的实务议题上升为宏观经济学、金融经济学与金融监管研究的核心对象。这场危机同时动摇了两条研究传统的自信：一方面，以动态随机一般均衡（DSGE）模型为主干、以"金融加速器"（financial accelerator）为核心机制的宏观金融框架，未能预见危机，也被普遍认为难以在模型内部生成一场真正的金融危机；另一方面，长期处于主流之外、以海曼·明斯基（Hyman Minsky）的"金融不稳定性假说"（Financial Instability Hypothesis, FIH）为代表的非正统传统，虽然被认为"预见了"危机，却长期缺乏可检验的形式化表达。
> 
> 危机后的十余年间，研究沿着两条互补的路径推进：一是把金融摩擦更细致地嵌入动态一般均衡框架，并对其进行反思与扩展；二是从微观市场结构出发，研究金融网络、流动性与传染如何把个体冲击放大为系统性事件。本综述即沿这两条线索展开。
> 
> ### 二、综述的组织结构
> 
> 本综述分为两个主体部分：
> 
> - **第一部分 理论基础对比**：系统梳理并对比两种解释系统性风险形成机制的主要理论——DSGE 传统中的金融加速器理论，与明斯基的金融不稳定性假说。内容包括各自的思想渊源、核心逻辑、关键假设、对实体经济的影响机制，以及二者的系统比较与调和尝试。
> - **第二部分 微观结构视角下的系统性风险研究**：围绕四个相互衔接的方向展开——金融网络（复杂性与"稳健但脆弱"、核心-边缘结构）、市场流动性与融资流动性（流动性螺旋）、金融传染（渠道与两种主要类型），以及银行间传染、贱卖外部性与系统性风险的实证度量工具箱。
> 
> 最后一部分给出综合评述：两条传统如何互补，微观结构研究如何为宏观理论提供传导机制的微观基础。
> 
> ### 三、方法说明与引用规范
> 
> 1. **时间边界**：本综述仅使用 2020 年 3 月之前公开发表或可获取的文献。凡在 2020 年 3 月之后才发表（或仅有其后版本）的研究，均不纳入；对工作论文后来正式发表的情形，以 2020 年 3 月之前的版本年份与出处为准。
> 2. **引用规范**：正文尽量给出"作者—年份—文献名—期刊/出版方"的可追溯信息；对无法逐项核实的卷期页码等信息，正文以作者与年份为准，并在参考文献中标注。
> 3. **代表性学者**：在相应机制处点明代表性学者及其关键文献，例如金融加速器处的伯南克（Bernanke）、格特勒（Gertler）与吉尔克里斯特（Gilchrist），流动性螺旋处的布伦纳迈尔（Brunnermeier）与佩德森（Pedersen），金融网络处的哈尔丹（Haldane）、盖伊与卡帕迪亚（Gai & Kapadia）、阿杰姆奥卢等（Acemoglu et al.），金融传染处的马松（Masson）与福布斯和里戈本（Forbes & Rigobon），以及明斯基（Minsky）本人及其后继者。
> 4. **文献类型**：优先采用原始期刊论文、工作论文与专著；监管与政策文件以 BIS、FSB、Basel Committee 等在 2020 年 3 月之前发布的版本为准。
> 5. **引用更正提示**：本综述在核对过程中发现并更正了若干在文献中被广

**报告结尾（含参考文献）**：

> 172. Borio, C., & Lowe, P. (2002). Assessing the Risk of Banking Crises. *BIS Quarterly Review*, December 2002, 43–54.
> 173. Boss, M., Elsinger, H., Summer, M., & Thurner, S. (2004). Network Topology of the Interbank Market. *Quantitative Finance*, 4(6), 677–684（另有 OeNB *Financial Stability Report* 7, 77–87）.
> 174. Brownlees, C., & Engle, R. F. (2017). SRISK: A Conditional Capital Shortfall Measure of Systemic Risk. *Review of Financial Studies*, 30(1), 48–79.
> 175. Cifuentes, R., Ferrucci, G., & Shin, H. S. (2005). Liquidity Risk and Contagion. *Journal of the European Economic Association*, 3(2–3), 556–565.
> 176. De Bandt, O., & Hartmann, P. (2000). Systemic Risk: A Survey. *ECB Working Paper No. 35*.
> 177. Degryse, H., & Nguyen, G. (2007). Interbank Exposures: An Empirical Examination of Contagion Risk in the Belgian Banking System. *International Journal of Central Banking*, 3(2), 123–171.
> 178. Drehmann, M., & Tarashev, N. (2011). Measuring the Systemic Importance of Interconnected Banks. *BIS Working Paper No. 342*（期刊版 *Journal of Financial Intermediation*, 22(4), 586–607, 2013）.
> 179. Eisenberg, L., & Noe, T. H. (2001). Systemic Risk in Financial Systems. *Management Science*, 47(2), 236–249.
> 180. Ellul, A., Jotikasthira, C., & Lundblad, C. T. (2011). Regulatory Pressure and Fire Sales in the Corporate Bond Market. *Journal of Financial Economics*, 101(3), 596–620.
> 181. Elsinger, H., Lehar, A., & Summer, M. (2006). Risk Assessment for Banking Systems. *Management Science*, 52(9), 1301–1314.
> 182. Engle, R. F. (2002). Dynamic Conditional Correlation. *Journal of Business & Economic Statistics*, 20(3), 339–350.
> 183. Furfine, C. H. (2003). Interbank Exposures: Quantifying the Risk of Contagion. *Journal of Money, Credit and Banking*, 35(1), 111–128.
> 184. Greenwood, R., Landier, A., & Thesmar, D. (2015). Vulnerable Banks. *Journal of Financial Economics*, 115(3), 471–485.
> 185. Huang, X., Zhou, H., & Zhu, H. (2009). A Framework for Assessing the Systemic Risk of Major Financial Institutions. *Journal of Banking & Finance*, 33(11), 2036–2049.
> 186. Huang, X., Zhou, H., & Zhu, H. (2012). Systemic Risk Contributions. *Journal of Financial Services Research*, 42(1), 55–83.
> 187. Kaufman, G. G., & Scott, K. E. (2003). What Is Systemic Risk, and Do Bank Regulators Retard or Contribute to It? *The Independent Review*, 7(3), 371–391.
> 188. Müller, J. (2006). Interbank Credit Lines as a Channel of Contagion. *Journal of Financial Services Research*, 29(1), 37–60.
> 189. Schwarcz, S. L. (2008). Systemic Risk. *Georgetown Law Journal*, 97(1), 193–249.
> 190. Tarashev, N., Borio, C., & Tsatsaronis, K. (2010). Attributing Systemic Risk to Individual Institutions. *BIS Working Paper No. 308*.
> 191. Upper, C. (2011). Simulation Methods to Assess the Danger of Contagion in Interbank Markets. *Journal of Financial Stability*, 7(3), 111–125.
> 192. van Lelyveld, I., & Liedorp, F. (2006). Interbank Contagion in the Dutch Banking Sector: A Sensitivity Analysis. *International Journal of Central Banking*, 2(2), 99–133.
> 193. Wells, S. (2004). Financial Interlinkages in the United Kingdom's Interbank Market and the Risk of Contagion. *Bank of England Working Paper No. 235*.
> 
> ### H. 官方与政策文件
> 
> 194. Basel Committee on Banking Supervision (2010). *Guidance for National Authorities Operating the Countercyclical Capital Buffer*. Bank for International Settlements.
> 195. Basel Committee on Banking Supervision (2011). *Global Systemically Important Banks: Assessment Methodology and the Additional Loss Absorbency Requirement*. Bank for International Settlements.
> 196. Basel Committee on Banking Supervision (2013). *Global Systemically Important Banks: Updated Assessment Methodology and the Higher Loss Absorbency Requirement* (BCBS255). Bank for International Settlements.
> 197. CPSS-IOSCO (2012). *Principles for Financial Market Infrastructures*. Bank for International Settlements.
> 198. Financial Stability Board (2011, rev. 2014). *Key Attributes of Effective Resolution Regimes for Financial Institutions*.
> 199. Financial Stability Board (2015). *Principles on Loss-Absorbing and Recapitalisation Capacity of G-SIBs in Resolution: Total Loss-Absorbing Capacity (TLAC) Term Sheet*.
> 
> ---
> 
> *本综述由 8 个相互独立的专题调研分头完成、再统一整合与核对。所有引文均发表于 2020 年 3 月之前；正文中标注"待考"的卷期页码等信息，建议在正式引用前再次核对原始出处。*

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 23

**题目**：Survey of Quadrotor UAV Control Methods（Science & Technology）

**禁用的来源文章**：A Review on Comparative Remarks, Performance Evaluation and Improvement Strategies of Quadrotor Controllers

- https://www.mdpi.com/2227-7080/9/2/37
- https://scispace.com/papers/a-review-on-comparative-remarks-performance-evaluation-and-42w5jk652t
- https://www.researchgate.net/publication/351649063_A_Review_on_Comparative_Remarks_Performance_Evaluation_and_Improvement_Strategies_of_Quadrotor_Controllers
- https://dro.deakin.edu.au/articles/journal_contribution/A_review_on_comparative_remarks_performance_evaluation_and_improvement_strategies_of_quadrotor_controllers/20665578/1
- https://ouci.dntb.gov.ua/en/works/4Yp2ryQ7/
- https://doi.org/10.3390/TECHNOLOGIES9020037

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 170 条；相同的参考文献 0 条。

相同片段举例：`attitude control of quadrotors based on fractional sliding modes theory and experiments`

**这次运行打开过 503 个地址，最多的站点**：api.crossref.org 256，api.semanticscholar.org 86，api.openalex.org 17，export.arxiv.org 13，dblp.org 11，doi.org 8，w3.org 7，arxiv.org 7，mdpi.com 5，link.springer.com 4，infoscience.epfl.ch 4，ieeexplore.ieee.org 4

**打开过的、和禁用来源同一个站点的地址**：
- https://doi.org/10.1007/s40998-018-0155-4
- https://doi.org/10.1016/j.ifacol.2019.11.195
- https://doi.org/10.1016/j.isatra.2014.03.006
- https://doi.org/10.1016/j.jfranklin.2011.02.008
- https://doi.org/10.1016/j.jfranklin.2011.06.025
- https://doi.org/10.1080/00207179308923053
- https://doi.org/10.1109/TCST.2018.2831175
- https://doi.org/10.4236/ojapps.2014.414053
- https://www.mdpi.com/1424-8220/19/1/24
- https://www.mdpi.com/1424-8220/19/1/24/pdf
- https://www.mdpi.com/2079-9292/8/7/760/pdf
- https://www.mdpi.com/2218-6581/8/2/36

**报告的各级标题**：

    # 四旋翼无人机（Quadrotor）控制方法技术综述
    ## 0. 检索范围、分类约定与排除说明
    ### 0.1 检索范围
    ### 0.2 排除说明（重要）
    ### 0.3 分类约定与边界说明
    ## 第一部分　控制器分类与特性总结
    ### 1.1 三类控制方法总览
    ### 1.2 逐控制器优缺点总结
    #### 1.2.1 PID（比例—积分—微分控制）
    #### 1.2.2 LQR（线性二次调节器）
    #### 1.2.3 H∞（H-无穷鲁棒控制）
    #### 1.2.4 Feedback Linearization（反馈线性化 / 动态逆 / 精确线性化）
    #### 1.2.5 Backstepping（反步法）
    #### 1.2.6 SMC（滑模控制）
    #### 1.2.7 MPC（模型预测控制）
    #### 1.2.8 Adaptive Control（自适应控制）
    #### 1.2.9 Fuzzy Logic（模糊逻辑控制）
    #### 1.2.10 Neural Network（神经网络控制）
    ### 1.3 小结：三类方法的取舍逻辑
    ## 第二部分　性能改进策略总表
    ### 2.1 四旋翼控制器性能改进策略总表
    ### 2.2 表格阅读说明与编写约定
    ### 2.3 表格要点解读
    ### 2.3.1 证据缺口与引用核实说明（重要）
    ### 2.4 参考文献
    #### 2.4.1 综述、专著与教材
    #### 2.4.2 PID 与经典频域控制
    #### 2.4.3 LQR、SDRE 与最优控制
    #### 2.4.4 H∞ 与鲁棒控制
    #### 2.4.5 反馈线性化、动态逆与微分平坦
    #### 2.4.6 反步法
    #### 2.4.7 滑模控制
    #### 2.4.8 模型预测控制
    #### 2.4.9 自适应控制与观测器
    #### 2.4.10 模糊逻辑控制
    #### 2.4.11 神经网络与强化学习
    #### 2.4.12 其他四旋翼建模、控制与实现
    #### 2.4.13 补充文献 A：线性控制（PID / LQR / H∞，经 Crossref 逐条核实）
    #### 2.4.14 补充文献 B：非线性控制（反馈线性化 / 反步法 / 滑模，经 Crossref 逐条核实）
    #### 2.4.15 补充文献 C：MPC 与自适应控制（经 Crossref 逐条核实）

**报告开头**：

> # 四旋翼无人机（Quadrotor）控制方法技术综述
> 
> **时间截点：文献覆盖至 2021 年 5 月**
> **文档用途：四旋翼控制方法调研报告（第一部分：控制器特性总结；第二部分：性能改进策略表格）**
> 
> ---
> 
> ## 0. 检索范围、分类约定与排除说明
> 
> ### 0.1 检索范围
> 
> 本报告以四旋翼（quadrotor / quadcopter / 四旋翼直升机）的姿态控制、位置控制与轨迹跟踪控制为对象，覆盖以下十种控制方法：
> 
> - 线性控制类：**PID**、**LQR**、**H∞**
> - 非线性控制类：**Feedback Linearization（反馈线性化）**、**Backstepping（反步法）**、**SMC（滑模控制）**、**MPC（模型预测控制）**、**Adaptive Control（自适应控制）**
> - 基于学习的控制类：**Fuzzy Logic（模糊逻辑）**、**Neural Network（神经网络，含深度强化学习）**
> 
> 文献时间范围为 2021 年 5 月（含）之前公开发表/在线可得的期刊论文、会议论文、学位论文与专著。经典控制理论工具（如 Lyapunov 稳定性、Riccati 方程、LMI、滑模理论、自适应理论）的原始文献不受此时间限制，但报告中对四旋翼应用层面的引用均控制在 2021 年 5 月以前。
> 
> ### 0.2 排除说明（重要）
> 
> 按任务要求，以下综述文章及其**全部转载页、镜像页、摘要页、聚合页**在本次调研中被完全排除：在检索、阅读、撰写全过程中**未打开、未读取、未引用**，其任何内容与结论均未进入本报告。被排除的入口包括该文在 MDPI、SciSpace、ResearchGate、Deakin University DRO、OUCI（ouci.dntb.gov.ua）以及 doi.org 上的页面。本报告全部结论均来自独立检索到的其他公开文献。
> 
> ### 0.3 分类约定与边界说明
> 
> | 类别 | 纳入的控制器 | 设计基础 | 说明 |
> |---|---|---|---|
> | 线性控制 | PID、LQR、H∞ | 在悬停/慢速飞行平衡点处线性化得到的线性模型（或频域对象） | H∞ 属于**鲁棒线性控制**：在频域/LMI 框架下处理线性模型的不确定性与外扰。LQR 属于**最优线性控制**。PID 是**无模型/弱模型**的线性定常控制。 |
> | 非线性控制 | 反馈线性化、反步法、SMC、MPC、自适应控制 | 直接基于四旋翼非线性模型，用 Lyapunov/几何/最优控制理论设计 | MPC 若采用线性预测模型可归入线性控制，但四旋翼上以 NMPC/LTV-MPC 为主，故归入非线性类。自适应控制本质属非线性/鲁棒控制范畴。 |
> | 基于学习的控制 | 模糊逻辑、神经网络 | 不依赖（或仅部分依赖）解析模型，依靠专家知识、数据或奖励信号构造控制律 | 模糊逻辑严格说是**知识驱动/智能控制**而非"学习"，但在四旋翼控制文献中习惯与神经网络并列为"智能/学习型控制"。神经网络类包含监督学习、自适应神经网络与深度强化学习。 |
> 
> **关于类别边界的四点提醒：**
> 
> 1. 十种控制器中，PID、LQR、H∞ 均在**线性化模型**上设计，其有效性严格局限于平衡点邻域；一旦进入大姿态机动（如特技飞行、强风、大载荷偏移），线性化误差会同时侵蚀性能指标与稳定性裕度。
> 2. 非线性类控制器并非"无需模型"：反馈线性化与反步法对模型精度的依赖甚至高于线性方法；真正降低模型依赖的

**报告结尾（含参考文献）**：

> 372. F. L. Lewis, A. Yesildirek, K. Liu, "Multilayer neural-net robot controller with guaranteed tracking performance", *IEEE Transactions on Neural Networks*, 1996. https://doi.org/10.1109/72.485674
> 373. J. Kober, J. A. Bagnell, J. Peters, "Reinforcement learning in robotics: a survey", *International Journal of Robotics Research*, 2013. https://doi.org/10.1177/0278364913495721
> 374. J. Ibarz, J. Tan, C. Finn, M. Kalakrishnan, S. Pastor, S. Levine, "How to train your robot with deep reinforcement learning: lessons we have learned", *International Journal of Robotics Research*, 2021. https://doi.org/10.1177/0278364920987859
> 375. A. Gandhi, L. Pinto, A. Gupta, "Learning to fly by crashing", *IEEE/RSJ IROS*, 2017. https://doi.org/10.1109/IROS.2017.8206247
> 376. S. Ross, N. Melik-Barkhudarov, K. S. Shankar, J. A. Wendel, D. Dey, J. A. Bagnell, M. Hebert, "Learning monocular reactive UAV control in cluttered natural environments", *IEEE ICRA*, 2013. https://doi.org/10.1109/ICRA.2013.6630809
> 377. P. Abbeel, A. Coates, A. Y. Ng, "Autonomous helicopter aerobatics through apprenticeship learning", *International Journal of Robotics Research*, 2010. https://doi.org/10.1177/0278364910371999
> 378. A. Carrio, C. Sampedro, A. Rodriguez-Ramos, P. Campoy, "A review of deep learning methods and applications for unmanned aerial vehicles", *Journal of Sensors*, 2017. https://doi.org/10.1155/2017/3296874
> 379. J. Hewing, K. P. Wabersich, M. Menner, M. N. Zeilinger, "Learning-based model predictive control: toward safe learning in control", *Annual Review of Control, Robotics, and Autonomous Systems*, 2020. https://doi.org/10.1146/annurev-control-090419-075625
> 380. A. Aswani, H. Gonzalez, S. S. Sastry, C. Tomlin, "Provably safe and robust learning-based model predictive control", *Automatica*, 2013. https://doi.org/10.1016/j.automatica.2013.02.003
> 381. T. Koller, F. Berkenkamp, M. Turchetta, A. Krause, "Learning-based model predictive control for safe exploration", *IEEE CDC*, 2018. https://doi.org/10.1109/CDC.2018.8619572
> 382. S. Gros, M. Zanon, "Data-driven economic NMPC using reinforcement learning", *IEEE Transactions on Automatic Control*, 2020. https://doi.org/10.1109/TAC.2019.2913768
> 383. J. Kabzan, L. Hewing, A. Liniger, M. N. Zeilinger, "Learning-based model predictive control for autonomous racing", *IEEE Robotics and Automation Letters*, 2019. https://doi.org/10.1109/LRA.2019.2926677
> 384. C. J. Ostafew, A. P. Schoellig, T. D. Barfoot, "Robust constrained learning-based NMPC enabling reliable mobile robot path tracking", *International Journal of Robotics Research*, 2016. https://doi.org/10.1177/0278364916645661
> 385. F. Zhao, J. Queralta, T. Westerlund, "Sim-to-real transfer in deep reinforcement learning for robotics: a survey", *IEEE SSCI*, 2020. https://doi.org/10.1109/SSCI47803.2020.9308468
> 386. X. B. Peng, M. Andrychowicz, W. Zaremba, P. Abbeel, "Sim-to-real transfer of robotic control with dynamics randomization", *IEEE ICRA*, 2018. https://doi.org/10.1109/ICRA.2018.8460528
> 387. S. Rudin, "Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead", *Nature Machine Intelligence*, 2019. https://doi.org/10.1038/s42256-019-0048-x
> 388. J. García, F. Fernández, "Safe exploration of state and action spaces in reinforcement learning", *Journal of Artificial Intelligence Research*, 2012. https://doi.org/10.1613/jair.3761
> 389. G. Dulac-Arnold, D. Mankowitz, T. Hester, "Challenges of real-world reinforcement learning", arXiv:1904.12901, 2019. https://arxiv.org/abs/1904.12901
> 390. F. L. Lewis, D. Vrabie, "Reinforcement learning and adaptive dynamic programming for feedback control", *IEEE Circuits and Systems Magazine*, 2009. https://doi.org/10.1109/MCAS.2009.933854
> 391. R. Rubi, M. Morcego, R. Perez, "A deep reinforcement learning approach for path following on a quadrotor", *European Control Conference (ECC)*, 2020. https://doi.org/10.23919/ECC51009.2020.9143591
> 392. Y. Xu, Z. Liu, X. Wang, "Monocular vision based autonomous landing of quadrotor through deep reinforcement learning", *Chinese Control Conference (CCC)*, 2018. https://doi.org/10.23919/ChiCC.2018.8482830
> 393. C. Chi, Z. Ji, X. Gao, "Attitude tracking control for a quadrotor via backstepping and adaptive dynamic programming", *CCDC*, 2019. https://doi.org/10.1109/CCDC.2019.8832799
> 394. T. Guettal, A. Chelihi, S. Touba, H. Glida, R. Ajgou, "Neural network-based adaptive backstepping controller for UAV quadrotor system", *CCSSP*, 2020. https://doi.org/10.1109/CCSSP49278.2020.9151813
> 395. Y. Wang, X. Chen, Y. Lin, "Fixed-time backstepping control of quadrotor trajectory tracking based on neural network", *IEEE Access*, 2020. https://doi.org/10.1109/ACCESS.2020.3027052
> 396. D. Grande, G. Chowdhary, J. P. How, "Experimental validation of Bayesian nonparametric adaptive control using Gaussian processes", *Journal of Aerospace Information Systems*, 2014. https://doi.org/10.2514/1.I010190
> 
> ---
> 
> ## 结语：面向工程选型的四条建议
> 
> 1. **从任务剖面出发选择控制器类别。** 悬停与低速航点飞行优先选择级联 PID + 前馈 + 观测器，成本最低且可靠性最高；需要强抗扰与快速机动的任务优先考虑 SMC（配超螺旋与扰动观测器）或反步 + 自适应；需要显式避障与约束满足的任务优先考虑 MPC（配 LTV 线性化与代码生成求解器）；任务涉及复杂感知与决策时，用学习型方法处理感知—决策层，把姿态内环留给经典控制器。
> 2. **把"观测器"作为第一优先级增强项。** 无论主体控制器是哪种，ESO/DOB/卡尔曼滤波带来的抗扰与噪声改善通常比更换控制器本体更划算，且不破坏原有稳定性论证。
> 3. **把"混合"限制在必要的最小集合。** 每增加一个模块都会带来新的整定参数、新的失效模式与新的验证工作量；建议以"一个标称控制器 + 一个扰动观测器 + 一个学习/自适应补偿项"为常见上限。
> 4. **把"验证"纳入设计的第一天。** 学习型与自适应控制器的主要障碍不是性能而是验证；建议从设计之初就准备蒙特卡洛仿真、硬件在环测试、失效注入与安全层（控制屏障函数、备份控制器、包线保护），并保留可解释的基线控制器作为降级方案。
> 

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 24

**题目**：A Literature Review of Systemic Financial Risk（Finance & Business）

**禁用的来源文章**：A Review of Micro-Based Systemic Risk Research from Multiple Perspectives

- https://www.mdpi.com/1099-4300/22/7/711
- https://pubmed.ncbi.nlm.nih.gov/33286483/
- https://www.researchgate.net/publication/342524950_A_Review_of_Micro-Based_Systemic_Risk_Research_from_Multiple_Perspectives
- https://ui.adsabs.harvard.edu/abs/2020Entrp..22..711B/abstract
- https://www.mdpi.com/1099-4300/22/7/711/reprints
- https://researchportal.u-tokai.ac.jp/ja/publications/a-review-of-micro-based-systemic-risk-research-from-multiple-pers

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 3 条。

**这次运行打开过 184 个地址，最多的站点**：api.crossref.org 60，ideas.repec.org 46，bis.org 14，nber.org 10，digitalcommons.bard.edu 8，api.openalex.org 7，levyinstitute.org 4，link.springer.com 3，ecb.europa.eu 3，bankofengland.co.uk 3，api.semanticscholar.org 3，pnas.org 2

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 系统性金融风险研究综述：理论范式与微观结构
    ## 引言
    # 第一部分 理论基础对比
    ## 1.1 金融加速器的理论渊源与DSGE建模框架
    ### 思想渊源与"信贷观点"：从债务-通缩到有成本的状态验证
    ### 奠基性模型：BG（1989）、KM（1997）与"逃向质量"
    ### BGG（1999）的DSGE架构、校准与后续扩展
    ### 关键假设与传导链条小结
    ## 1.2 金融加速器的传导机制、政策含义与经验检验
    ### 传导渠道的细分与比较
    ### 开放经济与新兴市场版本
    ### 政策含义
    ### 经验检验与批评
    ## 1.3 明斯基金融不稳定性假说的思想渊源与核心命题
    ### 生平与思想谱系：资产负债表版的凯恩斯
    ### 代表性著作与文献
    ### 三类融资、两价格理论与"稳定即不稳定"
    ### 概念辨析与风险向实体经济的传导
    ## 1.4 金融不稳定性假说的模型化、经验证据与批评
    ### 三条形式化路线及其技术取舍
    ### 经验证据：信贷繁荣、杠杆与危机
    ### 批评与争论
    ### 总体评价：模型化现状与证据强度
    ## 1.5 两大范式的系统对比与综合
    ### 对比框架与总表
    ### 各自的优势与批评
    ### 接触点、互补性与融合尝试
    ### 小结：对系统性风险研究的方法论启示
    # 第二部分 微观结构研究
    ## 2.1 金融网络、稳健但脆弱与核心-边缘结构
    ### 网络的表示、传导机制与数据基础
    ### 网络结构与稳定性：稳健但脆弱的经济学逻辑
    ### 核心-边缘结构的经验证据与风险含义
    ### 政策与测度含义
    ## 2.2 市场流动性、融资流动性与流动性螺旋
    ### 概念界定：市场流动性、融资流动性与流动性的公共品属性
    ### "流动性螺旋"的因果机制
    ### 杠杆、保证金与抵押品的顺周期性
    ### 2007–09 年危机的经验解读、测度与政策
    ## 2.3 金融传染的渠道、类型与测度

**报告开头**：

> # 系统性金融风险研究综述：理论范式与微观结构
> 
> **信息截止时间：2020年3月。** 本综述所引文献、事实与数据的发表时间均不晚于2020年3月。
> 
> ## 引言
> 
> 2007—2009年全球金融危机之后，系统性风险（systemic risk）从金融监管的实务议题上升为宏观经济学、金融学与市场微观结构交叉的核心研究领域。所谓系统性风险，通常指金融体系的一部分或全部受损，并通过金融体系与实体经济之间的反馈回路，导致金融服务大规模中断、进而危及整体经济活动的风险。其研究至少包含两个相互补充的层面：一是**理论层面**，即金融摩擦与金融脆弱性如何进入宏观经济模型，风险如何产生、放大并传导至实体经济；二是**微观结构层面**，即金融机构之间的网络关联、流动性的相互依赖以及跨市场传染，如何把个体冲击转化为系统性事件。
> 
> 本综述按上述两个层面组织。**第一部分"理论基础对比"**梳理并对照两种主要解释：以动态随机一般均衡（DSGE）模型为载体的"金融加速器"（financial accelerator）理论，以及以海曼·明斯基（Hyman P. Minsky）为代表的"金融不稳定性假说"（Financial Instability Hypothesis, FIH）。前者构成危机后主流宏观金融分析的技术基准，后者提供了一种关于内生脆弱性的替代叙事与理论传统。第一部分先分别阐述两者的思想渊源、核心机制与关键假设，继而评述其模型化与经验证据，最后给出系统性的对比与综合。**第二部分"微观结构研究"**聚焦三个方向：金融网络的复杂性与稳定性（含"稳健但脆弱"与核心-边缘结构）、市场流动性与融资流动性的相互作用（"流动性螺旋"），以及金融传染的渠道、类型与测度。每一节均力求指出代表性学者、关键文献与理论贡献，并说明结论的适用条件与争议所在。
> 
> 在方法上，本综述以已发表的学术文献为依据，优先引用奠基性论文、权威期刊论文与官方研究报告；凡涉及存在争议的经验结论，均标明争议来源。文献引用采用"作者（年份）"格式，完整出处见文末参考文献。
> 
> # 第一部分 理论基础对比
> 
> ## 1.1 金融加速器的理论渊源与DSGE建模框架
> 
> 金融加速器（financial accelerator）指信贷市场摩擦使初始冲击经由借款人资产负债表状况被放大并持续传播的机制。本节梳理其思想渊源、"信贷观点"的理论基础、奠基性模型与 Bernanke-Gertler-Gilchrist（BGG, 1999）的 DSGE 架构，并归纳该范式的关键假设与核心传导链条；传导机制的经验检验、政策含义与批评留待 1.2 节。
> 
> ### 思想渊源与"信贷观点"：从债务-通缩到有成本的状态验证
> 
> **债务-通缩。** Fisher（1933）提出，过度负债与价格水平下跌相互作用会形成累积性的破坏过程：名义债务负担因通缩而实际加重，债务人被迫抛售资产（distress selling），资产价格与货币流通速度进一步下降，净值缩水、破产增加，从而引发新一轮通缩。其关键洞见是：名义值固定的债务合约使价格变动具有真实的分配与破坏效应，金融因素不能被化约为纯粹的货币现象。
> 
> **大萧条中的非货币金融因素。** Bernanke（1983）在货币收缩之外识别出"信贷中介成本"（cost of credit intermediation）的上升：银行体系崩溃使储蓄向借款人转化的成本显著提高，进而压低总需求，为1930年代产出的持续低迷提供了货币因素之外的解释。该文被视为"金融加速器"的思想前身——信贷市场状况本身成为独立的传播

**报告结尾（含参考文献）**：

> - Peek, J., & Rosengren, E. S. (2000). Collateral Damage: Effects of the Japanese Bank Crisis on Real Activity in the United States. *American Economic Review*, 90(1), 30–45. DOI: 10.1257/aer.90.1.30
> - Pericoli, M., & Sbracia, M. (2003). A primer on financial contagion. *Journal of Economic Surveys*, 17(4), 571–608. DOI: 10.1111/1467-6419.00205
> - Pesaran, M. H., & Pick, A. (2007). Econometric issues in the analysis of contagion. *Journal of Economic Dynamics and Control*, 31(4), 1245–1277.
> - Pritsker, M. (2001). The channels for financial contagion. In S. Claessens & K. Forbes (Eds.), *International Financial Contagion*. Kluwer Academic Publishers.（卷期页码待核）
> - Quadrini, V. (2011). Financial Frictions in Macroeconomic Fluctuations. *Federal Reserve Bank of Richmond Economic Quarterly*, 97(3)（页码待核）.
> - Rajan, R. G. (2005). *Has Financial Development Made the World Riskier?* NBER Working Paper No. 11728；亦载于 Federal Reserve Bank of Kansas City, *Proceedings – Economic Policy Symposium – Jackson Hole*, 313–369. DOI: 10.3386/w11728
> - Reinhart, C. M., & Rogoff, K. S. (2009). *This Time Is Different: Eight Centuries of Financial Folly*. Princeton, NJ: Princeton University Press.
> - Rigobon, R. (2002). Contagion: How to measure it? In S. Edwards & J. A. Frankel (Eds.), *Preventing Currency Crises in Emerging Markets*. University of Chicago Press.（工作论文 NBER WP 8118；章节页码待核）
> - Rodriguez, J. C. (2007). Measuring financial contagion: A copula approach. *Journal of Empirical Finance*, 14(3), 401–423.
> - Roll, R. (1984). A simple implicit measure of the effective bid-ask spread in an efficient market. *Journal of Finance*, 39(4), 1127–1139. DOI: 10.1111/j.1540-6261.1984.tb03897.x
> - Ryoo, S. (2010). Long waves and short cycles in a model of endogenous financial fragility. *Journal of Economic Behavior & Organization*, 74(3), 163–186. https://ideas.repec.org/a/eee/jeborg/v74y2010i3p163-186.html
> - Schinasi, G. J., & Smith, R. T. (2000). Portfolio diversification, leverage, and financial contagion. *IMF Staff Papers*, 47(2).（工作论文 IMF WP 1999/136；页码待核）
> - Schnabl, P. (2012). The International Transmission of Bank Liquidity Shocks: Evidence from an Emerging Market. *Journal of Finance*, 67(3), 897–932.
> - Schularick, M., & Taylor, A. M. (2012). Credit booms gone bust: Monetary policy, leverage cycles, and financial crises, 1870–2008. *American Economic Review*, 102(2), 1029–1061. DOI: 10.1257/aer.102.2.1029
> - Schumpeter, J. A. (1934). *The Theory of Economic Development*. Cambridge, MA: Harvard University Press.
> - Shleifer, A., & Vishny, R. W. (1997). The limits of arbitrage. *Journal of Finance*, 52(1), 35–55. DOI: 10.1111/j.1540-6261.1997.tb03807.x
> - Shleifer, A., & Vishny, R. W. (2010). Unstable banking. *Journal of Financial Economics*, 97(3), 306–318. DOI: 10.1016/j.jfineco.2009.10.007
> - Shleifer, A., & Vishny, R. W. (2011). Fire sales in finance and macroeconomics. *Journal of Economic Perspectives*, 25(1), 29–48. DOI: 10.1257/jep.25.1.29
> - Smets, F., & Wouters, R. (2007). Shocks and frictions in US business cycles: A Bayesian DSGE approach. *American Economic Review*, 97(3), 586–606. DOI: 10.1257/aer.97.3.586
> - Soramäki, K., Bech, M. L., Arnold, J., Glass, R. J., & Beyeler, W. E. (2007). The topology of interbank payment flows. *Physica A: Statistical Mechanics and its Applications*, 379(1), 317–333. DOI: 10.1016/j.physa.2006.11.093
> - Stein, J. C. (2012). Monetary policy as financial stability regulation. *Quarterly Journal of Economics*, 127(1), 57–95. DOI: 10.1093/qje/qjr054
> - Stiglitz, J. E. (2011). Rethinking macroeconomics: What failed, and how to repair it. *Journal of the European Economic Association*, 9(4), 591–645. DOI: 10.1111/j.1542-4774.2011.01030.x
> - Stiglitz, J. E. (2018). Where modern macroeconomics went wrong. *Oxford Review of Economic Policy*, 34(1–2), 70–106.
> - Svensson, L. E. O. (2017). Cost-Benefit Analysis of Leaning Against the Wind. *Journal of Monetary Economics*, 90, 193–213.
> - Taylor, L., & O'Connell, S. A. (1985). A Minsky crisis. *Quarterly Journal of Economics*, 100(Supplement), 871–885.
> - Thurner, S., Farmer, J. D., & Geanakoplos, J. (2012). Leverage causes fat tails and clustered volatility. *Quantitative Finance*, 12(5), 695–707. DOI: 10.1080/14697688.2012.674301
> - Tobin, J. (1969). A General Equilibrium Approach to Monetary Theory. *Journal of Money, Credit and Banking*, 1(1), 15–29.
> - Townsend, R. M. (1979). Optimal Contracts and Competitive Markets with Costly State Verification. *Journal of Economic Theory*, 21(2), 265–293. DOI: 10.1016/0022-0531(79)90031-0
> - Upper, C. (2011). Simulation methods to assess the danger of contagion in interbank markets. *Journal of Financial Stability*, 7(3), 111–125. DOI: 10.1016/j.jfs.2010.12.001
> - Upper, C., & Worms, A. (2004). Estimating bilateral exposures in the German interbank market: Is there a danger of contagion? *European Economic Review*, 48(4), 827–849. https://ideas.repec.org/a/eee/eecrev/v48y2004i4p827-849.html
> - Van Rijckeghem, C., & Weder, B. (2001). Sources of contagion: Is it finance or trade? *Journal of International Economics*, 54(2), 293–308.
> - Vayanos, D. (2004). *Flight to quality, flight to liquidity, and the pricing of risk* (NBER Working Paper No. 10327). National Bureau of Economic Research. https://www.nber.org/papers/w10327 （工作论文）
> - White, W. R. (2006). *Is Price Stability Enough?* BIS Working Papers No. 205. https://www.bis.org/publ/work205.htm
> - Wray, L. R. (2011). Minsky's Money Manager Capitalism and the Global Financial Crisis. *International Journal of Political Economy*, 40(2), 5–20. DOI: 10.2753/IJP0891-1916400201
> - Yuan, K. (2005). Asymmetric price movements and borrowing constraints: A rational expectations equilibrium model of crises, contagion, and confusion. *The Journal of Finance*, 60(1), 379–411.

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 25

**题目**：Legal Research on Traffic Accident Liability for German Autonomous Vehicles（Crime & Law）

**禁用的来源文章**：Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China

- https://www.mdpi.com/2032-6653/15/7/305
- https://www.mdpi.com/2032-6653/15/7/305/pdf
- https://www.mdpi.com/2032-6653/15/7/305/html
- https://www.mdpi.com/2032-6653/15/7/305/xml
- https://www.researchgate.net/publication/382225455_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_of_the_German_Legislation_for_China
- https://www.researchgate.net/publication/382400472_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_from_the_German_Legislation_for_China/download

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里出现了来源文章的标题；与来源正文相同的 12 词片段 11 条；相同的参考文献 0 条。

相同片段举例：`distribution of the burden of proof in autonomous driving tort cases implications`

**这次运行打开过 610 个地址，最多的站点**：buzer.de 147，web.archive.org 69，gesetze-im-internet.de 44，dejure.org 24，publications.europa.eu 23，de.wikipedia.org 22，eur-lex.europa.eu 20，dserver.bundestag.de 16，gesetze-in-app.de 14，gesetze-im-internet.juris.de 12，prinz.law 12，verkehrslexikon.de 8

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 德国 L3 级及以上自动驾驶汽车交通事故责任划分调研报告
    ## 阅读提示与研究方法说明
    ### 德文核心术语对照
    ## 一、核心结论速览
    ### 表 1　三类主体的责任框架（2024 年中期）
    ### 表 2　举证责任一目了然
    ## 二、法律与制度框架
    ### 2.1 自动化等级与德国法上的概念对应
    ### 2.2 2017 年改革：为高度自动化驾驶建立框架
    ### 2.3 2021 年改革：《自动驾驶法》
    ### 2.4 国际规则与技术标准
    ### 2.5 责任竞合的整体图景
    ## 三、驾驶员（Fahrzeugführer）的责任
    ### 3.1 谁是「驾驶员」？
    ### 3.2 法律依据
    ### 3.3 责任类型：过错责任，但过错被推定
    ### 3.4 受害人对驾驶员需要证明什么？
    ### 3.5 驾驶员如何免责？
    ### 3.6 自动驾驶场景下的特别问题
    #### （1）L3 的权利与义务来自 § 1b StVG
    #### （2）信赖原则的边界
    #### （3）表见证明（Anscheinsbeweis）在自动驾驶下的争议
    #### （4）事故数据：§ 63a StVG（L3）
    ### 3.7 驾驶员责任小结
    ## 四、车辆持有人（Halter）的责任
    ### 4.1 法律依据与责任类型：无过错危险责任
    ### 4.2 与驾驶员责任的区别
    ### 4.3 受害人对持有人需要证明什么？
    ### 4.4 持有人的免责：不可抗力与不可避免事件
    #### （1）不可抗力（§ 7 Abs. 2 StVG，höhere Gewalt）
    #### （2）不可避免事件（§ 17 Abs. 3 StVG，unabwendbares Ereignis）
    ### 4.5 责任限额（§ 12 StVG）与强制保险
    ### 4.6 内部关系与追偿
    ### 4.7 L4 自主驾驶中的特别规则
    ### 4.8 持有人责任小结
    ## 五、生产者侵权责任（Produzentenhaftung）与制造商产品责任（Herstellerprodukthaftung）
    ### 5.1 两个概念的真实区别
    ### 5.2 表 3　两条路径的逐项对比
    ### 5.3 Produzentenhaftung（§ 823 BGB）详解
    #### （1）四种缺陷类型

**报告开头**：

> # 德国 L3 级及以上自动驾驶汽车交通事故责任划分调研报告
> 
> **信息基准：2024 年中期（2024 年 6 月前后）**
> **报告语言：中文（保留德文法律术语与条文原文）**
> 
> ---
> 
> ## 阅读提示与研究方法说明
> 
> 1. **时间基准**：本报告以 **2024 年中期** 有效的德国法和欧盟法为准。2024 年下半年及以后才发生的变化（例如欧盟新产品责任指令的正式通过、德国 2026 年修法），在文中均以「**2024 年中之后**」明确标注，不作为基准时点的法律状态陈述。
> 2. **来源限制（最高优先级规则的遵守）**：本报告在调研与写作全过程中 **没有打开、阅读、检索或引用** 以下文献及其任何转载页、镜像页、摘要页或 PDF/HTML/XML 版本：
>    - *Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China*（作者：Zhihua Chen、Qianyi Cai、Hanbing Wei，MDPI *World Electric Vehicle Journal* 15(7):305；及其 ResearchGate 转载/下载页）。
>    - 文中所有结论均来自下文「来源清单」中列明的其他独立来源。特此声明。
> 3. **来源等级**：正文引用区分 **[一手]**（法律条文、判决全文、立法机关文件、官方公报、官方机构页面）与 **[二手]**（律所评论、学术文献、专业媒体）。凡调研中未能核实的细节，文中标注「未能核实」，不做虚构。
> 4. **条文版本**：德国法条文以 2024 年中期有效的整合版本为准。由于调研环境对 `gesetze-im-internet.de`、`dejure.org` 的直接访问不稳定，部分条文系通过 **Wayback Machine 的 2024 年 4—8 月存档快照** 核对（见来源清单），并与 `buzer.de`、`gesetze-in-app.de` 等整合文本交叉比对。个别条文（如 § 18 StVG）自 2020 年 7 月以来未修改，且已用 2024 年 6 月的官方存档快照核对。
> 
> ### 德文核心术语对照
> 
> | 德文 | 中文 | 说明 |
> |---|---|---|
> | Fahrzeugführer / Fahrer | 驾驶员、车辆驾驶者 | § 1a Abs. 4 StVG：激活并使用自动化功能的人，即使不亲手驾驶，也是 Fahrzeugführer |
> | Halter | 车辆持有人 | 为自身计算、以自己的责任对车辆行使事实处分权并承担使用费用之人（判例定义） |
> | Technische Aufsicht | 技术监督人 | L4（§ 1d StVG）中通过远程/后台方式解除自动驾驶功能、放行替代操纵的自然人，**不是**驾驶员 |
> | Hersteller | 制造商 | ProdHaftG § 4 的法定概念（含准制造商、进口商、供应商替代责任） |
> | Produzent | 生产者 | 非法定术语，学理上多与 Hersteller 混用；「Produzentenhaftung」指基于 § 823 BGB 的判例法责任 |
> | Produzentenhaftung | 生产者侵权责任 | 基于 BGB § 823 的**过错责任**（判例法），举证责任在过错上倒置（因果关系原

**报告结尾（含参考文献）**：

> 
> **StVG § 1b（驾驶员的权利与义务）**
> 
> > (1) Der Fahrzeugführer darf sich während der Fahrzeugführung mittels hoch- oder vollautomatisierter Fahrfunktionen gemäß § 1a vom Verkehrsgeschehen und der Fahrzeugsteuerung abwenden; dabei muss er derart wahrnehmungsbereit bleiben, dass er seiner Pflicht nach Absatz 2 jederzeit nachkommen kann.
> > (2) Der Fahrzeugführer ist verpflichtet, die Fahrzeugsteuerung unverzüglich wieder zu übernehmen, 1. wenn das hoch- oder vollautomatisierte System ihn dazu auffordert oder 2. wenn er erkennt oder auf Grund offensichtlicher Umstände erkennen muss, dass die Voraussetzungen für eine bestimmungsgemäße Verwendung der hoch- oder vollautomatisierten Fahrfunktionen nicht mehr vorliegen.
> 
> **StVG § 12 Abs. 1（限额）**
> 
> > Der Ersatzpflichtige haftet 1. im Fall der Tötung oder Verletzung eines oder mehrerer Menschen durch dasselbe Ereignis nur bis zu einem Betrag von insgesamt fünf Millionen Euro, bei Verursachung des Schadens auf Grund der Verwendung einer hoch- oder vollautomatisierten Fahrfunktion gemäß § 1a oder beim Betrieb einer autonomen Fahrfunktion gemäß § 1e nur bis zu einem Betrag von insgesamt zehn Millionen Euro; … 2. im Fall der Sachbeschädigung … nur bis zu einem Betrag von insgesamt einer Million Euro, bei Verursachung des Schadens auf Grund der Verwendung einer hoch- oder vollautomatisierten Fahrfunktion gemäß § 1a oder beim Betrieb einer autonomen Fahrfunktion gemäß § 1e, nur bis zu einem Betrag von insgesamt zwei Millionen Euro.
> 
> **StVG § 63a Abs. 1、3（L3 数据存储与传输）**
> 
> > (1) Kraftfahrzeuge gemäß § 1a speichern die durch ein Satellitennavigationssystem ermittelten Positions- und Zeitangaben, wenn ein Wechsel der Fahrzeugsteuerung zwischen Fahrzeugführer und dem hoch- oder vollautomatisierten System erfolgt. Eine derartige Speicherung erfolgt auch, wenn der Fahrzeugführer durch das System aufgefordert wird, die Fahrzeugsteuerung zu übernehmen oder eine technische Störung des Systems auftritt.
> > (3) Der Fahrzeughalter hat die Übermittlung der gemäß Absatz 1 gespeicherten Daten an Dritte zu veranlassen, wenn 1. die Daten zur Geltendmachung, Befriedigung oder Abwehr von Rechtsansprüchen im Zusammenhang mit einem in § 7 Absatz 1 geregelten Ereignis erforderlich sind und 2. das entsprechende Kraftfahrzeug mit automatisierter Fahrfunktion an diesem Ereignis beteiligt war. …
> 
> **ProdHaftG § 1（责任与免责）**
> 
> > (1) Wird durch den Fehler eines Produkts jemand getötet, sein Körper oder seine Gesundheit verletzt oder eine Sache beschädigt, so ist der Hersteller des Produkts verpflichtet, dem Geschädigten den daraus entstehenden Schaden zu ersetzen. …
> > (2) Die Ersatzpflicht des Herstellers ist ausgeschlossen, wenn 1. er das Produkt nicht in den Verkehr gebracht hat, 2. nach den Umständen davon auszugehen ist, daß das Produkt den Fehler, der den Schaden verursacht hat, noch nicht hatte, als der Hersteller es in den Verkehr brachte, 3. er das Produkt weder für den Verkauf oder eine andere Form des Vertriebs mit wirtschaftlichem Zweck hergestellt noch im Rahmen seiner beruflichen Tätigkeit hergestellt oder vertrieben hat, 4. der Fehler darauf beruht, daß das Produkt in dem Zeitpunkt, in dem der Hersteller es in den Verkehr brachte, dazu zwingenden Rechtsvorschriften entsprochen hat, oder 5. der Fehler nach dem Stand der Wissenschaft und Technik in dem Zeitpunkt, in dem der Hersteller das Produkt in den Verkehr brachte, nicht erkannt werden konnte.
> > (4) Für den Fehler, den Schaden und den ursächlichen Zusammenhang zwischen Fehler und Schaden trägt der Geschädigte die Beweislast. Ist streitig, ob die Ersatzpflicht gemäß Absatz 2 oder 3 ausgeschlossen ist, so trägt der Hersteller die Beweislast.
> 
> **BGB § 823（一般侵权责任）**
> 
> > (1) Wer vorsätzlich oder fahrlässig das Leben, den Körper, die Gesundheit, die Freiheit, das Eigentum oder ein sonstiges Recht eines anderen widerrechtlich verletzt, ist dem anderen zum Ersatz des daraus entstehenden Schadens verpflichtet.
> > (2) Die gleiche Verpflichtung trifft denjenigen, welcher gegen ein den Schutz eines anderen bezweckendes Gesetz verstößt. …
> 
> ---
> 
> ### 附：本报告的已知局限
> 
> 1. 调研环境对 `gesetze-im-internet.de`、`dejure.org`、`bundestag.de/dserver`、`bundesrat.de`、`eur-lex.europa.eu` 等官方站点的直接访问不稳定或受限；本报告因此大量使用 **Wayback Machine 上官方页面的 2024 年快照**，并以 `buzer.de`、`gesetze-in-app.de` 等整合文本交叉核对。少数官方 PDF（BT-Drs. 18/11300 的立法理由、BR-Drs. 155/1/21 全文、BMDV 的法定评估报告）**未能打开**，相关处已标注「未能核实」。
> 2. 2024 年中期之前，德国尚无直接针对 L3/L4 交通事故责任的最高法院判决；本报告对 L3/L4 具体场景的分析，部分建立在条文文义、立法材料与一般交通事故判例的类推之上，已在文中标明。
> 3. 2024 年下半年之后的立法动态（欧盟新产品责任指令 2024/2853、AI Act 的适用时间表、德国后续修法）**不属于本报告基准时点的法律状态**，文中已单独标注，仅供跟踪参考。
> 4. 仍未能核实的点主要包括：（a）AI Liability Directive 提案 COM(2022) 496 的内容与 2024 年中期状态；（b）COM(2022) 495 / Directive (EU) 2024/2853 中举证减轻与证据披露义务的具体条文；（c）欧盟 EDR（事件数据记录器）的强制适用时间表；（d）机器法规 Reg (EU) 2023/1230 的适用时间；（e）德国联邦参议院 BR-Drs. 155/1/21 的完整文本；（f）2024 年中期之前是否存在直接适用 § 1b StVG 的 BGH/OLG 判决（未检索到，但检索范围有限）。
> 5. 本报告为法律信息调研，不构成针对具体案件的法律意见。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 26

**题目**：A Survey of Population-Based Deep Reinforcement Learning（Software Development）

**禁用的来源文章**：A Survey on Population-Based Deep Reinforcement Learning

- https://www.mdpi.com/2227-7390/11/10/2234
- https://ideas.repec.org/a/gam/jmathe/v11y2023i10p2234-d1143662.html
- https://encyclopedia.pub/entry/44828
- https://www.mdpi.com/2227-7390/11/10/2234/reprints

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 2 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 5 条；相同的参考文献 0 条。

相同片段举例：`reinforcement learning weifan long taixian hou xiaoyi wei shichao yan peng zhai`

**这次运行打开过 259 个地址，最多的站点**：arxiv.org 75，ar5iv.labs.arxiv.org 34，export.arxiv.org 24，proceedings.mlr.press 16，api.crossref.org 15，nature.com 8，dblp.org 8，api.semanticscholar.org 8，raw.githubusercontent.com 7，github.com 6，static-content.springer.com 5，proceedings.neurips.cc 5

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 基于群体的深度强化学习（PB-DRL）算法调研报告
    ## ——截至 2023 年初的主要算法与框架比较
    ## 0. 调研范围、方法与合规声明
    ## 1. 五大类别介绍与发展脉络
    ### 1.1 朴素自博弈（Naive Self-Play, Naive SP）
    ### 1.2 虚拟自博弈：博弈论一脉（Fictitious Play 家族）
    ### 1.3 群体博弈（Population Play 一脉）
    ### 1.4 基于演化的方法（Evolutionary / Population-Based Training）
    ### 1.5 通用框架（PSRO 家族）
    ### 1.6 脉络小结
    ## 2. 19 个算法的详细比较表
    ## 3. 关键更正与命名歧义说明
    ### 3.1 命名/记号歧义（本清单特有）
    ### 3.2 事实性更正（二手文献常见错误）
    ## 4. 主要参考文献（按类别）

**报告开头**：

> # 基于群体的深度强化学习（PB-DRL）算法调研报告
> ## ——截至 2023 年初的主要算法与框架比较
> 
> ---
> 
> ## 0. 调研范围、方法与合规声明
> 
> **范围。** 本报告覆盖基于群体的深度强化学习（Population-Based Deep Reinforcement Learning, PB-DRL）
> 中截至 2023 年初的主要算法与框架，具体为以下 19 个条目：
> 
> Naive SP、Fictitious Play、FSP、NFSP、ED、δ-Uniform FSP、Prioritized FSP、PP、FCP、
> Hidden-Utility Self-Play、PBT、MERL、CERL、DERL、PSRO、PSROηN、Diverse PSRO、Pipeline PSRO、α-PSRO。
> 
> **方法。** 调研按 8 个互不重叠的部分并行展开，每部分由独立调研单元完成，均要求以**一手来源**
> （arXiv 预印本、NeurIPS/ICML/ICLR/AAAI/AAMAS/JMLR/PMLR 正式论文、Nature/Science/Nature Communications、
> IEEE Transactions on Games、官方代码仓库）为主要依据，并明确区分「已核实的来源事实」与「推断」。
> 汇总阶段由报告作者交叉核对命名歧义条目，并对若干流行但错误的转述做了更正（见 §3）。
> 
> **命名歧义处理原则。** 本清单中若干缩写在不同文献中并不唯一。凡遇此类情况，本报告：给出最有可能的
> 规范来源并附证据；同时**显式标注不确定性**，绝不臆造引用。具体涉及 `PSROηN`、`DERL`、
> `Diverse PSRO`、`Hidden-Utility Self-Play`、`PP`、`δ-Uniform FSP`。
> 
> **合规声明。** 本调研全程**未打开、未抓取、未阅读、未引用**《A Survey on Population-Based Deep
> Reinforcement Learning》（Weifan Long, Taixian Hou, Xiaoyi Wei, Shichao Yan, Peng Zhai, Lihua Zhang）
> 一文及其下列网址，亦未使用其任何转载页、摘要页或镜像页：
> 
> - MDPI *Mathematics* 期刊上该文的正式页面与其 reprints 页面；
> - ideas.repec.org 上该文的索引页；
> - encyclopedia.pub 上该文的条目页。
> 
> （为避免复述被禁止来源的链接，此处不逐一罗列其完整 URL。）
> 
> 所有结论均来自上述一手来源或其他独立文献。检索过程中若出现指向该文的链接（含 `encyclopedia.pub`
> 及该刊域名上的相关条目/镜像/下载页），一律跳过、未予打开，也未在 §4 参考文献中列出该文。
> 
> ---
> 
> ## 1. 五大类别介绍与发展脉络
> 
> PB-DRL 要回答的核心问题是：**在对手（或合作者）策略不断变化时，一个智能体应当"跟谁学"，以及"学什么目标"**。
> 下表的 19 个算法可按"训练信号/对手分布的来源"归为五类。这五类并非简单并列，而是一条逐步演化的脉络：
> 从"只跟最新的自己打"，到"跟历史平均打"，到"跟一个显式维护的群体打"，再到"用进化算子维持多样性"，
> 最终收敛为"用元求解器 + 最优反应 oracle 主动构造群体"的统一框架。
> 
> ### 1.1 朴素自博弈（Naive Self-Play, Naive SP）
> 

**报告结尾（含参考文献）**：

> - J. Heinrich, D. Silver, "Deep Reinforcement Learning from Self-Play in Imperfect-Information Games," arXiv:1603.01121, 2016.
> - M. Lanctot et al., "OpenSpiel: A Framework for Reinforcement Learning in Games," arXiv:1908.09453, 2019.
> - E. Lockhart, M. Lanctot, J. Pérolat, J.-B. Lespiau, D. Morrill, F. Timbers, K. Tuyls, "Computing Approximate Equilibria in Sequential Adversarial Games by Exploitability Descent," IJCAI 2019, pp. 464–470；扩展版 arXiv:1903.05614 v4.
> - O. Vinyals et al., "Grandmaster level in StarCraft II using multi-agent reinforcement learning," *Nature* 575:350–354, 2019.
> - D. Hernandez, K. Denamganaï, S. Devlin, S. Samothrakis, J. A. Walker, "A Comparison of Self-Play Algorithms Under a Generalized Framework," *IEEE Trans. Games* 14(2), 2022, arXiv:2006.04471.
> - C. Berner et al. (OpenAI), "Dota 2 with Large Scale Deep Reinforcement Learning," arXiv:1912.06680, 2019.
> - F. Lin et al., "TiZero: Mastering Multi-Agent Football with Curriculum Learning and Self-Play," AAMAS 2023, arXiv:2302.07515.
> 
> **群体博弈与零样本协作**
> - DJ Strouse, K. R. McKee, M. Botvinick, E. Hughes, R. Everett, "Collaborating with Humans without Human Data," NeurIPS 2021, arXiv:2110.08176.
> - M. Carroll et al., "On the Utility of Learning about Humans for Human-AI Coordination," NeurIPS 2019, arXiv:1910.05789.
> - C. Yu, J. Gao, W. Liu, B. Xu, H. Tang, J. Yang, Y. Wang, Y. Wu, "Learning Zero-Shot Cooperation with Humans, Assuming Humans Are Biased" (HSP), ICLR 2023, arXiv:2302.01605.
> - R. Zhao et al., "Maximum Entropy Population-Based Training for Zero-Shot Human-AI Coordination" (MEP), AAAI 2023, arXiv:2112.11701.
> - X. Lou et al., "PECAN: Leveraging Policy Ensemble for Context-Aware Zero-Shot Human-AI Coordination," AAMAS 2023, arXiv:2301.06387.
> - H. Hu, A. Lerer, A. Peysakhovich, J. Foerster, "'Other-Play' for Zero-Shot Coordination," ICML 2020, arXiv:2003.02979.
> 
> **演化与群体训练**
> - M. Jaderberg et al., "Population Based Training of Neural Networks," arXiv:1711.09846, 2017.
> - M. Jaderberg et al., "Human-level performance in 3D multiplayer games with population-based reinforcement learning," *Science* 364(6443):859–865, 2019.
> - S. Khadka, K. Tumer, "Evolution-Guided Policy Gradient in Reinforcement Learning" (ERL), NeurIPS 2018, arXiv:1805.07917.
> - S. Khadka et al., "Collaborative Evolutionary Reinforcement Learning" (CERL), ICML 2019, PMLR 97:3341–3350, arXiv:1905.00976.
> - S. Majumdar, S. Khadka, S. Miret, S. McAleer, K. Tumer, "Evolutionary Reinforcement Learning for Sample-Efficient Multiagent Coordination" (MERL), ICML 2020, PMLR 119；arXiv:1906.07315.
> - C. Bodnar, B. Day, P. Lió, "Proximal Distilled Evolutionary Reinforcement Learning" (PDERL), AAAI 2020, arXiv:1906.09807.
> - A. Gupta, S. Savarese, S. Ganguli, L. Fei-Fei, "Embodied intelligence via learning and evolution" (DERL), *Nature Communications* 12:5721, 2021, arXiv:2102.02202.
> - H. Bai, R. Cheng, Y. Jin, "Evolutionary Reinforcement Learning: A Survey," arXiv:2303.04150, 2023.
> 
> **PSRO 家族**
> - M. Lanctot et al., "A Unified Game-Theoretic Approach to Multiagent Reinforcement Learning" (PSRO), NIPS 2017, arXiv:1711.00832.
> - D. Balduzzi et al., "Open-ended Learning in Symmetric Zero-sum Games" (PSRO_rN), ICML 2019, PMLR 97:434–443, arXiv:1901.08106.
> - N. Perez-Nieves, Y. Yang, O. Slumbers, D. H. Mguni, Y. Wen, J. Wang, "Modelling Behavioural Diversity for Learning in Open-Ended Games" (Diverse PSRO / DPP-PSRO), ICML 2021, PMLR 139:8514–8524, arXiv:2103.07927.
> - X. Liu et al., "Towards Unifying Behavioral and Response Diversity for Open-ended Learning in Zero-sum Games," NeurIPS 2021, arXiv:2106.04958.
> - S. McAleer, J. Lanier, R. Fox, P. Baldi, "Pipeline PSRO: A Scalable Approach for Finding Approximate Nash Equilibria in Large Games," NeurIPS 2020, arXiv:2006.08555.
> - P. Muller et al., "A Generalized Training Approach for Multiagent Learning" (α-PSRO), ICLR 2020, arXiv:1909.12823.
> - S. Omidshafiei et al., "α-Rank: Multi-Agent Evaluation by Evolution," *Scientific Reports* 9:9937, 2019, arXiv:1903.01373.
> - H. B. McMahan, G. J. Gordon, A. Blum, "Planning in the Presence of Cost Functions Controlled by an Adversary," ICML 2003（Double Oracle 源头）.

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 27

**题目**：Legal Research on Traffic Accident Liability for German Autonomous Vehicles（Crime & Law）

**禁用的来源文章**：Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China

- https://www.mdpi.com/2032-6653/15/7/305
- https://www.mdpi.com/2032-6653/15/7/305/pdf
- https://www.mdpi.com/2032-6653/15/7/305/html
- https://www.mdpi.com/2032-6653/15/7/305/xml
- https://www.researchgate.net/publication/382225455_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_of_the_German_Legislation_for_China
- https://www.researchgate.net/publication/382400472_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_from_the_German_Legislation_for_China/download

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 200 个地址，最多的站点**：buzer.de 55，publications.europa.eu 20，gesetze-im-internet.de 12，eur-lex.europa.eu 10，gesetze-im-internet.juris.de 8，rewis.io 5，dejure.org 4，umwelt-online.de 4，pubaffairsbruxelles.eu 4，unece.org 3，europarl.europa.eu 3，commission.europa.eu 3

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 德国 L3 级及以上自动驾驶汽车交通事故责任划分研究报告
    ## 摘要（结论速览）
    ## 一、导论：德国法的规范框架
    ### 1.1 自动化等级的德国法映射
    ### 1.2 两次关键修法及其在 2024 年中期的效力状态
    ### 1.3 责任体系的总体结构
    ## 二、驾驶员（Fahrzeugführer）的责任
    ### 2.1 谁是"驾驶员"？——§ 1a Abs. 4 StVG 的拟制
    ### 2.2 法律依据与责任类型：过错责任 + 法定的过错推定
    ### 2.3 驾驶员在自动化运行期间的义务：§ 1b StVG
    ### 2.4 诉讼中的举证责任：受害人证明什么？驾驶员如何免责？
    ### 2.5 过错标准与"合规使用"的互动
    ### 2.6 L4 车辆（§ 1d StVG）的"技术监督"责任
    ## 三、车辆持有人（Halter）的责任
    ### 3.1 法律依据与责任类型：无过错责任（Gefährdungshaftung）
    ### 3.2 与驾驶员责任的区别
    ### 3.3 免责事由：仅限"不可抗力"（höhere Gewalt）
    ### 3.4 举证责任
    ### 3.5 自动驾驶场景下持有人的附加义务
    ### 3.6 责任限额、强制保险与受害人的直接请求权
    ## 四、生产者责任（Produzentenhaftung）与制造商产品责任（Produkthaftung）
    ### 4.1 概念澄清：不是"两个主体"，而是"两套责任制度"
    ### 4.2 生产者侵权责任（Produzentenhaftung）——§ 823 BGB
    ### 4.3 制造商产品责任（Produkthaftung）——ProdHaftG
    ### 4.4 两种责任的系统对比
    ### 4.5 在自动驾驶场景中的具体适用
    ## 五、证据与数据：自动驾驶事故中的关键问题
    ### 5.1 L3 车辆：§ 63a StVG（2017 年引入）
    ### 5.2 L4 车辆：§ 1g StVG（2021 年引入）
    ### 5.3 对举证责任的实际影响
    ## 六、欧盟层面的相关发展（截至 2024 年中期）
    ### 6.1 《人工智能法》（AI Act）：Regulation (EU) 2024/1689
    ### 6.2 新《产品责任指令》：Directive (EU) 2024/2853
    ### 6.3 机动车强制保险指令与型式批准框架
    ### 6.4 UN Regulation No. 157（ALKS）与 L3 的实际落地
    ## 七、结论与实务要点
    ### 7.1 对三个问题的直接回答
    ### 7.2 德国模式的三个特征
    ### 7.3 受害人的实务路径（德国法下）
    ## 八、主要来源

**报告开头**：

> # 德国 L3 级及以上自动驾驶汽车交通事故责任划分研究报告
> 
> **信息截止：2024 年中期**（对 2024 年下半年之后的立法动态，报告仅在末尾以"截止日之后的动态"单独标注，不计入正文结论）
> 
> **术语约定**：本报告中的德文法律术语首次出现时以「德文（中文）」形式标注；条文引用一律采用德国《道路交通法》（Straßenverkehrsgesetz, **StVG**）、《民法典》（Bürgerliches Gesetzbuch, **BGB**）、《产品责任法》（Produkthaftungsgesetz, **ProdHaftG**）、《强制保险法》（Pflichtversicherungsgesetz, **PflVG**）、《保险合同法》（Versicherungsvertragsgesetz, **VVG**）以及《自动驾驶汽车许可与运营条例》（Autonome-Fahrzeuge-Genehmigungs-und-Betriebs-Verordnung, **AFGBV**）。
> 
> ---
> 
> ## 摘要（结论速览）
> 
> 德国法对自动驾驶事故责任的处理，不是"另起炉灶"制定一部特别侵权法，而是**在既有的三层责任体系上做增量调整**，并通过"数据存储／调取义务"来缓解受害人的举证困难。三层体系及其在自动驾驶场景下的分工如下：
> 
> | 角色 | 请求权基础 | 责任类型 | 归责原则 | 免责／抗辩 | 举证责任的核心分配 |
> |---|---|---|---|---|---|
> | **驾驶员**（Fahrzeugführer） | § 18 Abs. 1 StVG；并行：§ 823 Abs. 1、Abs. 2 BGB | **过错责任**（Verschuldenshaftung） | 以过错（故意／过失）为要件，但**法律推定其有过错** | 证明自己"完全合乎交通规则地行为"（verkehrsgerechtes Verhalten），即证明损害非因其过错所致 | 受害人证明"机动车运行—损害—因果关系"等客观要件；**驾驶员承担无过错的证明责任**（通说：过错推定／举证责任倒置） |
> | **车辆持有人**（Halter） | § 7 Abs. 1 StVG | **无过错责任**（Gefährdungshaftung，危险责任） | **不以过错为要件** | **仅**"不可抗力"（höhere Gewalt，§ 7 Abs. 2 StVG） | 受害人证明"机动车运行—损害—因果关系"；**持有人承担不可抗力的证明责任**。技术缺陷**不构成**不可抗力 |
> | **生产者／制造商**（Hersteller） | 两条并行轨道：<br>① **生产者侵权责任**（Produzentenhaftung）：§ 823 Abs. 1 BGB（＋§ 823 Abs. 2、§ 831、§ 840 BGB）<br>② **制造商产品责任**（Produkthaftung）：ProdHaftG §§ 1 ff. | ① 过错责任（但举证责任被司法倒置）<br>② **无过错责任** | ① 以违反产品相关交往安全义务（Verkehrspflicht）＋过错为要件，但**过错与客观义务违反的举证责任均由制造商承担**<br>② 以"产品缺陷"为独立要件，**完全不以过错为要件** | ① 证明已尽必要且可期待的全部注意<br>② 仅限 ProdHaftG § 1 Abs. 2、Abs. 3 的封闭抗辩清单（含"发展风险"抗辩） | ① 受害人

**报告结尾（含参考文献）**：

> 
> **欧盟法**
> 
> - **Directive (EU) 2024/2853**（新《产品责任指令》，2024 年 10 月 23 日，OJ L, 2024/2853, 2024 年 11 月 18 日）：https://eur-lex.europa.eu/eli/dir/2024/2853/oj ｜提案 COM(2022) 495：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52022PC0495 ｜欧洲议会一读决议 P9_TA(2024)0132：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52024AP0132
> - 旧《产品责任指令》**85/374/EEC**：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:31985L0374
> - **Regulation (EU) 2024/1689**（AI Act，2024 年 7 月 12 日，OJ L, 2024/1689）：https://eur-lex.europa.eu/eli/reg/2024/1689/oj
> - **COM(2022) 496**（《AI 责任指令》提案）：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52022PC0496 ｜撤回：Commission Work Programme 2025, COM(2025) 45 final, Annex IV
> - **Regulation (EU) 2019/2144**（《通用安全条例》）：https://eur-lex.europa.eu/eli/reg/2019/2144/oj ｜**Delegated Regulation (EU) 2022/1398**（UN R157 强制适用）：https://eur-lex.europa.eu/eli/reg_del/2022/1398/oj
> - **Implementing Regulation (EU) 2022/1426**（全自动车辆 ADS 型式批准）：https://eur-lex.europa.eu/eli/reg_impl/2022/1426/oj ｜**Delegated Regulation (EU) 2022/2236**（小系列全自动车辆整车批准）：https://eur-lex.europa.eu/eli/reg_del/2022/2236/oj
> - **UN Regulation No. 157**（OJ L 82, 9.3.2021, p. 75；CELEX 42021X0389）：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:42021X0389
> - **Directive 2009/103/EC**（机动车强制保险指令）：https://eur-lex.europa.eu/eli/dir/2009/103/oj ｜**Directive (EU) 2021/2118**（修改指令）：https://eur-lex.europa.eu/eli/dir/2021/2118/oj
> - **COM(2018) 283 final**（自动化出行战略）：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52018DC0283 ｜**COM(2020) 64 final**（AI、IoT 与机器人对安全与责任影响的报告）：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52020DC0064 ｜**COM(2018) 246 final**（产品责任指令适用报告）：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52018DC0246
> - 欧洲议会 2020 年 10 月 20 日关于 AI 民事责任制度的决议（2020/2014(INL)）：https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52020IP0276
> 
> **欧盟法评注（用于核验时间线与条文结构）**
> 
> - Bird & Bird, *Update: Reform of product liability adopted*（2024 年 11 月 19 日，含新旧指令逐项对照表）：https://www.twobirds.com/en/insights/2024/germany/update-reform-der-produkthaftung-beschlossen
> - Bird & Bird, *Has the Revised Product Liability Directive reversed the Burden of proof?*（2025 年 6 月 24 日，第 10 条三层推定）：https://www.twobirds.com/en/insights/2025/spain/has-the-revised-product-liability-directive-reversed-the-burden-of-proof-placing-it-onto-producers-t
> - AI Act 附件 I 全文（Section B 第 (18)、(19) 项）：https://artificialintelligenceact.com/annex-i-section-b-list-of-other-union-harmonisation-legislation/
> 
> ---
> 
> ## 九、截止日之后的动态（仅作提示，不计入正文结论）
> 
> 以下事项发生在 **2024 年中期之后**，供后续更新参考：
> 
> 1. **2024 年 9 月 17 日／10 月 10 日／10 月 23 日**：欧盟新《产品责任指令》(EU) 2024/2853 依次经新一届欧洲议会批准（9 月 17 日）、理事会正式通过（10 月 10 日）、落款（10 月 23 日）；**2024 年 11 月 18 日**公布于《官方公报》；**2024 年 12 月 8 日**生效；转化期限 **2026 年 12 月 9 日**。德国须相应修改 ProdHaftG。
> 2. **2024 年 12 月 17 日**：KBA 批准 Mercedes-Benz DRIVE PILOT 的 **95 km/h** 版本，适用于德国全部 13,191 公里高速公路网。
> 3. **2025 年 2 月 11 日**：欧盟委员会在《2025 年工作计划》（COM(2025) 45 final）**附件 IV"撤回"清单**中列入《AI 责任指令》提案 **COM(2022) 496**，理由为"**无可预见的一致意见**"，并计划在六个月内正式撤回；该提案于 2025 年内被正式放弃。这意味着欧盟层面针对**过错责任**下 AI 索赔的**证据披露与过错／因果关系推定**规则出现空缺，短期内该功能由新《产品责任指令》第 9、10 条承担。
> 4. **2025 年 7 月 16 日**：德国《道路交通远程操控条例》（StVFernLV，BGBl. 2025 I Nr. 176）颁布，明确不影响 StVG §§ 1a–1k。
> 5. **2026 年 5 月 12 日**：德国《第五次 StVG 修订法》（BGBl. 2026 I Nr. 142，2026 年 7 月 1 日生效）将 §§ 1a、1b、12、63a StVG 中的"hoch- oder vollautomatisiert"统一改为"automatisiert"，并在 § 1e Abs. 1 Nr. 2 中补充对欧盟／外国型式批准的援引。**条文编号未变。**
> 
> ---
> 
> *本报告基于截至 2024 年中期公开可查的德国成文法、判例与欧盟立法文件整理。报告未使用、未引用、未查阅任何被明确排除的文献。*

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 28

**题目**：The development of urban rail transit in mainland China from 2015 to 2023（Transportation）

**禁用的来源文章**：Urban Rail Transit in China: Progress Report and Analysis (2015–2023)

- https://link.springer.com/article/10.1007/s40864-024-00231-7
- https://journal.hep.com.cn/urt/EN/10.1007/s40864-024-00231-7
- https://www.researchgate.net/publication/386163277_Urban_Rail_Transit_in_China_Progress_Report_and_Analysis_2015-2023
- https://ira.lib.polyu.edu.hk/bitstream/10397/112952/1/s40864-024-00231-7.pdf
- https://www.scilit.com/publications/e905a6e69bebdba754a750664efa88c1
- https://trid.trb.org/View/2521815

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里出现了来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 260 个地址，最多的站点**：camet.org.cn 39，infosharingp2-oss.camet.org.cn 33，dskgjt.ijournals.cn 18，rail.ally.net.cn 13，163.com 11，castjournals.cast.org.cn 10，lhratings.com 10，chinanews.com.cn 8，sohu.com 7，chinametro.net 7，mp.weixin.qq.com 5，chinautc.com 5

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 2015—2023年中国内地城市轨道交通发展调研报告
    ## 摘要
    ## 数据口径与阅读说明（重要）
    ## 一、整体发展规模
    ### 1.1 开通运营城市数量与运营线路总长度（2015—2023年）
    ### 1.2 在建线路总里程（2015—2022年）
    ## 二、主要城市运营里程（2015—2023年）
    ### 2.1 主表：CAMET口径（全制式运营线路长度，公里，年末累计）
    ### 2.2 对照表一：同一报告的"其中：地铁"口径（公里）
    ### 2.3 对照表二：交通运输部年度运营数据速报口径（公里）
    ### 2.4 口径说明（为何同一城市会出现多个里程数）
    ## 三、城轨系统制式构成（截至2023年底）
    ## 四、服务效率分析
    ### 4.1 全国城轨网络日均客运强度变化趋势（2015—2022年）
    ### 4.2 五城2019年与2022年客运效率对比
    ### 4.3 2019年后全国平均客运强度下降的主要原因
    ## 五、主要结论
    ## 附录A：主要数据来源
    ## 附录B：数据局限性说明

**报告开头**：

> # 2015—2023年中国内地城市轨道交通发展调研报告
> 
> **报告范围**：中国内地（不含港澳台）城市轨道交通（以下简称"城轨交通"）
> **主要数据源**：中国城市轨道交通协会（CAMET）《城市轨道交通XXXX年度统计和分析报告》（2015—2023年，共9份官方报告原文）；辅以《都市快轨交通》期刊、交通运输部运营数据速报
> **编制日期**：2026年
> 
> ---
> 
> ## 摘要
> 
> 2015—2023年是中国内地城轨交通从"单线运营"走向"网络化运营"的关键八年。
> 
> - **规模**：开通运营城市由26个增至59个，运营线路总长度由3618公里增至11224.54公里，八年间增长210.2%，年均复合增长率约15.2%。2022年底运营里程首破1万公里。
> - **建设**：在建线路总里程由2015年的4448公里升至2019年峰值6902.5公里，此后回落至2022年的6350.55公里、2023年的5671.65公里，"建设高峰已过、进入平稳期"特征明显。
> - **结构**：截至2023年底，10种系统制式同时在运营，地铁8543.11公里（占76.11%），市域快轨1454.86公里（占12.96%）为第二大制式。
> - **效率**：全国平均客运强度由2016年的0.83万人次/公里日降至2019年的0.71、2020年的0.45、2022年的0.38；2023年随疫情结束回升至0.55，客运量创历史新高（294.66亿人次）。客运强度下降是"疫情冲击"与"网络快速扩张摊薄"共同作用的结果，后者是长期性、结构性的。
> 
> ---
> 
> ## 数据口径与阅读说明（重要）
> 
> 城轨交通统计数据存在多套口径，若不加以区分会造成误读。本报告的处理原则如下：
> 
> | 口径 | 典型数值（2023年底） | 说明 |
> |---|---|---|
> | **CAMET年度报告（本报告主口径）** | 59城、338条、**11224.54公里** | 全制式统计，含地铁、轻轨、单轨、市域快轨、有轨电车、磁浮、APM、智轨、胶轮、悬挂式单轨；含试运营线路及部分地方政府批复项目 |
> | CAMET"快报"数（每月/年初发布） | 与年报略有出入（如2020年底快报7978.19 vs 年报7969.7公里） | 协会内部两套数据，年度报告为终稿 |
> | 《都市快轨交通》期刊口径 | 59城、338条、**11232.65公里** | 与CAMET年报相差8.11公里（仅地铁、市域快轨、有轨电车三项不同） |
> | **交通运输部运营数据速报** | 55城、306条、**10165.7公里** | 按城市客运企业上报口径，不含部分制式及试运营线路，数值显著偏小 |
> 
> 其他说明：
> 1. **制式分类标准**：采用CAMET团体标准《城市轨道交通分类》（T/CAMET 00001—2020），将城轨交通分为**10类**（地铁、轻轨、市域快轨、磁浮交通、跨座式单轨、悬挂式单轨、自导向轨道系统、有轨电车、导轨式胶轮系统、电子导向胶轮系统）。
> 2. **"在建"有两套口径**：本报告"在建线路总里程"指**已开工在建线路总长**，不同于"在实施的建设规划线路总长"（后者不含已开通运营线路，如2019年为7339.4公里）。两者不可混用。
> 3. **客运强度口径**：CAMET公布的"全国平均客运强度"是**各城市客运强度的算术平均**（非按里程加权）。经逐城市数值核算，2019年40城均值0.706、2021年47城均值0.490、2022年47城均值0.383，与官方公布的0.71

**报告结尾（含参考文献）**：

> 
> ## 附录A：主要数据来源
> 
> **中国城市轨道交通协会（CAMET）年度统计和分析报告（本报告主数据源，均下载原文核对）：**
> 
> | 年份 | 协会文章页 | 报告PDF原文 |
> |---|---|---|
> | 2015 | [3103.shtml](https://www.camet.org.cn/xytj/tjxx/3103.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202206/15160551jqjn.pdf) |
> | 2016 | [3102.shtml](https://www.camet.org.cn/xytj/tjxx/3102.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202206/151603194hru.pdf) |
> | 2017 | [4513.shtml](https://www.camet.org.cn/xytj/tjxx/4513.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202206/1516010190cl.pdf) |
> | 2018 | [3101.shtml](https://www.camet.org.cn/xytj/tjxx/3101.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202206/15155806ka9f.pdf) |
> | 2019 | [5133.shtml](https://www.camet.org.cn/xytj/tjxx/5133.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202206/15155455y8f6.pdf) |
> | 2020 | [7647.shtml](https://www.camet.org.cn/xytj/tjxx/7647.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202206/15152611wudg.pdf) |
> | 2021 | [9944.shtml](https://www.camet.org.cn/xytj/tjxx/9944.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202204/22173707u9ay.pdf) |
> | 2022 | [11944.shtml](https://www.camet.org.cn/xytj/tjxx/11944.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202304/07144043slcg.pdf) |
> | 2023 | [14894.shtml](https://www.camet.org.cn/xytj/tjxx/14894.shtml) | [PDF](https://infosharingp2-oss.camet.org.cn/u/cms/www/202403/28125736mgzp.pdf) |
> 
> 协会统计报告栏目总入口：[统计报告](https://www.camet.org.cn/xytj/tjxx/index.shtml)
> 
> **其他来源：**
> - 侯秀芳，冯晨，燕汉民，左超. 2023年中国内地城市轨道交通运营线路概况[J]. 都市快轨交通，2024，37(1)：10-16. [PDF](https://castjournals.cast.org.cn/joweb/dskgjt/CN/PDF/10.3969/j.issn.1672-6073.2024.01.002)
> - 交通运输部《城市轨道交通运营数据速报》及第一财经报道 [中新网转载](https://www.chinanews.com.cn/cj/2024/01-17/10147587.shtml)
> - 第一财经《城市轨交大数据：广州西安为何最拥挤？》 [澎湃新闻](https://www.thepaper.cn/newsDetail_forward_7441652)
> - 西部城事《盘点 | 34城地铁拥挤度排行：广州第一，西安第二》 [搜狐](https://www.sohu.com/a/251036388_365037)（转引CAMET 2017年度报告）
> - 联合资信《城市轨道交通行业评级报告》（2021、2022、2023年） [2023年报告](https://www.lhratings.com/reports/B2807-P07963-2016-GZ2023.pdf)｜[2022年报告](https://www.lhratings.com/reports/B0594-P64497-2022.pdf)
> - 环球网《城市轨道交通二〇一八年度统计和分析报告发布》 [百家号](https://baijiahao.baidu.com/s?id=1630395080576538632)
> - 工信部《中国内地投运城轨交通线路近8000公里》 [miit.gov.cn](https://www.miit.gov.cn/xwdt/gxdt/sjdt/art/2021/art_3e7df00050db4fa8aa50d9f4f900c7e8.html)
> 
> ## 附录B：数据局限性说明
> 
> 1. **存在多套官方口径**，本报告已尽量并列呈现并标明出处，但不同口径之间的数值不可直接加减或比较。
> 2. **部分年份数据为整数**（如2015年各城市里程），精度低于后续年份。
> 3. **2015年的客运强度1.21与其他年份不可比**，原因见"数据口径与阅读说明"第4条。
> 4. **2016—2018年CAMET未公布全国口径的"日均客运总量"**，仅公布"全国城市平均日均客运量"（158.1、175.0、177.7万人次，为各城市日均的算术平均），本表相关单元格留空。
> 5. **CAMET网站的2015—2018年条目标题与PDF内容存在整体错位一年**的现象，本报告附录A中的PDF链接为经内容核对后的真实年度报告。

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 29

**题目**：A Review of the Application of Artificial Intelligence (AI) in Government Decision-Making（Finance & Business）

**禁用的来源文章**：Navigating Governmental Choices: A Comprehensive Review of Artificial Intelligence's Impact on Decision-Making

- https://www.mdpi.com/2227-9709/11/3/64
- https://doi.org/10.3390/informatics11030064
- https://text2fa.ir/wp-content/uploads/Text2fa.ir-Navigating-Governmental-Choices-A-Comprehensive-R.pdf
- https://pure.ups.edu.ec/en/publications/navigating-governmental-choices-a-comprehensive-review-of-artific
- https://www.semanticscholar.org/paper/Navigating-Governmental-Choices%3A-A-Comprehensive-of-Caiza-Sangu%C3%B1a/ef838c9723caeba6042168ec17c02358b5a50721
- https://ouci.dntb.gov.ua/en/works/lxdPJKEl/

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 278 个地址，最多的站点**：en.wikipedia.org 17，oecd.ai 11，europarl.europa.eu 11，digital-strategy.ec.europa.eu 10，federalregister.gov 10，chinalawtranslate.com 8，gao.gov 7，nao.org.uk 6，digichina.stanford.edu 6，nist.gov 5，oecd.org 4，eur-lex.europa.eu 4

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 人工智能在政府决策中的应用：2019—2023 年综合综述
    ## 执行摘要
    ## 引言：范围、方法与分析框架
    ### 研究问题
    ### 时间与地理范围
    ### 方法
    ### 分析框架
    ## 第一章 人工智能在政府运作中的作用
    ### 1.1 总览：AI 进入公共管理的三条路径
    ### 1.2 数据处理：从信息过载到异常发现
    #### 1.2.1 税务与福利欺诈检测
    #### 1.2.2 公共采购与反腐中的异常检测
    #### 1.2.3 文件处理、知识管理与档案数字化
    #### 1.2.4 地理空间分析与城市治理
    ### 1.3 服务供给：聊天机器人、数字身份与自动化福利
    #### 1.3.1 公共服务聊天机器人与虚拟助手
    #### 1.3.2 数字身份与"默认数字化"的政府
    #### 1.3.3 医疗、教育与城市服务的行政智能化
    #### 1.3.4 算法透明度基础设施：登记册与影响评估（2020—2022）
    ### 1.4 政策制定与决策支持
    #### 1.4.1 证据型政策：从回顾到前瞻
    #### 1.4.2 危机管理中的 AI
    #### 1.4.3 决策支持 vs. 决策自动化
    ### 1.5 三类代表性应用深度案例
    #### 1.5.1 案例一：公共服务聊天机器人
    #### 1.5.2 案例二：安防与执法中的人脸识别
    ##### (1) Clearview AI：本时期最具争议的私营基础设施
    ##### (2) 监管反制：从城市禁令到欧盟决议
    ##### (3) 美国联邦政府的使用与准确性差异
    ##### (4) 其他辖区的扩散与治理缺陷
    #### 1.5.3 案例三：公共交通中的自动驾驶
    ##### (1) 美国的监管建设与旧金山的"压力测试"
    ##### (2) 其他辖区的进展
    ### 1.6 成效评估：收益、证据与"试点困境"
    #### 已较为确证的收益
    #### 证据的薄弱之处（本报告最重要的方法学结论）
    #### 一个整合性判断
    ## 第二章 政府中人工智能的监管框架：欧盟、美国与中国的比较
    ### 2.0 比较的基准问题
    ### 2.1 欧盟：以基本权利为基础的风险分级统一立法

**报告开头**：

> # 人工智能在政府决策中的应用：2019—2023 年综合综述
> 
> **报告类型**：政策与文献综合综述（Comprehensive Review）
> **时间范围**：2019—2023 年（重点），必要处回溯至 2017 年、延伸至 2024 年初
> **覆盖地区**：全球视野，重点比较欧盟、美国与中国；案例覆盖新加坡、英国、爱沙尼亚、拉脱维亚、奥地利、澳大利亚、荷兰、丹麦、印度、日本、巴西等
> **编制日期**：2024 年
> 
> ---
> 
> ## 执行摘要
> 
> 过去五年（2019—2023），人工智能（AI）从政府改革的"前沿议题"转变为公共行政的常规工具。这一转变呈现三个并行趋势：
> 
> **第一，应用层面从实验走向规模化，但仍处于"试点困境"之中。** AI 已被广泛嵌入政府的数据处理、服务供给与政策制定环节：新加坡的 Ask Jamie 自 2014 年起已帮助公民浏览 70 个政府网站；维也纳 WienBot 到 2019 年 10 月累计回答逾 40 万次咨询；爱沙尼亚 Bürokratt 自 2023 年 6 月起可从国家云以每 30 天 150.48 欧元订购。英国国家审计署（NAO）2024 年的调查显示，70% 的受访政府机构正在试点或规划 AI 应用场景，但 AI **尚未被广泛部署**，中央层面亦缺乏最终确定的战略。美国政府问责局（GAO）2023 年 12 月发现联邦机构**已识别约 1,200 个 AI 用例，但实际实施的寥寥无几**；在 GAO 持续跟踪的 11 个机构中，有记录的用例从 2023 年的 **571 个增至 2024 年的 1,110 个**，其中 **61% 属于"任务支撑型"内部行政支持**，而非直接面向公民的决策。**"清单规模"与"实际部署"之间的落差，是本时期最稳定的经验发现**（见第一章）。
> 
> **第二，监管层面形成三种截然不同的模式。** 欧盟选择"统一立法 + 风险分级"路径，以《人工智能法案》（AI Act，2021 年提案、2023 年 12 月达成政治协议）为核心，按不可接受、高、有限、极小四级风险配置义务；美国选择"市场主导 + 部门分散 + 自愿标准"路径，以行政命令（EO 13859、EO 13960、EO 14110）、OMB 备忘录和 NIST《AI 风险管理框架》（2023 年 1 月）为主要工具，至今没有综合性 AI 成文法；中国选择"国家主导 + 敏捷迭代 + 安全与发展并重"路径，针对算法推荐（2022）、深度合成（2023）、生成式 AI（2023）逐项出台专门规章，并建立算法备案制度。三者的分歧不仅是法律技术的分歧，更是对"谁来决定 AI 的边界"这一政治问题的不同回答（见第二章）。
> 
> **第三，挑战层面呈现"技术—社会—伦理"三层叠加结构。** 技术层面，遗留系统、数据质量、人才短缺与"最后一公里"规模化障碍构成主要瓶颈；社会层面，岗位替代焦虑、公众信任赤字与数字鸿沟限制采纳；伦理层面，"黑箱"、算法偏见与问责真空构成最尖锐的合法性质疑。澳大利亚 Robodebt 计划（**约 47 万笔错误债务、18 亿澳元和解、2023 年皇家委员会认定其为"代价高昂的失败"**）、荷兰 SyRI 风险画像系统（2020 年 2 月被海牙地方法院裁定违反《欧洲人权公约》第 8 条）与儿童福利金丑闻（导致内阁于 2021 年 1 月集体辞职）、英国 2020 年 A-Level 评分算法事件、美国密歇根州 MiDAS（2,000 万美元和解），以及**至少 7 起已确认的人脸识别误捕

**报告结尾（含参考文献）**：

> 
> **技术、社会与伦理挑战的专门文献**
> 
> - US Government Accountability Office, *Information Technology: Agencies Need to Develop Modernization Plans for Critical Legacy Systems*, GAO-19-471, June 2019. https://www.gao.gov/products/gao-19-471
> - US Government Accountability Office, *Testimony Before the Subcommittee on Emerging Threats and Spending Oversight* (legacy systems), GAO-21-524T. https://www.gaotest.org/assets/gao-21-524t.pdf
> - UK National Audit Office, *Challenges in Using Data Across Government*, 21 June 2019. https://www.nao.org.uk/insights/challenges-in-using-data-across-government/
> - UK National Audit Office, *Digital Transformation in Government: Addressing the Barriers to Efficiency*, 10 March 2023. https://www.nao.org.uk/reports/digital-transformation-in-government-addressing-the-barriers/
> - Government of Canada, Treasury Board of Canada Secretariat, *Directive on Automated Decision-Making* (2019) and *Guide to Peer Review of Automated Decision Systems*. https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592
> - Ada Lovelace Institute & DataKind UK, *Examining the Black Box: Tools for Assessing Algorithmic Systems*, 29 April 2020. https://www.adalovelaceinstitute.org/report/examining-the-black-box-tools-for-assessing-algorithmic-systems/
> - Ada Lovelace Institute, AI Now Institute & Open Government Partnership, *Algorithmic Accountability for the Public Sector: Learning From the First Wave of Policy Implementation*, 24 August 2021. https://www.adalovelaceinstitute.org/report/algorithmic-accountability-public-sector/
> - Brent Mittelstadt, "Principles Alone Cannot Guarantee Ethical AI," *Nature Machine Intelligence* 1, 501–507 (2019); arXiv:1906.06668. https://arxiv.org/abs/1906.06668
> - Ziad Obermeyer, Brian Powers, Christine Vogeli & Sendhil Mullainathan, "Dissecting Racial Bias in an Algorithm Used to Manage the Health of Populations," *Science* 366(6464), 25 October 2019. https://www.eurekalert.org/news-releases/877184
> - ProPublica (Angwin, Larson, Mattu & Kirchner), *Machine Bias*, 23 May 2016 (widely cited 2019–2023). https://www.propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing
> - University of Bologna, *Italian Labour and Employment Law e-Journal*, "Behind the Scenes of Deliveroo's Algorithm: The Discriminatory Effect of Frank's Blindness," 2021. https://illej.unibo.it/article/download/12990/12946/48776
> - Reuters, *Amazon Scraps Secret AI Recruiting Tool That Showed Bias Against Women*, 10 October 2018. https://www.reuters.com/article/technology/amazon-scraps-secret-ai-recruiting-tool-that-showed-bias-against-women-idUSKCN1MK08G/
> - ASH Clinical News, *Watson Supercomputer Recommended Unsafe Treatments* (reporting STAT News), 2 August 2018. https://www.ashclinicalnews.org/news/watson-supercomputer-recommended-unsafe-treatments
> - The Guardian, *Ofqual Head Sally Collier Resigns Over Exams Fiasco*, 25 August 2020. https://www.theguardian.com/education/2020/aug/25/ofqual-head-sally-collier-resigns-over-exams-fiasco
> - Ada Lovelace Institute, *Can Algorithms Ever Make the Grade?*, 18 August 2020. https://www.adalovelaceinstitute.org/blog/can-algorithms-ever-make-the-grade/
> - International Labour Organization, *World Employment and Social Outlook: Trends 2021*, 2 June 2021. https://www.ilo.org/publications/world-employment-and-social-outlook-trends-2021
> - World Bank, *World Development Report 2019: The Changing Nature of Work*. https://blogs.worldbank.org/en/developmenttalk/world-development-report-2019-changing-nature-work-finally-out-officially
> - World Health Organization, *Ethics and Governance of Artificial Intelligence for Health*, 28 June 2021. https://www.who.int/publications/i/item/9789240029200
> - Pew Research Center, *Public Awareness of Artificial Intelligence in Everyday Activities*, 15 February 2023. https://www.pewresearch.org/science/2023/02/15/public-awareness-of-artificial-intelligence-in-everyday-activities/
> - Pew Research Center, *Americans Have Grown More Concerned About AI Over Time* (trend chart). https://www.pewresearch.org/chart/americans-have-grown-more-concerned-about-ai-over-time/
> - Jason Burton, Mari-Klara Stein & Tina Blegind Jensen, "A Systematic Review of Algorithm Aversion in Augmented Decision Making," *Journal of Behavioral Decision Making* (2020). https://onlinelibrary.wiley.com/doi/full/10.1002/bdm.2155
> - UN General Assembly, Report of the Special Rapporteur on Extreme Poverty and Human Rights (Philip Alston), *The Digital Welfare State*, A/74/493, 11 October 2019. https://digitallibrary.un.org/record/3834146
> - UK Government (DCMS / Office for AI / BEIS), *Guidelines for AI Procurement*, 8 June 2020. https://www.gov.uk/government/publications/guidelines-for-ai-procurement
> - ENISA, *Artificial Intelligence and Next-Gen Technologies* (AI cybersecurity work, incl. December 2020 report). https://www.enisa.europa.eu/topics/artificial-intelligence-and-next-gen-technologies
> - OECD & CAF, *The Strategic and Responsible Use of Artificial Intelligence in the Public Sector of Latin America and the Caribbean*, March 2022. https://www.oecd.org/content/dam/oecd/en/publications/reports/2022/03/the-strategic-and-responsible-use-of-artificial-intelligence-in-the-public-sector-of-latin-america-and-the-caribbean_17c90e5e/1f334543-en.pdf
> - OECD, *Tax Administration 2022*. https://www.oecd.org/content/dam/oecd/en/publications/reports/2022/06/tax-administration-2022_5944859e/1e797131-en.pdf
> - Cities Today, *Generative AI Could Boost Government Productivity by $1.75 Trillion a Year* (reporting BCG), 13 December 2023. https://cities-today.com/generative-ai-could-boost-government-productivity-by-1-75-trillion-a-year/
> - CNIL (France), *43e rapport annuel d'activité 2022* (Clearview AI €20m sanction, October 2022). https://www.cnil.fr/sites/cnil/files/atoms/files/cnil_-_43e_rapport_annuel_-_2022.pdf
> 
> ---
> 
> *本报告基于公开资料编写，仅供研究参考。报告中涉及的政策文件与法律条文，请以官方发布文本为准。*

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---

## 条目 30

**题目**：Legal Research on Traffic Accident Liability for German Autonomous Vehicles（Crime & Law）

**禁用的来源文章**：Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China

- https://www.mdpi.com/2032-6653/15/7/305
- https://www.mdpi.com/2032-6653/15/7/305/pdf
- https://www.mdpi.com/2032-6653/15/7/305/html
- https://www.mdpi.com/2032-6653/15/7/305/xml
- https://www.researchgate.net/publication/382225455_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_of_the_German_Legislation_for_China
- https://www.researchgate.net/publication/382400472_Distribution_of_the_Burden_of_Proof_in_Autonomous_Driving_Tort_Cases_Implications_from_the_German_Legislation_for_China/download

**脚本查到的**：读入禁用来源 0 次；下载了没读 0 次；只是提到 0 次；日志里出现评测集名字 0 次。 文字重合：报告里没有出现来源文章的标题；与来源正文相同的 12 词片段 0 条；相同的参考文献 0 条。

**这次运行打开过 149 个地址，最多的站点**：buzer.de 58，gesetze-im-internet.de 24，dejure.org 13，lexcada.com 8，verkehrsopferhilfe.de 6，gesetze-im-internet.juris.de 6，umwelt-online.de 5，eur-lex.europa.eu 4，rewis.io 2，jusline.de 2，bundesgerichtshof.de 1，jura.uni-hannover.de 1

**打开过的、和禁用来源同一个站点的地址**：无

**报告的各级标题**：

    # 德国 L3 级及以上自动驾驶汽车交通事故责任调研报告
    ## 一、结论摘要
    ## 二、法律框架与基本概念（模块 1）
    ### 2.1 立法沿革
    ### 2.2 概念与主体
    ### 2.3 三层责任结构
    ### 2.4 国际与欧盟框架（要点）
    ### 2.5 自动化等级与德国法框架的对应
    ## 三、驾驶员（Fahrer）责任（模块 2）
    ### 3.1 请求权基础与责任类型
    ### 3.2 诉讼中的证明结构
    ### 3.3 其他请求权基础
    ### 3.4 刑事与秩序法责任（要点）
    ### 3.5 判例与现状
    ## 四、持有人（Halter）责任（模块 3）
    ### 4.1 请求权基础与责任类型
    ### 4.2 与驾驶员责任的区别
    ### 4.3 举证责任
    ### 4.4 赔偿范围与上限
    ## 五、生产者侵权责任：Produzentenhaftung（`§ 823 BGB` 路径）（模块 4）
    ### 5.1 概念与法律来源
    ### 5.2 构成要件与注意义务
    ### 5.3 举证责任：BGH“鸡瘟案”（Hühnerpest）
    ### 5.4 法律后果与竞合
    ## 六、制造商产品责任：`ProdHaftG` 路径（模块 5）
    ### 6.1 法律来源与性质
    ### 6.2 构成要件（`§§ 1–5 ProdHaftG`）
    ### 6.3 免责与抗辩（`§ 1 Abs. 2, Abs. 3 ProdHaftG`）
    ### 6.4 举证责任（`§ 1 Abs. 4 ProdHaftG`）
    ### 6.5 法律后果与期间
    ### 6.6 两套制度的系统对比
    ### 6.7 2024 年中期之后的欧盟新动态（单独标注）
    ## 七、技术监督人与无人驾驶运营（`§§ 1d–1l StVG`）（模块 7）
    ### 7.1 规范结构
    ### 7.2 技术监督人的民事责任
    ### 7.3 AFGBV（2022）
    ### 7.4 2024 年“常规运营”改革状态
    ## 八、保险、赔付与受害人救济（模块 6）
    ## 九、举证责任、数据与证据获取（模块 8，横向汇总）
    ### 9.1 三方举证责任总表

**报告开头**：

> # 德国 L3 级及以上自动驾驶汽车交通事故责任调研报告
> 
> **信息截止点：2024 年中期**（此后发生的变化在文中以“2024 年中期之后”单独标注）
> 
> **调研方法说明**：本报告将主题拆分为 8 个互不重叠的模块并行调研，再行汇总；所有法条、金额、日期均以德国现行法官方文本及权威一手来源核对。报告只讨论民事（及必要时的刑事）责任，不构成法律意见。
> 
> ---
> 
> ## 一、结论摘要
> 
> 1. **德国没有为自动驾驶另建一套责任体系**，而是在原有三层结构上做“增量调整”：
>    - **驾驶员责任**：`§ 18 StVG`（《道路交通法》第 18 条）——形式上以过错为要件，但**举证责任倒置**，驾驶员必须证明“损害并非因自己的过错造成”才能免责；
>    - **持有人责任**：`§ 7 StVG`——**无过错危险责任**（Gefährdungshaftung），原则上只有“不可抗力”（höhere Gewalt）才能免责；
>    - **生产者/制造商责任**：`§ 823 BGB`（《民法典》，法官法上的“生产者侵权责任”Produzentenhaftung，**过错责任**）与 `ProdHaftG`（《产品责任法》，**无过错严格责任**）两条轨道并行。
> 2. **自动化程度越高，责任重心越向持有人和制造商转移**：L3 阶段（`§ 1a StVG`）“系统驾驶、人须随时接管”，驾驶员仍是法律上的 Fahrzeugführer（`§ 1a Abs. 4 StVG` 拟制），但若损害纯由系统缺陷造成，驾驶员可依 `§ 18 Abs. 1 S. 2 StVG` 举证免责；L4 阶段（`§§ 1d ff. StVG`）无驾驶员，`§ 7 StVG` 持有人责任照旧适用，“技术监督人”（Technische Aufsicht）依 `§ 1f Abs. 2 StVG` 承担义务并可能依 `§ 823 BGB` 承担责任。
> 3. **对受害人最有利的路径通常是**：直接起诉**持有人 + 责任保险人**（`§ 7 StVG` + `§ 115 VVG` 直接请求权），因为持有人几乎无法免责；对生产者/制造商则须跨过“产品缺陷”和因果关系的证明门槛。
> 4. **赔偿上限**：`§ 12 StVG` 普通机动车为人身 500 万欧元/财产 100 万欧元；**使用自动化驾驶功能（`§ 1a`）或自动驾驶功能（`§ 1e`）时提高为人身 1,000 万欧元/财产 200 万欧元**。`ProdHaftG` 人身损害上限 8,500 万欧元，财产损害有 500 欧元自负额。
> 5. **证据核心是“黑匣子”数据**：`§ 63a StVG`（2017 年，L3）与 `§ 1g StVG`（2021 年，L4）分别规定数据存储；`§ 63a Abs. 3`、`§ 1g Abs. 7 StVG` 赋予事故相关第三人为主张或抗辩民事请求权而获取数据的权利，这是自动驾驶诉讼举证责任分配的关键配套制度。
> 6. **截至 2024 年中期，德国尚无 L3/L4 事故的终审判决**；实务规则仍由传统判例（尤其是 `§ 7 Abs. 2`、`§ 18 StVG` 的举证责任判例）和学理支撑。联邦政府“常规运营”（Regelbetrieb）修法在 2024 年中期尚未完成。
> 
> **责任链条一览（L3/L4 事故致害）**
> 
> ```
> 事故造成损害
> ├── 驾驶人（Fahrer）
> │     § 18 Abs. 1 StVG：推定过错责任；须自证“损害非因自己过错”（§ 1

**报告结尾（含参考文献）**：

> 
> **法条原文（均为实际核对页）**
> 
> - StVG：`§ 7` https://www.buzer.de/7_StVG.htm ｜`§ 18` https://www.buzer.de/18_StVG.htm ｜`§ 12` https://www.buzer.de/12_StVG.htm ｜`§ 17` https://www.buzer.de/17_StVG.htm ｜`§ 8` https://www.buzer.de/8_StVG.htm
> - StVG（2017/2021 新增条款）：`§ 1a` https://www.buzer.de/1a_StVG.htm ｜`§ 1b` https://www.buzer.de/1b_StVG.htm ｜`§ 1d` https://www.buzer.de/1d_StVG.htm ｜`§ 1e` https://www.buzer.de/gesetz/848/al0-151981.htm ｜`§ 1f` https://www.buzer.de/1f_StVG.htm ｜`§ 1g` https://www.buzer.de/1g_StVG.htm ｜`§ 63a` https://www.buzer.de/63a_StVG.htm
> - ProdHaftG（全文）https://www.buzer.de/ProdHaftG.htm
> - PflVG：`§ 4` https://www.buzer.de/4_PflVG.htm ｜附件（最低保额）https://www.buzer.de/Anlage_PflVG.htm
> - VVG：`§ 115` https://www.buzer.de/115_VVG.htm
> - 2024 年 8 月第 6 次 StVG 修改法对照 https://www.buzer.de/gesetz/848/v316269-2024-08-22.htm
> - 官方法条门户（本次网络不可达时以 buzer 逐句核对）：https://www.gesetze-im-internet.de/stvg/__18.html
> 
> **判例**
> 
> - BGH, 26.11.1968 – VI ZR 212/66 = BGHZ 51, 91（Hühnerpest）http://lorenz.userweb.mwn.de/urteile/bghz51_91.htm
> - BGH, 11.06.1974 – VI ZR 37/73（驾驶人免责举证）https://verkehrslexikon.de/Texte/FuehrerHaftung6.php
> - BGH, 18.01.2005 – VI ZR 115/04（unabwendbares Ereignis）https://www.iww.de/quellenmaterial/id/14688
> - BGH, 07.02.2023 – VI ZR 87/22（挂车溜车仍属“车辆运营”）https://www.bundesgerichtshof.de/SharedDocs/Entscheidungen/DE/Zivilsenate/VI_ZS/2022/VI_ZR__87-22.pdf
> - BGH, 15.11.1966 – VI ZR 280/64（höhere Gewalt，据 dejure 索引）https://dejure.org/dienste/vernetzung/rechtsprechung?Text=VersR%201967,%20138
> - BGH, 09.05.1995 – VI ZR 158/94（Airbag/产品观察义务）https://dejure.org/dienste/vernetzung/rechtsprechung?Gericht=BGH&Datum=09.05.1995&Aktenzeichen=VI%20ZR%20158%2F94
> - BGH, 16.06.2009 – VI ZR 107/08（安全气囊/说明义务）https://www.anwalt24.de/urteile/bgh/2009-06-16/vi-zr-107_08
> - BayObLG, 21.10.2024 – 202 ObOWi 644/24（Tesla Autopilot 定为 L2，2024 年中期之后的动态）https://www.burhoff.de/asp_weitere_beschluesse/inhalte/9114.htm
> 
> **立法与欧盟文件**
> 
> - 欧盟议会与理事会条例 (EU) 2024/1689（AI 法案）：eur-lex.europa.eu
> - 新《产品责任指令》(EU) 2024/2853：eur-lex.europa.eu
> - 指令 2009/103/EG 与修订指令 (EU) 2021/2118：https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32009L0103 ｜ https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32021L2118
> - EDR/EDR 强制要求（日期依二手表述，条文细节待核实）：条例 (EU) 2019/2144 ｜ 授权条例 (EU) 2022/545 ｜ UN R160
> - AFGBV（2022-06-24，BGBl. I S. 986）全文（核对页）：https://www.umwelt-online.de/recht/gefahr.gut/strasse/afgbv22.htm
> - 2021 年法立法材料线索：https://dserver.bundestag.de/btd/19/298/1929875.pdf ｜ BR-Drs. 155/21：https://www.bundesrat.de/SharedDocs/drucksachen/2021/0101-0200/155-1-21.pdf
> - 第十次 StVG 修改法（2024-07-17 生效，BGBl. 2024 I Nr. 233）对照：https://www.buzer.de/gesetz/848/v313657-2024-07-17.htm
> - 德国 2024-04-11 转化指令 (EU) 2021/2118 的法律（BGBl. 2024 I Nr. 119）：buzer.de
> - Verkehrsopferhilfe e.V.（赔偿基金/赔偿机构）：https://www.verkehrsopferhilfe.de/ ｜ https://www.verkehrsopferhilfe.de/garantiefonds-entschaedigungsfonds/
> 
> *本报告基于公开的一手法律文本、判例与官方文件编写，信息截止 **2024 年中期**；文中明确标注为“2024 年中期之后”的内容仅供背景参考。报告为学理与实务梳理，不构成法律意见。*

判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：

---
