# -*- coding: utf-8 -*-
"""一条规则都没检成，就不许报绿。

2026-07-28 本机用历史数据全量压测 13 个技能时抓到的第五个「绿的但没干活」：

  work-check-morning / work-check-evening 在云端跑了 9 次，**次次 rc=0、次次绿**。
  真跑一遍才看见输出里是：

      "rules_evaluated": []      ← 一条规则都没评
      "results": []              ← 零结果
      "notification_events": [{"issue_code": "ZIP_INPUT_MISSING", ...}]

  它的输入 `/opt/kmfa/data/DWS_Outputs.zip` **全仓搜下来没有任何东西会去生成**
  —— 没有 Dockerfile COPY、没有 compose 挂载、没有 entrypoint 下载，
  这个路径只出现在 run_skill.sh 的默认值里。也就是说线上那个文件从来没存在过。

  再往上一层：文件之所以造不出来，是上游归档拿不到聊天记录——
  钉钉侧 `chat/list_conversation_message_v2` 报 AUTH_PERMISSION_DENIED（连续 44 次失败）。
  于是一条因果链：**权限没授 → 归档拿不到聊天记录 → zip 永远不存在 →
  work-check 空转 → 但它报绿 → 没人知道**。绿灯把上游的权限问题盖了整整一段时间。

判据必须是「本该检查的东西检查成了没有」，不是「进程有没有崩」。
但也**不能矫枉过正**：本窗口本来就没有到期规则（周五规则在周二）是合法的空跑，
那种情况报红就是天天假红，最后一定被人关掉——那比不报还糟。
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

REPO = Path(__file__).resolve().parents[2]


def _run(*args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, "-m", "KMFA.tools.daily_routine_check.main", *args],
        cwd=REPO, capture_output=True, text=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"_stdout": proc.stdout, "_stderr": proc.stderr}
    return proc.returncode, payload


def _fresh_zip(path: Path, day: str) -> None:
    """一份「今天就有消息」的输入，用来证明正常情况下仍然绿。"""
    with zipfile.ZipFile(path, "w") as zf:
        for group, sender in (("付款请示群", "杨婷"), ("生产管理群", "黄婷")):
            zf.writestr(
                f"DWS_Outputs/{group}/chat_records/chat_records.csv",
                "group_name,open_message_id,message_time,sender_name,content,"
                "resource_count,resource_types\n"
                f"{group},{group}-m1,{day} 10:00:00,{sender},资金账户明细表 可用资金合计 800000,0,\n",
            )
            zf.writestr(
                f"DWS_Outputs/{group}/_manifest/manifest.csv",
                "group_name,message_id,message_time,sender_name,resource_type,"
                "output_path,sha256,status\n"
                f"{group},{group}-m1,{day} 10:00:00,{sender},image,"
                f"files/x/{group}.png,sha-{group},downloaded\n",
            )


def test_missing_input_zip_must_be_red():
    """线上那个真场景：输入路径根本不存在。

    这**正是**云端跑了 9 次的那一种，它当时返回 0。
    """
    rc, out = _run("--input-zip", "/opt/kmfa/data/DWS_Outputs.zip",
                   "--trigger-window", "morning_1135", "--dry-run",
                   "--date", "2026-07-28")
    assert rc != 0, (
        "输入源整个不存在还返回 0——线上就是这么绿了 9 次的。"
        f"实际 rc={rc}"
    )
    assert out.get("failure_code") == "ZIP_INPUT_MISSING", \
        f"失败码没上到日志里，台账就还是查不动：{out.get('failure_code')!r}"


def test_all_rules_blocked_by_stale_source_must_be_red():
    """源在、但全部到期规则都因为过期被堵——一条也没检成，同样不算干了活。"""
    with TemporaryDirectory() as tmp:
        z = Path(tmp) / "DWS_Outputs.zip"
        _fresh_zip(z, "2026-07-01")          # 消息停在 7/1，检查日 7/28 → 全部过期
        rc, out = _run("--input-zip", str(z), "--trigger-window", "morning_1135",
                       "--dry-run", "--date", "2026-07-28")
    assert out.get("rules_evaluated") == [], "前提变了：这份输入本该把规则全堵住"
    assert rc != 0, f"到期规则一条都没检成却返回 0，实际 rc={rc}"
    assert out.get("failure_code") == "ALL_RULES_BLOCKED_BY_SOURCE"


def test_a_healthy_run_stays_green():
    """源新鲜、规则真评过——必须还是绿。修红不能把好路径一起弄红。"""
    with TemporaryDirectory() as tmp:
        z = Path(tmp) / "DWS_Outputs.zip"
        _fresh_zip(z, "2026-07-28")
        rc, out = _run("--input-zip", str(z), "--trigger-window", "morning_1135",
                       "--dry-run", "--date", "2026-07-28")
    assert out.get("rules_evaluated"), "前提变了：这份输入本该有规则被评到"
    assert rc == 0, f"正常跑被误判成红了，rc={rc}"
    assert "failure_code" not in out, "绿的时候不该带失败码"


def test_a_window_with_nothing_due_stays_green():
    """本窗口没有到期规则 = 合法空跑，不是失败。

    这条是防「矫枉过正」的锚：周五才跑的规则在周二没到期，
    这种空跑天天报红，红灯就会被当噪音关掉——那比不报还糟。

    判据是纯函数，直接喂进去测——比造一份「恰好没规则到期」的输入稳。
    """
    from KMFA.tools.daily_routine_check.main import run_exit_code

    assert run_exit_code(input_missing=False, rules_due=0, rules_evaluated=0) == (0, None), \
        "本窗口无规则到期是合法空跑，不该判红"


def test_the_exit_code_distinguishes_the_two_ways_of_doing_nothing():
    """「源没了」和「源在但全过期」是两种成因，失败码必须分得开——
    合成一个码就退回到「rc=5 有十来种成因」那种查不动的状态。"""
    from KMFA.tools.daily_routine_check.main import run_exit_code

    missing = run_exit_code(input_missing=True, rules_due=2, rules_evaluated=0)
    blocked = run_exit_code(input_missing=False, rules_due=2, rules_evaluated=0)
    assert missing[0] != 0 and blocked[0] != 0
    assert missing[1] == "ZIP_INPUT_MISSING"
    assert blocked[1] == "ALL_RULES_BLOCKED_BY_SOURCE"
    assert missing != blocked, "两种成因用了同一个码，等于没分"

    partial = run_exit_code(input_missing=False, rules_due=3, rules_evaluated=1)
    assert partial == (0, None), "评到一条就算干了活，部分受阻不判红"


def test_the_phantom_production_path_is_not_referenced_anymore():
    """`/opt/kmfa/data/DWS_Outputs.zip` 没有任何东西会去生成它。

    留着这个默认值，等于把「源没配」伪装成「源配好了只是没数」。
    真源应当来自上游归档落地的目录；配不上就该显式报源缺失。
    """
    run_skill = (REPO / "KMFA/deploy/skills-runtime/run_skill.sh").read_text(encoding="utf-8")
    # 只看可执行部分：注释里写明「为什么删掉它」是该留的，那不是引用。
    code = "\n".join(
        line for line in run_skill.splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "/opt/kmfa/data/DWS_Outputs.zip" not in code, \
        "还在指着那个从来没被生成过的幽灵路径"
    assert "ZIP_INPUT_MISSING" in code, "找不到输入时没有显式报源缺失，又会退回静默空跑"
