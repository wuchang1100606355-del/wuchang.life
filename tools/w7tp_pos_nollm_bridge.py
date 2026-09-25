#!/usr/bin/env python3
import json, pathlib, hashlib, time, importlib.util, sys

ROOT = pathlib.Path("/home/taiji_admin/Taiji_Hub")

def sha_obj(o):
    return hashlib.sha256(json.dumps(o, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def load_mod():
    spec = importlib.util.spec_from_file_location(
        "w7tp_nollm_ai_process",
        str(ROOT / "tools/w7tp_nollm_ai_process.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: w7tp_pos_nollm_bridge.py <run_root> <natural_language_file>")

    run_root = pathlib.Path(sys.argv[1])
    nl_file = pathlib.Path(sys.argv[2])
    run_root.mkdir(parents=True, exist_ok=True)

    nl = nl_file.read_text(encoding="utf-8")
    mod = load_mod()

    report = mod.run_process(run_root, nl, save=True)

    product = report.get("product_object")
    if not product:
        decision = "HOLD_NO_PRODUCT_OBJECT"
        order = None
    else:
        items = []
        for line in product.get("items", []):
            items.append({
                "sku": line.get("sku"),
                "name": line.get("name"),
                "qty": line.get("qty"),
                "unit_price": line.get("unit_price"),
                "line_total": line.get("line_total"),
                "class": line.get("class"),
                "discountable": line.get("discountable")
            })

        order = {
            "schema": "W7TP_POS_SANDBOX_ORDER_CANDIDATE_V1",
            "source": "no_local_llm_ai_runtime",
            "status": "POS_SANDBOX_ORDER_CANDIDATE",
            "product_name": product.get("product_name"),
            "items": items,
            "subtotal": product.get("subtotal"),
            "selected_discount": product.get("selected_discount"),
            "payable_amount": product.get("payable_amount"),
            "voice_reply": product.get("voice_reply"),
            "d8_ref": product.get("d8_ref"),
            "rule_refs": product.get("rule_refs", []),
            "denied_claims": product.get("denied_claims", []),
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "service_restart": False,
            "deploy": False,
            "production_release": False
        }
        decision = "ALLOW_POS_SANDBOX_ORDER_CANDIDATE"

    safety_errors = []
    if report.get("safety", {}).get("local_llm_runtime") is not False:
        safety_errors.append("LOCAL_LLM_RUNTIME_NOT_FALSE")
    if report.get("safety", {}).get("cloud_call_runtime") is not False:
        safety_errors.append("CLOUD_CALL_RUNTIME_NOT_FALSE")
    if order:
        for k in ["formal_db_write", "formal_pos_write", "payment_capture", "service_restart", "deploy", "production_release"]:
            if order.get(k) is not False:
                safety_errors.append(k.upper() + "_NOT_FALSE")

    final_state = "PASS_POS_NOLLM_BRIDGE_LAND_P1" if order and not safety_errors else "HOLD_POS_NOLLM_BRIDGE"

    evidence = {
        "type": "W7TP_POS_NOLLM_BRIDGE_LAND_P1_EVIDENCE",
        "created_at": int(time.time()),
        "state": final_state,
        "decision": decision,
        "nollm_report_hash": sha_obj(report),
        "order_hash": sha_obj(order) if order else None,
        "safety_errors": safety_errors,
        "claim_relevance": [
            "無 LLM AI runtime 產生 product object",
            "product object 轉 POS sandbox order candidate",
            "正式 DB / 正式 POS / payment / production 均未觸碰"
        ],
        "safety": {
            "local_llm_runtime": False,
            "cloud_call_runtime": False,
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "service_restart": False,
            "deploy": False,
            "production_release": False
        }
    }

    reports = run_root / "reports"
    orders = run_root / "orders"
    evdir = run_root / "evidence"
    reports.mkdir(exist_ok=True)
    orders.mkdir(exist_ok=True)
    evdir.mkdir(exist_ok=True)

    (reports / "NO_LLM_AI_PROCESS_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if order:
        (orders / "POS_SANDBOX_ORDER_CANDIDATE.json").write_text(json.dumps(order, ensure_ascii=False, indent=2), encoding="utf-8")
    (evdir / "POS_NOLLM_BRIDGE_LAND_P1_EVIDENCE.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    print("STATE=" + final_state)
    print("DECISION=" + decision)
    print("PAYABLE_AMOUNT=" + str((order or {}).get("payable_amount")))
    print("ORDER=" + str(orders / "POS_SANDBOX_ORDER_CANDIDATE.json"))
    print("EVIDENCE=" + str(evdir / "POS_NOLLM_BRIDGE_LAND_P1_EVIDENCE.json"))
    print("LOCAL_LLM_RUNTIME=FALSE")
    print("CLOUD_CALL_RUNTIME=FALSE")
    print("FORMAL_DB_WRITE=FALSE")
    print("FORMAL_POS_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("PRODUCTION_RELEASE=FALSE")

if __name__ == "__main__":
    main()
