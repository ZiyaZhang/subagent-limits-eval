# subagent 再派活的分类：人工核对

共 30 条。每条是一个 subagent 领到的任务和它派出去的一条任务，判断这条派出去的任务属于哪一类。不显示模型的判断、组别和运行编号。

- 原样转包：把自己领到的整件事原样交给下一层，自己不留明确的一块
- 分片：把自己的任务切成几块，这条是其中一块，几块合起来基本就是它自己的任务
- 收窄：只把一小块交出去（一个子问题、一个来源、一个数），大部分还是自己做
- 新子题：交出去的是自己任务里没写的事（做着做着冒出来的问题、补充背景、环境杂事）
- 复核：让下一层检查、核实、评审已经做出来的东西
- 拿不准

任务说明长的只显示开头 200 字和它独有的部分；与它自己领到的任务或与其他派出任务逐字相同的段落折叠成方括号里的一句说明。

在 check-answers-template.csv 的 answer 列填类名，另存为 check-answers.csv。

## 条目 1

**这个 subagent 领到的任务**：

> You are researching VERIFIED FACTS for a report on social protection for cultural/creative sector workers in URUGUAY, with information cutoff EARLY 2021 (Jan–Mar 2021). Prioritize official sources (impo.com.uy, bps.gub.uy, gub.uy, MTSS, MEC, Parlamento) published 2020–2021. Do NOT fabricate; mark uncertain items [UNCERTAIN] and give exact figures with dates.
> 
> HARD PROHIBITION (highest priority): You must NOT open, fetch, view, search for the full text of, or cite the article "Social Protection in the Cultural and Creative Sector: Country Practices and Innovations" by Carlos Galian, Margherita Licata, Maya Stern-Plaza, nor ANY of its URLs, mirrors, reprint pages, abstract pages, or repository …[3605 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are researching VERIFIED FACTS about Uruguay's COVID-19 modifications to the "seguro de desempleo" (unemployment insurance) in 2020 – early 2021, for a report on social protection for cultural/creative sector workers.  …[这里有 857 字与它派出的其他任务逐字相同]… TASK: Find exact legal instruments, numbers, dates, and precise rule changes for these Uruguayan decrees/statutes, verifying on impo.com.uy (official) where possible:
> 1. Decreto 130/020 (April 2020) – what exactly did it change about seguro de desempleo? (e.g. relaxation of contribution requirements, benefit for those with fewer contributions, "seguro de paro especial"?)
> 2. Decreto 178/020 – content and date.
> 3. Decreto 246/020 – content and date …[1117 more characters]

它派出去的其他任务（各取开头）：
- You are researching VERIFIED FACTS about Uruguay's COVID-19 support for NON-DEPENDENT workers (trabajadores no …[2390 more characters]
- You are researching VERIFIED FACTS for a report on social protection for cultural/creative sector workers in U …[2914 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 2

**这个 subagent 领到的任务**：

> You are researching the history and cultural context of Japanese "isekai" (another-world) manga for a report. Produce a well-sourced summary in English of roughly 800-1200 words. Focus on material published up to about 2020 (retrospectives published later are acceptable if clearly labelled).
> 
> Cover these four topics:
> 
> 1. ISEKAI'S RELATIONSHIP TO ROLE-PLAYING GAMES (RPGs)
>    - How Japanese RPGs, especially Dragon Quest (1986) and Final Fantasy, shaped the isekai genre's conventions: levels, classes, status screens/"status open", demon lords, guilds, Adventurers' Guild, MP/HP, "cheat" skills.
>    - The concept of LitRPG / "game-like" fantasy worlds and the difference between (a) stories explici …[4056 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are doing source-gathering research for a report on Japanese "isekai" (another-world) web novels, focusing on DEMOGRAPHICS and READERSHIP DATA. Work in English; return findings with URLs.
> 
> HARD CO …[这里有 863 字与它派出的其他任务逐字相同]… Shōsetsuka ni Narō (小説家になろう, "Syosetu", founded 2 April 2004 by Yusuke Umezaki):
>    - Registered user counts and total works over time (e.g. 2010s figures such as ~1 million users / ~400,000 works around 2018-2020, and later figures).
>    - Age and gender breakdown of users. There is a well-known Japanese source: a Syosetu user's activity report page 「小説家になろう、及びなろう発コミック・アニメの男女比・年齢比」 at https://ncode.syosetu.com/n2194ga/ which reportedly gives figures like 20s = 44%, 30 …[2718 more characters]

它派出去的其他任务（各取开头）：
- You are doing source-gathering research for a report on Japanese "isekai" (another-world) manga, focusing on O …[4398 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 3

**这个 subagent 领到的任务**：

> 你是免疫学/RNA表观转录组学文献调研员。任务：调研 m⁶A 修饰在以下**巨噬细胞特殊主题**中的研究。必须使用 web_search 与 web_fetch（PubMed 摘要页 https://pubmed.ncbi.nlm.nih.gov/<PMID>/ 、PMC 全文、期刊页）核实**每一篇**文献。
> 
> 【绝对禁止（最高优先级）】不得打开、阅读、引用、转述以下文章及其任何版本/转载/摘要页/镜像：
> "Impact of N6-methyladenosine (m⁶A) modification on immunity" (Elsabbagh RA, Rady M, Watzl C, Abou-Aisha K, Gad MZ)。
> 禁止URL：researchgate.net/publication/363416511...、researchgate.net/publication/363481920...、biosignaling.biomedcentral.com/articles/10.1186/s12964-022-00939-8、pubmed.ncbi.nlm.nih.gov/36085064/、unboundmedicine.com 上对应条目。搜索结果中出现则跳过，不要在输出中列出。
> 
> 【调研内容】
> 1) m⁶A 与**训练免疫（trained immunity）/先天免疫记忆**：例如 β-glucan、BCG、LPS 诱导的 trained immunity 中 METTL3、METTL14、YTHDF1/2、FTO、ALKBH5、m⁶A 修饰的作用；靶 …[667 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are a bibliographic verification agent. Your ONLY job is to verify that a list of PubMed IDs (PMIDs) exist and that their official titles match what PubMed reports. Do not summarize or interpret t …[这里有 959 字与它派出的其他任务逐字相同]… 34225477, 37858336, 33220174, 36864027, 33910903, 30875984, 34758326, 40920087, 42032669, 42327744, 38548762, 34019807, 36658237, 33654093, 32964498, 32747553, 38197667, 34416901, 35526050, 34258163, 34670781, 38872221, 35982895, 37402945, 37236197, 35197058, 42766005, 41507178, 40856928, 40419792, 40401803, 39447407
>  …[这里有 359 字与它派出的其他任务逐字相同]…

它派出去的其他任务（各取开头）：
- You are a bibliographic verification agent. Your ONLY job is to verify that a list of PubMed IDs (PMIDs) exist …[1727 more characters]
- You are a bibliographic verification agent. Your ONLY job is to verify that a list of PubMed IDs (PMIDs) exist …[1737 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 4

**这个 subagent 领到的任务**：

> You are a research assistant gathering evidence for the DRAWBACKS/RISKS section of a systematic review on ChatGPT in teaching and learning, restricted to publications available on or before 12 October 2023.
> 
> HARD PROHIBITION (highest priority, do not violate): You must NOT open, fetch, read, cite, or summarize the article "ChatGPT in Teaching and Learning: A Systematic Review" by Duha Ali, Yasin Fatemi, Elahe Boskabadi, Mohsen Nikfar, Jude Ugwuoke, Haneen Ali, nor any of its pages/mirrors/abstracts. NEVER access these URLs:
> - https://www.mdpi.com/2227-7102/14/6/643
> - https://www.researchgate.net/publication/381430312_ChatGPT_in_Teaching_and_Learning_A_Systematic_Review
> - https://www.semantic …[3150 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are a research assistant gathering evidence for a systematic review on ChatGPT in teaching and learning, restricted to publications available on or before 12 October 2023.
> 
> HARD PROHIBITION (highe …[这里有 757 字与它派出的其他任务逐字相同]… YOUR TASK: Find real, verifiable, peer-reviewed or well-cited preprint/report sources published/posted ON OR BEFORE 12 OCTOBER 2023 that document DRAWBACKS of ChatGPT / large language models specifically in teaching and learning, in these THREE theme areas:
> (A) Privacy, data protection and security risks (e.g., students/teachers entering personal or sensitive data into ChatGPT; data used for training; FERPA/GDPR concerns; account/data leakage).
> (B) Equity, digital div …[1470 more characters]

它派出去的其他任务（各取开头）：
- You are a research assistant gathering evidence for a systematic review on ChatGPT in teaching and learning, r …[3279 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 5

**这个 subagent 领到的任务**：

> You are researching, for a factual report, the use of augmented reality (AR) for HISTORY EDUCATION in classroom/formal-education settings, limited to material publicly available BEFORE MAY 2019.
> 
> HARD CONSTRAINT — you must NEVER open, fetch, read, quote or cite any of the following (and no mirror, repost, abstract page, or translation of it):
> - The article "A Review of Augmented Reality Applications for History Education and Heritage Visualisation" by Jennifer Challenor & Minhua Ma
> - https://www.mdpi.com/2414-4088/3/2/39
> - https://doaj.org/article/e1537f41ad544db0aa2fd93fe828582b
> - https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/A-Review-of-Augmented-Reality-Applications/999 …[3443 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are verifying bibliographic citations and SPECIFIC findings for a factual research brief on augmented reality (AR) in education. Your work must be strictly evidence-based: never invent authors, ye …[这里有 3642 字与它派出的其他任务逐字相同]…  the DOAJ API https://doaj.org/api/search/articles/...; core.ac.uk; learntechlib.org; university repository pages; dspace/mit; …[这里有 671 字与它派出的其他任务逐字相同]…

它派出去的其他任务（各取开头）：
- You are verifying bibliographic citations and SPECIFIC findings for a factual research brief on augmented real …[4653 more characters]
- You are verifying bibliographic citations and SPECIFIC empirical findings for a factual research brief on augm …[4891 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 6

**这个 subagent 领到的任务**：

> 你是"量子系统自测试（self-testing）技术综述报告"项目的研究员，负责【第 4 部分：鲁棒自测试（robust self-testing）——定义与解析方法】。最终报告由主控 agent 汇总，你只需产出你这一部分的素材文件。
> 
> ## 一、最高优先级硬性约束（必须遵守，不可违反）
> 1. 严禁打开、检索、抓取、引用以下文章及其任何转载页、摘要页、预印本页、HTML/ar5iv 版本、数据库条目：
>    文章：《Self-testing of quantum systems: a review》，作者 Ivan Šupić & Joseph Bowles。
>    禁止访问的 URL（一个都不许打开）：
>    - https://arxiv.org/abs/1904.10042
>    - https://quantum-journal.org/papers/q-2020-09-30-337/
>    - https://www.researchgate.net/publication/350646502_Self-testing_of_quantum_systems_a_review
>    - https://ui.adsabs.harvard.edu/abs/2020Quant...4..337S/abstract
>    - https://inspirehep.net/literature/1730930
>    - https://ar5iv.labs.arxiv.org/html/1904.10042
>    - https://ouci.dntb.gov.ua/en/w …[1612 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are assisting a literature-survey project on "robust self-testing" (quantum information). Your job: extract EXACT robustness statements from papers on multipartite / general-state self-testing.
> 
> S …[这里有 641 字与它派出的其他任务逐字相同]… Only consider works publicly available on or before 2020-09-30 (this is a hard cutoff; if you find something important that is later, put it in a clearly-marked "AFTER DEADLINE" note, do not mix it in).
> 
> TASKS — for each, give the exact bibliographic record, the exact robustness statement (formula with exponents/constants), method used (analytic/direct-sum-of-squares/algebraic/isometry-swap/NPA-based), and stated limitations:
> 
> (1) M. McKague, "Self-testing graph state …[1497 more characters]

它派出去的其他任务（各取开头）：
- You are assisting a literature-survey project on "robust self-testing" (quantum information). Your job: extrac …[2879 more characters]
- You are assisting a literature-survey project on "robust self-testing" (quantum information). Your job: extrac …[2548 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 7

**这个 subagent 领到的任务**：

> You are researching for a technical report on railway/rail-adjacent communications. DATA CUTOFF: only public information available BEFORE June 2017 (prefer sources dated <= May 2017). Do not cite sources published after May 2017. Work in /work/<run>/workspace.
> 
> ABSOLUTE PROHIBITION (highest priority): Never open, fetch, search-for, quote, or cite the following article or ANY mirror/abstract/figure/reprint page of it:
> Title: "Towards the Internet of Smart Trains: A Review on Industrial IoT-Connected Railways"; Authors: Paula Fraga-Lamas, Tiago M. Fernández-Caramés, Luis Castedo.
> URLs never to touch: https://www.mdpi.com/1424-8220/17/6/1457 ; https://pubmed.ncbi.nlm.nih.gov/28635672/ ; ht …[3062 more characters]

**它一共派出 1 条不同的任务，要判的是这一条**：

> You are doing evidence gathering for a technical report on railway/rail-adjacent communications. DATA CUTOFF: only public information available BEFORE June 2017 (prefer sources dated <= May 2017). Never cite anything published after May 2017. Work in /work/<run>/workspace (you may write scratch files there, e.g. rail_notes.md).
> 
> ABSOLUTE PROHIBITION (highest priority): Never open, fetch, search for, quote, or cite this article or any mirror/abstract/figure/reprint page of it:
> "Towards the Internet of Smart Trains: A Review on Industrial IoT-Connected Railways" by Paula Fraga-Lamas, Tiago M. Fernández-Caramés, Luis Castedo (MDPI Sensors 2017). Never touch mdpi.com/1424-8220/17/6/1457, pu …[2583 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 8

**这个 subagent 领到的任务**：

> You are researching the SOLID-STATE BATTERY industry for a market report with an information cutoff of END OF 2023 (situation as of ~December 2023). Do NOT include 2024+ developments except where a plan was already announced by end-2023.
> 
> STRICT RULE (highest priority): You MUST NOT open, read, fetch, quote, or cite the article "Technological Advances and Market Developments of Solid-State Batteries: A Review" by Felix Thomas, Lauren Mahdi, Julien Lemaire, Diogo M. F. Santos, nor any of its pages/mirrors/abstracts: https://www.mdpi.com/1996-1944/17/1/239 , https://www.researchgate.net/publication/377061990_Technological_Advances_and_Market_Developments_of_Solid-State_Batteries_A_Review , htt …[3231 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are researching the SOLID-STATE BATTERY (SSB) industry for a market report with an information cutoff of END OF 2023 (situation as of ~December 2023). Do NOT include 2024+ developments except wher …[这里有 899 字与它派出的其他任务逐字相同]… TASK: Investigate JAPANESE CHEMICAL/MATERIALS companies' activities in SOLID-STATE BATTERY electrolytes, with emphasis on POLYMER electrolytes / polymer binders / ion-conductive polymers / PVDF / gel-polymer / "semi-solid" polymer approaches, AS OF END-2023.
> 
> Companies to investigate (for each: does it make a POLYMER solid electrolyte or polymer-composite electrolyte? Or is it supplying materials like binders, separators, PVDF, sulfide/oxide raw materials?):
> - Sumitom …[2669 more characters]

它派出去的其他任务（各取开头）：
- You are researching the SOLID-STATE BATTERY (SSB) industry for a market report with an information cutoff of E …[4156 more characters]
- You are researching the SOLID-STATE BATTERY (SSB) industry for a market report with an information cutoff of E …[5157 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 9

**这个 subagent 领到的任务**：

> You are doing literature research for a report on Learning Analytics (LA) in higher education. RESEARCH SCOPE: only sources published up to and including 2023.
> 
> STRICT PROHIBITION (highest priority rule): You must NEVER open, fetch, read, search-for, or cite the article titled "The Evolving Classroom: How Learning Analytics Is Shaping the Future of Education and Feedback Mechanisms" by Hanan Sharif and Amara Atif, and you must never open these URLs or any mirror/repost/abstract page of that article:
> - https://www.mdpi.com/2227-7102/14/2/176
> - https://www.researchgate.net/publication/378088586_The_Evolving_Classroom_How_Learning_Analytics_Is_Shaping_the_Future_of_Education_and_Feedback_Mechan …[4111 more characters]

**它一共派出 4 条不同的任务，要判的是这一条**：

> You are doing citation verification for a literature review on Learning Analytics in higher education. Only sources published up to and including 2023 may be used.
> 
> ABSOLUTE PROHIBITION (highest prior …[这里有 1213 字与它派出的其他任务逐字相同]… Cluster: dashboards/visualisation & feedback, predictive/early-warning systems, learning design & curriculum analytics, assessment/feedback loops, conversational agents/chatbots/generative AI in feedback.
> 
> 1. Verbert, K., Govaerts, S., Duval, E., Santos, J. L., Van Assche, F., Parra, G., & Klerkx, J. (2014). Learning dashboards: an overview and future research opportunities. Personal and Ubiquitous Computing.
> 2. Verbert, K., Ochoa, X., De Croon, R., Dourado, R. A., & …[2889 more characters]

它派出去的其他任务（各取开头）：
- You are doing citation verification for a literature review on Learning Analytics in higher education. Only so …[4449 more characters]
- You are doing citation verification for a literature review on Learning Analytics in higher education. Only so …[4118 more characters]
- You are doing citation verification for a literature review on Learning Analytics in higher education. Only so …[5017 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 10

**这个 subagent 领到的任务**：

> You are researching general background on sovereign wealth funds (SWFs) for a report that must reflect the situation as of early 2021.
> 
> STRICT RULE — DO NOT OPEN, READ, OR CITE ANY OF THESE (and no mirrors/reposts/abstract pages of them):
> - The article "Sovereign wealth funds and corporate social responsibility: a comparison of Norway's Government Pension Fund Global and Abu Dhabi Fund for Development" by Sivakumar Velayutham and Rashedul Hasan
> - https://doi.org/10.1108/PAP-08-2020-0037
> - https://pureportal.coventry.ac.uk/en/publications/sovereign-wealth-funds-and-corporate-social-responsibility-a-comp
> - https://www.researchgate.net/publication/353481812_Sovereign_wealth_funds_and_corporate_ …[2860 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are researching sovereign wealth funds (SWFs) for a report that must reflect the situation as of early 2021. You have web_search and web_fetch. Work rigorously; never fabricate a fact or URL. If y …[这里有 862 字与它派出的其他任务逐字相同]… TASK: Produce a compact, citation-rich research note (bullet points, each claim with its exact source URL) covering:
> 
> A. SWF funding sources, with at least one concrete country example each:
>    1) commodity (oil/gas/minerals) export revenues
>    2) accumulated foreign-exchange reserves
>    3) fiscal/budget surpluses
>    4) pension contributions
>    5) privatisation proceeds
>    6) transfers from the central bank
> Prefer IMF (imf.org), World Bank (worldbank.org), OECD (oecd. …[2980 more characters]

它派出去的其他任务（各取开头）：
- You are researching sovereign wealth funds (SWFs) for a report that must reflect the situation as of early 202 …[3525 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 11

**这个 subagent 领到的任务**：

> You are researching German road-traffic liability law for a report on automated/autonomous driving (Level 3+). Information cutoff: mid-2024.
> 
> ABSOLUTE PROHIBITION — you must NEVER open, fetch, search for, cite, or quote any of these URLs, nor any mirror/reprint/abstract page of the article they belong to:
> - Article title: "Distribution of the Burden of Proof in Autonomous Driving Tort Cases: Implications of the German Legislation for China" by Zhihua Chen, Qianyi Cai, Hanbing Wei
> - URLs: https://www.mdpi.com/2032-6653/15/7/305 , https://www.mdpi.com/2032-6653/15/7/305/pdf , https://www.mdpi.com/2032-6653/15/7/305/html , https://www.mdpi.com/2032-6653/15/7/305/xml , https://www.researchgate.n …[7098 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are researching German and EU product-liability law and joint-liability rules for a memo on automated driving. Research in GERMAN (and English for EU sources); prefer primary sources: gesetze-im-internet.de (use the mirror pattern https://web.archive.org/web/2024/https://www.gesetze-im-internet.de/prodhaftg/__8.html — the direct domain is unreachable/403 here), eur-lex.europa.eu, bundestag.de, bmj.de/bmjv.de, dejure.org, openjur.de, Wikipedia DE as fallback.
>  …[这里有 960 字与它自己领到的任务逐字相同]… TASK — verify with exact paragraph numbers, current wording (as of mid-2024), and URLs:
> 1. § 1 ProdHaftG (liability of the manufacturer), § 3 ProdHaftG (no exculpation for fault; the "Ausreißer" defence is …[2246 more characters]

它派出去的其他任务（各取开头）：
- You are researching German road-traffic law facts. Research in GERMAN, prefer official/primary sources (kba.de …[3160 more characters]
- You are researching German road-traffic liability law (StVG) case law. Research in GERMAN, prefer primary sour …[3949 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 12

**这个 subagent 领到的任务**：

> 你是流媒体系统方向研究员。请调研视频"码率阶梯（bitrate ladder）"与 per-title encoding 的演进，输出**详细结构化中文调研笔记**（约 1500–2500 字，含来源 markdown 链接），用于技术综述写作。时间截点以 2025 年初为准，若信息更晚请注明。
> 
> 【最高优先级限制】绝对不要访问、阅读、抓取、引用或提及《HTTP Adaptive Streaming: A Review on Current Advances and Future Challenges》（作者：Christian Timmerer, Hadi Amirpour, Farzad Tashtarian, Samira Afzal, Amr Rizk, Michael Zink, Hermann Hellwagner）及其任何页面、镜像、摘要页或转载页，包括其 ACM Digital Library 页面与 PDF（doi: 10.1145/3736306）、ResearchGate、Semantic Scholar、athena.itec.aau.at 与 campus.aau.at 的对应页面、以及 doi.org/10.1145/3736306。若搜索结果中出现该文献，请直接跳过、不要点击、不要引用、也不要在笔记中提及它。即使意外看到其内容，也必须完全忽略。
> 
> 需要覆盖：
> 1. bitrate ladder 的定义与静态 ladder 的由来/代表规范（Apple HLS Authoring Specification、DASH-IF Interoperabil …[817 more characters]

**它一共派出 1 条不同的任务，要判的是这一条**：

> You are a research assistant gathering verifiable facts with source URLs for a Chinese-language survey on video bitrate ladders and per-title encoding.
> 
> STRICT PROHIBITION: Never access, read, fetch, cite, or mention the paper "HTTP Adaptive Streaming: A Review on Current Advances and Future Challenges" (authors: Christian Timmerer, Hadi Amirpour, Farzad Tashtarian, Samira Afzal, Amr Rizk, Michael Zink, Hermann Hellwagner) or ANY of its pages/mirrors/abstract pages/repositories, including its ACM Digital Library page or PDF (doi: 10.1145/3736306), ResearchGate, Semantic Scholar, athena.itec.aau.at pages for it, campus.aau.at, or doi.org/10.1145/3736306. If it appears in search results, skip  …[3252 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 13

**这个 subagent 领到的任务**：

> You are doing literature research for a technical review of quantum self-testing with a knowledge cutoff of September 2020. Work only with sources you actually fetch (arXiv abstract pages, publisher pages, arXiv full text via ar5iv, journal pages).
> 
> HARD CONSTRAINT (highest priority): Do NOT open, fetch, read, quote, or cite the article "Self-testing of quantum systems: a review" by Ivan Šupić and Joseph Bowles, and do NOT open any of these URLs or any mirror/abstract page of that article:
> https://arxiv.org/abs/1904.10042
> https://quantum-journal.org/papers/q-2020-09-30-337/
> https://www.researchgate.net/publication/350646502_Self-testing_of_quantum_systems_a_review
> https://ui.adsabs.harvard.e …[3692 more characters]

**它一共派出 8 条不同的任务，要判的是这一条**：

> Reply with exactly the word: OK. Do not use any tools. This is a connectivity test only.

它派出去的其他任务（各取开头）：
- You are doing literature research for a technical review. Work ONLY with sources you actually fetch (arXiv abs …[3920 more characters]
- You are doing literature research for a technical review of quantum self-testing with a knowledge cutoff of Se …[3004 more characters]
- You are doing literature research for a technical review of quantum self-testing with a knowledge cutoff of Se …[3285 more characters]
- You are doing literature research for a technical review of quantum self-testing with a knowledge cutoff of Se …[3499 more characters]
- You are doing literature research for a technical review. Work ONLY with sources you actually fetch (arXiv abs …[3655 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 14

**这个 subagent 领到的任务**：

> You are doing research for a report on Artificial Intelligence in government decision-making, focused on 2019-2023.
> 
> STRICT PROHIBITION (highest priority): You must NOT open, fetch, read, or cite the article "Navigating Governmental Choices: A Comprehensive Review of Artificial Intelligence's Impact on Decision-Making" by Gustavo Caiza, Verónica Sanguña, Natalia Tusa, Violeta Masaquiza, Alexandra Ortiz, Marcelo V. Garcia. Do NOT access ANY of these URLs (nor any mirror/reprint/abstract page of that article):
> - https://www.mdpi.com/2227-9709/11/3/64
> - https://doi.org/10.3390/informatics11030064
> - https://text2fa.ir/wp-content/uploads/Text2fa.ir-Navigating-Governmental-Choices-A-Comprehensive- …[3306 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are researching the COMPARATIVE dimension of AI regulation: EU vs US vs China, focused on 2019-2023. Use web_search and web_fetch.
> 
> STRICT PROHIBITION (highest priority): Do NOT open, fetch, read, …[这里有 973 字与它派出的其他任务逐字相同]… COLLECT:
> 1. The "Brussels effect" applied to AI regulation — Bradford's work (Anu Bradford, "The Brussels Effect", 2020; and her writing on the AI Act / digital sovereignty). Evidence of third countries aligning with the EU AI Act.
> 2. Regulatory fragmentation vs harmonization: US state-level AI laws (e.g., Colorado AI Act 2024, NYC Local Law 144 on automated employment decision tools 2021/effective 2023, Illinois AI Video Interview Act 2020, California), and the absen …[1660 more characters]

它派出去的其他任务（各取开头）：
- You are researching CHINA's regulatory framework for artificial intelligence and government use of AI, focused …[3873 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 15

**这个 subagent 领到的任务**：

> 你是研究助理，请为一份关于中国"土地财政"模式转型的研究报告（覆盖至2021年）收集"转型机制"方面的公开政策与案例素材。请通过 web_search / web_fetch 自主检索，给出政策文件名称、发布时间、关键条款、来源URL。
> 
> 需要覆盖：
> 1) 土地出让收入征管改革：2021年6月财政部、自然资源部、税务总局、人民银行《关于将国有土地使用权出让收入、矿产资源专项收入、海域使用金、无居民海岛使用金四项政府非税收入划转税务部门征收有关问题的通知》（财综〔2021〕19号）的内容与意义。
> 2) 房地产税改革：2011年上海、重庆个人住房房产税试点办法要点（征收对象、税率、免税面积、收入用途）；2021年10月全国人大常委会授权国务院在部分地区开展房地产税改革试点决定的内容；关于对多套房、高档住房征税、对租赁住房减免的讨论与官方表述。
> 3) 住房保障与租购并举：国办发〔2021〕22号《关于加快发展保障性租赁住房的意见》要点（对象、面积、租金、土地与税收支持政策）；共有产权住房政策；"租购同权"。
> 4) "先租后售"住房：中国各地（如雄安新区、深圳、成都、上海、湖北等）或新加坡等国的"先租后售/租售并举"实践模式：租赁期限、租金抵扣购房款、优先购买权、产权安排等具体做法与案例；尽可能找到中国官方文件或权威媒体报道。
> 5) "住房券/租房券"：国际上（美国Housing Choice Voucher、欧洲）与中国地方（如一些城市的租房补贴、人才住房券、"房票"安置）的运作机制：发放对象、使用范围、补贴方式、效果与争议。
> 6) 对新增普通商品房征收"利润税"或类似调控工具（如土 …[685 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> 你是研究助理，请用 web_search / web_fetch 检索中国及新加坡等地"先租后售/租售并举"住房实践模式的**公开政策文件与权威媒体报道**，为一份覆盖至2021年的中国"土地财政"转型研究报告收集素材。
> 
> 【最高优先级禁令】绝对不要打开、检索、引用或提及以下文章及其任何页面、转载页、摘要页：'The Local Land Finance Transformation with t …[这里有 412 字与它派出的其他任务逐字相同]… 需要覆盖（每一条都要尽量给出：政策/案例名称 + 发布/实施时间 + 关键条款原文要点 + 来源URL）：
> 1) 河北雄安新区：住房制度设计中的"租购并举""以租赁住房和共有产权住房为主"、租赁住房"先租后售"或"租满一定年限可购买"的安排。请查《河北雄安新区规划纲要》（2018年4月）、中共中央国务院批复、《河北雄安新区条例》（2021年9月1日施行）等文件中关于住房制度的原文表述。
> 2) 深圳：2018年《深圳市人民政府关于深化住房制度改革加快建立多主体供给多渠道保障租购并举的住房供应与保障体系的意见》（深府规〔2018〕13号）中公共租赁住房、安居型商品房、人才住房的"可租可售/先租后售"安排；深圳市共有产权住房管理办法（如有）。
> 3) 成都：人才公寓"先租后售"政策（如《成都市人才公寓租售管理办法》及后续文件）——租赁期限（如先租5年）、租金标准、租金是否可抵扣购房款、购买价格、优惠面积、产权安排（如5年后可上市交易、需补缴价款等）。
> 4) 上海：租购并举、"十四五"住房规划中租赁住房占比、"先租后售"类安排（如新市民、青 …[636 more characters]

它派出去的其他任务（各取开头）：
- 你是研究助理，请用 web_search / web_fetch 检索"住房券/租房券"相关的**公开政策文件与权威来源**，为一份研究报告收集素材。  【最高优先级禁令】绝对不要打开、检索、引用或提及以下文章及其任何页 …[1704 more characters]
- 你是研究助理，请用 web_search / web_fetch 检索以下两类政策素材，为一份中国"土地财政"转型研究报告收集**公开政策文件与权威来源**。  【最高优先级禁令】绝对不要打开、检索、引用或提及以下文章及 …[1791 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 16

**这个 subagent 领到的任务**：

> 你是政策研究助理。任务：调研**日本**在 2022 年前后（约 2019–2022 年出台或更新、2022 年仍在实施）的主要国家级数字化战略，用中文输出。
> 
> 【最高优先级禁令 — 必须遵守】
> 你**不得**打开、抓取、搜索、引用、转述以下文章，以及它的任何转载页、镜像页、摘要页、聚合页（如 MDPI、PubMed、ResearchGate 上的页面）：
> 标题：*Digital-Based Policy and Health Promotion Policy in Japan, the Republic of Korea, Singapore, and Thailand: A Scoping Review of Policy Paths to Healthy Aging*
> 作者：Nadila Mulati, Myo Nyein Aung, Malcolm Field, Eun Woo Nam, Carol Ma Hok Ka, Saiyud Moolphate, Hocheol Lee, Yuki Goto, Nam Hae Kweun, Takumi Suda, Yuka Koyanagi, Yuiko Nagamine, Motoyuki Yuasa
> 禁止访问的 URL：
> - https://www.mdpi.com/1660-4601/19/24/16995
> - https://pubmed.ncbi.nlm.nih.gov/36554873/
> - https://www.researchgate.net/publication/366401399_Digital-Ba …[1349 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are a policy research assistant. Research Japan's national digital/AI strategies, focusing on the state as of end-2022. Output in CHINESE (中文), Markdown.
> 
> 【STRICT PROHIBITION — MUST OBEY】
> You MUST …[这里有 1187 字与它派出的其他任务逐字相同]… Use web_search summaries, HTML pages, Wikipedia (ja), ministry HTML pages, news articles from 2022, and archives (warp.ndl.go.jp) to verify facts.
> 
> 【YOUR ASSIGNED TOPICS】
> 1. **AI戦略2022** (AI Strategy 2022) — approved 2022年4月22日 by 統合イノベーション戦略推進会議 (Integrated Innovation Strategy Promotion Council), 内閣府. Need: official title, date, core vision (official wording), main pillars (3-6), quantitative targets, responsible ministry, source URL. Also cover the related "AIに関する暫 …[1164 more characters]

它派出去的其他任务（各取开头）：
- You are a policy research assistant. Research Japan's national digital strategies, focusing on the state as of …[3413 more characters]
- You are a policy research assistant. Research Japan's national digital government strategies, focusing on the  …[3993 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 17

**这个 subagent 领到的任务**：

> You are doing research for a report comparing Egypt and Iran on transgender/sex-reassignment policy (information cutoff: early 2024).
> 
> ABSOLUTE PROHIBITION — DO NOT VIOLATE: You must NEVER open, fetch, read, quote, or cite the article "Transsexual Surgery in Egypt or the Suspicion of Homosexuality" by Corinne Fortier, nor any of these URLs or any mirror/abstract/PDF page of it:
> - https://hal.science/hal-05097583v1/document
> - https://hal.science/hal-05097583v1
> - https://www.berghahnjournals.com/view/journals/ame/20/1/ame200108.xml
> If it appears in search results, skip it entirely. If you accidentally see content from it, ignore it.
> 
> TASK: Research IRAN's policy on sex reassignment surgery (SR …[2930 more characters]

**它一共派出 1 条不同的任务，要判的是这一条**：

> You are doing research for a comparative report on transgender/sex-reassignment policy in Egypt and Iran (information cutoff early 2024). Research ONLY the SUNNI Islamic jurisprudence side and the Egyptian institutional side. Do NOT write any files. Return a dense, factual summary (400-700 words) with inline markdown links to every source used.
>  …[这里有 506 字与它自己领到的任务逐字相同]… Cover:
> 1. The classical Sunni legal categories: al-khuntha (intersex) and al-mukhannath (effeminate man), how Sunni fiqh treated them, and the hadith-based condemnation of "mukhannathun" (e.g. the hadith of the mukhannath in Umm Salama's house). Cite academic/encyclopedia sources (Encyclopaedia of Islam, Oxford Islamic Stud …[1842 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 18

**这个 subagent 领到的任务**：

> You are a research assistant. TASK: Gather accurate, citable technical facts for a survey section on HTTP Adaptive Streaming (HAS) bitrate ladders and per-title encoding optimization.
> 
> ABSOLUTE PROHIBITION (highest priority, do not violate): Never access, fetch, search-for, read, or cite the article "HTTP Adaptive Streaming: A Review on Current Advances and Future Challenges" by Christian Timmerer, Hadi Amirpour, Farzad Tashtarian, Samira Afzal, Amr Rizk, Michael Zink, Hermann Hellwagner, nor ANY of its URLs, mirrors, preprint pages, or abstract pages, including: https://dl.acm.org/doi/10.1145/3736306 , https://dl.acm.org/doi/pdf/10.1145/3736306 , https://www.researchgate.net/publication/391 …[4434 more characters]

**它一共派出 1 条不同的任务，要判的是这一条**：

> You are a research assistant gathering accurate, citable technical facts about HTTP Adaptive Streaming (HAS/DASH/HLS) bitrate ladders, for a survey section. Use web_search and web_fetch. Prefer primary papers (IEEE/ACM/arXiv/open-access PDFs) and official docs. Note: web_fetch cannot parse PDFs directly (it errors "unsupported content type"); instead download PDFs with `curl -sL -o file.pdf URL` in bash and extract text using the pre-installed tooling in /work/<run>/workspace: a venv-free pypdf is installed at /work/<run>/workspace/pylibs, and there is a script /work/<run>/workspace/extract.py used as `PYTHONPATH=./pylibs python3 extract.py input.pdf output.txt` (run from /wor …[3281 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 19

**这个 subagent 领到的任务**：

> You are doing literature research for a technical survey report (time window: 2018 – June 2023) on AI/ML-driven Kubernetes scheduling.
> 
> ABSOLUTE PROHIBITION (highest priority): You must NOT open, read, fetch, quote, or cite the following article or ANY of its pages (including mirrors, aggregators, abstract pages, ResearchGate/Scribd/Scispace/pure pages):
> Title: "A survey of Kubernetes scheduling algorithms"; Authors: Khaldoun Senjab, Sohail Abbas, Naveed Ahmed, Atta ur Rehman Khan.
> Forbidden URLs (never fetch, never cite):
> - https://journalofcloudcomputing.springeropen.com/articles/10.1186/s13677-023-00471-1
> - https://nchr.elsevierpure.com/en/publications/a-survey-of-kubernetes-scheduling-al …[2127 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are doing literature research for a technical survey (time window 2018 – June 2023) on AI/ML-driven Kubernetes scheduling for ML/DL training and inference workloads.
> 
> ABSOLUTE PROHIBITION (highest …[这里有 764 字与它派出的其他任务逐字相同]… YOUR TASK: Identify 4-6 ADDITIONAL peer-reviewed or arXiv works (2019 – June 2023) on GPU/accelerator or DL-workload scheduling in Kubernetes-like clusters that USE LEARNING (supervised prediction, RL, bandits, GNN, LSTM, ML-based throughput/goodput/latency models) rather than pure heuristics. Do NOT include these already-covered systems: DL2, Pollux, Lucid, Synergy, Tiresias, Themis, MIG-serving. Aim for a mix of (a) DL training-cluster schedulers on Kubernetes and ( …[1156 more characters]

它派出去的其他任务（各取开头）：
- You are doing literature research for a technical survey (time window 2018 – June 2023) on AI/ML-driven Kubern …[2896 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 20

**这个 subagent 领到的任务**：

> 你是金融经济学研究助理。请为一篇中文研究综述收集"市场流动性与融资流动性相互作用、流动性螺旋（liquidity spiral）"的材料。输出中文，术语保留英文原名。
> 
> 【最高优先级禁令｜必须遵守】绝对不要查看、下载、引用或转述以下论文及其任何转载页、摘要页、预印本页、机构页面：
> 标题：A Review of Micro-Based Systemic Risk Research from Multiple Perspectives
> 作者：Xiao Bai, Huaping Sun, Shibao Lu, Farhad Taghizadeh-Hesary
> 禁止访问的 URL：https://www.mdpi.com/1099-4300/22/7/711 ；https://pubmed.ncbi.nlm.nih.gov/33286483/ ；https://www.researchgate.net/publication/342524950_A_Review_of_Micro-Based_Systemic_Risk_Research_from_Multiple_Perspectives ；https://ui.adsabs.harvard.edu/abs/2020Entrp..22..711B/abstract ；https://www.mdpi.com/1099-4300/22/7/711/reprints ；https://researchportal.u-tokai.ac.jp/ja/publications/a-review-of-micro-based-systemic- …[2831 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> 任务：用 web_search / web_fetch 核实以下文献/文件的准确出处元数据。逐条给出"已核实/待核"和证据 URL。
> 
> 【最高优先级禁令】绝对不要查看、下载、引用或转述这篇论文及任何转载/摘要/预印本/机构页面（若搜索结果出现，跳过不点开）：
> "A Review of Micro-Based Systemic Risk Research from Multiple Perspect …[这里有 287 字与它派出的其他任务逐字相同]… 另：只采用 2020 年 3 月之前的文献/文件。
> 
> 需核实清单（优先用期刊官网 DOI 页、RePEc/ideas.repec.org、BIS/BCBS 官网、ECB 官网、NBER、作者主页）：
> 1. Amihud, Y. (2002). "Illiquidity and stock returns: cross-section and time-series effects." Journal of Financial Markets — 卷(期)、页码。
> 2. Pástor, Ľ. & Stambaugh, R. (2003). "Liquidity Risk and Expected Stock Returns." Journal of Political Economy — 卷(期)、页码。
> 3. Chordia, T., Roll, R. & Subrahmanyam, A. (2001). "Market liquidity and trading activity." Journal of Finance — 卷 …[1472 more characters]

它派出去的其他任务（各取开头）：
- 任务：用 web_search / web_fetch 核实以下文献的准确出处元数据（作者、年份、标题、期刊全名、卷(期)、页码范围）。逐条给出"已核实/待核"和证据 URL。  【最高优先级禁令】绝对不要查看、下载、引 …[1996 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 21

**这个 subagent 领到的任务**：

> 你是研究助手，负责为一份中文调研报告收集资料。报告主题：《构建有效分散风险的股票投资组合需要多少只股票？》——面向个人投资者，覆盖 1968 年至 2021 年 11 月之前的研究成果。
> 
> 【最高优先级禁令，必须遵守】
> 严禁打开、阅读、引用、转述或以任何方式使用以下文章及其任何转载页、摘要页、镜像页、PDF：
> - 标题："How Many Stocks Are Sufficient for Equity Portfolio Diversification? A Review of the Literature"
> - 作者：Azra Zaimovic, Adna Omanovic, Almira Arnaut-Berilo
> - 已知 URL：https://www.mdpi.com/1911-8074/14/11/551 ；https://ideas.repec.org/a/gam/jjrfmx/v14y2021i11p551-d679488.html ；https://www.researchgate.net/publication/356217672_How_Many_Stocks_Are_Sufficient_for_Equity_Portfolio_Diversification_A_Review_of_the_Literature
> 搜索结果里出现它就直接跳过、绝不 fetch、绝不使用其内容或其参考文献列表。必须独立检索原始文献。
> 
> 【你负责的切片：1990–2007 年美国市场的研究（方法扩展：长期持有/终端财富、个股特质波动率、个人投资者行为）】
> 请检索并核实（以及 …[1023 more characters]

**它一共派出 1 条不同的任务，要判的是这一条**：

> You are a research assistant gathering source-verified facts for a Chinese-language report on "How many stocks are needed to diversify a stock portfolio?" — specifically the slice of US-market studies from 1990–2007.
> 
> ABSOLUTE PROHIBITION (highest priority): You must NEVER open, fetch, read, cite, quote, summarize, or use in any way the article titled "How Many Stocks Are Sufficient for Equity Portfolio Diversification? A Review of the Literature" by Azra Zaimovic, Adna Omanovic, Almira Arnaut-Berilo, including these URLs and any mirror/abstract/PDF version:
> - https://www.mdpi.com/1911-8074/14/11/551
> - https://ideas.repec.org/a/gam/jjrfmx/v14y2021i11p551-d679488.html
> - https://www.researchga …[2178 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 22

**这个 subagent 领到的任务**：

> 你是技术调研 subagent，为一份中文技术综述《量子模拟器（Quantum Simulators）主流实现方案》撰写其中「分片 1」。报告整体要求反映「截至 2021 年初（约 2021 年 3 月以前）」的技术状况，因此请优先使用 2021 年 4 月以前发表的综述、论文与权威网页；若某条信息只能来自更晚的来源，请明确标注（最好避免依赖）。
> 
> 【最高优先级的禁令，必须遵守】严禁访问、检索、下载、引用或使用以下文献及其任何转载页、摘要页、镜像页、PDF 页的内容：
> 标题：Quantum Simulators: Architectures and Opportunities
> 作者：Ehud Altman, Kenneth R. Brown, Giuseppe Carleo, Lincoln D. Carr, Eugene Demler, Cheng Chin, Brian DeMarco, Sophia E. Economou, Mark A. Eriksson, Kai-Mei C. Fu, Markus Greiner, Kaden R. A. Hazzard, Randall G. Hulet, Alicia J. Kollar, Benjamin L. Lev, Mikhail D. Lukin, Ruichao Ma, Xiao Mi, Shashank Misra, Christopher Monroe, Kater Murch, Zaira Nazario, Kang-Kuen Ni, Andrew C. Potter, Pedram Roushan, Mark …[2705 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are a citation-verification assistant. Use the `web_fetch` tool (web_search is currently BROKEN and returns "No results found" — do not rely on it). 
> 
> PRIMARY TOOL: the arXiv API, e.g.
> https://exp …[这里有 1537 字与它派出的其他任务逐字相同]… Items to verify (titles may differ slightly from published titles — find the real record):
> 1. Bakr, Gillen, Peng, Fölling, Greiner — "A quantum gas microscope for detecting single atoms in a Hubbard-regime optical lattice" (Nature, 2009)
> 2. Endres et al. — "Observation of single-site-resolved ... " actually: Endres, Cheneau, Fukuhara, Weitenberg, Schauss, Gross, Mazza, Pollet, Bloch, Kuhr — "Observation of correlated particle-hole pairs and string order in low-dimens …[2772 more characters]

它派出去的其他任务（各取开头）：
- You are a citation-verification assistant. Use the `web_fetch` tool (web_search is currently BROKEN and return …[5414 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 23

**这个 subagent 领到的任务**：

> You are researching US federal AI regulatory framework 2019-2023 for a well-sourced research brief. Use web_search and web_fetch on OFFICIAL sources (whitehouse.gov, congress.gov, govinfo.gov, federalregister.gov, nist.gov, ftc.gov, omb.gov, gao.gov) and reputable analyses (Brookings, CSIS, Stanford HAI, law firm trackers like Covington/Inside Privacy, Gibson Dunn, Orrick, EPIC, Brennan Center).
> 
> HARD RULE (highest priority): Do NOT open, fetch, read, or cite this article or its URLs, mirrors, or abstract pages in any form:
> Title: "Navigating Governmental Choices: A Comprehensive Review of Artificial Intelligence's Impact on Decision-Making" by Gustavo Caiza, Verónica Sanguña, Natalia Tusa,  …[3601 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are researching US federal AI policy for a well-sourced research brief. Use web_search and web_fetch on OFFICIAL sources (whitehouse.gov, federalregister.gov, govinfo.gov, nist.gov, omb.gov, gao.gov, congress.gov) and reputable analyses (Brookings, CSIS, Stanford HAI, law firm trackers like Covington/Inside Privacy, Gibson Dunn, Orrick, EPIC, Brennan Center).
>  …[这里有 1166 字与它派出的其他任务逐字相同]… TASK: Verify exact dates, key provisions, and source URLs for these post-2023 US federal AI items:
> 1. Executive Order 14148 "Initial Rescissions of Harmful Executive Orders and Actions" (Jan 20, 2025) — confirm it rescinded EO 14110 of Oct 30, 2023; exact date; Federal Register citation if available (e.g …[1624 more characters]

它派出去的其他任务（各取开头）：
- You are researching US federal public-sector AI governance for a well-sourced research brief. Use web_search a …[4142 more characters]
- You are researching the US federal AI regulatory framework 2019-2023 for a well-sourced research brief. Use we …[4439 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 24

**这个 subagent 领到的任务**：

> Research the academic origins of the concepts "collective memory" (mémoire collective) and "social memory" (mémoire sociale), focusing on Émile Durkheim and Maurice Halbwachs.
> 
> ABSOLUTE PROHIBITION (highest priority rule): You must NOT open, fetch, read, or quote the article "Collective memory: between individual systems of consciousness and social systems" by Jean-François Orianne and Francis Eustache, nor ANY of these URLs or any mirror/reprint/abstract page of it:
> - https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1238272/full
> - https://pubmed.ncbi.nlm.nih.gov/37901083/
> - https://pmc.ncbi.nlm.nih.gov/articles/PMC10603192/
> - https://www.semanticscholar.org/paper/ …[3393 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are researching the German-language tradition of memory theory for a scholarly literature report. Use web_search and web_fetch. Prefer scholarly sources (university pages, journals, publisher pages, encyclopedias).
>  …[这里有 757 字与它派出的其他任务逐字相同]… Jan Assmann's "Das kulturelle Gedächtnis: Schrift, Erinnerung und politische Identität in frühen Hochkulturen" (C.H. Beck, 1992): what is the thesis, what is "kulturelles Gedächtnis", and how does it relate to Maurice Halbwachs's "mémoire collective"? Find the exact place/way Assmann credits Halbwachs. Also Jan Assmann's earlier essay with Aleida Assmann and his 1988 essay "Kollektives Gedächtnis und kulturelle Identität" (in "Kultur und Gedächtnis" …[1816 more characters]

它派出去的其他任务（各取开头）：
- You are researching the Anglophone history of the terms "collective memory" and "social memory" for a scholarl …[4466 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 25

**这个 subagent 领到的任务**：

> You are researching for a literature review on Intelligent Tutoring Systems (ITS) in K-12 education, focused on empirical studies published 2009–2024. You have web_search and web_fetch tools.
> 
> ABSOLUTE PROHIBITION — you must NEVER open, fetch, search for, or cite this article or any of its republication/abstract pages:
> Title: "A systematic review of AI-driven intelligent tutoring systems (ITS) in K-12 education"
> Authors: Angélique Létourneau, Marion Deslandes Martineau, Patrick Charland, John Alexander Karran, Jared Boasen, Pierre Majorique Léger
> Forbidden URLs: https://www.nature.com/articles/s41539-025-00320-7 and https://www.researchgate.net/publication/391755170_A_systematic_review_of_AI …[3069 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are supporting a literature review on Intelligent Tutoring Systems (ITS) in K-12 education, empirical studies 2009-2024. You have web_search and web_fetch tools. Work only from sources you actuall …[这里有 860 字与它派出的其他任务逐字相同]… (1) GEOGRAPHIC DISTRIBUTION: which countries produce the most K-12 ITS empirical research? Find systematic reviews / bibliometric studies reporting country counts or percentages of primary studies (e.g., USA dominant, then China/Taiwan, UK, Netherlands, Germany, Canada, Turkey, Greece, India, Singapore, Spain, Brazil, etc.). Good candidate sources to check: Mousavinasab et al. (2021) "Intelligent tutoring systems: a systematic review of characteristics, applications,  …[1363 more characters]

它派出去的其他任务（各取开头）：
- You are supporting a literature review on Intelligent Tutoring Systems (ITS) in K-12 education, empirical stud …[3315 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 26

**这个 subagent 领到的任务**：

> You are doing research for a market report on solid-state batteries (SSBs), with information current as of end-2023.
> 
> ABSOLUTE PROHIBITION (highest priority rule): You must NEVER open, fetch, view, or cite the following article or ANY of its mirrors, reprint pages, abstract pages, indexing pages, or aggregator pages:
> Title: "Technological Advances and Market Developments of Solid-State Batteries: A Review"
> Authors: Felix Thomas, Lauren Mahdi, Julien Lemaire, Diogo M. F. Santos
> Prohibited URLs (do not fetch, do not cite, do not search for them):
> - https://www.mdpi.com/1996-1944/17/1/239
> - https://www.mdpi.com/1996-1944/17/1/239/reprints
> - https://www.researchgate.net/publication/377061990_Tec …[2476 more characters]

**它一共派出 3 条不同的任务，要判的是这一条**：

> You are researching SULFIDE-electrolyte solid-state battery developers for a market report with information current as of END-2023 (you may note later publicly announced plans, but clearly date them). …[这里有 1010 字与它派出的其他任务逐字相同]… YOUR SCOPE: Korean companies and institutions developing SULFIDE-based solid-state batteries/electrolytes. Cover at minimum:
> - Samsung SDI (Suwon pilot line / "S-Line", sulfide, Ag/Li anode-free, 900 Wh/L)
> - LG Energy Solution (sulfide, 2030 mass production target)
> - SK On (sulfide, partnership with Solid Power? Solid Energy? Factorial?)
> - Hyundai Motor / Kia (joint development, pilot line, Uiwang research center)
> - POSCO Holdings / POSCO JK Solid Solution (포스코JK솔리드솔 …[1504 more characters]

它派出去的其他任务（各取开头）：
- You are researching SULFIDE-electrolyte solid-state battery (全固态电池) developers for a market report with inform …[3110 more characters]
- You are researching SULFIDE-electrolyte solid-state battery developers for a market report with information cu …[4076 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 27

**这个 subagent 领到的任务**：

> 你是一名研究助理，参与一份中文技术综述《量子模拟器（Quantum Simulators）技术综述》的撰写，内容反映截至 2021 年 3 月左右的状态（尽量只用 2021 年 3 月及以前的资料）。
> 
> 【最高优先级禁令，必须严格遵守】绝对不要打开、抓取、搜索、引用或转述论文《Quantum Simulators: Architectures and Opportunities》（Ehud Altman 等）及其任何转载页、摘要页、镜像页。禁止访问的 URL（含任意变体）：https://arxiv.org/abs/1912.06938 ；https://link.aps.org/doi/10.1103/PRXQuantum.2.017003 ；https://www.researchgate.net/publication/360393483_Quantum_Simulators_Architectures_and_Opportunities ；https://profiles.wustl.edu/en/publications/quantum-simulators-architectures-and-opportunities ；https://knowledge.uchicago.edu/record/13089 ；https://inspirehep.net/literature/1771054 ；https://scispace.com/papers/quantum-simulators-architectures-and-opportunities-39u96xcy …[1253 more characters]

**它一共派出 1 条不同的任务，要判的是这一条**：

> You are a research fact-checker. I need you to verify specific bibliographic and numerical facts about photonic quantum simulation experiments, using web_search and web_fetch on primary sources (arXiv abstracts, journal pages, PubMed, Semantic Scholar/OpenAlex APIs).
> 
> ABSOLUTE PROHIBITION: Never open, fetch, search for, cite, or paraphrase the paper "Quantum Simulators: Architectures and Opportunities" (Ehud Altman et al., PRX Quantum 2, 017003). Do not visit these URLs or any variant: https://arxiv.org/abs/1912.06938 , https://link.aps.org/doi/10.1103/PRXQuantum.2.017003 , https://www.researchgate.net/publication/360393483_Quantum_Simulators_Architectures_and_Opportunities , https://profile …[3352 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 28

**这个 subagent 领到的任务**：

> 你是一名研究助理，正在参与撰写一份中文技术综述报告《量子系统自测试（self-testing）技术综述》，时间截止到 2020 年 9 月。报告由 8 个并行的子任务完成，你负责【第 1 部分：基本概念与理论基础】。
> 
> 【最高优先级禁令（不可违反）】严禁打开、阅读、参考、引用或转述以下文献及其任何转载页、摘要页、HTML 版本、镜像页、聚合站页面：《Self-testing of quantum systems: a review》，作者 Ivan Šupić 与 Joseph Bowles。禁止访问的 URL：
> - https://arxiv.org/abs/1904.10042
> - https://quantum-journal.org/papers/q-2020-09-30-337/
> - https://www.researchgate.net/publication/350646502_Self-testing_of_quantum_systems_a_review
> - https://ui.adsabs.harvard.edu/abs/2020Quant...4..337S/abstract
> - https://inspirehep.net/literature/1730930
> - https://ar5iv.labs.arxiv.org/html/1904.10042
> - https://ouci.dntb.gov.ua/en/works/7ALqvWP9/
> 如果搜索结果里出现上述 URL，直接跳过，绝不 web_fetch；也不要把它列进参考文献。注意：Šupić …[2223 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are verifying bibliographic references for a Chinese technical survey on quantum self-testing (deadline: works published on or before 2020-09-30).
> 
> *** ABSOLUTE PROHIBITION (do not violate) ***
> Yo …[这里有 707 字与它派出的其他任务逐字相同]… YOUR TASK: verify the exact bibliographic details (authors, year, journal, volume, page/article number, and arXiv ID if it exists) for the following works.  …[这里有 55 字与它派出的其他任务逐字相同]… pages, journal DOI pages, publisher pages, university pages). If you cannot confirm something, say "UNVERIFIED" rather than guessing.
> 
> 1. Summers, S. J. & Werner, R. "Maximal violation of Bell's inequalities is generic in quantum field theory", Communications in Mathematical Physics, 110  …[1766 more characters]

它派出去的其他任务（各取开头）：
- You are verifying bibliographic references for a Chinese technical survey on quantum self-testing (deadline: w …[4114 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 29

**这个 subagent 领到的任务**：

> You are researching US federal public-sector AI governance for a well-sourced research brief. Use web_search and web_fetch on OFFICIAL sources (gao.gov, whitehouse.gov, omb.gov, nist.gov, acquisition.gov, ai.gov, govinfo.gov, federalregister.gov) and reputable analyses (Brookings, CSIS, Stanford HAI, law firm trackers like Covington/Inside Privacy, Gibson Dunn, Orrick, EPIC, Brennan Center).
> 
> HARD RULE (highest priority): Do NOT open, fetch, read, or cite the article titled "Navigating Governmental Choices: A Comprehensive Review of Artificial Intelligence's Impact on Decision-Making" by Gustavo Caiza, Verónica Sanguña, Natalia Tusa, Violeta Masaquiza, Alexandra Ortiz, Marcelo V. Garcia, or  …[3552 more characters]

**它一共派出 2 条不同的任务，要判的是这一条**：

> You are researching US federal public-sector AI governance for a well-sourced research brief. Use web_search and web_fetch on OFFICIAL sources (nist.gov, whitehouse.gov, omb.gov, gao.gov, ai.gov, govi …[这里有 179 字与它自己领到的任务逐字相同]…  …[这里有 89 字与它派出的其他任务逐字相同]… federalregister.gov redirects cross-origin to unblock.federalregister.gov and the tool will not follow it — instead use govinfo.gov HTML Federal Register pages (https://www.govinfo.gov/content/pkg/FR-YYYY-MM-DD/html/YYYY-NNNNN.htm) and/or the federalregister.gov API (https://www.federalregister.gov/api/v1/documents/<doc-number>.json) which may work.
>  …[这里有 117 字与它派出的其他任务逐字相同]… nist.gov publication landing pages (e.g. https://www.nist.gov/pub …[2227 more characters]

它派出去的其他任务（各取开头）：
- You are researching US federal public-sector AI governance for a well-sourced research brief. Use web_search a …[4399 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---

## 条目 30

**这个 subagent 领到的任务**：

> You are doing research for a technical survey report (time window: 2018 – June 2023) on AI/ML-driven Kubernetes scheduling.
> 
> ABSOLUTE PROHIBITION (highest priority): You must NOT open, read, fetch, quote, or cite the following article or ANY of its pages (mirrors, aggregators, abstract pages, ResearchGate/Scribd/Scispace/Elsevier Pure pages):
> Title: "A survey of Kubernetes scheduling algorithms"; Authors: Khaldoun Senjab, Sohail Abbas, Naveed Ahmed, Atta ur Rehman Khan.
> Forbidden URLs (never fetch, never cite):
> - https://journalofcloudcomputing.springeropen.com/articles/10.1186/s13677-023-00471-1
> - https://nchr.elsevierpure.com/en/publications/a-survey-of-kubernetes-scheduling-algorithms
> - h …[2085 more characters]

**它一共派出 4 条不同的任务，要判的是这一条**：

> You are researching for a technical survey report (time window 2018 – June 2023) on AI/ML-driven Kubernetes scheduling.
> 
> ABSOLUTE PROHIBITION (highest priority): You must NOT open, read, fetch, quote, …[这里有 872 字与它派出的其他任务逐字相同]… If you find the ACM Computing Surveys / other survey with the same or similar title by different authors, that is fine to use — but verify authorship.
> 
> YOUR SCOPE: Find 4-6 credible surveys / systematic literature reviews / taxonomies / benchmark studies published between 2018 and June 2023 on ML-based / AI-based container and Kubernetes scheduling. They must be EXCLUDING the prohibited article above. Prefer peer-reviewed venues (ACM Computing Surveys, IEEE Access, IE …[2084 more characters]

它派出去的其他任务（各取开头）：
- You are researching for a technical survey report (time window 2018 – June 2023) on AI/ML-driven Kubernetes sc …[3610 more characters]
- You are researching for a technical survey report (time window 2018 – June 2023) on AI/ML-driven Kubernetes sc …[4203 more characters]
- You are researching for a technical survey report (time window 2018 – June 2023) on AI/ML-driven Kubernetes sc …[3496 more characters]

[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准

---
