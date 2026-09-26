# 开明高新 30 秒宣传动画（单镜头 · 卡点）

竖屏 1080×1920 / 30fps / 30.0s，H.264 + AAC，响度 -14 LUFS，适配抖音、X、Instagram Reels、Facebook Reels。
画面与 BGM 全部由本目录代码生成：无第三方素材、无第三方音乐，可商用发布。成片不入仓。

## 生成

```bash
pip install playwright numpy scipy imageio-ffmpeg pillow
mkdir -p fonts   # 放入两款 OFL 字体：
#  得意黑 SmileySans-Oblique.ttf  https://github.com/atelier-anchor/smiley-sans/releases/download/v2.0.1/smiley-sans-v2.0.1.zip
#  思源黑体 NotoSansSC-Black.otf   https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/SubsetOTF/SC/NotoSansSC-Black.otf
python3 music.py /tmp/bgm.wav
python3 render.py /tmp/KM_30s.mp4 --audio /tmp/bgm.wav        # 成片
python3 render.py /tmp/frames --frames 2.6,9.4,21.5            # 抽帧目检
```

`render.py` 用本机 Chromium（`/opt/pw-browsers/chromium-1194`）逐帧调用 `render.html` 的 `renderAt(t)`，
PNG 流直送 ffmpeg；甩镜时段做 6 次时间超采样，得到真实运动模糊。

## 时间轴（120 BPM，1 拍 = 0.5s，画面与音乐共用同一套秒数）

| 秒 | 画面 | 音乐/音效 |
|---|---|---|
| 0–3.6 | 窑宝哭脸，轮带磨损红光，“嘎吱~”；气泡“哎哟…轮带磨秃了” | 低通 pad，吱嘎，悲伤长号 |
| 3.6–4.2 | 甩镜下摇到老板办公室 | whoosh |
| 4.2–7.0 | 硬币飞出窗外；日历狂翻到第 60 天；老板安全帽弹飞 | 鼓进场，硬币叮，翻页，boing，军鼓加速滚奏 + 上升音 |
| 7.0–8.0 | 手机来电“武汉开明高新”，镜头冲进手机屏 | 来电铃，7.875 留白 |
| 8.0 | 白闪 + KM 标志砸入，“开明高新 上门啦 / 别拆！现场修！” | **Drop** |
| 8.9–10 | 工程车冲过头急刹，“嘀嘀嘀”倒车回位 | 急刹、倒车嘀 |
| 10–20 | 5 个工位，每 2s 一次甩镜：轮带在线车削 / 托轮修复 / 大齿圈断齿重生 / 表针归零 / 调窑找正“嗒！” | 主旋律 hook，工位音效卡在拍点 |
| 20–23 | 唱片急停；手放咖啡在转动的窑上，水平仪居中，“咖啡一滴不洒”；老板冒出来偷喝，安全帽再次弹飞 | 急停刮碟，秒针滴答，嘶溜，boing |
| 23–27 | 整个工厂缩成地球上的武汉落点；近 10,000 家企业 / 30+ 省份 / 18 个国家 / 行业标签 | 音乐回归，计数滴答，落点音阶 |
| 27–30 | 冲进地球 → 片尾卡：公司名、大型设备 · 在线修复、免拆运/现场修/少停机、抖音搜索 @WHKM2020；窑宝探头眨眼“坏了？找开明！” | 27.875 留白，28.0 终击，29.5 收尾 |

## 事实来源

- 业务与服务规模（冶金、建材、矿山、冶炼厂、电厂、石油钻探等近万家企业，30 多个省、18 个国家；齿轮/轮带在线修复）：
  搜索引擎收录的官网简介 `whkm.cn/about`（标题“公司简介-武汉开明高新科技有限公司”）。
- 工序（测量、加工、焊接、复检）与部件（轮带、托轮、筒体、调窑）：`KMDatabase/data/KMVideo/素材登记表_public.md` 画面标注。
- KM 标志为动画自绘字标，发布前可替换为公司正式 logo。
