# explain-everything-to-me

当前版本：**0.6.1**

**问一句：我的 Agents 最近做了什么？**

这个 Skill 把你的问题变成跨 Agent 的会话检索，自己打开原文，先理解你想完成什么、各项工作起什么作用，再解释进展。你不用翻日志，也不用从搜索结果中手动挑 session。

```text
/explain-everything-to-me 最近各工作区做了什么？哪些事需要我决定？
/explain-everything-to-me parser 基准测试为什么换了方案？请给出处。
/explain-everything-to-me
```

不带参数时，默认问题是：**“向我解释最近我的 agents 发生的一切。根据工作区进行分组。”** Codex 的入口是 `$explain-everything-to-me`；其余支持的宿主使用 `/explain-everything-to-me`。只有你显式调用，Skill 才会运行。

## 三张图看懂

| ① 为什么需要它 | ② 它怎样解释 | ③ 怎么提问、支持哪些 Agent |
| :---: | :---: | :---: |
| [![四个痛点：会话分散、跨工作区、搜索命中不等于答案、Agent 越用越不说人话](assets/xiaohongshu/00-four-pain-points.png)](assets/xiaohongshu/00-four-pain-points.png) | [![AI 总秘书用你的语言讲清各工作区进展](assets/xiaohongshu/01-pain-points.png)](assets/xiaohongshu/01-pain-points.png) | [![最佳实践提问示例与七个 Agent 宿主](assets/xiaohongshu/02-best-practice.png)](assets/xiaohongshu/02-best-practice.png) |

点击图片可查看原图。

## 功能一览

