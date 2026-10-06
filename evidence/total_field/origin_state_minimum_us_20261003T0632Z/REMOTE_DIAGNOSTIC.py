import json, sqlite3, sys, tempfile, shutil
from pathlib import Path
ROOT=Path("/tmp/w7tp-origin-us-min-20261003T0632Z")
sys.path.insert(0,str(ROOT))
from products.eight_dimensional_generative_memory import w7tp_origin_cell_generative_v2 as gen
expected=json.loads((ROOT/"DIAGNOSTIC_EXPECTED_ROWS.json").read_text())
recipe=gen._build_fixture_recipe(256,3)
work=Path(tempfile.mkdtemp(prefix="w7tp-diag-",dir="/dev/shm"))
out=work/"reconstructed"
out.mkdir()
try:
    gen.execute_reconstruction_rules(out,recipe["rules"],recipe["execution_order"])
    rows,total,manifest=gen.file_manifest(out)
    exp={r["path"]:r for r in expected["rows"]}
    got={r["path"]:r for r in rows}
    diffs=[]
    for p in sorted(set(exp)|set(got)):
        if exp.get(p)!=got.get(p):
            diffs.append({"path":p,"expected":exp.get(p),"observed":got.get(p)})
    result={"remote_python":sys.version,"remote_sqlite":sqlite3.sqlite_version,
            "expected_manifest":expected["manifest"],"observed_manifest":manifest,
            "expected_bytes":expected["bytes"],"observed_bytes":total,
            "mismatch_count":len(diffs),"mismatches":diffs[:20]}
    print(json.dumps(result,ensure_ascii=False))
finally:
    shutil.rmtree(work,ignore_errors=True)
