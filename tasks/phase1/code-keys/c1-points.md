# c1 答案键：22 个要点（快照 dsh-cc0fb5f8b7 逐条核对）

不给被测模型看。主批次开跑前按方案附录 C 把本目录设为 chmod 000，判分前再改回。

题面（tasks/code.jsonl 的 c1，与 tasks/pilot.jsonl 第 1 行逐字相同）：

> 这个仓库是 DeepSeek Harness 的源码。请调研：子代理（subagent）的“同时存活数量上限”和“递归深度上限”分别在哪里实现、默认值是多少、在什么时机检查、各自对哪些子代理不起作用。写到 answer.md，每条结论附文件路径和行号。

## 由来和核对方法

- 由 tasks/answer-keys.md 的 c1 六条拆成 22 个要点（方案 2.1）：
  - 第 1 条（同时存活上限的名称、默认值、位置）：P1–P3；
  - 第 2 条（深度上限的名称、默认值、同一个 Config、工具行写法）：P4–P7；
  - 第 3 条（同时存活上限的检查时机、实现、报错、共享方式）：P8–P11；
  - 第 4 条（不计入同时存活上限的五类子代理）：P12–P16；
  - 第 5 条（深度上限的检查时机、实现、报错、两条路径）：P17–P20；
  - 第 6 条（workflow 自己的上限）：P21–P22。
- 每个要点都打开快照里的源码或 README 读到行，下面"核对"一栏摘了原文。除了名字和数字出现，还核对了适用对象和方向：它管哪些子代理、在什么时机生效、往哪个方向限制。
- 路径都相对快照根目录 /Users/ziya/harness/subagent-experiment/data/repos/dsh-cc0fb5f8b7。
- 判分口径与 rubrics/code-rubrics.md 的"计分 / c1"一致：
  - 每个要点判"对 / 错 / 没提到"，对记 1 分；
  - 得分 = 对的个数 ÷ 22 × 100；
  - 答错的个数、编造位置数另记，不计分。

## 要点总表

| 编号 | 原条目 | 要点 | 正确内容 | 快照位置 |
|---|---|---|---|---|
| P1 | 1 | 同时存活上限叫什么 | `maxActiveSubagents` | packages/subagent/subagent/src/index.ts:193-194、203 |
| P2 | 1 | 默认值 | 8 | packages/subagent/subagent/src/index.ts:193、203 |
| P3 | 1 | 定义在哪 | dsh-subagent 服务（`SubagentRuntime`）的 Config | packages/subagent/subagent/src/index.ts:191-204 |
| P4 | 2 | 深度上限叫什么 | `maxDepth` | packages/subagent/subagent/src/index.ts:195-196、202 |
| P5 | 2 | 默认值 | 1（0 表示不能委派） | packages/subagent/subagent/src/index.ts:195、202 |
| P6 | 2 | 同一个 Config | 两个字段同在 `SubagentRuntime` 的 Config | packages/subagent/subagent/src/index.ts:192-204 |
| P7 | 2 | 工具行可单独设深度 | 写死整数，或 `'provider-managed'`；不写时每次委派读 Host 当前设置 | packages/subagent/tool-subagent/src/index.ts:93-103、130、514 |
| P8 | 3 | 同时存活上限何时检查 | 新建和冷恢复可续聊子代理时，重建 Agent 之前 | packages/subagent/subagent/src/continuation-activation.ts:484-489 |
| P9 | 3 | 检查代码 | `ActivationPool.reserve` | packages/subagent/subagent/src/continuation-activation.ts:40-56、489 |
| P10 | 3 | 报错 | `subagent limit reached (active child limit: N); …`，错误码 `ACTIVATION_LIMIT_REACHED` | packages/subagent/subagent/src/continuation-activation.ts:47-50 |
| P11 | 3 | 名额池怎么共享 | 非可续聊父代理（如根代理）的可续聊后代共用一个池 | packages/subagent/subagent/src/continuation-activation.ts:488、604-612 |
| P12 | 4 | 不计入：前台一次性子代理 | `run_in_background: false` 走一次性路径 | packages/subagent/subagent/src/continuation.ts:76-81 |
| P13 | 4 | 不计入：一次性后台任务 | `backgroundMode: one-shot` 的后台 job | packages/subagent/tool-subagent/src/index.ts:544-556 |
| P14 | 4 | 不计入：workflow 的 `agent()` | workflow-ptc 走一次性路径启动 | packages/workflow/workflow-ptc/src/host.ts:197-211 |
| P15 | 4 | 不计入：外部 provider | codex、claude-code 等不能可续聊 | packages/subagent/subagent-codex/src/index.ts:64 |
| P16 | 4 | 不计入：池的所有者本身 | 根代理自己不占名额 | packages/subagent/subagent/README.md:51 |
| P17 | 5 | 深度上限何时检查 | 每次启动子代理时 | packages/subagent/tool-subagent/src/index.ts:97-98、514 |
| P18 | 5 | 检查代码 | `resolveChildDepth` | packages/subagent/subagent/src/child-agent.ts:50-58 |
| P19 | 5 | 报错 | `subagent depth N exceeds maxDepth M` | packages/subagent/subagent/src/child-agent.ts:33-38 |
| P20 | 5 | 两条路径都查 | 一次性：`startInProcessRun`；可续聊：`startContinuable` | packages/subagent/subagent-in-process-driver/src/index.ts:111；packages/subagent/subagent/src/continuation.ts:112 |
| P21 | 6 | workflow 总数上限 | `maxTotalAgents` 默认 1000 | packages/workflow/workflow-ptc/src/index.ts:37-38、108 |
| P22 | 6 | workflow 并发上限 | `min(16, max(1, 可用 CPU 数 − 2))` | packages/workflow/workflow-ptc/src/index.ts:35-36、141-143 |

