# KMVideo

KMOS 视频生成流程的源码入口；本目录不保存任何原始素材。

仅由 DWS 实时确认是 INTERNAL_GROUP、且由用户明确授权的群聊图片、照片与视频才可归档。外部群、普通群、未知类型群和单聊一律不处理。

长期落点如下：

- GitHub：LinzeColin/Private-Database/Private-KMDatabase/KMVideo/
- SMB 外接硬盘：smb://192.168.0.1/share/03_资料库/MetaData/IDS_MetaData/KMVideo/

SMB 保存全部原始素材，媒体路径固定为：

    KMVideo/
      <群名称>/
        photo/<原始照片或图片>
        video/<原始视频>

每个群目录可有一个隐藏 .manifest.jsonl 文件。小于 GitHub 客户端 95 MiB 上限的原件同时保存到 GitHub；无法写入 GitHub 的原件必须保存至 SMB，并在 GitHub 的同群 .manifest.jsonl 留下 SMB 相对路径和原因作为索引路标。它不是额外素材目录。此 SMB 外接盘只能通过执行器的分块写入路径转存，禁止 macOS 快速复制路径；执行器把目录创建、写入及大小和有限头尾字节校验视为同一次受控尝试，任一步骤失败都会删除未验证目标、用新临时文件重试一次，仍失败则停止该条且不写完成状态。任何生成视频的 Agent 都必须先读取 SMB 完整素材库，再自行挑选素材，不要求用户手选。

运行期间允许使用独立本机临时目录下载和转存；每个文件完成 SMB 保存及 GitHub 原件或索引记录后立即删除，运行结束必须清空整个临时目录。采集范围只能是用户在当前线程批准的起点至冻结终点；本次任务为 2026-01-01 起。以连续、不重叠、每段最多 30 天的切片从旧到新推进，单段未完成不得前进。同一群只允许一个归档写入器，避免覆盖群级清单。

群聊素材归档规则见 [dingtalk-incremental-media-archive](skills/dingtalk-incremental-media-archive/SKILL.md)。
