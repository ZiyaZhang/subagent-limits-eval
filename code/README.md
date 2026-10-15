# 脚本

单文件、平铺。跑批在开发机上执行，读日志和分析在本机。开发机路径和内部端点域名还在脚本里（不含密钥），公开前要替换。

## 跑批

| 脚本 | 用途 |
|---|---|
| `dsec_matrix_v6.py` | 第二阶段跑批：读每格的运行清单，按随机顺序一次一个容器地提交 |
| `run_matrix_v2.py` | 第一阶段跑批 |
| `phase2-run.v2.sh`、`stage6-extras.sh`、`phase2-post.sh` | 启动器：主批、补充批（行为标注、再派活、搜索费用抽样）、跑完后的收尾 |
| `search_cost_probe.py` | 抽样实测搜索请求的单价 |

## 读日志

| 脚本 | 用途 |
|---|---|
| `run_metrics.py` | 从一次运行的全部会话日志算出 token、费用、agent 数、开 subagent 的调用和被拒数、搜索与网页、时间点。`test_run_metrics.py` 是它的测试 |
| `run_table.py`、`master_table.py` | 拼出运行级总表（前者在开发机读日志，后者在本机接上判分） |
| `delegation_stats.py`、`message_census.py`、`tool_error_census.py`、`retry_waits.py`、`request_timing.py`、`write_timing.py` | 再派活、消息、工具报错、被拒后的等待、请求用时、文件写入时间 |
| `depth_all.py`、`merge_stats.py`、`run_digest.py`、`run_excerpt.py` | 深度分布、合并组的统计、单次运行的摘要和节选 |

## 判分

| 脚本 | 用途 |
|---|---|
| `drb2_score_gpt.py` | 调研题判分：调用评测集官方的 GPT-5.5 评分流程 |
| `drb2_score_gpt_repair.py` | 同上，另外修复评分项原文被判分模型改写一两个字导致对不上的情况（改动记进 `repairs-*.json`） |
| `drb2_score.py`、`drb2_sources.py`、`drb2_fetch_sources.py`、`drb2_ngram_leak.py` | 本地判分、来源清单、抓来源、与禁用来源的文字重合度（查泄漏） |
| `judge_length_bias.py`、`judge_false_facts.py` | 判分验证：报告加三成无关但正确的文字、插入看起来合理的错误事实 |
| `llm_client.py` | 模型调用的公共部分 |

## 分析

| 脚本 | 用途 |
|---|---|
| `phase2_combine.py` | 预注册分析：9 个确认性对比，分层模型加 Holm 校正，出 `analysis/phase2/` 下的全部文件 |
| `paired_stats.py`、`phase2_balance.py`、`phase2_models.py`、`phase2_judgments.py` | 配对比较、各格的样本均衡、两个模型的对比、判分项级的一致性 |
| `mechanism_extra.py`、`v2_tables.py`、`master_table.py` | 对照组（多搜索、分段、合并）、结果表 |
| `phase2_figures.py`、`plot_clean.py`、`plot_wiki.py`、`plot_wiki5.py`、`plot_brief.py` | 画图 |

## 标注与核对

| 脚本 | 用途 |
|---|---|
| `behavior_annotate.py` | 行为清单标注：十项行为，逐次运行给出判定和证据句 |
| `delegation_classify.py` | 再派活分类：把 subagent 派出去的任务分成分片、收窄、原样转包、新子题、复核 |
| `behavior_check.py`、`human_check_sample.py`、`leak_top20.py`、`leak_supplement.py`、`label_page.py` | 生成核对表单（盲核：只给证据，不给已有结论） |

## 发布

`feishu_publish.py`、`feishu_replace_body.py`、`feishu_update.py`、`wiki_apply.py`、`wiki_edit.py`、`build_report.py`、`build_clean.py`、`render-brief.sh` 把报告发到飞书文档。其余 `.sh` 是单次用的启动和搬运脚本。
