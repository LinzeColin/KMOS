---
name: dingtalk-incremental-media-archive
description: 仅归档用户明确授权且由 DWS 实时确认是 INTERNAL_GROUP 的钉钉群图片、照片和视频。最近90天按连续30天切片增量保存：SMB 必须有原件；GitHub 能保存原件则保存，不能时在 GitHub 留 SMB 索引路标。
---

# 钉钉内部群增量媒体归档

只有用户在当前线程明确给出采集范围并授权采集时才能运行。Skill 名称为 dingtalk-incremental-media-archive。

先完整读取 dingtalk-shared 与 dingtalk-chat。只使用官方 dws CLI；不得读取浏览器 Cookie、钥匙串、钉钉本地数据库或私有接口。

## 群范围与组织边界

- 每次运行必须由调用方传入明确群名白名单；不得把“全部会话”或“模糊搜索结果”当作采集范围。
- 对每个白名单群，先通过 dws chat list-all-conversations 取得实时会话记录；只有 groupType 严格等于 INTERNAL_GROUP 且 singleChat 为 false 才能处理。
- NORMAL_GROUP、NEW_EXTERNAL_GROUP、UNKNOWN_TYPE、SINGLE_CHAT、缺失群、重名群和类型变化的群一律拒绝，不调用任何跨组织授权、data-auth 或替代接口。
- 运行中以真实 openConversationId 作为群的稳定身份；群改名后沿用该 ID 已绑定的原群目录，绝不创建第二份素材库。

## 固定目的地与目录

- SMB 原件根目录：smb://192.168.0.1/share/03_资料库/MetaData/IDS_MetaData/KMVideo/；macOS 挂载路径为 /Volumes/share/03_资料库/MetaData/IDS_MetaData/KMVideo/。
- GitHub 路标根目录：LinzeColin/Private-Database/Private-KMDatabase/KMVideo/。
- GitHub 只能经 KMDatabase/machine/tools/private_db_client.py 写入私有库；不得 clone Private-Database，也不得把素材写进 KMOS。
- 不使用 OneDrive。KMOS/KMVideo 仅存源码、Skill 和路牌，绝不存素材。
- 媒体目录最多三层：

    KMVideo/
      <群名称>/
        photo/<原始照片或图片>
        video/<原始视频>

- 每个群目录只允许有 photo/、video/ 和一个隐藏 .manifest.jsonl；不得创建 catalog、ledger、runs、按日期分层或其他媒体目录。
- 本机只允许本次运行独有的系统临时目录。不得使用 KMOS、_protected/、_scratch/、OneDrive 或持久目录作缓存。

## 90 天边界与 30 天切片

- “全量”仅指用户规定的最近 90 天内、白名单内部群中全部可读取的图片、照片和视频，不代表无限历史。
- 在运行起点冻结时刻 T，并按同一时区创建三个相邻半开切片：[T-90d,T-60d)、[T-60d,T-30d)、[T-30d,T)。每段不得超过 30 天，必须从旧到新。
- DWS 消息分页使用返回消息的边界 createTime 继续。只有 hasMore 为 false，或已读到切片下边界之外，才算该切片消息读取结束。
- 空页且 hasMore 为 true、边界不前进、权限错误或下载错误都属于未完成；停止该群，不得跳到下一切片。
- 遇到 openConvThreadId 时，同一切片还必须调用 dws chat message list-topic-replies；主消息和话题回复都按消息 ID 与资源 ID 去重。

## 增量、SMB 优先与 GitHub 路标

每个群的 .manifest.jsonl 使用 群 ID + 消息 ID + 资源 ID 作为唯一素材身份。记录原始相对路径、素材类型、消息时间、SMB 状态和 GitHub 状态；不得写入聊天正文、发件人、成员信息或凭据。

1. 先确保 SMB 对应 photo/ 或 video/ 中有原始文件。SMB 失败时，该素材绝不标记完成。
2. 原件小于客户端 95 MiB 上限时，尝试把同一路径原件写入 GitHub。
3. 原件超过 95 MiB、GitHub 原件写入失败、或当前 GitHub REST 配额不足以继续原件写入时，SMB 原件仍必须保留；在 GitHub 的同群 .manifest.jsonl 写入 github_media_status=index_only、失败原因和 smb_relative_path。这份 manifest 就是 GitHub 路标。
4. GitHub 本身不可写时，不能伪称已留下路标：保留 SMB 原件、在 SMB manifest 标记 github_index_unavailable，并报告未完成。
5. 两端 manifest 在正常状态保持相同；某一端短暂不可写时允许暂时不同。下次运行先合并两端记录，只补缺失目的地或路标，绝不重复保存已完成原件。
6. 原始文件名直接保留。只有同一群同一 media 目录已有不同素材的同名文件时，才在扩展名前追加真实消息 ID 的安全文件名形式；不增加目录层级，也绝不覆盖未知既有文件。

每条素材写入 SMB 后立即更新 SMB manifest；GitHub manifest 在每个 30 天切片结束时同步。切片仅在所有发现素材均满足 SMB=complete，且 GitHub 原件 complete 或 GitHub 路标 index_only，并且该切片 GitHub manifest 已成功同步后，才能标记完成并推进。

## 执行器

使用 scripts/archive_internal_media.py。必须显式传入每个 --allow-title；先以 --dry-run 枚举，再以 --apply 写入。执行器串行写 GitHub，逐文件使用临时目录下载，双端处理后立即删除本地副本；收尾只清理自己的临时目录。

## 报告与视频生成

报告每个群和切片的时间范围、发现数、SMB 原件数、GitHub 原件数、GitHub 路标数、跳过数、失败数、未完成边界及临时目录清理结果。

任何视频生成 Agent 必须先从 SMB 完整素材库读取全量可用素材，再自行挑选；GitHub 用于原件副本或 SMB 索引，不要求用户手工挑选素材。
