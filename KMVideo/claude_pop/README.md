# 窑宝咯噔了 · 开明高新 × Clawd 手绘卡点宣传片

仿照 Claude 官方 MV《I'm Upping My P(doom)》（参考片在 KMOS Release `ClaudeVideo`）的手绘水彩风格，
以 Claude 的吉祥物 Clawd 为主角，讲武汉开明高新“大型设备 · 在线修复”。

- 竖屏 1080×1920 · 24fps · 46 秒 · H.264 + AAC · 响度 -14 LUFS。适配抖音、X、Instagram Reels、Facebook Reels（竖屏在各平台都原生支持）。
- **一镜到底**：没有硬切，所有转场都是同一个镜头在同一个手绘世界里推、拉、甩、钻进气泡、升云、落回。
- 画面、配乐、音效全部由本目录代码生成：无第三方素材、无第三方音乐。字体均为 SIL OFL（可商用）。
- 分镜与事实来源：[STORYBOARD.md](STORYBOARD.md)。时间唯一来源：[cues.js](cues.js)（画面和 `music.py` 都读它，改一个时间两边一起动）。

## 出片

```bash
CHROME_PATH=/path/to/chromium KMVideo/claude_pop/build.sh out.mp4
```

步骤：下载并校验字体（`fonts/SOURCES.txt`）→ `npm ci`（ClaudeAnimationBase）→ 预渲染 4 块水彩天空底板 → 合成配乐 →
逐帧渲染（可断点续跑，`WORKERS` 控制并行页数）→ ffmpeg 合成。无 GPU 的云主机约 40–60 分钟。

检查某几个时刻（改完动画必做，先看再渲染全片）：

```bash
cd ClaudeAnimationBase
node render.mjs --soft-gl --page=../KMVideo/claude_pop/index.html --sheet=16.1,22.5,27.3 --cols=3 --w=300 --out=/tmp/check.jpg
```

也可以用 Chrome 直接打开 `index.html` 拖进度条预览（需 `--allow-file-access-from-files`）。

## 文件

| 文件 | 内容 |
|---|---|
| `cues.js` | 全片时间表：段落、事件时刻、字幕（中英）、音效清单 |
| `src/lib.js` | 字幕胶囊（逐字弹入、关键词高亮、随拍跳）、拟声大字、无状态粒子、水彩底板加载 |
| `src/cast.js` | 窑宝（回转窑端面 + 轮带 + 托轮 + 斜伸筒身）、厂长、开明高新木箱、车刀架、百分表、大齿圈、行业岛、噩梦 |
| `src/plates.js` | 4 块水彩天空底板（灰 / 金 / 蓝 / 噩梦紫） |
| `src/film.js` | 一镜到底的镜头路径与全部表演 |
| `music.py` | 原创配乐 + 59 个卡通音效（尤克里里、口哨主旋律、钢片琴、大号、铜管、鼓组；numpy 合成） |
| `build.sh` | 一键出片 |

引擎是仓库里的 [`ClaudeAnimationBase`](../../ClaudeAnimationBase)（p5.js + p5.brush）。本片给它加了几项向后兼容的开关：
`PROJECT.w/h`（竖屏）、`PROJECT.fastFill`（无 GPU 时把角色的水彩填充换成平涂，大面积水彩改走预渲染底板）、
`PROJECT.fonts`、`window.prepare`、`letterFn()`，以及 `render.mjs` 的 `--page` / `--frames-dir`。

## 发布前要人工确认的事

- 听一遍配乐与音效的平衡（代码只按电平表调过）。
- 片中说法“近万家企业”证据等级为中（见 STORYBOARD 事实表）；如有官方最新口径请替换 `cues.js` 与 `src/film.js` 的计数器文案。
- 片中“开明高新”字样为动画手写体，不是公司正式 logo。
