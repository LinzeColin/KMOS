"""manim 引擎模板（待本机安装后验证）：竖屏 1080×1920，品牌色，示例为「圆 ≠ 同轴」的几何讲解骨架。

  manim -qh --fps 30 -r 1080,1920 template.py Coaxial      # 输出在 media/videos/
配音与音乐另行合成后用 ffmpeg 混入（-af loudnorm=I=-14:TP=-1.5:LRA=11）。
"""
from manim import *

GREEN, CREAM, GOLD = "#1E4638", "#F4EFE3", "#C9A24A"
config.background_color = GREEN
config.frame_width, config.frame_height = 9, 16


class Coaxial(Scene):
    def construct(self):
        a = Circle(radius=1.6, color=CREAM).shift(UP * 3)
        b = Circle(radius=1.6, color=CREAM).shift(DOWN * 3 + RIGHT * 0.25)
        title = Text("两个孔都是圆的", font_size=48, color=CREAM, weight=HEAVY).to_edge(UP, buff=1.4)
        self.play(Write(title), Create(a), Create(b), run_time=1.5)
        axis = DashedLine(a.get_center() + UP * 2.2, a.get_center() + DOWN * 8.2, color=GOLD)
        self.play(Create(axis), run_time=1)
        gap = Arrow(b.get_center() + LEFT * 0.25, b.get_center(), buff=0, color=GOLD)
        self.play(GrowArrow(gap), Indicate(b, color=GOLD), run_time=1)
        self.wait(1)
