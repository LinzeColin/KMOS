"""采集：生产管理群的人员表图片 + 钉钉打卡结果。全部经 dws，不直连钉钉 API。"""
from __future__ import annotations
import json, subprocess
from datetime import datetime, timedelta
from pathlib import Path

class Dws:
    def __init__(self, exe: str, timeout: int = 180):
        self.exe, self.timeout = exe, timeout

    def json(self, args: list[str]):
        p = subprocess.run([self.exe] + args + ["-f", "json"],
                           capture_output=True, text=True, timeout=self.timeout)
        try:
            return json.loads(p.stdout)
        except Exception:
            return None

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
