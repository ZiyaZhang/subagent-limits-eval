# c2 评分标准：12 个互相独立的源码调研题

- 答案键以快照 data/repos/dsh-cc0fb5f8b7 为准，路径都相对快照根目录。每个要点的依据逐行摘录在 tasks-draft/c2/evidence.json（脚本核对过每一行都和快照原文一致）。
- 每题只问一个包（个别题涉及同一目录下相邻的两个包，已在"所在包"里写明），题与题之间没有依赖。
- 判分模型看到本文件的"计分"一节和"c2"一节。

## 计分

### c2：12 个问题、48 个要点

- 每个要点判"对 / 错 / 没提到"：对记 1 分，错和没提到记 0 分。
- 得分 = 对的要点数 ÷ 48 × 100，两次判分取平均。
- 另记两项，不计分，报告里单列：
  - 答错的要点数，即判"错"的个数；
  - 编造位置数：答案里写的"路径:行号"在快照里找不到的次数。由脚本数，打分模型不用数。
- 给分要求：
  1. 内容和适用对象都要对。名字、数字写对了，但说错了它管什么、在什么时机生效，判错。
  2. 一句话覆盖几个要点时分别给分；一个要点分散在几处写，合起来判。答案写在别的问题那一节里，只要内容对，照样给分。
  3. 给分条件里要求指到某个文件、函数或位置的，行号落在答案键范围内、前后 5 行内或指向同一个声明、函数，都算对；文件写错判错。其他要点不要求位置。
  4. 多写的正确内容不加分。多写的错误内容，只有和某个要点矛盾时才把那个要点判错。每题表后"不计分、答出来也不算错的内容"既不加分也不扣分。
  5. 标了"待核验"的要点，内容对算对，内容错算错。
  6. 包内实现的默认值和 bundle 出厂配置不是一回事。题目问"默认值"指包内实现（`src/*.ts`）的默认；答案另外写出 base bundle 的配置值并注明来自 bundle，不算错；把 bundle 的值说成包内默认值，按对应要点的给分条件处理。

### 判定细则

1. **编造和归错都判错。** 编造：快照里不存在的包、文件、函数、配置项、事件类型，被当成现有的写出来。归错：名字或数字在快照里有，但说错了它管谁、在什么时机、往哪个方向生效。
2. **以快照为准。** 仓库文档和实现不一致时以实现为准；照文档写、又没指出不一致的，按错误记。
3. **只按内容判。** 写到了但没附位置，除给分条件明确要求位置的要点外，照样按内容给分。
4. **不要因为文件长、来源多、排版好就加分。**

## c2 12 个互相独立的源码调研题

总题面：这个仓库是 DeepSeek Harness 的源码。下面有 12 个互相独立的问题，每个问题问仓库里的一个包或一种机制。逐题调研并回答，写到 answer.md，每题一节，每条结论附文件路径和行号。

### Q01 自动上下文压缩什么时候触发

题面：自动上下文压缩在哪里实现、在什么时机检查要不要压缩？写出压力阈值和"保留最近对话"两个比例的默认值，以及模型请求报上下文超限时它怎么处理。

