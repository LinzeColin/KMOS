# KMDY-RF 配方工坊

**名字**：KMDY-RF（Recipe Foundry，配方工坊）。与 KMDY 同一个抖音内容域，RF 表明它的方法：
用配方组合出片。本机的 Blender 工作间以 **7 维 + 4 要素** 把每部片子做好，
配方工坊以 **3 层因素 + 配方组合** 让每部片子彼此不同；两边共用同一套质量闸门（`GATES.md`），
配方库互相登记，自动避开对方用过的组合。

## 1. 两套东西各管什么

| | 管什么 | 在哪 |
|---|---|---|
| 3 层因素 + 配方 | **差异**：这部片子和别的片子哪里根本不同 | `factors.yaml` `lanes.yaml` `factory.py` |
| 4 要素 + 7 维 | **质量**：这部片子够不够好 | `GATES.md`（执行 KMDY《通用基准.md》） |

一部片子 = 一份配方 = 18 个因子各取一个值。改 L0 得到另一部片子；改 L1 得到同一部片子的另一种讲法；
改 L2 得到同一部片子的皮肤。**两部片子 L0 至少 3 项不同才算两部片子。**

Blender 工作间现有 3 部成片（N03 / N04 / N06）用配方语言登记在 `recipes/EXT/`，可以看出它开始趋同的原因：
三部都是获得感主打、无人物、面向检修负责人、惊喜机制都是「信息差 / 先演错法」、标题都是「A ≠ B」句式。
它只有一条生成轴（STY 叙事风格目录）；配方工坊把惊喜机制、观众、主角、画风拆成独立的 L0 轴，
每条轴都参与去同质化。

## 2. 三层因素

| 层 | 因子 |
|---|---|
| **L0 根本**（8 个） | 价值主打、叙事母型（18）、惊喜机制（11）、主角（9）、目标观众（7）、画风（22，决定引擎）、业务入口（14，KMBID 分类）、情绪弧（8） |
| **L1 结构**（7 个） | 行业场景（12，KMBID 分类）、开头钩子、镜头语言、音乐、人声、时长、字幕 |
| **L2 表层**（3 个） | 品牌色配比、转场主招、结尾引导 |

行业放 L1：同一个故事换一个行业名，正是 KMDY 退回条件里的「换名词、换皮肤」。
带 `requires` 的取值只在 `workspace.yaml capabilities` 为 true 时开放：写实真人主角要真实来源，
数据可视化要带出处的数据，防腐保温业务要公司原件。

## 3. 车道：每个 agent 领一个大类组合

车道固定画风家族（同一引擎、同一套手艺），其余 L0 因子在车道内持续演化。

| 车道 | 画风 | 引擎 | 偏向 | 状态 |
|---|---|---|---|---|
| TOON | 扁平卡通 / 像素 / 剪纸 / 粉笔 | Canvas2D | 惊喜、幽默、卡点 | 成片 R001 + 配方 TOON-001 |
| INK | 水彩 / 国潮水墨 / 蜡笔 | p5.brush（KMBearAnimationBase） | 感染力、温度；开明小熊 IP | 成片 INK-002 讲解片 + 配方 INK-001 |
| TYPE | 蓝图 / 排版 / 数据 / 信息图 | SVG + GSAP | 获得感、出片最快 | 配方 TYPE-001，模板已测 |
| MATH | 几何讲解 / 物理曲线 | manim | 原理的「为什么」 | 待本机装 manim |
| VOX | 低多边形 / X 光剖视 / 霓虹 / 黏土感 3D | three.js | 表达力、看穿结构 | 配方 VOX-001，模板已测 |
| REAL | 实拍包装 / 照片图解 / 现场纪实 | Remotion + ffmpeg | 可信度、真实处境 | 配方 REAL-001，需 SMB 素材 |
| EXT | Blender 3D + 真实照片 | Blender | — | Blender 工作间，只登记不出片 |

