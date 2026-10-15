# 代码题评分标准（v1.1 草稿，2026-10-02，待签字）

v1.1 是对抗核查后的改动：B7 补上第三种改窗口的方式（message projection，只改已有消息的内容、不增删节点），B6 改成"经 Session.append 加不上 ignorable"并收窄错误条件，B1、B3、B12 补了说明，P11 写清哪种"每个父代理各有 N 个"算错。

本文件给 c1、w1 两道代码调研题判分用：打分模型 Opus 5.5，推理强度 max，每份判 2 次。p4 用 scripts/grade_tests.py 跑隐藏测试判分，不用模型，不在本文件里。

- 答案键全部以快照 data/repos/dsh-cc0fb5f8b7 为准。每条都打开源码读到行号，并核对了适用对象和方向：它管谁、在什么时机、往哪个方向生效，不只是字符串或数字出现过。下文路径都相对快照根目录。
- c1 22 个要点的逐条核对记录（源码摘录、判错的写法、不计分的正确补充）在 tasks/code-keys/c1-points.md。
- 计分规则沿用办公题 v1.3（rubrics/office-rubrics-draft.md 的"计分"一节），判定细则的例子换成了代码题的。
- 判分前脚本先做三件事：
  - 删掉描述做题过程的句子（方案 6.1，每处人工确认）；
  - w1 按下面的篇幅规则截断；
  - 没有产出文件或短于阈值（c1 answer.md 1000 字节、w1 report.md 2000 字节）的运行，直接记 0 分、满分照常，不交给打分模型，也不剔除（方案附录 C）。
- 打分模型只看到本文件的"计分"一节和对应题目一节、被评文件；w1 另有脚本抽出的 5 处源码片段。看不到组别、运行编号和题面后缀。
- 签字和冻结：
  - 主批次开跑前请用户过一遍（方案 6.4）；
  - 签字后把本文件和 c1-points.md 的 sha256 写进预注册；
  - 运行期间按方案附录 C 把 rubrics/、tasks/code-keys/ 设为 chmod 000，判分前改回。

## 计分

### c1：22 个要点

- 每个要点判"对 / 错 / 没提到"：对记 1 分，错和没提到记 0 分。
- 得分 = 对的要点数 ÷ 22 × 100，两次判分取平均。满分 22。
- 另记两项，不计分，报告里单列：
  - 答错的要点数，即判"错"的个数；
  - 编造位置数：答案里写的"路径:行号"在快照里找不到的次数。由脚本数，打分模型不用数。
- 给分要求：
  1. 内容和适用对象都要对。名字、数字写对了，但说错了它管哪些子代理、什么时候检查，判错。
  2. 一句话覆盖几个要点时分别给分；一个要点分散在几处写，合起来判。
  3. 要求写出位置的要点（P3、P9、P18）要写出文件。行号落在答案键范围内、前后 5 行内或指向同一个声明或函数，都算对；文件写错判错。其他要点不要求位置。
  4. 多写的正确内容不加分。多写的错误内容，只有和某个要点矛盾时才把那个要点判错，例如说"深度上限只在加载配置时检查"，P17 判错。
  5. 标了"待核验"的要点，内容对算对，内容错算错。

### w1：A/B/C/D 四类（沿用办公题 v1.3）

- A、C、D 每条 0/1/2 分：
  - 2 分：完全做到，找不到问题；
  - 1 分：做到了一部分，或者有任何一处问题（遗漏、前后矛盾、说错、个别结论没来源）；
  - 0 分：基本没做到。
