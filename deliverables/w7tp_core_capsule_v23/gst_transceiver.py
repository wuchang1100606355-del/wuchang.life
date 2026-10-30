#!/usr/bin/env python3
"""
8D 原胞狀態傳輸：具備確定性分析及純 CPU 合成能力的雙向收發器 (Symmetric Bidirectional Transceiver)
支援模式：
  1. encode (正向分析)：標的物辨識 -> 求同(基座/靜止) -> 存異(單量/總量/變化量/速度 & 抗位移差值) -> 產出 .8dcell 封包
  2. decode (逆向合成)：D8 權威與基座指紋守門 -> 純 CPU 對號入座重構 -> local_discrete_state_verifier 雜湊驗收
  3. roundtrip (雙向閉環自檢)：單指令完成「分析 -> 封包落盤 -> 合成還原 -> Byte-Exact 驗證收據」
"""
import argparse
import hashlib
import json
import os
import struct
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

MAGIC_HEADER = b"8DGSTv23"

class GSTBidirectionalTransceiver:

    # ==========================================================================
    # 【通道 A：檔案與高熵二進位雙向引擎】(含前後綴抗位移錨點辨識 + 區塊指紋求同存異)
    # ==========================================================================
    @classmethod
    def encode_file_state(cls, base_bytes: bytes, target_bytes: bytes, d8_token: str = "D8_PASS") -> Dict[str, Any]:
        """【正向分析器】：比較接收端基座 (base_bytes) 與目標檔案 (target_bytes)，產出最小 .8dcell 二進位封包"""
        if not d8_token.startswith("D8_"):
            return {"status": "HOLD_D8_AUTHORITY_REQUIRED", "cell_packet": b"", "wire_bytes": 0}

        base_hash = hashlib.sha256(base_bytes).digest()
        target_hash = hashlib.sha256(target_bytes).digest()

        # 1. 完全靜止判定 (求同：100% 未變更)
        if base_hash == target_hash:
            # 封包格式: MAGIC(8B) + Mode=0(1B) + BaseHash(32B) + TargetHash(32B) + TotalLen(4B) = 77 Bytes
            pkt = MAGIC_HEADER + struct.pack(">B32s32sI", 0, base_hash, target_hash, len(target_bytes))
            return {
                "status": "ENCODED_MODE_0_STATIC_LOCK",
                "mode": "MODE_0_FULL_STATIC",
                "raw_bytes": len(target_bytes),
                "wire_bytes": len(pkt),
                "cell_packet": pkt,
                "base_sha256": base_hash.hex(),
                "target_sha256": target_hash.hex()
            }

        # 2. 抗位移前後綴標的物辨識 (Shift-Invariant Prefix/Suffix Anchor Probe)
        prefix_len = 0
        min_len = min(len(base_bytes), len(target_bytes))
        while prefix_len < min_len and base_bytes[prefix_len] == target_bytes[prefix_len]:
            prefix_len += 1

        suffix_len = 0
        while (suffix_len < (min_len - prefix_len)) and (
            base_bytes[len(base_bytes) - 1 - suffix_len] == target_bytes[len(target_bytes) - 1 - suffix_len]
        ):
            suffix_len += 1

        mid_target = target_bytes[prefix_len : len(target_bytes) - suffix_len]
        mid_base = base_bytes[prefix_len : len(base_bytes) - suffix_len]

        # 計算「抗位移單一區間原胞 (Mode 1)」大小
        mode1_pkt = (
            MAGIC_HEADER
            + struct.pack(
                ">B32s32sIIII",
                1, base_hash, target_hash,
                prefix_len, len(base_bytes) - suffix_len, suffix_len, len(mid_target)
            )
            + mid_target
        )

        # 計算「多點區塊求同存異原胞 (Mode 2)」大小 (適用於多處分散局部修改)
        block_size = 256
        b_chunks = [mid_base[i:i+block_size] for i in range(0, len(mid_base), block_size)]
        t_chunks = [mid_target[i:i+block_size] for i in range(0, len(mid_target), block_size)]
        diff_subpkts = []
        for idx, chk in enumerate(t_chunks):
            if idx < len(b_chunks) and b_chunks[idx] == chk:
                continue
            diff_subpkts.append(struct.pack(">II", idx, len(chk)) + chk)

        mode2_body = b"".join(diff_subpkts)
        mode2_pkt = (
            MAGIC_HEADER
            + struct.pack(
                ">B32s32sIIIIII",
                2, base_hash, target_hash,
                prefix_len, len(base_bytes) - suffix_len, suffix_len,
                block_size, len(t_chunks), len(mid_target)
            )
            + struct.pack(">I", len(diff_subpkts))
            + mode2_body
        )

        # 確定性最優選路：自動選擇位元組數最小之原胞封裝模式
        if len(mode1_pkt) <= len(mode2_pkt):
            chosen_pkt, mode_name = mode1_pkt, "MODE_1_SHIFT_ANCHOR_CELL"
        else:
            chosen_pkt, mode_name = mode2_pkt, "MODE_2_MULTIBLOCK_DELTA_CELL"

        return {
            "status": "ENCODED_ORIGIN_CELL_READY",
            "mode": mode_name,
            "raw_bytes": len(target_bytes),
            "wire_bytes": len(chosen_pkt),
            "prefix_static_bytes": prefix_len,
            "suffix_shifted_bytes": suffix_len,
            "cell_packet": chosen_pkt,
            "base_sha256": base_hash.hex(),
            "target_sha256": target_hash.hex()
        }

    @classmethod
    def decode_file_state(cls, base_bytes: bytes, cell_packet: bytes, d8_token: str = "D8_PASS") -> Dict[str, Any]:
        """【逆向合成器 + 本地離散狀態驗證器 (local_discrete_state_verifier)】"""
        if not d8_token.startswith("D8_"):
            return {"status": "HOLD_D8_AUTHORITY_REQUIRED", "byte_exact": False}
        if not cell_packet.startswith(MAGIC_HEADER):
            return {"status": "HOLD_INVALID_PACKET_MAGIC", "byte_exact": False}

        mode = cell_packet[8]
        expected_base_hash = cell_packet[9:41]
        expected_target_hash = cell_packet[41:73]

        # D3/D4 基座一致性守門：若接收端本地基座與發送端基座指紋不符，立即觸發 HOLD 隔離
        actual_base_hash = hashlib.sha256(base_bytes).digest()
        if actual_base_hash != expected_base_hash:
            return {
                "status": "HOLD_BASE_HASH_MISMATCH",
                "byte_exact": False,
                "expected_base": expected_base_hash.hex()[:16],
                "actual_base": actual_base_hash.hex()[:16]
            }

        if mode == 0:
            (total_len,) = struct.unpack(">I", cell_packet[73:77])
            recon_bytes = base_bytes[:total_len]

        elif mode == 1:
            p_len, b_suf_start, s_len, mid_len = struct.unpack(">IIII", cell_packet[73:89])
            mid_payload = cell_packet[89 : 89 + mid_len]
            recon_bytes = base_bytes[:p_len] + mid_payload + base_bytes[b_suf_start : b_suf_start + s_len]

        elif mode == 2:
            p_len, b_suf_start, s_len, bs, total_chunks, mid_len, diff_cnt = struct.unpack(">IIIIIII", cell_packet[73:101])
            mid_base = base_bytes[p_len:b_suf_start]
            b_chunks = [mid_base[i:i+bs] for i in range(0, len(mid_base), bs)]
            recon_chunks = [b_chunks[i] if i < len(b_chunks) else b"" for i in range(total_chunks)]

            offset = 101
            for _ in range(diff_cnt):
                c_idx, c_len = struct.unpack(">II", cell_packet[offset : offset + 8])
                offset += 8
                recon_chunks[c_idx] = cell_packet[offset : offset + c_len]
                offset += c_len
            mid_recon = b"".join(recon_chunks)[:mid_len]
            recon_bytes = base_bytes[:p_len] + mid_recon + base_bytes[b_suf_start : b_suf_start + s_len]
        else:
            return {"status": "HOLD_UNKNOWN_MODE", "byte_exact": False}

        # 本地離散狀態驗證器 (local_discrete_state_verifier)：強制驗算重構後 SHA-256
        recon_hash = hashlib.sha256(recon_bytes).digest()
        is_exact = (recon_hash == expected_target_hash)

        return {
            "status": "LOCAL_RECONSTRUCTION_VERIFIED" if is_exact else "HOLD_RECONSTRUCTION_HASH_MISMATCH",
            "verifier": "local_discrete_state_verifier",
            "byte_exact": is_exact,
            "reconstructed_bytes": len(recon_bytes),
            "wire_bytes": len(cell_packet),
            "sha256": recon_hash.hex(),
            "payload": recon_bytes if is_exact else b""
        }

    # ==========================================================================
    # 【通道 B：時序數值／視覺發光點／音訊雙向引擎】(單量、總量、變化量、速度)
    # ==========================================================================
    @classmethod
    def encode_temporal_series(cls, series: List[int]) -> bytes:
        """將一維整數時序流 (音訊振幅/亮度軌跡) 拆解為『靜止時間 + 變動時間 + 單量/變化量/速度』雙向原胞封包"""
        raw_bytes = struct.pack(f">{len(series)}i", *series)
        src_hash = hashlib.sha256(raw_bytes).digest()
        cells = []
        n = len(series)
        i = 0
        while i < n:
            v0 = series[i]
            dt_static = 1
            while (i + dt_static) < n and series[i + dt_static] == v0:
                dt_static += 1
            rem = i + dt_static
            dt_active = 0
            vel = 0
            if rem < n:
                vel = series[rem] - v0
                cur = v0
                while (rem + dt_active) < n and (series[rem + dt_active] - cur) == vel:
                    cur = series[rem + dt_active]
                    dt_active += 1
            net_delta = vel * dt_active
            cells.append(struct.pack(">IIIiii", i, dt_static, dt_active, v0, net_delta, vel))
            i += dt_static + dt_active
        return MAGIC_HEADER + struct.pack(">B32sII", 10, src_hash, n, len(cells)) + b"".join(cells)

    @classmethod
    def decode_temporal_series(cls, packet: bytes) -> Dict[str, Any]:
        """從時序原胞封包逆向由 CPU 合成完整序列並驗證雜湊"""
        _, src_hash, total_n, cell_cnt = struct.unpack(">B32sII", packet[8:49])
        recon = [0] * total_n
        offset = 49
        for _ in range(cell_cnt):
            coord_i, dt_s, dt_a, v0, net_delta, vel = struct.unpack(">IIIiii", packet[offset:offset+24])
            offset += 24
            for s in range(dt_s):
                recon[coord_i + s] = v0
            for a in range(1, dt_a + 1):
                recon[coord_i + dt_s + a - 1] = v0 + vel * a
        recon_bytes = struct.pack(f">{len(recon)}i", *recon)
        r_hash = hashlib.sha256(recon_bytes).digest()
        return {
            "status": "LOCAL_RECONSTRUCTION_VERIFIED" if r_hash == src_hash else "HOLD_HASH_MISMATCH",
            "byte_exact": r_hash == src_hash,
            "raw_bytes": len(recon_bytes),
            "wire_bytes": len(packet),
            "cell_count": cell_cnt,
            "sha256": r_hash.hex()
        }


