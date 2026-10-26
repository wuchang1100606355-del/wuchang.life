#!/usr/bin/env python3
import hashlib, json, os, pathlib, shutil, sys, tempfile, zlib
HERE = pathlib.Path(__file__).resolve().parent
SHM = pathlib.Path("/dev/shm/w7tp_ram_workspace") if pathlib.Path("/dev/shm").exists() else pathlib.Path(tempfile.gettempdir()) / "w7tp_ram_workspace"
def bootstrap():
    m = json.loads((HERE / "CAPSULE_MANIFEST.json").read_text(encoding="utf-8"))
    if SHM.exists(): shutil.rmtree(SHM, ignore_errors=True)
    SHM.mkdir(parents=True, exist_ok=True)
    for k, v in m["files"].items():
        src = HERE / k
        data = src.read_bytes()
        if hashlib.sha256(data).hexdigest() != v["sha256"]:
            raise ValueError(f"HOLD_CAPSULE_SHA256_MISMATCH:{k}")
        (SHM / k).write_bytes(data)
    (SHM / "CAPSULE_MANIFEST.json").write_bytes((HERE / "CAPSULE_MANIFEST.json").read_bytes())
    pack = SHM / "cloud_sync_batch_1000_cells.w7pack"
    cells = zlib.decompress(pack.read_bytes()).split(b"\n---CELL---\n") if pack.exists() else []
    return {"state": "PASS_NODE_RAM_WORKSPACE_BOOTSTRAPPED", "ram_workspace": str(SHM), "verified_files": len(m["files"]), "total_bytes": m["total_bytes"], "prewarmed_cells": len(cells)}
if __name__ == "__main__":
    print(json.dumps(bootstrap(), indent=2, ensure_ascii=False))
