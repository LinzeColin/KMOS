---
name: dingtalk-incremental-media-archive
description: 通过 DingTalk Workspace（DWS）把所有授权群、所有历史时段的图片、照片、视频和语音增量归档到 Private-Database 的 KMVideo 私有 GitHub 素材库。用于创建、恢复、审计或执行 KMVideo 群素材采集；已归档的源素材绝不重复下载或上传。
---

# DWS 增量媒体归档

只在用户当前线程明确授权采集范围时执行。默认范围由用户指定；“全量”必须同时表示所有可见群、全部历史页、图片、照片、视频和语音。

先完整读取 `dingtalk-shared` 与 `dingtalk-chat`。只使用官方 `dws` CLI；不读取浏览器 Cookie、钥匙串、钉钉本地数据库或私有接口。

## 不可突破的落地边界

- `KMOS/KMVideo/` 只保存本 Skill 的源码，绝不保存素材、缩略图、群聊正文、下载缓存或运行日志。
- 素材字节只允许进入 `LinzeColin/Private-Database` 关联的私有 GitHub Release；`Private-KMDatabase/KMVideo/` 只保存台账、目录和远端素材指针。
- 不使用本机磁盘、`_protected/`、`_scratch/`、OneDrive、外接盘、网络共享或临时下载目录作为素材中转、缓存或备份。
- 只在存在“DWS → 私有 GitHub Release”的直接流式传输能力时采集。若命令要求本地 `--output`，停止并报告 `CLOUD_STREAM_UNAVAILABLE`；不得改用本机暂存。
- 不在公共仓、Skill 源码、AgentDatabase registry 或用户可见报告中写入群名、会话 ID、消息正文、素材名、下载 URL、凭据或素材字节。

## 增量唯一性契约

把每个媒体资源的不可变来源身份作为唯一键：

`profile_scope + openConversationId + openMessageId + resourceRefId`

`resourceRefId` 必须来自 DWS 的真实返回并能代表该条资源；没有稳定资源标识或版本标识时，停止该项并记为 `IDENTITY_UNAVAILABLE`。不要按文件名、时间、大小或内容猜测同一素材。

每次运行必须先读取私有台账。台账状态为 `archived` 的来源身份是已完成项：不再下载、不再上传、不新建第二个素材对象。若第一次完成了 1–80，第二次发现 1–85，只能传输 81–85；1–80 只保留为已归档记录。

读取 [`references/ledger-contract.md`](references/ledger-contract.md) 后再处理远端台账或恢复中断批次。

## 采集顺序

1. 确认当前 DWS profile 唯一且授权有效；没有唯一当前组织时停止，不选择最近或第一个 profile。
2. 枚举所有可见群，逐页直到 API 明确结束。任何 `hasMore=true`、未解析 cursor、失败页或权限缺口都使本轮全量状态为 `INCOMPLETE`。
3. 对每个群从已知最早边界开始遍历消息分页，直至服务端明确终点。不得用当前页面为空代替历史终点。
4. 仅从真实消息 `resourceRefs` 提取图片、照片、视频和语音资源。保留每条来源身份，不凭群名或文件名合并。
5. 先向私有 GitHub 台账查询来源身份。`archived` 立即跳过；`pending` 或 `failed` 仅依据已有远端回执恢复，不重新传输已确认归档的对象。
6. 对真正新增项，使用已验证的云端流式执行器直接上传到私有 GitHub Release。上传成功后取得远端回执，才把该身份写为 `archived`。
7. 对上传失败、身份缺失、分页未闭合或权限不足的项写入相应非完成状态；不得把群 cursor 越过该页，也不得把本轮表述为全量完成。
8. 仅在所有群都取得历史终点、所有新增项都有远端回执、且没有未处理失败项时，写入 `COMPLETE_ALL_GROUPS_ALL_TIME`。否则写 `INCOMPLETE` 并列出边界类别和计数。

## 中断与恢复

- 先有远端素材回执，后有 `archived` 台账记录；两者缺一不可。
- `pending` 代表尚未完成，不代表可重新上传。恢复时先读其远端回执；能确认已存在则补写台账，不能确认则保留 `REMOTE_RECEIPT_UNAVAILABLE`，不猜测。
- 任何群的历史页、权限或媒体流式能力不完整时，保留其他群的已完成增量结果，但全局状态必须是 `INCOMPLETE`。
- 永不删除已有素材、台账项或 Release 资产来“重新开始”。修复范围只处理未完成的新来源身份。

## 报告格式

只报告汇总：群总数、历史闭合群数、新发现数、新归档数、已归档跳过数、失败数、未闭合边界数、全局状态和唯一下一步。不要输出私有来源标识或素材信息。

对“全量完成”的声明必须同时有：所有群枚举结束证据、所有群历史结束证据、每个新增项的远端回执、以及台账中零个未处理项。任一证据缺失时，只能报告 `INCOMPLETE`。