- B 每条：正确 +2，标了"待核验" +1，没提到 0，错误 −2；标了"待核验"但内容错了，记 0。
- 带 ★ 的是严重项：出错时在总分之外单独记一次"严重错误"，报告里单列。
- A7（结果写进 report.md）由脚本判定，打分模型不用打。
- 得分 = 各条得分之和 ÷ 满分 × 100，两次判分取平均。满分 = 26 条 × 2 = 52（A 14、B 24、C 8、D 6，A7 计入）。B 有负分，总分可以是负数。
- 篇幅：
  - 题面限 3000 字。计数方法：汉字数，加上英文单词、数字、路径片段的段数，每段算 1。
  - 超过 3300 的部分在判分前由脚本截掉，文末注明"已截断"。评分只看截断后的文本，截掉的内容不计入任何一条。
  - 不因为没写满 3000 字扣分。

### 判定细则

第 1、3、5、6 条沿用办公题 v1.3 的同号细则，例子换成了代码题的；第 2、4 条替换了办公题里只适用于网页来源的两条（价格常变、测试条件不同的数字）；第 7 条是新加的；第 8 条照抄 judge.py 评分说明的第 7 条。

1. **编造和归错分开记。**
   - 编造：快照里不存在的包、文件、导出的函数或方法、配置项、事件类型，被当成现有的写出来。w1 记 C3 严重错误；c1 把对应要点判错。
   - 归错：名字或数字在快照里有，但说错了它管谁、在什么时机、往哪个方向生效。例如把只管可续聊子代理的 maxActiveSubagents 说成管所有子代理，把默认不装的 tool-session-query 说成默认可用。归错按"错误"记（c1 判错，w1 对应 B 条 −2），不记严重错误。
2. **以快照为准。**
   - 行号和答案键不完全一致，但落在前后 5 行内或指向同一个声明、函数，算对。
   - 仓库文档和实现不一致时以实现为准。例如 docs/cookbook/extension-cookbook.md:113 说根目录 AGENTS.md 由 section provider 读入，实现（packages/context/agent-instructions）是在第一次请求前注入一条 user 消息。照文档写、又没指出不一致的，按错误记。
3. **"待核验"的写法。** w1 里标了"待核验"或"未核实"、内容其实对的，B 条 +1；内容错的记 0：不给 +1，也不按错误扣 2 分。
4. **新设计不算编造。** w1 要设计一个还不存在的插件。报告里新起的工具名、事件名、包名，写明是新增或建议的，不算编造；说成仓库里已经有，按编造记。
5. **有问题就不能给满分。** A、C、D 类条目，打分理由里写出了任何问题、瑕疵或遗漏的，最多 1 分。
6. **结论和正文矛盾算可用性问题。** 例如摘要里的难度和正文难度表对同一个模块说法不同，D2 最多 1 分。
7. **B 条只按内容判。**
   - 写到了但没附位置，照样按内容给分，缺的位置扣在 C1。
   - 一条里写对了要求的部分，又写了和正确值矛盾的内容，按错误记 −2。
8. **不要因为文件长、来源多、排版好就加分。**

## c1 子代理两个上限在哪里实现

题面：这个仓库是 DeepSeek Harness 的源码。请调研：子代理（subagent）的“同时存活数量上限”和“递归深度上限”分别在哪里实现、默认值是多少、在什么时机检查、各自对哪些子代理不起作用。写到 answer.md，每条结论附文件路径和行号。