**建议开 7 个 agent**：6 条车道各 1 个 + 1 个质检调度。
- 按引擎分车道，agent 的手艺（`手艺.md`）会越积越深，出片越来越快
- 每条车道只放一个 agent：同车道两个 agent 会互相抢组合空间，车道窗口也会失效
- 质检调度单独一个：打分的人不做片，七维评分才可信
- 首批先开 6 个：TOON、INK、TYPE、VOX、REAL 五条车道 + 质检调度。本机装好 manim 后再开 MATH

## 4. 演化与衍变

- **抽样** `sample`：车道刚开工，或想换全新方向
- **演化** `evolve`：从本车道得分最高的片子出发，继承它的价值主打（`--keep` 可指定更多基因，最多 5 个），
  其余 L0 重新抽；子代记录 `parent`，形成谱系。Owner 打的分写进配方 `score`
- **衍变**：闸门开始拒绝（组合空间收窄），车道 agent 提议新的因子取值，质检调度收录进 `factors.yaml`。
  因子库随生产持续变大，量产与不趋同同时成立
- **四道闸**：L0 ≥3 项不同；(叙事, 惊喜机制, 画风) 全库唯一；车道最近 4 部叙事与惊喜机制不重复；
  批内同值 ≤ ceil(n/3)。`status` 显示各车道剩余三元组

## 5. 部署（全部在本机与 SMB，不连接 GitHub）

1. 解压，按 `AGENT_PROMPTS.md §0` 派一个部署 agent：填 `workspace.yaml`，建 SMB 目录，装依赖，验证引擎，登记 Blender 工作间成片
2. 每条车道派一个车道 agent（`§1`），把 `{LANE}` 换成车道 ID
3. 派一个质检调度 agent（`§2`）
4. Owner 只做两件事：人眼验收（给 `score`）、决定发布

目录（SMB，`paths.root`）：

```
KMDY-RF/
  配方/<车道>/<RID>.yaml      全局进度表：draft → storyboarded → rendered → qc_pass → owner_accepted → published
  车道/<车道>/手艺.md          本车道引擎经验（车道 agent 追加）
  车道/<车道>/<RID>/           代码、分镜、接触表、成片
  登记/事件.jsonl              只追加：待质检、质检结论、发布回执
  登记/提议.md                 新因子取值提议
  00_广播/发件.KMDY-RF.jsonl
```

## 6. 命令

```bash
python3 factory.py status                                     # 各车道进度与剩余组合空间
python3 factory.py sample --lane TYPE --n 2                   # 抽样
python3 factory.py sample --lane TOON --fix business=rotary_kiln --fix duration=s30
python3 factory.py evolve --lane TOON --parent R001 --keep value_core,twist
python3 factory.py check                                      # 全库趋同检查，0 处才放行
python3 factory.py show VOX-001
python3 engines/capture.py 页面.html 成片.mp4 --audio bgm.wav   # 页面引擎出片
python3 engines/capture.py 成片.mp4 接触表.png --sheet 20       # 任意成片拼接触表
```

## 7. 文件

| 文件 | 内容 |
|---|---|
| `factors.yaml` | 因子库与引擎表 |
| `lanes.yaml` | 车道定义 |
| `workspace.yaml` | 本机/SMB 路径与能力开关（部署时只改它） |
| `factory.py` | 抽样、演化、闸门、状态 |
| `GATES.md` | 固定层、四要素、七维 |
| `AGENT_PROMPTS.md` | 部署 / 车道 / 质检调度 / 单片提示词 |
| `engines/` | 通用采集器与各引擎模板 |
| `recipes/` | R001、INK-002 两部成片的配方，5 条车道首份配方，EXT 登记的 3 部 Blender 成片 |
| `refs/` | 《故事型广告 S1 创作基准》《KMDY 共同底座》原文 |

相关项目（仓库根目录）：`ClaudeAnimationBase/`（Clawd 手绘底座）、`KMBearAnimationBase/`（开明小熊手绘底座，INK 车道引擎）、
`ClaudeVideo/`（PDoomVideo 长片源码，分章并行与舞台秀递进的范例）。
