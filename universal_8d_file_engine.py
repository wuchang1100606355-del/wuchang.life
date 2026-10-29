
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()

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
    @staticmethod
    def analyze_audio_pcm(samples):
        samples = list(samples)
        raw = struct.pack(f'>{len(samples)}h', *samples)
        packets = []
        i, n = 0, len(samples)
        while i < n:
            if i + 2 < n and samples[i] == samples[i+1] == samples[i+2]:
                j = i + 3
                while j < n and samples[j] == samples[i]:
                    j += 1
                packets.append(struct.pack('>BIh', 0, j-i, samples[i]))
            elif i + 2 < n and samples[i+1] - samples[i] == samples[i+2] - samples[i+1]:
                step = samples[i+1] - samples[i]
                j = i + 3
                while j < n and samples[j] - samples[j-1] == step:
                    j += 1
                # signed 32-bit step accommodates legal int16 extreme jumps
                packets.append(struct.pack('>BIhi', 1, j-i, samples[i], step))
            else:
                j = i + 1
                while j < n:
                    if j+2 < n and (samples[j] == samples[j+1] == samples[j+2] or
                                      samples[j+1]-samples[j] == samples[j+2]-samples[j+1]):
                        break
                    j += 1
                segment = samples[i:j]
                packets.append(struct.pack('>BI', 2, len(segment)) +
                               struct.pack(f'>{len(segment)}h', *segment))
            i = j
        cell = b'8DPCM2' + struct.pack('>II', n, len(packets)) + b''.join(packets)
        return {'family': 'FAMILY_2_AUDIO_WAVEFORM', 'format_version': 2, 'packets': [cell], 'total_samples': n, 'target_cells': len(packets), 'cell': cell, 'source_sha256': _sha(raw),
                'raw_bytes': len(raw), 'wire_bytes': len(cell), 'cells': len(packets)}


    @classmethod
    def _legacy_reconstruct_audio_pcm(cls, bundle: Dict[str, Any]) -> Dict[str, Any]:
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

    @staticmethod
    def reconstruct_audio_pcm(bundle, *, return_values=False):
        if 'cell' not in bundle: return Universal8DFileEngine._legacy_reconstruct_audio_pcm(bundle)
        cell = bundle['cell']
        if not cell.startswith(b'8DPCM2') or len(cell) < 14:
            raise ValueError('INVALID_PCM_HEADER')
        n, count = struct.unpack('>II', cell[6:14]); off = 14
        if n > 100_000_000 or count > n+1:
            raise ValueError('PCM_LIMIT')
        values = []
        for _ in range(count):
            if off+5 > len(cell):
                raise ValueError('TRUNCATED_PCM')
            mode, length = struct.unpack('>BI', cell[off:off+5]); off += 5
            if length < 1 or len(values)+length > n:
                raise ValueError('INVALID_PCM_CELL_LENGTH')
            if mode == 0:
                if off+2 > len(cell): raise ValueError('TRUNCATED_STATIC')
                (v,) = struct.unpack('>h', cell[off:off+2]); off += 2
                values.extend([v]*length)
            elif mode == 1:
                if off+6 > len(cell): raise ValueError('TRUNCATED_RAMP')
                start, step = struct.unpack('>hi', cell[off:off+6]); off += 6
                values.extend(start + step*j for j in range(length))
            elif mode == 2:
                if off+2*length > len(cell): raise ValueError('TRUNCATED_LITERAL')
                values.extend(struct.unpack(f'>{length}h', cell[off:off+2*length]))
                off += 2*length
            else:
                raise ValueError('UNKNOWN_PCM_MODE')
        if len(values) != n or off != len(cell):
            raise ValueError('PCM_FRAMING_MISMATCH')
        raw = struct.pack(f'>{n}h', *values)
        result = {'byte_exact': _sha(raw) == bundle['source_sha256'],
                  'sha256': _sha(raw), 'reconstructed_bytes': len(raw)}
        if return_values:
            result['values'] = values
        return result


    # --------------------------------------------------------------------------
    # 家族 3：3D 幾何與骨骼關節動作分析器 (固定網格拓撲 + 關節角度單量/變化量/速度)
    # --------------------------------------------------------------------------
    @classmethod
    def analyze_3d_bone_tracks(cls, frames):
        n = len(frames); bones = len(frames[0]) if n else 0
        if any(len(frame) != bones for frame in frames):
            raise ValueError('UNEQUAL_BONE_COUNT')
        coords = [v for frame in frames for bone in frame for v in bone]
        raw = struct.pack(f'>{len(coords)}h', *coords)
        tracks = [[cls.analyze_audio_pcm([frames[t][j][axis] for t in range(n)])
                   for axis in range(3)] for j in range(bones)]
        return {'family': 'FAMILY_3_3D_SPATIAL_BONES', 'format_version': 2, 'bone_cells': bones, 'packets': [item['cell'] for group in tracks for item in group], 'total_frames': n,
                'num_bones': bones, 'tracks': tracks, 'source_sha256': _sha(raw),
                'raw_bytes': len(raw),
                'wire_bytes': 8+sum(cell['wire_bytes'] for group in tracks for cell in group)}


    @classmethod
    def _legacy_reconstruct_3d_bone_tracks(cls, bundle: Dict[str, Any]) -> Dict[str, Any]:
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

    @classmethod
    def reconstruct_3d_bone_tracks(cls, bundle):
        if 'tracks' not in bundle: return cls._legacy_reconstruct_3d_bone_tracks(bundle)
        n, bones = bundle['total_frames'], bundle['num_bones']
        frames = [[(0, 0, 0) for _ in range(bones)] for _ in range(n)]
        for j, group in enumerate(bundle['tracks']):
            axes = [cls.reconstruct_audio_pcm(t, return_values=True)['values'] for t in group]
            for t in range(n):
                frames[t][j] = tuple(axis[t] for axis in axes)
        coords = [v for frame in frames for bone in frame for v in bone]
        raw = struct.pack(f'>{len(coords)}h', *coords)
        return {'byte_exact': _sha(raw) == bundle['source_sha256'],
                'sha256': _sha(raw), 'frames': frames}


    # --------------------------------------------------------------------------
    # 家族 4：結構化資料與帳本分析器 (JSON / POS 菜單 / 資料庫列)
    # --------------------------------------------------------------------------
    @staticmethod
    def analyze_structured_records(base, target):
        for records in (base, target):
            ids = [r['id'] for r in records]
            if len(ids) != len(set(ids)):
                raise ValueError('DUPLICATE_RECORD_ID')
        known = {r['id']: r for r in base}
        changed = [r for r in target if r['id'] not in known or known[r['id']] != r]
        delta = _canonical({'order': [r['id'] for r in target], 'upserts': changed})
        target_bytes = _canonical(target)
        return {'family': 'FAMILY_4_STRUCTURED_DATA', 'format_version': 2, 'static_records_skipped': len(target)-len(changed), 'base_sha256': _sha(_canonical(base)),
                'source_sha256': _sha(target_bytes), 'wire_payload': delta,
                'wire_bytes': len(delta), 'raw_bytes': len(target_bytes),
                'active_cells': len(changed)}


    @classmethod
    def _legacy_reconstruct_structured_records(cls, base_records: List[Dict[str, Any]], bundle: Dict[str, Any]) -> Dict[str, Any]:
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

    @staticmethod
    def reconstruct_structured_records(base, bundle):
        if 'base_sha256' not in bundle: return Universal8DFileEngine._legacy_reconstruct_structured_records(base, bundle)
        if _sha(_canonical(base)) != bundle['base_sha256']:
            return {'byte_exact': False, 'status': 'HOLD_BASE_HASH_MISMATCH'}
        delta = json.loads(bundle['wire_payload'])
        by_id = {r['id']: copy.deepcopy(r) for r in base}
        for r in delta['upserts']:
            by_id[r['id']] = r
        reconstructed = [by_id[i] for i in delta['order']]
        raw = _canonical(reconstructed)
        return {'byte_exact': _sha(raw) == bundle['source_sha256'],
                'sha256': _sha(raw), 'records': reconstructed}


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
