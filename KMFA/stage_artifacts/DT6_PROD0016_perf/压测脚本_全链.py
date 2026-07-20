"""万行级 xlsx 全链时限实测：登记 → staging → 报表聚合。金额一律整数分。"""
import hashlib, json, time, pathlib, statistics
import openpyxl, duckdb

SRC = pathlib.Path("/out/stress_10k.xlsx")
DB = pathlib.Path("/out/stress.duckdb")
DB.unlink(missing_ok=True)
marks = {}

def stage(name):
    class T:
        def __enter__(s): s.t = time.perf_counter(); return s
        def __exit__(s, *a): marks[name] = round(time.perf_counter() - s.t, 3)
    return T()

# ① 登记：内容寻址（与 file_import_register 同口径：sha256 + 大小 + 行数）
with stage("① 登记"):
    data = SRC.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    wb = openpyxl.load_workbook(SRC, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header, body = rows[0], rows[1:]
    manifest = {"sha256": sha, "size_bytes": len(data), "rows": len(body)}

# ② staging：入 DuckDB，**金额转整数分**（浮点只在读 xlsx 那一刻存在，落库即整数）
with stage("② staging"):
    con = duckdb.connect(str(DB))
    con.execute("CREATE TABLE stg(voucher VARCHAR, dt VARCHAR, code VARCHAR, name VARCHAR,"
                " debit_cents BIGINT, credit_cents BIGINT, memo VARCHAR, project VARCHAR)")
    payload = [(r[0], r[1], r[2], r[3],
                int(round(float(r[4]) * 100)), int(round(float(r[5]) * 100)), r[6], r[7])
               for r in body]
    con.executemany("INSERT INTO stg VALUES (?,?,?,?,?,?,?,?)", payload)

# ③ 报表聚合：按项目×月汇总（真 SQL，非 mock）
with stage("③ 报表"):
    agg = con.execute("""
        SELECT project, substr(dt,1,7) AS period,
               SUM(debit_cents) AS debit_cents, COUNT(*) AS n
        FROM stg GROUP BY 1,2 ORDER BY 1,2
    """).fetchall()

total = round(sum(marks.values()), 3)
checks = con.execute("SELECT COUNT(*), SUM(debit_cents) FROM stg").fetchone()
print(json.dumps({
    "输入": {"文件": SRC.name, "字节": manifest["size_bytes"], "数据行": manifest["rows"],
             "sha256": "sha256:" + sha[:16] + "…"},
    "分段耗时秒": marks,
    "全链耗时秒": total,
    "落库校验": {"行数": checks[0], "借方合计分": checks[1],
                 "行数一致": checks[0] == manifest["rows"]},
    "报表聚合": {"分组数": len(agg), "样例": [list(agg[0]), list(agg[-1])]},
    "金额表示": "整数分（BIGINT）",
}, ensure_ascii=False, indent=1))
