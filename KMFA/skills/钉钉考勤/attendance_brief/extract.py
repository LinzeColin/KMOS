"""人员表图片 -> 结构化记录。

版式（已用 82 张历史图验证）：
  列  0 类别 | 1 施工总人数 | 2 项目名称 | 3 工种 | 4..N-3 作业人员 | 人数 | 车辆 | 车牌
  类别列自上而下的合并块固定为：表头 → 检修 → 生产部 → 休息人员 → 回程途中
「检修」「休息」在原图里是竖排文字，Vision 认不出来 —— 所以类别不靠 OCR 认，
靠合并块的块序推断，再用能认出来的「生产部」「回程途中」当校验锚点。
"""
from __future__ import annotations
import numpy as np
from . import grid as G
from . import vision

CAT, TOT, PROJ, KIND = 0, 1, 2, 3
# 表尾有一行是「焊工 / 工程师·后勤 / 车工 / 业务员 / 司机」的分组表头，不是人名
NOT_A_NAME = {"焊工", "车工", "管理", "内部", "外协", "司机", "业务员", "钳工",
              "工程师", "后勤", "工程师/后勤", "后勤司机", "休息", "途中", "人数",
              "类别", "工种", "项目名称", "作业人员", "施工总人数", "车辆类型", "车牌号"}
PUNCT = "、，,。.·:：;；|/\\ 　()（）"
# 表头词。NOT_A_NAME 是给**人名**候选用的，里面混着工种值（内部 / 外协 / 焊工…），
# 拿它去过滤工种列会把正确答案一起滤掉 —— 这里只滤真正的表头。
HEADER = {"类别", "工种", "项目名称", "作业人员", "施工总人数", "人数",
          "车辆类型", "车牌号", "序号"}

def clean(tok: str) -> str:
    return tok.strip(PUNCT).strip()
CATEGORY_ORDER = ["检修", "生产部", "休息人员", "回程途中"]
ONSITE_PROJECT = "厂内"          # 类别属检修但人在厂里 —— 照样要打卡

def _spans(gray, xs, ys, col: int) -> list[tuple[int, int]]:
    out, start = [], 1
    for r in range(2, len(ys) - 1):
        if G.has_hline(gray, xs[col], xs[col + 1], ys[r]):
            out.append((start, r - 1)); start = r
    out.append((start, len(ys) - 2))
    return [s for s in out if s[1] >= s[0]]

def _categories(gray, xs, ys, cell_text) -> dict[int, str]:
    """按块序给每一行定类别，并用可识别的锚点校验。"""
    blocks = [b for b in _spans(gray, xs, ys, CAT) if b[0] >= 2]
    named = {i: cell_text(r, CAT) for i, (a, b) in enumerate(blocks)
             for r in range(a, b + 1) if cell_text(r, CAT)}
    order = CATEGORY_ORDER if len(blocks) == len(CATEGORY_ORDER) else None
    out: dict[int, str] = {}
    for i, (a, b) in enumerate(blocks):
        lit = next((cell_text(r, CAT) for r in range(a, b + 1) if cell_text(r, CAT)), "")
        name = lit if lit in CATEGORY_ORDER else (order[i] if order else "")
        for r in range(a, b + 1):
            out[r] = name
    # 锚点校验：认得出来的那几个必须坐在预期的块上
    for i, (a, b) in enumerate(blocks):
        lit = named.get(i, "")
        if lit in CATEGORY_ORDER and order and lit != order[i]:
            return {}          # 块序与锚点冲突 -> 放弃推断，交由上层降级
    return out

