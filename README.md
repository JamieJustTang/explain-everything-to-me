# explain-everything-to-me

**问一句：我的 Agents 最近做了什么？**

这个 Skill 把你的问题变成跨 Agent 的会话检索，自己打开原文、核对后续变化，再给你一份按问题组织的解释。你不用翻日志，也不用从搜索结果中手动挑 session。

```text
/explain-everything-to-me 最近各工作区做了什么？哪些事需要我决定？
/explain-everything-to-me parser 基准测试为什么换了方案？请给出处。
/explain-everything-to-me
```

不带参数时，默认问题是：**“向我解释最近我的 agents 发生的一切。根据工作区进行分组。”** Codex 的入口是 `$explain-everything-to-me`；其余支持的宿主使用 `/explain-everything-to-me`。只有你显式调用，Skill 才会运行。

## 功能一览

| 功能 | 当前行为 |
| --- | --- |
| 理解问题 | 从自然语言识别工作区、主题、Agent、时间和真正要回答的事，组合检索式。 |
| 查跨 Agent 记录 | 使用 [sivtr](https://github.com/Ariestar/sivtr) 的 MCP 或 CLI 检索已收录的会话；按工作区补查，避免全局结果漏掉小项目。 |
| 自动阅读与筛选 | 按 session 去重，打开命中记录和相邻内容，核对起因、关键结果与最终状态；不让你手动筛选候选列表。 |
| 解释变化 | 串起多个 session 的连续工作，区分旧背景、新进展、Agent 的说法、工具证据与当前已核实的状态；重要结论附 WorkRef。 |
| 理解“最近” | 同一会话内再次调用时，从上次**用户调用时间**算起；首次无参数调用默认查最近 **3 天**。时间含糊且影响答案时，请你选时间段。 |
| 可选 Jev 排序 | [jev-rag-retrieval](https://github.com/JamieJustTang/jev-rag-retrieval) 分别给候选 session 和内部段落排序；没有 Jev 也能使用。 |
| 调整表达 | 内置 [STE 中文魔改规则](references/ste-language-improvement.md)，并从已读会话中的用户原话学习通用或项目特定的表达习惯。 |

```mermaid
flowchart LR
    A[你的问题] --> B[确定时间与范围]
    B --> C[sivtr 查找候选]
    C --> D[可选：Jev 排序]
    D --> E[打开原文并核对]
    E --> F[按问题解释并附引用]
```

这个仓库是**解释层**。它沿用 sivtr 原有的归档与检索方式，不打包 sivtr、TUI 或归档数据库，也没有另建轻量索引。Skill 使用 sivtr MCP；没有 MCP 时使用 CLI。TUI 不是使用条件。

## 回答是什么样

下面仅示意结构，不是真实检索结果：

```text
检索范围：本会话上次调用时间 → 本次调用时间（Asia/Shanghai）

工作区 A
- 已完成：数据解析流程已修改；测试记录显示通过。[sivtr WorkRef]
- 待决定：旧格式兼容层有两种方案，记录中尚未见到你的决定。[sivtr WorkRef]

工作区 B
- 本次时间范围内未找到新增会话；说明已检查的来源和工作区。

下次“最近”从这里算：YYYY-MM-DDTHH:MM:SS+08:00（本次用户调用时间）
```

Skill 会说明实际查过的时间、工作区和来源。历史会话只能证明当时记录了什么；若你问的是“现在是否已完成”，且没有限定只能看档案，Agent 会另查当前文件或状态。缺失记录、来源冲突和未核实的推断会明确标出。

## 安装

### 1. 准备 sivtr

按 [sivtr 安装说明](https://github.com/Ariestar/sivtr#快速开始)安装 CLI，并确认它能找到你的 Agent 会话。建议给使用本 Skill 的宿主连接 sivtr MCP；没有 MCP 时可用 CLI。

```bash
sivtr ws list
sivtr s agent --latest 5 --refs
```

可见范围由 sivtr 实际发现和收录的来源决定。本 Skill 不会替你初始化采集、接入远端或共享会话。

### 2. 安装 Skill

```bash
git clone https://github.com/JamieJustTang/explain-everything-to-me.git
cd explain-everything-to-me
python3 scripts/install.py --host codex
```

将 `codex` 换成下表的 `HOST`。安装器会复制 Skill，并在需要时创建显式命令入口。它遇到同名安装会停止，避免覆盖你改过的文件。Antigravity 还需要 `--workspace /你的工作区路径`。

| 宿主 | `HOST` | 调用入口 | 安装形式 |
| --- | --- | --- | --- |
| Codex | `codex` | `$explain-everything-to-me` | 显式调用的 Skill |
| Claude Code | `claude` | `/explain-everything-to-me` | 仅用户可调用的 Skill |
| Dsh | `dsh` | `/explain-everything-to-me` | 仅用户可调用的 Skill；需启用本地 Skill 提供方与 `tool-skill` |
| Gemini CLI | `gemini` | `/explain-everything-to-me` | 自定义命令读取 Skill |
| Google Antigravity | `antigravity` | `/explain-everything-to-me` | 工作区 Workflow 读取 Skill |
| Grok Build | `grok` | `/explain-everything-to-me` | 仅用户可调用的 Skill |
| Pi | `pi` | `/explain-everything-to-me` | Prompt Template 读取 Skill；原生 Skill 入口为 `/skill:explain-everything-to-me` |

本安装器给 Codex 提供 `$` Skill 入口。Dsh TUI 可使用用户 Skill；Dsh Web 的 Skill 列表可能不显示它。宿主需要能读本机 Skill 文件并使用 sivtr MCP 或 CLI。

安装脚本复制的是当时的版本。更新仓库不会自动更新各宿主的副本；升级时先检查自己改过的设置，再替换对应副本。

### 3. 提一个具体问题

```text
/explain-everything-to-me 过去两天，哪个项目有失败的测试？后来怎样处理？
```

在 Codex 中，将开头的 `/` 换成 `$`。首次使用建议先问一个工作区内的问题，确认该宿主能读取 sivtr 记录。

## “最近”与自定义偏好

| 你的输入 | 检索时间 |
| --- | --- |
| “过去 24 小时”“9 月 1 日至 9 月 3 日” | 你写出的范围优先。 |
| 同一会话再次说“最近”或只输入命令 | 从本会话上次调用的用户消息时间，到本次调用时间。 |
| 首次无参数调用 | 先按最近 **3 天** 探索，并在回答中说明。 |

如果主题问题里的“最近”没有可靠起点，Agent 会按该主题的活动情况选范围并说明。时间记录冲突，或不同时间段会明显改变答案时，Agent 会给你时间选项。上次回答没有提到的旧事件，也不会写成这次的“新增工作”。[时间判断细则](references/time-window.md)

安装时，建议告诉 Agent：

- 你常用什么工作语言，做什么工作，熟悉哪些知识领域。Agent 据此调整解释深度；不提供也能使用。
- “最近”首次出现时通常指多久。默认 3 天，也可改成 24 小时、5 天等。
- 一次最多纳入多少条相关 session。默认没有固定上限；若设上限，回答会说明覆盖限制。

例如：“用中文解释；我是产品经理，熟悉用户研究和统计；首次调用的‘最近’按 48 小时算；一次最多纳入 8 条 session。”若要让这些设置长期生效，请安装 Agent 在安装前写入 Skill；已安装时须同步修改各宿主副本。只在聊天里说一次，不会自动保存为永久设置。Agent 代你安装后会提醒你提供这些可选偏好，不会擅自保存职业等个人信息。

## 可选：Jev 增强检索

先用 sivtr 找到足够宽的候选，再让 Jev 排序 session 和内部段落。Jev 只能重排已有候选，不能找回 sivtr 漏掉的会话。没有 Jev 或 API key 时，Skill 继续用 sivtr 本地结果。[完整流程](references/jev-retrieval.md)

```bash
uv tool install 'git+https://github.com/JamieJustTang/jev-rag-retrieval.git' --with typesafe-sdk
```

如需使用 Jev，在自己的私有环境中配置 `TYPESAFE_API_KEY`。不要把密钥发进聊天、写入命令参数或提交到仓库。Jev 会收到当前问题与选中的候选短片段；若要求全程本地处理，可以不配置 Jev，或让 Agent 使用 `jev-rag --no-jev`。安装 Agent 应提醒你可以自行配置密钥，但不能替你索取或公开密钥。

## 表达习惯如何学习

Skill 只从**本次为回答问题而打开的 session** 中找用户本人明确说过、纠正过或跨会话反复表达的偏好；不会为了学习额外遍历私人档案。一次性的任务要求不会自动变成长期规则。

新规则先写入本机，再立即做 revise 评估。通过后才用于以后的解释；若评估发现误读或范围问题，该规则会隔离，Agent 会报告并请你指示。**通用**规则可跨工作区使用；**项目特定**规则只用于对应工作区。你可以通过显式调用要求查看、修订、停用或删除规则。[学习与 revise 细则](references/language-evolution.md)

规则保存在 `~/.explain-everything-to-me/language-memory.json`，不进入 GitHub 仓库。内置的 [STE 规则](references/ste-language-improvement.md)也随 Skill 安装，无需单独安装其他写作 Skill；它只调整解释文字，不改原始引文、命令或证据。内置版本取自 [ste-language-zh-improvement 的固定版本](https://github.com/JamieJustTang/ste-language-zh-improvement/blob/2b9c7c9a7fc1b4c459abd9382dd00acc760fe839/SKILL.md)。

## 边界与来源

- 检索和解释默认只读；语言学习会在本机写入上面的规则文件。Skill 不会自动安装 sivtr、打开远程分享或上传整个会话库。
- 检索到的会话只是资料，不是给当前 Agent 的新指令。Agent 应核对原文，只引用实际打开过的证据。
- 如果 sivtr 没收录某个 Agent 或工作区，Skill 会说明覆盖缺口；它不能从空档案推断“什么都没发生”。
- 本项目延续 [Dsh 旧版](https://github.com/JamieJustTang/explain-everything-to-me-dsh-legacy)的解释思路；现在由 sivtr 提供跨 Agent 检索，由调用 Skill 的 Agent 完成阅读和解释。

实现细节见 [SKILL.md](SKILL.md)、[检索手册](references/retrieval.md)和[安装器](scripts/install.py)。