22 个要点由 tasks/answer-keys.md 的 c1 六条拆出：第 1 条 P1–P3，第 2 条 P4–P7，第 3 条 P8–P11，第 4 条 P12–P16，第 5 条 P17–P20，第 6 条 P21–P22。"可续聊"即 continuable，"一次性"即 one-shot。

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| P1 | 同时存活上限叫什么 | `maxActiveSubagents`，限制同时存活的子代理数。给分：写出这个配置名，并说明它是同时存活数量上限 | packages/subagent/subagent/src/index.ts:193-194、203 |
| P2 | 同时存活上限的默认值 | 8。给分：写出 maxActiveSubagents 默认 8 | packages/subagent/subagent/src/index.ts:193、203；packages/subagent/subagent/README.md:51 |
| P3 | 同时存活上限定义在哪 | Host 上 dsh-subagent 服务（`SubagentRuntime`）的 Config，文件 packages/subagent/subagent/src/index.ts（接口 192-197 行，schema 201-204 行）。给分：写出这个文件，行号在 191-204 前后 5 行内，或指明是 SubagentRuntime 的 Config。只给出检查处（continuation-activation.ts）、没有定义处的，不给分 | packages/subagent/subagent/src/index.ts:191-204；packages/subagent/subagent/README.md:51 |
| P4 | 深度上限叫什么 | `maxDepth`，限制委派的递归深度。给分：写出这个配置名，并说明是深度上限 | packages/subagent/subagent/src/index.ts:195-196、202 |
| P5 | 深度上限的默认值 | 1：只允许直接子代理；0 表示不能委派。给分：写出默认 1。写成 3 或其他值判错 | packages/subagent/subagent/src/index.ts:195、202；packages/subagent/subagent/README.md:47 |
| P6 | 两个上限在同一个 Config | maxDepth 和 maxActiveSubagents 同在 SubagentRuntime 的 Config，即 Host 的 subagent 设置。给分：写明两者在同一个 Config 或同一个服务设置里，或给出 packages/subagent/subagent/src/index.ts 191-204 行内的定义位置 | packages/subagent/subagent/src/index.ts:192-204；packages/subagent/subagent/README.md:47 |
| P7 | 委派工具行可以单独设深度 | tool-subagent 的每行配置都可以写 maxDepth：写死一个非负整数，或写 `'provider-managed'`（不发上限，交给进程外 provider）；不写时每次委派读 Host 当前设置（默认 1）。给分：写出工具行可以显式设置深度，数值或 provider-managed 至少提到一种 | packages/subagent/tool-subagent/src/index.ts:93-103、130、514；packages/subagent/subagent/src/index.ts:239-250；packages/subagent/tool-subagent/README.md:53、63 |
| P8 | 同时存活上限何时检查 | 新建可续聊子代理、冷恢复已落盘的可续聊子代理时检查，在重建 Agent 之前预占名额。给分：新建和冷恢复两种时机都要写到。说成每次调用 subagent 工具都检查（包括一次性子代理），判错 | packages/subagent/subagent/src/continuation-activation.ts:484-489；packages/subagent/subagent/src/continuation.ts:161、436；packages/subagent/subagent/README.md:51、53 |
| P9 | 同时存活上限的检查代码 | continuation-activation.ts 的 `ActivationPool.reserve`：池里已占名额数 ≥ 上限就抛错，否则占一个名额并返回释放函数；materialize 里调用 `pool.reserve(this.maxActiveSubagents())`。给分：写出 ActivationPool.reserve（或 reserve 的调用点）和文件 continuation-activation.ts | packages/subagent/subagent/src/continuation-activation.ts:40-56、489 |
| P10 | 达到同时存活上限的报错 | 报错文字 `subagent limit reached (active child limit: N); wait for an existing child to finish or complete this work with the current agents`，错误码 `ACTIVATION_LIMIT_REACHED`；满了直接拒绝，不排队。给分：写出报错文字开头或错误码之一。说成排队等待，判错 | packages/subagent/subagent/src/continuation-activation.ts:47-50；packages/subagent/subagent/README.md:55 |
| P11 | 名额池怎么共享 | 名额池沿连续的可续聊父子关系共享：每个非可续聊的父代理（如根代理）有一个池，它的可续聊子代理及这些子代理的可续聊后代共用这个池；一次性父代理下面的可续聊子代理另开一个池；不同根会话的池互不相干。给分：写出根代理（或非可续聊父代理）的可续聊后代共用一个池。说成每个父代理（包括可续聊的父代理）都各有 N 个名额，或整个进程所有会话共用 N 个，判错；"每个非可续聊父代理各有一个池"是对的 | packages/subagent/subagent/src/continuation-activation.ts:40、65、488、604-612；packages/subagent/subagent/src/index.ts:193；packages/subagent/subagent/README.md:51 |
| P12 | 不计入：前台一次性子代理 | `run_in_background: false` 的前台调用走 `ctx.subagents.start()`（一次性），不进名额池。给分：写出前台或一次性子代理不计入 | packages/subagent/subagent/src/continuation.ts:76-81；packages/subagent/tool-subagent/src/index.ts:563-567；packages/subagent/tool-subagent/README.md:61；packages/subagent/subagent/README.md:51 |
| P13 | 不计入：一次性后台任务 | 工具行 `backgroundMode: one-shot` 时，`run_in_background: true` 启动的是普通后台 job，内部仍调 `ctx.subagents.start()`，不进名额池。给分：写出一次性后台任务（后台 job）不计入。只写"一次性子代理不计入"、没提后台的，不给这一点 | packages/subagent/tool-subagent/src/index.ts:544-556；packages/subagent/tool-subagent/README.md:59；packages/subagent/subagent/README.md:51 |
| P14 | 不计入：workflow 的 agent() 子代理 | workflow 脚本里的 `agent()` 由 workflow-ptc 用 `ctx.subagents.start()`（一次性）启动，不进名额池。给分：明确写出 workflow 开的子代理不受 maxActiveSubagents 限制。只在深度部分提到 workflow 的，不给这一点 | packages/workflow/workflow-ptc/src/host.ts:197-211；packages/subagent/subagent/README.md:51 |
| P15 | 不计入：外部 provider | codex、claude-code 等进程外 provider 没有 `prepareContinuable`，只能一次性运行，不进名额池。给分：写出外部（进程外）provider 不计入，点名 codex 或 claude-code 之一即可 | packages/subagent/subagent-codex/src/index.ts:64；packages/subagent/subagent-claude-code/src/index.ts:74；packages/subagent/subagent/src/index.ts:596-609；packages/subagent/subagent/README.md:51 |
| P16 | 不计入：池的所有者本身 | 拥有名额池的非可续聊父代理（如根代理）自己不占名额。给分：写出根代理或池的所有者自己不计入 | packages/subagent/subagent/README.md:51；packages/subagent/subagent/src/continuation-activation.ts:604-612；.agents/notes/implemented/feature/2026-09-15-continuable-activation-capacity.md:13 |
| P17 | 深度上限何时检查 | 每次启动子代理时检查，读的是当前设置，改了下一次委派就生效；工具在上限处仍可见，超限的调用返回错误结果。给分：写出每次启动或每次委派都检查。说成只在加载配置时检查，判错 | packages/subagent/tool-subagent/src/index.ts:97-98、100-101、514；packages/subagent/tool-subagent/README.md:63；packages/subagent/subagent/README.md:47 |
| P18 | 深度上限的检查代码 | child-agent.ts 的 `resolveChildDepth`：子代理深度 = 父代理深度 + 1，maxDepth 有值且子代理深度大于它时抛 `SubagentDepthError`。给分：写出 resolveChildDepth 和文件 child-agent.ts | packages/subagent/subagent/src/child-agent.ts:50-58 |
| P19 | 超过深度上限的报错 | `subagent depth N exceeds maxDepth M`（SubagentDepthError）。给分：写出这句报错（N、M 可写成具体数字）或 SubagentDepthError | packages/subagent/subagent/src/child-agent.ts:33-38 |
| P20 | 一次性和可续聊两条路径都查深度 | 一次性子代理在共享驱动 `startInProcessRun` 里检查，spawn、fork 两个进程内 provider 都用它；可续聊子代理在 `startContinuable` 里检查。给分：写出两条路径都检查，给出两个调用点之一并说明两条都查也算对。说成可续聊或后台子代理不查深度，判错 | packages/subagent/subagent-in-process-driver/src/index.ts:104-111；packages/subagent/subagent/src/continuation.ts:104-112；packages/subagent/subagent-spawn-in-process/src/index.ts:58；packages/subagent/subagent-fork-in-process/src/index.ts:78 |
| P21 | workflow 的总数上限 | workflow-ptc 的 `maxTotalAgents`，默认 1000：一次 workflow 运行最多启动的 agent() 数。给分：写出 1000，并说明是 workflow 的上限 | packages/workflow/workflow-ptc/src/index.ts:37-38、108 |
| P22 | workflow 的并发上限 | `maxConcurrentAgents` 默认 0，表示自动取 min(16, max(1, 可用 CPU 数 − 2))。给分：写出 min(16, 核数 − 2)，带不带 max(1, …) 都算对，并说明是 workflow 的并发上限 | packages/workflow/workflow-ptc/src/index.ts:35-36、107、141-143 |

