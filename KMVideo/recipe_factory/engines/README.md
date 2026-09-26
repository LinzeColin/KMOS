# 引擎目录

所有页面引擎共用 `capture.py`：页面提供 `window.ready`、`window.renderAt(t, fps)`、`window.DURATION`，
采集器逐帧取 PNG 交给 ffmpeg；有 `<canvas id="c">` 用 toDataURL，没有就截整页（SVG/DOM）。
`vendor/` 放 three.js r170 与 GSAP 3.13，页面用相对路径引用，本机离线可用。

| 引擎 | 起步文件 | 状态 | 车道 |
|---|---|---|---|
| canvas2d | `../../promo_30s/render.html` + `music.py` | 云端出过 30 秒成片（R001） | TOON |
| p5brush | `../../../KMBearAnimationBase/`（开明小熊 + Clawd；`node render.mjs --clip --soft-gl`） | 云端出片 INK-002（62 秒讲解片）；无显卡用 --soft-gl --density=0.6667，1080p 约 1.7 秒/帧 | INK |
| threejs | `threejs/template.html` | 云端 SwiftShader 出过接触表 | VOX |
| svg_gsap | `svg_gsap/template.html` | 云端出过接触表与 6 秒 mp4 | TYPE |
| manim | `manim/template.py` | 模板已写，本机装 manim 后验证 | MATH |
| remotion | 空位 → `workspace.yaml paths.remotion_project` | 本机已有 Remotion，按 `renderAt` 同样的秒点表写 composition | REAL |
| ffmpeg_footage | 空位 | 素材从 `paths.footage_registry` 选片，ffmpeg 剪辑 + capture.py 出透明叠层 | REAL |
| blender | 空位 → `paths.blender_entry` | Blender 工作间负责，本工坊只登记（EXT） | EXT |
| comfyui | 空位 → `paths.comfyui_entry` | 本机具备 GPU 与 ComfyUI 后开放 `ai_illustration` | 可并入 INK/VOX |

新引擎接入三步：在 `factors.yaml engines` 加一行（requires、kit、status）→ 给 `medium` 加画风取值并写 engine →
在 `lanes.yaml` 把画风归到一条车道。能力就绪后在 `workspace.yaml capabilities` 改 true。

`vendor/` 不入代码仓，压缩包里自带；需要重新获取时：
`https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js`、`https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js`。
