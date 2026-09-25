# Jev 增强检索

可选工具：[jev-rag-retrieval](https://github.com/JamieJustTang/jev-rag-retrieval)。它是通用 JSON 记录排序器，不绑定 sivtr 或具体 Agent。官方 [TypeSafe Reranking 指南](https://docs.typesafe.ai/cookbooks/rerank_typesafe)明确：快速检索先给候选，Jev 只重排候选，无法找回漏掉的记录。

## 使用条件与边界

- 先按用户限定的时间、工作区、来源和隐私条件检索。不要让模型排序覆盖硬约束。对于空参数的跨工作区盘点，按工作区分别扩展候选，避免一个繁忙工作区挤掉其他工作区。
- `command -v jev-rag` 且环境中有 `TYPESAFE_API_KEY` 时可用 Jev。配置密钥表示允许把选中的问题和候选短片段发往 TypeSafe。用户明确要求只在本机处理时运行 `jev-rag --no-jev` 或只用 sivtr。
- 不为一次解释自动安装工具、索取密钥、修改环境或上传整个会话库。没有 Jev 时正常完成解释。

## 两级排序

1. 从用户问题写出实际信息需求；用 sivtr 的 BM25、别名、时间浏览和工作区范围得到足够宽的候选。只送入当前问题相关、已允许阅读的记录。搜不到时先扩大 sivtr 召回，不要让 Jev 对空候选打分。
2. 从已打开的候选记录整理 JSONL。每行至少有 `session_id`、`workref`、`text`；可加 `workspace`、`title`、`timestamp`。`workref` 必须指向可再次打开的原始记录；同名 session 跨工作区时填 `workspace` 区分。对于一条过长的记录，工具会分段并保留原 ref 与字符偏移。把临时文件放在私有目录，完成后删除。
3. 运行 `jev-rag --query '用户实际要知道的问题' --input /私有路径/records.jsonl --session-limit 8`。工具先用本地 BM25 建立 session 候选池，再用 Jev 排序 session；对选中 session 的段落再次排序。默认最多评估 30 个 session、80 个段落，可按问题规模调整 `--session-candidates` 与 `--passage-candidates`。这些是排序候选上限，不等于最终回答数。
4. 检查返回的 `mode`、`warnings`、`input_sessions`、`candidate_sessions` 和每条 `workref`。分数高的先读，低分但覆盖独特工作区、反证或后续决策的也应读。若 Jev 调用失败或候选覆盖不足，回到 sivtr 扩展查询并继续人工阅读。不要用固定 Jev 分数阈值删掉证据。
5. 对最终可能引用的 WorkRef 用 sivtr `show` / `zoom` / `nav` 打开原文；核对上下文、时间和最终状态。只用这些原文与必要的当前状态核查写答案，不把排序结果当引用本身。

工具的输出会含记录正文；不要把含私人会话的 JSONL 或结果提交到仓库。Jev 请求最多包含 1,500 字符的问题及每段最多 2,500 字符的候选。若用户需要严格的本地处理，保持 `--no-jev`。
