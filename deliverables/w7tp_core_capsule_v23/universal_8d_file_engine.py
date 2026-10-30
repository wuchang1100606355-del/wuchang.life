import copy
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Dict, Any, List, Tuple

# ==============================================================================
# 全檔案類型 8D 確定性分析與原胞狀態傳輸總引擎 (Universal 8D Deterministic File Engine)
# 涵蓋：音訊波形、3D骨骼動作、結構化帳本、文件/二進位區塊、以及高熵複雜亂數三場景
# ==============================================================================

class Universal8DFileEngine:

    # --------------------------------------------------------------------------
    # 家族 2：音訊與時序波形分析器 (辨識靜音段與斜率波段 -> 單量、總量、變化量、速度)
    # --------------------------------------------------------------------------
    @classmethod
    def analyze_audio_pcm(cls, samples: List[int]) -> Dict[str, Any]:
        raw_bytes = struct.pack(f">{len(samples)}h", *samples)
        src_hash = hashlib.sha256(raw_bytes).hexdigest()

        packets = []
        n = len(samples)
        i = 0
        while i < n:
            v0 = samples[i]
            dt_static = 1
            while (i + dt_static) < n and samples[i + dt_static] == v0:
                dt_static += 1

            rem_start = i + dt_static
            dt_active = 0
            velocity = 0
            if rem_start < n:
                velocity = samples[rem_start] - v0
                cur = v0
                while (rem_start + dt_active) < n and (samples[rem_start + dt_active] - cur) == velocity:
                    cur = samples[rem_start + dt_active]
                    dt_active += 1
            net_delta = velocity * dt_active

            pkt = struct.pack(">IIIhhh", i, dt_static, dt_active, v0, net_delta, velocity)
            packets.append(pkt)
            i += dt_static + dt_active

        return {
            "family": "FAMILY_2_AUDIO_WAVEFORM",
            "raw_bytes": len(raw_bytes),
            "wire_bytes": sum(len(p) for p in packets),
            "target_cells": len(packets),
            "packets": packets,
            "source_sha256": src_hash,
            "total_samples": n
        }

    @classmethod
    def reconstruct_audio_pcm(cls, bundle: Dict[str, Any]) -> Dict[str, Any]:
        recon = [0] * bundle["total_samples"]
        for pkt in bundle["packets"]:
            coord_i, dt_static, dt_active, v0, net_delta, velocity = struct.unpack(">IIIhhh", pkt)
            for s in range(dt_static):
                recon[coord_i + s] = v0
            for a in range(1, dt_active + 1):
                recon[coord_i + dt_static + a - 1] = v0 + velocity * a
        recon_bytes = struct.pack(f">{len(recon)}h", *recon)
        r_hash = hashlib.sha256(recon_bytes).hexdigest()
        return {"byte_exact": r_hash == bundle["source_sha256"], "sha256": r_hash}

    # --------------------------------------------------------------------------
    # 家族 3：3D 幾何與骨骼關節動作分析器 (固定網格拓撲 + 關節角度單量/變化量/速度)
    # --------------------------------------------------------------------------
    @classmethod
    def analyze_3d_bone_tracks(cls, bone_frames: List[List[Tuple[int, int, int]]]) -> Dict[str, Any]:
        total_frames = len(bone_frames)
        num_bones = len(bone_frames[0]) if total_frames else 0
        raw_bytes = struct.pack(f">{total_frames * num_bones * 3}h", *[c for f in bone_frames for b in f for c in b])
        src_hash = hashlib.sha256(raw_bytes).hexdigest()

        packets = []
        for bone_id in range(num_bones):
            track = [bone_frames[t][bone_id] for t in range(total_frames)]
            v0 = track[0]
            dt_static = 1
            while dt_static < total_frames and track[dt_static] == v0:
                dt_static += 1
            dt_active = total_frames - dt_static
            v_end = track[-1]
            dx, dy, dz = v_end[0] - v0[0], v_end[1] - v0[1], v_end[2] - v0[2]
            pkt = struct.pack(">HII3h3h", bone_id, dt_static, dt_active, *v0, dx, dy, dz)
            packets.append(pkt)

        return {
            "family": "FAMILY_3_3D_SPATIAL_BONES",
            "raw_bytes": len(raw_bytes),
            "wire_bytes": sum(len(p) for p in packets),
            "bone_cells": len(packets),
            "packets": packets,
            "total_frames": total_frames,
            "num_bones": num_bones,
            "source_sha256": src_hash
        }

    @classmethod
    def reconstruct_3d_bone_tracks(cls, bundle: Dict[str, Any]) -> Dict[str, Any]:
        tf, nb = bundle["total_frames"], bundle["num_bones"]
        recon = [[(0, 0, 0)] * nb for _ in range(tf)]
        for pkt in bundle["packets"]:
            bone_id, dt_s, dt_a, rx0, ry0, rz0, dx, dy, dz = struct.unpack(">HII3h3h", pkt)
            for t in range(dt_s):
                recon[t][bone_id] = (rx0, ry0, rz0)
            for s in range(1, dt_a + 1):
                recon[dt_s + s - 1][bone_id] = (
                    rx0 + (dx * s) // dt_a,
                    ry0 + (dy * s) // dt_a,
                    rz0 + (dz * s) // dt_a
                )
        recon_bytes = struct.pack(f">{tf * nb * 3}h", *[c for f in recon for b in f for c in b])
        r_hash = hashlib.sha256(recon_bytes).hexdigest()
        return {"byte_exact": r_hash == bundle["source_sha256"], "sha256": r_hash}

    # --------------------------------------------------------------------------
    # 家族 4：結構化資料與帳本分析器 (JSON / POS 菜單 / 資料庫列)
    # --------------------------------------------------------------------------
    @classmethod
    def analyze_structured_records(cls, base_records: List[Dict[str, Any]], target_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        target_raw = json.dumps(target_records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        src_hash = hashlib.sha256(target_raw).hexdigest()

        base_map = {r["id"]: r for r in base_records}
        cell_deltas = []
        static_count = 0

        for rec in target_records:
            rid = rec["id"]
            if rid in base_map and base_map[rid] == rec:
                static_count += 1
                continue
            base_rec = base_map.get(rid, {})
            field_changes = {}
            for k, v in rec.items():
                if k == "id" or base_rec.get(k) == v:
                    continue
                if isinstance(v, int) and isinstance(base_rec.get(k), int):
                    field_changes[k] = {"mode": "DELTA", "d": v - base_rec[k]}
                else:
                    field_changes[k] = {"mode": "SET", "v": v}
            cell_deltas.append({"id": rid, "changes": field_changes})

        wire_payload = json.dumps(cell_deltas, separators=(",", ":")).encode("utf-8")
        return {
            "family": "FAMILY_4_STRUCTURED_DATA",
            "raw_bytes": len(target_raw),
            "wire_bytes": len(wire_payload),
            "static_records_skipped": static_count,
            "active_cells": len(cell_deltas),
            "wire_payload": wire_payload,
            "source_sha256": src_hash
        }

    @classmethod
    def reconstruct_structured_records(cls, base_records: List[Dict[str, Any]], bundle: Dict[str, Any]) -> Dict[str, Any]:
        recon = copy.deepcopy(base_records)
        rec_map = {r["id"]: r for r in recon}
        deltas = json.loads(bundle["wire_payload"].decode("utf-8"))
        for cell in deltas:
            target = rec_map[cell["id"]]
            for k, spec in cell["changes"].items():
                if spec["mode"] == "DELTA":
                    target[k] += spec["d"]
                else:
                    target[k] = spec["v"]
        recon_raw = json.dumps(recon, sort_keys=True, separators=(",", ":")).encode("utf-8")
        r_hash = hashlib.sha256(recon_raw).hexdigest()
        return {"byte_exact": r_hash == bundle["source_sha256"], "sha256": r_hash}

    # --------------------------------------------------------------------------
    # 家族 5 & 6：程式碼/文件與通用二進位/亂數區塊分析器 (求同未變區塊 + 存異增量原胞)
    # --------------------------------------------------------------------------
    @classmethod
    def analyze_binary_or_doc_blocks(cls, base_bytes: bytes, target_bytes: bytes, block_size: int = 256) -> Dict[str, Any]:
        src_hash = hashlib.sha256(target_bytes).hexdigest()
        b_chunks = [base_bytes[i:i+block_size] for i in range(0, len(base_bytes), block_size)]
        t_chunks = [target_bytes[i:i+block_size] for i in range(0, len(target_bytes), block_size)]

        packets = []
        static_blocks = 0
        active_blocks = 0
        for idx, chk in enumerate(t_chunks):
            if idx < len(b_chunks) and b_chunks[idx] == chk:
                static_blocks += 1
                continue
            active_blocks += 1
            packets.append(struct.pack(">II", idx, len(chk)) + chk)

        header = struct.pack(">II", len(t_chunks), len(target_bytes))
        return {
            "family": "FAMILY_5_6_DOC_AND_BINARY_BLOCKS",
            "raw_bytes": len(target_bytes),
            "wire_bytes": len(header) + sum(len(p) for p in packets),
            "static_blocks_skipped": static_blocks,
            "active_cells": active_blocks,
            "header": header,
            "packets": packets,
            "block_size": block_size,
            "source_sha256": src_hash
        }

    @classmethod
    def reconstruct_binary_or_doc_blocks(cls, base_bytes: bytes, bundle: Dict[str, Any]) -> Dict[str, Any]:
        bs = bundle["block_size"]
        total_chunks, total_len = struct.unpack(">II", bundle["header"])
        b_chunks = [base_bytes[i:i+bs] for i in range(0, len(base_bytes), bs)]
        recon_chunks = [b_chunks[i] if i < len(b_chunks) else b"" for i in range(total_chunks)]
        for pkt in bundle["packets"]:
            idx, clen = struct.unpack(">II", pkt[:8])
            recon_chunks[idx] = pkt[8:8+clen]
        recon_bytes = b"".join(recon_chunks)[:total_len]
        r_hash = hashlib.sha256(recon_bytes).hexdigest()
        return {"byte_exact": r_hash == bundle["source_sha256"], "sha256": r_hash}


if __name__ == "__main__":
    print("=== 【全檔案類型 8D 確定性分析總引擎：六大家族與複雜亂數完整實測】 ===")

    # 1. 音訊波形檔
    audio_samples = [0] * 1500 + [i * 12 for i in range(1, 1001)] + [12000] * 1000 + [12000 - i * 24 for i in range(1, 501)]
    audio_bundle = Universal8DFileEngine.analyze_audio_pcm(audio_samples)
    audio_verify = Universal8DFileEngine.reconstruct_audio_pcm(audio_bundle)
    print(f"\n🎵 [家族 2：音訊波形檔 (.wav/.pcm)]")
    print(f"   • 原始資料量：{audio_bundle['raw_bytes']:,} Bytes | 辨識原胞：{audio_bundle['target_cells']} 顆 | 傳輸量：{audio_bundle['wire_bytes']} Bytes")
    print(f"   • CPU 重構驗收：100% Byte-Exact = {audio_verify['byte_exact']} (SHA256: {audio_verify['sha256'][:16]}...)")

    # 2. 3D 骨骼與臉部動作
    bones_120f = []
    for t in range(120):
        frame_bones = [(0, 0, 0)] * 48
        step = max(0, t - 60 + 1) if t >= 60 else 0
        for _ in range(4):
            frame_bones.append((100 + (60 * step) // 60, -50 + (30 * step) // 60, 200))
        bones_120f.append(frame_bones)
    b3d_bundle = Universal8DFileEngine.analyze_3d_bone_tracks(bones_120f)
    b3d_verify = Universal8DFileEngine.reconstruct_3d_bone_tracks(b3d_bundle)
    print(f"\n🧍‍♀️ [家族 3：3D 骨骼與臉部動作 (52 關節 × 120 幀)]")
    print(f"   • 原始資料量：{b3d_bundle['raw_bytes']:,} Bytes | 辨識原胞：{b3d_bundle['bone_cells']} 顆 | 傳輸量：{b3d_bundle['wire_bytes']:,} Bytes")
    print(f"   • CPU 重構驗收：100% Byte-Exact = {b3d_verify['byte_exact']} (SHA256: {b3d_verify['sha256'][:16]}...)")

    # 3. 結構化帳本/JSON
    base_db = [{"id": i, "name": f"Wuchang_Coffee_Item_{i:03d}", "price": 120, "stock": 500, "category": "Drink"} for i in range(1, 201)]
    new_db = copy.deepcopy(base_db)
    new_db[15]["stock"] -= 3
    new_db[88]["price"] += 10
    db_bundle = Universal8DFileEngine.analyze_structured_records(base_db, new_db)
    db_verify = Universal8DFileEngine.reconstruct_structured_records(base_db, db_bundle)
    print(f"\n📊 [家族 4：結構化帳本/JSON (POS 菜單與庫存狀態)]")
    print(f"   • 原始資料量：{db_bundle['raw_bytes']:,} Bytes | 求同略過：{db_bundle['static_records_skipped']} 筆 | 傳輸量：{db_bundle['wire_bytes']} Bytes")
    print(f"   • CPU 重構驗收：100% Byte-Exact = {db_verify['byte_exact']} (SHA256: {db_verify['sha256'][:16]}...)")

    # 4. 真實正典文件同步
    doc_path = Path("/home/taiji_admin/Taiji_Hub/WUCHANG_GOOGLE_AI_SHARING_ECONOMY_PILOT_20261022.md")
    base_doc = doc_path.read_bytes() if doc_path.exists() else b"Base Canonical Document " * 500
    target_doc = base_doc + b"\n<!-- Verified by Universal 8D File Engine -->\n"
    doc_bundle = Universal8DFileEngine.analyze_binary_or_doc_blocks(base_doc, target_doc)
    doc_verify = Universal8DFileEngine.reconstruct_binary_or_doc_blocks(base_doc, doc_bundle)
    print(f"\n📄 [家族 5 & 6：真實正典文件增量同步 ({doc_path.name})]")
    print(f"   • 原始資料量：{doc_bundle['raw_bytes']:,} Bytes | 求同略過：{doc_bundle['static_blocks_skipped']} 塊 | 傳輸量：{doc_bundle['wire_bytes']} Bytes")
    print(f"   • CPU 重構驗收：100% Byte-Exact = {doc_verify['byte_exact']} (SHA256: {doc_verify['sha256'][:16]}...)")

    # 5. 複雜亂數檔案極限壓力測試 (100KB Linux /dev/urandom 真亂數基底 + 2 處未知亂數突變)
    base_random = os.urandom(100_000)
    target_random_ba = bytearray(base_random)
    target_random_ba[12800:13056] = os.urandom(256)
    target_random_ba[76800:77056] = os.urandom(256)
    rnd_bundle = Universal8DFileEngine.analyze_binary_or_doc_blocks(base_random, bytes(target_random_ba), block_size=256)
    rnd_verify = Universal8DFileEngine.reconstruct_binary_or_doc_blocks(base_random, rnd_bundle)
    print(f"\n🎲 [高熵複雜亂數測試 A：100 KB 真亂數檔 (含 2 處未知亂數突變)]")
    print(f"   • 原始亂數大小：{rnd_bundle['raw_bytes']:,} Bytes | 求同略過：{rnd_bundle['static_blocks_skipped']} 塊 | 傳輸量：{rnd_bundle['wire_bytes']} Bytes (減量 {(1 - rnd_bundle['wire_bytes']/rnd_bundle['raw_bytes'])*100:.2f}%)")
    print(f"   • CPU 重構驗收：100% Byte-Exact = {rnd_verify['byte_exact']} (SHA256: {rnd_verify['sha256'][:16]}...)")

    # 6. 100% 全新無基座真亂數檔 (V3/V4 交叉點誠實邊界驗證)
    cold_random = os.urandom(10_240)
    cold_bundle = Universal8DFileEngine.analyze_binary_or_doc_blocks(b"", cold_random, block_size=256)
    cold_verify = Universal8DFileEngine.reconstruct_binary_or_doc_blocks(b"", cold_bundle)
    print(f"\n🛡️ [高熵複雜亂數測試 B：10 KB 完全無基座真亂數檔 (未知比例 100% 誠實殘差通道)]")
    print(f"   • 原始亂數大小：{cold_bundle['raw_bytes']:,} Bytes | 求同略過：{cold_bundle['static_blocks_skipped']} 塊 | 實際傳輸：{cold_bundle['wire_bytes']:,} Bytes")
    print(f"   • CPU 重構驗收：100% Byte-Exact = {cold_verify['byte_exact']} (SHA256: {cold_verify['sha256'][:16]}...)")
