# 配方工厂：固定一部分根本因素、改变另一部分，批量量产不雷同的短视频

一部短视频 = 一份**配方**（15 个因子各取一个值）。批量量产时，调度者**固定**本批要统一的因子
（如业务方向、时长），其余因子由 `factory.py` 抽取，并用三道闸保证每部片子彼此不同；
每份配方交给一条 Opus agent 流水线（编剧 → 制作 → 质检）独立做完。

```
factors.yaml ──► factory.py sample ──► recipes/R00x.yaml ──► 编剧 agent ──► 制作 agent ──► 质检 agent ──► Owner 人眼验收
   因子库          固定 + 抽取 + 去同质化        配方            分镜+四要素自评     按引擎出片       规格/事实/合规      发布
                                                   ▲                                                         │
                                                   └──────── 发布后 24h/7d 数据写回配方，调整因子权重 ◄──────────┘
```

## 1. 三层因素

| 层 | 含义 | 因子（详见 factors.yaml） |
|---|---|---|
| **L0 根本因素** | 换一个值，整部片子就是另一部片子 | 价值主打（精选四要素）、叙事母型、视角与主角、媒介与画风、业务入口、情绪弧 |
| **L1 结构因素** | 还是那部片子，但节奏、观感、传播方式明显不同 | 开头钩子、镜头语言、音乐风格、人声策略、时长、字幕策略 |
| **L2 表层因素** | 同一部片子的皮肤，用于同配方 A/B | 色彩、转场主招、结尾引导 |

**去同质化靠 L0**：两部片子 L0 至少 3 项不同，才算两部片子。只改 L1/L2 得到的是同一部片子的变体
（例如 R001 去掉水印、改文案、换 logo，都属于 L2）。

**批量量产靠"固定 + 抽取"**：
- 按方向量产：`--fix business=tyre` → 6 部都讲轮带，但叙事、主角、画风、情绪全不同
- 按系列量产：`--fix medium=watercolor --fix protagonist=machine` → 同一画风同一 IP 的系列剧，每集叙事与业务不同
- 按平台量产：`--fix duration=s15 --fix text_policy=bilingual_kinetic` → 海外短版

## 2. 可以换的画风（媒介与画风因子）

| 画风 | 引擎 | 适合 | 现状 |
|---|---|---|---|
| 扁平矢量卡通 | Canvas2D | 拟人、喜剧、快节奏卡点 | **已跑通**：R001 / `KMVideo/promo_30s` |
| 手绘水彩、线条抖动 | p5.brush | 温情、感染力、慢叙事 | **引擎在库**：`ClaudeAnimationBase/`（默认无字规则，可按配方放开） |
| 国潮水墨 | p5.brush | 匠心、传承、师徒 | 复用 ClaudeAnimationBase 笔刷 |
| 低多边形 3D / 写实金属 3D | three.js | 设备结构、环绕展示 | 需要搭建；无 GPU 时用 SwiftShader 软渲染，慢但可行 |
| X 光 / 剖视 | three.js | 获得感：看穿设备内部为什么坏 | 同上 |
| 赛博霓虹 | three.js | 惊喜感、年轻受众 | 同上 |
| 工程蓝图线稿 | SVG + GSAP | 精度、测量、原理讲解 | 需要搭建 |
| 纯文字排版动效 | SVG + GSAP | 清单揭秘、反常识问句 | 需要搭建 |
| 数据可视化叙事 | SVG + GSAP / D3 | 规模、效率对比 | 需要搭建 |
| 3Blue1Brown 式几何讲解 | manim | 齿形、同轴度、偏摆的原理 | 需要搭建 |
| 黑板粉笔 / 像素游戏 / 剪纸拼贴 | Canvas2D | 科普、闯关、手作感 | 复用 promo_30s 的渲染管线 |
| 实拍素材 + 动态包装 | ffmpeg（+ Canvas 叠层） | 真实感、可信度最高 | 需要 NAS 素材库可读（`requires: footage`） |

## 3. 固定层（所有配方共用，任何 agent 都按此执行）

