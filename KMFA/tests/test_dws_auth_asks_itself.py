# -*- coding: utf-8 -*-
"""dws 数据授权请求做成自愈：卡住了自己去请求，静默期内不连发。

**这是同一件事的第二版，第一版线上没生效。**

第一版做成环境变量 `KMFA_DWS_DATA_AUTH_REQUEST`。排查到最后：开关在 Coolify
里、compose 里也声明了、部署用的确实是含改动的提交，但技能从没进过台账——
变量看着设了、实际没到容器。**这正是 `KMFA_BOOT_SWEEP` 那次的重演。**
仓里那条「开关必须声明进 compose」的门禁只能验仓里写没写，
验不了「Coolify 有没有重新读 compose」。

也没做成 App 上的按钮：那个面匿名可达，而「给 Owner 的钉钉弹窗」被反复触发
就是骚扰——**不该为了省事开一个陌生人能按的门。**

所以判据回到系统自己身上：upstream-archive 红着 = 授权断了 = 去请求一次；
外加静默期，防止技能一直红就一直弹。
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "KMFA/tools/should_request_dws_auth.py"
sys.path.insert(0, str(REPO / "KMFA/tools"))

import should_request_dws_auth as decider  # noqa: E402

NOW = "2026-07-29T16:00:00+08:00"


def _ledger(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "ledger.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                 encoding="utf-8")
    return p


def _decide(tmp_path, rows, *, state_ts: str | None = None, now: str = NOW,
            outcome: str = "AUTH_REQUESTED"):
    """state_ts 默认写成**带成功凭据**的戳记。

    2026-07-29 改：裸时间戳现在不算静默期（它分不出「请求成功过」和「只是判过」，
    而后者曾把系统锁死 6 小时）。所以要测静默期本身，就得给它一个真凭据。
    """
    ledger = _ledger(tmp_path, rows)
    state = tmp_path / "last_request"
    if state_ts:
        decider.write_stamp(state, now=datetime.fromisoformat(state_ts), outcome=outcome)
    return decider.decide(ledger=ledger, state=state, now=datetime.fromisoformat(now))


BLOCKED = {"skill": "upstream-archive", "rc": 1, "ts": "2026-07-29T15:00:00+08:00"}
HEALTHY = {"skill": "upstream-archive", "rc": 0, "ts": "2026-07-29T15:00:00+08:00"}


def test_it_asks_when_the_chain_is_actually_blocked(tmp_path):
    ok, why = _decide(tmp_path, [BLOCKED])
    assert ok, why


def test_it_stays_quiet_when_auth_is_working(tmp_path):
    """授权通着还弹窗 = 纯骚扰。"""
    ok, why = _decide(tmp_path, [HEALTHY])
    assert not ok
    assert "成功" in why, why


def test_it_does_not_ask_before_the_skill_has_ever_run(tmp_path):
    """没有「卡住」的证据就不打扰 Owner——沉默不等于故障。"""
    ok, why = _decide(tmp_path, [{"skill": "dws-keepalive", "rc": 0, "ts": NOW}])
    assert not ok
    assert "还没跑过" in why, why


def test_the_quiet_period_stops_it_from_spamming(tmp_path):
    """**本文件的正主。** 技能会一直红；不能因此每 10 分钟弹一次。"""
    ok, why = _decide(tmp_path, [BLOCKED], state_ts="2026-07-29T14:00:00+08:00")
    assert not ok, "静默期内又弹了一次"
    assert "静默" in why or "间隔" in why, why


def test_after_the_quiet_period_it_asks_again(tmp_path):
    """授权是会过期的。静默期一过就该再问一次，不能问一次就永远闭嘴。"""
    ok, why = _decide(tmp_path, [BLOCKED], state_ts="2026-07-29T05:00:00+08:00")
    assert ok, why


def test_a_corrupt_state_file_does_not_wedge_it_shut(tmp_path):
    """状态文件坏了不能变成「永远不再请求」——那会让整条链无声地卡死。"""
    ledger = _ledger(tmp_path, [BLOCKED])
    state = tmp_path / "last_request"
    state.write_text("不是时间也不是 JSON", encoding="utf-8")
    ok, why = decider.decide(ledger=ledger, state=state, now=datetime.fromisoformat(NOW))
    assert ok, why


def test_the_quiet_period_has_a_lower_bound():
    """没有下界 = 技能红着就一直弹，那是骚扰。"""
    assert 1.0 <= decider.MIN_INTERVAL_HOURS <= 24.0


def test_the_reason_is_always_printed(tmp_path):
    """「没请求」和「请求了但没反应」在日志里长得一样——理由必须写出来。"""
    ledger = _ledger(tmp_path, [HEALTHY])
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--ledger", str(ledger),
         "--state", str(tmp_path / "s"), "--now", NOW],
        capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    assert proc.stderr.strip(), "拒绝了却没说为什么"


def test_mark_only_writes_when_it_actually_decides_to_ask(tmp_path):
    """判成「不请求」却写下时间戳，会把下一次真该请求的时机推掉。"""
    ledger = _ledger(tmp_path, [HEALTHY])
    state = tmp_path / "s"
    subprocess.run(
        [sys.executable, str(TOOL), "--ledger", str(ledger), "--state", str(state),
         "--now", NOW, "--mark"], capture_output=True, text=True, check=False)
    assert not state.exists(), "没请求却盖了时间戳——把下一次真请求推掉了"


def test_the_dead_env_switch_is_gone():
    """**不管用的开关比没有更糟**——真出事时会去按它。

    KMFA_DWS_DATA_AUTH_REQUEST 线上实证不生效，整条路必须删干净，
    不许在 entrypoint 或 compose 里留下半截。
    """
    entry = (REPO / "KMFA/deploy/skills-runtime/entrypoint.sh").read_text(encoding="utf-8")
    compose = (REPO / "KMFA/deploy/coolify/docker-compose.yml").read_text(encoding="utf-8")
    assert 'if [ "${KMFA_DWS_DATA_AUTH_REQUEST:-0}" = "1" ]' not in entry, \
        "entrypoint 里还留着那个不生效的开关"
    assert "KMFA_DWS_DATA_AUTH_REQUEST:" not in compose, "compose 里还留着它"


def test_every_decision_reaches_the_ledger():
    """**本轮最重要的一条。** entrypoint 必须**无条件**调 run_skill.sh。

    上一版把闸放在 entrypoint 里：判据说「不跑」，整件事就只在 cron.log 留一行，
    而 cron.log 谁都读不到——Coolify 的 logs 返空、exec 返回 404、
    /api/排程健康 在 Access 后面。于是线上表现成「什么都没发生」，
    跟故障完全分不开。**为此浪费了一次部署。**

    仓里本来就写着这条经验（run_skill.sh 的回传注释：「回传后验证就是一条
    gh api，不必登录也不必进容器」）——上一版是我自己把它破坏了。
    """
    entry = (REPO / "KMFA/deploy/skills-runtime/entrypoint.sh").read_text(encoding="utf-8")
    assert "run_skill.sh dws-data-auth" in entry, "技能没被调用"
    assert "should_request_dws_auth.py" not in entry, (
        "闸又回到 entrypoint 里了——它一旦说「不跑」，决定就只落在读不到的 cron.log，"
        "线上跟故障分不开")

    runner = (REPO / "KMFA/deploy/skills-runtime/run_skill.sh").read_text(encoding="utf-8")
    assert "--only-if-blocked" in runner, "闸没交给技能——那就是无条件弹窗了"


def test_the_gate_lives_inside_the_skill():
    """闸在技能内部，且「按设计没请求」必须是 rc=0。

    判成非零会让心跳天天假红，而天天亮的红灯最后一定被当噪音关掉——
    真出事那次跟着被忽略。
    """
    tool = (REPO / "KMFA/tools/automation/dws_data_auth_request.py").read_text(encoding="utf-8")
    assert "--only-if-blocked" in tool, "技能不认这个参数"
    assert "NOT_REQUESTED_BY_DESIGN" in tool, "没有「按设计没请求」这个状态"
    idx = tool.index("NOT_REQUESTED_BY_DESIGN")
    assert "return 0" in tool[idx:idx + 200], "按设计没请求却报了非零——那是假红"


def test_the_quiet_period_stamp_is_written_only_after_a_real_request():
    """时间戳只在真发起之后写。没发起却盖时间戳，会把下一次真请求推掉。"""
    tool = (REPO / "KMFA/tools/automation/dws_data_auth_request.py").read_text(encoding="utf-8")
    stamp = tool.index("write_stamp(Path(args.state)")
    # 写时间戳这段必须在「真调用了授权命令」之后
    invoke = tool.index("rc, output = run(invocation")
    assert invoke < stamp, "还没真调用就盖了时间戳"


def test_the_trigger_does_not_depend_on_the_entrypoint_alone():
    """触发必须有一条**已证明能工作**的通道：cron。

    2026-07-29 试过两次 entrypoint，两次都没让技能进过台账：
      · v2 判据放 entrypoint 里 → 判「不跑」只在读不到的 cron.log 留一行
      · v3 判据搬进技能、entrypoint 无条件调 → **技能仍然没进过台账**，
        原因至今没定位到（容器内不可观测：logs 返空、exec 404、/api 在 Access 后）

    而 cron 是有实证的：dws-keepalive 12:20 准点跑过（`20 */4`）。
    所以判据不能只挂在 entrypoint 上——**一条没被证明过的通道，
    不该是唯一的通道**。
    """
    cron = (REPO / "KMFA/deploy/skills-runtime/crontab.txt").read_text(encoding="utf-8")
    line = next((l for l in cron.splitlines()
                 if "run_skill.sh dws-data-auth" in l and not l.lstrip().startswith("#")), None)
    assert line, "crontab 里没有 dws-data-auth——只剩 entrypoint 那条没被证明过的路"
    assert line.split()[0].startswith("*/"), f"不是周期性节拍：{line}"


def test_a_frequent_tick_does_not_mean_frequent_popups():
    """每 15 分钟跑一次 ≠ 每 15 分钟弹一次窗——闸在技能内部，静默期挡住连发。

    这条防的是「为了让它快点跑就把节拍调密，顺手把闸也放宽」。
    """
    runner = (REPO / "KMFA/deploy/skills-runtime/run_skill.sh").read_text(encoding="utf-8")
    assert "--only-if-blocked" in runner, "节拍密了却没有闸——那就是每 15 分钟骚扰一次"
    assert decider.MIN_INTERVAL_HOURS >= 1.0, "静默期太短，撑不住密节拍"


def test_the_skill_can_actually_show_up_on_the_health_page():
    """**这条是今天最贵的一课。**

    健康端点是 `for skill in sorted(SCHEDULE_CONTRACT)`——只输出**契约里有**的技能。
    dws-data-auth 一开始没登记进契约，于是它**哪怕一直在跑，端点也永远不显示它**。

    我据此连着两轮判定「技能没跑」，还为此改了两版触发方式（判据搬进技能、
    改走 cron）。**判据用了一个结构上就不可能显示该技能的面。**
    仓里那条 test_every_scheduled_skill_is_visible 是对的，
    但它只在技能**进了 crontab** 之后才管得着——我前两版只挂 entrypoint，
    正好从它下面绕了过去。

    所以这里补一条不依赖 crontab 的：只要这个技能存在，它就必须能在健康面上出现。
    """
    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    from app.main import SCHEDULE_CONTRACT, SKILL_MODULE  # noqa: PLC0415

    assert "dws-data-auth" in SCHEDULE_CONTRACT, (
        "技能没登记进 SCHEDULE_CONTRACT——健康端点按它取值，"
        "没登记就等于这个技能在页面上不存在，跑没跑永远看不见")
    assert "dws-data-auth" in SKILL_MODULE, "没归业务模块，驾驶舱分组里会掉出去"


# ── 静默期必须有凭据（2026-07-29 线上卡死在这里）───────────────────────────

def test_a_stamp_without_proof_does_not_buy_silence(tmp_path):
    """**本轮最贵的一条。**

    上一版的 `--mark` 在「判定该请求」时就盖戳，而不是在**真请求之后**。
    于是盖了戳、请求却没发出去，接下来 6 小时全被自己盖的戳拦住——
    端点只报 NOT_REQUESTED_BY_DESIGN，看上去一切正常，Owner 却永远收不到弹窗。
    **系统自己把自己锁死了，而且锁得毫无痕迹。**

    静默期存在的理由是「刚打扰过 Owner、别再打扰」。没请求成功，就没打扰过，
    也就不该买到安静。
    """
    ledger = _ledger(tmp_path, [BLOCKED])
    state = tmp_path / "s"
    decider.write_stamp(state, now=datetime.fromisoformat("2026-07-29T15:00:00+08:00"),
                        outcome="DECIDED_ONLY")
    ok, why = decider.decide(ledger=ledger, state=state,
                             now=datetime.fromisoformat(NOW))
    assert ok, f"没有成功凭据的戳记却买到了静默期——系统会把自己锁死：{why}"
    assert "没有成功请求的凭据" in why, why


def test_a_real_request_does_buy_silence(tmp_path):
    """真请求过就该安静——否则每 15 分钟弹一次就是骚扰。"""
    ledger = _ledger(tmp_path, [BLOCKED])
    state = tmp_path / "s"
    decider.write_stamp(state, now=datetime.fromisoformat("2026-07-29T15:00:00+08:00"),
                        outcome="AUTH_REQUESTED")
    ok, why = decider.decide(ledger=ledger, state=state,
                             now=datetime.fromisoformat(NOW))
    assert not ok, "真请求过还连发，那是骚扰"
    assert "AUTH_REQUESTED" in why, why


def test_the_legacy_bare_timestamp_is_not_trusted(tmp_path):
    """线上**此刻**就有一个旧格式的裸时间戳，它正是把系统锁死的那个。

    旧格式没有结局字段，分不出「请求成功过」和「只是判过」——
    分不出的时候必须当作没凭据，否则这次修复对线上那个戳记不起作用。
    """
    ledger = _ledger(tmp_path, [BLOCKED])
    state = tmp_path / "s"
    state.write_text("2026-07-29T15:00:00+08:00", encoding="utf-8")   # 旧格式
    ok, why = decider.decide(ledger=ledger, state=state,
                             now=datetime.fromisoformat(NOW))
    assert ok, f"旧的裸时间戳还在锁着——线上那个戳记不会被解开：{why}"


def test_awaiting_confirm_also_counts_as_asked(tmp_path):
    """命令阻塞超时通常意味着弹窗已推出、正等 Owner 点——那也是打扰过了。"""
    ledger = _ledger(tmp_path, [BLOCKED])
    state = tmp_path / "s"
    decider.write_stamp(state, now=datetime.fromisoformat("2026-07-29T15:00:00+08:00"),
                        outcome="AUTH_REQUESTED_AWAITING_CONFIRM")
    ok, _ = decider.decide(ledger=ledger, state=state, now=datetime.fromisoformat(NOW))
    assert not ok, "弹窗已推出却又推一次"


def test_only_the_requester_writes_a_proof_stamp():
    """凭据只能由**真发起的那一方**写。判据方写的戳记不许带成功结局。"""
    gate = (REPO / "KMFA/tools/should_request_dws_auth.py").read_text(encoding="utf-8")
    assert 'outcome="DECIDED_ONLY"' in gate, "判据方写了带成功结局的戳记——那又能锁死自己"
    tool = (REPO / "KMFA/tools/automation/dws_data_auth_request.py").read_text(encoding="utf-8")
    assert "write_stamp(" in tool, "发起方没写凭据——静默期永远不会生效，变成连发"
    assert "AUTH_REQUESTED" in tool
