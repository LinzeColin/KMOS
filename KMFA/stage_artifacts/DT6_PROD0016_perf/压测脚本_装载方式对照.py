"""同一份数据，只把 staging 段从 executemany 换成 DuckDB 批量装载——验证瓶颈定位是否正确。"""
import time, pathlib, json, openpyxl, duckdb

SRC = pathlib.Path("/out/stress_10k.xlsx")
wb = openpyxl.load_workbook(SRC, read_only=True)
body = list(wb.active.iter_rows(values_only=True))[1:]
payload = [(r[0], r[1], r[2], r[3], int(round(float(r[4])*100)), int(round(float(r[5])*100)), r[6], r[7])
           for r in body]

def run(mode):
    db = pathlib.Path(f"/out/s_{mode}.duckdb"); db.unlink(missing_ok=True)
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE stg(voucher VARCHAR, dt VARCHAR, code VARCHAR, name VARCHAR,"
                " debit_cents BIGINT, credit_cents BIGINT, memo VARCHAR, project VARCHAR)")
    t = time.perf_counter()
    if mode == "executemany":
        con.executemany("INSERT INTO stg VALUES (?,?,?,?,?,?,?,?)", payload)
    else:
        con.execute("INSERT INTO stg SELECT * FROM (SELECT UNNEST(?, recursive := true))",
                    [[{"a":p[0],"b":p[1],"c":p[2],"d":p[3],"e":p[4],"f":p[5],"g":p[6],"h":p[7]} for p in payload]])
    dt = round(time.perf_counter() - t, 3)
    n, s = con.execute("SELECT COUNT(*), SUM(debit_cents) FROM stg").fetchone()
    return dt, n, s

a = run("executemany")
b = run("bulk")
print(json.dumps({
    "executemany": {"秒": a[0], "行": a[1], "借方合计分": a[2]},
    "批量装载":     {"秒": b[0], "行": b[1], "借方合计分": b[2]},
    "提速倍数": round(a[0]/b[0], 1) if b[0] else None,
    "结果一致": a[1] == b[1] and a[2] == b[2],
}, ensure_ascii=False, indent=1))