- **品牌三线**（来自故事型广告创作基准 S1）：同一组剧情事件同时推进 ① 观众的判断与情绪 ② 人物对服务的需求与服务的作用 ③ 观众对开明的认识。技术服务在故事里承担关键因果作用。
- **精选四要素全部及格**：获得感（学到判断/方法）、惊喜感（选题或形式新）、表达力（清晰生动、印象深）、感染力（真诚、引发共鸣）。`value_core` 指定的那一项做到最强，自评 ≥4/5。
- **事实**：品牌能力、技术效果、项目与数字只用有出处的资料（宣传册、官网、素材登记表、项目资料）；人物、对白、情节可以艺术化创作。每部片子的事实逐条写进配方 `facts`。
- **合规**：广告性质清楚标识；AI 生成内容按《人工智能生成合成内容标识办法》第 10 条主动声明并使用平台标识功能；服务效果与实际可实现条件对应（广告法第 8、14、28 条）。
- **技术规格**：1080×1920 竖屏、30fps、H.264 High + AAC、-14 LUFS；平台 UI 安全区（顶部 250px、底部 350px、右侧 150px）；先接触表自查再全量渲染；成片与字体不入仓。
- **声音版权**：原创合成（numpy，参照 `promo_30s/music.py`）或已核实商用授权的曲库；授权信息写进配方。

## 4. 引擎表：制作 agent 要用的技术与工具

| engine | 技术栈 | 许可 | 说明 |
|---|---|---|---|
| canvas2d | HTML Canvas + Playwright/Chromium 逐帧 `renderAt(t)` → PNG 流 → ffmpeg | 自有代码 | R001 实测 900 帧约 2.5 分钟（无 GPU） |
| p5brush | p5.js + p5.brush + puppeteer（`ClaudeAnimationBase/render.mjs`） | MIT / LGPL | 水彩填充在无 GPU 时每帧数秒，可改用平涂 |
| threejs | three.js + 同一套逐帧捕获；`preserveDrawingBuffer: true` | MIT | 无 GPU 用 `--use-angle=swiftshader` |
| svg_gsap | SVG + GSAP 时间线 `tl.seek(t)` 逐帧 | GSAP 标准许可（发布前核对条款） | 适合排版与线稿 |
| manim | Manim Community | MIT | Python 原生，直接出 mp4 |
| ffmpeg_footage | ffmpeg 剪辑 + Canvas 生成透明叠层（字幕/贴纸/标注） | LGPL/GPL 工具，产物不受限 | 素材读自 NAS，按 KMVideo 素材登记表选片 |
| 音乐/音效 | numpy + scipy 合成；ffmpeg `loudnorm` | 自有 | 需要人声时 TTS 走外包顺序并先查 public-apis 选型 |

Remotion 也能做，但公司使用需购买公司许可，列为备选。

## 5. 多 agent 流水线怎么搭

| 站 | agent | 输入 → 输出 | 提示词 |
|---|---|---|---|
| 0 | 调度 | 本批目标 → N 份配方（`factory.py sample` + `check` 0 趋同） | AGENT_PROMPTS.md · D |
| 1 | 编剧 ×N（并行） | 配方 → 分镜、四要素自评、facts | A |
| 2 | 制作 ×N（并行，每个独立 worktree） | 分镜 → 代码 + 成片 | B |
| 3 | 质检 | 成片 → pass / return | C |
| 4 | Owner | 人眼验收 → 发布 | — |

每个 agent 只读配方与本 README，零上下文可接手；配方 `status` 字段（draft → storyboarded → rendered → qc_pass → published）就是全局进度表。

## 6. 复盘回路

发布后把 24h / 7d 数据（完播率、互动率、搜索账号数）写进配方 `metrics`。
按因子取值汇总表现，表现好的取值提高抽样权重，差的降低，但任何取值都保留非零概率，保证持续出新。

## 7. 命令

```bash
cd KMVideo/recipe_factory
python3 factory.py sample --n 6 --fix business=tyre --fix duration=s30   # 抽 6 份并写入 recipes/
python3 factory.py sample --n 4 --fix medium=watercolor --dry            # 只看不写
python3 factory.py check                                                 # 全库趋同检查，0 对才放行
python3 factory.py show R003
```

## 8. 当前库存

| RID | 状态 | 固定 | 叙事 / 主角 / 画风 / 情绪 |
|---|---|---|---|
| R001 | shipped | — | 困境—救星—反转 / 拟人窑 / 扁平矢量 / 焦虑→释然 |
| R002–R007 | draft | 轮带修复 · 30 秒 | 由 `factory.py sample --seed 7` 抽出，`check` 0 对趋同，待编剧 agent 写分镜 |
