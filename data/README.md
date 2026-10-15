# 数据

一行一次运行的总表加几张标注表。不知道的值留空，不用别的量顶替；运行的设置（D、K、题面加的句子、进程等不等）取自运行记录，不靠组名。费用由 token 数乘公开高峰价算出（没进缓存的输入 2.0 元/百万，读缓存 0.04，输出 8.0，搜索每请求 0.0173 元）。

列的逐条解释见 `phase1/columns.md`、`phase2/columns.md`。

## phase1/

| 文件 | 内容 |
|---|---|
| `runs.csv` | 2,873 次运行，22 批 |
| `facts-kappa.json` | 办公报告题事实清单判定的一致性检查 |

## phase2/

| 文件 | 内容 |
|---|---|
| `runs.csv` | 2,200 次运行 |
| `behavior-checklist.csv` | 行为清单标注，21,572 条（每次运行十项行为，GPT-5.5 标注，附证据句） |
| `behavior-checklist-by-cell.csv` | 行为清单按格汇总，对应报告里的行为图 |
| `tree-behavior-by-cell.csv` | 脚本从日志直接数的每格行为：agent 数、开 subagent 的调用、被拒数、主 agent 自己做的搜索占比、重复、回答时还有 subagent 在跑 |
| `delegation-by-cell.csv` | 再派活分类按格汇总 |

### phase2/human-check/

人工核对。`sealed.txt` 记下答案文件封存时的哈希，`*-answers.csv` 只读。

| 文件 | 内容 |
|---|---|
| `judgement-check-form.md` / `judgement-check-answers.csv` | 判分核对：120 条判定，只给报告节选和评分项，不给判分模型的结论 |
| `judgement-check-score.txt` | 核对结果与 GPT-5.5、Opus 的一致率 |
| `leak-look-form.md` / `leak-look-answers.csv` | 泄漏核对：得分最高的 20 份报告和与禁用来源文字重合最多的 10 份 |
| `leak-look-supplement.md` | 上一张表里判不准的条目的补充材料（同样不给结论） |

### phase2/model-checks/

行为清单和再派活分类这两项是 GPT-5.5 标注的，人工核对没做，改由 Opus 5.5 在看不到标注的情况下盲核：行为清单 58 条，再派活分类 30 条。表单和答案都在这里。一致率见报告的行为一节。
