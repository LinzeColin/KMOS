"""经 DWS 以当前用户身份发送。

**发群默认关闭。** 测试期只发张霖泽个人；发群要用户明确授权后
把 DAILY_FUNDS_ALLOW_GROUP=1 打开并给出群 ID。
失败通知永远只发个人，任何时候都不进群——群里不加噪音。

三条血的教训，都写在代码里：

1. ``chat media upload`` 需要 DWS_CLIENT_ID / DWS_CLIENT_SECRET 环境变量，
   而 ``chat message send`` 不需要（它用已存的用户 token）。所以缺凭证时
   **文字发得出去、图发不出去**——正是第一次真发时踩的坑。

2. **dws 出错时退出码仍然是 0**，错误在返回体的 ``error`` 字段里。只看
   returncode 和 ``success`` 会把失败当成功。

3. 图就是这个东西本身。上传失败绝不能吞掉降级成纯文字然后报「已发送」——
   那会让人以为发出去了。宁可整条失败并告警。
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import time
from typing import Optional

DWS = os.path.expanduser("~/.local/bin/dws")
ENV_FILE = os.path.expanduser("~/.kmfa_daily_funds.env")
OWNER_USER_ID = "01256723246324629191"          # 张霖泽
PAYMENT_GROUP = "cidkU176W26z9HoAK9q5cb1lA=="   # 付款请示群

# 授权到期前多少天开始提醒。dws auth login 只能走 OAuth 人工授权，
# 没法无人值守续期，所以唯一能做的是别让它突然断掉。
AUTH_WARN_DAYS = 7


class SendError(RuntimeError):
    pass


def _env() -> dict:
    """把 ~/.kmfa_daily_funds.env 叠加到环境里。凭证不进仓库。"""
    env = dict(os.environ)
    if os.path.exists(ENV_FILE):
        for line in open(ENV_FILE, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


# 瞬时错误重试次数与间隔。
# 实测 2026-09-07 16:54 那次发送就栽在这上面：
#   获取访问令牌失败: Get "https://oapi.dingtalk.com/gettoken?..."
# 钉钉接口偶发不通，重试一次就好。无人值守不能因为一次网络抖动就整天不发。
RETRIES = 3
RETRY_SLEEP = 8

# 认得出「值得重试」的错。认不出的一律不重试——
# 把权限、参数、未授权这类确定性错误反复重试只是浪费时间并延后告警。
_TRANSIENT = ("获取访问令牌失败", "timeout", "timed out", "connection",
              "temporarily", "EOF", "reset by peer", "502", "503", "504")


def _is_transient(text: str) -> bool:
    low = (text or "").lower()
    return any(k.lower() in low for k in _TRANSIENT)


def _run(args, timeout: int = 120) -> dict:
    last = None
    for attempt in range(RETRIES):
        try:
            return _run_once(args, timeout)
        except SendError as exc:
            last = exc
            if attempt == RETRIES - 1 or not _is_transient(str(exc)):
                raise
            time.sleep(RETRY_SLEEP)
    raise last


def _run_once(args, timeout: int = 120) -> dict:
    rc = subprocess.run([DWS] + args + ["-f", "json", "-y"],
                        capture_output=True, text=True, timeout=timeout, env=_env())
    if rc.returncode != 0:
        raise SendError("dws %s 失败: %s" % (args[:3], rc.stderr.strip()[:200]))
    try:
        body = json.loads(rc.stdout)
    except ValueError:
        raise SendError("dws %s 返回不是 JSON: %s" % (args[:3], rc.stdout.strip()[:160]))
    # dws 出错时退出码是 0，错误只在这个字段里——必须单独查。
    err = body.get("error")
    if err:                     # dict 或字符串都算失败，只要不为空
        msg = err.get("message") if isinstance(err, dict) else err
        raise SendError("dws %s: %s" % (args[:3], str(msg)[:200]))
    if body.get("success") is False:
        raise SendError("dws %s 业务失败: %s" % (args[:3], str(body.get("errorMsg"))[:160]))
    return body


def dws_json(args, timeout: int = 120) -> dict:
    """只读查询（如拉群消息）也走同一套：exit 0 也要查 error 字段，瞬时错误重试。"""
    return _run(args, timeout)


def auth_status() -> dict:
    return _run(["auth", "status"], timeout=45)


def auth_ok() -> bool:
    try:
        return bool(auth_status().get("authenticated"))
    except Exception:
        return False


def auth_expiry() -> Optional[tuple]:
    """(refresh token 还剩几天, 到期时刻原文)。拿不到返回 None（当作未知，不误报）。"""
    try:
        raw = auth_status().get("refresh_expires_at") or ""
        exp = dt.datetime.fromisoformat(raw)
    except Exception:
        return None
    now = dt.datetime.now(exp.tzinfo) if exp.tzinfo else dt.datetime.now()
    return (exp - now).days, raw


def auth_expiry_notice() -> Optional[tuple]:
    """快到期时返回 (首报键, 提醒文案)，没到阈值返回 None。不在这里发——调用方按首报去重。

    键用到期时刻原文，不用剩余天数：天数每天变，拿它当键就成了每天报一次。
    重新登录必须人来点，自动化补不了；能做的只是别让它某天早上突然静默停摆。
    """
    got = auth_expiry()
    if got is None or got[0] > AUTH_WARN_DAYS:
        return None
    days, raw = got
    return ("auth_expiring:%s" % raw,
            "钉钉授权还有 %d 天到期，到期后资金日报会发不出去。\n在这台 Mac 上跑一次：dws auth login" % days)


def upload_image(path: str) -> str:
    body = _run(["chat", "media", "upload", "--file", path])
    result = body.get("result") or body
    for key in ("mediaId", "media_id", "id"):
        if result.get(key):
            return result[key]
    raise SendError("上传返回里没有 mediaId: %s" % str(body)[:160])


def resolve_target(*, to_group: bool) -> list:
    """公开入口：解析发送目标，未授权发群时抛错。

    调用方应该**在做任何工作之前**先调它——尤其是 dry-run。
    实测踩过：dry-run 在校验之前就 return 了，于是未授权的发群预演也「通过」，
    看起来一切正常，真发时才炸。
    """
    return _target(to_group)


def _target(group: bool) -> list:
    if not group:
        return ["--user", OWNER_USER_ID]
    if os.environ.get("DAILY_FUNDS_ALLOW_GROUP") != "1":
        raise SendError("发群未授权：DAILY_FUNDS_ALLOW_GROUP 未开启")
    gid = os.environ.get("DAILY_FUNDS_GROUP_ID") or PAYMENT_GROUP
    return ["--group", gid]


def send_card(png_path: str, text: str, *, to_group: bool = False) -> None:
    """先发图，再发文字摘要。

    图传不上去就整条失败——图是这个东西本身，只发文字等于没发。
    """
    target = _target(to_group)
    media_id = upload_image(png_path)          # 失败就抛，绝不降级
    _run(["chat", "message", "send"] + target
         + ["--msg-type", "image", "--media-id", media_id])
    _run(["chat", "message", "send"] + target + ["--text", text])


def send_notice(text: str) -> None:
    """不影响发送、但需要人知道的事——同样只发个人。调用方负责首报去重。"""
    _run(["chat", "message", "send", "--user", OWNER_USER_ID, "--text", text])


def send_failure(reason: str) -> None:
    """失败通知——只发个人，绝不进群。静默失败是本方案最大的风险。"""
    _run(["chat", "message", "send", "--user", OWNER_USER_ID,
          "--text", "资金日报未能发出：\n%s" % reason])
