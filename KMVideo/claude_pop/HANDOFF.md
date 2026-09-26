# 交接手册 · 《窑宝咯噔了》（KMVideo/claude_pop）

给接手的人或本地 agent：**先读完本页再动手**。这里记的每一条坑都真实踩过、花过时间。
数字均为 2026-09-26 在云端容器实测（4 核 CPU、15GB 内存、无显卡）。

## 0. 东西在哪

| 要什么 | 在哪 |
|---|---|
| 源码、脚本、分镜、事实来源 | 本目录（git 分支 `claude/great-newton-g4w5mw`，合并后在 `main`） |
| 成片、配乐分轨、字体/底板/依赖离线包、审片对比图、源码快照 | **交付包** `KM_claude_pop_bundle.tar`（云端会话里以 `.part-aa…` 分片发给了 Owner，拼接方法见 §7）；可选再传成 GitHub Release `KMVideo-claude-pop-v1` |
| 逐帧图 1104 张 | 不单独存：母版 `KM_claude_pop.mp4` 是 crf17 肉眼无损，`fetch_release.sh build` 会自动从母版拆回 `out/frames/` |
| 参考片（Claude 官方 MV 原片） | GitHub Release `ClaudeVideo`，sha256 `141f4f2e14c7923821eda9f87ae824ebea32fadd7c56c3d56b523a0ef4a0b7f5` |

## 1. 三种接手方式（按省事程度排）

```bash
# 先把交付包拼好解开（§7），得到 KM_claude_pop_bundle/ 文件夹；下面的 SRC 指向它（有 Release 时可以不设 SRC，直接下载）
# A. 只要成片：校验后四个文件落到 out/
SRC=~/Downloads/KM_claude_pop_bundle KMVideo/claude_pop/fetch_release.sh video

# B. 要改字幕 / 配乐 / 片尾文案：先拿回全部中间物（逐帧图 1104 张、字体、底板、依赖），再按需重渲
SRC=~/Downloads/KM_claude_pop_bundle KMVideo/claude_pop/fetch_release.sh build
#   改配乐（music.py / cues.js 的 sfx）：不用重渲任何帧，直接跑 build.sh（帧齐全时实测 6 分 52 秒出四件成品）
#   改某段画面（src/*.js 或 cues.js 字幕）：先删掉那段的旧帧，再跑 build.sh，只补删掉的帧
KMVideo/claude_pop/tools/invalidate.sh 20.5 24          # 删 20.5–24 秒的帧（帧号 = round(秒×24)）
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" GL= KMVideo/claude_pop/build.sh

# C. 从零重建（不用交付包）：build.sh 自己下字体、npm ci、画底板、合成配乐、渲全片
CHROME_PATH=<chrome> KMVideo/claude_pop/build.sh      # 无显卡约 1.5–3 小时；有显卡用 GL= 会快很多（未实测）
```

`build.sh` 结尾自动跑 `verify.sh`（规格 / 帧数 / 响度 / 真峰值 / 16 秒卡点），不合格退出码 1。

**改完画面，出片前必须人眼看**：用抽帧对比图（不要只信 verify.sh，它只查机器参数）：

```bash
cd ClaudeAnimationBase
node render.mjs --soft-gl --page=../KMVideo/claude_pop/index.html --sheet=16.1,22.5,27.3 --cols=3 --w=300 --out=/tmp/check.jpg
```

## 2. 环境（实测版本）

| 组件 | 版本 | 备注 |
|---|---|---|
| Node.js | 22.22.2 | `render.mjs` 是 ESM |
| p5 / p5.brush / puppeteer-core | 2.3.3 / 2.2.3 / 25.11.0 | `ClaudeAnimationBase/package-lock.json` 锁定；交付包里有 `node_modules.tar.gz`（纯 JS，跨平台） |
| Chromium | 141.0.7390.37（Playwright 1194） | 本机 Chrome 也行。容器路径 `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` |
| ffmpeg | 7.0.2 静态版 | 容器里没有 ffprobe；`verify.sh` 只用 ffmpeg |
| Python / numpy / scipy | 3.11 / 2.4.6 / 1.17.1 | `music.py` 用 |
| 字体 | 4 款 SIL OFL / Apache | `fonts/SOURCES.txt` 有来源与 sha256；交付包 `build_env.zip` 里有现成文件（含字体许可证） |

## 3. 工作流（这片是怎么做出来的）

1. **时间唯一来源 `cues.js`**：段落、事件时刻、字幕、59 个音效都在这里。画面（`src/film.js`）和配乐（`music.py`）都读它，
   改一个时间两边一起动，卡点就不会漂。120 BPM，1 拍 = 0.5 秒 = 12 帧。
2. **每帧是时间 t 的纯函数**：帧会被多个页面并行、乱序渲染。任何“上一帧的状态”都不许存；粒子、彩纸都是按 t 现算的。
3. **一镜到底**：`film.js` 的 `CAMK` 是镜头关键帧（位置 + 缩放，缩放按对数插值），外加甩镜旋转和撞击震屏。转场只能是
   推、拉、甩、钻气泡、升云、落回，不许硬切。
