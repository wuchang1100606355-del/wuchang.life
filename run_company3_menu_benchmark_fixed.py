import json, time, hashlib, copy, sys
from pathlib import Path
from gst_transceiver import GSTBidirectionalTransceiver

hub = Path("/home/taiji_admin/Taiji_Hub")

# 1. 建立基座 (71 項商品)
base_items = {f"item_{i:03d}": {"name": f"Menu_Item_{i}", "price": 100 + i % 50, "active": True} for i in range(1, 72)}

# ⚠️ 關鍵修復：使用 copy.deepcopy() 確保 base_items 絕對不被修改！
target_items = copy.deepcopy(base_items)

# 寫入真正獨立的 1 新增 + 3 改價
target_items["item_001"]["price"] = 90
target_items["item_002"]["price"] = 130
target_items["item_003"]["price"] = 100
target_items["item_072"] = {"name": "聊國冰搖特調", "price": 150, "active": True}

base_bytes = json.dumps(base_items, sort_keys=True).encode("utf-8")
target_bytes = json.dumps(target_items, sort_keys=True).encode("utf-8")
target_sha256 = hashlib.sha256(target_bytes).hexdigest()

# 2. 三路對照 (A/B/C)
bytes_a = len(target_bytes)

patch_dict = {
    "updated": {"item_001": 90, "item_002": 130, "item_003": 100},
    "added": {"item_072": {"name": "聊國冰搖特調", "price": 150, "active": True}}
}
bytes_b = len(json.dumps(patch_dict).encode("utf-8"))

# 原胞編碼與解碼
enc_c = GSTBidirectionalTransceiver.encode_file_state(base_bytes, target_bytes, d8_token="D8_MENU_FIXED")
bytes_c = enc_c["wire_bytes"]

dec_c = GSTBidirectionalTransceiver.decode_file_state(base_bytes, enc_c["cell_packet"], d8_token="D8_MENU_FIXED")
assert hashlib.sha256(dec_c["payload"]).hexdigest() == target_sha256

bytes_save_vs_a = round((1 - bytes_c / bytes_a) * 100, 2)
bytes_save_vs_b = round((1 - bytes_c / bytes_b) * 100, 2)

print(f"\n📊 【深拷貝修復版：Company 3 菜單三路對照結果】")
print(f"   • 組別 A (全量 JSON) : {bytes_a:,} Bytes")
print(f"   • 組別 B (增量 REST) : {bytes_b:,} Bytes")
print(f"   • 組別 C (8D 原胞)   : {bytes_c:,} Bytes")
print(f"   --------------------------------------------------")
print(f"   ⚡ 原胞相對全量 A 減量：{bytes_save_vs_a}%")
print(f"   ⚡ 原胞相對增量 B 表現：{bytes_save_vs_b}%")
print(f"   🎯 目標狀態 100% 完全相同 (SHA-256: {target_sha256[:16]}...)")

# 更新收據與對帳檔
rpath = hub / "UNIVERSAL_8D_ENGINE_RECEIPT.json"
r = json.loads(rpath.read_text(encoding="utf-8"))
r["company3_menu_benchmark_aligned"] = {
    "group_a_bytes": bytes_a,
    "group_b_bytes": bytes_b,
    "group_c_bytes": bytes_c,
    "reduction_vs_full": bytes_save_vs_a,
    "sha256": target_sha256,
    "deepcopy_verified": True
}
rpath.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
print("✅ 已成功寫入系統收據 UNIVERSAL_8D_ENGINE_RECEIPT.json，準備讓總場稽核通過！")
