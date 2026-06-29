#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import pathlib
import hashlib
import glob
import sys

SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "DB_WRITE": False,
    "PAYMENT_CAPTURE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "PRODUCTION_RELEASE": False,
    "DIRECT_EXECUTION": False,
    "CANDIDATE_ONLY": True,
}

def sha(obj):
    if not isinstance(obj, str):
        obj = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(obj.encode("utf-8")).hexdigest()

def latest_registry():
    paths = sorted(
        glob.glob("runtime/total_field/static_llm_runtime_candidate_registry/STATIC_LLM_UX_RUNTIME_CANDIDATE_REGISTRY_*/RUNTIME_CANDIDATE_REGISTRY.json"),
        reverse=True,
    )
    if not paths:
        raise SystemExit("NO_RUNTIME_CANDIDATE_REGISTRY_FOUND")
    return paths[0]

def load_registry(path):
    p = pathlib.Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))

    if data.get("state") != "CANDIDATE_ONLY":
        raise SystemExit("REGISTRY_NOT_CANDIDATE_ONLY")
    if data.get("production_release") is not False:
        raise SystemExit("REGISTRY_PRODUCTION_RELEASE_NOT_FALSE")
    if data.get("direct_execution") is not False:
        raise SystemExit("REGISTRY_DIRECT_EXECUTION_NOT_FALSE")
    if data.get("db_write") is not False:
        raise SystemExit("REGISTRY_DB_WRITE_NOT_FALSE")

    return data

def render(registry, template_id, slots):
    tables = registry["tables"]
    templates = {x["template_id"]: x for x in tables["template_table"]}
    tones = {x["tone_policy_id"]: x for x in tables["tone_policy_table"]}

    if template_id not in templates:
        raise SystemExit(f"TEMPLATE_NOT_FOUND:{template_id}")

    template = templates[template_id]
    tone = tones.get(template["tone_policy_id"], {})

    required_slots = template.get("required_slots", [])
    missing = [k for k in required_slots if k not in slots]
    if missing:
        return {
            "STATE": "HOLD_PACKET_TONE_RENDER_MISSING_SLOTS",
            "missing_slots": missing,
            "template_id": template_id,
            "candidate_only": True,
            "production_release": False,
            "db_write": False,
            "direct_execution": False,
        }

    text = template["template"].format(**slots)

    forbidden_hits = []
    for claim in template.get("forbidden_claims", []):
        if claim and claim in text and template.get("decision") != "BLOCK":
            forbidden_hits.append(claim)

    decision = "PASS" if not forbidden_hits else "HOLD"

    return {
        "STATE": "PASS_PACKET_TONE_RENDER" if decision == "PASS" else "HOLD_PACKET_TONE_RENDER",
        "decision": decision,
        "candidate_only": True,
        "production_release": False,
        "db_write": False,
        "direct_execution": False,
        "renderer_rule": {
            "tone_mutable": True,
            "facts_immutable": True,
            "risk_immutable": True,
            "execution_boundary_immutable": True
        },
        "template": {
            "template_id": template_id,
            "speech_act": template.get("speech_act"),
            "intent_id": template.get("intent_id"),
            "decision": template.get("decision"),
            "risk_code": template.get("risk_code", ""),
            "tone_policy_id": template.get("tone_policy_id")
        },
        "tone_style": tone.get("style", {}),
        "slots": slots,
        "rendered_text": text,
        "forbidden_hits": forbidden_hits,
        "render_hash": sha({
            "template_id": template_id,
            "slots": slots,
            "text": text,
            "tone_policy_id": template.get("tone_policy_id")
        }),
        "safety_flags": SAFETY_FLAGS
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="")
    ap.add_argument("--template-id", required=True)
    ap.add_argument("--slots-json", default="{}")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    reg_path = args.registry or latest_registry()
    registry = load_registry(reg_path)
    slots = json.loads(args.slots_json)

    result = render(registry, args.template_id, slots)
    result["registry"] = reg_path

    s = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(s)

    if args.out:
        p = pathlib.Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(s + "\n", encoding="utf-8")

    if result["STATE"].startswith("HOLD"):
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
