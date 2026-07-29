# -*- coding: utf-8 -*-
"""冷启动补发只许发生在业务窗口内。

这是**第二道门**。第一道是压测节拍（每 30 分钟挑最久没跑的技能），
已由 PR #282 关掉——压测跑一律强制 dry-run。

第二道在 entrypoint 的「冷启动重试失败技能」：它直接调
`run_skill.sh <skill>`，**没带 KMFA_SWEEP_RUN=1，所以投递是开的**。
于是 attendance-evening 只要失败过一次，之后**每次部署**都会在部署发生的
那个时刻真发一次考勤给 Owner——而部署时间是任意的，可能是凌晨三点。
当时没爆只是因为两个考勤技能恰好都是 rc=0、没进重试名单。**那是运气不是设计。**

这次**没有照抄** #282 的改法（把投递一律关掉）：
「补发一次失败的投递」本身可能正是想要的——晚间报告 17:31 挂了，18:30 补上
比不发好。错的从来不是「补发」，是「在任意时刻补发」。

所以判据是窗口。下面每一条测试都对着一件具体的坏事：
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "KMFA/tools/pick_coldstart_retries.py"
sys.path.insert(0, str(REPO / "KMFA/tools"))

import pick_coldstart_retries as picker  # noqa: E402

CRONTAB = """SHELL=/bin/sh
1  8  * * *   root /opt/runtime/run_skill.sh attendance-morning  >> /var/log/kmfa/cron.log 2>&1
31 17 * * *   root /opt/runtime/run_skill.sh attendance-evening  >> /var/log/kmfa/cron.log 2>&1
0  11 * * *   root /opt/runtime/run_skill.sh upstream-archive    >> /var/log/kmfa/cron.log 2>&1
*/30 * * * *  root SK=$(python3 pick_stalest_skill.py); run_skill.sh "$SK"
"""


def _fixture(tmp_path: Path, rows: list[dict]) -> tuple[Path, Path]:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                      encoding="utf-8")
    cron = tmp_path / "crontab.txt"
    cron.write_text(CRONTAB, encoding="utf-8")
    return ledger, cron


def _pick(tmp_path: Path, rows: list[dict], now: str):
    ledger, cron = _fixture(tmp_path, rows)
    return picker.pick(ledger=ledger, crontab=cron, now=datetime.fromisoformat(now))


FAILED_EVENING = {"skill": "attendance-evening", "rc": 5, "ts": "2026-07-29T17:31:10+08:00"}
FAILED_ARCHIVE = {"skill": "upstream-archive", "rc": 1, "ts": "2026-07-29T11:00:05+08:00"}


def test_the_three_am_deploy_does_not_push_attendance(tmp_path):
    """**本文件的正主。** 凌晨三点部署，不许把考勤补发出去。"""
    retry, skipped = _pick(tmp_path, [FAILED_EVENING], "2026-07-30T03:00:00+08:00")
    assert "attendance-evening" not in retry, "凌晨三点把考勤推给 Owner 了"
    assert any("attendance-evening" in s for s in skipped)


def test_a_reasonable_late_retry_still_happens(tmp_path):
    """18:30 补发 17:31 挂掉的晚间报告——这**正是**想要的，别一刀切掉。"""
    retry, _ = _pick(tmp_path, [FAILED_EVENING], "2026-07-29T18:30:00+08:00")
    assert "attendance-evening" in retry, "把有意义的补发也堵死了，那是过度修正"


def test_it_never_fires_before_the_anchor(tmp_path):
    """早于锚点补发 = 「晚间报告在早上发出去」，正是 #282 那个 bug 的形状。"""
    retry, skipped = _pick(tmp_path, [FAILED_EVENING], "2026-07-29T07:28:00+08:00")
    assert "attendance-evening" not in retry
    assert any("还没到今天的锚点" in s for s in skipped), skipped


def test_yesterdays_failure_is_not_resurrected(tmp_path):
    """补发一份**过期**报告比不发更糟：收到的人会以为那是今天的数。"""
    stale = {**FAILED_EVENING, "ts": "2026-07-26T17:31:10+08:00"}
    retry, skipped = _pick(tmp_path, [stale], "2026-07-29T18:00:00+08:00")
    assert "attendance-evening" not in retry
    assert any("不是今天" in s for s in skipped), skipped


def test_just_outside_the_grace_window_is_refused(tmp_path):
    """边界要真是边界：锚点 +3h 之内放行，之外拒绝。"""
    inside, _ = _pick(tmp_path, [FAILED_EVENING], "2026-07-29T20:30:00+08:00")
    outside, _ = _pick(tmp_path, [FAILED_EVENING], "2026-07-29T20:32:00+08:00")
    assert "attendance-evening" in inside, "17:31+3h=20:31，20:30 该放行"
    assert "attendance-evening" not in outside, "20:32 已过窗口，不该放行"


def test_skills_without_outward_delivery_retry_unconditionally(tmp_path):
    """窗口只管**会往外发东西**的那几个。别把普通技能的冷启动重试也拖慢。"""
    retry, _ = _pick(tmp_path, [FAILED_ARCHIVE], "2026-07-30T03:00:00+08:00")
    assert "upstream-archive" in retry, "把不发消息的技能也拦了——那是过度修正"


