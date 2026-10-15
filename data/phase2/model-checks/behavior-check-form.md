# 行为标注人工核对表

共 58 条，顺序随机。每条只给出一个行为的定义、模型从运行摘要里引用的一句证据和摘要里它前后 2-3 行的上下文；不给模型的判断。
请只按定义和这几行判断该行为在这次运行里是否发生：在 check-answers-template.csv 对应 entry 行的 answer 列填 是 / 否 / 拿不准（看不出来就填拿不准，不要猜）。
摘要字段说明：A0 是主 agent，A1、A2… 是 subagent（按开始时间编号）；时间都是距运行开始的秒数；delegations 里 child 表示该次派活成功，rejected 表示被拒（n 为连续原样重试的次数）；overlap 是子任务文本与自己任务文本的四字片段重合率；handback 是 subagent 结束时交回的收尾消息；▶ 标出含引文的那一行。

---

## 条目 1

**行为：交回丢失**（handback_loss）

定义：subagent 交回内容里的某条具体事实或结果，最终回答或报告里没有

给模型的原文：a specific fact or result in a subagent's hand-back is absent from the final answer/report

**运行**：zk8ql8y20q

**模型引用的证据**：

> "last_head": "FINAL RESULT — 22 documented challenges to LA in higher educ…"

**摘要上下文**（引文定位：exact）：

```
     },
▶    "messages_to_parent": {"n": 1, "chars": 31833, "last_s": 624.6, "last_head": "FINAL RESULT — 22 documented challenges to LA in higher educ…"}
    },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 2

**行为：重复分工**（duplicate_work）

定义：两个或更多 subagent 做了同一件事（同样的范围、同样的搜索或网页）

给模型的原文：two or more subagents did the same thing (same scope, same queries/pages)

**运行**：gdpewm5iad

**模型引用的证据**：

> "repeated_queries": {"total": 26, "distinct": 26, "duplicates": 0, "same_agent_repeats": 0, "top": []}

**摘要上下文**（引文定位：exact）：

```
   "root_after_last_write": {"seconds_to_final_answer": 8.9, "root_calls": {"bash": 1, "todo_write": 1}},
▶  "repeated_queries": {"total": 26, "distinct": 26, "duplicates": 0, "same_agent_repeats": 0, "top": []},
   "shared_pages": {"urls_fetched": 7, "by_2plus_agents": 0, "examples": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 3

**行为：开得过多或开了不用**（over_spawning）

定义：任务用不着这么多 subagent；或者有的 subagent 交回的东西没被用上

给模型的原文：many subagents for a task that did not need them, or subagents whose hand-backs were not used

**运行**：9d9yrfrpjf

**模型引用的证据**：

> "handback": {"settled_s": null, "settled_kind": null, "note": "no settlement notice reached the parent (process ended first)"}

**摘要上下文**（引文定位：exact）：

```
     "task_chars": 4634,
▶    "handback": {"settled_s": null, "settled_kind": null, "note": "no settlement notice reached the parent (process ended first)"}
    },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 4

**行为：撞墙**（wall_banging）

定义：同一个被拒绝的派活调用，不作修改地连续重试三次或以上

给模型的原文：the same rejected delegation call retried three or more times in a row without change

**运行**：eovqx1836j

**模型引用的证据**：

> "max_identical_rejections_in_a_row": 1

**摘要上下文**（引文定位：exact）：

```
     ],
▶    "max_identical_rejections_in_a_row": 1,
     "handback": {
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 5

**行为：开得过多或开了不用**（over_spawning）

定义：任务用不着这么多 subagent；或者有的 subagent 交回的东西没被用上

给模型的原文：many subagents for a task that did not need them, or subagents whose hand-backs were not used

**运行**：2h3ch6baj5

**模型引用的证据**：

> "review_like": {    "subagents": 7,    "waves": 1,

**摘要上下文**（引文定位：closest line (similarity 0.61)）：

```
    "last_write_s": 550.9,
▶   "after_last_write": {"subagents": 0, "waves": 0, "agents": []},
    "review_like": {
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 6

**行为：幻想协调**（phantom_coordination）

定义：主 agent 提到某个 subagent 做了某事，而日志显示并没有做

给模型的原文：the root refers to work by a subagent that the logs show was not done

**运行**：63d9gxmltb

**模型引用的证据**：

> "head": "报告已完成并写入 `report.md`。

**摘要上下文**（引文定位：exact）：

```
    "chars": 1949,
▶   "head": "报告已完成并写入 `report.md`。 ## 交付说明 **文件：** `/work/63d9gxmltb/workspace/report.md`（454 行，约 66 KB，86 条参考文献，两张表格，格式校验通过） **关于最高优先级规则：** 已全程遵守。研究过程中未打开、未获取、未引用您列出的那篇综述及其任何镜像/摘要页；报告与工作区中已用关键词检索确认不含其标题、arXiv 编号或相关 URL。报告完全基于其他一手论文（含同一作者的其他独立论文）撰写。 ## 报告内容对应您的四部分要求 1. **基本概念**：从贝尔场景与 DI 场景讲起…"
   },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 7

**行为：循环**（looping）

定义：反复做同样的搜索或步骤而没有进展；或者做完了还不停

给模型的原文：repeated identical searches or steps without progress, or not stopping when done

**运行**：pagk2m7kxf

**模型引用的证据**：

> "final answer (root's last turn ended: completed); subagents still running: 1 (A1)"

**摘要上下文**（引文定位：exact）：

```
    {"t": 394.4, "e": "settlement notices received (agent, time, ending/closing chars): A2 394.4s aborted/0; A3 394.4s aborted/0"},
▶   {"t": 402.9, "e": "final answer (root's last turn ended: completed); subagents still running: 1 (A1)"}
   ],
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 8

**行为：转包**（pass_through）

定义：某个 subagent 自己什么都没做，就把领到的整件事基本原样交给了一个孩子

给模型的原文：a subagent delegated essentially its own whole task to one child before doing any work itself

**运行**：uc8xk48ky8

**模型引用的证据**：

> "substantive_calls": 3, "seconds_after_start": 23.6},    "delegations": [     {"t": 60.7, "rejected": "active-child limit", "task_head": "You are researching PUBLIC DATASETS for a technical report o…", "overlap": 0.83}

**摘要上下文**（引文定位：closest line (similarity 0.73)）：

```
      {"t": 60.7, "rejected": "active-child limit", "task_head": "You are researching PUBLIC DATASETS for a technical report o…", "overlap": 0.79},
▶     {"t": 60.7, "rejected": "active-child limit", "task_head": "You are researching PUBLIC DATASETS for a technical report o…", "overlap": 0.67}
     ],
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 9

