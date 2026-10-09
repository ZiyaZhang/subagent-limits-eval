# Analysis scripts, committed 2026-10-09 while the main batch was still running

Written and committed before any report of the second phase was judged (the judging starts only after the last
web batch). They implement section 七 of the protocol; the choices the protocol had left open are listed in the
protocol's change log under 2026-10-09T03:00Z and at the top of `phase2_report.py`.

| File | What it does |
|---|---|
| `phase2_report.py` | every contrast (the 9 confirmatory ones with Holm, the exploratory ones), levels per cell, demand curves, Table 1, the rule for recommending a default; five versions of the rows (confirmatory, all runs, with leaks, first repetition only, without the blocks hit by the interface fault) |
| `phase2_figures.py` | the figures, from the outputs of `phase2_report.py` |
| `phase2_judgments.py` | the judgments table and the agreement between judges; reads no cell information |
| `phase2_balance.py` | interface speed by cell and repetition (balance check) |
| `leak_top20.py` | blind material for the human leak look, and its scoring |
| `phase2-post.sh` | order of operations after the chain: blind pre-step, sealing of the two human forms, then the master table with judgements |
| `master_table.py` | run-level master table; changed to know module O, the two other coding tasks and the human leak flags |
| `phase2_fake_master.py` | simulated rows for dry runs of the scripts; nothing it writes is a result |
| `label_page.py`, `phase2-forms.sh` | one offline page per blind check form, filled with the keyboard, exporting exactly the answer file the scoring scripts read |
| `tool_errors.py`, `run_excerpt.py`, `phase2-pull-figs.sh` | failed searches and fetches per run; a viewer of one run's agents and timelines; the Mac-side fetch-and-draw step |
| `retry_waits.py` | seconds each run waited for automatic retries of failed model requests (names the blocks hit by the interface fault) |
| `delegation_classify.py` | what subagents hand on when they delegate: extraction, classification by the judge model, human check, per-cell summary |

Checked on simulated rows: the paired differences of four confirmatory contrasts were recomputed by an independent
plain calculation and agree in estimate, standard error and number of tasks.
