import time,zlib,hashlib,json,sys,pathlib as P
p=P.Path("/dev/shm/w7tp_ram_workspace")
sys.path.insert(0,str(p))
from gst_transceiver import GSTBidirectionalTransceiver as T
t0=time.perf_counter()
raw=(p/"stress_10000_cells.w7pack").read_bytes()
assert hashlib.sha256(raw).hexdigest()=="210dc7200c3c04437d3c27e7c57f985b81a84b725b72b54617d287f9eb15c9d3"
cs=zlib.decompress(raw).split(b"|CELL|")
base=b"W7TP_8D_ADI_V23_STATIC_PREFIX_C01_TO_C05_LUT_ANCHOR_"*20
ok=all(T.decode_file_state(base,c)["byte_exact"] for c in cs)
print(json.dumps({"msi_verified_cells":len(cs),"msi_all_byte_exact":ok,"msi_effect_state":"PASS_EFFECT_VERIFIED" if ok else "HOLD_EFFECT_NOT_EQUIVALENT","msi_unpack_and_reconstruct_ms":round((time.perf_counter()-t0)*1000,2)}))