## 逐条说明

### 第 1 条：同时存活上限的名称、默认值、位置

**P1 名称。**
- 正确内容：`maxActiveSubagents`，限制同时存活的子代理数。
- 给分：写出这个配置名，并说明它是同时存活数量上限。
- 核对：
  - packages/subagent/subagent/src/index.ts:193-194：`/** Maximum live children sharing uninterrupted continuable parent links; defaults to 8. */ maxActiveSubagents: Volatile<number>`。

**P2 默认值。**
- 正确内容：8。
- 给分：写出 `maxActiveSubagents` 默认 8。
- 核对：
  - packages/subagent/subagent/src/index.ts:203：`maxActiveSubagents: z.number().step(1).min(1).max(Number.MAX_SAFE_INTEGER).default(8).volatile()`；
  - packages/subagent/subagent/README.md:51："It defaults to `8` and accepts positive safe integers."

**P3 位置。**
- 正确内容：Host 上 `dsh-subagent` 服务的配置，即 `SubagentRuntime` 的 Config，文件 packages/subagent/subagent/src/index.ts。接口在 192-197 行，schema（`static Config`）在 201-204 行。
- 给分：写出这个文件；行号在 191-204 前后 5 行内，或明确指出是 `SubagentRuntime` 的 Config。
- 不给分：只给出检查处（continuation-activation.ts），没有给出定义处。
- 核对：
  - packages/subagent/subagent/src/index.ts:191：`/** Host configuration for continuable subagent capacity. */`；
  - 200-204：`export class SubagentRuntime … static Config = z.object({ maxDepth: …, maxActiveSubagents: … })`；
  - packages/subagent/subagent/README.md:51："Set `maxActiveSubagents` on the host `dsh-subagent` plugin"。

### 第 2 条：深度上限的名称、默认值、同一个 Config、工具行写法

**P4 名称。**
- 正确内容：`maxDepth`，限制委派的递归深度。
- 给分：写出这个配置名，并说明是深度上限。
- 核对：packages/subagent/subagent/src/index.ts:195-196：`/** Default delegation depth for tools without an explicit limit; defaults to 1. */ maxDepth: Volatile<number>`。

**P5 默认值。**
- 正确内容：1，只允许直接子代理；0 表示通过继承这个设置的工具不能委派。
- 给分：写出默认 1。
- 判错：写成 3（旧默认）或其他值。
- 核对：
  - packages/subagent/subagent/src/index.ts:202：`maxDepth: z.number().step(1).min(0)….default(1).volatile()`；
  - packages/subagent/subagent/README.md:47："`maxDepth` defaults to `1` … Depth `0` disables delegation through tools inheriting this setting; depth `1` permits direct children only."

