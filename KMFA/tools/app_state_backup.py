#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KMFA App 状态面异地备份（TSK.KMFA 数据耐久）。

背景：App 自己写的状态（人工拍板事件 / 导出记录 / 重跑 / 审计）落在云服务器一块
命名卷 `kmfa-app-state`（SQLite + 若干 JSONL）。命名卷能扛「普通重部署 / Flag 回滚」，
但**扛不住整机损毁 / 卷被删**——没有异地副本就是单点。本工具把整个状态目录打成
一个带 sha256 的归档，推到 **GitHub 私有库 Private-Database**（异地、多副本、有版本）。
真实业务金额本就该只在私有库；App 状态含拍板引用，同样只进私有库，绝不进公开 KMOS。

用法（云端 cron 每日一跑；也可本地对样例目录自测往返）：
    backup  --state-dir /var/lib/kmfa/state     # 打包 → 推私有库 → 追加 manifest
    restore --out /var/lib/kmfa/state           # 取最新备份 → 解包还原
    list                                        # 列已有备份（时间/大小/sha 前缀）

凭据：环境变量 `KMFA_BACKUP_GH_TOKEN`（对 Private-Database 有 contents:write 的 GitHub token）。
未设置时 backup 走**降级**：只把归档写到本地 `--fallback-dir`（默认 /var/log/kmfa/backups，
命名卷内，能扛重部署但非异地），并明确告警「异地未激活」——不静默假装成功。
无 `gh` 依赖：直接走 GitHub REST（urllib），VPS 容器只需 python3 即可。
"""
import argparse, base64, hashlib, io, json, os, shutil, sqlite3, subprocess, sys, tarfile, tempfile, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

REPO_DEFAULT = "LinzeColin/Private-Database"           # REST(token)路径:入 Private-Database
SSH_REPO_DEFAULT = "LinzeColin/KMFA-App-State-Backup"  # git-SSH(部署密钥)路径:专用私有备份库(最小爆炸半径)
PREFIX = "kmfa-app-state"                      # 备份对象前缀
MANIFEST = "backups/kmfa-app-state-manifest.jsonl"
API = "https://api.github.com"
KEEP_LAST = 30                                 # git-SSH 路径保留最近 N 份(防仓无限膨胀)


def _bj_ts():
    """北京时间时间戳（业务锚 +0800，全年零漂移）。"""
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")


def _token():
    for k in ("KMFA_BACKUP_GH_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        v = os.environ.get(k)
        if v:
            return v.strip()
    return None


def _api(method, path, token, body=None, raw=False):
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        req.add_header("Content-Type", "application/json")
    last = None
    for attempt in range(4):                  # 瞬时错误指数退避 1/2/4s
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = r.read()
                return out if raw else (json.loads(out) if out else {})
        except urllib.error.HTTPError as e:
            if e.code in (404, 409, 422) and method in ("GET", "PUT"):
                return None if method == "GET" else _raise(e)
            last = e
        except urllib.error.URLError as e:
            last = e
        if attempt < 3:
            time.sleep(2 ** attempt)
    raise SystemExit(f"GitHub API 失败 {method} {path}: {last}")


def _raise(e):
    raise SystemExit(f"GitHub API {e.code}: {e.read().decode(errors='replace')[:300]}")


def _sqlite_consistent_bytes(path):
    """用 SQLite 在线备份 API 取**一致快照**——即便 app 正在写也不会抓到撕裂状态。
    源以只读打开（immutable 视角），备份到临时库再读回字节。失败则退回原始字节。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    tmp.close()
    try:
        src = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
        dst = sqlite3.connect(tmp.name)
        with dst:
            src.backup(dst)
        src.close(); dst.close()
        with open(tmp.name, "rb") as f:
            return f.read()
    except Exception:
        with open(path, "rb") as f:              # 兜底：直接原始拷贝（不理想但不丢）
            return f.read()
    finally:
        try: os.unlink(tmp.name)
        except OSError: pass