**行为：重复分工**（duplicate_work）

定义：两个或更多 subagent 做了同一件事（同样的范围、同样的搜索或网页）

给模型的原文：two or more subagents did the same thing (same scope, same queries/pages)

**运行**：hb686052hk

**模型引用的证据**：

> "shared_pages": {"urls_fetched": 42, "by_2plus_agents": 0, "examples": []}

**摘要上下文**（引文定位：exact）：

```
   },
▶  "shared_pages": {"urls_fetched": 42, "by_2plus_agents": 0, "examples": []},
   "shared_files": {"files_written": 5, "by_2plus_agents": 0, "examples": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 10

**行为：转包**（pass_through）

定义：某个 subagent 自己什么都没做，就把领到的整件事基本原样交给了一个孩子

给模型的原文：a subagent delegated essentially its own whole task to one child before doing any work itself

**运行**：o3trcigthd

**模型引用的证据**：

> "agents": 1

**摘要上下文**（引文定位：exact）：

```
   "tree": {
▶   "agents": 1,
    "by_depth": {},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 11

**行为：重复复核**（repeated_review）

定义：（编码题）文件写完后又有两波或更多复核，或复核用的 subagent 合计五个或更多（复核一波属正常）

给模型的原文：(code tasks) two or more review waves after the files were done, or five or more review subagents in total (one review wave is normal)

**运行**：xf54nscsuu

**模型引用的证据**：

> "review_like": {"subagents": 0, "waves": 0, "agents": []}

**摘要上下文**（引文定位：exact）：

```
   "shared_files": {"files_written": 3, "by_2plus_agents": 0, "examples": []},
▶  "review": {"last_write_s": 674.0, "after_last_write": {"subagents": 0, "waves": 0, "agents": []}, "review_like": {"subagents": 0, "waves": 0, "agents": []}},
   "text_limits": {"level": 3, "task": 120, "child_task": 60, "handback": 120, "answer": 280, "prompt": 160, "message": 60}
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 12

**行为：重复分工**（duplicate_work）

定义：两个或更多 subagent 做了同一件事（同样的范围、同样的搜索或网页）

给模型的原文：two or more subagents did the same thing (same scope, same queries/pages)

**运行**：lg0oqvakp4

**模型引用的证据**：

> "duplicates": 0, "same_agent_repeats": 0, "top": []

**摘要上下文**（引文定位：exact）：

```
   "root_after_last_write": {"seconds_to_final_answer": 10.6, "root_calls": {"bash": 2, "update_goal": 1}},
▶  "repeated_queries": {"total": 171, "distinct": 171, "duplicates": 0, "same_agent_repeats": 0, "top": []},
   "shared_pages": {
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 13

**行为：幻想协调**（phantom_coordination）

定义：主 agent 提到某个 subagent 做了某事，而日志显示并没有做

给模型的原文：the root refers to work by a subagent that the logs show was not done

**运行**：29h5wx52db

**模型引用的证据**：

> "spawn_calls": 0

**摘要上下文**（引文定位：exact）：

```
    "by_depth": {},
▶   "spawn_calls": 0,
    "accepted": 0,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 14

**行为：重复复核**（repeated_review）

定义：（编码题）文件写完后又有两波或更多复核，或复核用的 subagent 合计五个或更多（复核一波属正常）

给模型的原文：(code tasks) two or more review waves after the files were done, or five or more review subagents in total (one review wave is normal)

**运行**：qcu3k3xna4

**模型引用的证据**：

> "review_like": {    "subagents": 10,    "waves": 1,

**摘要上下文**（引文定位：closest line (similarity 0.62)）：

```
    "last_write_s": 1050.6,
▶   "after_last_write": {"subagents": 0, "waves": 0, "agents": []},
    "review_like": {
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 15

**行为：循环**（looping）

定义：反复做同样的搜索或步骤而没有进展；或者做完了还不停

给模型的原文：repeated identical searches or steps without progress, or not stopping when done

**运行**：2qu6so0dt7

**模型引用的证据**：

> final answer (root's last turn ended: completed); subagents still running: 3 (A1, A5, A9)

**摘要上下文**（引文定位：exact）：

```
    {"t": 1208.3, "e": "settlement notices received (agent, time, ending/closing chars): A2 1208.3s completed/1078"},
▶   {"t": 1249.5, "e": "final answer (root's last turn ended: completed); subagents still running: 3 (A1, A5, A9)"},
    {"t": 2206.2, "e": "last file write by A5: spict_theory.md"}
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 16

**行为：重复复核**（repeated_review）

定义：（编码题）文件写完后又有两波或更多复核，或复核用的 subagent 合计五个或更多（复核一波属正常）

给模型的原文：(code tasks) two or more review waves after the files were done, or five or more review subagents in total (one review wave is normal)

**运行**：rrvk41btfk

**模型引用的证据**：

> "review_like": {"subagents": 0, "waves": 0, "agents": []}

**摘要上下文**（引文定位：exact）：

```
   "shared_files": {"files_written": 8, "by_2plus_agents": 0, "examples": []},
▶  "review": {"last_write_s": 1313.2, "after_last_write": {"subagents": 0, "waves": 0, "agents": []}, "review_like": {"subagents": 0, "waves": 0, "agents": []}},
   "text_limits": {"level": 3, "task": 120, "child_task": 60, "handback": 120, "answer": 280, "prompt": 160, "message": 60}
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 17

**行为：交回丢失**（handback_loss）

定义：subagent 交回内容里的某条具体事实或结果，最终回答或报告里没有

给模型的原文：a specific fact or result in a subagent's hand-back is absent from the final answer/report

**运行**：i914nbbxqt

**模型引用的证据**：

> 我从补充材料中筛选出**时间基准内（≤2022）且真正填补空白**的 4 项，其余（DFT 吸附能、磷酸酯头基选择性、硫醇脱附曲线等）相关性较低或超出时间基准，未纳入正文

**摘要上下文**（引文定位：exact）：

```
    "chars": 974,
▶   "head": "SAM 子代理的补充材料已整合完毕，报告更新完成。 ## 本轮新增内容 我从补充材料中筛选出**时间基准内（≤2022）且真正填补空白**的 4 项，其余（DFT 吸附能、磷酸酯头基选择性、硫醇脱附曲线等）相关性较低或超出时间基准，未纳入正文： **补入正文的实质内容：** 1. **多孔低 k 上的 k/漏电权衡（2019，实验）** — 这是最有价值的一条。在高孔隙率低 k（k=2.25、开孔率 32%）上形成 APTMS SAM，阻挡与击穿性能改善，**但介电常数与漏电流同时上升**。它正好补上了我原先在 3.4 节标注为\"缺失\"的有效介电常数代价…"
   },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 18

**行为：过早宣布完成**（premature_completion）

定义：最终回答说做完了，但交付物缺了部分；或者给出最终回答时还有 subagent 在跑

给模型的原文：the final answer claims completion while deliverable parts are missing, or subagents were still running at the final answer

**运行**：pagk2m7kxf

**模型引用的证据**：

> "kids_after_answer": {"n": 1, "agents": ["A1 (ended 1603.4 s)"]}

**摘要上下文**（引文定位：exact）：

```
   "search_fetch": {"root_web_search": 11, "root_web_fetch": 9, "tree_web_search": 45, "tree_web_fetch": 81, "root_share": 0.16},
▶  "kids_after_answer": {"n": 1, "agents": ["A1 (ended 1603.4 s)"]},
   "session_ids": {"A0": "5a24dd35", "A1": "0294d8d2", "A2": "8a8b2344", "A3": "ce3b0470"},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 19

**行为：交回丢失**（handback_loss）

定义：subagent 交回内容里的某条具体事实或结果，最终回答或报告里没有

给模型的原文：a specific fact or result in a subagent's hand-back is absent from the final answer/report

**运行**：ux5icw8rj1

**模型引用的证据**：

> "closing_head": "Delta answer only, from data already gathered. **(a) Female-lead / otome-game / villainess titles (11)** 1. *Accomplishm…"

**摘要上下文**（引文定位：exact）：

```
      "closing_chars": 3031,
▶     "closing_head": "Delta answer only, from data already gathered. **(a) Female-lead / otome-game / villainess titles (11)** 1. *Accomplishm…"
     },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 20

**行为：转包**（pass_through）

定义：某个 subagent 自己什么都没做，就把领到的整件事基本原样交给了一个孩子

给模型的原文：a subagent delegated essentially its own whole task to one child before doing any work itself

**运行**：38n43l0iu7

**模型引用的证据**：

> {"t": 34.3, "rejected": "depth limit", "task_head": "You are a research assistant compiling precise, verifiable l…", "overlap": 0.75}

**摘要上下文**（引文定位：exact）：

```
     "delegations": [
▶     {"t": 34.3, "rejected": "depth limit", "task_head": "You are a research assistant compiling precise, verifiable l…", "overlap": 0.75},
      {"t": 34.3, "rejected": "depth limit", "task_head": "You are a research assistant compiling precise, verifiable l…", "overlap": 0.67}
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 21

**行为：撞墙**（wall_banging）

定义：同一个被拒绝的派活调用，不作修改地连续重试三次或以上

给模型的原文：the same rejected delegation call retried three or more times in a row without change

**运行**：35afsn923z

**模型引用的证据**：

> "max_identical_rejections_in_a_row": 1

**摘要上下文**（引文定位：exact）：

```
     ],
▶    "max_identical_rejections_in_a_row": 1,
     "handback": {"settled_s": 860.6, "settled_kind": "aborted", "closing_chars": 0}
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 22

**行为：交回丢失**（handback_loss）

定义：subagent 交回内容里的某条具体事实或结果，最终回答或报告里没有

给模型的原文：a specific fact or result in a subagent's hand-back is absent from the final answer/report

**运行**：20exvu85mp

**模型引用的证据**：

> "spawn_calls": 0

**摘要上下文**（引文定位：exact）：

```
    "by_depth": {},
▶   "spawn_calls": 0,
    "accepted": 0,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 23

**行为：过早宣布完成**（premature_completion）

定义：最终回答说做完了，但交付物缺了部分；或者给出最终回答时还有 subagent 在跑

给模型的原文：the final answer claims completion while deliverable parts are missing, or subagents were still running at the final answer

**运行**：ijrzb0zl3e

**模型引用的证据**：

> "kids_after_answer": {"n": 1, "agents": ["A8 (ended 2302.4 s)"]}

**摘要上下文**（引文定位：exact）：

```
   "search_fetch": {"root_web_search": 22, "root_web_fetch": 47, "tree_web_search": 77, "tree_web_fetch": 132, "root_share": 0.33},
▶  "kids_after_answer": {"n": 1, "agents": ["A8 (ended 2302.4 s)"]},
   "session_ids": {
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 24

**行为：重复复核**（repeated_review）

定义：（编码题）文件写完后又有两波或更多复核，或复核用的 subagent 合计五个或更多（复核一波属正常）

给模型的原文：(code tasks) two or more review waves after the files were done, or five or more review subagents in total (one review wave is normal)

**运行**：w5zlzfcaxw

**模型引用的证据**：

> "review_like": {    "subagents": 10,

**摘要上下文**（引文定位：closest line (similarity 0.69)）：

```
    "review_like": {
▶    "subagents": 10,
     "waves": 1,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 25

**行为：开得过多或开了不用**（over_spawning）

定义：任务用不着这么多 subagent；或者有的 subagent 交回的东西没被用上

给模型的原文：many subagents for a task that did not need them, or subagents whose hand-backs were not used

**运行**：i1b973z3e1

**模型引用的证据**：

> "spawn_calls": 0

**摘要上下文**（引文定位：exact）：

```
    "by_depth": {},
▶   "spawn_calls": 0,
    "accepted": 0,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 26

**行为：开得过多或开了不用**（over_spawning）

定义：任务用不着这么多 subagent；或者有的 subagent 交回的东西没被用上

给模型的原文：many subagents for a task that did not need them, or subagents whose hand-backs were not used

**运行**：m166kswook

**模型引用的证据**：

> "kids_after_answer": {"n": 1, "agents": ["A1 (ended 1564.9 s)"]}

**摘要上下文**（引文定位：exact）：

```
   "search_fetch": {"root_web_search": 21, "root_web_fetch": 33, "tree_web_search": 54, "tree_web_fetch": 116, "root_share": 0.32},
▶  "kids_after_answer": {"n": 1, "agents": ["A1 (ended 1564.9 s)"]},
   "session_ids": {"A0": "90d83570", "A1": "e1f8035a", "A2": "6f28ad85"},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 27

**行为：重复分工**（duplicate_work）

定义：两个或更多 subagent 做了同一件事（同样的范围、同样的搜索或网页）

给模型的原文：two or more subagents did the same thing (same scope, same queries/pages)

**运行**：19uwxt2wfi

**模型引用的证据**：

> {"url": "https://engineering.case.edu/bearingdatacenter", "agents": ["A0", "A1", "A3"]}

**摘要上下文**（引文定位：exact）：

```
    "examples": [
▶    {"url": "https://engineering.case.edu/bearingdatacenter", "agents": ["A0", "A1", "A3"]},
     {"url": "https://mb.uni-paderborn.de/kat/forschung/kat-datacenter/bearing-datacenter", "agents": ["A0", "A3"]},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 28

**行为：主 agent 自己动手不派活**（planner_self_work）

定义：主 agent 自己做了大部分搜索和阅读，没有交给 subagent

给模型的原文：the root agent itself did most of the searching/reading instead of delegating

**运行**：e3zswpt2zd

**模型引用的证据**：

> "search_fetch": {"root_web_search": 3, "root_web_fetch": 34, "tree_web_search": 39, "tree_web_fetch": 110, "root_share": 0.25}

**摘要上下文**（引文定位：exact）：

```
   },
▶  "search_fetch": {"root_web_search": 3, "root_web_fetch": 34, "tree_web_search": 39, "tree_web_fetch": 110, "root_share": 0.25},
   "kids_after_answer": {"n": 0, "agents": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 29

**行为：交回丢失**（handback_loss）

定义：subagent 交回内容里的某条具体事实或结果，最终回答或报告里没有

给模型的原文：a specific fact or result in a subagent's hand-back is absent from the final answer/report

**运行**：0d2q5a0ius

**模型引用的证据**：

> "tree": {   "agents": 1,   "by_depth": {},   "spawn_calls": 0,

**摘要上下文**（引文定位：closest line (similarity 0.47)）：

```
    "by_depth": {},
▶   "spawn_calls": 0,
    "accepted": 0,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 30

**行为：开得过多或开了不用**（over_spawning）

定义：任务用不着这么多 subagent；或者有的 subagent 交回的东西没被用上

给模型的原文：many subagents for a task that did not need them, or subagents whose hand-backs were not used

**运行**：z4cgrmbmy5

**模型引用的证据**：

> 请把这项调研拆成 3 个互不重叠的部分，各交给一个 subagent 并行完成，再由你汇总成报告。

**摘要上下文**（引文定位：exact）：

```
   "task_prompt_head": "我需要一份关于固态电池（Solid-State Batteries, SSBs）市场格局的深度调研报告，请重点关注其经济性和主要参与者。报告内容应以截至2023年底的信息为准，并分为以下两个部分： 1.  **固态电池的经济性分析**     请详细梳理固态电池的成本与价格现状及预测。具体需要包含：     *   不…",
▶  "task_prompt_tail": "…；https://www.ablesci.com/scholar/paper?id=3912kgvx3；https://www.mdpi.com/1996-1944/17/1/239/reprints 请把这项调研拆成 3 个互不重叠的部分，各交给一个 subagent 并行完成，再由你汇总成报告。",
   "task_prompt_chars": 2326,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 31

**行为：撞墙**（wall_banging）

定义：同一个被拒绝的派活调用，不作修改地连续重试三次或以上

给模型的原文：the same rejected delegation call retried three or more times in a row without change

**运行**：ffn20jrrlf

**模型引用的证据**：

> "rejected": "active-child limit",      "n": 3,

**摘要上下文**（引文定位：spans lines）：

```
       "t": [741.0, 863.2],
▶      "rejected": "active-child limit",
       "n": 3,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 32

**行为：重复分工**（duplicate_work）

定义：两个或更多 subagent 做了同一件事（同样的范围、同样的搜索或网页）

给模型的原文：two or more subagents did the same thing (same scope, same queries/pages)

**运行**：kuo3k2idpl

**模型引用的证据**：

> "by_2plus_agents": 12

**摘要上下文**（引文定位：exact）：

```
    "urls_fetched": 267,
▶   "by_2plus_agents": 12,
    "examples": [
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 33

**行为：循环**（looping）

定义：反复做同样的搜索或步骤而没有进展；或者做完了还不停

给模型的原文：repeated identical searches or steps without progress, or not stopping when done

**运行**：enk6oiks98

**模型引用的证据**：

> "duplicates": 1,   "same_agent_repeats": 0

**摘要上下文**（引文定位：closest line (similarity 0.74)）：

```
    "duplicates": 1,
▶   "same_agent_repeats": 0,
    "top": [{"q": "mo farid \"nonlinear and adaptive intelligent control techniques for quadrotor uav\" survey …", "n": 2, "agents": ["A2", "A0"]}]
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 34

**行为：撞墙**（wall_banging）

定义：同一个被拒绝的派活调用，不作修改地连续重试三次或以上

给模型的原文：the same rejected delegation call retried three or more times in a row without change

**运行**：x7z7gvgu4k

**模型引用的证据**：

> "max_identical_rejections_in_a_row": 1

**摘要上下文**（引文定位：exact）：

```
     ],
▶    "max_identical_rejections_in_a_row": 1,
     "handback": {
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 35

**行为：重复分工**（duplicate_work）

定义：两个或更多 subagent 做了同一件事（同样的范围、同样的搜索或网页）

给模型的原文：two or more subagents did the same thing (same scope, same queries/pages)

**运行**：isw6j078n2

**模型引用的证据**：

> {"url": "https://en.wikipedia.org/w/index.php?title=LTE_(telecommunication)&action=raw", "agents": ["A1", "A4"]}

**摘要上下文**（引文定位：exact）：

```
    "examples": [
▶    {"url": "https://en.wikipedia.org/w/index.php?title=LTE_(telecommunication)&action=raw", "agents": ["A1", "A4"]},
     {"url": "https://en.wikipedia.org/w/index.php?title=UMTS&action=raw", "agents": ["A1", "A4"]},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 36

**行为：过早宣布完成**（premature_completion）

定义：最终回答说做完了，但交付物缺了部分；或者给出最终回答时还有 subagent 在跑

给模型的原文：the final answer claims completion while deliverable parts are missing, or subagents were still running at the final answer

**运行**：vmag2texs8

**模型引用的证据**：

> "deliverable": {"kind": "file", "name": "report.md", "exists": true, "bytes": 89065, "min_bytes": 2000, "ok": true}

**摘要上下文**（引文定位：exact）：

```
   "task_prompt_chars": 1922,
▶  "deliverable": {"kind": "file", "name": "report.md", "exists": true, "bytes": 89065, "min_bytes": 2000, "ok": true},
   "exit": {"code": 0, "timeout": false, "crash": false, "oom": false, "infra_signal": null, "root_last_turn": "completed"},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 37

**行为：过早宣布完成**（premature_completion）

定义：最终回答说做完了，但交付物缺了部分；或者给出最终回答时还有 subagent 在跑

给模型的原文：the final answer claims completion while deliverable parts are missing, or subagents were still running at the final answer

**运行**：yxz8h2ucr0

**模型引用的证据**：

> "deliverable": {"kind": "file", "name": "report.md", "exists": true, "bytes": 125257, "min_bytes": 2000, "ok": true}

**摘要上下文**（引文定位：exact）：

```
   "task_prompt_chars": 2683,
▶  "deliverable": {"kind": "file", "name": "report.md", "exists": true, "bytes": 125257, "min_bytes": 2000, "ok": true},
   "exit": {"code": 0, "timeout": false, "crash": false, "oom": false, "infra_signal": null, "root_last_turn": "completed"},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 38

**行为：循环**（looping）

定义：反复做同样的搜索或步骤而没有进展；或者做完了还不停

给模型的原文：repeated identical searches or steps without progress, or not stopping when done

**运行**：x4kzijjby5

**模型引用的证据**：

> "kids_after_answer": {"n": 1, "agents": ["A6 (ended 1835.4 s)"]}

**摘要上下文**（引文定位：exact）：

```
   "search_fetch": {"root_web_search": 14, "root_web_fetch": 34, "tree_web_search": 156, "tree_web_fetch": 186, "root_share": 0.14},
▶  "kids_after_answer": {"n": 1, "agents": ["A6 (ended 1835.4 s)"]},
   "session_ids": {"A0": "f8d649fb", "A1": "7d3c5067", "A2": "94b202a5", "A3": "cfbaabe6", "A4": "bfa25cf2", "A5": "e43b5dd2", "A6": "59082a50", "A7": "1a23b7ea"},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 39

**行为：主 agent 自己动手不派活**（planner_self_work）

定义：主 agent 自己做了大部分搜索和阅读，没有交给 subagent

给模型的原文：the root agent itself did most of the searching/reading instead of delegating

**运行**：fpk1brk182

**模型引用的证据**：

> "search_fetch": {"root_web_search": 4, "root_web_fetch": 5, "tree_web_search": 4, "tree_web_fetch": 5, "root_share": 1.0}

**摘要上下文**（引文定位：exact）：

```
   },
▶  "search_fetch": {"root_web_search": 4, "root_web_fetch": 5, "tree_web_search": 4, "tree_web_fetch": 5, "root_share": 1.0},
   "kids_after_answer": {"n": 0, "agents": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 40

**行为：幻想协调**（phantom_coordination）

定义：主 agent 提到某个 subagent 做了某事，而日志显示并没有做

给模型的原文：the root refers to work by a subagent that the logs show was not done

**运行**：8gwungr13m

**模型引用的证据**：

> **8 份底稿**：全部完成于 `/work/8gwungr13m/workspace/parts/`。

**摘要上下文**（引文定位：exact）：

```
    "chars": 693,
▶   "head": "Part 7 已正式结束，其内容在本报告汇总阶段就已全部读取并整合，因此**无需对 `report.md` 做任何修改**。 最终状态确认： - **交付物**：`/work/8gwungr13m/workspace/report.md`（627 行，257 个来源链接，涵盖执行摘要、分析框架、法/德/韩/阿/乌五国分述、融资专题、横向比较、国际参照、结论与附录）。 - **8 份底稿**：全部完成于 `/work/8gwungr13m/workspace/parts/`。 - **Part 7 的贡献**（第 8 章及第 4、7.4 节）：德国 201…"
   },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 41

**行为：循环**（looping）

定义：反复做同样的搜索或步骤而没有进展；或者做完了还不停

给模型的原文：repeated identical searches or steps without progress, or not stopping when done

**运行**：pt21ybjppw

**模型引用的证据**：

> "duplicates": 0, "same_agent_repeats": 0, "top": []

**摘要上下文**（引文定位：exact）：

```
   "root_after_last_write": {"seconds_to_final_answer": 15.7, "root_calls": {"bash": 3, "job_list": 1, "todo_write": 1}},
▶  "repeated_queries": {"total": 36, "distinct": 36, "duplicates": 0, "same_agent_repeats": 0, "top": []},
   "shared_pages": {"urls_fetched": 17, "by_2plus_agents": 0, "examples": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 42

**行为：重复复核**（repeated_review）

定义：（编码题）文件写完后又有两波或更多复核，或复核用的 subagent 合计五个或更多（复核一波属正常）

给模型的原文：(code tasks) two or more review waves after the files were done, or five or more review subagents in total (one review wave is normal)

**运行**：11i6n64ug2

**模型引用的证据**：

> "review_like": {    "subagents": 5,    "waves": 1

**摘要上下文**（引文定位：closest line (similarity 0.60)）：

```
    "last_write_s": 1056.1,
▶   "after_last_write": {"subagents": 0, "waves": 0, "agents": []},
    "review_like": {
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 43

**行为：幻想协调**（phantom_coordination）

定义：主 agent 提到某个 subagent 做了某事，而日志显示并没有做

给模型的原文：the root refers to work by a subagent that the logs show was not done

**运行**：zwk4lerj96

**模型引用的证据**：

> `logs/search_queries.md`、`logs/verification.csv` | 检索记录与 489 个网页的逐页核对结果

**摘要上下文**（引文定位：exact）：

```
    "chars": 1759,
▶ …整研究报告（8 个章节、15 张表格、44 条参考资料） | | `data/*.csv` | Cboe 官方 VIX/GVZ/OVX 历史数据 + FRED 交叉验证数据 | | `analysis.py` / `analysis2.py` / `analysis3.py` | 全部统计与计量分析脚本 | | `outputs/*.json|csv` | 分析结果（描述统计、Granger 稳健性、IRF/FEVD 等） | | `logs/search_queries.md`、`logs/verification.csv` | 检索记录与 489 个网页的逐页核对结果 | ## 主要发现 **1. 三个指数**：VIX（Cb…"
   },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 44

**行为：主 agent 自己动手不派活**（planner_self_work）

定义：主 agent 自己做了大部分搜索和阅读，没有交给 subagent

给模型的原文：the root agent itself did most of the searching/reading instead of delegating

**运行**：9892nit6xj

**模型引用的证据**：

> "search_fetch": {"root_web_search": 4, "root_web_fetch": 6, "tree_web_search": 45, "tree_web_fetch": 213, "root_share": 0.04}

**摘要上下文**（引文定位：exact）：

```
   },
▶  "search_fetch": {"root_web_search": 4, "root_web_fetch": 6, "tree_web_search": 45, "tree_web_fetch": 213, "root_share": 0.04},
   "kids_after_answer": {"n": 0, "agents": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 45

**行为：幻想协调**（phantom_coordination）

定义：主 agent 提到某个 subagent 做了某事，而日志显示并没有做

给模型的原文：the root refers to work by a subagent that the logs show was not done

**运行**：6v5z5ka7i4

**模型引用的证据**：

> "head": "All agents stopped. Report finalized: `/work/6v5z5ka7i4/workspace/report.md` (**354 lines, ~65 KB**). ## 合规声明（最高优先级规则）

**摘要上下文**（引文定位：exact）：

```
    "chars": 1683,
▶   "head": "All agents stopped. Report finalized: `/work/6v5z5ka7i4/workspace/report.md` (**354 lines, ~65 KB**). ## 合规声明（最高优先级规则） **全程遵守**：从未打开、阅读或引用 Mulati 等人的 *Digital-Based Policy and Health Promotion Policy in Japan, the Republic of Korea, Singapore, and Thailand: A Scoping Review of Po…"
   },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 46

**行为：开得过多或开了不用**（over_spawning）

定义：任务用不着这么多 subagent；或者有的 subagent 交回的东西没被用上

给模型的原文：many subagents for a task that did not need them, or subagents whose hand-backs were not used

**运行**：69tth6e8wi

**模型引用的证据**：

> 请把这项调研拆成 8 个互不重叠的部分，各交给一个 subagent 并行完成，再由你汇总成报告。

**摘要上下文**（引文定位：exact）：

```
   "task_prompt_head": "我正在研究不同国家如何为文化和创意产业（CCS）的从业者（如艺术家、音乐家、作家等，特别是那些非典型雇佣关系的，例如自由职业或短期合同工）提供社会保障。请帮我深入调研一下这个问题，信息请截止到2021年初。 我特别关注以下几个国家的实践：法国、德国、韩国、阿根廷和乌拉圭。 我希望你为每个国家提供一份详细的概述，内容至少…",
▶  "task_prompt_tail": "…-practices-and-1；https://socialprotection-humanrights.org/wp-content/uploads/2021/10/wcms_781638.pdf 请把这项调研拆成 8 个互不重叠的部分，各交给一个 subagent 并行完成，再由你汇总成报告。",
   "task_prompt_chars": 2447,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 47

**行为：交回丢失**（handback_loss）

定义：subagent 交回内容里的某条具体事实或结果，最终回答或报告里没有

给模型的原文：a specific fact or result in a subagent's hand-back is absent from the final answer/report

**运行**：ivjhrsv61g

**模型引用的证据**：

> "accepted": 0

**摘要上下文**（引文定位：exact）：

```
    "spawn_calls": 0,
▶   "accepted": 0,
    "rejected_depth": 0,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 48

**行为：主 agent 自己动手不派活**（planner_self_work）

定义：主 agent 自己做了大部分搜索和阅读，没有交给 subagent

给模型的原文：the root agent itself did most of the searching/reading instead of delegating

**运行**：1cwfwpzyuj

**模型引用的证据**：

> "root_share": 1.0

**摘要上下文**（引文定位：exact）：

```
   },
▶  "search_fetch": {"root_web_search": 15, "root_web_fetch": 49, "tree_web_search": 15, "tree_web_fetch": 49, "root_share": 1.0},
   "kids_after_answer": {"n": 0, "agents": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 49

**行为：过早宣布完成**（premature_completion）

定义：最终回答说做完了，但交付物缺了部分；或者给出最终回答时还有 subagent 在跑

给模型的原文：the final answer claims completion while deliverable parts are missing, or subagents were still running at the final answer

**运行**：8zkfyyp8lv

**模型引用的证据**：

> "kids_after_answer": {"n": 1, "agents": ["A2 (ended 1571.8 s)"]}

**摘要上下文**（引文定位：exact）：

```
   "search_fetch": {"root_web_search": 18, "root_web_fetch": 25, "tree_web_search": 28, "tree_web_fetch": 49, "root_share": 0.56},
▶  "kids_after_answer": {"n": 1, "agents": ["A2 (ended 1571.8 s)"]},
   "session_ids": {"A0": "caf6df89", "A1": "5d5c3d59", "A2": "e10b7b32"},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 50

**行为：重复复核**（repeated_review）

定义：（编码题）文件写完后又有两波或更多复核，或复核用的 subagent 合计五个或更多（复核一波属正常）

给模型的原文：(code tasks) two or more review waves after the files were done, or five or more review subagents in total (one review wave is normal)

**运行**：cfbztrp8zj

**模型引用的证据**：

> "review_like": {"subagents": 0, "waves": 0, "agents": []}

**摘要上下文**（引文定位：exact）：

```
   "shared_files": {"files_written": 1, "by_2plus_agents": 0, "examples": []},
▶  "review": {"last_write_s": 555.2, "after_last_write": {"subagents": 0, "waves": 0, "agents": []}, "review_like": {"subagents": 0, "waves": 0, "agents": []}},
   "text_limits": {"level": 0, "task": 300, "child_task": 120, "handback": 300, "answer": 400, "prompt": 300, "message": 150}
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 51

**行为：主 agent 自己动手不派活**（planner_self_work）

定义：主 agent 自己做了大部分搜索和阅读，没有交给 subagent

给模型的原文：the root agent itself did most of the searching/reading instead of delegating

**运行**：aeztu33oqu

**模型引用的证据**：

> "root_share": 1.0

**摘要上下文**（引文定位：exact）：

```
   },
▶  "search_fetch": {"root_web_search": 35, "root_web_fetch": 41, "tree_web_search": 35, "tree_web_fetch": 41, "root_share": 1.0},
   "kids_after_answer": {"n": 0, "agents": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 52

**行为：转包**（pass_through）

定义：某个 subagent 自己什么都没做，就把领到的整件事基本原样交给了一个孩子

给模型的原文：a subagent delegated essentially its own whole task to one child before doing any work itself

**运行**：jzi6b8xmzt

**模型引用的证据**：

> "spawn_calls": 0

**摘要上下文**（引文定位：exact）：

```
    "by_depth": {},
▶   "spawn_calls": 0,
    "accepted": 0,
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 53

**行为：主 agent 自己动手不派活**（planner_self_work）

定义：主 agent 自己做了大部分搜索和阅读，没有交给 subagent

给模型的原文：the root agent itself did most of the searching/reading instead of delegating

**运行**：g5foecets7

**模型引用的证据**：

> "root_share": 0.12

**摘要上下文**（引文定位：exact）：

```
   },
▶  "search_fetch": {"root_web_search": 13, "root_web_fetch": 6, "tree_web_search": 106, "tree_web_fetch": 59, "root_share": 0.12},
   "kids_after_answer": {"n": 0, "agents": []},
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 54

**行为：过早宣布完成**（premature_completion）

定义：最终回答说做完了，但交付物缺了部分；或者给出最终回答时还有 subagent 在跑

给模型的原文：the final answer claims completion while deliverable parts are missing, or subagents were still running at the final answer

**运行**：ubktx659ax

**模型引用的证据**：

> "final answer (root's last turn ended: completed); subagents still running: 0"

**摘要上下文**（引文定位：exact）：

```
    {"t": 4603.4, "e": "last file write by A0: report.md"},
▶   {"t": 4608.8, "e": "final answer (root's last turn ended: completed); subagents still running: 0"}
   ],
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 55

**行为：循环**（looping）

定义：反复做同样的搜索或步骤而没有进展；或者做完了还不停

给模型的原文：repeated identical searches or steps without progress, or not stopping when done

**运行**：zsddgqjtxa

**模型引用的证据**：

> "repeated_queries": {"total": 390, "distinct": 390, "duplicates": 0, "same_agent_repeats": 0, "top": []}

**摘要上下文**（引文定位：exact）：

```
   "root_after_last_write": {"seconds_to_final_answer": 10.2, "root_calls": {"bash": 1, "get_goal": 1, "todo_write": 1, "update_goal": 1}},
▶  "repeated_queries": {"total": 390, "distinct": 390, "duplicates": 0, "same_agent_repeats": 0, "top": []},
   "shared_pages": {
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 56

**行为：幻想协调**（phantom_coordination）

定义：主 agent 提到某个 subagent 做了某事，而日志显示并没有做

给模型的原文：the root refers to work by a subagent that the logs show was not done

**运行**：fl1zsdov8m

**模型引用的证据**：

> "head": "调研完成，报告已写入 **`report.md`**（约 3.4 万字 / 545 行，含执行摘要、三大部分、参考文献与合规附录）。

**摘要上下文**（引文定位：exact）：

```
    "chars": 1886,
▶   "head": "调研完成，报告已写入 **`report.md`**（约 3.4 万字 / 545 行，含执行摘要、三大部分、参考文献与合规附录）。 ## 报告结构 | 部分 | 内容要点 | |---|---| | **执行摘要** | 给负责人的 5 分钟版：教材默认异性恋剧本、LGBTQ+ 缺席、练习造成\"撒谎或出柜\"两难、性别化语言教法问题、可行改进方向 | | **第一部分 主流教材的问题** | 以《げんき》《みんなの日本語》《できる日本語》为主，兼及 JSL、Yookoso、An Integrated Approach、Nakama 等；含页码/课次级例证…"
   },
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 57

**行为：转包**（pass_through）

定义：某个 subagent 自己什么都没做，就把领到的整件事基本原样交给了一个孩子

给模型的原文：a subagent delegated essentially its own whole task to one child before doing any work itself

**运行**：veg2eesmlq

**模型引用的证据**：

> "before_first_delegation": {"substantive_calls": 29, "seconds_after_start": 254.7}

**摘要上下文**（引文定位：exact）：

```
     "task_chars": 2895,
▶    "before_first_delegation": {"substantive_calls": 29, "seconds_after_start": 254.7},
     "delegations": [{"t": 280.7, "child": "A3", "overlap": 0.57}, {"t": 280.7, "child": "A4", "overlap": 0.58}, {"t": 280.7, "child": "A5", "overlap": 0.54}],
```

[ ] 是  [ ] 否  [ ] 拿不准

---

## 条目 58

**行为：转包**（pass_through）

定义：某个 subagent 自己什么都没做，就把领到的整件事基本原样交给了一个孩子

给模型的原文：a subagent delegated essentially its own whole task to one child before doing any work itself

**运行**：k4cwb0npwl

**模型引用的证据**：

> "before_first_delegation": {"substantive_calls": 0, "seconds_after_start": 23.4},    "delegations": [     {"t": 95.7, "rejected": "depth limit"

**摘要上下文**（引文定位：spans lines）：

```
     "calls": {"web_search": 21, "web_fetch": 12, "read": 4, "write": 18, "bash": 82, "delegate": 2, "other": 17},
▶    "before_first_delegation": {"substantive_calls": 19, "seconds_after_start": 72.3},
     "delegations": [{"t": 72.3, "child": "A1", "overlap": 0.17}, {"t": 72.3, "child": "A2", "overlap": 0.14}],
```

[ ] 是  [ ] 否  [ ] 拿不准

---