**P6 同一个 Config。**
- 正确内容：`maxDepth` 和 `maxActiveSubagents` 同在 `SubagentRuntime` 的 Config 里，对应 Host 的 `subagent` 设置（设置页 Plugins → Subagent 的 limits 一节）。
- 给分：写明两者在同一个 Config 或同一个服务设置里，或给出 packages/subagent/subagent/src/index.ts 191-204 行内的定义位置。
- 核对：
  - packages/subagent/subagent/src/index.ts:192-197、201-204；
  - packages/subagent/subagent/README.md:47："The limits section on the **Plugins → Subagent** page edits the Host’s `subagent` settings section."

**P7 委派工具行可以单独设深度。**
- 正确内容：tool-subagent 的每一行配置都可以写 `maxDepth`：
  - 写一个非负整数（写死）；
  - 或写 `'provider-managed'`：不发上限，交给进程外 provider 自管；
  - 不写时，每次委派读 Host 当前的 `subagent.maxDepth`（默认 1）。
- 给分：写出工具行可以显式设置深度，数值或 `provider-managed` 至少提到一种。"不写时每次读当前设置"可以不提。
- 核对：
  - packages/subagent/tool-subagent/src/index.ts:93-103：注释原文 "Maximum child depth: a non-negative safe integer (0 forbids delegation), or 'provider-managed' to send no cap. … Omission reads the current Host subagent depth setting (default 1) at each delegation."，声明 `maxDepth?: number | 'provider-managed'`；
  - 130 行 schema：`maxDepth: z.union([z.natural().max(Number.MAX_SAFE_INTEGER), z.const('provider-managed' as const)])`，没有默认值；
  - 514 行（每次调用时执行）：`const maxDepth = runtimeCtx.subagents.resolveMaxDepth(config.maxDepth)`；
  - packages/subagent/subagent/src/index.ts:244-250 `resolveMaxDepth`：`'provider-managed'` 返回 undefined，显式数值原样返回，不写时读 `this.config.maxDepth.get()`；
  - 实例：packages/bundle/web-app/presets/standard.patch.yml:103-118，codex、claude-code 两行写了 `maxDepth: provider-managed`。

### 第 3 条：同时存活上限的检查时机、实现、报错、共享方式

**P8 检查时机。**
- 正确内容：只在新建可续聊（continuable）子代理、冷恢复已落盘的可续聊子代理时检查，而且在重建 Agent 之前就预占名额。
  - 新建：`startContinuable` → `materialize`；
  - 冷恢复：父代理给不在内存里的直接子代理发消息时，`coldResume` → `materialize`。
- 给分：新建和冷恢复两种时机都要写到。
- 判错：说成每次调用 subagent 工具都检查（包括一次性子代理）。
- 核对：
  - packages/subagent/subagent/src/continuation-activation.ts:484-489：`materialize(inputs)` 里 `const releaseSlot = pool.reserve(this.maxActiveSubagents())`；
  - packages/subagent/subagent/src/continuation.ts:161（新建）、436（冷恢复）都调用 `this.activations.materialize(…)`；
  - packages/subagent/subagent/README.md:51："Fresh creation and cold resume reserve before reconstructing the Agent"；
  - packages/subagent/subagent/README.md:53："sampled before every new or cold-resumed Activation"。

**P9 检查代码。**
- 正确内容：continuation-activation.ts 的 `ActivationPool.reserve`：
  - 池里已占名额数 ≥ 上限就抛错；
  - 否则占一个名额，返回释放函数；
  - 唯一调用点在 `materialize`：`pool.reserve(this.maxActiveSubagents())`，上限每次现读。
- 给分：写出 `ActivationPool.reserve`（或 reserve 的调用点）和文件 continuation-activation.ts。
- 核对：
  - packages/subagent/subagent/src/continuation-activation.ts:40-56：`class ActivationPool { private readonly slots = new Set<symbol>() … reserve(capacity: number) { if (this.slots.size >= capacity) { throw … } … } }`；
  - 489 行调用。方案 2.1 写的 41-48 行在这个范围内。

**P10 报错。**
- 正确内容：
  - 报错文字：`subagent limit reached (active child limit: ${capacity}); wait for an existing child to finish or complete this work with the current agents`；
  - 错误码 `ACTIVATION_LIMIT_REACHED`；
  - 满了直接拒绝，不排队。
