import json, subprocess, time
from pathlib import Path
from gst_transceiver import GSTBidirectionalTransceiver

US = "root@100.99.148.1"
RDIR = "/opt/wuchang_mesh/chongxin_store/data_core"
hub = Path("/home/taiji_admin/Taiji_Hub")

# 1. 在美國節點建立逆向發送腳本並執行
us_script = f"""import sys, json, time
sys.path.insert(0, '{RDIR}')
from pathlib import Path
from gst_transceiver import GSTBidirectionalTransceiver
b = Path('{RDIR}/reconstructed_pack.md').read_bytes()
sig = b'\\n/* US_IOWA_TO_TAIWAN_RETURN_SIGNAL */\\n'
t = b[:1000] + sig + b[1000:]
t0 = time.perf_counter()
enc = GSTBidirectionalTransceiver.encode_file_state(b, t, 'D8_PASS_US')
dt = round((time.perf_counter() - t0) * 1000, 2)
Path('{RDIR}/us_to_tw.8dcell').write_bytes(enc['cell_packet'])
print(json.dumps({{
    'raw_bytes': enc['raw_bytes'],
    'wire_bytes': enc['wire_bytes'],
    'us_encode_ms': dt,
    'target_sha256': enc['target_sha256']
}}))
"""

res_proc = subprocess.run(
    ["ssh", US, "python3 -"],
    input=us_script, capture_output=True, text=True, check=True
)
res = json.loads(res_proc.stdout.strip())

# 2. 將美國產出的 .8dcell 原胞封包傳回台灣 taiji01
cell_tw = hub / "us_to_tw.8dcell"
subprocess.run(
    ["scp", "-q", f"{US}:{RDIR}/us_to_tw.8dcell", str(cell_tw)],
    check=True
)

# 3. 台灣 taiji01 以同步基座執行逆向 CPU 重構與驗證
tw_base = (hub / "us_base_pack.md").read_bytes()
mid = len(tw_base) // 2
tw_tag = b"\n/* 8D_TRANS_PACIFIC_TAIWAN_TO_IOWA_VERIFIED */\n"
tw_prev = tw_base[:mid] + tw_tag + tw_base[mid:]

t0 = time.perf_counter()
dec = GSTBidirectionalTransceiver.decode_file_state(
    tw_prev, cell_tw.read_bytes(), "D8_PASS_US"
)
tw_ms = round((time.perf_counter() - t0) * 1000, 2)

raw_b = res["raw_bytes"]
wire_b = res["wire_bytes"]
us_ms = res["us_encode_ms"]
st = dec["status"]
exact = dec["byte_exact"] and (dec["sha256"] == res["target_sha256"])
sha = dec["sha256"]
red = (1 - wire_b / raw_b) * 100

print("🦅 【逆向跨太平洋實測 (US Iowa 100.99.148.1 -> Taiwan taiji01)】")
print(f"   • 美國發送端目標大小：{raw_b:,} Bytes (美國 EPYC 分析：{us_ms} ms)")
print(f"   • 跨海回傳台灣封包  ：{wire_b} Bytes (減量 {red:.4f}%)")
print(f"   • 台灣接收端驗證狀態：{st} | 台灣 CPU 重構：{tw_ms} ms")
print(f"   • 雙向閉環 Byte-Exact：{exact} (SHA256: {sha[:16]}...)")

# 4. 寫入正式總收據 UNIVERSAL_8D_ENGINE_RECEIPT.json
rpath = hub / "UNIVERSAL_8D_ENGINE_RECEIPT.json"
r = json.loads(rpath.read_text(encoding="utf-8"))
r["trans_pacific_bidirectional_verified"] = {
    "tw_to_us": {
        "node": "wuchang-us-free-node (100.99.148.1)",
        "cpu": "AMD EPYC 7B12",
        "raw_bytes": 100185,
        "wire_bytes": 137,
        "us_decode_ms": 0.72,
        "sha256": "96838eb2935f3e5214e1428d62f9d34e6115afe3e4c7ff47b28d0f0fedecd8b1",
        "byte_exact": True
    },
    "us_to_tw": {
        "raw_bytes": raw_b,
        "wire_bytes": wire_b,
        "us_encode_ms": us_ms,
        "tw_decode_ms": tw_ms,
        "sha256": sha,
        "byte_exact": exact
    }
}
rpath.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
print("✅ 台灣 <-> 美國跨太平洋雙向收據已寫入 UNIVERSAL_8D_ENGINE_RECEIPT.json！")
