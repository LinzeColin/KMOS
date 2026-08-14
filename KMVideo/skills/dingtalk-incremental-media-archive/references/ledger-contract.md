# KMVideo 私有增量台账契约

本文件定义私有 `Private-KMDatabase/KMVideo/` 下的元数据协议。它不是素材存储位置，且不应进入公开仓或本机运行目录。

## 私有目录职责

| 私有位置 | 内容 |
| --- | --- |
| `KMVideo/ledger/` | 以来源身份为键的归档状态记录 |
| `KMVideo/catalog/` | 可供后续视频生成检索的媒体元数据与 Release 指针 |
| `KMVideo/runs/` | 仅汇总状态、分页闭合状态和失败类别的运行记录 |
| 私有 GitHub Release | 原始图片、照片、视频和语音字节 |

使用 `KMDatabase/machine/tools/private_db_client.py` 对私有台账进行小型元数据读写；不得 clone Private-Database，也不得把素材字节交给该客户端或 Git 普通提交。

## 一条台账记录

每条记录至少包含以下逻辑字段。字段值只保留在私有数据库：

| 字段 | 作用 |
| --- | --- |
| `source_identity` | `profile_scope + conversation + message + resource` 的不可变组合 |
| `source_kind` | `image`、`video` 或 `voice` |
| `observed_at` | DWS 返回的观察时间 |
| `state` | `discovered`、`pending`、`archived`、`failed`、`blocked` 之一 |
| `release_receipt` | 私有 GitHub Release 与资产的远端回执；仅 `archived` 必填 |
| `catalog_pointer` | 指向私有目录条目的稳定引用 |
| `failure_code` | 非完成状态的机器可读原因 |
| `run_id` | 首次发现或最后处理它的运行标识 |

`archived` 是唯一的去重终态。任何新一轮先批量读取已知 `source_identity`；存在 `archived` 即跳过字节传输。不得按本地文件是否存在、文件名相同或目录内容相同来决定跳过。

## 原子状态转换

```text
absent -> discovered -> pending -> archived
                         |          ^
                         v          |
                    failed/blocked -+
```

只有拿到可读取的私有 Release 回执后才允许 `pending -> archived`。若过程在上传后中断，保留 `pending` 并在下次从回执恢复；不能确认回执时不得重新上传或伪造完成。

## 历史闭合与增量窗口

- 记录每个群最后一个**已明确闭合**的历史边界，而不是仅记录最后一次运行时间。
- 一个群的中间页失败、`hasMore=true` 但 cursor 不可用、或权限不足时，禁止推进其闭合边界。
- 新运行可以重读消息元数据以发现迟到消息，但必须先查询台账，因此即使回读 1–80，也不会再次传输 1–80 的素材字节。
- 全局“所有群所有时间”仅在每个当前可见群均有明确闭合边界时成立；新增群或恢复访问的群自动使全局状态回到 `INCOMPLETE`，直至其历史闭合。

## 视频生成交接

后续生成视频时，先查询 `KMVideo/catalog/` 的全量私有索引，再由生成任务依据主题、时间、媒体类型和可用性自行挑选素材。只有被选中的源素材可由云端执行器按 Release 指针流式读取；不把整库下载到本机，也不要求用户手选素材。
