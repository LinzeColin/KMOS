# -*- coding: utf-8 -*-
"""考勤归档根必须落在 app 也能读到的卷上。

这条门禁挡的是一个已经发生过的失效：`KMFA_ATTENDANCE_ARCHIVE_ROOT` 原默认
`/var/lib/kmfa/attendance` 是**纯容器内路径**——没有任何 volume 挂在那里。后果两条：

  · 容器重建，全部投递回执消失；
  · app 永远读不到，「考勤到底发出去没有」无从查证。

于是考勤能安静地一条不发而台账全绿，只能等 Owner 说「我没收到」才被发现。

修法是复用 `kmfa-logs`（skills 读写、app 只读的既有共享卷）。这个测试盯住它别再飘回去。
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "coolify" / "docker-compose.yml"
ENTRYPOINT = ROOT / "deploy" / "skills-runtime" / "entrypoint.sh"

#: app 服务只读挂了这个卷；归档根必须在它下面，app 才读得到。
SHARED_MOUNT = "/var/log/kmfa"


def _compose_text():
    assert COMPOSE.is_file(), f"缺 {COMPOSE}"
    return COMPOSE.read_text(encoding="utf-8")


def test_archive_root_is_declared_in_compose():
    """不显式声明就会退回镜像默认值，而默认值曾经是错的。"""
    assert "KMFA_ATTENDANCE_ARCHIVE_ROOT" in _compose_text()


def test_archive_root_sits_on_the_volume_the_app_can_read():
    text = _compose_text()
    match = re.search(r'KMFA_ATTENDANCE_ARCHIVE_ROOT:\s*"([^"]+)"', text)
    assert match, "compose 里没找到 KMFA_ATTENDANCE_ARCHIVE_ROOT 的值"
    assert match.group(1).startswith(SHARED_MOUNT + "/"), (
        f"归档根 {match.group(1)} 不在 {SHARED_MOUNT} 下——app 读不到，"
        f"「考勤发出去没有」就又变成无从查证")


def test_app_really_mounts_that_volume():
    """上一条依赖 app 确实挂了 kmfa-logs；这条防的是有人把挂载删了。"""
    text = _compose_text()
    assert re.search(rf"kmfa-logs:{re.escape(SHARED_MOUNT)}:ro", text), \
        "app 没有只读挂 kmfa-logs，公开回执端点会永远返回『读不到』"


@pytest.mark.parametrize("default", re.findall(
    r'KMFA_ATTENDANCE_ARCHIVE_ROOT:-([^}"\s]+)',
    ENTRYPOINT.read_text(encoding="utf-8") if ENTRYPOINT.is_file() else ""))
def test_entrypoint_fallback_is_also_on_the_shared_volume(default):
    """entrypoint 的兜底默认值同样不能指向没挂卷的路径——
    compose 万一漏配，兜底会静默把回执写进容器内存层。"""
    assert default.startswith(SHARED_MOUNT + "/"), \
        f"entrypoint 兜底默认 {default} 不在共享卷上"