所在包：packages/compaction/compaction-basic

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q01-1 | 压力检查的时机和位置 | `BasicCompactionEngine` 在 `auto` 为 true（默认）时注册 `agent/pre-step` 监听：每一步（step）开始、发模型请求之前调用 `compactIfNeeded(agent, 'pressure')`。实现在 packages/compaction/compaction-basic/src/index.ts。给分：写出"每一步请求前"或 `agent/pre-step`，并指到 compaction-basic 的 src/index.ts（行号在 140-176 前后 5 行内，或点名 `_registerAutomaticCompaction`、`compactIfNeeded`）。说成每轮（turn）结束后、收到用户消息时或工具返回后检查，判错 | packages/compaction/compaction-basic/src/index.ts:140、158-176 |
| Q01-2 | 压力阈值 | `thresholdRatio` 默认 0.8。阈值 = floor(min(上下文窗口 × 0.8, 上下文窗口 − 输出预留 − `headroomTokens`))，`headroomTokens` 默认 65536；估算的总 token 数 ≥ 阈值才压缩。给分：写出默认 0.8（或 80%），并说明是上下文窗口的比例。只写 65536、没写 0.8 的不给分；比例写成其他数判错 | packages/compaction/compaction-basic/src/config.ts:20、75、172-194；packages/compaction/compaction-basic/src/index.ts:319 |
| Q01-3 | 保留最近对话的比例 | `retainRatio` 默认 0.16：最近的对话按（上下文窗口 − 输出预留）× 0.16 的 token 预算原样保留，更早的部分才被摘要替换。给分：写出 0.16（或 16%），并说明是保留不压缩的尾部。写成其他数判错 | packages/compaction/compaction-basic/src/config.ts:23、195-197；packages/compaction/compaction-basic/src/index.ts:331 |
| Q01-4 | 上下文超限时的处理 | 监听 `agent/request-error`：失败码是 `CONTEXT_WINDOW_EXCEEDED` 时以 `context-overflow` 触发一次压缩（不看阈值、不保留尾部），窗口确实缩小后返回 `{ kind: 'retry' }` 重发请求；一次连续溢出里最多恢复 `maxOverflowRetries` 次，默认 1。给分：写出"上下文超限 → 压缩后重试"，并写出 `agent/request-error`、`CONTEXT_WINDOW_EXCEEDED`、`maxOverflowRetries` 默认 1 三者之一。说成超限时直接结束本轮或只报错，判错 | packages/compaction/compaction-basic/src/index.ts:190-234、294-302；packages/compaction/compaction-basic/src/config.ts:106；packages/llm/llm/src/error.ts:25 |

不计分、答出来也不算错的内容：`headroomTokens` 默认 65536；`compactionRetries` 默认 1；摘要输出上限 `maxTokens` 默认等于 headroomTokens；`auto: false` 时只剩手动 `/compact`；可用 `modelPolicies` 按 provider/model 覆盖；压缩前先调 toolResultPruner；base bundle 没有覆盖这些默认值。

### Q02 审批请求怎么判定

题面：审批服务（`ctx.approval`）有哪几种审批策略、默认是哪种，每种策略下一个审批请求会得到什么结果？写出结果的全部取值、没有人能应答时的结果，以及每次请求在会话日志里留下什么记录。

所在包：packages/interaction/user-approval

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q02-1 | 策略取值和默认 | `ApprovalPolicy` 只有 `ask` 和 `never` 两种，配置项 `policy` 默认 `ask`；单个会话可用 `approval/policy` 事件覆盖，最后一条为准。给分：写出 ask、never 两种且默认 ask | packages/interaction/user-approval/src/index.ts:67、151-153、243-245、252-259 |
| Q02-2 | never 的含义 | `never` 表示不向任何人询问，每个审批请求直接得到 `rejected`（在分发给 answerer 之前就决定）。给分：写出 never 下请求被自动拒绝。说成 never 表示不需要审批、自动放行，判错 | packages/interaction/user-approval/src/index.ts:61-65、270-275 |
| Q02-3 | 结果取值和无人应答 | 结果只有四种：`allowed-once`、`rejected`、`cancelled`、`unavailable`，唯一的放行是 `allowed-once`（只对这一次请求有效）。`ask` 下没有 answerer、answerer 抛错或返回表外的值，结果都是 `unavailable`（不放行）；请求的 signal 被中止是 `cancelled`。给分：写出四种结果中至少三种，并写出无人应答时为 `unavailable`、不放行。说成没有 answerer 时默认放行，判错 | packages/interaction/user-approval/src/types.ts:32；packages/interaction/user-approval/src/index.ts:55、267-292 |
| Q02-4 | 日志记录 | 每次 `request()` 往发起 agent 的会话日志追加一对事件：先 `approval/asked`（id、toolName、可选的 callId 和 reason），得到结果后 `approval/decided`（同一 id 加 outcome）。只能在未结束的 turn 内调用，否则抛错、什么都不写。给分：两个事件名都写出 | packages/interaction/user-approval/src/index.ts:215-234；packages/interaction/user-approval/src/types.ts:44-58 |

不计分、答出来也不算错的内容：当前策略通过 runtime context 的 `approval:policy` 一段告诉模型；`setPolicy` 切换时给模型注入一条策略变更通知；base bundle 在 `DSH_PERMISSION_MODE=danger-full-access` 时把 policy 配成 never（packages/bundle/base/cordis.patch.yml:245-248）。

### Q03 glob 和 grep 怎么实现、上限多少

题面：`glob` 和 `grep` 两个工具底层靠什么程序执行搜索、通过哪个服务启动它？写出两个工具各自内联保留的结果条数上限和默认超时。