4. **先看后渲**：改动 → 抽 3–6 个时刻出对比图 → 人眼看 → 删掉相关帧 → build.sh 补帧 → verify.sh → 再抽帧看成片。
5. **配乐**：`music.py` 用 numpy 合成（尤克里里 Karplus-Strong、口哨、钢片琴、大号、铜管、鼓、59 个音效），同样输入 → 逐字节
   相同输出。响度按 BS.1770 归一到 -14 LUFS、真峰值 ≤ -1.3 dBTP。15.75–16.0 秒是**精确静音**（爆点前的留白）。
   调平衡用 `python3 music.py out/bgm.wav --stems out/stems && python3 tools/mix_report.py out/bgm.wav out/stems`。

## 4. 踩坑记录（症状 → 根因 → 做法）

| # | 症状 | 根因 | 做法 |
|---|---|---|---|
| 1 | YouTube 打不开（429） | 云主机 IP 被 YouTube 限流 | 用 Release `ClaudeVideo` 里的原片，别再去 YouTube 试 |
| 2 | 官网 whkm.cn 打不开；抖音 @WHKM2020 看不到视频；鄂州政府网被拦 | 容器 DNS 解析不到 whkm.cn；抖音网页要登录 + 动态加载；代理策略拦截 | 事实来自搜索引擎摘要 + `KMVideo` 施工素材登记表，按证据分级（见 STORYBOARD 事实表）。**本地有浏览器的话，建议人工补看抖音号** |
| 3 | 无头 Chrome 加载 Google Fonts 报证书错误 | 云端代理重签 TLS，Chrome 不认 | 字体全部本地化（`index.html` 里 `@font-face` 指向 `fonts/`），`build.sh` 按 sha256 校验 |
| 4 | 一帧 40 秒，全片要十几小时 | p5.brush 的水彩 `fill` 在软件 WebGL 下极慢（基准测试里带 fill 的页面 30 秒都没画完；单次 2–9 秒） | `PROJECT.fastFill`：角色的 fill 改成平涂 wash；大面积水彩天空预渲染成 4 张“底板”jpg，每帧直接贴图 |
| 5 | 第一帧奇慢，误以为整体很慢 | 每种笔刷第一次用要编译着色器（几十秒，一次性） | 测速看第 24 帧以后的“有效速度”（实测 5.0–10.7 秒/帧，3 页并行） |
| 6 | puppeteer `Navigation timeout of 30000 ms exceeded` | 首次加载 + 着色器编译超过默认 30 秒 | `render.mjs` 已把 goto/waitForFunction 超时设为 0 |
| 7 | 两个浏览器同时出对比图，其中一个失败 | 4 核被抢满 | 对比图一张一张出；全片渲染 `WORKERS=3` |
| 8 | 渲染到一半容器重启，进程没了 | 云容器会回收/杀后台进程 | 渲染可续跑（只补缺的帧，写帧是原子改名）。改了画面记得先 `tools/invalidate.sh` 删旧帧，否则旧帧会被当成“已完成” |
| 9 | 日志里刷屏 `WebGL: INVALID_OPERATION: uniform… location is not from the associated program` | p5.brush 内部的无害告警 | 忽略；看 `frame N/M` 行 |
| 10 | render.mjs 找不到 Chromium | 它只自动找 `~/.cache/ms-playwright/chromium-*/chrome-linux64`，容器里是 `/opt/pw-browsers/…/chrome-linux` | 设 `CHROME_PATH` |
| 11 | ffprobe 不存在 | 容器只有 pip 装的 imageio-ffmpeg | `ln -s $(python3 -c 'import imageio_ffmpeg as m;print(m.get_ffmpeg_exe())') /usr/local/bin/ffmpeg`；检查用 `ffmpeg -i` |
| 12 | 71MB 的平台版发不到聊天窗口 | 发送上限 30MiB | `build.sh` 另出 `_share.mp4`（两遍编码 4.9Mbps ≈ 28MB，SSIM 0.91，肉眼无明显损失） |
| 13 | 字幕 / 拟声字被抖音 UI 挡住 | 抖音底部约 350px 是文案区、右侧是点赞栏、顶部有状态栏 | 动作放 y 150–1300，字幕胶囊中心 y=1470；片尾卡整体下移 + 镜头拉远到 0.88 |
| 14 | 并行渲染出现“上一帧残留” | 在帧之间存了状态 | 所有东西写成 t 的纯函数（`lib.js` 的 `sparks`/`confetti` 是范例） |
| 15 | 云端 agent 用 API 建公开 Release 被拦（auto mode 安全审查拒绝，未给理由） | 往公开仓库发布属于对外发布，需 Owner 自己决定 | 改为分片交付包直接发给 Owner；要上 Release 由 Owner 本地执行 §7 的命令 |
| 16 | 逐帧图 900MB，分片发送要 31 片 | 逐帧图和 crf17 母版信息几乎等价 | 交付包不带逐帧图；`fetch_release.sh build` 从母版拆帧（`-start_number 0 -q:v 2`，正好 1104 张） |

