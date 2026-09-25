# explain-everything-to-me

用一个斜杠命令，请当前 Agent 查阅多个 Agent 的工作记忆并把事情讲明白。检索由 [sivtr](https://github.com/Ariestar/sivtr) 提供；解释、关联、筛选和核对由调用 Skill 的 Agent 完成。它不绑定 DeepSeek、Codex、Claude 或任何单一 Agent。

```text
/explain-everything-to-me 最近各个项目的 agents 做了什么？哪些需要我决定？
/explain-everything-to-me 解释 parser 基准测试为何改了方案，给我原始证据。
/explain-everything-to-me
```

不附加内容时，默认问题是“向我解释最近我的 agents 发生的一切。根据工作区进行分组。”**同一会话再次调用时**，“最近”默认从上一次调用的用户消息时间算起；首次调用则先探索过去 3 天。时间无法可靠判定且会影响答案时，Agent 应弹出时间段选项。Agent 会自行挑出相关 sessions、阅读原文并汇总，不要求你手动筛选。回答会标明实际检索时间范围、证据来源和无法核实的地方。

## 准备与安装

1. 按 [sivtr README](https://github.com/Ariestar/sivtr#快速开始) 安装 CLI，并配置所需的 Agent 会话采集。已有 sivtr 时无需重复安装。推荐把 sivtr MCP 连接到要使用的宿主；没有 MCP 时，本 Skill 可调用 CLI。第一次运行前确认 `sivtr ws list`、`sivtr s agent --latest 5 --refs` 有可读记录。索引能覆盖哪些 Agent 和工作区，取决于 sivtr 的实际发现与配置。
2. 运行 `python3 scripts/install.py --host HOST`，其中 `HOST` 为下表之一。Antigravity 需加 `--workspace /你的工作区路径`。安装器复制同一份 Skill，并仅在宿主需要时生成显式命令适配；遇到已有目标会停止，不覆盖原文件。它不会安装 sivtr 或修改采集、分享设置。

| 宿主 | 安装命令中的 `HOST` | 用户入口 | 显式调用实现 |
| --- | --- | --- | --- |
| Codex | `codex` | `$explain-everything-to-me` | `agents/openai.yaml` 禁止隐式调用；[官方 Skill 入口](https://learn.chatgpt.com/docs/build-skills)是 `$` 或 `/skills`，目前不能把 Skill 自身注册为同名斜杠命令。 |
| Claude Code | `claude` | `/explain-everything-to-me` | 安装器为副本加入 `disable-model-invocation: true`；见 [Claude Skills 文档](https://code.claude.com/docs/en/skills)。 |
| Dsh | `dsh` | `/explain-everything-to-me` | 安装器加入用户可调用、模型不可调用字段；要求启用 Dsh 的 `tool-skill` 与本地 Skill 提供方。Dsh TUI 支持用户专用 Skill；当前 Dsh Web 的 Skill 列表只显示模型与用户均可调用的交集，因此 Web 中可能不显示此命令。 |
| Gemini CLI | `gemini` | `/explain-everything-to-me` | 安装器生成[自定义命令](https://geminicli.com/docs/cli/custom-commands/)；Skill 放在非自动发现目录，由命令按路径读取。 |
| Google Antigravity | `antigravity` | `/explain-everything-to-me` | 安装器在工作区生成 [Workflow](https://codelabs.developers.google.com/autonomous-ai-developer-pipelines-antigravity)；Skill 放在非自动发现目录。 |
| Grok Build | `grok` | `/explain-everything-to-me` | 安装器加入 `disable-model-invocation: true` 和 `user-invocable: true`；见 [Grok Skills 文档](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/08-skills.md)。 |
| Pi | `pi` | `/explain-everything-to-me` | 安装器生成 Prompt Template，Skill 放在非自动发现目录；原生 Skill 入口是 `/skill:explain-everything-to-me`，见 [Pi Skills 文档](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md)。 |

Gemini CLI 与 Antigravity 是不同宿主；上表的 `gemini` 指 Gemini CLI，`antigravity` 指 Google Antigravity IDE。Grok 行指 Grok Build CLI，不是 grok.com 网页聊天。宿主若不支持本机文件读取或 `sivtr`，无法执行本地记忆检索。首次安装后可用宿主的 Skill/命令列表确认入口，再用一条小范围查询试运行。

严格同名斜杠入口目前不能在 Codex 的 Skill 机制中实现；这一项需要 Codex 提供自定义斜杠命令映射，或接受其 `$` 显式入口。其余六个宿主按上表提供同名斜杠入口。

### 安装时建议设定

建议告诉安装 Agent 两个偏好：

- **“最近”通常指多久**：首次调用或找不到上次调用时间时，默认探索过去 **3 天**。你可以改成“过去 24 小时”“过去 5 天”等。同一会话再次调用时，仍优先从上次调用时间算起；每次命令里明确写出的时间范围始终优先。
- **一次最多纳入多少条相关 session**：默认由问题和证据覆盖情况决定，没有固定上限。若你希望控制阅读与回答篇幅，可以设为“最多 8 条”等；达到上限时，Agent 应优先保留最相关的会话，并说明仍有多少候选未读或未纳入，不能把受限结果说成完整盘点。

例如：“用中文解释；我是产品经理，熟悉用户研究和统计；首次调用的‘最近’按过去 48 小时算；一次最多纳入 8 条相关 session。”若在安装前提供，请安装 Agent 将这两个偏好写入本 Skill 的时间规则和检索/筛选规则，再安装到各宿主。若已经安装，需同步修改各宿主的 Skill 副本；只在对话中说一次不会自动变成永久设置。不设偏好也能使用上述默认规则。

**如果由 Agent 代你安装：** 安装完成后，还请它提醒你可选地说明工作语言、职业或工作角色、熟悉的知识领域，以及上述两个时间和数量偏好。这些信息用于调整解释方式与检索范围。除非你明确要求保存，安装 Agent 不应把职业和知识背景等个人信息写进文件或记忆库。

## 设计来源

本 Skill 延续 [Dsh 旧版](https://github.com/JamieJustTang/explain-everything-to-me-dsh-legacy) 的思路：把别的 Agent 的会话当作可追溯、有限的上下文；解释“做了什么、为什么、当前卡在哪、用户该决定什么”；用平实语言把机器汇报变成人能判断的内容。此版本把检索层改为 sivtr，覆盖其支持的多个 Agent、终端记录和工作区，并让 Agent 自主完成候选会话筛选。旧版依赖 Dsh 的会话导入机制；本版只依赖 Skill 宿主与 sivtr 的现有能力。

本 Skill 默认只读。历史会话是证据，不代表当前项目状态；需要现状结论时 Agent 会另行核实。
