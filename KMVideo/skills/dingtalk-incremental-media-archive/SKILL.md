---
name: dingtalk-incremental-media-archive
description: 仅归档用户明确授权且由 DWS 实时确认是 INTERNAL_GROUP 的钉钉群图片、照片和视频。用户指定起点至冻结终点按连续30天切片增量保存：SMB 必须有原件；GitHub 能保存原件则保存，不能时在 GitHub 留 SMB 索引路标。
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

## 历史边界与 30 天切片

- “全量”只指用户在本线程明确批准的起点至冻结终点内、白名单内部群中全部可读取的图片、照片和视频；不得自行扩大为无限历史或跨组织会话。本次已授权任务范围为 `[2026-01-01 00:00:00, T)`。
- 调用方必须在起点超过最近 90 天时显式传入 `--start`；未传 `--start` 才允许默认最近 90 天。按同一时区创建相邻半开切片，每段不得超过 30 天，必须从旧到新连续前滚直到冻结终点 T。
- DWS 消息分页使用返回消息的边界 createTime 继续。只有 hasMore 为 false，或已读到切片下边界之外，才算该切片消息读取结束。
- 空页且 hasMore 为 true、边界不前进、权限错误或下载错误都属于未完成；停止该群，不得跳到下一切片。
- 遇到 openConvThreadId 时，必须调用 dws chat message list-topic-replies；已发现的话题 ID 要持续带入后续切片，以覆盖父消息与回复跨切片的情况。主消息和话题回复都按消息 ID 与资源 ID 去重。

## 增量、SMB 优先与 GitHub 路标

每个群的 .manifest.jsonl 使用 群 ID + 消息 ID + 资源 ID 作为唯一素材身份。记录原始相对路径、素材类型、消息时间、SMB 状态和 GitHub 状态；不得写入聊天正文、发件人、成员信息或凭据。

1. 先确保 SMB 对应 photo/ 或 video/ 中有原始文件。SMB 失败时，该素材绝不标记完成。
2. 原件小于客户端 95 MiB 上限时，尝试把同一路径原件写入 GitHub。
3. 原件超过 95 MiB、GitHub 原件写入失败、或当前 GitHub REST 配额不足以继续原件写入时，SMB 原件仍必须保留；在 GitHub 的同群 .manifest.jsonl 写入 github_media_status=index_only、失败原因和 smb_relative_path。这份 manifest 就是 GitHub 路标。
4. GitHub 本身不可写时，不能伪称已留下路标：保留 SMB 原件、在 SMB manifest 标记 github_index_unavailable，并报告未完成。
5. 两端 manifest 在正常状态保持相同；某一端短暂不可写时允许暂时不同。下次运行先合并两端记录，只补缺失目的地或路标，绝不重复保存已完成原件。
6. 原始文件名直接保留。只有同一群同一 media 目录已有不同素材的同名文件时，才在扩展名前追加真实消息 ID 的安全文件名形式；不增加目录层级，也绝不覆盖未知既有文件。
7. 同一群同一时刻只允许一个归档写入器。不同历史段也不得并发覆盖同一群的 manifest；如需并行，必须按互不重叠的群白名单拆分，或等待前一写入器结束后再启动下一段。

每条素材写入 SMB 后立即更新 SMB manifest；GitHub manifest 在每个 30 天切片结束时同步。切片仅在所有发现素材均满足 SMB=complete，且 GitHub 原件 complete 或 GitHub 路标 index_only，并且该切片 GitHub manifest 已成功同步后，才能标记完成并推进。

## 执行器

使用 scripts/archive_internal_media.py。必须显式传入每个 --allow-title；先以 --dry-run 枚举，再以 --apply 写入。执行器串行写 GitHub，逐文件使用临时目录下载，双端处理后立即删除本地副本；收尾只清理自己的临时目录。

- 常规归档：`--start`、`--end`、`--window-days 30` 与 `--apply`。若当前存在 GitHub 原件写入器，历史段使用 `--smb-only`，先完成 SMB 原件与本地 SMB manifest。
- 复扫补漏：规则修正、任务中断恢复或清单合并后，以同一时间范围运行 `--smb-only --reconcile --apply`。它重读 DWS，但对已完成 SMB 原件直接跳过；只下载 manifest 中缺失的素材，不重复保存已有文件。
- 路标补齐：确认没有其他 GitHub 写入器后，以同一群白名单运行 `--sync-github-index --apply`。它不重新下载，不重复保存 SMB 原件，只为 SMB 已完成且 GitHub 尚未完成的素材写入 `index_only` 路标，并在成功后将对应切片标为完成。
- 最终审计：以同一时间范围运行 `--audit --dry-run`。它重新读取 DWS 消息与话题回复，不下载素材，逐群输出 photo/video 的已完成时间范围和数量，以及未完成时间范围、数量、原因。DWS 分页或权限异常必须报告为未验证，不能报零。

## 报告与视频生成

报告每个群和切片的时间范围、发现数、SMB 原件数、GitHub 原件数、GitHub 路标数、跳过数、失败数、未完成边界及临时目录清理结果。

任何视频生成 Agent 必须先从 SMB 完整素材库读取全量可用素材，再自行挑选；GitHub 用于原件副本或 SMB 索引，不要求用户手工挑选素材。
