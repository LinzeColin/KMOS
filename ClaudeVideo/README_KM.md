# ClaudeVideo：PDoomVideo 并入说明

来源：https://github.com/JohnHeibel/PDoomVideo（提交 `fa546a3`，2026-09-25）。作者是 John Heibel，也是 `ClaudeAnimationBase` 的作者。
原仓库没有 LICENSE 文件，`package.json` 写的是 ISC。本目录只作内部学习与参考，不对外再分发。
**歌曲 `assets/pdoom.mp3` 不入仓**，因为它的来源是第三方 AI 生成歌曲，权属不明。需要复现原片时，按原仓库 README 自行放回 `assets/`。

## 它是什么

一部 2 分 36 秒的 Clawd 音乐 MV《I'm Upping My P(doom)》的完整源码，全部由 Opus 5.5 在 Claude Code 里生成。
它和 `ClaudeAnimationBase` 用同一套 p5.js + p5.brush 手绘引擎：`ClaudeAnimationBase` 是作者事后从这部片子里提炼出的通用底座，这里是原始的长片工程。

| 部分 | 内容 |
|---|---|
| `src/ch/c01…c09` | 9 个章节，一章一个文件，由并行子 agent 分头绘制 |
| `ANIMATION_GUIDE.md` | 模型写给子 agent 的风格与代码简报：每个子 agent 读它就能独立画一章 |
| `STORYBOARD.md` | 全片分镜：一个贯穿舞台、四次递进的副歌、首尾呼应的「原来是一场戏」反转 |
| `src/cast.js` | 人类角色「研究员」：和 Clawd 同一套姿态接口（手臂角度、走路、表情、挂点） |
| `src/props.js` | 反复出现的舞台道具（幕布、P(doom) 温度计） |
| `src/lyrics.js` | 歌词逐句时间表，画面按歌词卡点 |
| `legacy/` | 第一代（中等推理）版本，可对比两代差距 |

## 对 KMDY-RF 工坊有什么用

1. **长片与多 agent 分章的方法**：一部 1–3 分钟的片子拆成章节，共用一份简报，章节并行交给子 agent。
   这就是 RF 车道 agent 做长片时的模板，已写进 `KMVideo/recipe_factory/AGENT_PROMPTS.md`。
2. **人类角色套件**：`researcher()` 可以直接改成开明员工、客户、老师傅，和 Clawd、开明小熊同台，补上 INK 车道缺的人物。
3. **递进母题与反转收尾**：同一个舞台、同一个道具（温度计）每次副歌都升级一档，结尾拉远揭晓。
   已作为新的叙事母型「舞台秀递进」和惊喜机制「拉远揭晓」加入因子库。
4. **歌词/旁白卡点**：`lyrics.js` 的逐句时间表可以直接换成 TTS 旁白或原创歌曲的时间表。
5. **两代对比**：`legacy/` 与正式版并排，说明推理强度和「先写分镜再动手」对成片质量的影响，可作质检培训材料。

## 运行

```bash
npm install
node render.mjs --frames=0:156.6 --workers=4   # 需要 assets/pdoom.mp3
node render.mjs --encode --out=out/pdoom.mp4
```
没有显卡的机器上，水彩填充每帧要数十秒；参照 `ClaudeAnimationBase` 的 `--flat` 平涂模式改造后，1080p 每帧约 3 秒。
