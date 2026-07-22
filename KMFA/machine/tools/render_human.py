#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_human.py —— 从机器平面渲染人类平面七文件

双平面原则：
- 机器平面由 machine/canonical_facts.yaml、acceptance_contract.yaml、
  task_graph.yaml、release_policy.yaml、traceability.csv（v1.5.2 交付合同）与 machine/facts/*
  （旧业务状态）两个已声明 namespace 组成。
- 人类平面 文档/ 七个文件全部是渲染产物，无一手写。
  agent 负责生产机器平面事实，渲染器把它们渲染成七文件；负责人只复审，不手写。
- 因此没有任何"手写区"。每次渲染都会覆盖全部七个文件。

为什么人类平面必须渲染而不能手写：
  「功能清单里没有功能」的根因是它允许被手写。任何允许手写的人类可读文件，
  最终必然退化成 append-only 日志。这是结构决定的。产品需求与口径字典同样如此，
  所以它们也从机器平面渲染，不留手写口子。

事实源约定（每个渲染文件的头注释也声明同一映射）：
  00_我在哪.md      <- canonical 合同索引 + legacy status/blockers/roadmap
  01_产品需求.md    <- canonical goal/decisions/OKRs/non-goals/requirements + legacy product
  02_系统架构.md    <- canonical storage/privacy + legacy features/data_contract/config
  03_口径字典.md    <- canonical metrics + legacy glossary
  04_操作流程.md    <- canonical authorization/domain index + legacy flows
  05_执行与验收.md  <- canonical + Acceptance/Task DAG/Release/Traceability + legacy plan/acceptance/runs
  06_运维手册.md    <- canonical ops requirement index + legacy config/ops/changelog

Canonical Facts 缺失、损坏、ID 重复或关键字段不完整时必须停止渲染；
旧业务事实缺失时对应章节仍如实显示“待补”。

用法:  python3 machine/tools/render_human.py [--root .]
退出码: 0=渲染完成
"""
import argparse
import json
import re
import sys
from pathlib import Path

from check_traceability import load_and_validate

GENERATED = (
    "<!-- 本文件由 machine/tools/render_human.py 从机器平面生成。请勿手写——下次渲染会覆盖。 -->"
)
# 单个字段还没值时的占位——短、明确、不装懂
UNKNOWN = "待补"


def blank_note(what, whence):
    """某个章节暂时没内容时，用一句人话说明，而不是摆一张空表。

    what: 这一节本该写什么（读者视角）
    whence: 内容将来从哪来（谁补、补什么）；其中的文件路径会自动包成代码样式，
            以豁免中文门。
    """
    # 把 machine/facts/xxx.yaml 之类路径包进反引号（代码标识符豁免中文门）
    whence = re.sub(r"(machine/[\w./-]+)", r"`\1`", whence)
    return f"> 暂时还没有{what}。等{whence}之后，这里会自动出现内容。现在空着是如实反映——没接上就是没接上。"

# 跨项目通用治理术语，渲染 03_口径字典 时并入术语表，使中文门对它们豁免。
COMMON_GLOSSARY = [
    ("Owner", "负责人", "项目/产品的决策与复审责任人"),
    ("Stage", "阶段", "路线图一级单元"),
    ("Phase", "步骤", "阶段下的二级单元"),
    ("Task", "任务", "步骤下的三级单元"),
    ("Roadmap", "路线图", "阶段→步骤→任务的完整计划"),
]


def load_json(path: Path, default):
    """读一个 JSON 事实源；缺失或损坏时返回 default（渲染成 UNKNOWN）。"""
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return default


def load_yaml_or_json(path: Path, default):
    """config/data_contract 允许 yaml 或 json。

    JSON 内容优先用标准库解析 —— 无第三方依赖，渲染结果跨环境完全确定。
    这一条很关键：曾经这里直接 import yaml，没装 PyYAML 的 CI 会把配置读成
    {"_raw": ...} -> 02/06 渲染成空 -> 渲染一致门莫名报红。JSON 是 YAML 的子集，
    所以把事实写成 JSON 内容即可彻底摆脱该依赖。
    """
    if not path.is_file():
        return default
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text) or default
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    try:
        import yaml  # noqa
        return yaml.safe_load(text) or default
    except Exception:
        # 既非 JSON 又没有 yaml 库：不阻塞渲染，调用方只判存在性
        return {"_raw": text}


def load_required_canonical(root: Path):
    """读取并最小校验 v1.5.2 Canonical Facts；失败必须阻断渲染。"""
    path = root / "machine" / "canonical_facts.yaml"
    data = load_yaml_or_json(path, None)
    if not isinstance(data, dict) or "_raw" in data:
        raise ValueError(f"Canonical Facts 不可解析: {path}")
    required = {
        "schema_version", "taskpack_version", "status", "authorized_at",
        "product", "owner_authorization", "decisions", "strategic_goal",
        "okrs", "non_goals", "storage_contract", "privacy_contract",
        "requirements", "stage_count", "task_count", "acceptance_count",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"Canonical Facts 缺字段: {missing}")
    decisions = data.get("decisions")
    requirements = data.get("requirements")
    if not isinstance(decisions, list) or not isinstance(requirements, list):
        raise ValueError("Canonical Facts decisions/requirements 必须是列表")
    expected_counts = {
        "decisions": (len(decisions), 14),
        "requirements": (len(requirements), 49),
        "okrs": (len(data.get("okrs", [])), 4),
        "non_goals": (len(data.get("non_goals", [])), 7),
    }
    wrong_counts = {key: pair for key, pair in expected_counts.items() if pair[0] != pair[1]}
    if wrong_counts:
        raise ValueError(f"Canonical Facts 固定集合计数错误: {wrong_counts}")
    nested_required = {
        "product": {"name", "target_url", "homepage_path", "pursuing_goal"},
        "owner_authorization": {"interpretation"},
        "storage_contract": {"structured_data", "file_bytes", "browser_storage",
                             "retention", "durability_proof"},
        "privacy_contract": {"site_visibility", "workspace_visibility_default",
                             "publish_mode", "secret_transport", "public_indexing"},
    }
    for section, keys in nested_required.items():
        value = data.get(section)
        if not isinstance(value, dict) or any(key not in value for key in keys):
            raise ValueError(f"Canonical Facts {section} 结构不完整")
    if len(data["owner_authorization"]["interpretation"]) != 4:
        raise ValueError("Canonical Facts owner_authorization.interpretation 必须为 4 条")
    for label, rows in (("decision", decisions), ("requirement", requirements)):
        ids = [row.get("id") for row in rows if isinstance(row, dict)]
        if len(ids) != len(rows) or any(not value for value in ids):
            raise ValueError(f"Canonical Facts {label} ID 缺失")
        if len(ids) != len(set(ids)):
            raise ValueError(f"Canonical Facts {label} ID 重复")
    required_requirement_fields = {
        "id", "area", "title", "statement", "priority", "metric",
        "baseline", "target", "window", "owner", "task",
    }
    for row in requirements:
        absent = sorted(key for key in required_requirement_fields if not row.get(key))
        if absent:
            raise ValueError(f"Canonical Facts {row.get('id', '?')} 缺字段: {absent}")
    metric_ids = [f"metric::{row['id']}" for row in requirements]
    if len(metric_ids) != len(set(metric_ids)):
        raise ValueError("Canonical Facts 指标 ID 重复")
    return data


def load_required_release_policy(root: Path):
    """读取 sealed 发布策略；缺失或结构漂移必须阻断七文件渲染。"""
    path = root / "machine" / "release_policy.yaml"
    data = load_yaml_or_json(path, None)
    if not isinstance(data, dict) or "_raw" in data:
        raise ValueError(f"Release Policy 不可解析: {path}")
    list_fields = (
        "environments", "release_principles", "promotion_gates",
        "automatic_rollback_triggers", "rollback_order", "stop_conditions",
    )
    required = {"schema_version", "taskpack_version", *list_fields}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"Release Policy 缺字段: {missing}")
    if str(data.get("taskpack_version")) != "1.5.2":
        raise ValueError("Release Policy taskpack_version 必须为 1.5.2")
    for field in list_fields:
        value = data.get(field)
        if not isinstance(value, list) or not value:
            raise ValueError(f"Release Policy {field} 必须是非空列表")
    expected_gates = [
        "G0 Authority", "G1 Product Contract", "G2 Walking Skeleton",
        "G3 Product Completeness", "G4 Assurance", "G5 GA",
    ]
    gates = data["promotion_gates"]
    if any(not isinstance(row, dict) for row in gates):
        raise ValueError("Release Policy promotion_gates 行必须是 mapping")
    if [row.get("gate") for row in gates] != expected_gates:
        raise ValueError("Release Policy promotion_gates 必须按 G0-G5 精确排列")
    for row in gates:
        requires = row.get("requires")
        if not isinstance(requires, list) or not requires:
            raise ValueError(f"Release Policy {row.get('gate')} requires 必须非空")
    return data


def md_cell(value):
    """机械转义 Markdown 表格单元格，不改变事实含义。"""
    return str(value).replace("|", r"\|").replace("\n", "<br>")


def flatten_strings(value):
    """按 Canonical Facts 原顺序提取字符串，仅用于派生术语索引。"""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from flatten_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from flatten_strings(child)


def group_requirement_ids(requirements):
    """按 Canonical Facts 首次出现顺序生成事实域 -> Requirement ID 索引。"""
    grouped = {}
    for row in requirements:
        grouped.setdefault(row["area"], []).append(row["id"])
    return grouped


def table(rows, header, empty=None):
    """把 [(a,b,...)] 渲染成 markdown 表。

    空 rows 时不摆空表，改用一句人话（empty）。没给 empty 就退回极简提示。
    """
    if not rows:
        return empty or "> 暂时没有内容。"
    out = ["| " + " | ".join(md_cell(value) for value in header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(md_cell(value) for value in r) + " |")
    return "\n".join(out)


# ---------- 各文件渲染器 ----------

def render_00(facts: Path, canonical):
    status = load_json(facts / "status.json", {})
    blockers = load_json(facts / "blockers.json", [])
    roadmap = load_json(facts / "roadmap.json", {})
    product = canonical["product"]
    contract_rows = [
        ("任务包合同", f"`v{canonical['taskpack_version']}`"),
        ("授权", f"`{canonical['status']}` · `{canonical['authorized_at']}`"),
        ("产品", product["name"]),
        ("目标入口", f"`{product['target_url']}` · 首页 `{product['homepage_path']}`"),
        ("合同规模",
         f"{len(canonical['decisions'])} 决策 / {len(canonical['requirements'])} 需求 / "
         f"{canonical['stage_count']} Stage / {canonical['task_count']} Task / "
         f"{canonical['acceptance_count']} Acceptance"),
        ("当前交付进度", "只读 `../HANDOFF.md`；本文件不复制 delivery phase"),
        ("产品/runtime 版本", "只读 `../VERSION`；不得由任务包版本推断"),
    ]

    def val(key, default="待补"):
        v = status.get(key)
        return f"`{v}`" if v else default

    state_rows = [
        ("版本", val("version")),
        ("进行到哪", f"{val('stage')} · {val('phase')} · {val('task')}"),
        ("进度", status.get("real_progress") or "待补"),
        ("报告可信度", status.get("report_grade") or "待口径字典裁定"),
        ("业务结论", status.get("business_verdict") or "待补"),
        ("卡住的事", f"{len(blockers)} 件" if blockers else "无"),
    ]
    blk_rows = [
        (b.get("id", "?"), b.get("内容", b.get("desc", "")),
         "**只有你能解**" if b.get("owner_only") else (b.get("owner") or "待定"),
         b.get("首次登记", b.get("since", "?")))
        for b in blockers
    ]
    rm_rows = [
        (s.get("id", "?"), s.get("name", ""), s.get("gate", ""),
         s.get("status", ""))
        for s in roadmap.get("stages", [])
    ]

    body = f"""{GENERATED}
<!-- 事实源：machine/canonical_facts.yaml（交付合同索引）；machine/facts/status.json、blockers.json、roadmap.json（旧业务状态） -->
<!-- 上限 120 行 -->

# 我在哪

一眼区分 v1.5.2 交付合同、当前交付进度与旧业务状态。

## 一、v1.5.2 交付合同索引

{table(contract_rows, ["对象", "唯一读取位置或状态"])}

## 二、旧业务当前状态

**业务快照更新于** {status.get('rendered_at', '待渲染')}

{table(state_rows, ["", ""])}

## 三、旧业务卡住的事

{table(blk_rows, ["编号", "什么事", "谁能解", "卡了多久"],
       empty="> 目前没有卡住的事。一旦出现只有你能拍板的阻塞，会自动列在这里并提醒你。")}

## 四、旧业务路线图

{table(rm_rows, ["阶段", "名称", "过关标准", "状态"],
       empty=blank_note("路线图", "把阶段计划写进机器平面（machine/facts/roadmap.json）"))}

## 五、这套文档怎么读

想了解什么，就翻对应的一份。七份全部由机器平面自动生成，你只需复审：

| 想知道 | 翻哪份 |
|---|---|
| 这东西为谁做、要解决什么、不碰什么 | `01_产品需求.md` |
| 有哪些功能、数据怎么流、参数为什么这么设 | `02_系统架构.md` |
| 每个数字到底怎么算、外部数据得长什么样 | `03_口径字典.md` |
| 业务上一步步怎么走 | `04_操作流程.md` |
| 这一轮在做什么、怎么算做完、做到哪了 | `05_执行与验收.md` |
| 怎么跑起来、参数改哪、报错了怎么办 | `06_运维手册.md` |
"""
    return body


def render_01(facts: Path, canonical):
    """产品需求：v1.5.2 合同为主，旧业务范围作为独立快照保留。"""
    prod = load_json(facts / "product.json", {})
    users = [(u.get("who", ""), u.get("want", "")) for u in prod.get("users", [])]
    nots = prod.get("non_goals", [])
    goal = prod.get("goal") or ""
    decision_rows = [
        (f"`{row['id']}`", row["title"], row["decision"], f"`{row['status']}`")
        for row in canonical["decisions"]
    ]
    okr_rows = [
        (f"`{row['id']}`", row["objective"], " ".join(row["key_results"]))
        for row in canonical["okrs"]
    ]
    requirement_rows = [
        (f"`{row['id']}`", row["area"], row["title"], f"`{row['priority']}`", row["statement"])
        for row in canonical["requirements"]
    ]
    body = f"""{GENERATED}
<!-- 事实源：machine/canonical_facts.yaml（v1.5.2 产品合同）；machine/facts/product.json（旧业务范围快照） -->
<!-- 上限 200 行 -->

# 产品需求

## 一、v1.5.2 目标

**总目标：** {canonical['product']['pursuing_goal']}

**战略目标：** {canonical['strategic_goal']}

## 二、决策

{table(decision_rows, ["ID", "标题", "已授权决定", "状态"])}

## 三、目标与关键结果

{table(okr_rows, ["目标 ID", "目标", "关键结果"])}

## 四、非目标

{chr(10).join(f"- {item}" for item in canonical['non_goals'])}

## 五、需求注册表

指标口径只在 `03_口径字典.md` 展开；`Task`/`Owner` 映射只在 `05_执行与验收.md` 展开。

{table(requirement_rows, ["需求 ID", "事实域", "标题", "优先级", "合同陈述"])}

## 六、旧业务范围快照（独立事实域）

### 旧业务目标

{goal if goal else blank_note("旧业务产品目标", "在机器平面写清目标（machine/facts/product.json 的 goal）")}

### 旧业务用户

{table(users, ["用户", "他要什么"], empty=blank_note("旧业务目标用户", "在机器平面登记用户（machine/facts/product.json 的 users）"))}

### 旧业务非目标

{chr(10).join(f"- {item}" for item in nots) if nots else blank_note("旧业务不做清单", "在机器平面登记非目标（machine/facts/product.json 的 non_goals）")}
"""
    return body


def render_03(facts: Path, canonical):
    """口径字典：v1.5.2 指标与旧业务口径各自保持唯一来源。"""
    g = load_json(facts / "glossary.json", {})
    numbers = [(n.get("项", n.get("item", "")), n.get("裁定", n.get("rule", "")),
                n.get("状态", n.get("status", ""))) for n in g.get("numbers", [])]
    shapes = [(s.get("来源", s.get("source", "")), s.get("要求", s.get("shape", "")),
               s.get("状态", s.get("status", ""))) for s in g.get("data_shapes", [])]
    rules = [(r.get("规则", r.get("rule", "")), r.get("说明", r.get("note", "")))
             for r in g.get("invariants", [])]
    # 术语表 = 通用治理术语 + 项目专属术语（机器平面提供）
    terms = list(COMMON_GLOSSARY) + [
        (t.get("英文", t.get("en", "")), t.get("中文", t.get("zh", "待补中文")),
         t.get("说明", t.get("note", "")))
        for t in g.get("terms", [])
    ]
    metric_rows = [
        (f"`metric::{row['id']}`", f"`{row['id']}`", row["metric"],
         row["baseline"], row["target"], row["window"])
        for row in canonical["requirements"]
    ]
    canonical_terms = sorted({
        word
        for text in flatten_strings(canonical)
        for word in re.findall(r"[A-Za-z][A-Za-z_-]{1,}", text)
    }, key=lambda word: (word.casefold(), word))
    term_lines = "\n".join(
        "- " + "、".join(f"`{word}`" for word in canonical_terms[i:i + 12])
        for i in range(0, len(canonical_terms), 12)
    )
    body = f"""{GENERATED}
<!-- 事实源：machine/canonical_facts.yaml（v1.5.2 指标）；machine/facts/glossary.json（旧业务口径） -->
<!-- 全项目唯一裁定"一个数字是什么"的地方。有争议以本文件为准。 -->
<!-- 中文门：正文出现的英文术语必须在本文件术语对照登记，否则渲染 FAIL。 -->

# 口径字典

## 一、v1.5.2 指标注册表

指标 ID 由需求 ID 机械派生，不另建可写字段：`metric::<requirement.id>`。

{table(metric_rows, ["指标 ID", "需求 ID", "指标", "Baseline", "目标", "观察周期"])}

## 二、旧业务关键数字口径

{table(numbers, ["项", "裁定", "状态"], empty=blank_note("数字口径", "在机器平面裁定（machine/facts/glossary.json 的 numbers）"))}

## 三、旧业务外部数据形态

{table(shapes, ["来源", "必须长什么样", "状态"], empty=blank_note("外部数据形态", "在机器平面登记（machine/facts/glossary.json 的 data_shapes）"))}

## 四、旧业务恒定为真的规则

{table(rules, ["规则", "说明"], empty=blank_note("恒真规则", "在机器平面登记（machine/facts/glossary.json 的 invariants）"))}

## 五、证据等级定义

| 等级 | 含义 |
|---|---|
| `已提取` | 从代码或配置提取并核对 |
| `已声明` | 只有文档说法，未核对 |

## 六、术语对照

正文出现的英文术语在此登记。

{table(terms, ["英文", "中文", "说明"])}

### v1.5.2 授权原文词项

以下词项机械提取自 Canonical Facts，仅登记原文拼写，不在派生层增加定义：

{term_lines}
"""
    return body



def _status_zh(mapping, status):
    """状态值中文化。长的机器串（含下划线）归到其首词的中文，避免污染人类平面。"""
    if not status:
        return ""
    if status in mapping:
        return mapping[status]
    head = status.split("_")[0].split("-")[0].lower()
    if head in mapping:
        return mapping[head] + "（详见机器平面）"
    return status if status.isascii() is False or "_" not in status else "详见机器平面"

def render_02(facts: Path, canonical):
    features = load_json(facts / "features.json", [])
    config = load_yaml_or_json(facts / "config.yaml", {})
    contract = load_yaml_or_json(facts / "data_contract.yaml", {})

    STATUS_ZH = {"active": "进行中", "in_progress": "进行中", "completed": "已完成",
                 "done": "已完成", "planned": "计划中", "blocked": "阻塞",
                 "deprecated": "已弃用", "draft": "草案", "pending": "待办",
                 "proposed": "提议中", "reconstructed": "已重建", "verified": "已核实"}
    feat_rows = [
        (f"`{f.get('id', '?')}`", f.get("name", ""),
         _status_zh(STATUS_ZH, f.get("status", "")),
         "已提取" if f.get("evidence") == "extracted" else "已声明")
        for f in features
    ]
    cfg = config if isinstance(config, dict) and "_raw" not in config else {}
    param_rows = [(k, v.get("intent", "") if isinstance(v, dict) else "")
                  for k, v in cfg.get("parameters", {}).items()] if cfg else []
    ent_rows = [(e.get("entity", "?"), ", ".join(e.get("keys", [])), e.get("pk", ""))
                for e in (contract.get("entities", []) if isinstance(contract, dict) else [])]
    storage = canonical["storage_contract"]
    storage_rows = [
        ("结构化数据", storage["structured_data"]),
        ("文件字节", storage["file_bytes"]),
        ("浏览器存储", storage["browser_storage"]),
        ("保留规则", storage["retention"]),
        ("耐久证明", "；".join(storage["durability_proof"])),
    ]
    privacy = canonical["privacy_contract"]
    privacy_rows = [
        ("站点可见性", f"`{privacy['site_visibility']}`"),
        ("工作区默认可见性", f"`{privacy['workspace_visibility_default']}`"),
        ("发布模式", f"`{privacy['publish_mode']}`"),
        ("秘密传输边界", privacy["secret_transport"]),
        ("公开索引边界", privacy["public_indexing"]),
    ]

    body = f"""{GENERATED}
<!-- 事实源：machine/canonical_facts.yaml（存储/隐私合同）；machine/facts/features.json、data_contract.yaml、config.yaml（旧业务实现快照） -->
<!-- 上限 200 行 -->
<!-- 纯净门：本文件「一、功能清单」章节出现 phase/gate/review/replay/audit 等日志词 -> 渲染 FAIL -->

# 系统架构

区分 v1.5.2 目标合同与旧业务已核验实现；目标不能冒充当前已实现能力。

## 一、功能清单（旧业务实现快照）

只列已经进入旧业务机器事实的功能。做了什么、过了哪些关，去看 `05_执行与验收.md`。

{table(feat_rows, ["编号", "功能", "状态", "证据"],
       empty=blank_note("功能清单", "从代码里把功能抽进机器平面（machine/facts/features.json）"))}

{"**证据一栏怎么看：** 「已提取」= 从代码或配置里核对过；「已声明」= 目前只有文档说法，还没对过代码。" if feat_rows else ""}

## 二、v1.5.2 存储合同

{table(storage_rows, ["关注点", "合同"])}

## 三、v1.5.2 隐私合同

{table(privacy_rows, ["关注点", "合同"])}

## 四、旧业务数据从哪到哪

{contract.get('data_flow') if isinstance(contract, dict) and contract.get('data_flow') else blank_note("数据流说明", "在机器平面写清一份数据流（machine/facts/data_contract.yaml）")}

## 五、旧业务关键参数为什么这么定

当前值和改哪里在 `06_运维手册.md`，这里只讲**为什么是这个值**。

{table(param_rows, ["参数", "为什么定这个值"],
       empty=blank_note("参数设计说明", "在机器平面登记参数及其意图（machine/facts/config.yaml）"))}

## 六、旧业务数据长什么样

{table(ent_rows, ["数据", "关键字段", "主键"],
       empty=blank_note("数据结构", "在机器平面写清数据契约（machine/facts/data_contract.yaml）"))}
"""
    return body


def render_04(facts: Path, canonical):
    flows = load_json(facts / "flows.json", {})
    main_rows = [
        (s.get("step", "?"), s.get("who", ""), s.get("do", ""), s.get("out", ""))
        for s in flows.get("main", [])
    ]
    authorization = canonical["owner_authorization"]["interpretation"]
    domain_rows = [
        (area, "、".join(f"`{req_id}`" for req_id in req_ids))
        for area, req_ids in group_requirement_ids(canonical["requirements"]).items()
    ]
    body = f"""{GENERATED}
<!-- 事实源：machine/canonical_facts.yaml（使用授权/事实域索引）；machine/facts/flows.json（旧业务流程） -->
<!-- 上限 150 行 -->

# 操作流程

授权边界来自 v1.5.2 合同；旧业务实际流程继续由独立事实源渲染。

## 一、v1.5.2 使用授权边界

{chr(10).join(f"- {item}" for item in authorization)}

## 二、v1.5.2 合同域索引

下表只按 Canonical Facts 的首次出现顺序建立导航，不推断尚未写入机器平面的步骤顺序。

{table(domain_rows, ["事实域", "需求 ID"])}

## 三、旧业务主流程

每一步是谁、做什么、产出什么。数字规则在 `03_口径字典.md`。

{table(main_rows, ["第几步", "谁", "做什么", "产出"],
       empty=blank_note("操作流程", "把业务流程写进机器平面（machine/facts/flows.json）"))}
"""
    return body


def render_05(facts: Path, runs_dir: Path, canonical, trace_documents, release_policy):
    plan = load_json(facts / "plan.json", {})
    acceptance = load_json(facts / "acceptance.json", {})
    runs = []
    if runs_dir.is_dir():
        for f in sorted(runs_dir.glob("*.json")):
            data = load_json(f, [])
            runs.extend(data if isinstance(data, list) else [data])

    now = " · ".join(x for x in [plan.get("stage"), plan.get("phase"),
                                 plan.get("task")] if x) or None
    owner = plan.get("owner")
    acc_rows = [(a.get("id", "?"), a.get("criteria", ""), a.get("status", ""))
                for a in acceptance.get("items", [])]
    run_rows = [(r.get("run_id", "?"), r.get("action", ""), r.get("result", ""))
                for r in runs[-5:]]
    trace_by_requirement = {
        row["requirement_id"]: row for row in trace_documents["trace_rows"]
    }
    execution_rows = []
    for requirement in canonical["requirements"]:
        row = trace_by_requirement[requirement["id"]]
        task_ids = " ".join(f"`{task_id}`" for task_id in row["task_ids"].split(";") if task_id)
        execution_rows.append(
            (
                f"`{row['requirement_id']}`",
                f"`{row['acceptance_id']}`",
                f"`{row['oracle_threshold']}`",
                task_ids,
                f"`{row['test_id']}`",
                f"`{row['artifact']}`",
                f"`{row['owner']}`",
            )
        )

    gate_rows = [
        (
            f"`{row['gate']}`",
            "；".join(f"`{requirement}`" for requirement in row["requires"]),
        )
        for row in release_policy["promotion_gates"]
    ]

    this_round = (f"**在做：** {now}\n\n**负责：** {owner or '待定'}"
                  if now else blank_note("当前任务", "把这一轮的计划写进机器平面（machine/facts/plan.json）"))

    body = f"""{GENERATED}
<!-- 事实源：machine/canonical_facts.yaml、acceptance_contract.yaml、task_graph.yaml、release_policy.yaml、traceability.csv（v1.5.2 验收追踪/发布门）；machine/facts/plan.json、acceptance.json、runs/*.json（旧业务执行状态） -->
<!-- 上限 100 行 -->

# 执行与验收

本文件只展开执行与验收映射；需求陈述见 `01_产品需求.md`，指标见 `03_口径字典.md`。

## 一、v1.5.2 需求验收追踪

下表按 Canonical Facts 的需求顺序，机械投影唯一主 Acceptance、Oracle、Task、Test、Artifact 与 Owner。完整字段保留在机器平面；`check_traceability.py` 对 49 条映射失败即关闭。

{table(execution_rows, ["需求 ID", "主 Acceptance", "Oracle 阈值", "Task", "Test", "Artifact", "Owner"])}

## 二、v1.5.2 晋级门（由发布策略生成；未知不晋级）

{table(gate_rows, ["门", "必要条件"])}

## 三、旧业务这一轮在做什么

{this_round}

## 四、旧业务怎么算做完

{table(acc_rows, ["编号", "达成标准", "状态"],
       empty=blank_note("验收标准", "把这一轮的验收标准写进机器平面（machine/facts/acceptance.json）"))}

## 五、旧业务最近 5 条运行记录

{table(run_rows, ["记录", "做了什么", "结果"],
       empty="> 还没有运行记录。每完成一步会自动追加一条，这里就有了。")}
"""
    return body


def render_06(facts: Path, project_name: str, canonical):
    config = load_yaml_or_json(facts / "config.yaml", {})
    ops = load_json(facts / "ops.json", {})
    changelog = load_json(facts / "changelog.json", [])

    cfg = config if isinstance(config, dict) and "_raw" not in config else {}
    param_rows = [(k, v.get("value", "") if isinstance(v, dict) else v,
                   v.get("where", "") if isinstance(v, dict) else "")
                  for k, v in cfg.get("parameters", {}).items()] if cfg else []
    err_rows = [(e.get("symptom", "?"), e.get("cause", ""), e.get("fix", ""))
                for e in ops.get("troubleshooting", [])]
    # changelog.json 约定新条目在前（insert(0)）——取前 10 条即最新 10 条。
    # 曾用 [-10:]（列表尾＝最旧）：条目数≤10 时两种切片等价、门恒绿，第 11 条起最新条目被静默隐藏。
    cl_rows = [(c.get("version", "?"), c.get("date", ""), c.get("summary", ""))
               for c in changelog[:10]]
    # 运维三节同样吃 facts：改 ops.json 就自然反映到手册，不手改渲染件
    rb = ops.get("runbook", {}) if isinstance(ops, dict) else {}
    run_rows = [(r.get("场景", "?"), r.get("怎么做", "")) for r in rb.get("服务启停", [])]
    bak_rows = [(r.get("对象", "?"), r.get("去哪", "")) for r in rb.get("备份", [])]
    chk_rows = [(r.get("查什么", "?"), r.get("怎么查", "")) for r in rb.get("断链自检", [])]
    go_rows = [(r.get("步", "?"), r.get("动作", ""), r.get("不做会怎样", ""))
               for r in rb.get("上线清单", [])]
    ops_areas = {"持久化", "可靠性", "安全", "运营"}
    ops_groups = group_requirement_ids([
        row for row in canonical["requirements"] if row["area"] in ops_areas
    ])
    ops_contract_rows = [
        (area, "、".join(f"`{req_id}`" for req_id in req_ids))
        for area, req_ids in ops_groups.items()
    ]

    body = f"""{GENERATED}
<!-- 事实源：machine/canonical_facts.yaml（运维合同索引）；machine/facts/config.yaml、ops.json、changelog.json（旧业务运行快照） -->
<!-- 上限 200 行 -->

# 运维手册

v1.5.2 运维要求只在此建立需求索引；当前可执行方式仍以旧业务机器事实为准。

> 旧业务快照含与 v1.5.2 公开目标冲突的登录墙/私有入口步骤，仅供历史运行取证，
> 不得作为 v1.5.2 发布指令；交付合同以 `01_产品需求.md` 为准。

## 一、v1.5.2 运维合同索引

需求陈述与指标分别见 `01_产品需求.md`、`03_口径字典.md`；本表不复制合同正文。

{table(ops_contract_rows, ["事实域", "需求 ID"])}

## 二、怎么跑

改完机器平面，按顺序跑这三条，让人类平面刷新并过关：

```bash
python3 machine/tools/render_human.py            # 先渲染人类平面
python3 machine/tools/check_doc_budget.py        # 体积、中文、纯净三道门
python3 machine/tools/check_blocker_stop.py      # 阻塞重审门
```

## 三、旧业务参数在哪调

改一个参数要动哪个文件，都在这。为什么定这个值在 `02_系统架构.md`。

{table(param_rows, ["参数", "当前值", "改哪里"],
       empty=blank_note("参数清单", "在机器平面登记参数（machine/facts/config.yaml）"))}

## 四、旧业务报错了怎么办

{table(err_rows, ["遇到什么", "为什么", "怎么解决"],
       empty="> 还没有登记常见故障。踩过坑、解决了，就往 machine/facts/ops.json 里记一条，这里会自动列出，下次少走弯路。")}

## 五、旧业务服务启停

{table(run_rows, ["场景", "怎么做"],
       empty="> 还没登记启停方式。往 machine/facts/ops.json 的 runbook.服务启停 里记。")}

## 六、旧业务上线清单（顺序不能乱）

{table(go_rows, ["步", "动作", "不做会怎样"],
       empty="> 还没登记上线步骤。往 machine/facts/ops.json 的 runbook.上线清单 里记。")}

## 七、旧业务备份去哪

{table(bak_rows, ["对象", "去哪"],
       empty="> 还没登记备份去向。往 machine/facts/ops.json 的 runbook.备份 里记。")}

## 八、旧业务断链自检

一条链断了往往不报错，只是安静地不干活。定期照这张单子过一遍。

{table(chk_rows, ["查什么", "怎么查"],
       empty="> 还没登记自检项。往 machine/facts/ops.json 的 runbook.断链自检 里记。")}

## 九、旧业务最近 10 条变更

{table(cl_rows, ["版本", "时间", "改了什么"],
       empty="> 还没有变更记录。每次发版往 machine/facts/changelog.json 记一条，这里就有了。")}
"""
    return body


# ---------- 主流程 ----------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root)
    docs = root / "文档"
    facts = root / "machine" / "facts"
    runs = root / "machine" / "runs"
    project_name = root.resolve().name
    canonical = load_required_canonical(root)
    release_policy = load_required_release_policy(root)
    trace_documents, _trace_counts = load_and_validate(root)

    docs.mkdir(parents=True, exist_ok=True)
    rendered = {
        "00_我在哪.md": render_00(facts, canonical),
        "01_产品需求.md": render_01(facts, canonical),
        "02_系统架构.md": render_02(facts, canonical),
        "03_口径字典.md": render_03(facts, canonical),
        "04_操作流程.md": render_04(facts, canonical),
        "05_执行与验收.md": render_05(
            facts, runs, canonical, trace_documents, release_policy
        ),
        "06_运维手册.md": render_06(facts, project_name, canonical),
    }
    for name, body in rendered.items():
        (docs / name).write_text(body.rstrip() + "\n", encoding="utf-8")

    print(f"渲染完成：{len(rendered)} 个文件全部由机器平面生成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