不计分、答出来也不算错的内容：深度上限对 workflow 的 agent() 和 provider-managed 的工具行不起作用；冷恢复不重新检查深度；maxActiveSubagents 最小 1、maxDepth 最小 0；名额满了不排队；调低上限不会停掉已驻留的子代理。依据见 c1-points.md 末尾两节。

## w1 记忆溯源插件的实现路径

题面：这个仓库是 DeepSeek Harness 的源码。我想做一个dsh的插件，用于记忆来源追溯与修改，能够在一个会话或者项目进行时随时review这个对话和项目产生的窗口记忆和长期记忆，以及实现长期记忆在跨会话项目的调用和管理。帮我研究这里的实现路径以及技术难度。写到 report.md，不超过 3000 字，关键结论附文件路径和行号。

题面来源：用户日志 s18 的原话（data/user-sessions/s18-memory-plugin/extracted/session.v3.jsonl 第 7 行，原本是一条 /goal 命令）。改动只有四处：去掉 /goal；前面加"这个仓库是 DeepSeek Harness 的源码。"；原话末尾补一个句号；后面加篇幅和引用要求。

### A 硬性覆盖

| 编号 | 条目 |
|---|---|
| A1 | 宿主插件 API：说明插件怎样接进 DSH（Cordis 插件），以及要用到的扩展点，例如 system prompt section、工具注册、agent.inject()、session/event 监听、SessionEventMap 扩展、agent/pre-step，至少两种，并落到具体包或文件 |
| A2 | 会话日志和窗口记忆：说明模型每一步看到的窗口怎样由会话日志推导、怎样读出来供 review；说明压缩后窗口怎样变化 |
| A3 | 长期记忆：存在哪里（宿主存储、外部 MCP、文件等），怎样跨会话、跨项目检索和调用，现有能力能用到什么程度 |
| A4 | 溯源和修改的限制：能追溯到什么（日志、压缩摘要引用的原事件等），能改、能删到什么程度（只追加、只能替换遮蔽或用 message projection 改写内容、自定义事件的限制等） |
| A5 | 界面扩展：会话或项目进行中怎样随时 review，例如 Web 客户端的会话节点、侧栏、工具卡片、命令，落到具体包 |
| A6 | 分阶段的实现路径和难度分级：给出实现顺序，每个模块有难度等级和理由 |
| A7 | 结果写进 report.md（脚本判定） |