所在包：packages/fs/tool-fs-search

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q03-1 | 底层实现 | 两个工具都运行随 npm 依赖分发的 ripgrep 二进制（`@vscode/ripgrep`，`resolveRgPath()`），用 `ctx.subprocess.spawn()` 以 argv 数组直接启动（前面加 `--no-config`）；不经过 `ctx.shell`，也不是 `ctx.fs` 的方法，不需要系统装 `rg`。给分：写出 ripgrep，并写出"经 `ctx.subprocess`（子进程服务）启动"或"不走 shell"之一。说成调用系统的 grep / find，或经 bash 工具执行，判错 | packages/fs/tool-fs-search/src/search-core.ts:171-184、238-248；packages/fs/tool-fs-search/src/index.ts:9-19、70 |
| Q03-2 | glob 条数上限 | `GLOB_MAX_RESULTS = 100`（配置项 `globMaxResults`）：一次最多内联返回 100 个路径。给分：写出 100 | packages/fs/tool-fs-search/src/glob.ts:21-25；packages/fs/tool-fs-search/src/index.ts:99 |
| Q03-3 | grep 条数上限 | `GREP_MAX_MATCHES = 250`（配置项 `grepMaxMatches`）：一次最多内联保留 250 条匹配。给分：写出 250 | packages/fs/tool-fs-search/src/grep.ts:24-29；packages/fs/tool-fs-search/src/index.ts:100 |
| Q03-4 | 超时 | `SEARCH_TIMEOUT_MS = 30_000`（30 秒，配置项 `timeoutMs`），写进两个工具定义的 `timeoutMs`，由 tool-call timeout policy 通过 `exec.signal` 执行。给分：写出 30 秒（30000 ms） | packages/fs/tool-fs-search/src/search-core.ts:38-43；packages/fs/tool-fs-search/src/index.ts:90-94、106；packages/fs/tool-fs-search/src/glob.ts:320；packages/fs/tool-fs-search/src/grep.ts:293 |

不计分、答出来也不算错的内容：glob 结果按修改时间排序；grep 单行预览上限 2000 字节（`GREP_MAX_LINE_BYTES`）；rg 原始输出上限 20,000,000 字节，超过报 `SEARCH_RAW_OUTPUT_OVERFLOW`；超过条数上限时完整结果经 `ctx.spillStore` 存成文件；glob 排除 .git、.svn 等 VCS 目录；单文件打包运行时用可执行文件旁的 `-rg` 伴随文件；其他错误码 `SEARCH_INVALID_PATTERN`、`SEARCH_FAILED`、`SEARCH_ABORTED`。

### Q04 web_search 的 DeepSeek 搜索是怎么实现的

题面：`web_search` 工具默认用的 DeepSeek 搜索 provider 是怎样完成一次网络搜索的？写出它调用的接口形式、默认端点和默认模型，以及返回内容里不含搜索结果块时怎么处理。

所在包：packages/web/web-search-deepseek

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q04-1 | 实现方式 | 向 DeepSeek 的 Anthropic 兼容 Messages API（`<baseURL>/messages`）发一次模型请求，`tools` 里带原生 server tool `{ type: 'web_search_20250305', name: 'web_search' }`，检索由服务端完成；用 provider 自己的 `fetch` 调用，不经过 `ctx.llm`。给分：写出"Anthropic 兼容的 Messages 接口加服务端 web_search 工具（web_search_20250305）"。说成调用独立的搜索引擎 API（Bing、Google、Exa 等）或由本地抓网页实现，判错 | packages/web/web-search-deepseek/src/provider.ts:1-6、218-229、238 |
| Q04-2 | 默认端点 | `https://api.deepseek.com/anthropic/v1`，再拼 `/messages`。可用配置 `baseURL` 或环境变量 `DEEPSEEK_SEARCH_BASE_URL` 改；不复用对话用的 `DEEPSEEK_BASE_URL`。给分：写出默认端点 `https://api.deepseek.com/anthropic/v1`（带不带 `/messages` 都对）。说它用 `DEEPSEEK_BASE_URL` 或聊天补全端点，判错 | packages/web/web-search-deepseek/src/provider.ts:29-34；packages/web/web-search-deepseek/src/index.ts:79-83、123-125 |
| Q04-3 | 默认模型 | `deepseek-v4-flash`（`DEEPSEEK_DEFAULT_MODEL`，配置项 `model`）。给分：写出 deepseek-v4-flash。写成对话默认模型 `deepseek-flash` 或其他名字，判错 | packages/web/web-search-deepseek/src/provider.ts:36-37；packages/web/web-search-deepseek/src/index.ts:73 |
| Q04-4 | 响应里没有搜索结果块 | 响应内容里没有任何 `web_search_tool_result` 块时抛 `WebError`，错误码 `WEB_PROVIDER_ERROR`（消息以 `DeepSeek returned no web_search_tool_result blocks` 开头），不退回去从正文文字里提取链接。给分：写出这种情况按错误处理（`WEB_PROVIDER_ERROR`）。说成返回空结果列表或 "No results found"，判错 | packages/web/web-search-deepseek/src/provider.ts:150-160 |