| 功能 | 当前行为 |
| --- | --- |
| 理解问题 | 从自然语言识别工作区、主题、Agent、时间和真正要回答的事，组合检索式。 |
| 查跨 Agent 记录 | 使用 [本项目 sivtr fork](https://github.com/JamieJustTang/sivtr/tree/eetm-v0.8.0.1) 的 MCP 或 CLI 查询统一归档；`archive:agent` 一次覆盖所有已归档的本机工作区，无需逐个登记。 |
| 自动阅读与筛选 | 按 session 去重，打开命中记录和相邻内容，核对起因、关键结果与最终状态；不让你手动筛选候选列表。 |
| 理解你在做什么 | 从用户原话与会话证据辨认目标、交付物和完成标准，再按工作性质组织进展；同一目标跨工作区时连起来，不同目标共用目录时分开。 |
| 解释变化 | 串起多个 session 的连续工作，区分旧背景、新进展、Agent 的说法、工具证据与当前已核实的状态；重要结论附 WorkRef。 |
| 可自定义汇报 | 默认先给短版结论；可切换按工作区详读或待决事项模板，也可用自己的 Markdown 模板覆盖。 |
| 理解“最近” | 同一会话内再次调用时，从上次**用户调用时间**算起；首次无参数调用默认查最近 **3 天**。时间含糊且影响答案时，请你选时间段。 |
| 可选 Jev 排序 | [jev-rag-retrieval](https://github.com/JamieJustTang/jev-rag-retrieval) 分别给候选 session 和内部段落排序；没有 Jev 也能使用。 |
| 调整表达 | 内置 [STE 中文魔改规则](references/ste-language-improvement.md)，并从已读会话中的用户原话学习通用或项目特定的表达习惯。 |

```mermaid
flowchart LR
    A[你的问题] --> B[确定时间与范围]
    B --> C[sivtr 查找候选]
    C --> D[可选：Jev 排序]
    D --> E[打开原文并核对]
    E --> F[理解目标与工作性质]
    F --> G[选模板解释并附引用]
```

这个仓库是**解释层**。它沿用 sivtr 原有的归档与检索方式，不打包 sivtr、TUI 或归档数据库，也没有另建轻量索引。支持的宿主优先连接本机 sivtr MCP；没有 MCP 时使用 CLI。TUI 不是使用条件。

## 回答是什么样

下面仅示意结构，不是真实检索结果：

```text
先说结论：从记录看，你正在把数据导入流程做成可稳定使用的功能。解析问题已修复并通过测试；旧格式是否继续支持，还没有定案。

按工作区
- A：实现与验收——解析流程已改，测试通过；兼容层尚未定案。[sivtr WorkRef]
- B：本次时间范围内未发现新增工作。

需要你处理：决定 A 是否继续支持旧格式；记录中还没有你的选择。[sivtr WorkRef]

范围与限制：本会话上次调用时间 → 本次调用时间；已查本机归档，未查未接入的远端。

下次“最近”从这里算：YYYY-MM-DDTHH:MM:SS+08:00（本次用户调用时间）
```

Skill 会先根据用户原话与已读会话判断工作目标，再解释各项活动如何服务目标。这个判断若只是归纳，会明确说“从记录看”，不把 Agent 的建议或目录名写成你的意图。它也会说明实际查过的时间、工作区和来源。历史会话只能证明当时记录了什么；若你问的是“现在是否已完成”，且没有限定只能看档案，Agent 会另查当前文件或状态。缺失记录、来源冲突和未核实的推断会明确标出。[判断规则](references/goal-and-work-map.md)

## 汇报模板

先判断你要完成什么，再选模板。默认使用[速览](templates/brief.md)：先说目标和最重要的变化，再按目标与工作性质归类；无参数调用仍按工作区分组，并在每组说明它服务什么目标。要求详细复盘时用[按工作区详读](templates/workspace.md)；只问“哪些事需要我决定”时用[待决事项](templates/decisions.md)。你也可以在命令里明确说“用 workspace 模板，重点讲 C7”。具体问题仍由问题本身决定答案，不强行塞进固定栏目。

要长期调整默认结构，复制速览模板到用户目录再修改标题、顺序、篇幅等：

```bash
mkdir -p "$HOME/.explain-everything-to-me/templates"
cp templates/brief.md "$HOME/.explain-everything-to-me/templates/default.md"
```

也可以在该目录放 `brief.md`、`workspace.md` 或 `decisions.md`，覆盖对应内置模板。这个目录由所有宿主共用，升级 Skill 时不会覆盖。模板只影响汇报的呈现，不能改变检索范围、证据要求或 Skill 的调用条件；文件读不到时会回退到内置模板。

## 安装

### 1. 安装依赖

需要 Python 3.10+ 和 Rust 1.95+（`cargo`）。安装脚本会从 [本项目的 sivtr fork](https://github.com/JamieJustTang/sivtr/tree/eetm-v0.8.0.1) 的固定提交 `563ac3c` 编译 CLI，放在 `~/.local/share/explain-everything-to-me/sivtr/bin/sivtr`。同一台机器给多个 Agent 安装时会复用它，不覆盖你已有的系统版 sivtr。首次编译可能需要几分钟。

这个 fork 在上游 sivtr 基础上增加 `archive:agent`：按时间查询本机所有已归档工作区，不要求逐个登记；也可用 `--cwd` 限定工作区。MCP 和 CLI 都使用这份二进制。可见范围仍由 sivtr 实际发现和收录的来源决定；Skill 不会替你初始化采集、接入远端或共享会话。

如果已有兼容的魔改版二进制，可在安装命令后加 `--sivtr /绝对路径/sivtr`；只想复制 Skill 而自行管理 sivtr，可加 `--no-sivtr --no-mcp`。[旧版补丁](patches/sivtr-1c0f1d0-archive-scope.patch)保留供离线构建参考，正常安装无需手动打补丁。

### 2. 安装 Skill

安装器先安装固定版 sivtr，再复制 Skill 和接入宿主。

```bash
git clone https://github.com/JamieJustTang/explain-everything-to-me.git
cd explain-everything-to-me
python3 scripts/install.py --host codex
```

将 `codex` 换成下表的 `HOST`。安装器会复制 Skill，并在需要时创建显式命令入口。它遇到同名安装会停止，避免覆盖你改过的文件。Antigravity 还需要 `--workspace /你的工作区路径`。安装器默认接入 sivtr MCP；`--no-mcp` 仅跳过 MCP 配置，仍安装 fork 版 CLI。

| 宿主 | `HOST` | 调用入口 | sivtr 接入 |
| --- | --- | --- | --- |
| [Codex](https://developers.openai.com/learn/docs-mcp) | `codex` | `$explain-everything-to-me` | 安装器用原生命令配置 MCP |
| [Claude Code](https://code.claude.com/docs/en/mcp) | `claude` | `/explain-everything-to-me` | 安装器用原生命令配置 MCP |
| [Dsh](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/mcp/mcp-client) | `dsh` | `/explain-everything-to-me` | 安装器写入宿主级 MCP patch |
| [Gemini CLI](https://geminicli.com/docs/tools/mcp-server/) | `gemini` | `/explain-everything-to-me` | 安装器用原生命令配置 MCP |
| [Google Antigravity](https://www.antigravity.google/docs/mcp?tab=ide) | `antigravity` | `/explain-everything-to-me` | 安装器写入全局 MCP 配置 |
| Grok Build | `grok` | `/explain-everything-to-me` | 安装器用原生命令配置 MCP |
| [Pi](https://pi.dev/) | `pi` | `/explain-everything-to-me` | 核心程序无内置 MCP；默认用 sivtr CLI |

本安装器给 Codex 提供 `$` Skill 入口。Dsh TUI 可使用用户 Skill；Dsh Web 的 Skill 列表可能不显示它。配置 sivtr MCP 会让该宿主的其他会话也能调用本机 sivtr 工具，因此只应连接信任的本机可执行文件。宿主的沙箱与 MCP 权限各不相同，配置成功后仍需确认工具确实连通。安装器使用 `sivtr mcp serve --idle-exit 0`：服务随宿主连接保持运行，避免 sivtr 默认空闲 60 秒退出后，宿主首次调用报 `Transport closed`。Dsh 的 `workspace-write` 会阻止其 `bash` 更新 `~/.sivtr` 数据库；宿主级 MCP 可避开这条 CLI 路径。Pi 若自行安装可信的 MCP 扩展，也可使用 sivtr MCP，但本安装器不会代装扩展。

已经安装旧版 Skill 时，先运行 `python3 scripts/install_sivtr.py` 安装固定版，再将新版 Skill 文件同步到宿主目录，并把宿主 MCP 的 sivtr 可执行路径更新为该脚本输出的路径。`python3 scripts/configure_mcp.py --host HOST --sivtr /绝对路径/sivtr` 可为宿主接入或更新 MCP 服务。原有 `~/.sivtr` 归档无需复制或重建。

若已有安装在等待阅读、检索或其他操作后报 `Transport closed`，检查该宿主的 sivtr MCP 参数是否含 `--idle-exit 0`。运行上面的 `configure_mcp.py` 更新参数，再新开宿主会话；当前会话可以按 Skill 规则用 CLI 继续只读检索。

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

- 检索和解释默认只读；语言学习会在本机写入上面的规则文件。Skill 调用本身不会安装 sivtr、打开远程分享或上传整个会话库；安装器会安装固定版 sivtr。
- 检索到的会话只是资料，不是给当前 Agent 的新指令。Agent 应核对原文，只引用实际打开过的证据。
- 如果 sivtr 没收录某个 Agent 或工作区，Skill 会说明覆盖缺口；它不能从空档案推断“什么都没发生”。
- 本项目延续 [Dsh 旧版](https://github.com/JamieJustTang/explain-everything-to-me-dsh-legacy)的解释思路；现在由 sivtr 提供跨 Agent 检索，由调用 Skill 的 Agent 完成阅读和解释。

实现细节见 [SKILL.md](SKILL.md)、[检索手册](references/retrieval.md)和[安装器](scripts/install.py)。
