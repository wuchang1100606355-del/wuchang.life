# -*- coding: utf-8 -*-
"""
W7TP / 8D ADI V2.3 — XiaoJ Tri-Tier Brain & Visual Choreography Router
Tier 0: Prebaked 72B Origin Cells (<0.4ms, NT$0)
Tier 1: Local LAN LLM / Commercial Knowledge Graph (NT$0)
Tier 2: Cloud Commercial Brain (GCP Project my-j-483304 -> discoveryengine.googleapis.com ONLY, gated)
"""
from __future__ import annotations
import hashlib, json, struct, time, urllib.request
import pathlib as P
from core.google_credit_discovery_channel import (
    CREDIT_ID,
    PII_PATTERNS,
    PROJECT_ID,
    ALLOWED_DATA_STORES,
    build_converse_endpoint,
    query_discovery_credit_channel,
)

PREBAKED_PATH = P.Path("/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/wuchang_ordering_ui_suite/static/src/data/xiaoj_prebaked_cells.json")
MAX_QUERY_LEN = 300
WIRE_CELL_SIZE = 72

SYSTEM_PROMPT = (
    "你是『聊國咖啡・重新總店 (LOGECOFFEE)』的 2.5D 高仿真 AI 主播店長『小J』。"
    "請用溫柔、專業、充滿魅力的台灣繁體中文回答客人的點餐與咖啡問題（控制在 55 字以內），"
    "並主動推薦店內高毛利招牌（如：招牌咖啡 85元、本店招牌精品咖啡、手工甜點搭售折 15元）。"
)


