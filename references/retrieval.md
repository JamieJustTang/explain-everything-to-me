# sivtr 检索手册

以下命令按 [sivtr 官方 Skill](https://github.com/Ariestar/sivtr/tree/main/skills/sivtr-memory) 与 [CLI 文档](https://sivtr.pages.dev/zh-cn/reference/cli/)编写。版本不同时，以本机 `sivtr --help` 和实际 MCP schema 为准。优先使用已连接的 MCP 同名工具；命令仅是 CLI 回退示例。

## 先确定检索范围

```bash
sivtr ws list
sivtr s all:agent --last 3d --latest 80 -f timeline
sivtr s docs:agent --last 3d --latest 20 -f timeline
```

`all:agent` 跨所有本机工作区及已挂载来源搜索。`agent` 面向当前工作区。工作区范围可用 `sivtr ws list` 返回的 origin，例如 `docs:agent`；示例中的 `docs` 必须换成真实 origin，不要猜名称。全局结果不能证明覆盖完整：即使命中数低于 `--limit`，跨工作区问题仍应按 `ws list` 对每个相关工作区补查。`--cwd` 可把当前工作区解析到指定目录。`--latest` 限制近期候选记录，不能误认为 session 数。只有确认当前会话确实被 sivtr 识别、且需要避免自引用时才加 `--exclude-current`；该选项在某些宿主/档案组合中会意外排除当前工作区的唯一相关会话，零命中时要移除它重试。

先看 `sivtr ws list`。`all:agent` 只覆盖已登记的工作区；当前目录若未登记，需对相应目录用 `agent --cwd /实际路径` 另查。不能把全局零命中解释成整个本机没有会话。检索输出量大时把 `--json` 写入权限为 600 的临时文件，再读取少量元数据；不要把完整 WorkSet 或大量同步警告直接交给 Agent 上下文。

定向问题示例：

```bash
sivtr s all:agent "parser benchmark" --last 30d --limit 30 -f timeline
sivtr s all:agent -m "解析器|parser|基准|benchmark" --last 30d --limit 30 -f timeline
sivtr s docs:agent "decision" --last 14d --limit 20 --refs
sivtr s all:agent --since 2026-09-25T10:00:00+08:00 --until 2026-09-25T16:00:00+08:00 --limit 40 -f timeline
```

位置参数是 BM25 文本查询，`-m` 是不区分大小写的正则过滤；二者不是同一种语法。`--last` 是相对时间，`--limit` 是输出硬上限；词面搜索漏掉主题时可搜标题、输入或别名，并用按时间浏览兜底。终端证据需要时用 `terminal` 或 `all:terminal` 另查。记录可能来自不同 provider，不能把一个 provider 当作全部 Agent。

上面 `--since` / `--until` 仅演示 RFC3339 格式。真正的时间必须来自[时间范围规则](time-window.md)中的本次与上次调用记录，不要照抄示例日期。

## 从命中到 session

```bash
sivtr s all:agent "release failure" --last 14d --limit 20 --save explain_hits --refs
sivtr show '@explain_hits[1]' --full
sivtr zoom '@explain_hits[1]' -C 2 --refs
sivtr nav '@explain_hits[1]' '~' --refs
```

`show` 查看原始记录，`zoom` 看前后，`nav ... '~'` 取得所在 session 的记录集合；按需要再 `show`，控制输出体量。`@name` 是临时 WorkSet，不是永久的解释结论。若 MCP 的字段或返回形态不同，依据工具 schema 实现同一“搜索 → 打开 → 上下文 → 会话阅读”的过程。

检索时先按 ref 的 origin/provider/session 标识去重。按“解释该问题需要多少证据”选择阅读量：同一会话多个词命中时只算一个候选会话；同一任务的后续 session 应串起时间线。对长会话先读开头与结尾，再补读有争议的决策、工具结果、测试和失败记录。不能因 token 预算只读结尾却声称了解全程。

不要运行裸 `sivtr`（会打开交互界面）、交互选择器、`sivtr clear`、`sivtr setup`、`sivtr init`、`sivtr share`、`sivtr remote add` 或修改配置来完成一次只读解释。
