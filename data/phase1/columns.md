# 运行级总表 results/master/runs.csv

一行一次运行，共 2,873 行，22 批。由 scripts/run_table.py（开发机，读原始日志）和 scripts/master_table.py（本机，接上判分）两步生成。

规则：不知道的值留空，不用别的量顶替；运行的设置（深度、K、题面加的句子、进程等不等）取自运行记录，不靠组名；钱由 token 数乘价格表算出。

价格表（元 / 百万 token，公开高峰价）：没进缓存的输入 2.0，读缓存的输入 0.04，输出 8.0；搜索每个请求 0.0173 元（抽样实测）。

## 列

| 列 | 含义 |
|---|---|
| id | run id given by the runner |
| batch | batch: the settings that were run and judged together |
| task | task |
| family | kind of task: office (2 research reports), ws (WideSearch), drb2 (DeepResearch Bench II), reading (2 tasks on the DSH source), p4 (4 exercises), timed24 / timed24-120 (24 exercises with a time limit), chain (16 serial steps), free24 (24 exercises, no limit), xl (the 61-file package) |
| rep | repetition number inside the batch |
| block | batch|task|rep: the runs of one block ran in the same round; contrasts pair runs inside a block |
| group | group name in the batch (kept for look-ups; the design columns below are read from the run record, not from this name) |
| D | depth limit of the run (0 = no subagents) |
| K | limit on subagents alive at once (empty when D = 0) |
| hint | sentence appended to the task prompt: none / parallel / no-review / search-100-100 / search-150-250 / search-250-500 / keep-all |
| told | 1 when the limit was written into the tool description (group prefix T-) |
| wait | 1 when the process was told to stay up until the subagents settle |
| web | 1 when the task may use the web |
| started_utc | start of the run's container |
| order | position of the run in the batch's random order |
| status | how the run ended, first rule that applies: timeout (the runner stopped it at the time limit) / crash_at_exit (the process crashed while leaving, issue 5063) / no_answer (the root agent's last turn did not complete) / nonzero_exit / ok |
| exit | exit code of the process |
| root_end | kind of the root agent's last turn end |
| oom_kill | 1 when the kernel killed a process inside the container for memory |
| kids_after_answer | subagents still active more than 2 s after the root agent's final answer |
| wait_cap | 1 when the waiting process gave up after its 20-minute cap |
| complete | 1 when the run handed in what the task asked for and it was judged; 0 when the judge marked the deliverable incomplete; empty when the task has no such check |
| recognized | 1 when the logs show the agent recognized the public benchmark (such runs are left out of the benchmark contrasts) |
| q | quality on the family's own scale, 0-100 (see q_metric) |
| q_metric | what q is: facts63 / f1_item / drb2_total / judge_score / tests |
| facts63 | office: % of the 63 items fixed before any run that the report states correctly |
| facts_all | office: % of the whole list (195 items) stated correctly |
| facts_wrong | office: items the report states wrongly (firm statements) |
| facts_right_n | office: items stated correctly, count |
| tests_failed | xl: hidden tests that did not pass (of 3,737; the grader's count) |
| rubric_score | office, first batch only: total of the old scoring rubric |
| report_chars | length of the deliverable in characters |
| t_answer_s | seconds from the first log event to the end of the root agent's last turn: what the user waits for |
| process_s | seconds the dsh process ran (runner's clock) |
| t_first_kid_s | seconds to the first event of the first subagent |
| t_last_write_s | seconds to the last result of a write or edit call, any agent |
| t_last_event_s | seconds to the last event of any agent |
| all_written_s | xl and free24: seconds until every required file existed (path analysis of the batch) |
| agents | agents of the run, root included |
| kids_d1 | subagents at depth 1 |
| kids_d2 | subagents at depth 2 |
| kids_d3 | subagents at depth 3 |
| review_kids | xl: subagents started after every file was written |
| spawn_calls | calls of the delegation tools |
| rejected_depth | delegation calls rejected by the depth limit |
| rejected_cap | delegation calls rejected by K |
| tok_miss | input tokens not read from cache, every agent |
| tok_hit | input tokens read from cache |
| tok_out | output tokens |
| search_requests | requests of the search plugin's own model |
| n_web_search | web_search calls |
| n_web_fetch | web_fetch calls |
| pages_saved | office-dose: pages the agents saved to disk (downloads by script included) |
| model_yuan | tokens times the price table |
| search_yuan | search requests times the measured price per request |
| total_yuan | model_yuan + search_yuan |
| root_turns | turns of the root agent |
| mem_peak_gb | memory peak of the container |
| parallel | runs at once in the batch |
| module | phase 2: module of the protocol the run belongs to: A (K and depth curves, natural demand) / B (fixed demand: the split-n-delegate sentence) / C (loose limit, D3-K64) / H (K x D grid) / G (mechanism: the search or split-self sentence on one agent, D0 repeats 2-4 on the g40 tasks, the merge batch) / D (v4-pro) / F (code) / pilot (smoke and calibration batches) |
| model | model the run asked for: deepseek-flash / deepseek-v4-pro (phase 1: deepseek-flash, the model its price was computed with) |
| model_requested | model id in the root agent's requests as the session log records it (raw tables of the new run_table.py only) |
| peak_alive | most subagents holding a slot of the K limit at once, in any one pool, as DSH counts them (run_table.py's rule; raw tables of the new run_table.py only) |
| peak_alive_d1 | the same, counting the root agent's direct children only |
| peak_alive_time_s | seconds from the first log event to the moment peak_alive was first reached (empty when peak_alive is 0) |
| model_yuan_offpeak | tokens times the off-peak price table of the model |
| drb2_recall | phase 2 drb2: info_recall dimension of the GPT-5.5 judge, % of its rubric items met |
| drb2_analysis | phase 2 drb2: analysis dimension, % of its rubric items met |
| drb2_presentation | phase 2 drb2: presentation dimension, % of its rubric items met |
| drb2_blocked_rate | phase 2 drb2: % of rubric items judged -1 (supported only by a blocked source) |
| judge_calls | phase 2 drb2: calls to the judge model in the first GPT-5.5 pass |
| judge_anomalous | phase 2 drb2: calls of that pass whose usage record was implausible (such replies were asked again) |
| q_opus | phase 2 drb2: total of the Opus second judge, when its file exists |
| q_gpt_r2 | phase 2 drb2: total of the second, independent GPT-5.5 pass, when its file exists |
| judge_note | phase 2 drb2: why the first GPT-5.5 pass has no score: judge refused / no report.md; empty when scored |

## 题面加的句子

| hint | 原文 |
|---|---|
| parallel | 独立的子任务尽量交给 subagent 并行做。 |
| no-review | 文件都写完以后，不要再另开子代理去复核、验证或补测试；需要检查就自己检查。 |
| search-100-100 | 写报告之前，请至少做 100 次网页搜索，并打开至少 100 个网页核对内容。 |
| search-150-250 | 写报告之前，请至少做 150 次网页搜索，并打开至少 250 个网页核对内容。 |
| search-250-500 | 写报告之前，请至少做 250 次网页搜索，并打开至少 500 个网页核对内容。 |
| keep-all | subagent 交回来的有来源的事实都写进最后的文件，重复的只写一次。 |

## 各类任务的运行数和退出状态

| 任务类 | 运行 | ok | crash_at_exit | timeout | no_answer | nonzero_exit |
|---|---|---|---|---|---|---|
| chain | 30 | 30 | 0 | 0 | 0 | 0 |
| drb2 | 210 | 210 | 0 | 0 | 0 | 0 |
| free24 | 240 | 237 | 1 | 0 | 2 | 0 |
| office | 1200 | 1143 | 50 | 0 | 7 | 0 |
| p4 | 160 | 156 | 0 | 0 | 4 | 0 |
| reading | 400 | 395 | 5 | 0 | 0 | 0 |
| timed24 | 140 | 60 | 0 | 80 | 0 | 0 |
| timed24-120 | 110 | 12 | 0 | 98 | 0 | 0 |
| ws | 233 | 227 | 1 | 3 | 2 | 0 |
| xl | 150 | 148 | 1 | 0 | 0 | 1 |

## 和各批原来的表对照（同一个量，新表减旧表）

| 量 | 对得上的运行 | 差的中位数 | 差的最大绝对值 | 差超过 1% 或 1 个单位的运行 |
|---|---|---|---|---|
| model yuan | 2873 | +0.000 | 0.000 | 0 |
| search requests | 2203 | +0.000 | 0.000 | 0 |
| total yuan | 2203 | +0.000 | 0.000 | 0 |
| subagents | 2873 | +0.000 | 0.000 | 0 |
| rejected by K | 2873 | +0.000 | 0.000 | 0 |
| rejected by depth | 2873 | +0.000 | 0.000 | 0 |
| process seconds | 2873 | +0.000 | 0.000 | 0 |
| answer time | 1668 | +0.000 | 0.600 | 0 |

## 第二阶段（p2-*）的批、新列和规则

第二阶段的批由 2026-10-08 版 scripts/run_table.py 抽取（多出 peak_alive、peak_alive_d1、peak_alive_time_s、wait_max_busy、wait_max_resident、model_id、model_requested 七列，另有 <batch>.spawn_calls.csv 和 <batch>.agents.csv 两张边表）。本脚本在 results/master/raw/<batch>.csv 存在时接入下面的批；第二阶段没有各批自己的分析表，运行记录只有原始表一个来源，判分从判分文件读（方案第十节）。新列从 module 起列在上面的列表末尾；第一阶段的行里这些列留空，只有 model（全是 deepseek-flash，即算它们价格用的模型）和 model_yuan_offpeak（空闲价）有值。

| 批 | module | model | 内容 |
|---|---|---|---|
| p2-smoke | pilot | deepseek-flash | 冒烟：smoke 题 × 各 flash 组各 1 次，不计分 |
| p2-smoke-d | pilot | deepseek-v4-pro | 冒烟：smoke 题 × 五个 v4-pro 组 |
| p2-calib | pilot | deepseek-flash | 四句附加句各 4 题 × 2 次的校准，不计分 |
| p2-main | A / B / C / H / G，按组 | deepseek-flash | 主批：方案第四节的 A、B、C、G、H 同一批 |
| p2-d | D | deepseek-v4-pro | 换模型 |
| p2-f | F | deepseek-flash | 代码题，不联网 |
| p2-merge | G | deepseek-flash | 四份单 agent 报告合并（任务 drb2_m4_<idx>） |
| p2-smoke-f（phase2-run.sh 里的名字；phase2-smoke-f 也认） | pilot | deepseek-flash | 代码题冒烟 |

主批里组到 module：D0 第 1 次和 W-D1-K1、W-D1-K2、W-D1-K3、W-D1-K4、W-D1-K8、W-D2-K8、W-D2-K16、W-D3-K8 → A；W-Pb3-*、W-Pb8-* → B；W-D3-K64 → C；W-D2-K2、W-D2-K4、W-D3-K2、W-D3-K4、W-D3-K16 → H；Pgm-D0、Pgs-D0 和 g40 题（tasks/phase2-drb2-index.json 里 sets 含 g40 的 40 道）上 D0 的第 2–4 次 → G。

第二阶段的题面附加句（tasks/phase2-sentences.json；hint 列新增的值）：

| 标签 | hint | sha256 前 8 位 | 原文 |
|---|---|---|---|
| b3 | split-3-delegate | 72baafb1 | 请把这项调研拆成 3 个互不重叠的部分，各交给一个 subagent 并行完成，再由你汇总成报告。 |
| b8 | split-8-delegate | 98231bd6 | 请把这项调研拆成 8 个互不重叠的部分，各交给一个 subagent 并行完成，再由你汇总成报告。 |
| gs | split-8-self | 590e3dba | 请把这项调研拆成 8 个互不重叠的部分，自己依次完成，再汇总成报告。 |
| gm | search-150-250 | 9ab9b59e | 写报告之前，请至少做 150 次网页搜索，并打开至少 250 个网页核对内容。（与第一阶段 search-150-250 逐字相同，哈希核对过） |

句子怎么定：run_table.py 只输出 hint_a / hint_b（第一阶段 E- / N- 两句的哈希），不输出运行记录里的 sentence_sha256。本脚本拿原始表的 prompt 列（运行记录里整段题面的 sha256 前 8 位）和「题面文件里的题面 + 空行 + 句子」算出的哈希对照来定（题面文件：tasks/phase2-drb2-tasks.jsonl、tasks/phase2-drb2-tasks-v4pro.jsonl、tasks/phase2-code-tasks.jsonl、tasks/phase2-merge-tasks.jsonl）；原始表若有 sentence_sha256 / sentence_tag 列则先用它。对不上的行 hint 留空并在运行时打印。组名里的 P<标签>- 只用来核对，不作来源。

价格（元 / 百万 token，results/price-snapshot-2026-10-08.md）：

| 模型 | 读缓存的输入 高峰 / 空闲 | 没进缓存的输入 高峰 / 空闲 | 输出 高峰 / 空闲 |
|---|---|---|---|
| deepseek-flash | 0.04 / 0.02 | 2.0 / 1.0 | 8.0 / 4.0 |
| deepseek-v4-pro | 0.3 / 0.15 | 9.0 / 4.5 | 27.0 / 13.5 |

model_yuan 按高峰价、model_yuan_offpeak 按空闲价，模型取 model 列（原始表的 model_requested；没有这一列时按批：p2-d、p2-smoke-d 为 deepseek-v4-pro，其余 deepseek-flash；两者不一致时脚本停下）；search_yuan 仍是搜索请求数 × 抽样实测单价；total_yuan 仍是高峰模型费加搜索费。

complete（报告题，family = drb2）：workspace/report.md 存在且不少于 2,000 字节记 1，否则 0。run_table.py 不输出 runner 的 deliverable_ok，依次取：原始表的 deliverable_ok 列；results/runs-dsec/<batch>/manifest.jsonl 的 deliverable_ok；判分文件（note 为 no report.md → 0；chars ≥ 2,000 → 1，一个字符至少一个字节）；都没有则留空并打印。

判分（family = drb2）：q = results/drb2-score-gpt/<batch>/<id>.r1.json 的 total（q_metric = drb2_total_gpt55），drb2_recall / drb2_analysis / drb2_presentation 为三个维度的 score，drb2_blocked_rate 为 blocked_rate，judge_calls / judge_anomalous 为 llm.calls / llm.anomalous，report_chars 为 chars。没有这个文件时 q 留空，不用别的替；note 为 judge refused 或 no report.md 时 q 留空、judge_note 记 note。q_opus = results/drb2-score/<batch>/<id>.r1.json 的 total（Opus 复判），q_gpt_r2 = results/drb2-score-gpt/<batch>/<id>.r2.json 的 total（GPT-5.5 第二遍）。recognized 取 results/analysis-<batch>-sources.json 的 n_hits > 0。代码题（p2-f，toolkit-xl）：results/grade/<batch>/index.jsonl 存在时 q = score（q_metric = tests）、tests_failed = total − passed；其余代码题的分还没有接。