def _tar_state(state_dir):
    """把状态目录打成 tar.gz 字节。SQLite 走一致快照；JSONL 等追加文件直接读。"""
    if not os.path.isdir(state_dir):
        raise SystemExit(f"状态目录不存在：{state_dir}")
    buf = io.BytesIO()
    names = []
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for root, _dirs, files in os.walk(state_dir):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, state_dir)
                payload = _sqlite_consistent_bytes(full) if fn.endswith((".sqlite3", ".db", ".sqlite")) \
                    else open(full, "rb").read()
                ti = tarfile.TarInfo(name=rel)
                ti.size = len(payload); ti.mtime = 0; ti.mode = 0o644
                tar.addfile(ti, io.BytesIO(payload))
                names.append(rel)
    return buf.getvalue(), names


def _put_object(token, repo, path, data, msg):
    """PUT contents（内容寻址路径，幂等：已存在同 sha 则跳过）。"""
    existing = _api("GET", f"/repos/{repo}/contents/{path}", token)
    if existing and existing.get("sha"):
        return existing["sha"], False        # 已在库
    body = {"message": msg, "content": base64.b64encode(data).decode()}
    res = _api("PUT", f"/repos/{repo}/contents/{path}", token, body)
    return res["content"]["sha"], True


def _append_manifest(token, repo, record):
    cur = _api("GET", f"/repos/{repo}/contents/{MANIFEST}", token)
    prev = base64.b64decode(cur["content"]) if cur and cur.get("content") else b""
    if record["sha256"].encode() in prev:
        print("= manifest 已含该 sha256，不重复追加"); return
    newc = prev + (json.dumps(record, ensure_ascii=False) + "\n").encode()
    body = {"message": f"backup(kmfa): app-state {record['ts']}",
            "content": base64.b64encode(newc).decode()}
    if cur and cur.get("sha"):
        body["sha"] = cur["sha"]
    _api("PUT", f"/repos/{repo}/contents/{MANIFEST}", token, body)


def _read_manifest(token, repo):
    cur = _api("GET", f"/repos/{repo}/contents/{MANIFEST}", token)
    if not cur or not cur.get("content"):
        return []
    return [json.loads(l) for l in base64.b64decode(cur["content"]).decode().splitlines() if l.strip()]


def _resolve_ssh_key():
    """部署密钥来源（按优先级）：
      `KMFA_BACKUP_SSH_KEY_FILE`（已就位的 600 密钥文件路径；VPS 首选，entrypoint 已解码好）
      `KMFA_BACKUP_SSH_KEY`（私钥明文内容）
      `KMFA_BACKUP_SSH_KEY_B64`（私钥 base64——单行，便于经 env/Coolify 传递）
    返回 (key_path, is_temp) 或 None。"""
    kf = os.environ.get("KMFA_BACKUP_SSH_KEY_FILE")
    if kf and os.path.isfile(kf):
        return kf, False
    content = os.environ.get("KMFA_BACKUP_SSH_KEY")
    if not content:
        b64 = os.environ.get("KMFA_BACKUP_SSH_KEY_B64")
        if b64:
            try:
                content = base64.b64decode(b64).decode()
            except Exception:
                raise SystemExit("KMFA_BACKUP_SSH_KEY_B64 无法 base64 解码")
    if content:
        fd, path = tempfile.mkstemp(prefix="kmfa-bk-key-")
        with os.fdopen(fd, "w") as f:
            f.write(content if content.endswith("\n") else content + "\n")
        os.chmod(path, 0o600)
        return path, True
    return None


def _git(args, cwd, key_path):
    env = dict(os.environ)
    env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    env["GIT_TERMINAL_PROMPT"] = "0"
    r = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {args[0]} 失败：{(r.stderr or r.stdout)[:300]}")
    return r.stdout


