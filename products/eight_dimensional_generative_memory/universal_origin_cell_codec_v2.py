#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import gzip, hashlib, json, struct, time, zlib
from pathlib import Path

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

class OriginCellHold(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code

class UniversalOriginCellDecoder:
    MAGIC_WARM = 0x8D
    MAGIC_COLD = 0x8E
    OP_TEMPLATE_SEQ   = 0x01
    OP_LUT_RUN        = 0x02
    OP_LUT_PATTERN_2D = 0x03
    OP_RAW_REPEAT     = 0x04
    OP_RAW_ARITH_2D   = 0x05
    OP_RAW_LITERAL    = 0x06
    OP_SPARSE_PATCH   = 0x07
    ALLOWED_OPS = {1, 2, 3, 4, 5, 6, 7}

    def __init__(self):
        self.luts = {}
        self.tpls = {}
        self.packets_decoded = 0

    def cache_sha256(self) -> str:
        s = {
            "luts": {k: [x.hex() for x in v] for k, v in sorted(self.luts.items())},
            "tpls": {k: list(v) for k, v in sorted(self.tpls.items())},
        }
        return hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _read(buf: bytes, pos: int, fmt: str):
        sz = struct.calcsize(fmt)
        if pos + sz > len(buf):
            raise OriginCellHold("HOLD_PACKET_TRUNCATED")
        return struct.unpack_from(fmt, buf, pos), pos + sz

    @classmethod
    def _parse_bundle(cls, bundle: bytes):
        pos = 0
        (lc,), pos = cls._read(bundle, pos, ">B")
        if lc < 1:
            raise OriginCellHold("HOLD_EMPTY_BUNDLE")
        nl, nt = {}, {}
        for _ in range(lc):
            (lid, ec), pos = cls._read(bundle, pos, ">BB")
            if lid in nl or ec < 1:
                raise OriginCellHold("HOLD_INVALID_OR_DUPLICATE_LUT")
            ents = []
            for _ in range(ec):
                (L,), pos = cls._read(bundle, pos, ">B")
                if L < 1 or pos + L > len(bundle):
                    raise OriginCellHold("HOLD_LUT_ENTRY_TRUNCATED")
                ents.append(bundle[pos:pos + L])
                pos += L
            nl[lid] = ents
        (tc,), pos = cls._read(bundle, pos, ">B")
        for _ in range(tc):
            (tid, tl), pos = cls._read(bundle, pos, ">BB")
            if tid in nt or tl < 1:
                raise OriginCellHold("HOLD_INVALID_OR_DUPLICATE_TEMPLATE")
            vals, pos = cls._read(bundle, pos, f">{tl}b")
            nt[tid] = list(vals)
        if pos != len(bundle):
            raise OriginCellHold("HOLD_SUBSTRATE_BUNDLE_TRAILING_BYTES")
        return nl, nt

    @staticmethod
    def _strict_zlib(cb: bytes) -> bytes:
        try:
            dco = zlib.decompressobj()
            raw = dco.decompress(cb) + dco.flush()
            if not dco.eof or dco.unused_data != b"" or dco.unconsumed_tail != b"":
                raise OriginCellHold("HOLD_ZLIB_SUBSTREAM_TRAILING_BYTES")
            return raw
        except OriginCellHold:
            raise
        except Exception as e:
            raise OriginCellHold("HOLD_SUBSTRATE_DECOMPRESS_FAILED") from e

    def decode(self, pkt: bytes) -> dict:
        if not pkt:
            raise OriginCellHold("HOLD_EMPTY_PACKET")
        (m,), pos = self._read(pkt, 0, ">B")
        if m == self.MAGIC_COLD:
            (cf, bl), pos = self._read(pkt, pos, ">BH")
            if bl < 1 or pos + bl > len(pkt):
                raise OriginCellHold("HOLD_SELF_CONTAINED_BUNDLE_TRUNCATED")
            rb = pkt[pos:pos + bl]
            pos += bl
            if cf == 1:
                rb = self._strict_zlib(rb)
            elif cf != 0:
                raise OriginCellHold("HOLD_INVALID_COMPRESSION_FLAG")
            pl, pt = self._parse_bundle(rb)
            out = self._decode_mux(pkt, pos, pl, pt)
            self.luts, self.tpls = pl, pt
            self.packets_decoded += 1
            return out
        if m == self.MAGIC_WARM:
            out = self._decode_mux(pkt, 0, self.luts, self.tpls)
            self.packets_decoded += 1
            return out
        raise OriginCellHold("HOLD_INVALID_PACKET_MAGIC")

    def _decode_mux(self, buf: bytes, pos: int, luts: dict, tpls: dict) -> dict:
        (m, nch), pos = self._read(buf, pos, ">BB")
        if m != self.MAGIC_WARM or nch < 1:
            raise OriginCellHold("HOLD_INVALID_MUX_HEADER_OR_CHANNEL_COUNT")
        out = {}
        for exp_id in range(1, nch + 1):
            (tid, opc), pos = self._read(buf, pos, ">BB")
            if tid != exp_id or tid in out or opc < 1:
                raise OriginCellHold("HOLD_INVALID_TARGET_ID_OR_OP_COUNT")
            co = bytearray()
            for _ in range(opc):
                (op,), pos = self._read(buf, pos, ">B")
                if op not in self.ALLOWED_OPS:
                    raise OriginCellHold(f"HOLD_UNKNOWN_OPCODE_{op:#04x}")
                if op == 1:
                    (lid, pid, rc, cc, rep), pos = self._read(buf, pos, ">BBBBB")
                    if lid not in luts or pid not in tpls:
                        raise OriginCellHold("HOLD_MISSING_LUT_OR_TEMPLATE_ID")
                    if rc < 1 or cc < 1 or rep < 1:
                        raise OriginCellHold("HOLD_INVALID_TEMPLATE_SEQ_PARAMS")
                    lut, tpl = luts[lid], tpls[pid]
                    recs = []
                    for _ in range(rc):
                        r, pos = self._read(buf, pos, f">{cc}B")
                        recs.append(r)
                    blk = bytearray()
                    for r in recs:
                        for c in tpl:
                            if c < 0:
                                vi = -c - 1
                                if vi >= cc:
                                    raise OriginCellHold("HOLD_TEMPLATE_VAR_OUT_OF_RANGE")
                                ai = r[vi]
                            else:
                                ai = c
                            if ai >= len(lut):
                                raise OriginCellHold("HOLD_LUT_COORDINATE_OUT_OF_RANGE")
                            blk.extend(lut[ai])
                    co.extend(blk * rep)
                elif op == 2:
                    (lid, crd, cnt), pos = self._read(buf, pos, ">BBH")
                    if lid not in luts or crd >= len(luts[lid]) or cnt < 1:
                        raise OriginCellHold("HOLD_LUT_RUN_OUT_OF_RANGE")
                    co.extend(luts[lid][crd] * cnt)
                elif op == 3:
                    (lid, sc, rows), pos = self._read(buf, pos, ">BBB")
                    if lid not in luts or sc < 1 or rows < 1:
                        raise OriginCellHold("HOLD_INVALID_PATTERN_2D_HEADER")
                    rb = bytearray()
                    for _ in range(sc):
                        (crd, rl), pos = self._read(buf, pos, ">BB")
                        if crd >= len(luts[lid]) or rl < 1:
                            raise OriginCellHold("HOLD_PATTERN_2D_OUT_OF_RANGE")
                        rb.extend(luts[lid][crd] * rl)
                    co.extend(rb * rows)
                elif op == 4:
                    (pl, rep), pos = self._read(buf, pos, ">BH")
                    if pl < 1 or rep < 1 or pos + pl > len(buf):
                        raise OriginCellHold("HOLD_INVALID_RAW_REPEAT_PARAMS")
                    co.extend(buf[pos:pos + pl] * rep)
                    pos += pl
                elif op == 5:
                    (st, sp, sl, rows), pos = self._read(buf, pos, ">BBBB")
                    if sl < 1 or rows < 1:
                        raise OriginCellHold("HOLD_INVALID_ARITH_2D_PARAMS")
                    co.extend(bytes([(st + i * sp) % 256 for i in range(sl)]) * rows)
                elif op == 6:
                    (ll,), pos = self._read(buf, pos, ">H")
                    if ll < 1 or pos + ll > len(buf):
                        raise OriginCellHold("HOLD_INVALID_RAW_LITERAL")
                    co.extend(buf[pos:pos + ll])
                    pos += ll
                elif op == 7:
                    (pc,), pos = self._read(buf, pos, ">B")
                    if pc < 1:
                        raise OriginCellHold("HOLD_EMPTY_SPARSE_PATCH")
                    for _ in range(pc):
                        (off, val), pos = self._read(buf, pos, ">HB")
                        if off >= len(co):
                            raise OriginCellHold("HOLD_SPARSE_PATCH_OUT_OF_BOUNDS")
                        co[off] = val
            out[tid] = bytes(co)
        if pos != len(buf):
            raise OriginCellHold("HOLD_TRAILING_GARBAGE_BYTES")
        return out

class AutoOriginCellEncoder:
    @staticmethod
    def encode_template_channel_with_pruning(tid, lid, pid, raw, flut, ftpl):
        vslots = sorted({-c - 1 for c in ftpl if c < 0})
        if vslots != list(range(len(vslots))):
            raise OriginCellHold("HOLD_INVALID_TEMPLATE_SLOT_DEFINITION")
        nvars = len(vslots)
        lines = raw.splitlines(keepends=True)
        if not lines:
            raise OriginCellHold("HOLD_EMPTY_INPUT")
        ilut = sorted(enumerate(flut), key=lambda x: len(x[1]), reverse=True)
        rows = []
        try:
            for ln in lines:
                pos = 0
                rv = [None] * nvars
                for i, c in enumerate(ftpl):
                    if c >= 0:
                        at = flut[c]
                        if ln[pos:pos + len(at)] != at:
                            raise ValueError()
                        pos += len(at)
                    else:
                        si = -c - 1
                        if i + 1 < len(ftpl) and ftpl[i + 1] >= 0:
                            ns = flut[ftpl[i + 1]]
                            ep = ln.index(ns, pos)
                            ai = flut.index(ln[pos:ep])
                            pos = ep
                        else:
                            ai = None
                            for idx, at in ilut:
                                if ln.startswith(at, pos):
                                    ai = idx
                                    pos += len(at)
                                    break
                            if ai is None:
                                raise ValueError()
                        if rv[si] is not None and rv[si] != ai:
                            raise ValueError()
                        rv[si] = ai
                if pos != len(ln) or any(v is None for v in rv):
                    raise ValueError()
                rows.append(tuple(rv))
            nr = len(rows)
            per = next(p for p in range(1, nr + 1) if nr % p == 0 and rows[:p] * (nr // p) == rows)
            urows = [list(r) for r in rows[:per]]
            rep = nr // per
            used = sorted({c for c in ftpl if c >= 0} | {x for r in urows for x in r})
            o2n = {o: n for n, o in enumerate(used)}
            plut = [flut[i] for i in used]
            rtpl = [o2n[c] if c >= 0 else c for c in ftpl]
            rrows = [[o2n[x] for x in r] for r in urows]
            flat = [x for r in rrows for x in r]
            cw = struct.pack(f">BBBBBBBB{len(flat)}B", tid, 1, 1, lid, pid, len(rrows), nvars, rep, *flat)
            td = UniversalOriginCellDecoder()
            td.luts[lid], td.tpls[pid] = plut, rtpl
            if td.decode(struct.pack(">BBBB", 0x8D, 1, 1, 1) + cw[2:])[1] != raw:
                raise ValueError()
            return cw, plut, rtpl, len(flut) - len(plut)
        except ValueError:
            fw = struct.pack(">BBBH", tid, 1, 6, len(raw)) + raw
            return fw, [b"\x00"], [0], len(flut)

    @staticmethod
    def encode_2d_lut_channel(tid, lid, raw, lut):
        if not raw:
            raise OriginCellHold("HOLD_EMPTY_INPUT")
        al = len(lut[0])
        runs = []
        for p in range(0, len(raw), al):
            c = lut.index(raw[p:p + al])
            if runs and runs[-1][0] == c:
                runs[-1][1] += 1
            else:
                runs.append([c, 1])
        ow, oc, i = bytearray(), 0, 0
        while i < len(runs):
            if i + 3 < len(runs) and runs[i:i + 2] == runs[i + 2:i + 4]:
                pat, rws = runs[i:i + 2], 0
                while i + 1 < len(runs) and runs[i:i + 2] == pat:
                    rws += 1
                    i += 2
                ow.extend(struct.pack(">BBBBBBBB", 3, lid, 2, rws, pat[0][0], pat[0][1], pat[1][0], pat[1][1]))
                oc += 1
            else:
                ow.extend(struct.pack(">BBBH", 2, lid, runs[i][0], runs[i][1]))
                oc += 1
                i += 1
        return struct.pack(">BB", tid, oc) + bytes(ow)

    @staticmethod
    def encode_motion_channel_with_sparse_patch(tid: int, raw: bytes) -> bytes:
        if not raw:
            raise OriginCellHold("HOLD_EMPTY_INPUT")
        if len(raw) > 65535:
            raise OriginCellHold("HOLD_CHANNEL_EXCEEDS_UINT16_OFFSET_SPACE")
        segs = [raw[i:i + 1040] for i in range(0, len(raw), 1040)]
        bops, rbase, oc = bytearray(), bytearray(), 0
        for seg in segs:
            v1 = seg[0] if (len(seg) < 3 or seg[0] == seg[1] or seg[0] == seg[2]) else seg[1]
            cands = [(bytes([v1]) * len(seg), struct.pack(">BBHB", 4, 1, len(seg), v1))]
            if len(seg) >= 4 and len(seg) % 4 == 0:
                p4 = seg[:4] if (len(seg) < 8 or seg[:4] == seg[4:8]) else seg[4:8]
                cands.append((p4 * (len(seg) // 4), struct.pack(">BBH4B", 4, 4, len(seg) // 4, *p4)))
            if len(seg) >= 52 and len(seg) % 52 == 0:
                rr = seg[:52] if (len(seg) < 104 or seg[:52] == seg[52:104]) else seg[52:104]
                st, sp = rr[0], (rr[1] - rr[0]) % 256
                rw = bytes([(st + i * sp) % 256 for i in range(52)])
                cands.append((rw * (len(seg) // 52), struct.pack(">BBBBB", 5, st, sp, 52, len(seg) // 52)))
            bb, bo = min(cands, key=lambda x: sum(1 for a, b in zip(x[0], seg) if a != b))
            df = sum(1 for a, b in zip(bb, seg) if a != b)
            if len(bo) + df * 3 + ((df + 254) // 255) * 2 < len(seg) + 3:
                bops.extend(bo)
                rbase.extend(bb)
            else:
                bops.extend(struct.pack(">BH", 6, len(seg)) + seg)
                rbase.extend(seg)
            oc += 1
        gdiffs = [(idx, b) for idx, (a, b) in enumerate(zip(rbase, raw)) if a != b]
        for bs in range(0, len(gdiffs), 255):
            bat = gdiffs[bs:bs + 255]
            pb = bytearray([7, len(bat)])
            for off, val in bat:
                pb.extend(struct.pack(">HB", off, val))
            bops.extend(pb)
            oc += 1
        if oc > 255:
            return struct.pack(">BBBH", tid, 1, 6, len(raw)) + raw
        return struct.pack(">BB", tid, oc) + bytes(bops)

    @staticmethod
    def pack_bundle(ld: dict, td: dict) -> bytes:
        out = bytearray([len(ld)])
        for lid, ents in ld.items():
            out.extend([lid, len(ents)])
            for e in ents:
                out.append(len(e))
                out.extend(e)
        out.append(len(td))
        for tid, tpl in td.items():
            out.extend([tid, len(tpl)])
            out.extend(struct.pack(f">{len(tpl)}b", *tpl))
        return bytes(out)

if __name__ == "__main__":
    lut_c1 = [
        b'{"company_id":3,"shop":"', b'","item":"', b'","options":[', b'],"price":',
        b',"voucher_op":"', b'","before":', b',"after":', b',"state":"', b'"}\n',
        b'"', b',', "上品聊國重新總店".encode(), "錫蘭紅茶".encode(), "招牌拿鐵".encode(),
        "厚片吐司".encode(), "微冰".encode(), "半糖".encode(), "加購起司".encode(),
        "燕麥奶升級".encode(), b"35", b"45", b"55", b"65", b"80", b"10", b"9", b"0",
        b"XJ-021_REDEEM", b"HOLD_PHONE_MATCH_FAILED", b"PASS_EFFECT_VERIFIED"
    ]
    tpl_c1 = [0, 11, 1, -1, 2, 9, -2, 9, 10, 9, -3, 9, 3, -4, 4, 27, 5, 24, 6, -5, 7, -6, 8]
    raw_c1 = b"".join([
        '{"company_id":3,"shop":"上品聊國重新總店","item":"錫蘭紅茶","options":["微冰","半糖"],"price":35,"voucher_op":"XJ-021_REDEEM","before":10,"after":9,"state":"PASS_EFFECT_VERIFIED"}\n'.encode() +
        '{"company_id":3,"shop":"上品聊國重新總店","item":"招牌拿鐵","options":["微冰","燕麥奶升級"],"price":80,"voucher_op":"XJ-021_REDEEM","before":10,"after":10,"state":"HOLD_PHONE_MATCH_FAILED"}\n'.encode()
        for _ in range(16)
    ])
    lut_c2 = [bytes([245, 240, 230]), bytes([42, 28, 20]), bytes([185, 65, 35]), bytes([255, 215, 140])]
    raw_c2 = lut_c2[0]*1024 + (lut_c2[1]*32 + lut_c2[2]*32)*32 + lut_c2[3]*1024
    raw_c3 = bytes([10, 12, 14, 12])*260 + bytes([(20 + i*2)%256 for i in range(52)])*20 + bytes([180])*1040
    lut_c4 = [
        b"W7TP_OP|", b"taiji01->taiji03|", b"taiji01->taiji02|",
        b"order.candidate.create.v1|", b"anchor.render_state.v1|",
        b"pos.formal.submit.request.v1|", b"CANDIDATE_ONLY|",
        b"HOLD_OPERATOR_CONFIRM|", b"NO_PLAINTEXT_CLOUD=TRUE\n"
    ]
    tpl_c4 = [0, -1, -2, -3, 8]
    raw_c4 = b"".join([
        b"W7TP_OP|taiji01->taiji03|order.candidate.create.v1|CANDIDATE_ONLY|NO_PLAINTEXT_CLOUD=TRUE\n" +
        b"W7TP_OP|taiji01->taiji02|anchor.render_state.v1|CANDIDATE_ONLY|NO_PLAINTEXT_CLOUD=TRUE\n" +
        b"W7TP_OP|taiji01->taiji03|pos.formal.submit.request.v1|HOLD_OPERATOR_CONFIRM|NO_PLAINTEXT_CLOUD=TRUE\n"
        for _ in range(10)
    ])
    w1, pl1, pt1, pr1 = AutoOriginCellEncoder.encode_template_channel_with_pruning(1, 1, 1, raw_c1, lut_c1, tpl_c1)
    w2 = AutoOriginCellEncoder.encode_2d_lut_channel(2, 2, raw_c2, lut_c2)
    w3 = AutoOriginCellEncoder.encode_motion_channel_with_sparse_patch(3, raw_c3)
    w4, pl4, pt4, _ = AutoOriginCellEncoder.encode_template_channel_with_pruning(4, 4, 4, raw_c4, lut_c4, tpl_c4)
    warm = struct.pack(">BB", 0x8D, 4) + w1 + w2 + w3 + w4
    rb = AutoOriginCellEncoder.pack_bundle({1: pl1, 2: lut_c2, 4: pl4}, {1: pt1, 4: pt4})
    cb = zlib.compress(rb, 9)
    cold = struct.pack(">BBH", 0x8E, 1, len(cb)) + cb + warm
    dec = UniversalOriginCellDecoder()
    r1 = dec.decode(cold)
    r2 = dec.decode(warm)
    m256 = bytearray(raw_c3)
    for i in range(2090, 2090 + 256): m256[i] = (m256[i] + 1) % 256
    w256 = AutoOriginCellEncoder.encode_motion_channel_with_sparse_patch(1, bytes(m256))
    d256 = UniversalOriginCellDecoder().decode(struct.pack(">BB", 0x8D, 1) + w256)[1]
    len_ok = all(
        UniversalOriginCellDecoder().decode(
            struct.pack(">BB", 0x8D, 1) + AutoOriginCellEncoder.encode_motion_channel_with_sparse_patch(1, raw_c3[:L])
        )[1] == raw_c3[:L]
        for L in (1, 52, 1040, 2080, 3120)
    )
    p = Path(__file__).resolve()
    rec = {
        "schema": "w7tp.origin-cell-codec-v2.1.receipt/2.3",
        "module_path": str(p),
        "module_sha256": sha256_hex(p.read_bytes()),
        "cold_zlib_bytes": len(cold),
        "warm_mux_bytes": len(warm),
        "pruned_c1_entries": pr1,
        "all_4_channels_byte_exact": (r1[1]==raw_c1 and r1[2]==raw_c2 and r1[3]==raw_c3 and r1[4]==raw_c4 and r2 == r1),
        "patch_256_mutations_byte_exact": d256 == bytes(m256),
        "lengths_1_52_1040_2080_3120_byte_exact": len_ok
    }
    rp = p.parent / "UNIVERSAL_ORIGIN_CELL_CODEC_V2_RECEIPT_20261021.json"
    rp.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec, indent=2))
