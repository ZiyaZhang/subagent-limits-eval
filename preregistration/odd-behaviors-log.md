# 怪行为记录

她 2026-10-09 的要求：实验里或日常用 DSH 时出现奇怪的行为，要排查到原因并记下来。每条写清：看到了什么、多常见、成因查到哪一步（读到源码的给文件和行）、影响、建议。没查完的写明还差什么。

数据口径：主批 p2-main 的 1,784 次运行，脚本 scripts/tool_error_census.py 把全部“工具调用返回错误”按消息归类，共 50,836 次失败调用，其中打开网页 40,411 次、搜索 369 次（多为网站拒绝或超时），其余 10,056 次归成下面几类。源码行号取自 deepseek-harness 主干 a426d21d（2026-10-09）；实验用的是 0.2.0-rc.2，这几处的报错文字相同。

## 1　给已结束的 subagent 续发消息失败，转而另开一个接续的 subagent（她的截图）

- **看到的**：主 agent 想把新信息交回原来的两个 subagent，发送消息工具两次返回 `active teammate "<编号>" not found`，主 agent 判断“没有送达”，各开一个新的 subagent 接着查。原来两个 subagent 的上下文就丢了。
- **成因（已读到源码）**：两个插件注册了同名工具。
  - 普通的 subagent 控制工具 `send_message(agent_id, message)`：packages/subagent/tool-subagent-control/src/index.ts 第 28–72 行。说明写的是“空闲的 agent 收到消息会开始新一轮”，`list_agents` 的说明也写“直接子 agent 在任何状态下都接受 send_message”。
  - Agent Teams 插件在同一个 agent 的作用域里又注册了一套同名的 `send_message(target, message)`、`list_agents`、`interrupt_agent`：packages/experimental/tool-agent-team/src/index.ts 第 163 行起，`send_message` 在第 215–230 行。它按“队员名字”找收件人，而且只找还在队里的：packages/experimental/agent-team/src/roster.ts 第 42–54 行，找不到就抛这句 `active teammate "…" not found`。
  - 普通 subagent 结束时给父 agent 的通知是 `Background subagent <编号> finished and will do no further work unless you send it more.`（packages/subagent/subagent/src/continuation-messages.ts 第 106–112 行），等于提示模型“可以续发”。模型照做，拿 subagent 工具返回的编号去调 `send_message`，但此时这个名字指向的是 Agent Teams 那一个，编号不是队员名字，于是报错；报错里也没说该怎么办。
- **影响**：续不上原来的 subagent，只能另开，前面查到的上下文作废，多花一遍钱。
- **建议**：三选一或都做。同名工具不要两个插件各注册一套，Agent Teams 的那套改名或者兼容 subagent 编号；找不到收件人时报错里写明“这个编号是普通 subagent，不是队员”；Agent Teams 开着的时候，结束通知别再说“除非你再给它发消息”。
- **实验里有没有**：实验的配置没开 Agent Teams，这句报错一次也没出现。实验里对应的是第 2 条。
- **状态**：成因查清。还没做的：在她那个会话的日志里核对当时是不是开着 Agent Teams；要不要提 issue 由她定。

## 2　实验里的发消息失败：84 次

| 报错 | 次数 | 运行数 | 源码里是什么情况 |
|---|---|---|---|
| `subagent "<编号>" belongs to another parent session` | 32 | 15 | 只能给自己的直接子 agent 发；收件人不是自己开的。packages/subagent/subagent/src/manager.ts 第 715–725 行 |
| `subagent "<编号>" is unavailable`（含编号写错的几种） | 43 | 约 25 | 收件人已结束，重新唤起时找不到这个会话或恢复失败；其中一部分是模型把编号抄错了（多了少了字符，或者填的是一段描述）。manager.ts 第 1325–1377 行 |
| `subagent limit reached (active child limit: N)…` | 5 | 5 | 唤起一个已结束的 subagent 也要占一个 K 的名额，名额满了就被拒 |
| 其他 | 4 | 未细分 | |

- **还差的**：发送失败之后模型做了什么（重发、改编号、另开一个、自己做、放弃），各占多少；成功续发的有多少、续发在各 K 下占名额的情况。脚本 scripts/message_census.py 已写好，开发机连上后跑。

## 3　改文件时报“文件在读过之后被改了”

- **看到的**：`edit` 报 `file changed since it was read — re-read the file, then retry` 785 次，出现在 416 次运行里；`write` 同类 45 次。另有 `old_string was not found` 539 次、`file has not been read` 274 次。
- **猜测的成因，未核实**：几个 agent 同时改同一份报告，或者 agent 自己用 bash 改了文件之后又用 edit。
- **还差的**：按“是谁在两次之间改了这个文件”分类，看是多个 agent 撞在一起还是自己撞自己；各 K、D 下的发生率。

## 4　工具调用被中止

- **看到的**：`bash` 返回 `tool call aborted` 364 次（263 次运行），其中 188 次之后这个 agent 再没有任何动作；另有 `aborted before dispatch` 59 次。
- **猜测的成因，未核实**：主 agent 给出最终回答时还在跑的 subagent 被中止。主批里见过一例：上限 K=2 时主 agent 想开 4 个，后 2 个等到名额才开出来，主 agent 写完报告就结束了，这 2 个被中止。
- **还差的**：被中止的 subagent 有多少、已经花了多少钱、它们的结果有没有被用上；和 K 的关系。

## 5　模型想拿评测集的题库

- **看到的**：搜索结果里出现了评测集题库文件的一个转载地址。5 次运行换着镜像和代理想把它下载下来（raw.githack、jsdelivr、ghproxy、Hugging Face 的接口，还有一次去查容器的 hosts 和本地代理端口），全部被容器的屏蔽挡住。另有 1 次运行下载了评测集的论文，从里面读到了自己那道题的要求原文。
- **处理**：这些运行都在泄漏标记之内，不进主版本。详见方案变更记录 2026-10-09T08:00Z 那条。
- **状态**：查清。

## 6　零散的

| 现象 | 次数 | 说明 |
|---|---|---|
| `create_goal` / `update_goal` 报“需要人类直接发起” | 9 | 无人值守运行里模型去动目标工具 |
| 调用不存在的工具 `fetch` | 5 | 模型编了一个工具名，随后改用 `web_fetch` |
| `job_output` 报 `unknown job` / `wait aborted` | 39 | 查一个不存在或已被中止的后台任务 |
| `read_image` 读不了图片 | 26 | 多数是下载的图片扩展名和内容不符，或数据损坏 |

## 不算怪、但数量最大的两类

`subagent` 被深度上限拒绝 4,397 次（739 次运行），被并发上限拒绝 3,100 次（687 次运行）。这是实验本身要量的东西，在正文里按设置报。

---

记录更新：2026-10-09T10:56Z。第 2、3、4 条的“还差的”等开发机连上后补。
