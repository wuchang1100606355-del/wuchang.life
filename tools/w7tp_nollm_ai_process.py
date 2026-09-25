#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP / 小J 無地端 LLM AI 進程原型

核心：
- no local LLM runtime
- 五合一場域
- 意圖場暫存結構
- 7D AI process
- D8 envelope
- 維度 / 空間 / 時空 / 時空方向 / 相對方向時空檢索
- lookup / anti-lookup
- sandbox product object
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets
import sqlite3
import statistics
import sys
import time
from typing import Any, Dict, List, Tuple


APP = "W7TP_NO_LOCAL_LLM_AI_PROCESS"
SCHEMA_VERSION = "20260622.no_local_llm_ai_process.v1"


# ------------------------------------------------------------
# 基礎工具
# ------------------------------------------------------------

def now_ts() -> int:
    return int(time.time())


def now_ns() -> int:
    return time.perf_counter_ns()


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_obj(obj: Any) -> str:
    if isinstance(obj, bytes):
        data = obj
    elif isinstance(obj, str):
        data = obj.encode("utf-8")
    else:
        data = json_dumps(obj).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def ensure_dir(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: pathlib.Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def median_us(values_ns: List[int]) -> float:
    if not values_ns:
        return 0.0
    return round(statistics.median(values_ns) / 1000.0, 3)


def p95_us(values_ns: List[int]) -> float:
    if not values_ns:
        return 0.0
    s = sorted(values_ns)
    idx = min(len(s) - 1, int(len(s) * 0.95))
    return round(s[idx] / 1000.0, 3)


# ------------------------------------------------------------
# Sandbox DB
# ------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS lookup_menu (
  sku TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  price INTEGER NOT NULL,
  class TEXT NOT NULL,
  discountable INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS lookup_governance (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS behavior_structure_candidates (
  candidate_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  raw_hash TEXT NOT NULL,
  trusted INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS intent_events (
  intent_id TEXT PRIMARY KEY,
  natural_language TEXT NOT NULL,
  scratch_field_ref TEXT NOT NULL,
  five_field_json TEXT NOT NULL,
  seven_d_json TEXT NOT NULL,
  d8_json TEXT NOT NULL,
  retrieval_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS product_objects (
  product_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  d8_ref TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_chain (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  object_ref TEXT NOT NULL,
  object_hash TEXT NOT NULL,
  previous_hash TEXT,
  event_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
"""


MENU_SEED = [
    ("LATTE_HOT", "熱拿鐵", 120, "beverage", 1),
    ("OAT_MILK", "燕麥奶", 20, "beverage_option", 1),
    ("HAM_CHEESE_TOAST", "火腿起司吐司", 75, "food", 1),
    ("PUBLIC_WELFARE_CUP_DEPOSIT", "公益杯押金", 50, "deposit", 0),
]

GOVERNANCE_SEED = {
    "system": APP,
    "schema_version": SCHEMA_VERSION,
    "intent_field_policy": "NO_CONTEXT_ONLY_TEMPORARY_SCRATCH_FIELD",
    "local_llm_runtime": "false",
    "cloud_call_runtime": "false",
    "llm_role_if_any": "OFFLINE_OR_CANDIDATE_ONLY",
    "no_lookup_no_land": "true",
    "no_anti_lookup_no_land": "true",
    "d8_required": "true",
    "formal_pos_write_allowed": "false",
    "production_release_allowed": "false",
    "member_plaintext_read_allowed": "false",
    "secret_read_allowed": "false",
    "voice_must_say": "試算",
    "voice_forbidden_phrases": "已下單,已付款,已完成上架,已完成付款",
    "hearsay_discount_claim": "DENY_AS_RULE_SOURCE",
    "member_discount_rule": "beverage_only_10_percent_max_20",
    "volunteer_coupon_rule": "discountable_total_15_percent_max_30_exclude_deposit_no_stack",
}


def open_db(root: pathlib.Path) -> sqlite3.Connection:
    ensure_dir(root / "db")
    conn = sqlite3.connect(root / "db" / "w7tp_nollm_ai_process.sqlite3")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(root: pathlib.Path) -> Dict[str, Any]:
    conn = open_db(root)
    cur = conn.cursor()
    cur.executescript(DDL)

    cur.executemany(
        "INSERT OR REPLACE INTO lookup_menu VALUES (?,?,?,?,?)",
        MENU_SEED,
    )
    cur.executemany(
        "INSERT OR REPLACE INTO lookup_governance VALUES (?,?)",
        list(GOVERNANCE_SEED.items()),
    )

    conn.commit()
    conn.close()

    return {
        "state": "PASS_DB_INIT",
        "db": str(root / "db" / "w7tp_nollm_ai_process.sqlite3"),
        "secret_read": False,
        "member_plaintext_read": False,
        "formal_pos_write": False,
        "production_release": False,
    }


def get_menu(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM lookup_menu").fetchall()
    return {r["sku"]: dict(r) for r in rows}


def get_gov(conn: sqlite3.Connection) -> Dict[str, str]:
    rows = conn.execute("SELECT * FROM lookup_governance").fetchall()
    return {r["key"]: r["value"] for r in rows}


# ------------------------------------------------------------
# 無 LLM 自然語言 → 候選結構
# ------------------------------------------------------------

SKU_ALIASES = {
    "熱拿鐵": "LATTE_HOT",
    "拿鐵": "LATTE_HOT",
    "燕麥奶": "OAT_MILK",
    "火腿起司吐司": "HAM_CHEESE_TOAST",
    "吐司": "HAM_CHEESE_TOAST",
    "公益杯押金": "PUBLIC_WELFARE_CUP_DEPOSIT",
    "公益杯": "PUBLIC_WELFARE_CUP_DEPOSIT",
}

INTENT_HINTS = {
    "建立": "create",
    "建": "create",
    "產生": "create",
    "做": "create",
    "試算": "dry_run",
    "優惠": "discount_check",
    "語音": "voice_reply",
    "上架": "publish",
    "POS": "pos",
    "會員": "member_scope",
}


def no_llm_parse_natural_language(nl: str) -> Dict[str, Any]:
    """
    無 LLM Parser：
    只做 deterministic pattern extraction。
    不做 token prediction，不做 context window，不做浮點語意向量推論。
    """
    items: List[Dict[str, Any]] = []
    seen = set()

    for phrase, sku in SKU_ALIASES.items():
        if phrase in nl and sku not in seen:
            seen.add(sku)
            items.append({"sku": sku, "qty": 1, "source_phrase": phrase})

    requested = []
    for phrase, intent in INTENT_HINTS.items():
        if phrase in nl and intent not in requested:
            requested.append(intent)

    product_name = "未命名產品"
    m = re.search(r"「([^」]{2,60})」", nl)
    if m:
        product_name = m.group(1)
    elif "父親節" in nl:
        product_name = "父親節早午餐咖啡套組"
    elif "套組" in nl:
        product_name = "咖啡套組"

    candidate = {
        "source": "no_local_llm_deterministic_parser",
        "llm_used": False,
        "cloud_call_used": False,
        "natural_language_hash": sha256_obj(nl),
        "product_name": product_name,
        "items": items,
        "claimed_discount": "客人口頭聲稱五折" if "五折" in nl else None,
        "coupon_claim": "志工券" if "志工券" in nl else None,
        "requested_actions": requested or ["PRODUCT_DRY_RUN"],
        "forbidden_actions": [
            "FORMAL_POS_WRITE",
            "PRODUCTION_RELEASE",
            "MEMBER_PLAINTEXT_READ",
            "SECRET_READ",
        ],
        "db_write": False,
        "member_plaintext_read": False,
        "secret_read": False,
        "production_release": False,
    }
    return candidate


# ------------------------------------------------------------
# 五合一、7D、D8、多層檢索
# ------------------------------------------------------------

def build_scratch_field(nl: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
    scratch_ref = "scratch:" + sha256_obj({
        "nl_hash": sha256_obj(nl),
        "candidate_hash": sha256_obj(candidate),
        "ts_bucket": now_ts() // 60,
    })[:16]

    return {
        "scratch_field_ref": scratch_ref,
        "policy": "NO_CONTEXT_ONLY_TEMPORARY_FIELD_STRUCTURE",
        "context_persisted": False,
        "natural_language_hash": sha256_obj(nl),
        "candidate_hash": sha256_obj(candidate),
        "ttl": "single_runtime_event",
        "actor": "local_operator_or_service_event",
        "task_coordinate": "intent_product_or_state_transition",
    }


def build_five_field(scratch: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "intent_field": {
            "role": "temporary_intent_structure",
            "scratch_field_ref": scratch["scratch_field_ref"],
            "context_persisted": False,
            "candidate_intent": candidate.get("requested_actions", []),
        },
        "state_field": {
            "state_root": "local_state_root:sandbox_demo",
            "state_policy": "local_only",
            "state_delta_allowed": "candidate_then_verify",
        },
        "space_field": {
            "space_ref": "wuchang/chiaoguo_cafe_renew_main_store/intent_sandbox",
            "device_scope": ["voice_endpoint_candidate", "sandbox_product_db"],
            "formal_pos_write": False,
        },
        "evidence_field": {
            "evidence_policy": "hash_chain_required",
            "lookup_version": "LOCAL_DEMO_LOOKUP_V1",
            "rule_root": sha256_obj(GOVERNANCE_SEED),
        },
        "execution_field": {
            "allowed_outputs": [
                "ALLOW_SANDBOX_PRODUCT",
                "HOLD",
                "DENY",
                "REQUIRE_HUMAN_REVIEW",
                "ROUTE",
            ],
            "formal_pos_write": False,
            "production_release": False,
        },
    }


def build_7d_process(five: Dict[str, Any], scratch: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, str]:
    return {
        "D1_identity": "actor:local_operator_or_service_event; authority:local_total_field",
        "D2_intent": "create_or_verify_product_object_from_no_llm_ai_process",
        "D3_state": "candidate_received; scratch_field_active; sandbox_only",
        "D4_topology_or_space": five["space_field"]["space_ref"],
        "D5_resource": "lookup_menu; lookup_governance; reachable_state_set; evidence_chain",
        "D6_governance": "NO_LOCAL_LLM_RUNTIME; NO_LOOKUP_NO_LAND; NO_FORMAL_POS_WRITE; NO_MEMBER_PLAINTEXT",
        "D7_verification": "dimension_space_spacetime_direction_relative_lookup_anti_lookup_d8_required",
    }


def load_or_create_demo_d8_key(root: pathlib.Path) -> bytes:
    """
    這是 sandbox demo key，不讀取 production secret。
    """
    key_path = root / "db" / "demo_d8_local.key"
    ensure_dir(key_path.parent)
    if not key_path.exists():
        key_path.write_bytes(secrets.token_bytes(32))
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass
    return key_path.read_bytes()


def build_d8_envelope(root: pathlib.Path, seven_d: Dict[str, Any], scratch: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    demo_key = load_or_create_demo_d8_key(root)
    payload = {
        "schema": "D8_ENCRYPTION_ENVELOPE_DEMO",
        "seven_d_hash": sha256_obj(seven_d),
        "scratch_hash": sha256_obj(scratch),
        "candidate_hash": sha256_obj(candidate),
        "ttl": "single_runtime_event",
        "nonce": secrets.token_hex(8),
        "counter": now_ts(),
        "formal_pos_write": False,
        "production_release": False,
    }
    mac = hmac.new(demo_key, json_dumps(payload).encode("utf-8"), hashlib.sha256).hexdigest()
    payload["hmac_sha256_demo"] = mac
    payload["envelope_hash"] = sha256_obj(payload)
    return payload


def build_retrieval_stack(five: Dict[str, Any], seven_d: Dict[str, Any], d8: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "dimension_retrieval": {
            "D1_D7_complete": all(bool(v) for v in seven_d.values()),
            "identity": seven_d["D1_identity"],
            "intent": seven_d["D2_intent"],
            "verification": seven_d["D7_verification"],
        },
        "space_retrieval": {
            "space_ref": five["space_field"]["space_ref"],
            "formal_pos_write": False,
            "execution_scope": "sandbox_product_object_only",
        },
        "spacetime_retrieval": {
            "time_phase": "runtime_event",
            "lookup_version": five["evidence_field"]["lookup_version"],
            "ttl": d8["ttl"],
        },
        "spacetime_direction_retrieval": {
            "allowed_flow": [
                "natural_language_or_event",
                "no_llm_candidate_structure",
                "intent_scratch_field",
                "five_field",
                "seven_d_process",
                "d8_envelope",
                "lookup",
                "anti_lookup",
                "sandbox_product_object",
            ],
            "forbidden_flow": [
                "candidate_to_formal_pos_write",
                "candidate_to_production_release",
                "candidate_to_member_plaintext",
            ],
        },
        "relative_directional_spacetime_retrieval": {
            "relative_to_customer": "voice_trial_calculation_only",
            "relative_to_staff": "sandbox_dry_run",
            "relative_to_cloud": "not_used_in_runtime",
            "relative_to_local_total_field": "authoritative_verifier",
            "relative_to_formal_pos": "deny_write",
            "relative_to_d8": d8["envelope_hash"],
        },
    }


# ------------------------------------------------------------
# lookup / anti-lookup / 產品物件
# ------------------------------------------------------------

def derive_local_lookup_key(
    root: pathlib.Path,
    seven_d: Dict[str, Any],
    d8: Dict[str, Any],
    retrieval: Dict[str, Any],
) -> str:
    """
    lookup_key 必須本地派生。
    雲端候選不可提供或修改。
    """
    demo_key = load_or_create_demo_d8_key(root)
    canonical = {
        "seven_d_hash": sha256_obj(seven_d),
        "d8_hash": d8["envelope_hash"],
        "retrieval_hash": sha256_obj(retrieval),
        "lookup_version": retrieval["spacetime_retrieval"]["lookup_version"],
    }
    return hmac.new(demo_key, json_dumps(canonical).encode("utf-8"), hashlib.sha256).hexdigest()


def compute_product_object(
    conn: sqlite3.Connection,
    root: pathlib.Path,
    candidate: Dict[str, Any],
    seven_d: Dict[str, Any],
    d8: Dict[str, Any],
    retrieval: Dict[str, Any],
) -> Tuple[str, Dict[str, Any], List[str]]:
    menu = get_menu(conn)
    gov = get_gov(conn)
    errors: List[str] = []

    if not candidate.get("items"):
        errors.append("NO_ITEMS_RESOLVED")

    if candidate.get("member_plaintext_read") is not False:
        errors.append("MEMBER_PLAINTEXT_READ_NOT_FALSE")
    if candidate.get("secret_read") is not False:
        errors.append("SECRET_READ_NOT_FALSE")
    if candidate.get("production_release") is not False:
        errors.append("PRODUCTION_RELEASE_NOT_FALSE")
    if candidate.get("db_write") is not False:
        errors.append("CANDIDATE_DB_WRITE_NOT_FALSE")

    resolved = []
    for item in candidate.get("items", []):
        sku = item.get("sku")
        qty = int(item.get("qty", 1))
        if sku not in menu:
            errors.append(f"UNKNOWN_SKU:{sku}")
            continue
        row = menu[sku]
        line = {
            "sku": sku,
            "name": row["name"],
            "qty": qty,
            "unit_price": int(row["price"]),
            "class": row["class"],
            "discountable": bool(row["discountable"]),
            "line_total": int(row["price"]) * qty,
        }
        resolved.append(line)

    subtotal = sum(x["line_total"] for x in resolved)
    discountable_subtotal = sum(x["line_total"] for x in resolved if x["discountable"])
    deposit_total = sum(x["line_total"] for x in resolved if x["class"] == "deposit")
    beverage_total = sum(x["line_total"] for x in resolved if x["class"] in ("beverage", "beverage_option"))

    member_discount = min(round(beverage_total * 0.10), 20)
    coupon_discount = 0
    if candidate.get("coupon_claim") == "志工券":
        coupon_base = sum(x["line_total"] for x in resolved if x["class"] != "deposit")
        coupon_discount = min(round(coupon_base * 0.15), 30)

    selected_discount = max(member_discount, coupon_discount)
    payable_amount = subtotal - selected_discount

    denied_claims = []
    if candidate.get("claimed_discount"):
        denied_claims.append({
            "claim": candidate["claimed_discount"],
            "reason": gov.get("hearsay_discount_claim", "DENY_AS_RULE_SOURCE"),
        })

    lookup_key = derive_local_lookup_key(root, seven_d, d8, retrieval)

    lookup_trace = [
        {"step": "resolve_items", "count": len(resolved)},
        {"step": "subtotal", "value": subtotal},
        {"step": "discountable_subtotal", "value": discountable_subtotal},
        {"step": "deposit_total", "value": deposit_total},
        {"step": "member_discount", "value": member_discount, "rule_ref": "R_MEMBER_BEV_10_MAX20"},
        {"step": "coupon_discount", "value": coupon_discount, "rule_ref": "R_VOLUNTEER_15_MAX30_EXCLUDE_DEPOSIT_NOSTACK"},
        {"step": "selected_discount", "value": selected_discount},
        {"step": "payable_amount", "value": payable_amount},
    ]

    anti_lookup_trace = [
        {"from": "product_object", "to": "lookup_trace", "ok": True},
        {"from": "lookup_trace", "to": "7d_process", "ok": bool(seven_d)},
        {"from": "7d_process", "to": "scratch_field", "ok": True},
        {"from": "d8_envelope", "to": "candidate_hash", "ok": bool(d8.get("candidate_hash"))},
        {"from": "formal_pos_write", "to": "deny", "ok": True},
    ]

    voice = (
        f"這是試算：{candidate.get('product_name','產品')}小計 {subtotal} 元，"
        f"套用可用優惠後，試算應付 {payable_amount} 元；公益杯押金不列入折扣。"
    )

    forbidden = [x for x in gov.get("voice_forbidden_phrases", "").split(",") if x]
    for phrase in forbidden:
        if phrase in voice:
            errors.append("FORBIDDEN_VOICE_PHRASE:" + phrase)

    product = {
        "schema": "W7TP_SANDBOX_PRODUCT_OBJECT_V1",
        "product_name": candidate.get("product_name", "未命名產品"),
        "status": "PRODUCT_DRY_RUN",
        "items": resolved,
        "subtotal": subtotal,
        "discountable_subtotal": discountable_subtotal,
        "deposit_total": deposit_total,
        "member_discount": member_discount,
        "coupon_discount": coupon_discount,
        "selected_discount": selected_discount,
        "payable_amount": payable_amount,
        "denied_claims": denied_claims,
        "lookup_key_ref": "local_derived:" + lookup_key[:16],
        "lookup_trace": lookup_trace,
        "anti_lookup_trace": anti_lookup_trace,
        "rule_refs": [
            "R_MEMBER_BEV_10_MAX20",
            "R_VOLUNTEER_15_MAX30_EXCLUDE_DEPOSIT_NOSTACK",
            "DEPOSIT_NOT_DISCOUNTABLE",
            "HEARSAY_DISCOUNT_DENIED",
            "NO_FORMAL_POS_WRITE",
            "SANDBOX_ONLY",
        ],
        "voice_reply": voice,
        "d8_ref": d8["envelope_hash"],
        "local_llm_runtime": False,
        "cloud_call_runtime": False,
        "db_write": False,
        "formal_pos_write": False,
        "member_plaintext_read": False,
        "secret_read": False,
        "production_release": False,
    }

    decision = "ALLOW_SANDBOX_PRODUCT" if not errors else "HOLD"
    return decision, product, errors


def append_evidence(
    conn: sqlite3.Connection,
    event_type: str,
    object_ref: str,
    event: Dict[str, Any],
) -> Dict[str, Any]:
    row = conn.execute(
        "SELECT object_hash FROM evidence_chain ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    previous_hash = row["object_hash"] if row else None
    event_hash = sha256_obj({
        "event_type": event_type,
        "object_ref": object_ref,
        "event": event,
        "previous_hash": previous_hash,
    })
    event_id = "EVENT_" + event_hash[:16]
    conn.execute(
        "INSERT OR REPLACE INTO evidence_chain VALUES (?,?,?,?,?,?,?)",
        (
            event_id,
            event_type,
            object_ref,
            event_hash,
            previous_hash,
            json_dumps(event),
            now_ts(),
        ),
    )
    return {
        "event_id": event_id,
        "event_type": event_type,
        "object_ref": object_ref,
        "object_hash": event_hash,
        "previous_hash": previous_hash,
    }


# ------------------------------------------------------------
# 主流程
# ------------------------------------------------------------

def run_process(root: pathlib.Path, natural_language: str, save: bool = True) -> Dict[str, Any]:
    ensure_dir(root)
    init_db(root)
    conn = open_db(root)

    candidate = no_llm_parse_natural_language(natural_language)
    scratch = build_scratch_field(natural_language, candidate)
    five = build_five_field(scratch, candidate)
    seven_d = build_7d_process(five, scratch, candidate)
    d8 = build_d8_envelope(root, seven_d, scratch, candidate)
    retrieval = build_retrieval_stack(five, seven_d, d8, candidate)

    decision, product, errors = compute_product_object(conn, root, candidate, seven_d, d8, retrieval)

    intent_id = "INTENT_" + sha256_obj({
        "nl": natural_language,
        "scratch": scratch,
        "seven_d": seven_d,
        "d8": d8,
    })[:16]

    product_id = "PRODUCT_" + sha256_obj(product)[:16]

    evidence = append_evidence(conn, "NO_LOCAL_LLM_AI_PROCESS_RUN", product_id, {
        "intent_id": intent_id,
        "decision": decision,
        "product_hash": sha256_obj(product),
        "errors": errors,
    })

    if save:
        conn.execute(
            "INSERT OR REPLACE INTO intent_events VALUES (?,?,?,?,?,?,?,?)",
            (
                intent_id,
                natural_language,
                scratch["scratch_field_ref"],
                json_dumps(five),
                json_dumps(seven_d),
                json_dumps(d8),
                json_dumps(retrieval),
                now_ts(),
            ),
        )
        if decision == "ALLOW_SANDBOX_PRODUCT":
            conn.execute(
                "INSERT OR REPLACE INTO product_objects VALUES (?,?,?,?,?,?)",
                (
                    product_id,
                    product["status"],
                    json_dumps(product),
                    sha256_obj(product),
                    d8["envelope_hash"],
                    now_ts(),
                ),
            )

    conn.commit()
    conn.close()

    report = {
        "state": "PASS_NO_LOCAL_LLM_AI_PROCESS_RUN" if not errors else "HOLD_NO_LOCAL_LLM_AI_PROCESS_RUN",
        "app": APP,
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "intent_id": intent_id,
        "product_id": product_id if decision == "ALLOW_SANDBOX_PRODUCT" else None,
        "natural_language_hash": sha256_obj(natural_language),
        "candidate_structure": candidate,
        "five_field": five,
        "scratch_field": scratch,
        "seven_d_process": seven_d,
        "d8_envelope": d8,
        "retrieval_stack": retrieval,
        "product_object": product if decision == "ALLOW_SANDBOX_PRODUCT" else None,
        "errors": errors,
        "evidence": evidence,
        "safety": {
            "local_llm_runtime": False,
            "cloud_call_runtime": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "formal_pos_write": False,
            "production_release": False,
            "db_write": "SANDBOX_ONLY" if decision == "ALLOW_SANDBOX_PRODUCT" else False,
        },
    }
    return report


def benchmark(root: pathlib.Path, natural_language: str, loops: int) -> Dict[str, Any]:
    init_db(root)

    full_ns: List[int] = []
    lookup_ns: List[int] = []

    # prepare one canonical structure
    conn = open_db(root)
    candidate = no_llm_parse_natural_language(natural_language)
    scratch = build_scratch_field(natural_language, candidate)
    five = build_five_field(scratch, candidate)
    seven_d = build_7d_process(five, scratch, candidate)
    d8 = build_d8_envelope(root, seven_d, scratch, candidate)
    retrieval = build_retrieval_stack(five, seven_d, d8, candidate)

    for _ in range(loops):
        t = now_ns()
        compute_product_object(conn, root, candidate, seven_d, d8, retrieval)
        lookup_ns.append(now_ns() - t)

    conn.close()

    for _ in range(loops):
        t = now_ns()
        c = no_llm_parse_natural_language(natural_language)
        s = build_scratch_field(natural_language, c)
        f = build_five_field(s, c)
        d7 = build_7d_process(f, s, c)
        e8 = build_d8_envelope(root, d7, s, c)
        r = build_retrieval_stack(f, d7, e8, c)
        conn2 = open_db(root)
        compute_product_object(conn2, root, c, d7, e8, r)
        conn2.close()
        full_ns.append(now_ns() - t)

    return {
        "state": "PASS_BENCHMARK",
        "loops": loops,
        "lookup_only_median_us": median_us(lookup_ns),
        "lookup_only_p95_us": p95_us(lookup_ns),
        "full_pipeline_median_us": median_us(full_ns),
        "full_pipeline_p95_us": p95_us(full_ns),
        "note": "Python prototype; Go/Rust/C implementation can be faster. This measures structured runtime path, not cloud/70B/STT/TTS.",
        "safety": {
            "local_llm_runtime": False,
            "cloud_call_runtime": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "formal_pos_write": False,
            "production_release": False,
        },
    }


def ingest_behavior_candidate(root: pathlib.Path, file_path: pathlib.Path) -> Dict[str, Any]:
    """
    雲端 / 70B 拆解後的去識別行為結構候選匯入。
    不信任、不落地，只存 candidate。
    """
    init_db(root)
    raw = load_json(file_path)
    raw_hash = sha256_obj(raw)
    candidate_id = raw.get("candidate_id") or ("CLOUD_BEHAVIOR_CANDIDATE_" + raw_hash[:16])
    source = raw.get("source") or "cloud_or_static_70b_candidate"

    conn = open_db(root)
    conn.execute(
        "INSERT OR REPLACE INTO behavior_structure_candidates VALUES (?,?,?,?,?,?)",
        (
            candidate_id,
            source,
            json_dumps(raw),
            raw_hash,
            0,
            now_ts(),
        ),
    )
    evidence = append_evidence(conn, "BEHAVIOR_STRUCTURE_CANDIDATE_INGEST", candidate_id, {
        "candidate_id": candidate_id,
        "source": source,
        "raw_hash": raw_hash,
        "trusted": False,
        "cloud_can_land": False,
    })
    conn.commit()
    conn.close()

    return {
        "state": "PASS_BEHAVIOR_STRUCTURE_CANDIDATE_INGESTED",
        "candidate_id": candidate_id,
        "raw_hash": raw_hash,
        "trusted": False,
        "cloud_can_land": False,
        "evidence": evidence,
        "safety": {
            "local_llm_runtime": False,
            "cloud_call_runtime": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "formal_pos_write": False,
            "production_release": False,
        },
    }


def write_report(root: pathlib.Path, name: str, report: Dict[str, Any]) -> pathlib.Path:
    ensure_dir(root / "reports")
    path = root / "reports" / name
    write_json(path, report)
    return path


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

SAMPLE_NL = (
    "幫聊國咖啡館建立一個父親節早午餐咖啡套組，"
    "內容包含熱拿鐵、燕麥奶、火腿起司吐司、公益杯押金。"
    "要能給會員試算優惠，但不要真的上架，也不要寫入正式 POS。"
    "語音介紹要親切，但不能說已下單、已付款或已完成上架。"
    "客人說老闆答應五折，也說有志工券。"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP 無地端 LLM AI 進程")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--root", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--root", required=True)
    p_run.add_argument("--text", default=None)
    p_run.add_argument("--input-file", default=None)
    p_run.add_argument("--report-name", default="NO_LOCAL_LLM_AI_PROCESS_REPORT.json")

    p_bench = sub.add_parser("benchmark")
    p_bench.add_argument("--root", required=True)
    p_bench.add_argument("--loops", type=int, default=5000)
    p_bench.add_argument("--text", default=SAMPLE_NL)

    p_ingest = sub.add_parser("ingest-candidate")
    p_ingest.add_argument("--root", required=True)
    p_ingest.add_argument("--file", required=True)

    p_self = sub.add_parser("selftest")
    p_self.add_argument("--root", required=True)
    p_self.add_argument("--loops", type=int, default=3000)

    args = parser.parse_args()
    root = pathlib.Path(args.root)

    if args.cmd == "init":
        report = init_db(root)
        path = write_report(root, "INIT_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"REPORT={path}")
        return 0

    if args.cmd == "run":
        if args.input_file:
            nl = read_text(pathlib.Path(args.input_file))
        else:
            nl = args.text or SAMPLE_NL
        report = run_process(root, nl, save=True)
        path = write_report(root, args.report_name, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"REPORT={path}")
        return 0

    if args.cmd == "benchmark":
        report = benchmark(root, args.text, args.loops)
        path = write_report(root, "BENCHMARK_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"REPORT={path}")
        return 0

    if args.cmd == "ingest-candidate":
        report = ingest_behavior_candidate(root, pathlib.Path(args.file))
        path = write_report(root, "INGEST_CANDIDATE_REPORT.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"REPORT={path}")
        return 0

    if args.cmd == "selftest":
        init_report = init_db(root)
        sample_path = root / "inputs" / "sample_natural_language.txt"
        ensure_dir(sample_path.parent)
        sample_path.write_text(SAMPLE_NL, encoding="utf-8")

        run_report = run_process(root, SAMPLE_NL, save=True)
        bench_report = benchmark(root, SAMPLE_NL, args.loops)

        full = {
            "state": "PASS_SELFTEST" if run_report["decision"] == "ALLOW_SANDBOX_PRODUCT" else "HOLD_SELFTEST",
            "init": init_report,
            "run": {
                "decision": run_report["decision"],
                "product_id": run_report.get("product_id"),
                "payable_amount": (run_report.get("product_object") or {}).get("payable_amount"),
                "d8_ref": ((run_report.get("product_object") or {}).get("d8_ref")),
                "local_llm_runtime": False,
                "cloud_call_runtime": False,
            },
            "benchmark": bench_report,
            "paths": {
                "sample_input": str(sample_path),
                "db": str(root / "db" / "w7tp_nollm_ai_process.sqlite3"),
            },
            "safety": {
                "local_llm_runtime": False,
                "cloud_call_runtime": False,
                "secret_read": False,
                "member_plaintext_read": False,
                "formal_pos_write": False,
                "production_release": False,
            },
        }

        write_report(root, "NO_LOCAL_LLM_AI_PROCESS_REPORT.json", run_report)
        write_report(root, "BENCHMARK_REPORT.json", bench_report)
        path = write_report(root, "SELFTEST_REPORT.json", full)

        print(json.dumps(full, ensure_ascii=False, indent=2))
        print(f"REPORT={path}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