def extract(path: str) -> dict:
    gray = G.load_gray(path)
    xs, ys = G.grid(gray)
    cellmap = vision.cells(path, xs, ys)
    fullmap = vision.full(path)
    H, W = gray.shape

    def cell_text(r, c):
        return cellmap.get((r, c), ("", ""))[0].strip()

    def cell_candidates(r, c) -> list[str]:
        """该格的全部 OCR 候选：逐格 2 路 + 整图多路投票落在该格的文本。"""
        out = list(cellmap.get((r, c), ("", "")))
        # 整图路按「行」纳入候选：同一行里 OCR 常把整排姓名并成一个文本块，
        # 按格取会漏掉正确候选（实测有姓名就是这样漏掉的）。
        gy0 = ys[r] / H / 0.012
        gy1 = ys[r + 1] / H / 0.012
        for (_gx, gy), texts in fullmap.items():
            if gy0 - 1 <= gy <= gy1 + 1:
                out += texts
        toks = []
        for t in out:
            toks += [clean(x) for x in t.split()]
        return [t for t in dict.fromkeys(toks) if t and t not in NOT_A_NAME]

    cats = _categories(gray, xs, ys, cell_text)
    def block_text(col: int, a: int, b: int) -> str:
        """一个合并块的文字。先走逐格路，整块读空就退到整图路按几何范围取。

        逐格那一路对**跨多行的合并单元格**会整块读空：它按单行裁剪，而合并块里的字
        是垂直居中的 —— 大部分单行格子是纯空白（被 `std < 12` 判成空格子直接跳过），
        中间那一行又把字裁成上下半截，OCR 读不出完整的字。
        2026-09-15 实测：同一张表里跨 1–3 行的项目名全读到了，唯独跨 6 行的那个
        项目名整块全空，连带那一块的工种（内部 / 外协）也一起丢 ——
        后果是 23 个外协被当成自有员工去查考勤，整份报告被防呆闸判成「名单待核」。
        退到整图那一路后，同一个块拿到 8 票正确读法对 2 票误识，投票就纠回来了。
        """
        v = next((cell_text(x, col) for x in range(a, b + 1) if cell_text(x, col)), "")
        if v:
            return v
        gx0, gx1 = xs[col] / W / 0.015, xs[col + 1] / W / 0.015
        gy0, gy1 = ys[a] / H / 0.012, ys[b + 1] / H / 0.012
        toks: list[str] = []
        for (gx, gy), texts in fullmap.items():
            if gx0 <= gx <= gx1 and gy0 <= gy <= gy1:
                toks += [clean(x) for t in texts for x in t.split()]
        toks = [t for t in toks if t and t not in HEADER]
        if not toks:
            return ""
        # 多路投票：同一个块被十几路 OCR 读过，票数最高的那个才采信。
        return max(set(toks), key=toks.count)

    def inherit(col: int) -> dict[int, str]:
        out: dict[int, str] = {}
        for a, b in _spans(gray, xs, ys, col):
            v = block_text(col, a, b)
            for r in range(a, b + 1):
                out[r] = v
        return out

    projs = inherit(PROJ)
    kinds = inherit(KIND)

    ncol = len(xs) - 1
    # 表尾「休息人员 / 回程途中」区块的列结构与主体不同 —— 姓名从第 1 列就开始
    FOOTER = {"休息人员", "回程途中"}
    rows = []
    for r in range(2, len(ys) - 1):
        cat = cats.get(r, "")
        ppl_cols = range(1, ncol - 2) if cat in FOOTER else range(4, ncol - 3)
        names = []
        for c in ppl_cols:
            t = cell_text(r, c)
            pool = cell_candidates(r, c)
            for raw in t.split():
                n = clean(raw)
                if not (2 <= len(n) <= 4) or n.isdigit() or n in NOT_A_NAME:
                    continue
                # 候选池按「像不像」过滤。整图路是按整行取的，同一行别人的名字也在池里，
                # 若放得太宽就会把邻座当成本格候选 —— 实测某一格曾混进邻座的两个名字，
                # 两个都在花名册，直接把整份报告拖成「读不准」。
                # 2 字姓名差 2 字就是另一个人，只许差 1 字；3 字及以上才放到差 2 字。
                lim = 1 if len(n) <= 2 else 2
                cand = [n] + [x for x in pool if x != n and len(x) == len(n)
                              and sum(a != b for a, b in zip(x, n)) <= lim]
                names.append({"ocr": n, "候选": cand, "格": (r, c)})
        if not names:
            continue
        rows.append({
            "行": r,
            "类别": cat,
            "项目": "" if cat in FOOTER else projs.get(r, ""),
            "工种": "" if cat in FOOTER else (kinds.get(r, "") or cell_text(r, KIND)),
            "标注人数": cell_text(r, ncol - 3),
            "人员": names,
        })
    title = " ".join(cell_text(0, c) for c in range(ncol) if cell_text(0, c)).replace(" ", "")
    return {"标题": title, "网格": [len(ys) - 1, ncol], "行": rows,
            "类别可信": bool(cats)}

def must_punch(row: dict) -> bool:
    """该不该打钉钉卡。

    开明自有员工一律要打卡 —— 外派在项目现场的也要，不存在「出差就免打卡」。
    实测佐证：抽 8 名外派员工查 09-01~09-04，8/8 每天都有打卡记录（55 Normal / 9 NotSigned），
    说明外派人员确实在「开明考勤」考勤组内。
    只有明确标注休息的当天不判考勤。
    """
    return row["类别"] != "休息人员"

def is_outsourced(row: dict) -> bool:
    return "外协" in (row.get("工种") or "")