- 给分：写出报错文字开头 `subagent limit reached`，或错误码 `ACTIVATION_LIMIT_REACHED`，二者之一。
- 判错：说成满了会排队等待。
- 核对：
  - packages/subagent/subagent/src/continuation-activation.ts:47-50；
  - packages/subagent/subagent/README.md:55："At capacity, creation or cold resume rejects with `ACTIVATION_LIMIT_REACHED` … Admission does not queue"。

**P11 名额池怎么共享。**
- 正确内容：名额池沿连续的可续聊父子关系共享：
  - 每个非可续聊的父代理（例如根代理）有一个池；
  - 它的可续聊子代理，以及这些子代理再开的可续聊后代，共用这个池；
  - 一次性父代理下面的可续聊子代理另开一个池；
  - 不同根会话的池互不相干。
- 给分：写出根代理（或非可续聊父代理）的可续聊后代共用一个池，即整棵可续聊子树共享这个上限。
- 判错：
  - 说成每个父代理（包括可续聊的父代理）都各有 N 个名额。注意"每个非可续聊父代理各有一个池"是对的：一次性子代理开的可续聊子代理就另得 N 个；
  - 说成整个进程、所有会话共用 N 个。
- 核对：
  - packages/subagent/subagent/src/continuation-activation.ts:40：`Process-local slots shared through uninterrupted continuable parent links.`；
  - 65 行：`Shared capacity for this Activation and all its continuable descendants.`；
  - 488 行：`const pool = this.resident.get(inputs.parent.id)?.pool ?? this.rootPool(inputs.parent)`，父代理是驻留的可续聊子代理时沿用它的池，否则取父代理自己的池；
  - 604-612 行 `rootPool(parent)`：按父代理建池，存在 `rootPools`（180 行，`WeakMap<Agent, ActivationPool>`）；
  - packages/subagent/subagent/README.md:51："A non-continuable parent starts a separate pool … continuable descendants inherit that pool. … Pool inheritance does not cross a one-shot parent"。

### 第 4 条：不计入同时存活上限的五类子代理

总依据：packages/subagent/subagent/README.md:51："One-shot and external-provider runs are outside this limit."；只有走 `materialize` 的可续聊子代理才占名额（P8）。

**P12 前台一次性子代理。**
- 正确内容：`run_in_background: false` 的前台调用走 `ctx.subagents.start()`（一次性），不进名额池。工具行是 continuable 模式时也一样。
- 给分：写出前台或一次性子代理不计入。
- 核对：
  - packages/subagent/subagent/src/continuation.ts:76-81：注释原文 "foreground one-shot delegation keeps calling ctx.subagents.start() and never enters this lifecycle."；
  - packages/subagent/tool-subagent/src/index.ts:563-567：前台路径 `runtimeCtx.subagents.start(config.provider, …)`；
  - packages/subagent/tool-subagent/README.md:61："Set `run_in_background: false` to wait for the result in the foreground."

**P13 一次性后台任务。**
- 正确内容：工具行 `backgroundMode: one-shot` 时，`run_in_background: true` 启动的是普通后台 job（用 `job_output` 取结果），内部仍调 `ctx.subagents.start()`，不进名额池。
- 给分：写出一次性的后台任务（后台 job）不计入。
- 不给分：只写"一次性子代理不计入"，没提后台。
- 核对：
  - packages/subagent/tool-subagent/src/index.ts:544-556：`jobs.start({ kind: 'subagent', … run: () => { … runtimeCtx.subagents.start(config.provider, …) … } })`；
  - packages/subagent/tool-subagent/README.md:59："`run_in_background: true` starts a plain parent-owned background job"。

**P14 workflow 的 `agent()` 子代理。**
- 正确内容：workflow 脚本里的 `agent()` 由 workflow-ptc 用 `ctx.subagents.start()`（一次性）启动，不进名额池。workflow 另有自己的上限，见 P21、P22。
- 给分：明确写出 workflow 开的子代理不受 `maxActiveSubagents` 限制。
- 不给分：只在深度部分提到 workflow。
- 核对：
  - packages/workflow/workflow-ptc/src/host.ts:197-211：`startChild` 里 `const run = await this.subagents.start(this.provider, { prompt: …, parent: this.parent, … })`。

