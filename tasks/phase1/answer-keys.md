# 代码调研题的参考答案（不给模型看；镜像 cc0fb5f8b7 核对过）

## c1-subagent-limits
1. 同时存活上限 `maxActiveSubagents`，默认 8：`packages/subagent/subagent/src/index.ts`（SubagentRuntime.Config）。
2. 深度上限 `maxDepth`，默认 1：同一 Config；委派工具行可写死数值或 `provider-managed`，不写时每次委派读当前设置。
3. 同时存活上限在创建/冷恢复可续聊子代理时检查：`continuation-activation.ts` 的 `ActivationPool.reserve`，满了报 `subagent limit reached`（ACTIVATION_LIMIT_REACHED）；根代理的可续聊后代共用一个池。
4. 不计入同时存活上限：前台一次性子代理（`run_in_background: false`）、一次性后台任务、workflow 的 `agent()` 子代理、外部 provider（codex / claude-code）、池的所有者本身。
5. 深度在每次启动子代理时检查：`child-agent.ts` 的 `resolveChildDepth`，超过报 `subagent depth N exceeds maxDepth M`；一次性和可续聊两条路径都检查。
6. workflow 另有自己的上限：`workflow-ptc` 的 `maxTotalAgents` 默认 1000，并发 `min(16, CPU 核数 − 2)`。

## c2-session-log-format
1. 目录：`$DSH_HOME/sessions/<编码后的工作目录>/<会话 id>/`（session-persistence-jsonl，root = dshHomePath('sessions')）。
2. 文件：`session.v4.jsonl.zstd`，JSONL，zstd 压缩，格式版本 4。
3. 第一行：`{type: session, version, id, createdAt, cwd, parentSession?, isSeeded, origin?, delegationDepth}`。
4. 子代理是独立目录，靠 `parentSession`、`origin: subagent`、`delegationDepth` 关联；父会话里有 `subagent/catalog` 事件。
5. token 记在每条 `assistant/message` 的 `usage`，`inputTokens`（不含缓存）、`cacheReadTokens`、`outputTokens` 互不重叠。