### B 关键事实

每条都在快照里读到行，并核对了适用对象。

| 编号 | 事实 | 正确值 | 来源 |
|---|---|---|---|
| B1 | 仓库里现有的记忆能力 | 没有现成的记忆插件：packages/*/* 下 316 个目录没有一个名字含 memory，出厂组合里也没有 memory server。跨会话长期记忆目前只有 3 个默认关闭的第三方 MCP memory 参考配置（Memorix、MCP Reference Memory、Engram），要用 --patch 或写进用户补丁层（如 $DSH_HOME/cordis.patch.yml）显式加载，经 dsh-mcp-client 接入，工具名为 mcp__<serverName>__<tool>。给分：写出没有内置的记忆包或长期记忆服务即 +2。错误：说已有内置的记忆插件或长期记忆服务；把 MCP 示例说成默认启用 | packages/*/* 目录清单；docs/user/guide/mcp-memory.md:5、11、17-21、31、33；apps/cli/config/examples/mcp-memory/memorix.cordis.yml、mcp-reference-memory.cordis.yml、engram.cordis.yml |
| B2 | 扩展手册建议怎样做记忆 | 扩展手册的"产品功能—插件机制"对照表里，Memory 对应"section provider + tool"：用 system prompt section 提供记忆内容，用工具读写。这是设计建议，仓库里没有按它实现的记忆插件。给分：写出这条对应关系即 +2。错误：说手册或仓库里已有现成的 memory API 或插件 | docs/cookbook/extension-cookbook.md:104、126；section 注册接口 packages/core/system-prompt/src/index.ts:454 |
| B3 | 会话日志的位置和格式 | 默认在 $DSH_HOME/sessions（没设 DSH_HOME 时为 ~/.dsh/sessions）下，先按工作目录分项目目录（形如 --<路径编码>--），再按会话 id 分目录。当前文件名 session.v4.jsonl.zstd：JSONL，每行一个事件，默认 zstd 压缩（配 compression: none 时为 .jsonl；sdk-minimal 组合就这样配，写到这一点不算错），格式版本 4。第一行是 header：type: session、version、id、createdAt、cwd、parentSession、isSeeded、origin、delegationDepth、agentPreset。给分：目录和格式（JSONL 加 zstd，或写出文件名）都写到且无误即 +2；只写到其中一项记 0。错误：说成数据库；说默认不压缩；版本写成 3 | packages/bundle/base/cordis.patch.yml:130-133；packages/util/home-paths/src/index.ts:12、79-100；packages/session/session-persistence-jsonl/src/format.ts:79-95、225-269、298-305；packages/session/session-persistence-jsonl/src/index.ts:68、82-101；packages/session/session-format/src/filename.ts:14-17；packages/core/session/src/types.ts:89；packages/bundle/sdk-minimal/cordis.patch.yml:154-158 |
| B4 | 会话日志能不能改 | 会话的权威记录是只追加的事件日志，消息历史由日志推导；已提交的事件不改写，改动只能靠追加新事件。SessionEventMap 可以通过声明合并加入新的事件类型。给分：写出只追加、历史由日志推导即 +2，可扩展这一点可以不写。错误：说能直接修改或删除日志里的旧事件 | packages/core/session/src/types.ts:276-281；packages/core/session/README.md:12、88 |
| B5 | 新事件类型和 ignorable | 读取会话时，本构建不认识的事件类型（不在 KNOWN_SESSION_EVENT_TYPES 里）如果没带 ignorable: true，整份日志拒绝重建；ignorable 只该用在丢了也不影响重建的纯记录上。给分：写出"不认识的类型不带 ignorable 会被拒绝读取"（或"旧版本读到新类型会拒绝"）即 +2。错误：说不认识的事件会被静默跳过 | packages/core/session/src/types.ts:500-511；packages/session/session-persistence/src/storage-contract.ts:55-80；AGENTS.md:135 |
| B6 | 插件自己写会话事件的后果 | 已知类型表由仓库内声明的 SessionEventMap 生成，仓库外插件新增的类型按定义不在表里。插件运行中写事件用的 Session.append 只写 type、seq、time、data 和 surface 字段，没有参数能加 ignorable；ignorable 只在用 seed 创建或恢复会话时从已有记录里原样保留。所以仓库外插件经 Session.append 把记忆写成自定义会话事件，追加时不报错，这份会话下次加载却会被拒绝。可行的做法是把事件类型加进仓库并重新生成已知类型表，或者把记忆放在会话日志之外。给分：写出这条限制即 +2，说法不限。只说"自定义事件要标 ignorable"、没指出插件经 Session.append 加不上的，不算写出这条限制（记 0），也不算错。错误：说插件经 Session.append 写的事件可以带 ignorable；说仓库外插件不带 ignorable 的自定义事件下次加载时会被跳过或照常读取 | packages/core/session/src/known-event-types.ts:1-21；packages/core/session/src/index.ts:205-233、722-750；packages/session/session-persistence/src/storage-contract.ts:55-80；packages/session/session-persistence-jsonl/src/index.ts:675、807；.agents/notes/implemented/architecture/2026-08-30-retain-ignorable-external-session-events.md:13-15 |
| B7 | 模型窗口能怎样改 | 只有 5 类事件能成为模型可见窗口（surface）里的节点：system/message、developer/message、user/message、assistant/message、tool/result。节点进窗口只有 append（追加）和 replace 两种：replace 用一个新节点替换 startSeq 到 endSeq 一段，新节点的 sourceEventSeqs 要列出所有被遮蔽的节点。没有删除节点或日志事件的操作。其他事件（含插件自定义事件）不能带 surfaceOp 和 sourceEventSeqs，不会成为窗口节点。另有一种只改内容、不增删节点的方式：SessionEventMap 里标了 @messageProjection 的事件，由所属插件经 ctx.sessions.registerMessageProjection() 注册纯函数，改写已有消息的内容，消息身份不变，原事件仍在日志里；仓库里目前只有 compaction-image-offload 的 image/offload（从之后的请求里去掉选中的图片）。仓库外插件也能注册这种函数，但它的事件类型不在已知类型表里，会话下次加载会被拒绝（见 B6）。给分：写对下面任一点即 +2：①非 surface 事件（或插件自定义事件）不能带 surfaceOp、sourceEventSeqs，不会成为窗口节点；②窗口节点只能追加或替换，没有删除；③可以用 message projection 事件改写已有消息的内容，不增删节点。错误：说可以直接删除窗口里的节点或日志里的事件；说自定义事件本身会作为一条新消息出现在模型上下文里 | packages/core/session/src/types.ts:433-444、449-464、486-491、512-515；packages/core/session/src/surface.ts:34-46、308-318、529-537、573-583；packages/core/session/README.md:50、54；packages/core/session/src/index.ts:942-950；packages/core/session/src/known-event-types.ts:84-87；packages/compaction/compaction-image-offload/src/projection.ts:16-26；.agents/notes/implemented/architecture/2026-09-11-plugin-owned-message-projections.md:13-15 |
| B8 | 压缩怎样处理原文 | 只遮蔽、不删除：压缩用一条带 surfaceOp: { op: 'replace', startSeq, endSeq } 的 user/message 摘要替换旧区间，原事件留在日志里，只是不再出现在推导出的消息中，回放结果不变；摘要的 sourceEventSeqs 列出了被遮蔽的事件，可以据此找回原文。给分：写出遮蔽不删、原文还在日志里即 +2。错误：说压缩会删除或改写原消息 | packages/compaction/compaction/README.md:12、95-97、143；packages/compaction/compaction-basic/src/region.ts:506-509；packages/core/session/README.md:12、150 |
| B9 | AGENTS.md 怎样进入上下文 | dsh-agent-instructions（base 默认启用，预算 maxBytes 65536）在会话第一次请求前（第一个 agent/pre-step），把 $DSH_HOME/AGENTS.md 和从项目根到工作目录的各级 AGENTS.md、CLAUDE.md 拼成一条用 <system-reminder> 包着的持久 user/message，放在本轮用户消息之后；之后 read、write、edit 碰到更深的目录时补上新文件，改过的替换，删掉的发移除通知。它不是 system prompt 的一节。给分：写出"作为 user 消息、第一次请求前注入、会进日志"这种注入方式即 +2。错误：说成 system prompt 的一节。docs/cookbook/extension-cookbook.md:113 是这样写的，但与实现不符；指出了这处不一致的不算错 | packages/context/agent-instructions/README.md:12、28、32、86、102；packages/context/agent-instructions/src/index.ts:1-5、315-341；packages/bundle/base/cordis.patch.yml:289-292 |
| B10 | 跨会话检索默认能不能用 | 默认不能。base 里 session-query-sqlite 设 openAt: never：ctx.sessionQuery 仍可按 id 精确读、读标题和父子关系，但搜索调用报 SESSION_QUERY_SEARCH_DISABLED。模型侧的会话检索工具 tool-session-query 不在任何 bundle 补丁里，仓库里只有测试快照 snapshots/session/session-query-spill/cordis.yml 加载它；装上后也只放行 cwd 和调用方完全相同的会话，不能跨项目查。给分：写出全文检索默认关闭，或检索工具默认不装，即 +2。错误：说跨会话搜索默认可用；说装上 tool-session-query 就能跨项目检索 | packages/bundle/base/cordis.patch.yml:141-153；packages/bundle/web-app/cordis.patch.yml:22-30；packages/session-query/tool-session-query/README.md:12 |
| B11 | 宿主侧持久存储 | ctx.storageDomain（dsh-storage、storage-domain、storage-json）保存不进会话历史的应用数据：按 schema 校验的键值域，写入落盘后才返回；只供宿主代码用，不加工具、提示或会话事件，模型看不到；base 用 json 后端，目录 $DSH_HOME/storages。给分：写出它能存不进会话日志的持久数据、模型看不到即 +2。错误：说它自带检索或全文搜索；说写进去的数据会自动进入模型上下文或会话日志 | packages/storage/storage/README.md:12；packages/storage/storage-domain/README.md:12；packages/bundle/base/cordis.patch.yml:165-176 |
| B12 | 注入的记忆会不会留在日志里 | 会。进入模型请求的内容都必须能从会话日志重建（仓库规则"Model-visible ⟺ logged"）。agent.inject() 把上下文排进下一步，作为持久的 user/message 写进日志；按 types.ts 的说明，文件变更通知、子目录 AGENTS.md、技能内容也是这样注入的。所以召回的记忆一旦注入，原文就永久留在日志里，可以追溯；之后只能在窗口里用 replace 遮蔽或用 message projection 改写（见 B7），日志里的原文不会消失。给分：写出注入的内容会作为 user/message（或 system/message）持久记录，或写出"模型可见即入日志"，即 +2。错误：说注入只是临时的、不进日志；说可以只在请求里临时拼接而不记日志 | AGENTS.md:138；packages/core/session/README.md:88；packages/core/agent/src/runtime-types.ts:233-241；packages/core/session/src/types.ts:302-309 |