**P15 外部 provider。**
- 正确内容：codex、claude-code 等进程外 provider（另有 acp、dsh-sdk）没有 `prepareContinuable`，不能当可续聊子代理用，只能一次性运行，不进名额池。
- 给分：写出外部（进程外）provider 不计入，点名 codex 或 claude-code 之一即可。
- 核对：
  - packages/subagent/subagent-codex/src/index.ts:64、packages/subagent/subagent-claude-code/src/index.ts:74：`readonly capabilities: SubagentCapabilities = NO_START_CAPABILITIES`，两个类都没有 `prepareContinuable`；
  - packages/subagent/subagent/src/index.ts:596-609：没有 `prepareContinuable` 的 provider 走可续聊会被拒（`UNSUPPORTED_CAPABILITY`）；
  - packages/subagent/tool-subagent/src/index.ts:345-349：continuable 工具行配这种 provider 会在挂载时报错；
  - packages/bundle/web-app/presets/standard.patch.yml:103-118：codex、claude-code 两行是 `backgroundMode: one-shot`。

**P16 池的所有者本身。**
- 正确内容：拥有名额池的非可续聊父代理（例如根代理）自己不占名额。
- 给分：写出根代理或池的所有者自己不计入。
- 核对：
  - packages/subagent/subagent/README.md:51："A non-continuable parent starts a separate pool and does not consume a slot"；
  - packages/subagent/subagent/src/continuation-activation.ts:604-612：池按父代理建，只有子代理在 `materialize` 时占名额；
  - .agents/notes/implemented/feature/2026-09-15-continuable-activation-capacity.md:13："The pool owner itself is excluded."

### 第 5 条：深度上限的检查时机、实现、报错、两条路径

**P17 检查时机。**
- 正确内容：
  - 每次启动子代理时检查，读的是当前设置，改了下一次委派就生效；
  - 工具在上限处仍然可见，超限的调用返回错误结果。
- 给分：写出每次启动或每次委派都检查。
- 判错：说成只在加载配置时检查。
- 核对：
  - packages/subagent/tool-subagent/src/index.ts:97-98：`The provider checks the calling agent's current depth at every start; the tool remains model-visible so runtime policy owns rejection.`；
  - 514 行每次调用时取 `resolveMaxDepth`；
  - packages/subagent/tool-subagent/README.md:63："each attempted start checks the calling agent's current depth and rejects with an errored result"；
  - packages/subagent/subagent/README.md:47："Changes apply on the next delegation attempt."

**P18 检查代码。**
- 正确内容：child-agent.ts 的 `resolveChildDepth(parent, maxDepth)`：
  - 子代理深度 = 父代理深度 + 1，父代理深度取持久化的 header 和运行时选项中较大的一个；
  - `maxDepth` 有值且子代理深度大于它时，抛 `SubagentDepthError`。
- 给分：写出 `resolveChildDepth` 和文件 child-agent.ts。
- 核对：
  - packages/subagent/subagent/src/child-agent.ts:50-58：`const childDepth = delegationDepthOf(parent) + 1 … if (maxDepth !== undefined && childDepth > maxDepth) { throw new SubagentDepthError(childDepth, maxDepth) }`；
  - packages/subagent/subagent/src/depth.ts:28-36 `delegationDepthOf`。

**P19 报错。**
- 正确内容：`subagent depth N exceeds maxDepth M`（`SubagentDepthError`）。
- 给分：写出这句报错（N、M 可写成具体数字），或写出 `SubagentDepthError`。
- 核对：packages/subagent/subagent/src/child-agent.ts:33-38：``super(`subagent depth ${attemptedDepth} exceeds maxDepth ${maxDepth}`)``。

**P20 两条路径都检查。**
- 正确内容：
  - 一次性子代理：在共享驱动 `startInProcessRun` 里检查，spawn、fork 两个进程内 provider 都用这个驱动；
  - 可续聊子代理：在 `startContinuable` 里检查，早于名额预占。
- 给分：写出两条路径都检查。给出两个调用点之一、并说明两条都查，也算对。
- 判错：说成可续聊或后台子代理不查深度。
- 核对：
  - packages/subagent/subagent-in-process-driver/src/index.ts:104-111：`export async function startInProcessRun(…) { … const childDepth = resolveChildDepth(parent, request.maxDepth)`；
  - packages/subagent/subagent-spawn-in-process/src/index.ts:58、packages/subagent/subagent-fork-in-process/src/index.ts:78 都调用 `startInProcessRun`；
  - packages/subagent/subagent/src/continuation.ts:112：`const childDepth = resolveChildDepth(parent, request.maxDepth)`，在 161 行 `materialize` 之前。

