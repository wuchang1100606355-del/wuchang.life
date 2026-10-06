import hashlib,json,sqlite3,sys,tempfile,shutil
from pathlib import Path
ROOT=Path("/tmp/w7tp-origin-us-min-20261003T0632Z")
sys.path.insert(0,str(ROOT))
from products.eight_dimensional_generative_memory import w7tp_origin_cell_generative_v2 as gen
recipe=gen._build_fixture_recipe(256,3)
work=Path(tempfile.mkdtemp(prefix="w7tp-sqlite-diag-",dir="/dev/shm"))
out=work/"reconstructed"; out.mkdir()
try:
    gen.execute_reconstruction_rules(out,recipe["rules"],recipe["execution_order"])
    p=out/"database/data.db"
    con=sqlite3.connect(f"file:{p}?mode=ro",uri=True)
    try:
        schema=list(con.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"))
        h=hashlib.sha256(); n=0
        for rid,k,v in con.execute("SELECT id,k,v FROM records ORDER BY id"):
            row=[rid,k,hashlib.sha256(v).hexdigest()]
            b=json.dumps(row,separators=(",",":"),ensure_ascii=True).encode()
            h.update(len(b).to_bytes(8,"big")); h.update(b); n+=1
        d={"python_version":sys.version.split()[0],"python_sqlite_version":sqlite3.sqlite_version,
           "file_bytes":p.stat().st_size,"file_sha256":gen.sha256_file(p),
           "page_size":con.execute("PRAGMA page_size").fetchone()[0],
           "page_count":con.execute("PRAGMA page_count").fetchone()[0],
           "freelist_count":con.execute("PRAGMA freelist_count").fetchone()[0],
           "encoding":con.execute("PRAGMA encoding").fetchone()[0],
           "journal_mode":con.execute("PRAGMA journal_mode").fetchone()[0],
           "schema_version":con.execute("PRAGMA schema_version").fetchone()[0],
           "user_version":con.execute("PRAGMA user_version").fetchone()[0],
           "application_id":con.execute("PRAGMA application_id").fetchone()[0],
           "schema":schema,"row_count":n,"logical_rows_sha256":h.hexdigest()}
    finally: con.close()
    print(json.dumps(d,ensure_ascii=False))
finally:
    shutil.rmtree(work,ignore_errors=True)