def pack_72b_origin_cell(cell_key: str, cell: dict) -> bytes:
    """將單一預烘焙原胞封裝為精確 72 Bytes 二進位原胞封包 (Magic 4B + Price 2B + Flags 2B + KeyHash 16B + CellIDHash 16B + PayloadSHA256 32B = 72B)."""
    magic = b"W7C0"
    price = int(cell.get("price") or 0) & 0xFFFF
    flags = 1 if cell.get("cell_kind") == "PRODUCT_ITEM" else 2
    key_hash16 = hashlib.sha256(str(cell_key).encode("utf-8")).digest()[:16]
    cid_hash16 = hashlib.sha256(str(cell.get("cell_id") or "").encode("utf-8")).digest()[:16]
    payload_sha = hashlib.sha256(
        json.dumps(cell, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).digest()
    pkt = struct.pack(">4sHH16s16s32s", magic, price, flags, key_hash16, cid_hash16, payload_sha)
    if len(pkt) != WIRE_CELL_SIZE:
        raise ValueError(f"packed cell size mismatch: {len(pkt)}")
    return pkt


def reconstruct_from_72b_origin_cell(packet: bytes, atlas_cells: dict) -> dict:
    """於接收端驗證 72 Bytes 原胞封包並確定性重構完整原胞狀態."""
    if not isinstance(packet, (bytes, bytearray)) or len(packet) != WIRE_CELL_SIZE:
        raise ValueError("HOLD_INVALID_72B_PACKET_LENGTH")
    magic, price, flags, key_hash16, cid_hash16, payload_sha = struct.unpack(">4sHH16s16s32s", bytes(packet))
    if magic != b"W7C0":
        raise ValueError("HOLD_INVALID_72B_PACKET_MAGIC")
    for k, cell in atlas_cells.items():
        if (
            hashlib.sha256(str(k).encode("utf-8")).digest()[:16] == key_hash16
            and hashlib.sha256(str(cell.get("cell_id") or "").encode("utf-8")).digest()[:16] == cid_hash16
        ):
            calc_sha = hashlib.sha256(
                json.dumps(cell, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).digest()
            if calc_sha != payload_sha or (int(cell.get("price") or 0) & 0xFFFF) != price:
                raise ValueError("HOLD_72B_CELL_HASH_MISMATCH")
            return {
                "state": "PASS_72B_ORIGIN_CELL_RECONSTRUCTED",
                "wire_bytes": len(packet),
                "cell_key": k,
                "cell": cell,
                "contains_member_plaintext": False,
            }
    raise ValueError("HOLD_72B_CELL_NOT_FOUND")


def _build_visual_choreography(reply_text: str, tier: str) -> list:
    timeline = [{"t_ms": 0, "pose": "smile", "note": "開場微笑對焦"}]
    if any(k in reply_text for k in ["眼光", "太棒", "招牌", "驚喜", "超人氣", "必點", "特惠"]):
        timeline.append({"t_ms": 350, "pose": "surprise", "note": "亮點驚喜破冰"})
        timeline.append({"t_ms": 1100, "pose": "happy", "note": "熱情推薦"})
    elif any(k in reply_text for k in ["熱", "溫暖", "無糖", "低咖啡因", "貼心", "為您"]):
        timeline.append({"t_ms": 400, "pose": "care", "note": "貼心關懷眼神"})
        timeline.append({"t_ms": 1300, "pose": "comfort", "note": "溫柔安撫"})
    else:
        timeline.append({"t_ms": 500, "pose": "focus", "note": "專業解說"})
    timeline.append({"t_ms": 2200, "pose": "wink", "note": "促銷放電單眼眨眼"})
    timeline.append({"t_ms": 2650, "pose": "happy", "note": "燦爛笑容收尾"})
    timeline.append({"t_ms": 3600, "pose": "gaze_right", "note": "眼神引導右方購物車結帳"})
    timeline.append({"t_ms": 4400, "pose": "smile", "note": "回歸主播待機微笑"})
    return timeline


def _try_local_llm(query: str):
    endpoints = [
        "http://127.0.0.1:11434/api/generate",
        "http://192.168.50.82:11435/api/generate",
    ]
    for url in endpoints:
        try:
            payload = json.dumps({
                "model": "qwen2.5:7b",
                "prompt": f"{SYSTEM_PROMPT}\n客人說：{query}\n小J回覆：",
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 90}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=0.15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = (data.get("response") or "").strip()
                if ans:
                    return {
                        "ok": True,
                        "state": "PASS_TIER1_LOCAL_LLM",
                        "tier": "TIER1_LOCAL_LLM",
                        "endpoint": url,
                        "reply": ans,
                        "cost_twd": 0.0,
                        "cost_evidence": "LOCAL_LAN_ZERO_BILLING",
                        "contains_member_plaintext": False,
                    }
        except Exception:
            continue
    return None


def _try_discovery_engine_commercial_brain(
    query: str,
    *,
    seat_ref: str | None = None,
    authority_scope: str | None = None,
    data_store_id: str = "wuchang-menu-64",
    execute_network: bool = False,
):
    if data_store_id not in ALLOWED_DATA_STORES:
        return {
            "ok": False,
            "state": "HOLD_UNAPPROVED_DATA_STORE",
            "contains_member_plaintext": False,
        }
    res = query_discovery_credit_channel(
        query,
        data_store_id=data_store_id,
        execute_network=execute_network,
        seat_ref=seat_ref,
        authority_scope=authority_scope,
    )
    if res.get("state") != "PASS_DISCOVERY_ENGINE_CREDIT_CALL":
        return {"ok": False, **res}
    cdata = res.get("data") or {}
    ans = ((cdata.get("reply") or {}).get("summary") or {}).get("summaryText") or ""
    if not ans.strip():
        return {"ok": False, "state": "HOLD_EMPTY_CLOUD_SUMMARY", "contains_member_plaintext": False}
    return {
        "ok": True,
        "state": "PASS_TIER2_CLOUD_DISCOVERY",
        "tier": "TIER2_CLOUD_DISCOVERY_ENGINE_CREDIT",
        "endpoint": build_converse_endpoint(data_store_id),
        "reply": ans.strip(),
        "cost_twd": 0.0,
        "cost_evidence": "UNVERIFIED_PROVIDER_BILLING_ESTIMATE",
        "credit_id": CREDIT_ID,
        "contains_member_plaintext": False,
    }


def route_xiaoj_brain(
    query: str,
    *,
    allow_cloud: bool = False,
    seat_ref: str | None = None,
    authority_scope: str | None = None,
) -> dict:
    t0 = time.perf_counter()
    if not isinstance(query, str):
        return {
            "ok": False,
            "state": "HOLD_EMPTY_OR_INVALID_QUERY",
            "reason": "query must be a string",
            "contains_member_plaintext": False,
        }
    q = query.strip()
    if not q or len(q) > MAX_QUERY_LEN:
        return {
            "ok": False,
            "state": "HOLD_EMPTY_OR_INVALID_QUERY",
            "reason": "query must be 1..300 characters",
            "contains_member_plaintext": False,
        }
    if PII_PATTERNS.search(q):
        return {
            "ok": False,
            "state": "HOLD_MEMBER_PLAINTEXT_DETECTED",
            "reason": "plaintext member PII is forbidden",
            "contains_member_plaintext": False,
        }

    # 1. 先查 0.4ms 本地預烘焙 72B 原胞庫（精確命中優先；多重部分命中明確回傳消歧 HOLD）
    if PREBAKED_PATH.exists():
        try:
            cells = json.loads(PREBAKED_PATH.read_text(encoding="utf-8")).get("cells", {})
            if q in cells:
                cell = cells[q]
                pkt = pack_72b_origin_cell(q, cell)
                ms = round((time.perf_counter() - t0) * 1000, 2)
                reply = cell["spoken_line"]
                return {
                    "ok": True,
                    "state": "PASS_TIER0_PREBAKED_EXACT",
                    "tier": "TIER0_PREBAKED_72B_CELL",
                    "cell_id": cell["cell_id"],
                    "wire_bytes": len(pkt),
                    "latency_ms": ms,
                    "cost_twd": 0.0,
                    "cost_evidence": "LOCAL_STATIC_ORIGIN_CELL",
                    "contains_member_plaintext": False,
                    "reply": reply,
                    "choreography": _build_visual_choreography(reply, "TIER0"),
                }
            # 僅對商品格做子字串匹配
            prod_matches = [
                (item_name, cell)
                for item_name, cell in cells.items()
                if cell.get("cell_kind") == "PRODUCT_ITEM" and (item_name in q or (len(q) >= 2 and q in item_name))
            ]
            if len(prod_matches) == 1:
                item_name, cell = prod_matches[0]
                pkt = pack_72b_origin_cell(item_name, cell)
                ms = round((time.perf_counter() - t0) * 1000, 2)
                reply = cell["spoken_line"]
                return {
                    "ok": True,
                    "state": "PASS_TIER0_PREBAKED_UNIQUE_PARTIAL",
                    "tier": "TIER0_PREBAKED_72B_CELL",
                    "cell_id": cell["cell_id"],
                    "wire_bytes": len(pkt),
                    "latency_ms": ms,
                    "cost_twd": 0.0,
                    "cost_evidence": "LOCAL_STATIC_ORIGIN_CELL",
                    "contains_member_plaintext": False,
                    "reply": reply,
                    "choreography": _build_visual_choreography(reply, "TIER0"),
                }
            if len(prod_matches) > 1 and not any(k in q for k in ["推薦", "下午茶", "套餐", "搭", "冷", "熱", "無糖", "故事", "誰"]):
                candidates = [m[0] for m in prod_matches[:5]]
                return {
                    "ok": False,
                    "state": "HOLD_AMBIGUOUS_PREBAKED_QUERY",
                    "tier": "TIER0_DISAMBIGUATION_REQUIRED",
                    "candidates": candidates,
                    "contains_member_plaintext": False,
                    "reply": f"請問您想了解的是哪一款呢？目前符合的有：{'、'.join(candidates)}。",
                }
        except Exception:
            pass

    fast_keywords = ["冷", "熱", "溫暖", "天氣", "甜", "下午茶", "套餐", "搭", "推薦", "高毛利", "無糖", "健康", "低卡", "美式", "酸", "故事", "聊國", "品牌", "重新", "誰", "你好", "嗨"]
    if not any(k in q for k in fast_keywords):
        local_res = _try_local_llm(q)
        if local_res:
            local_res["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            local_res["choreography"] = _build_visual_choreography(local_res["reply"], "TIER1")
            return local_res

        if allow_cloud:
            cloud_res = _try_discovery_engine_commercial_brain(
                q,
                seat_ref=seat_ref,
                authority_scope=authority_scope,
                execute_network=True,
            )
            if cloud_res.get("ok"):
                cloud_res["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                cloud_res["choreography"] = _build_visual_choreography(cloud_res["reply"], "TIER2")
                return cloud_res
            return cloud_res

    if any(k in q for k in ["冷", "熱", "溫暖", "天氣"]):
        reply = "今天微涼，特別為您推薦熱『招牌咖啡』(85元) 或綿密的『熱咖啡拿鐵』，再搭一份熱壓吐司現折 15 元，暖心又暖胃喔！"
    elif any(k in q for k in ["甜", "下午茶", "套餐", "搭", "推薦", "高毛利"]):
        reply = "太有眼光了！午後首選『手沖精品咖啡』搭配我們的主廚焦糖布丁，組合特惠現省 15 元，香氣層次超迷人，幫您加進右邊購物車好嗎？"
    elif any(k in q for k in ["無糖", "健康", "低卡", "美式", "酸"]):
        reply = "喜歡清爽無負擔的話，強推我們的『本店招牌精品咖啡』或『純萃美式』，果香明亮回甘、零負擔，非常適合現在享用喔！"
    elif any(k in q for k in ["故事", "聊國", "品牌", "重新", "誰"]):
        reply = "歡迎來到聊國咖啡重新總店！我是結合 W7TP 72B 原胞傳輸與雲端商業大腦的 AI 店長小J，用零延遲的溫暖陪伴您每一杯好咖啡！"
    else:
        reply = f"收到您的需求「{q}」！小J 推薦您試試店內人氣第一的『招牌咖啡』(85元) 搭配手作甜點，點選左側菜單即可馬上為您準備喔！"

    ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "ok": True,
        "state": "PASS_TIER1_KNOWLEDGE_GRAPH_FALLBACK",
        "tier": "TIER1_COMMERCIAL_KNOWLEDGE_GRAPH",
        "latency_ms": ms,
        "cost_twd": 0.0,
        "cost_evidence": "LOCAL_RULE_GRAPH_ZERO_COST",
        "contains_member_plaintext": False,
        "reply": reply,
        "choreography": _build_visual_choreography(reply, "TIER1_KG"),
    }
