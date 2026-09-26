# KMDY-RF 本机部署与踩坑手册

写给 0 上下文的本地 agent。按顺序做完 §1–§4，工坊即可出片。§5 是云端已踩过的坑，照做就不用再试错。
云端搭建日期 2026-09-26；本文所有耗时都是云端（4 核、无显卡）实测，有显卡的 Mac 会快很多，以本机重测为准。

## 1. 目录与来源

部署包 `KMDY-RF_全量包` 解压后是一个 `KMDY-RF/` 目录，结构与 KMOS 仓库一致：

| 目录 | 作用 |
|---|---|
| `KMVideo/recipe_factory/` | 工坊本体：`factors.yaml` 因子库、`lanes.yaml` 车道、`recipes/` 配方库、`GATES.md` 质量闸门、`AGENT_PROMPTS.md` 车道 agent 提示词、`engines/` 引擎模板、`refs/` 创作基准、`factory.py` 抽样与查重 |
| `KMVideo/promo_30s/` | R001「窑宝的烦恼」工程（TOON 车道，Canvas2D + Playwright 渲染） |
| `KMVideo/kmbid_explainer/` | INK-002「KMBID 搜标讲解片」工程（INK 车道，KMBearAnimationBase） |
| `KMBearAnimationBase/` | 开明小熊 + Clawd 手绘动画底座（INK 车道引擎） |
| `ClaudeAnimationBase/` | Clawd 手绘动画底座（原版 + 平涂模式、分辨率参数、本地字体） |
| `ClaudeVideo/` | PDoomVideo 长片源码，分章并行的参考（`README_KM.md`） |
| `成片/` | R001 成片、INK-002 发送版与母版 |
| `WIP/` | 云端的接触表、校验截图、临时脚本，只作参考 |

正式工作间不连 GitHub：整个目录复制到 `workspace.yaml` 的 `paths.root`（SMB）后，只在本机与 SMB 上推进。

## 2. 环境

| 组件 | 云端实测版本 | 用途 |
|---|---|---|
| Node.js | 22.22 | 两套动画底座的渲染器 `render.mjs`（puppeteer-core） |
| Python | 3.11+，numpy 2.x、scipy 1.17、pyyaml | 配乐合成 `music.py`、`factory.py`、TOON 渲染 |
| Chrome / Chromium | Chromium 1194（Playwright 版） | 逐帧渲染；本机装的 Google Chrome 即可 |
| ffmpeg | 7.0 | 合成 mp4、响度标准化 |
| Playwright（Python） | 任意近期版本 | 只有 `promo_30s/render.py` 与 `engines/capture.py` 用 |

一键检查与安装：`bash KMVideo/recipe_factory/setup_local.sh`（只装依赖、不改系统设置；缺什么打印什么）。

浏览器路径：`render.mjs` 依次找 `--chrome=`、`CHROME_PATH`、Mac 的 `/Applications/Google Chrome.app/...`、`~/.cache/ms-playwright/chromium-*`。
找不到就 `export CHROME_PATH=<chrome 可执行文件>`。

## 3. 填配置

只改 `KMVideo/recipe_factory/workspace.yaml`：
1. `paths.root` 改成本机实际的 SMB 挂载路径（Mac 通常是 `/Volumes/share/...`）。
2. 标「空位」的六项（素材登记表、公司原件、字体、曲库、TTS、Remotion 工程）按本机填；没有就留空。
3. `capabilities` 里本机没有的能力改成 `false`，对应取值就不会被抽到。
4. 验证：`cd KMVideo/recipe_factory && python3 factory.py status && python3 factory.py check`，应列出 10 份配方、0 处趋同。

## 4. 出片流程（INK 车道，以 INK-002 为例）

```bash
cd KMVideo/kmbid_explainer && mkdir -p out && python3 music.py out/bgm.wav        # 1. 配乐，约 10 秒
cd ../../KMBearAnimationBase && npm install                                     # 2. 首次装依赖
# 3. 抽帧目检（先看 5–6 张，确认构图再全量）
node render.mjs --page=../KMVideo/kmbid_explainer/studio.html --sheet=3,16,26,35,45,57 --out=out/check.jpg
# 4. 全量出帧：有显卡用原版水彩；没显卡加 --soft-gl --density=0.6667
node render.mjs --page=../KMVideo/kmbid_explainer/studio.html --frames --workers=1
# 5. 合成（音频取 config.js 里的 audio）
node render.mjs --page=../KMVideo/kmbid_explainer/studio.html --encode --out=out/INK-002.mp4
# 6. 响度 -14 LUFS，并出一份便于微信/钉钉发送的小体积版
ffmpeg -i out/INK-002.mp4 -c:v copy -af loudnorm=I=-14:TP=-1:LRA=11 -c:a aac -b:a 256k out/INK-002_final.mp4
ffmpeg -i out/INK-002_final.mp4 -c:v libx264 -b:v 3200k -maxrate 4000k -bufsize 8000k -c:a copy out/INK-002_发送版.mp4
```