不计分、答出来也不算错的内容：provider id 是 `deepseek-official`；`max_tokens` 默认 4096、`max_uses` 默认 5、`anthropic-version` 默认 2023-06-01；鉴权优先用 DeepSeek 账号 token（`x-dsh-auth-token`），否则用 `DEEPSEEK_API_KEY`（同时发 `x-api-key` 和 `Authorization: Bearer`），都没有时报 `WEB_PROVIDER_CREDENTIAL_MISSING`；结果按 URL 去重，摘要取自 text 块的 citations；发请求前往会话追加 `web/deepseek-search-llm-request` 事件；模型侧工具 web_search 一次最多 4 个 query、8 条来源（tool-web）。

### Q05 web_fetch 的 HTTP 抓取有哪些限制

题面：`web_fetch` 工具默认用的匿名 HTTP 抓取 provider 对 URL 和重定向有哪些限制？写出响应体大小上限和超时的默认值，以及超出时的处理。

所在包：packages/web/web-fetch-http

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q05-1 | URL 准入 | 只接受 `http:` 和 `https:`，其他 scheme 报 `WEB_INVALID_URL`；URL 里带用户名或密码报 `WEB_BLOCKED_URL`。给分：写出只允许 http 和 https。凭据一项可不写 | packages/web/web-fetch-http/src/policy.ts:25-39 |
| Q05-2 | 重定向 | 只自动跟随同源（scheme、hostname、port 都相同）的重定向，默认最多 5 跳（`maxRedirects`）；跨源重定向不跟随，报 `WEB_REDIRECT_BLOCKED`，要对新地址重新发起调用。给分：写出"只跟随同源重定向，跨源拒绝"。跳数可不写，写成别的数判错 | packages/web/web-fetch-http/src/provider.ts:74-107；packages/web/web-fetch-http/src/policy.ts:65-67；packages/web/web-fetch-http/src/index.ts:49 |
| Q05-3 | 响应体大小上限 | `maxResponseBytes` 默认 5,000,000 字节：`Content-Length` 声明的长度超过它就直接报 `WEB_FETCH_TOO_LARGE`；实际读到上限时把后面的截掉并标记 truncated，不报错。给分：写出 5,000,000 字节（写 5 MB 也算对） | packages/web/web-fetch-http/src/index.ts:46；packages/web/web-fetch-http/src/provider.ts:185-192、207-216 |
| Q05-4 | 超时 | `timeoutMs` 默认 30,000 ms（30 秒），覆盖发请求和读正文，超时报 `WEB_FETCH_TIMEOUT`。给分：写出 30 秒 | packages/web/web-fetch-http/src/index.ts:48；packages/web/web-fetch-http/src/provider.ts:59-62、266-268 |

