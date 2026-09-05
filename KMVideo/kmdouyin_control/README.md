# KMDouyin Control Plane

`kmdouyin-control` 是 KMDouyin 的本机运行控制器。它把既有的日运行单、项目任务卡和发布回执投影为一个可执行的日队列；业务事实、素材、审批、成片和平台数据仍保留在各自既有真源。

## 它负责的边界

- 读取 `RUN-*.yaml`、商业任务卡和作品级发布回执；
- 生成当前运行态、唯一工作项队列、发布观测索引和事件账；
- 创建结构化日运行单与跨角色交接包；
- 对商业任务卡生成 T30 前的生产门结果；
- 对作品级回执生成 24h / 7d 的真实数据采集状态；
- 只产生本机暂存输出。正式 KMDouyin 控制面资料由调用方使用 `rsync -a --inplace` 迁入 SMB，并在目标侧读回。

它不读取或改写原始素材，不改变项目/素材/审批真源，不触发 OpenChatCut、Remotion、DaVinci 或平台发布。T30 的 `KMVideo Factory` 继续是素材分析、候选规划和内部渲染的执行引擎。

## 日常入口

```bash
PYTHONPATH=KMVideo/kmdouyin_control \
python3 -m kmdouyin_control.cli project \
  --workspace /Volumes/share/03_资料库/KMDouyin \
  --run-root /Volumes/share/03_资料库/KMDouyin/00_治理与登记/04_运行记录/内容增长循环 \
  --release-root /Volumes/share/03_资料库/KMDouyin/03_复盘与洞察/发布后复盘 \
  --task-card /Volumes/share/03_资料库/KMDouyin/01_视频项目/06_真实表达实验/260826_齿形秩序/05_策略重设与重做/商业片任务卡_v3.yaml \
  --out-dir /Users/linzezhang/Movies/Hub/KMDouyinRuntime/control-plane/<run>
```

通过 `new-run` 生成运行单，通过 `handoff` 为 T10/T20/T30/T40 生成交接包，通过 `preflight` 和 `observe-release` 生成门结果与发布观测。

`catalog-components` 将项目内已经存在的字幕、旁白、3D、BGM 等表达资产登记为 `candidate_review_required`；在有适用任务、权利/审批范围和一次实际复用结果前，它们持续保持 `internal_review_only`。

`scripts/run_daily_control.sh` 是每天运行一次的入口。它先把全部结果写入本机唯一暂存目录，再用 `rsync -a --inplace` 更新 KMDouyin，并逐个读取目标文件。它只刷新状态和队列，不触发制作、发布或平台操作。

## 输出关系

```text
既有 RUN / 任务卡 / 发布回执
        │
        ▼
KMDouyin Control Plane
  ├── 运行总线当前态.yaml
  ├── 工作项队列.jsonl
  ├── 发布观测索引.jsonl
  ├── 运行事件.jsonl
  └── 日运行状态.md
        │
        ├── T10 公开市场研究
        ├── T20 商业事实与策略
        ├── T30 KMVideo Factory
        └── T40 发布回执与复盘
```

运行总线只保存状态和精确引用，不复制项目、素材、审批、研究或指标正文。
