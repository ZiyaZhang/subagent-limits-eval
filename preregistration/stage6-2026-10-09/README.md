# Scripts started by hand during the judging stage (2026-10-09), none of which reads a judgement

| File | What it does |
|---|---|
| `opus-early.sh` | runs the Opus second-judge sample of a batch next to the GPT-5.5 first pass instead of after it; the sample selection code is the chain's, byte for byte |
| `stage6-extras.sh` | the search price probe (100 requests), the pilots of the two annotations, the behaviour checklist on every run, the classification of re-delegations |
| `deleg-repilot.sh` | second pilot of the classification on the first pilot's 40 units, after the change below |
| `delegation_classify.py` | changed after the first pilot: a long child task is shown with its first 200 characters and then with every passage it repeats word for word (40 characters or more) folded into a note; classes and definitions unchanged; one rule added to the prompt to explain the notes. First pilot: 20 of 102 labels "unclear" (the fixed-length cut showed only the rules that subagents copy at the top of each child task). Second pilot, same units: 0 "unclear" |
| `message_census.py`, `tool_error_census.py` | the two censuses behind odd-behaviors-log.md (unchanged since 41541d5; rerun after the fork correction) |

See the protocol's change log, entries 2026-10-09T17:05Z and 17:24Z.