if __name__ == "__main__":
    print("=== 【8D 雙向原胞狀態收發器 (gst_transceiver.py)｜正向分析 × 逆向 CPU 合成實測】 ===")
    hub = Path("/home/taiji_admin/Taiji_Hub")

    # 實測 1：拿當前開啟的真實商業素材包 (或正典文件) 進行「中間插入新段落 + 尾部更新」雙向閉環測試
    candidates = list(hub.rglob("LIAOGUO_GEMINI_COMMERCIAL_PACK_20261021.md")) + [hub / "WUCHANG_GOOGLE_AI_SHARING_ECONOMY_PILOT_20261022.md"]
    real_doc = next((p for p in candidates if p.exists()), None)
    base_data = real_doc.read_bytes() if real_doc else b"W7TP 8D ADI Canonical Base Content\n" * 2000
    doc_name = real_doc.name if real_doc else "Synthetic_Canonical_Base.md"

    # 模擬在真實大檔案的中間 (第 5000 Byte 處) 插入一段 48 Bytes 的新業務狀態，造成後方所有文字座標位移
    insert_pos = min(5000, len(base_data) // 2)
    inserted_state = b"\n<!-- [8D_ORIGIN_CELL_BIDIRECTIONAL_UPDATE] -->\n"
    target_data = base_data[:insert_pos] + inserted_state + base_data[insert_pos:]

    # Step 1: 發送端執行正向分析 (encode) -> 落盤為 .8dcell 封包檔
    enc_res = GSTBidirectionalTransceiver.encode_file_state(base_data, target_data, d8_token="D8_PASS_LOCAL")
    cell_file = hub / "latest_state_transfer.8dcell"
    cell_file.write_bytes(enc_res["cell_packet"])

    # Step 2: 接收端讀取 .8dcell 封包檔執行逆向 CPU 合成 (decode) 與本地驗證
    dec_res = GSTBidirectionalTransceiver.decode_file_state(base_data, cell_file.read_bytes(), d8_token="D8_PASS_LOCAL")

    # Step 3: 測試基座失配時的自動攔截保護 (故意傳入錯誤基座)
    hold_res = GSTBidirectionalTransceiver.decode_file_state(b"WRONG_BASE_CONTENT", cell_file.read_bytes(), d8_token="D8_PASS_LOCAL")

    print(f"\n🔄 [雙向實測 1：真實知識庫大檔 ({doc_name}) 抗位移雙向收發]")
    print(f"   • 【正向分析 encode】原始目標大小：{enc_res['raw_bytes']:,} Bytes -> 選用模式：{enc_res['mode']}")
    print(f"   • 【求同存異拆解】   前半靜止錨點：{enc_res['prefix_static_bytes']:,} B | 後半平移錨點：{enc_res['suffix_shifted_bytes']:,} B")
    print(f"   • 【封包落盤大小】   {cell_file.name} = {enc_res['wire_bytes']} Bytes (減量 {(1 - enc_res['wire_bytes']/enc_res['raw_bytes'])*100:.3f}%)")
    print(f"   • 【逆向合成 decode】驗證器狀態：{dec_res['status']} ({dec_res['verifier']})")
    print(f"   • 【端到端 SHA-256】 100% Byte-Exact = {dec_res['byte_exact']} ({dec_res['sha256'][:16]}...)")
    print(f"   • 【基座失配守門】   當基座不符時自動觸發：{hold_res['status']}")

    # 實測 2：時序雙向引擎 (10,000 點感測/音訊/亮度序列：正向分析 -> 逆向合成)
    series_data = [50] * 3000 + [50 + i * 5 for i in range(1, 2001)] + [10050] * 3000 + [10050 - i * 5 for i in range(1, 2001)]
    ts_pkt = GSTBidirectionalTransceiver.encode_temporal_series(series_data)
    ts_dec = GSTBidirectionalTransceiver.decode_temporal_series(ts_pkt)
    print(f"\n📈 [雙向實測 2：10,000 點時序狀態流 (單量/總量/變化量/速度) 雙向收發]")
    print(f"   • 【正向分析 encode】原始資料量：{ts_dec['raw_bytes']:,} Bytes -> 萃取原胞：{ts_dec['cell_count']} 顆 | 封包：{ts_dec['wire_bytes']} Bytes")
    print(f"   • 【逆向合成 decode】驗證器狀態：{ts_dec['status']} | 100% Byte-Exact = {ts_dec['byte_exact']} ({ts_dec['sha256'][:16]}...)")
