# KMVideo

KMOS 视频生成流程的源码入口；本目录不保存任何原始素材。

所有群聊图片、照片与视频有且只有两个长期落点：

- GitHub：`LinzeColin/Private-Database/Private-KMDatabase/KMVideo/`
- SMB 外接硬盘：`smb://192.168.0.1/share/03_资料库/MetaData/IDS_MetaData/KMVideo/`

两处目录完全同构，媒体路径固定为：

```text
KMVideo/
  <群名称>/
    photo/<原始照片或图片>
    video/<原始视频>
```

每个群目录可有一个隐藏的 `.manifest.jsonl` 文件，并在 GitHub 与 SMB 的对应群目录各保留一份相同内容，记录每条钉钉素材在两端是否已成功保存；它不是额外素材目录。任何生成视频的 Agent 都必须先读取完整素材库，再自行挑选素材，不要求用户手选。

运行期间允许使用独立本机临时目录下载和转存；每个文件完成双写或记录失败后立即删除，运行结束必须清空整个临时目录。采集以连续、不重叠的 30 天历史切片推进，单段未完成不得前进。

群聊素材归档规则见 [`dingtalk-incremental-media-archive`](skills/dingtalk-incremental-media-archive/SKILL.md)。
