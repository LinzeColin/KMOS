# 发给本地 agent 的部署 prompt

把下面整段原样发给本机 agent。

---

你负责把 KMDY-RF 配方工坊部署到本机和 SMB，并跑通第一部片子的出片流程。

**输入**：Owner 给你的两组分卷：`KMDY-RF_全量包.zip.000…`（工坊全部代码、依赖库、字体、配乐、成片发送版、WIP）与 `KMDY-RF_成片母版.zip.000…`（INK-002 母版，可选）。

**硬规则**：
- 正式工作间不连 GitHub：不 clone、不 push、不 pull、不下载 GitHub 上的东西。全部在本机和 SMB 上完成。
- key 不写进任何文件，也不回显。
- 删除、覆盖已有产物、花钱、改共享区之前先问 Owner。SMB 上的已有目录只追加，不改别人的产物。
- 后台任务自己起的自己收，收工时不留任何后台进程。

**步骤**：
1. 合并分卷并解压到本机缓存目录，例如 `~/KMDY-RF_cache/`：`cat KMDY-RF_全量包.zip.* > 全量包.zip && unzip 全量包.zip`；母版同理 `cat KMDY-RF_成片母版.zip.* > 母版.zip && unzip 母版.zip`，把 mp4 放进 `KMDY-RF/成片/`。合并前核对分卷齐全（编号连续），`unzip -t` 无报错再继续。
2. 先读 `部署说明.md`，再读 `KMVideo/recipe_factory/LOCAL_SETUP.md` 全文。§5 的踩坑表是云端已经验证过的结论，照做，不用重新试错。
3. 运行 `bash KMVideo/recipe_factory/setup_local.sh`，按打印的 ✗ 补齐环境，直到打印「环境就绪」。
4. 按 LOCAL_SETUP.md §3 填 `KMVideo/recipe_factory/workspace.yaml`：`paths.root` 指向 SMB 上的 KMDY-RF 目录；六个空位按本机实际填，没有的留空；本机没有的能力改成 false。
5. 用 `rsync -a --inplace` 把整个目录同步到 `paths.root`，然后读回核对文件数和总大小一致。
6. 在 SMB 目录运行 `python3 factory.py status` 和 `python3 factory.py check`，应列出 10 份配方、0 处趋同。
7. 验证出片链路：按 LOCAL_SETUP.md §4 的第 1、3 步给 INK-002 出一张接触表（`--sheet=3,16,26,35,45,57`）。本机有显卡就不加 `--soft-gl`，并记下每帧实际耗时。用眼睛看接触表：水彩质感、字幕、Logo 都正常才算通过。
8. 把第 7 步的实测耗时和显卡情况追加进 `LOCAL_SETUP.md` §2，标注「本机实测 + 日期」。只追加，不删云端的记录。
9. 向 Owner 汇报四件事：做了什么、产出在哪、哪些通过哪些没通过、下一步。接触表路径单独列出来，请他看。

**完成标准**：`setup_local.sh` 打印「环境就绪」；`factory.py check` 显示 0 处趋同；INK-002 接触表人眼验收通过；SMB 上的目录与本机读回一致。

**之后派车道 agent**：按 `AGENT_PROMPTS.md` 给每条车道派一个 agent，每个 agent 用 `factory.py sample --lane <车道>` 领配方。开明小熊的片子走 INK 车道，引擎是 `KMBearAnimationBase/`。