def test_an_unknown_anchor_fails_closed(tmp_path):
    """读不到锚点就不补发。不知道窗口的时候，「不发」是唯一安全的默认。"""
    ledger, cron = _fixture(tmp_path, [FAILED_EVENING])
    cron.write_text("# 排程里没有考勤行了\n", encoding="utf-8")
    retry, skipped = picker.pick(ledger=ledger, crontab=cron,
                                 now=datetime.fromisoformat("2026-07-29T18:00:00+08:00"))
    assert "attendance-evening" not in retry, "锚点未知却照发——fail open 了"
    assert any("读不到" in s for s in skipped), skipped


def test_a_broken_timestamp_fails_closed(tmp_path):
    """时间戳坏了 = 判不出是不是今天的失败 = 不许发。"""
    broken = {**FAILED_EVENING, "ts": "不是时间"}
    retry, skipped = _pick(tmp_path, [broken], "2026-07-29T18:00:00+08:00")
    assert "attendance-evening" not in retry
    assert any("解析不了" in s for s in skipped), skipped


def test_the_anchor_comes_from_the_crontab_not_a_hardcoded_table(tmp_path):
    """排程改了，窗口必须跟着改。两处各写一份必然漂移。"""
    ledger, cron = _fixture(tmp_path, [FAILED_EVENING])
    cron.write_text(CRONTAB.replace("31 17 * * *", "31 20 * * *"), encoding="utf-8")
    # 锚点搬到 20:31 之后，18:00 就变成「还没到锚点」
    retry, skipped = picker.pick(ledger=ledger, crontab=cron,
                                 now=datetime.fromisoformat("2026-07-29T18:00:00+08:00"))
    assert "attendance-evening" not in retry, "窗口没跟着 crontab 走——锚点被写死了"
    assert any("20:31" in s for s in skipped), skipped


def test_the_tick_line_is_not_mistaken_for_an_anchor(tmp_path):
    """`*/30` 那行没有业务锚点，不能被当成定点排程读进来。"""
    _, cron = _fixture(tmp_path, [])
    anchors = picker.scheduled_anchors(cron)
    assert anchors.get("attendance-evening") == (17, 31)
    assert "$SK" not in anchors and "SK" not in anchors, anchors


def test_the_skipped_reason_is_never_swallowed(tmp_path):
    """「因为在窗口外没发」和「什么也没发生」在日志里长得一样——必须写出来。"""
    ledger, cron = _fixture(tmp_path, [FAILED_EVENING])
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--ledger", str(ledger), "--crontab", str(cron),
         "--now", "2026-07-30T03:00:00+08:00"],
        capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", f"凌晨还是把它挑出来重试了：{proc.stdout}"
    assert "冷启动重试跳过" in proc.stderr, f"跳过理由被吞了：{proc.stderr!r}"
    assert "attendance-evening" in proc.stderr


def test_the_entrypoint_actually_uses_the_picker():
    """判据写好了但没接进 entrypoint = 白写。已经栽过一次（#273 的守卫）。"""
    entry = (REPO / "KMFA/deploy/skills-runtime/entrypoint.sh").read_text(encoding="utf-8")
    assert "pick_coldstart_retries.py" in entry, "entrypoint 没用上挑选器"
    # 旧的内联 python 必须真被换掉，不能留着并行跑
    assert 'if r.get("rc") not in (0, None):' not in entry, \
        "旧的内联挑选逻辑还在——两套并行，窗口判据会被绕过"


def test_the_two_skill_lists_share_one_definition():
    """时间锚定技能的名单只能有一份。两份必然漂移。"""
    from pick_stalest_skill import TIME_ANCHORED_DELIVERY_SKILLS  # noqa: PLC0415

    assert picker.TIME_ANCHORED_DELIVERY_SKILLS is TIME_ANCHORED_DELIVERY_SKILLS


def test_the_grace_window_has_an_upper_bound():
    """没有上界 = 回到「任意时刻补发」，等于没修。"""
    assert 0 < picker.LATE_GRACE_HOURS <= 12, \
        f"补发窗口 {picker.LATE_GRACE_HOURS}h 不合理"


def test_a_skipped_retry_writes_nothing_and_burns_no_slot(tmp_path):
    """跳过必须是**真的什么都没做**：不能留下一条会占掉当天去重名额的回执。

    这条是 Owner 点名要验的：改动前必须确认不会制造它要修的 bug。
    这里的修法根本不调用技能（跳过 = 不执行），所以不写任何回执；
    再加一道断言钉住 dry-run 状态本身也不算投递尝试。
    """
    sys.path.insert(0, str(REPO.parent))
    from KMFA.tools.dingtalk_attendance.notification_targets import (  # noqa: PLC0415
        DELIVERY_ATTEMPT_STATUSES,
    )
    from KMFA.tools.dingtalk_attendance.delivery_policy import (  # noqa: PLC0415
        DELIVERY_DISABLED_STATUS,
    )

    assert DELIVERY_DISABLED_STATUS not in DELIVERY_ATTEMPT_STATUSES

    ledger, cron = _fixture(tmp_path, [FAILED_EVENING])
    before = ledger.read_text(encoding="utf-8")
    picker.pick(ledger=ledger, crontab=cron,
                now=datetime.fromisoformat("2026-07-30T03:00:00+08:00"))
    assert ledger.read_text(encoding="utf-8") == before, "挑选器动了台账"