中断后续跑：重跑同一条 `--frames` 命令，已写出的 `out/frames/fNNNNN.jpg` 自动跳过；`--range=起始秒:结束秒` 只渲染一段；最后统一 `--encode`。有显卡时 `--workers=4`。
新片照 `kmbid_explainer/` 的结构：`STORYBOARD.md`（先写分镜与秒点表）→ `config.js` → 场景 js → `studio.html`（引用底座的 `src/`）→ `music.py`（与分镜同一张秒点表）。
45 秒以上的片子按 `AGENT_PROMPTS.md` 的长片分章法拆章，参考 `ClaudeVideo/`。

TOON 车道（R001）：`cd KMVideo/promo_30s && python3 music.py /tmp/bgm.wav && python3 render.py out.mp4 --audio /tmp/bgm.wav`，字体放 `fonts/`（包里已带）。

## 5. 已踩过的坑（照结论做）

| # | 现象 | 根因 | 做法 |
|---|---|---|---|
| 1 | 无显卡机器上每帧 40 秒以上 | p5.brush 水彩填充在软件 WebGL（SwiftShader）里极慢 | `--soft-gl` 自动启用平涂；再加 `--density=0.6667`，每帧约 1.7 秒（1080p），62 秒片约 45 分钟 |
| 2 | 抽帧表打印的「每帧几十毫秒」和实际总耗时对不上 | 打印的只是排队绘制命令的时间，GPU 真正干活发生在读回像素那一步 | 估算工期用总耗时 ÷ 帧数，不用单帧打印值 |
| 3 | `--workers=4` 不比 1 快，甚至超时 | SwiftShader 已经吃满所有核；后台标签页里 `img.decode()` 会挂起 | 无显卡时 1 个 worker；图片用 onload 等待（底座已改好） |
| 4 | `--flat` 不加 `--soft-gl` 报 `Error creating webgl context` | 无显卡机器必须显式要软件 WebGL | 无显卡一律带 `--soft-gl`；有显卡的 Mac 两个都不加 |
| 5 | 字体变成默认字体 | 云端连 Google Fonts 证书失败 | 字体已放进 `assets/fonts/`，`studio.html` 用本地 @font-face；新页面照抄 |
| 6 | 渲染到某一帧报 `spline()` 错误崩溃 | 只有 1 个点的折线交给 spline | 画线前判断点数 ≥ 2；修好后重跑 `--frames`，已出的帧自动跳过 |
| 7 | 镜头推拉时画面边缘露出空白 | 背景矩形只画到画面大小，镜头缩放后露边 | 背景矩形画大到 `-1400..W+2800` |
| 8 | 小熊翻转后口袋字变成「MK」 | `flip` 镜像了整个角色 | kmbear.js 已在翻转时把字单独反镜像；自己加文字道具时同样处理 |
| 9 | `pkill -f node` 把自己的 shell 也杀了 | `-f` 匹配到了包含关键词的命令行本身 | 用 `pkill -f '[n]ode render'` 这种方括号写法 |
| 10 | 打包时中文文件名的文件没进包 | `git ls-files` 默认把中文路径加引号 | `git ls-files -z | tar --null -T -` |
| 11 | 母版 110MB，发不出去 | 手绘纸纹很吃码率 | 母版存档，另出 3.2Mbps 发送版（约 26MB） |
| 12 | 小熊描边太粗、口袋字看不清、侧面鼻子成一团 | 线宽随尺寸线性放大 | 线宽已限幅 `clamp(u/15,.45,2.4)*.62`；侧面口鼻画在头下层。改造型后先出 `LOOPS.bear_views` 接触表人眼看 |

## 6. 验收与登记

- 每部片子按 `GATES.md` 过闸：四道多样性闸门由 `factory.py check` 机检，品牌三线与画面质量人眼看接触表。
- 成片登记：配方 yaml 的 `status` 改 `rendered`，`qc` 填自检；事件写 `paths.ledger`（只追加）。
- 成片、帧、wav 不进任何代码仓；长期数据按 KMOS `AGENTS.md` 的数据落地规则走私有库。
