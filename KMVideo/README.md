# KMVideo

KMOS 视频生成流程的源码入口。

- 原始素材与运行状态仅保存在 `LinzeColin/Private-Database` 的
  `Private-KMDatabase/KMVideo/`。
- 本目录不提交图片、照片、视频、音频或生成产物。
- 群聊素材归档使用
  [`dingtalk-incremental-media-archive`](skills/dingtalk-incremental-media-archive/SKILL.md)。
  它以私有 GitHub 台账作为唯一去重依据：已归档素材绝不在后续运行中重复下载或上传。