### 第 6 条：workflow 自己的上限

**P21 总数上限。**
- 正确内容：workflow-ptc 的 `maxTotalAgents`，默认 1000，指一次 workflow 运行最多启动的 `agent()` 数。
- 给分：写出 1000，并说明是 workflow 的上限。
- 核对：
  - packages/workflow/workflow-ptc/src/index.ts:37-38：注释原文 "Total agent() calls one run may start — the runaway-loop backstop (default 1000)."；
  - 108 行：`maxTotalAgents: z.natural().min(1).default(1000)`。

**P22 并发上限。**
- 正确内容：`maxConcurrentAgents` 默认 0，表示自动取 `min(16, max(1, availableParallelism() − 2))`，即可用 CPU 数减 2、最少 1、最多 16。
- 给分：写出 min(16, 核数 − 2)，带不带 max(1, …) 都算对，并说明是 workflow 的并发上限。
- 核对：
  - packages/workflow/workflow-ptc/src/index.ts:35-36：`` `0` (the default) auto-resolves to `min(16, max(1, cores - 2))` ``；
  - 107 行：`maxConcurrentAgents: z.natural().default(0)`；
  - 141-143 行：`Math.min(16, Math.max(1, availableParallelism() - 2))`。

## 不计分、答出来也对的内容

答案里出现下面这些，不加分，也不能当成错误：

- **深度上限对 workflow 的 `agent()` 不起作用。** packages/workflow/workflow-ptc/src/host.ts:200-211 调 `subagents.start` 时不带 `maxDepth`；`resolveChildDepth` 只在 `maxDepth` 有值时比较（packages/subagent/subagent/src/child-agent.ts:55）。
- **`'provider-managed'` 的工具行不向 provider 发深度上限，由外部 provider 自管。** 见 packages/subagent/subagent/src/index.ts:245；数值上限要求 provider 有 `depthLimit` 能力，否则挂载时报错（packages/subagent/tool-subagent/src/index.ts:329-333）。
- **冷恢复不重新检查深度。** packages/subagent/subagent/src/continuation.ts:406-456 没有调用 `resolveChildDepth`。深度从持久化的 header 取，恢复的子代理不会被当成顶层（packages/subagent/subagent/src/depth.ts:20-36）。
- **取值范围。** `maxActiveSubagents` 最小 1，`maxDepth` 最小 0（packages/subagent/subagent/src/index.ts:202-203）。
- **上限每次现读。** 每次新建、冷恢复前都读当前值；调低后，已驻留的子代理继续运行，用量降到上限以下之前拒绝新的（packages/subagent/subagent/README.md:53）。
- **哪些情况仍占名额。** 等待后代的父代理、收件箱还有待处理内容的、正在停止的仍占名额；给已驻留的子代理发消息复用它的名额（packages/subagent/subagent/README.md:51）；handle 释放后才归还名额（packages/subagent/subagent/src/continuation-activation.ts:863）。
- **浏览器侧的报错。** 浏览器续聊提示收到的是 `subagent/delivery-unavailable`（packages/subagent/subagent/README.md:55）。
- **名额只在本进程内有效。** 不限制累计的会话历史或 token 用量（packages/subagent/subagent/README.md:55）。

## 和 tasks/answer-keys.md、方案 2.1 的差别

- **第 3 条"根代理的可续聊后代共用一个池"。** 更准确的说法是：每个非可续聊父代理（根代理或一次性子代理）各有一个池，一次性父代理下面的可续聊子代理另开池（packages/subagent/subagent/README.md:51；packages/subagent/subagent/src/continuation-activation.ts:488、604-612）。P11 按这个口径判；只写"根代理的可续聊后代共用一个池"也给分。
- **第 6 条并发写的是"min(16, CPU 核数 − 2)"。** 代码是 `min(16, max(1, availableParallelism() − 2))`，下限为 1（packages/workflow/workflow-ptc/src/index.ts:142）。P22 两种写法都给分。
- **方案 2.1 写的行号。**
  - 方案写的 continuation-activation.ts 41-48 行，在本文的 40-56 行范围内：类在 41 行，`reserve` 在 45-55 行，调用点在 489 行。
  - 方案写的 packages/subagent/subagent/src/index.ts:200-203、packages/subagent/subagent/src/child-agent.ts:50、packages/workflow/workflow-ptc/src/index.ts:108、142 与快照一致。
