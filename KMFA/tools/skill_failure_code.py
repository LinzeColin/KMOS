#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从技能日志里提取一个**可以公开的**失败码。

为什么需要它（2026-07-27 实测逼出来的）：
  考勤连续多天 rc=5，而 rc=5 只说明「跑完了但没投出去」——它对应十来种截然不同的原因
  （DWS 没登录 / 目标解析不出来 / 官方考勤对不平 / 发送接口报错……）。
  想知道是哪一种，唯一的通道是容器日志，而 Coolify 的 `exec` 返回 404、`logs` 返回空，
  `/api/排程健康` 又在 Access 后面，Owner 明令不登录。
  结果就是：**每天都失败，每天都不知道为什么**，只能靠改一版等一天看会不会变绿。
  一个月没修好考勤，根因不是考勤难修，是没有诊断通道。

公开边界怎么保证：
  日志里有员工姓名、打卡记录、客户名、金额，一个字都不能进公开端点。
  所以这里**不做脱敏**——脱敏是"尽量删掉坏东西"，删漏了就泄露。
  这里做的是**白名单构造**：只认那些形如 `NOT_SENT_DWS_AUTH_REQUIRED` 的机器状态令牌
  和形如 `TimeoutError` 的异常类名，并且强制整体匹配 `^[A-Za-z][A-Za-z0-9_]{2,60}$`。
  中文、空格、路径、数字串、金额一律构造不出来——不是被过滤掉，是压根进不来。
  拿不到就返回 `UNKNOWN`，宁可少说也不多说。

完整取证（日志尾巴）走私有库，不走公开端点——见 skill_ledger_uplink.py。
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

#: 状态令牌的两种合法形状。**正形状白名单**，不是"过滤掉坏的"——
#: 单测抓到过一次：宽泛的 `^[A-Za-z][A-Za-z0-9_]+$` 能让 `ghp_…` 这种令牌整条过关。
_UPPER_SNAKE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")   # NOT_SENT_DWS_AUTH_REQUIRED
_CAMEL = re.compile(r"^(?:[A-Z]{1,6}[a-z0-9]+)+$")               # HTTPError / TimeoutError
_CREDENTIAL = re.compile(r"^(?:gh[pousr]_|sk-|xox[bap]-)|^[A-Fa-f0-9]{24,}$")

#: 提取器扫描时先用它粗筛，最终裁决一律走 is_public_safe()。
PUBLIC_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,60}$")

UNKNOWN = "UNKNOWN"

#: JSON 结果里的状态字段。顺序即优先级：投递状态比总状态更具体，先取。
_STATUS_KEYS = ("notification_status", "status", "collection_status", "failure_code")

_JSON_STATUS = re.compile(
    r'"(?P<key>' + "|".join(_STATUS_KEYS) + r')"\s*:\s*"(?P<val>[A-Za-z][A-Za-z0-9_]{2,60})"')

#: traceback 末行：`module.ClassName: 中文说明` —— 只取类名，说明部分丢弃。
_EXC = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*\.)*(?P<cls>[A-Z][A-Za-z0-9_]{2,60})\s*:", re.M)

#: 一眼就知道没信息量的状态，不值得占据那一格。
_USELESS = {"OK", "SUCCESS", "COMPLETED", "SENT", "NOT_RUN", "PENDING", "RUNNING", "SKIPPED"}


def extract(text: str) -> str:
    """返回一个公开安全的失败码；提取不到返回 UNKNOWN。

    从**后往前**找：一次运行会打很多行，最后写下的状态才是决定退出码的那个。
    """
    hits = [m.group("val") for m in _JSON_STATUS.finditer(text)]
    for value in reversed(hits):
        if value.upper() not in _USELESS and is_public_safe(value):
            return value

    for match in reversed(list(_EXC.finditer(text))):
        cls = match.group("cls")
        # 只认真正像异常类的（Error/Exception/Failed 结尾），否则 `Note: 说明` 这种也会中。
        if cls.endswith(("Error", "Exception", "Failure", "Failed", "Timeout")) and is_public_safe(cls):
            return cls

    return UNKNOWN


def is_public_safe(code: str) -> bool:
    """公开端点发出去之前必须过这一关——不信任台账文件写了什么。

    白名单式判定：只有长得像状态令牌或异常类名的才放行，其余一律拒。
    凭据前缀与长十六进制串单独拒一次——它们理论上能拼成合法大写串。
    """
    if not code or not (3 <= len(code) <= 60) or _CREDENTIAL.search(code):
        return False
    if _CAMEL.match(code):
        return True
    if _UPPER_SNAKE.match(code):
        # 无下划线的长纯大写串不是状态名，是随机串——`FAILED` 放行，二十位大写块不放。
        return "_" in code or len(code) <= 12
    return False


def tail(text: str, lines: int = 40) -> str:
    """给私有库的取证尾巴。私有库可以有业务信息，但凭据一律不留。"""
    kept = text.splitlines()[-lines:]
    scrubbed = []
    for line in kept:
        # token/密钥形态：长串无空格的十六进制或 gh 前缀，直接抹掉再入私有库。
        line = re.sub(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|[A-Fa-f0-9]{32,})\b", "«已抹除凭据»", line)
        scrubbed.append(line[:400])
    return "\n".join(scrubbed)


def main() -> int:
    ap = argparse.ArgumentParser(description="从技能日志提取公开安全的失败码")
    ap.add_argument("log", help="日志文件路径；给 - 从 stdin 读")
    ap.add_argument("--tail", action="store_true", help="改为输出私有取证尾巴")
    a = ap.parse_args()
    if a.log == "-":
        text = sys.stdin.read()
    else:
        path = Path(a.log)
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    print(tail(text) if a.tail else extract(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