**人眼复核抓出、机器检查抓不出的问题**（改画面时要照着再检查一遍）：窑宝正面看像一只钟 → 加斜伸的筒身才像回转窑；
厂长站太靠右被点赞栏挡；岛屿灰扑扑 → 提饱和度；噩梦底板太淡 → 提对比度重画；气泡里地面是矩形 → 改椭圆；日历压住百分表；
“咯噔!”字压住百分表；车削和齿圈两个镜头看不懂 → 重新设计机位 + 放大车屑 + 红色虚线提示圈 + 发红的新齿；
16 秒爆点不够炸 → Clawd 放大、镜头停顿；云朵丑 → 改“多个圆的并集”轮廓；“嗝~”压在脸上；开头/结尾的“咯噔!”落在底部遮挡区。

## 5. 关键决策与理由

| 决策 | 理由 | 想改怎么办 |
|---|---|---|
| 竖屏 9:16 | 抖音 / IG Reels / FB Reels / X 都原生支持竖屏 | 横屏要改 `config.js` 的 w/h、重排镜头与字幕位置，并全片重渲 |
| 配乐原创合成，不下载 BGM | 商用发布零版权风险 | 换成授权音乐：替换 `out/bgm.wav` 后跑 build.sh（不用重渲帧），注意卡点在 `cues.js` 的 120 BPM 网格上 |
| “近万家企业”而不是“18 国 / 30 省” | 前者有政府网报道（证据中），后者没核实到 | 拿到官方口径后改 `cues.js` 字幕与 `src/film.js` 计数器 |
| “开明高新”用手写体 | 没有拿到官方 logo 矢量文件 | 有 logo 后替换片尾卡（`film.js` 的 `endCard`） |
| 修改 `ClaudeAnimationBase`（竖屏、fastFill、fonts、prepare、letterFn、--page、--frames-dir） | 全部向后兼容；原 demo 重渲后画面不变（已人眼对比） | — |

## 6. 验收状态

机器检查：`verify.sh` 对母版 / 平台版 / 分享版全部合格（1080×1920、24fps、46.00s、1104 帧、-14.1 LUFS、-1.2 dBTP、
15.80–15.97s 静音、16.00s 炸开）。画面：云端 agent 逐段看过缩略图与关键帧。

**还没人做、需要人来做的**：①戴耳机 + 手机外放各听一遍（音效大小、低音是否太弱），agent 听不了；
②确认“近万家企业”的口径；③确认手写“开明高新”字样可以用；④人工看一遍 @WHKM2020 抖音号，判断风格是否需要贴近。

## 7. 交付包（= Release 附件）清单

拼接与解包（分片是 `split -b 29m` 切的，按文件名顺序拼回即可）：

```bash
cat KM_claude_pop_bundle.tar.part-* > KM_claude_pop_bundle.tar && tar -xf KM_claude_pop_bundle.tar   # Mac / Linux
#   Windows（cmd）：copy /b KM_claude_pop_bundle.tar.part-* KM_claude_pop_bundle.tar  然后  tar -xf KM_claude_pop_bundle.tar
cd KM_claude_pop_bundle && shasum -a 256 -c SHA256SUMS.txt                                             # 全部 OK 才算完整
```

想让它长期可下载（**KMOS 是公开仓库，传上去等于公开**，由 Owner 决定）：

```bash
gh release create KMVideo-claude-pop-v1 KM_claude_pop_bundle/* --repo LinzeColin/KMOS --target claude/great-newton-g4w5mw \
  --title "KMVideo · 窑宝咯噔了 v1" --notes "见 KMVideo/claude_pop/HANDOFF.md"
```

| 附件 | 内容 | 用途 |
|---|---|---|
| `KM_claude_pop.mp4` | 母版，crf17，约 31Mbps | 存档 / 再剪辑 |
| `KM_claude_pop_web.mp4` | 平台版，≤12Mbps | 上传抖音 / X / IG / FB |
| `KM_claude_pop_share.mp4` | 分享版 ≈28MB | 发微信 / 聊天软件 |
| `KM_claude_pop_cover.jpg` | 封面（片尾卡，43.6s） | 平台封面 |
| `bgm.wav` / `stems.zip` | 混音成品 / 6 条分轨（鼓、贝斯、键盘、主旋律、混响、音效） | 重混、给剪辑师 |
| `build_env.zip` | 字体 4 款 + 水彩底板 4 张 | 离线构建 |
| `node_modules.tar.gz` | ClaudeAnimationBase 依赖 | 离线构建（`npm ci` 慢或不通时） |
| `review_sheets.zip` | 审片对比图、参考片分镜抽帧、频谱图、性能测试图 | 了解改过什么、为什么改 |
| `source_snapshot.zip` | 本目录 + ClaudeAnimationBase 源码快照 | 不想 clone 仓库时用 |