### C 来源与诚实

| 编号 | 条目 |
|---|---|
| C1 | 关键结论附了"路径:行号"：抽 10 条关键结论（不足 10 条全抽），全部附了记 2 分，一半以上附了记 1 分，不到一半记 0 分 |
| C2 | 抽查 5 处"路径:行号"：脚本按运行编号固定抽取（不足 5 处全抽），给出快照里该处前后各 5 行原文。片段支持文中那句说法算"支持"；路径不存在或行号超出文件算"找不到"，按不支持计。5 处都支持记 2 分；支持的处数不少于一半（部分支持算半处）记 1 分；其余记 0 分；文中没有任何"路径:行号"记 0 分 |
| C3 ★ | 没有编造的包名、文件、API、配置项或事件类型：把快照里不存在的东西当成现有的写出来，发现一处即记严重错误。写明是新增或建议的不算（判定细则 4）；名字存在但说错作用或范围的是归错，扣在对应 B 条，不算编造 |
| C4 | 难度判断有依据：每个难度等级都指出难在哪段代码或哪条限制；没核实的写明"待核验"或"未核实" |

### D 可用性

| 编号 | 条目 |
|---|---|
| D1 | 实现路径能照着做：分阶段，每阶段写清用哪些扩展点或包、产出什么、先做什么 |
| D2 | 结论和正文一致：摘要、难度表和正文对同一件事说法相同（判定细则 6） |
| D3 | 不堆砌：围绕题目，没有大段重复、与记忆插件无关的仓库介绍或大段照抄代码 |
