"""采集：生产管理群的人员表图片 + 钉钉打卡结果。全部经 dws，不直连钉钉 API。"""
from __future__ import annotations
import json, subprocess, time
from datetime import datetime, timedelta
from pathlib import Path

class DwsUnavailable(RuntimeError):
    """钉钉网关这一趟够不着。不是「查到的结果是空」，是「根本没查成」。"""

class Dws:
    def __init__(self, exe: str, timeout: int = 180, tries: int = 3):
        self.exe, self.timeout, self.tries = exe, timeout, tries

    def json(self, args: list[str]):
        """够不着就抛 DwsUnavailable，绝不把它降级成「空结果」返回。

        2026-09-15 实测：`dws` 连 mcp-gw.dingtalk.com 会成串地失败 ——
        一个 20 次的窗口里 11 次 stdout 全空、退出码 1，而 JSON 里
        errorCode / errorMsg 都是 null；换个时间点又连着 24 次全成。
        是阵发性的网关抖动，跟人数、天数、超时设置都无关。

        旧写法只看 stdout 解不解得出 JSON，解不出就 return None，于是：
          · messages() 返回 []  →  判「群里今天没有人员表」→ 公开点发布人的名，而他发了
          · punches()  返回 []  →  判「所有人都没打卡」→ 要么整片点名补卡，
                                   要么走「全公司无人打卡 = 非工作日」那条路静默不发
        三种输出都是错的，而且一个告警都没有。**「够不着」必须是异常，不是空集。**
        退出码是唯一可信的分辨依据（JSON 里那两个字段在失败时也是 null）。
        """
        last = ""
        for i in range(self.tries):
            p = subprocess.run([self.exe] + args + ["-f", "json"],
                               capture_output=True, text=True, timeout=self.timeout)
            if p.returncode == 0:
                try:
                    return json.loads(p.stdout)
                except Exception:
                    # 退出码 0 但解不出 JSON —— 真·空/异常响应，交给调用方按空处理。
                    return None
            last = (p.stderr or "")[:200].replace("\n", " ")
            if i + 1 < self.tries:
                time.sleep(2 * (i + 1))         # 2s、4s，阵发一般几十秒内自己好
        raise DwsUnavailable(f"dws {' '.join(args[:3])} 连试 {self.tries} 次都失败: {last}")

    def messages(self, group: str, since: str) -> list[dict]:
        """翻页拉取群消息。hasMore 时用边界 createTime 续页。"""
        out, seen, cursor = [], set(), since
        for _ in range(60):
            d = self.json(["chat", "message", "list", "--group", group,
                           "--time", cursor, "--direction", "newer"])
            if not d or not d.get("success"):
                break
            ms = (d.get("result") or {}).get("messages") or []
            new = [m for m in ms if m.get("openMessageId") not in seen]
            for m in new:
                seen.add(m["openMessageId"])
            out += new
            if not (d["result"].get("hasMore") and new):
                break
            cursor = max(m["createTime"] for m in ms)
        return out

    def download(self, group: str, msg_id: str, res_id: str, dest: Path) -> bool:
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([self.exe, "chat", "message", "download-media",
                        "--type", "mediaId", "--resource-id", res_id,
                        "--message-id", msg_id, "--open-conversation-id", group,
                        "--output", str(dest)],
                       capture_output=True, timeout=self.timeout)
        return dest.exists() and dest.stat().st_size > 1000

    def punches(self, user_ids: list[str], start: str, end: str) -> list[dict]:
        """attendance check result —— 一次最多 100 人。
        注意：attendance record get 对本 corp 恒返回空，不要用它判断有无打卡。"""
        out = []
        for i in range(0, len(user_ids), 100):
            d = self.json(["attendance", "check", "result",
                           "--users", ",".join(user_ids[i:i + 100]),
                           "--start", start, "--end", end, "--limit", "500"])
            r = (d or {}).get("result")
            if isinstance(r, list):
                out += r
        return out

def find_table_images(dws: Dws, group: str, publishers: list[str],
                      day: str, workdir: Path) -> list[Path]:
    """取指定业务日当天由指定发布人发出的全部图片，按时间倒序（最新的先试）。"""
    since = (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    hits = []
    for m in dws.messages(group, since):
        if m.get("sender") not in publishers or not m.get("createTime", "").startswith(day):
            continue
        for res in (m.get("resources") or []):
            if res and res.get("resourceType") == "image":
                hits.append((m["createTime"], m["openMessageId"], res["resourceId"]))
    out = []
    for t, mid, rid in sorted(hits, reverse=True):
        p = workdir / f"{t[:10].replace('-','')}_{t[11:16].replace(':','')}.png"
        if dws.download(group, mid, rid, p):
            out.append(p)
    return out
