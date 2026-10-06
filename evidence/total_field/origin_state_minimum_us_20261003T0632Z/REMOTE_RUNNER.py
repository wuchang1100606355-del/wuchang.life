import hashlib, json, os, resource, socket, sys, time
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path("/tmp/w7tp-origin-us-min-20261003T0632Z")
sys.path.insert(0, str(ROOT))
from products.eight_dimensional_generative_memory.w7tp_origin_state_minimum_packet_v1 import (
    validate_minimum_packet, volatile_reconstruction, sha256_file,
)
packet_path = ROOT / "inbox/ORIGIN_STATE_MINIMUM_PACKET_256M.json"
packet = json.loads(packet_path.read_text(encoding="utf-8"))
started = time.monotonic()
validate_minimum_packet(packet, root=ROOT, registry_path=ROOT/"configs/total_field/w7tp_local_origin_state_rule_registry_v1.json")
workset_path = None
with volatile_reconstruction(packet, root=ROOT, registry_path=ROOT/"configs/total_field/w7tp_local_origin_state_rule_registry_v1.json") as result:
    workset_path = str(result["workset_path"])
    receipt = dict(result["receipt"])
    receipt["workset_observed_during_context"] = Path(workset_path).is_dir()
elapsed = time.monotonic() - started
receipt.update({
    "experiment_id": "20261003T0632Z",
    "source_node": "taiji01",
    "destination_node": socket.gethostname(),
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "packet_file_bytes": packet_path.stat().st_size,
    "packet_file_sha256": sha256_file(packet_path),
    "packet_canonical_sha256": packet["packet_sha256"],
    "reconstruction_elapsed_sec": elapsed,
    "maxrss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "workset_destroyed_after_context": not Path(workset_path).exists(),
    "rule_impl_sha256": sha256_file(ROOT/"products/eight_dimensional_generative_memory/w7tp_origin_cell_generative_v2.py"),
    "minimum_packet_impl_sha256": sha256_file(ROOT/"products/eight_dimensional_generative_memory/w7tp_origin_state_minimum_packet_v1.py"),
    "registry_sha256": sha256_file(ROOT/"configs/total_field/w7tp_local_origin_state_rule_registry_v1.json"),
})
out = ROOT / "REMOTE_RECEIPT.json"
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(receipt, ensure_ascii=False))
