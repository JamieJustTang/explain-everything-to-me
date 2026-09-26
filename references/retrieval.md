# sivtr 检索手册

以下命令按 [sivtr 官方 Skill](https://github.com/Ariestar/sivtr/tree/main/skills/sivtr-memory) 与 [CLI 文档](https://sivtr.pages.dev/zh-cn/reference/cli/)编写。版本不同时，以本机 `sivtr --help` 和实际 MCP schema 为准。**已连接 MCP 时直接用 MCP 工具，不必为了运行下列 CLI 示例而切换到 shell。**`sivtr_status.origins` 对应 CLI 的工作区列表；`sivtr_search` 对应搜索。

## 先确定检索范围

```bash
sivtr ws list
sivtr s archive:agent --cwd "$PWD" --last 3d --latest 30 -f timeline
sivtr s archive:agent --last 3d --latest 80 -f timeline
sivtr s all:agent --last 3d --latest 80 -f timeline
sivtr s docs:agent --last 3d --latest 20 -f timeline
```

`archive:agent --cwd /实际路径` 在归档索引阶段限制到一个工作区；不传 `--cwd` 则查询所有本机已归档工作区，不要求预先登记。多工作区盘点不要传 `--cwd`。旧版 `agent --cwd` 也能定位当前工作区，但会先加载较多历史记录。`all:agent` 仍跨**已登记**的本机工作区及当前工作区的远端挂载搜索，它并不代表全机归档。工作区范围可用 `sivtr ws list` 返回的 origin，例如 `docs:agent`；MCP 下可读 `sivtr_status` 返回的 `origins`。示例中的 `docs` 必须换成真实 origin。`archive:agent` 需要包含此功能的 sivtr 版本；旧版报 unknown scope 时退回 `agent --cwd` 加 `all:agent`，并注明未登记工作区尚未覆盖。`--latest` 限制近期候选记录，不能误认为 session 数。只有确认当前会话确实被 sivtr 识别、且需要避免自引用时才加 `--exclude-current`；零命中时要移除它重试。

每次 `archive:` 查询必须有 `--since`、`--until` 或 `--last`。全历史问题分段检索；若 sivtr 报窗口过大，缩短时间段或限定 provider。`--limit` 只限制最终返回数，不能代替时间边界。

全机归档与工作区注册表是两张不同的清单。`sivtr_status.origins` 只显示后者，不能用它判断 `archive:agent` 能否找到会话。归档零命中时可用 `sivtr_stats` 核对该时间段是否有记录，但统计中的记录也可能不是目标主题。确认时间格式有效后，先放宽术语或时间，再如实说明缺口。检索输出量大时把 `--json` 写入权限为 600 的临时文件，再读取少量元数据；不要把完整 WorkSet 或大量同步警告直接交给 Agent 上下文。

定向问题示例：

```bash
sivtr s archive:agent "parser benchmark" --last 30d --limit 30 -f timeline
sivtr s archive:agent -m "解析器|parser|基准|benchmark" --last 30d --limit 30 -f timeline
sivtr s docs:agent "decision" --last 14d --limit 20 --refs
sivtr s archive:agent --cwd "$PWD" --since 2026-09-25T10:00:00+08:00 --until 2026-09-25T16:00:00+08:00 --limit 40 -f timeline
```

位置参数是 BM25 文本查询，`-m` 是不区分大小写的正则过滤；二者不是同一种语法。`--last` 是相对时间，`--limit` 是输出硬上限；词面搜索漏掉主题时可搜标题、输入或别名，并用按时间浏览兜底。终端证据需要时用 `terminal` 或 `all:terminal` 另查。记录可能来自不同 provider，不能把一个 provider 当作全部 Agent。

项目名、目录名通常是 `cwd` 元数据，不一定出现在正文。要确认某工作区是否有会话，先用 `archive:agent --cwd /实际工作区路径` 加时间范围、不带关键词浏览；若从全机入口核对，读取 `archive:agent` 的时间浏览结果并按 `cwd` 分组。前 N 条按项目名排序的全文命中没有该工作区，不等于该工作区没有记录。

上面 `--since` / `--until` 仅演示 RFC3339 格式。真正的时间必须来自[时间范围规则](time-window.md)中的本次与上次调用记录，不要照抄示例日期。

## 从命中到 session

```bash
sivtr s archive:agent "release failure" --last 14d --limit 20 --save explain_hits --refs
sivtr show '@explain_hits[1]' --full
sivtr zoom '@explain_hits[1]' -C 2 --refs
sivtr nav '@explain_hits[1]' '~' --refs
```

`show` 查看原始记录，`zoom` 看前后，`nav ... '~'` 取得所在 session 的记录集合；按需要再 `show`，控制输出体量。`@name` 是临时 WorkSet，不是永久的解释结论。若 MCP 的字段或返回形态不同，依据工具 schema 实现同一“搜索 → 打开 → 上下文 → 会话阅读”的过程。

全机归档检索后，优先从刚保存的 WorkSet 按序号打开，例如 MCP 的 `sivtr_show(source="@last[1]")` 或上例的 `@explain_hits[1]`。若会继续检索，先用 `save` 给候选集命名，避免 `@last` 被下一次搜索覆盖。不要对每个归档命中的裸 WorkRef 反复调用 show；旧版 sivtr 可能每次重新加载整个工作区。

检索时先按 ref 的 origin/provider/session 标识去重。按“解释该问题需要多少证据”选择阅读量：同一会话多个词命中时只算一个候选会话；同一任务的后续 session 应串起时间线。对长会话先读开头与结尾，再补读有争议的决策、工具结果、测试和失败记录。不能因 token 预算只读结尾却声称了解全程。

不要运行裸 `sivtr`（会打开交互界面）、交互选择器、`sivtr clear`、`sivtr setup`、`sivtr init`、`sivtr share`、`sivtr remote add` 或修改配置来完成一次只读解释。
