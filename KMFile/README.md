# KMFile

KMOS 文件（文档）归档流程的源码入口；本目录不保存任何原始文件。

仅由 DWS 实时确认是 INTERNAL_GROUP、或已列入 `AUTHORIZED_NON_INTERNAL_TITLES` 且由用户明确授权的群聊文件才可归档。外部群、普通群、未知类型群和单聊一律不处理。

长期落点如下：

- GitHub：LinzeColin/Private-Database/Private-KMDatabase/KMFile/
- SMB 外接硬盘：smb://192.168.0.1/share/03_资料库/MetaData/IDS_MetaData/KMFile/

SMB 保存全部原始文件，路径固定为：

    KMFile/
      文件登记表.csv
      原名新名映射.csv          ← 改名账本，「现用名」的唯一权威
      待转KMVideo.csv           ← 以文件形式发送的音视频交接清单
      <群名称>/
        file/<原始文档>
        .manifest.jsonl         ← 禁止修改

## 与 KMVideo 的分流规则

钉钉里同一份内容可能走两种传输：

| 消息体 | 下载命令 | 归属 |
| --- | --- | --- |
| `[图片消息](mediaId=...)` / `[视频消息](mediaId=...)` | `dws chat message download-media --type mediaId` | KMVideo |
| `[文件] xxx.mp4 fileId: ...`（音视频/图片扩展名） | `dws drive download --node <fileId>` | KMVideo（KMMedia-Archive v0.2.1 起） |
| `[文件] xxx.xlsx fileId: ...`（文档扩展名） | `dws drive download --node <fileId>` | **KMFile** |

按扩展名分流，不重不漏。KMFile 侧遇到音视频只写 `handoff_av` 记录并导出 `待转KMVideo.csv`，绝不落地。

## 完整性校验

`dws drive info --node <fileId>` 直接返回服务端 `md5`（`base64(MD5 digest)`）与 `fileSize`，
因此本目录的落地件校验是三层：**字节数 + 头尾抽样 + 服务端 md5 逐份复核**。
存在性判定只读 `drive info`，**不整包下载**（云成本红线）。

## SMB 写入约束

此 SMB 外接盘只能通过 `rsync --inplace --whole-file` 或 `dd conv=fsync` 直接写入路径转存，
禁止 macOS 快速复制、Python SMB 直写和 SMB `os.replace` 发布路径 —— 该挂载的 rename 实测会随机返回 EIO，
写后 `stat` 也会短暂返回旧尺寸，所以校验失败必须先沉降再重试，连续三轮不符才认失败。

## 命名规则

与 KMVideo 共用同一套，不另立门户：

**文件名格式：`{业务}_{说明}_{YYMMDD}_{序号}.ext`**

- 说明 2–6 字，由文件名 / 消息上下文 / 抽取正文三路关键词判定；泛化词一律拒绝
- 抽不出说明就填「待确认」并**保留原文件名**，进待办清单等人工终审
- 业务映射表见 `KMVideo/README.md`，两库共用

改名成功的瞬间即写入 `原名新名映射.csv` 账本。`.manifest.jsonl` 永远记原名（禁止改写），
所以归档器判断「这份是否已落地」必须回查账本 —— 不回查就会把已改名的文件当缺失重下，
重下回来的原名又被再改一次，滚出 `_01/_02/_03` 一串重复件。

## 运行

归档规则与流水线见 [KMFile-Archive](skills/KMFile-Archive/SKILL.md)。

运行期间允许使用独立本机临时目录下载和转存；每个文件完成 SMB 保存后立即删除，运行结束必须清空整个临时目录。
采集范围只能是用户在当前线程批准的起点至冻结终点；首轮为 2025-01-01 起，按连续、不重叠、每段最多 30 天的切片从旧到新推进，单段未完成不得前进。
同一群只允许一个归档写入器。每次 DWS 调用显式使用 60 秒上限；网络超时属于未完成并停止当前窗口，不能伪称成功。
