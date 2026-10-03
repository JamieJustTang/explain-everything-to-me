# 日拱一卒：每日日志原型

## 目的

把一天的 Agent 对话和用户手写记录，整理成一篇可回看的日志。首页先讲今天在做什么、出现了什么转折、留下哪些对象、还有什么未完成；文件名作为正文中的可点击引用，读到相关判断时就能打开产物。左栏月历用虚线圆表示空白日期，有记录的日期会长出一个稳定的、按日期变化的 emoji。原始条目折叠在正文之后，供核对。右侧的 **READY TO SHARE** 是基于今日产物写给用户的个性化建议信，说明适合展示什么、找谁交流、可以问什么；它不触发发布、通知或联系他人。

## 设计规则

- 一条日志写一件可核对的变化。能指出产物时，填文件名或链接；只有讨论、没有行动时，写为“发现”，不冒充成果。
- Agent 从已打开的会话原文抽取事实，不从搜索摘要直接生成日志。自动写入条目必须带至少一个 WorkRef，说明它来自哪里。
- 同一天的同一事项使用稳定 `key` 更新（键含本地日期、工作区和事项），不因多次调用产生重复条目。用户手动改过的字段保留；用户删掉的自动条目不会再次出现。
- Agent 最多建议“可找人讨论”，不能标记“已经交流”。展示给谁、展示什么、何时发送，由用户决定。
- 日期按用户本地时区归属。跨午夜的会话按每项进展实际发生的时间归日，不能把整段长会话都算到最后一天。
- 原始会话仍保存在 sivtr；日志仅保存简短结论、产物位置和 WorkRef。避免复制密钥或长篇会话。
- 写摘要前先理解当天各工作线的目标与性质，再围绕起因、推进、转折、产物、局限写成连贯短文。正文不能只是把条目改写成清单；每节必须能追溯到当天条目。没有核对到的事实留白。
- 产物需填 `artifact` 名称和 `artifact_target`：可用 HTTPS 链接或本机绝对路径。网页中的本机链接会通过仅监听 localhost 的预览端点打开；超过 25 MB 的文件不在网页预览。路径也可在文件管理器中打开。页面不扫描磁盘查找产物。
- READY TO SHARE 必须引用至少一个产物，按用户的工作目标和产物成熟度写私人建议。推荐“可讨论”并不等于已经发表，也不等于用户已决定分享。
- 日志正文和建议信引用产物时，在句中写 `[[artifact:<条目 ID>]]`。页面将标记替换为带文件名的可点击链接；同节 `entry_ids` 仍保留可追溯关系。新写入的摘要若把有产物的条目列进 `entry_ids`，却不在正文里引用它，会被拒绝。旧摘要没有句中标记时，会在段末补一条内联“参见”链接。

## 当前原型

![使用虚构数据的日拱一卒 dashboard](../../assets/screenshots/journal-prototype.png)


```bash
python3 components/daily-journal/journal.py serve
```

页面位于 `http://127.0.0.1:8767/`。数据默认保存在 `~/.explain-everything-to-me/daily-journal/data.json`。可手动新增、编辑、删除条目，也可按日期查看。空日志不会自动填示例数据。单独展示虚构数据时：

```bash
python3 components/daily-journal/journal.py --data /tmp/journal-demo.json seed --input components/daily-journal/example.json
python3 components/daily-journal/journal.py --data /tmp/journal-demo.json serve --port 8767
```

Agent 的条目导入和叙事摘要写入接口已实现，但**还没有接入 `explain-everything-to-me` 的调用钩子，也没有每日定时任务**。目前不会自动扫描所有 Agent 会话。未来接入时，应在用户显式调用本 Skill 并要求记日志，或用户另设每日自动任务时，先按当日时间窗检索多宿主记录、阅读原文，核对产物，再写入条目和摘要。不能因为页面打开就扫描会话。

## 导入格式

把 JSON 写到本机文件，或通过标准输入传入：

```bash
python3 components/daily-journal/journal.py import --input /path/to/events.json
```

```json
{
  "events": [{
    "key": "2026-10-03:/absolute/workspace:stable-topic-key",
    "date": "2026-10-03",
    "kind": "artifact",
    "title": "留下第一版结构图",
    "detail": "图上已经能说明三个变量的关系；仍需核对边界条件。",
    "project": "示例项目",
    "artifact": "figure-draft.svg",
    "artifact_target": "/absolute/path/to/figure-draft.svg",
    "readiness": "discussable",
    "workrefs": ["codex/example/1"]
  }]
}
```

`kind` 可取 `progress | artifact | insight | share`；`readiness` 可取 `private | discussable`。`shared` 仅由用户在页面标记。`key` 应由本地日期、真实工作区和事项构成，不含随机时间戳。导入重复键时更新 Agent 字段，并保留用户修改。数据文件权限为 `0600`。

## 撰写今日日志与建议信

条目导入后，Agent 需阅读会话原文、打开产物，写一份结构化摘要，再执行：

```bash
python3 components/daily-journal/journal.py compose --input /path/to/digest.json
```

`digest.json` 的每个 `entry_ids` 必须指向同一天的已有条目。正文分节引用条目；有产物的条目还必须用 `[[artifact:<条目 ID>]]` 在对应句中引用文件。建议信至少引用一个产物，并把它写进信的正文。若来源条目后来被编辑或删除，页面提示重新撰写。

```json
{
  "date": "2026-10-03",
  "title": "从问题走到第一张可讨论的图",
  "lead": "今天把一个想法写成可检查的假设，并留下图稿。",
  "sections": [{"heading": "先把问题变得可检查", "body": "先列出两种解释，再把反例方向写进 [[artifact:sample-01]]。", "entry_ids": ["sample-01"]}],
  "closing": "下一步核对边界条件。",
  "letter": {"salutation": "写给今天的你", "body": "建议带着 [[artifact:sample-02]] 找合作者讨论。", "recipient": "熟悉问题的合作者", "suggested_ask": "哪条关系最缺证据？", "entry_ids": ["sample-02"]}
}
```

仓库中的 `example.json` 和 `example-artifacts/` 全是虚构示例，用于预览页面，不代表用户的真实日志。

## 待接入 Skill 时

1. 把此目录补上 `component.json`，再由安装器作为可选组件列出；用户选中后才安装。
2. 在 `SKILL.md` 增加一条有条件的调用路由，指向独立参考文件。明确按本地日期检索和核对、去重、失败回报。
3. 增加首次采集边界、跨会话去重和用户允许自动记录的设置。把手写日记与 Agent 摘录分开标注。
4. 如果用户要每日自动运行，用宿主的定时任务能力单独创建；当前原型不隐式启动后台扫描。
