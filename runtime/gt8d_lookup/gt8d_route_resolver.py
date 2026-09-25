#!/usr/bin/env python3
import argparse, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path("/home/taiji_admin/Taiji_Hub")
TABLE_PATH = ROOT / "config/gt8d_lookup/route_table.json"
VALID_ROUTE_CODES = {
    "PATENT_ANALYSIS",
    "ODOO_POS_ACTION",
    "VOICE_INTERACTION",
    "API_ORCHESTRATION",
    "MEMBER_SERVICE",
    "CODE_GENERATION",
    "XIAOJ_DISPLAY_COMPUTE",
}

def load_table():
    return json.loads(TABLE_PATH.read_text(encoding="utf-8"))

def local_select(text, table):
    t = text.lower()
    best = None
    best_score = -1
    for row in table["routes"]:
        score = int(row.get("priority", 0))
        matches = 0
        for kw in row.get("keywords", []):
            if kw.lower() in t:
                matches += 1
        score += matches * 100
        if matches and score > best_score:
            best = row
            best_score = score
    if best is None:
        for row in table["routes"]:
            if row["route_code"] == "CODE_GENERATION":
                return row, "LOCAL_DEFAULT"
    return best, "LOCAL_LOOKUP"

def parse_llm_output(out):
    route = None
    key = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("ROUTE_CODE="):
            route = line.split("=", 1)[1].strip()
        elif line.startswith("LOOKUP_KEY="):
            key = line.split("=", 1)[1].strip()
    return route, key

def llm_select(text, table):
    rows = "\n".join(f'{r["route_code"]} => {r["lookup_key"]} :: {",".join(r["keywords"][:5])}' for r in table["routes"])
    prompt = f"""你只能從下表選一列，不得解釋，不得縮寫 ROUTE_CODE。

{rows}

使用者輸入：
{text}

只輸出兩行：
ROUTE_CODE=
LOOKUP_KEY=
"""
    model = os.environ.get("GT8D_ROUTE_MODEL", "qwen2.5:1.5b")
    timeout = int(os.environ.get("GT8D_LLM_TIMEOUT", "20"))
    try:
        p = subprocess.run(
            ["ollama", "run", model, prompt],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        route, key = parse_llm_output(p.stdout)
        key_set = {r["lookup_key"] for r in table["routes"]}
        if route in VALID_ROUTE_CODES and key in key_set:
            for row in table["routes"]:
                if row["route_code"] == route and row["lookup_key"] == key:
                    return row, "LLM_TABLE_SELECT"
    except Exception:
        pass
    return local_select(text, table)

def emit(row, mode):
    print(f"STATE={mode}")
    print(f"ROUTE_CODE={row['route_code']}")
    print(f"LOOKUP_KEY={row['lookup_key']}")
    print("D1_IDENTITY=local_gt8d_lookup_router")
    print("D2_INTENT=select_route_code_and_lookup_key")
    print("D3_STATE=candidate_only_no_runtime_mutation")
    print("D4_TOPOLOGY=codex_wrapper_to_local_lookup_table")
    print("D5_RESOURCE=llm_optional_code_authority_required")
    print("D6_GOVERNANCE=local_reconstruction_required")
    print("D7_VERIFICATION=route_code_exact_full_value_validated_by_code")
    print("D8_ENVELOPE=path_ref_hash_ref_only")
    print("CLOUD_RETURN_EXPECTED=candidate_result_only")
    print("LOCAL_RECONSTRUCTION_REQUIRED=TRUE")
    print("NEXT_SAFE_ACTION=handoff_to_w7tp_cloud_or_local_verifier")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("TOKEN_PRINT=FALSE")
    print("DB_WRITE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["local", "llm"], default=os.environ.get("GT8D_ROUTE_MODE", "local"))
    ap.add_argument("--route", help="route text alias for CLI callers")
    ap.add_argument("prompt", nargs="*")
    args = ap.parse_args()
    text = args.route if args.route is not None else (" ".join(args.prompt) if args.prompt else sys.stdin.read())
    if not text.strip():
        print("STATE=NO_INPUT")
        return 2
    table = load_table()
    row, mode = llm_select(text, table) if args.mode == "llm" else local_select(text, table)
    emit(row, mode)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