不计分、答出来也不算错的内容：URL 长度上限 2048；目标主机必须解析到公网地址（非公网 IP 报 `WEB_BLOCKED_URL`）并固定连接地址；解码后正文另有 `maxBodyChars` 100,000 字符上限；只解码 text/html、text/* 和 JSON/XML 类内容，其他报 `WEB_UNSUPPORTED_CONTENT_TYPE`；provider id 是 `http`；模型侧工具层（tool-web）另有 `fetchMaxOutputChars` 200,000 和 `fetchTimeoutMs` 30,000。

### Q06 skill 从哪些目录发现、同名谁优先

题面：本地文件系统的 skill provider 默认扫描哪些目录？写出项目级和用户级目录、同名 skill 的优先顺序，以及一个 skill 在磁盘上要长什么样才会被识别。

所在包：packages/skill/skill-filesystem（同名裁决在相邻的 packages/skill/skill）

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q06-1 | 项目级目录 | `<项目根>/.dsh/skills` 和 `<项目根>/.agents/skills`。项目根是从会话 cwd 向上找到的第一个含 `.git` 的目录，找不到就用 cwd。给分：两个目录都写出。项目根的判定可不写 | packages/skill/skill-filesystem/src/index.ts:247-253、945-955 |
| Q06-2 | 用户级目录 | `$DSH_HOME/skills`（没设 DSH_HOME 时是 `~/.dsh/skills`）和 `~/.agents/skills`（可用配置 `agentsHome` 或环境变量 `DSH_AGENTS_HOME` 改）。给分：两个目录都写出，写成 `~/.dsh/skills` 和 `~/.agents/skills` 即可 | packages/skill/skill-filesystem/src/index.ts:167-168、255-260；packages/util/home-paths/src/index.ts:87-91 |
| Q06-3 | 同名优先顺序 | 每个根目录带一个 rank，同名 skill rank 小的胜出：项目 `.dsh/skills`（100）> 项目 `.agents/skills`（200）> `customSkillDirs`（300）> 用户 `$DSH_HOME/skills`（400）> 用户 `~/.agents/skills`（500）> bundled（600）。给分：写出项目级优先于用户级，并且同一级里 `.dsh` 优先于 `.agents`；或写出 rank 数值并说明小者优先。说成用户目录覆盖项目目录，或后扫描的覆盖先扫描的，判错 | packages/skill/skill-filesystem/src/index.ts:36-40；packages/skill/skill/src/index.ts:28、78-79、569-577、807-811 |
| Q06-4 | 磁盘上的形态 | 只认根目录下的直接子项：子目录里的 `SKILL.md`（目录式），或根目录下的 `<name>.md` 文件（单文件式）。文件开头的 YAML frontmatter 必须有 `name` 和 `description`，缺了就忽略并记 warn。给分：写出 `SKILL.md`，并写出 frontmatter 必须有 name 和 description。单文件式可不写 | packages/skill/skill-filesystem/src/index.ts:723-735、814-819 |

不计分、答出来也不算错的内容：`name` 必须是 kebab-case；用户 `.dsh/skills` 根跳过 `.system` 子项；bundled 根来自 `bundledSkillDir` 或环境变量 `DSH_BUNDLED_SKILL_DIR`；`includeDefaultRoots: false` 时只扫 customSkillDirs；目录有 watcher，增删改不用重启；frontmatter 里的 `disable-model-invocation`、`user-invocable`；skill 注册表按 scope 分层，最近一层的同名项直接胜出，rank 只在同一层内比较。

### Q07 plan mode 限制什么、怎么退出

题面：plan mode 激活后靠什么约束模型，工具会不会被禁用？写出它的状态记在哪里，以及模型和用户各自怎样退出。

所在包：packages/plan/plan-mode

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q07-1 | 靠什么约束 | 只靠提示词：plan mode 激活期间，每次请求多带一段名为 `plan:policy` 的 system prompt section，文本来自部署配置的 `section`。工具目录不变，没有工具被移除或拦截；要强制限制得靠沙箱模式和审批策略，它们不读写 plan 状态。给分：写出"只加提示段、工具不禁用"。说成 plan mode 下写文件或执行类工具被移除、被拒绝，或沙箱自动切成只读，判错 | packages/plan/plan-mode/src/index.ts:2-17、217-225；packages/plan/plan-mode/README.md:32 |
| Q07-2 | 状态记在哪里 | 会话日志事件 `plan/mode`，数据 `{ active: boolean }`，最后一条为准，所以 resume、fork 后状态还在。turn 进行中的切换先挂起，到下一个被接受的 `agent/pre-step` 才写入；没有进行中的 turn 时立即写入。给分：写出 `plan/mode` 事件 | packages/plan/plan-mode/src/index.ts:46-54、197-214、419-439、442-454 |
| Q07-3 | 模型怎样退出 | 调 `exit_plan_mode` 工具，参数 `plan`（以 `# ` 标题开头的 markdown）。工具通过 `ctx.userQuestions` 让用户审阅，选项是 `Approve` 和 `Keep planning`：选 Approve 才退出（从下一步起生效），否则工具报错、留在 plan mode 并把反馈带回给模型。给分：写出 `exit_plan_mode`，并写出需要用户批准才退出 | packages/plan/plan-mode/src/index.ts:67、76-82、278-354 |
| Q07-4 | 用户怎样进入和退出 | `/plan` 命令进入（可带一句话或附件），`/plan off` 直接退出，不需要审阅。给分：写出 `/plan off` | packages/plan/plan-mode/src/index.ts:230-275 |

不计分、答出来也不算错的内容：`exit_plan_mode` 在非 plan mode 下也注册着，调用会报 `is only available in plan mode`；没有 userQuestions 通道时报错并让用户手动切换；用户关掉审阅框时报 "dismissed the plan review"；`section` 配置必填且不能为空；用户切换时给模型注入 "The user switched this session to plan mode." 之类的通知；提示文本本身写在 base bundle 的配置里。

### Q08 token 是怎么估算的

题面：token meter 在没有真实分词器时怎样估算 token？写出字符与 token 的换算、固定附加的开销、什么时候改用 provider 返回的 usage，以及它有哪些配置项。

所在包：packages/llm/token-meter

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q08-1 | 换算比例 | 固定按 4 个字符算 1 个 token（`CHARS_PER_TOKEN = 4`）：text 和 reasoning 块是 ceil(字符数 / 4)，不调用分词器。给分：写出 4 字符 1 token | packages/llm/token-meter/src/estimate.ts:12-13、46-49 |
| Q08-2 | 固定开销 | 每个内容块加 4（`BLOCK_OVERHEAD`），每条消息再加 4（`ROLE_OVERHEAD`）。给分：两项至少写对一项且数值是 4。数值写错判错 | packages/llm/token-meter/src/estimate.ts:15-19、46-54、88-91 |
| Q08-3 | 何时用 provider 的 usage | `measure()` 里：最近一次成功调用的请求头与当前要计量的请求头一致，并且那次 usage 的总数（input + cacheRead + cacheWrite + output）不低于同一锚点的估算值时，以 usage 为基线（`baseline.kind` 为 `usage`），再加上之后窗口变化的估算增量；否则整份用估算（`estimated`）。给分：写出"请求头一致时复用 provider usage，否则退回估算"；第二个条件（usage 不低于估算）可不写。说成始终用 provider usage，或始终只用估算，判错 | packages/llm/token-meter/src/index.ts:70-76、158-181、187 |
| Q08-4 | 配置项 | 没有。`Config` 是空对象，传任何 key 都在构造时报 `TokenMeterConfig: unknown key "…" (no settings are supported)`。给分：写出没有配置项 | packages/llm/token-meter/src/index.ts:87-92、104、110-112 |

不计分、答出来也不算错的内容：tool-call 块按 name 和 arguments 分别除以 4；其他块（含图片引用）按 JSON 长度除以 4；system 消息不加块开销只加消息开销；工具 schema 按 JSON 长度除以 4 再加 4；路由声明了图片计价时图片按视觉 token 计；注册 tokenUsage、contextPressure、contextBreakdown 三个 projection。

### Q09 模型请求失败后的重试

题面：模型请求失败后的自动重试由哪个插件执行、挂在哪个事件上，重试策略配在哪里？写出默认的重试次数、退避参数和会被重试的错误码。

所在包：packages/llm/llm-retry（默认策略在相邻的 packages/llm/llm 的 src/retry-policy.ts）

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q09-1 | 默认重试次数 | 默认策略 mode 是 `normal`，`maxRetries` 5：首个请求之后最多再重试 5 次；计数按 provider 加策略记在同一个 step 内，新 step 或 turn 结束清零。给分：写出 5 次重试。明确写成"连首次在内一共 5 次请求"，或写成其他数，判错 | packages/llm/llm/src/retry-policy.ts:14、40-41、153-159；packages/llm/llm-retry/src/index.ts:131、222-224 |
| Q09-2 | 退避参数 | 指数退避：`initialDelayMs` 500、`maxDelayMs` 10000、`jitterRatio` 0.1。第 n 次重试的延迟 = min(500 × 2^(n−1), 10000) × 抖动系数（0.9 到 1.1），再封顶 10000 ms；provider 给了 Retry-After 且不超过 maxDelayMs 时用它。给分：500 ms 和 10000 ms 都写对。jitter 可不写 | packages/llm/llm/src/retry-policy.ts:15-17；packages/llm/llm-retry/src/index.ts:59-64、226-238 |
| Q09-3 | 会重试的错误码 | 默认 `retryableCodes`：`EMPTY_RESPONSE`、`RATE_LIMIT`、`SERVER`、`TIMEOUT`、`TRANSPORT`；不在表里的失败码不重试。给分：至少写出其中 4 个，并且没有把表外的码（如 `CONTEXT_WINDOW_EXCEEDED`、鉴权失败）说成会重试 | packages/llm/llm/src/retry-policy.ts:18-24；packages/llm/llm/src/error.ts:42；packages/llm/llm-retry/src/index.ts:215-217 |
| Q09-4 | 谁执行、策略配在哪 | `dsh-llm-retry` 插件（packages/llm/llm-retry/src/index.ts）监听 `agent/request-error` 执行重试。它自己没有配置项；策略是各 provider 配置里的 `retryPolicy`，省略时用上面的默认值，把 `retryPolicy` 写在 llm-retry 下会报错。给分：写出 llm-retry 和 `agent/request-error`，并写出策略归 provider 配置（`retryPolicy`） | packages/llm/llm-retry/src/index.ts:24-36、243-252；packages/llm/llm/src/retry-policy.ts:149-159 |

不计分、答出来也不算错的内容：mode `always` 对所有失败无限重试；每次重试先追加 `llm/retry` 事件，等待结束后追加 `llm/retry-started`；等待可被取消；Retry-After 超过 maxDelayMs 时 normal 模式放弃重试；base bundle 没有覆盖这些默认值。

### Q10 工具结果太大时写到文件（spill）

题面：工具结果过大时会被写到文件（spill policy）。它在什么时机、按什么量判断一条结果过大？写出阈值配置项、这个包自身有没有默认值以及不配置时的行为、哪个工具的结果不受处理，以及超限后模型实际看到什么。

所在包：packages/spill/spill-policy

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q10-1 | 触发时机和判断量 | 监听 `tools/post-execute`（工具执行完、结果被接受之后）：结果内容（text 和 image 块）的估算 token 合计超过 `maxInlineTokens` 才处理，没超过原样放行。给分：写出 `tools/post-execute`（或"工具执行之后"），并写出按估算 token 数比较。说成按字节数或字符数比较，判错 | packages/spill/spill-policy/src/index.ts:91-98、133-150 |
| Q10-2 | 默认值和不配置时 | 配置项 `maxInlineTokens` 在包内没有默认值；省略时 `apply` 直接返回，整个策略不生效。base bundle 给它配了 12500。给分：写出包内没有默认值、不配置时不生效。只写 12500 的：注明了来自 base bundle 配置的记"没提到"，把 12500 说成包内默认值的判错 | packages/spill/spill-policy/src/index.ts:25-28、34、49-50；packages/bundle/base/cordis.patch.yml:407-410 |
| Q10-3 | 不受处理的工具 | `read` 工具的结果永远不处理（`exec.name === 'read'`）；另外 post-execute 的决定不是 accept、或已经替换了 `value` 的结果也跳过。给分：写出 `read` 工具例外 | packages/spill/spill-policy/src/index.ts:135；packages/spill/spill-policy/README.md:61 |
| Q10-4 | 超限后模型看到什么 | 全文经 `ctx.spillStore.saveText()` 存成文件（建议文件名 `<工具名>.txt`）；结果里保留开头和结尾（各占一半预算），中间用 `[...]` 隔开，末尾附 `(Omitted N bytes. Full formatted result stored at: <路径>. …)`，提示用 read 或 grep 取回。没有 spillStore 或保存失败时记 warn、原内容照常返回。给分：写出全文写进 spill 文件，并且模型拿到的是截短的内容加文件路径提示。说成只截断、不写文件，或超出部分直接丢弃，判错 | packages/spill/spill-policy/src/index.ts:41、101-118、127-130；packages/spill/spill-policy/src/retention.ts:48-58、75；packages/spill/spill-policy/src/notice.ts:7、21-24 |

不计分、答出来也不算错的内容：图片块整块保留或整块省略，全文文件里在图片位置写附件路径；PTC 子调用的纯文本结果只截日志副本；本地后端 spill-local 把文件放在 `<root>/session-<hash>/` 下，默认根是系统临时目录里的 `dsh-spill-*`，超过 30 天的启动时清理；`maxInlineTokens` 必须是非负整数。

### Q11 todo 工具的规则

题面：todo 工具叫什么、每次调用怎样更新列表、有哪些状态？写出同时处于 in_progress 的数量限制由什么决定，以及列表保存在哪里。

所在包：packages/todo/tool-todo

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q11-1 | 工具名和更新方式 | 工具 `todo_write`，参数 `todos` 是完整列表，每次调用整体替换上一份，没有按条增删改。给分：写出 `todo_write`，并说明是整表替换 | packages/todo/tool-todo/src/index.ts:135-143 |
| Q11-2 | 状态取值 | 三种：`pending`、`in_progress`、`completed`。给分：三种都写对 | packages/todo/tool-todo/src/index.ts:26、148-152 |
| Q11-3 | 同时 in_progress 的限制 | 由必填配置 `allowParallelInProgress` 决定（没有默认值，不配则加载失败）：为 false 时一份列表里超过一个 `in_progress` 报错 `invalid todos: at most one task may be in_progress (got N)`；为 true 时不限。base bundle 配的是 true。给分：写出由 `allowParallelInProgress` 决定，并写出 false 时最多一个 in_progress。说成固定只能有一个 in_progress、不提这个配置，判错 | packages/todo/tool-todo/src/index.ts:29-43、96-98；packages/bundle/base/cordis.patch.yml:430-433 |
| Q11-4 | 列表存在哪里 | 每次调用往调用方 agent 的会话日志追加一条 `todo/write` 事件（带整份列表），回放时以最后一条为准；`todos` projection 在下一个 `turn/start` 清空。没有所属 agent 会话的调用被拒绝。给分：写出写进会话日志的 `todo/write` 事件。说成存在单独的文件或数据库，判错 | packages/todo/tool-todo/src/index.ts:123-134、192-199 |

不计分、答出来也不算错的内容：`content` 去掉首尾空白后不能为空、不能重复；item 不允许多余字段；成功时返回 `Updated todo list: X pending, Y in progress, Z completed.`；工具描述里关于 in_progress 的那句话随配置变化。

### Q12 后台任务（job）工具

题面：后台任务相关的模型工具有哪几个？写出等待任务输出时的默认等待时间和上限、任务结束后怎样通知所属 agent，以及哪些情况不发通知。

所在包：packages/jobs/tool-jobs

| 编号 | 要点 | 正确内容与给分条件 | 来源 |
|---|---|---|---|
| Q12-1 | 工具名 | 三个：`job_output`（读输出或结果）、`job_list`（列出本 agent 的任务）、`job_kill`（请求取消）。给分：三个名字都写出 | packages/jobs/tool-jobs/src/index.ts:310-312、351-353、371-373 |
| Q12-2 | 等待时间 | `job_output` 带 `wait: true` 时阻塞等待：没给 `timeout_ms` 用 `waitTimeoutMs`，默认 30,000 ms；任何等待都被 `maxWaitTimeoutMs` 封顶，默认 600,000 ms（10 分钟）。等到超时任务继续运行，工具照常返回当前输出和状态，不是 `TOOL_TIMEOUT` 错误。给分：30 秒和 10 分钟都写对 | packages/jobs/tool-jobs/src/index.ts:59-61、192-193、313-318、339-346 |
| Q12-3 | 完成通知 | 任务结算后给所属 agent 发一条来源为 `tool-jobs` 的通知消息（`background job <id> … finished …`）。默认 `completionDelivery` 是 `wakeup`：owner 空闲时用 `owner.followup()` 开新一轮；owner 正忙时用 `owner.inject()` 放进下一步。配成 `quiet` 时空闲的 owner 不被唤醒，只注入。给分：写出"空闲时唤醒开新一轮、忙时注入下一步"，或写出默认 `wakeup` 并说明空闲的 owner 会被唤醒 | packages/jobs/tool-jobs/src/index.ts:33-38、62、284-307 |
| Q12-4 | 不发通知的情况 | 模型自己用 `job_kill` 杀掉的任务、结算时正有调用在等它的任务（`event.awaited`，例如 `job_output` 带 `wait: true`）、因 teardown 结算的任务、没有 owner 的任务，都不发通知。给分：至少写出前两种之一 | packages/jobs/tool-jobs/src/index.ts:256-260、276-278 |

不计分、答出来也不算错的内容：`maxConsecutiveWakes` 默认不设（不限连续唤醒次数）；加载 tool-jobs 才给 `ctx.jobs` 挂上 controller，否则后台任务起不来；jobs-local 每个 owner 最多 10 个活动任务；任务 id 形如 `bash-1`；工具输出受任务的 `outputLimitBytes` 限制；`waitTimeoutMs` 大于 `maxWaitTimeoutMs` 时加载报错。