def _git_ssh_backup(data, names, sha, ts, repo, key_path):
    """git-over-SSH（部署密钥）推专用私有备份库；保留最近 KEEP_LAST 份。"""
    work = tempfile.mkdtemp(prefix="kmfa-bk-repo-")
    try:
        _git(["clone", "--quiet", f"git@github.com:{repo}.git", work], cwd=None, key_path=key_path)
        bkdir = os.path.join(work, "backups")
        os.makedirs(bkdir, exist_ok=True)
        fn = f"{ts}_{sha[:12]}_{PREFIX}.tar.gz"
        with open(os.path.join(bkdir, fn), "wb") as f:
            f.write(data)
        # 追加 manifest
        mpath = os.path.join(work, MANIFEST)
        rec = {"ts": ts, "sha256": sha, "size_bytes": len(data),
               "file_count": len(names), "object_path": f"backups/{fn}", "prefix": PREFIX}
        with open(mpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        # 保留最近 KEEP_LAST 份归档
        arch = sorted(x for x in os.listdir(bkdir) if x.endswith(".tar.gz"))
        for old in arch[:-KEEP_LAST]:
            os.remove(os.path.join(bkdir, old))
        _git(["add", "-A"], cwd=work, key_path=key_path)
        _git(["-c", "user.email=kmfa-backup@localhost", "-c", "user.name=KMFA Backup",
              "commit", "--quiet", "-m", f"backup(kmfa): app-state {ts}"], cwd=work, key_path=key_path)
        _git(["push", "--quiet", "origin", "HEAD"], cwd=work, key_path=key_path)
        print(f"✓ 异地备份完成（部署密钥→{repo}）sha256={sha[:12]}… "
              f"（{len(data)} 字节，{len(names)} 文件，backups/{fn}；保留最近 {KEEP_LAST} 份）")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def cmd_backup(a):
    data, names = _tar_state(a.state_dir)
    sha = hashlib.sha256(data).hexdigest()
    ts = _bj_ts()
    # 优先级：部署密钥(git-SSH,专用备份库) → token(REST,Private-Database) → 本地降级
    keyinfo = _resolve_ssh_key()
    if keyinfo:
        key_path, is_temp = keyinfo
        try:
            _git_ssh_backup(data, names, sha, ts, a.ssh_repo, key_path)
        finally:
            if is_temp:
                try: os.unlink(key_path)
                except OSError: pass
        return 0
    token = _token()
    if token:
        obj = f"objects/{sha[:2]}/{sha}_{ts}_{PREFIX}.tar.gz"
        _put_object(token, a.repo, obj, data, f"backup(kmfa): app-state {ts}")
        _append_manifest(token, a.repo, {
            "ts": ts, "sha256": sha, "size_bytes": len(data),
            "file_count": len(names), "object_path": obj, "prefix": PREFIX})
        print(f"✓ 异地备份完成（token→{a.repo}）sha256={sha[:12]}… "
              f"（{len(data)} 字节，{len(names)} 文件，对象 {obj}）")
        return 0
    os.makedirs(a.fallback_dir, exist_ok=True)
    fp = os.path.join(a.fallback_dir, f"{ts}_{PREFIX}_{sha[:12]}.tar.gz")
    with open(fp, "wb") as f:
        f.write(data)
    print(f"⚠ 异地未激活（无部署密钥/token）：仅本地降级副本 {fp}"
          f"（{len(data)} 字节，含 {len(names)} 文件）。设 Coolify secret 后自动切异地。")
    return 3


def _clone_backup_repo(repo, key_path):
    work = tempfile.mkdtemp(prefix="kmfa-bk-read-")
    _git(["clone", "--quiet", f"git@github.com:{repo}.git", work], cwd=None, key_path=key_path)
    return work


def cmd_restore(a):
    keyinfo = _resolve_ssh_key()
    if keyinfo:                                   # git-SSH：从专用备份库克隆还原
        key_path, is_temp = keyinfo
        try:
            work = _clone_backup_repo(a.ssh_repo, key_path)
            mpath = os.path.join(work, MANIFEST)
            man = [json.loads(l) for l in open(mpath, encoding="utf-8")] if os.path.isfile(mpath) else []
            if not man:
                raise SystemExit("备份库无 manifest 可还原")
            rec = man[-1] if not a.sha else next((r for r in man if r["sha256"].startswith(a.sha)), None)
            if not rec:
                raise SystemExit(f"未找到备份 sha={a.sha}")
            data = open(os.path.join(work, rec["object_path"]), "rb").read()
            got = hashlib.sha256(data).hexdigest()
            if got != rec["sha256"]:
                raise SystemExit(f"完整性校验失败：期望 {rec['sha256'][:12]} 得 {got[:12]}")
            os.makedirs(a.out, exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                tar.extractall(a.out)
            print(f"✓ 还原完成（部署密钥←{a.ssh_repo}）{rec['ts']} sha256={got[:12]}… → {a.out}"
                  f"（{rec['file_count']} 文件，完整性 OK）")
            shutil.rmtree(work, ignore_errors=True)
        finally:
            if is_temp:
                try: os.unlink(key_path)
                except OSError: pass
        return 0
    token = _token()
    if not token:
        raise SystemExit("restore 需部署密钥(KMFA_BACKUP_SSH_KEY) 或 KMFA_BACKUP_GH_TOKEN")
    man = _read_manifest(token, a.repo)
    if not man:
        raise SystemExit("私有库无备份可还原")
    rec = man[-1] if not a.sha else next((r for r in man if r["sha256"].startswith(a.sha)), None)
    if not rec:
        raise SystemExit(f"未找到备份 sha={a.sha}")
    blob = _api("GET", f"/repos/{a.repo}/contents/{rec['object_path']}", token)
    data = base64.b64decode(blob["content"]) if blob.get("content") else \
        _api("GET", blob["download_url"], token, raw=True)
    got = hashlib.sha256(data).hexdigest()
    if got != rec["sha256"]:
        raise SystemExit(f"完整性校验失败：期望 {rec['sha256'][:12]} 得 {got[:12]}")
    os.makedirs(a.out, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(a.out)
    print(f"✓ 还原完成（token←{a.repo}）{rec['ts']} sha256={got[:12]}… → {a.out}（{rec['file_count']} 文件，完整性 OK）")
    return 0


def cmd_list(a):
    keyinfo = _resolve_ssh_key()
    if keyinfo:
        key_path, is_temp = keyinfo
        try:
            work = _clone_backup_repo(a.ssh_repo, key_path)
            mpath = os.path.join(work, MANIFEST)
            man = [json.loads(l) for l in open(mpath, encoding="utf-8")] if os.path.isfile(mpath) else []
            for r in man:
                print(f"{r['ts']}  {r['size_bytes']:>10} 字节  {r['file_count']:>3} 文件  {r['sha256'][:12]}…")
            shutil.rmtree(work, ignore_errors=True)
        finally:
            if is_temp:
                try: os.unlink(key_path)
                except OSError: pass
        return 0
    token = _token()
    if not token:
        raise SystemExit("list 需部署密钥(KMFA_BACKUP_SSH_KEY) 或 KMFA_BACKUP_GH_TOKEN")
    for r in _read_manifest(token, a.repo):
        print(f"{r['ts']}  {r['size_bytes']:>10} 字节  {r['file_count']:>3} 文件  {r['sha256'][:12]}…")
    return 0


def main():
    p = argparse.ArgumentParser(description="KMFA App 状态面异地备份（→ GitHub 私有库）")
    p.add_argument("--repo", default=REPO_DEFAULT, help="token(REST) 路径的仓：默认 Private-Database")
    p.add_argument("--ssh-repo", default=SSH_REPO_DEFAULT, help="部署密钥(git-SSH) 路径的专用备份仓")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup"); b.add_argument("--state-dir", default="/var/lib/kmfa/state")
    b.add_argument("--fallback-dir", default="/var/log/kmfa/backups"); b.set_defaults(fn=cmd_backup)
    r = sub.add_parser("restore"); r.add_argument("--out", default="/var/lib/kmfa/state")
    r.add_argument("--sha", default=""); r.set_defaults(fn=cmd_restore)
    l = sub.add_parser("list"); l.set_defaults(fn=cmd_list)
    a = p.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
