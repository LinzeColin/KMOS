# -*- coding: utf-8 -*-
"""容器里读的每个开关，都必须在 compose 里声明——否则它到不了容器。

Compose 的语义容易记反：shell 环境里的变量**只能**用于 compose 文件里的 `${}` 插值，
不列在服务的 `environment:` 下就**不会传进容器**。所以「在 Coolify 里设了个变量」
和「容器里读得到它」是两回事。

这个坑在 KMFA 出现过两次，都是同一种表现——**开关看着有，其实不管用**：

  1. `KMFA_NOTIFICATION_TARGETS` 只加进 entrypoint 的合成清单、漏在 compose 里。
     靠 `run_skill.sh` 的默认值 `personal` 兜住了；默认值恰好是安全值，
     但那是运气不是设计（compose 里那段注释就是为它写的）。
  2. `KMFA_BOOT_SWEEP`（2026-07-28）：压测把线上打下线时我拿它当急停，
     在 Coolify 置 0 —— **它从没进过容器**。那晚站点稳下来是冷却闸的作用，
     不是这个开关。**一个不管用的急停比没有更糟**：真出事时会去按它，
     按完以为止住了，然后继续找别的原因。

所以这道门禁不是「补一个变量」，是把「读的 ≠ 传的」这件事变成会红的东西。
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "KMFA/deploy/coolify/docker-compose.yml"
ENTRY = REPO / "KMFA/deploy/skills-runtime/entrypoint.sh"
RUN_SKILL = REPO / "KMFA/deploy/skills-runtime/run_skill.sh"

# 这些不是「从容器外传进来的开关」，不该要求 compose 声明：
#   · 由 entrypoint / run_skill 自己 export 出来的（对内传递，不来自外部）
#   · 容器内固定路径、由代码自己钉死的
#   · Docker/系统本来就给的
EXEMPT = {
    "PATH", "HOME", "SHELL", "PWD", "TERM", "TZ",
    # run_skill.sh 自己 export 给子进程的
    "KMFA_ATTENDANCE_RUNTIME_DIR", "KMFA_FUND_VISION_OCR_COMMAND",
    "PYTHONPATH", "KMFA_SWEEP_RUN",
    # entrypoint 内部自己算出来的
    "KMFA_BACKUP_SSH_KEY_FILE", "BACKUP_KEY_FILE", "CRON_D",
}


def _read_switches(path: Path) -> set[str]:
    """抽出「从环境里**读**」的变量名：`${VAR:-...}` 或 `$VAR` 的读取用法。

    只认 KMFA_ 前缀与全大写下划线名，且必须是带默认值的读取形式
    （`${VAR:-default}`）——那正是「外部可传入的开关」的写法。
    """
    text = path.read_text(encoding="utf-8")
    # 去掉注释行，注释里举例说明的变量名不算真读
    body = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    return {m for m in re.findall(r"\$\{(KMFA_[A-Z0-9_]+):-", body)}


def _compose_declared() -> set[str]:
    text = COMPOSE.read_text(encoding="utf-8")
    body = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    return set(re.findall(r"^\s+([A-Z][A-Z0-9_]*):\s", body, re.M))


def test_every_switch_the_container_reads_is_declared_in_compose():
    read = (_read_switches(ENTRY) | _read_switches(RUN_SKILL)) - EXEMPT
    declared = _compose_declared()
    missing = sorted(read - declared)
    assert not missing, (
        f"这些开关容器里读、compose 里没声明——**它们到不了容器**：{missing}。"
        "在 Coolify 里设了也没用，是哑开关。"
    )


def test_the_sweep_kill_switch_specifically_is_wired():
    """单独锚死这一个：它是急停，哑掉的代价最大。"""
    assert "KMFA_BOOT_SWEEP" in _compose_declared(), \
        "压测急停没在 compose 里声明——按下去不会有任何反应"
    assert "KMFA_BOOT_SWEEP" in _read_switches(ENTRY), \
        "entrypoint 不再读这个开关了——那 compose 里声明它就没意义，两边要一起改"


def test_the_default_keeps_the_sweep_on():
    """默认要开——默认关等于这套机制不存在，而它是 Owner 明确要的
    「所有 skill 主动压测，不等自然时间」。"""
    text = COMPOSE.read_text(encoding="utf-8")
    line = next(l for l in text.splitlines()
                if "KMFA_BOOT_SWEEP:" in l and not l.lstrip().startswith("#"))
    assert ":-1}" in line, f"默认值不是 1：{line.strip()}"
