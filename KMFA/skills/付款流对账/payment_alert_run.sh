#!/bin/bash
# 付款异常哨兵入口。automation 一字不改地调这一条路径。
#
# 这个壳只做一件事：把控制权交给 Python。业务逻辑一行都不放在 bash 里 ——
# 考勤那条线 2026-09-07 就是死在 macOS 自带 bash 3.2 的空数组展开上
# （ARGS[@]: unbound variable），而且只在走到那条分支时才炸。
set -u
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
exec /usr/bin/python3 payment_alert_main.py
