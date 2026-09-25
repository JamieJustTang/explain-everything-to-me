# explain-everything-to-me

### 你的 Agents 做了什么？让它们自己查清楚，再讲给你听。

一个面向多 Agent 工作记忆的 Skill。你提出问题，当前 Agent 使用 [sivtr](https://github.com/Ariestar/sivtr) 搜索会话，阅读相关原文，核对进展与证据，然后给出能直接使用的解释。你无需翻日志，也无需从搜索结果里手动挑 session。

> **sivtr 保存并检索工作记录；这个 Skill 负责理解问题、阅读记录和组织答案。** 它不会替代 sivtr，也不需要把所有会话导入某个特定 Agent。

## 为什么需要它？

几个 Agent 同时工作时，信息很快散落在不同会话和工作区。一个 Agent 说测试通过，另一个 Agent 后来改了方案；你想知道的是**现在发生了什么、为什么改、还需要你决定什么**。

直接调用即可：

```text
/explain-everything-to-me 最近各个项目的 agents 做了什么？哪些需要我决定？
/explain-everything-to-me 解释 parser 基准测试为何改了方案，给我原始证据。
/explain-everything-to-me
```

最后一条不带参数，等同于：“向我解释最近我的 agents 发生的一切。根据工作区进行分组。”Codex 的显式入口是 `$explain-everything-to-me`，其余支持的宿主使用上面的斜杠命令。

## 它会怎样回答？

例如你问：“最近各工作区做了什么？”回答会按工作区组织，说明完成的事、关键决定、验证结果、未解决的问题，以及你是否需要行动。重要结论会附上 sivtr 的记录引用。下面是**格式示意，并非真实检索结果**：

```text
检索范围：9 月 22 日 10:00 至 9 月 25 日 10:00（首次调用，按最近 3 天）

工作区 A
- 完成：Agent 修改了数据解析流程，并运行了相关测试。[来源：sivtr WorkRef]
- 待决定：是否保留旧格式兼容层。记录里有两种方案，尚未见到你的决定。

工作区 B
- 本次时间范围内未找到新增会话；索引覆盖情况见下方说明。

下次“最近”从这里算：2026-09-25T10:00:00+08:00（本次用户调用时间）
```

它不会仅凭搜索摘要下结论。Skill 要求 Agent 打开候选记录，阅读必要的会话片段，合并同一任务的后续记录，再筛掉重复和无关内容。历史会话只能证明“当时记录了什么”；需要判断当前状态时，Agent 会另行核对现有文件或运行结果。

解释文字使用内置的 [STE 魔改规则](references/ste-language-improvement.md)。中文回答会避开翻译腔、空话和不必要的术语；英文回答按该规则的英文部分处理。规则只调整 Agent 自己写的句子，不改动记录原文、引用、命令和事实。安装本 Skill 时会一并复制规则文件，**无需另装 STE Skill**。内置版本取自 [ste-language-zh-improvement](https://github.com/JamieJustTang/ste-language-zh-improvement/blob/2b9c7c9a7fc1b4c459abd9382dd00acc760fe839/SKILL.md)。

### 会随你的用语习惯进化

Skill 会从本次查阅的 session 中留意你本人反复使用、明确要求或纠正过的表达方式。它只从已有证据提炼简短规则，不额外翻查与你的问题无关的私人会话。**通用**习惯可用于各工作区；**项目特定**词汇和说法只在对应项目使用。

学习顺序是“提取证据 → 自主写入 → revise 评估 → 通过后使用”。它不会每次都强行学到新规则，也不会在写入前逐条要求批准。若评估发现误读或范围问题，新规则会隔离，Skill 会向你报告并请求指示。通过的规则存于本机 `~/.explain-everything-to-me/language-memory.json`，不进入 GitHub 仓库；你可以要求查看、改写、停用或删除。[查看完整规则](references/language-evolution.md)。

## 快速开始

**1. 准备 sivtr。** 按 [sivtr 的安装说明](https://github.com/Ariestar/sivtr#快速开始) 安装并配置会话采集。建议为目标 Agent 配置 sivtr MCP；没有 MCP 时，本 Skill 可使用 sivtr CLI。先确认索引中有记录：

```bash
sivtr ws list
sivtr s agent --latest 5 --refs
```

**2. 下载并安装本 Skill。** 在仓库目录里选择一个宿主：

```bash
git clone https://github.com/JamieJustTang/explain-everything-to-me.git
cd explain-everything-to-me
python3 scripts/install.py --host codex
```

将 `codex` 换成下表中的 `HOST`。Antigravity 还需要 `--workspace /你的工作区路径`。安装器复制 Skill，并为需要的宿主创建显式命令入口。已有同名安装时，它会停止，不覆盖你的文件。

**3. 在宿主中显式调用。** 例如：

```text
/explain-everything-to-me 过去两天，哪个项目有失败的测试？后来如何处理？
```

如果你安装到 Codex，请改用 `$explain-everything-to-me`。初次使用时，建议先问一个小范围问题，确认宿主能读取 sivtr 记录。

## 支持的宿主

| 宿主 | `HOST` | 用户入口 | 安装方式 |
| --- | --- | --- | --- |
| Codex | `codex` | `$explain-everything-to-me` | Skill；[官方入口](https://learn.chatgpt.com/docs/build-skills)使用 `$` 或 `/skills` |
| Claude Code | `claude` | `/explain-everything-to-me` | 仅用户可调用的 [Skill](https://code.claude.com/docs/en/skills) |
| Dsh | `dsh` | `/explain-everything-to-me` | 仅用户可调用的 Skill；需启用 `tool-skill` 和本地 Skill 提供方 |
| Gemini CLI | `gemini` | `/explain-everything-to-me` | [自定义命令](https://geminicli.com/docs/cli/custom-commands/)读取 Skill |
| Google Antigravity | `antigravity` | `/explain-everything-to-me` | 工作区 [Workflow](https://codelabs.developers.google.com/autonomous-ai-developer-pipelines-antigravity) 读取 Skill |
| Grok Build | `grok` | `/explain-everything-to-me` | 仅用户可调用的 [Skill](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/08-skills.md) |
| Pi | `pi` | `/explain-everything-to-me` | Prompt Template 读取 Skill；原生 Skill 入口为 `/skill:explain-everything-to-me` |

Codex 目前不能把此 Skill 注册成同名斜杠命令。Dsh TUI 支持用户专用 Skill；Dsh Web 的 Skill 列表可能不显示它。这里的 Grok 指 Grok Build CLI，Gemini 指 Gemini CLI。宿主必须能读取本机文件或调用 sivtr，才能使用本地记忆。

## “最近”从什么时候算？

这个 Skill 会先读取**当前会话中上一次用户调用它的时间**：

| 你的说法 | 使用的时间范围 |
| --- | --- |
| “过去 24 小时”“9 月 1 日至 9 月 3 日”等 | 你明确给出的范围 |
| 同一会话再次说“最近”或只输入命令 | 从上一次调用的用户消息时间，到本次调用时间 |
| 首次调用或无法可靠找回上次时间 | 默认先探索最近 **3 天** |

如果时间记录互相冲突，或者不同时间范围会明显改变答案，Agent 会请你选择。每次回答都会写明实际检索范围，并留下本次调用时间，供下一次核对。“新增”按事件发生时间判断，不按 Agent 上次有没有提到判断。

## 安装时可以设定的偏好

建议告诉安装 Agent：

- **“最近”通常指多久**：首次调用默认 3 天，你可以改为 24 小时、5 天等。同一会话再次调用时，仍优先从上次调用时间算起。命令里明确写出的时间始终优先。
- **一次最多纳入多少条相关 session**：默认没有固定上限，由问题和证据决定。你可以设成“最多 8 条”。达到上限时，Agent 应保留最相关的会话，并说明还有多少候选未读或未纳入；受限结果不能称作完整盘点。

例如：“用中文解释；我是产品经理，熟悉用户研究和统计；首次调用的‘最近’按过去 48 小时算；一次最多纳入 8 条相关 session。”

若在安装前提供偏好，请安装 Agent 将时间与数量规则写入本 Skill，再安装到各宿主。若已经安装，需同步修改各宿主的 Skill 副本。只在对话中说一次，不会自动保存为永久设置。

如果由 Agent 代你安装，安装后它还应提醒你：可选地说明工作语言、职业或工作角色、熟悉的知识领域，以及上述两个偏好。这些信息帮助它调整解释深度。除非你明确要求保存，它不应把职业和知识背景写进文件或记忆库。

## 与 sivtr 的关系

| 组件 | 负责什么 |
| --- | --- |
| [sivtr](https://github.com/Ariestar/sivtr) | 采集、索引和检索终端与 Agent 会话；提供 MCP 工具、CLI 和稳定引用 |
| 本 Skill | 把自然语言需求变成检索意图，自动阅读并筛选会话，按问题解释结果 |
| 当前 Agent | 执行检索、核对证据、说明不确定性，并用你的工作语言回答 |

本 Skill 只在你显式调用时运行，默认只读。它不会自动安装 sivtr、打开远程分享，或把历史记录写成已经核实的当前事实。能看到哪些 Agent 和工作区，取决于 sivtr 的实际采集与索引。

这个项目延续 [Dsh 旧版](https://github.com/JamieJustTang/explain-everything-to-me-dsh-legacy) 的解释思路。新版本使用 sivtr 检索跨 Agent 记录，并让调用 Skill 的 Agent 自行完成会话筛选。
