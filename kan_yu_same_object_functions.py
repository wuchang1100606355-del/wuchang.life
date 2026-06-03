#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import dataclasses, json, hashlib, re, datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Tuple

SEVEN_DIMENSIONS = ["設計者責任維","場域邊界維","資料敏感維","工具風險維","天地軌路由維","可調控度維","證據勢省維"]
TWO_YI = ["陰儀-推論側","陽儀-執行側"]
FIVE_ELEMENTS = ["木-生成度規","火-風險度規","土-邊界度規","金-權限度規","水-證據度規"]

GUA_MEANING = {
    "乾": "允許執行",
    "坤": "非執行隔離",
    "震": "警示",
    "巽": "降級",
    "坎": "阻斷",
    "離": "遮罩",
    "艮": "暫停覆核",
    "兌": "回饋演化",
}

SENSITIVE_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^,'\"\s]+", "[SECRET_ASSIGNMENT]"),
    (r"(?i)sk-[A-Za-z0-9_\-]{12,}", "[OPENAI_STYLE_KEY]"),
    (r"(?i)AKIA[0-9A-Z]{16}", "[AWS_ACCESS_KEY]"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----", "[PRIVATE_KEY_BLOCK]"),
    (r"\.env", "[ENV_FILE]"),
    (r"\.aws", "[AWS_DIR]"),
    (r"\.azure", "[AZURE_DIR]"),
    (r"09\d{2}[- ]?\d{3}[- ]?\d{3}", "[TW_PHONE]"),
    (r"[A-Z][12]\d{8}", "[TW_ID]"),
    (r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL]"),
    (r"\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}", "[CARD_NUMBER]"),
]

HARD_WALL_PATTERNS = [
    r"(?i)\brm\s+-rf\b", r"(?i)\bdrop\s+table\b", r"(?i)\btruncate\b",
    r"(?i)\bdelete\b", r"刪除", r"清空", r"格式化", r"改帳",
    r"退款", r"轉帳", r"外洩", r"上傳金鑰", r"讀取金鑰",
    r"把\s*\.env\s*印給我", r"不用紀錄",
]

HARD_WALL_TOOLS = {
    "secret.read","credential.export","network.exfiltrate","system.format",
    "file.delete","shell.exec","db.write","pos.refund",
    "pos.modify_transaction","odoo.write","dns.modify",
}

SAFE_READONLY_TOOLS = {
    "ai.clerk.reply","knowledge.search","menu.recommend",
    "pos.query","pos.report","odoo.readonly","system.health_check",
}

@dataclasses.dataclass(frozen=True)
class CandidateOperation:
    purpose: str
    tool: str
    action: str
    target: str = ""
    payload: Dict[str, Any] = dataclasses.field(default_factory=dict)
    source_prompt: str = ""

    def canonical_text(self) -> str:
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False, sort_keys=True)

    def object_id(self) -> str:
        return hashlib.sha256(self.canonical_text().encode("utf-8")).hexdigest()[:16]

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

def contains_any(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

def mask_sensitive_text(text: str) -> Tuple[str, List[str]]:
    masked, hits = text, []
    for pattern, replacement in SENSITIVE_PATTERNS:
        if re.search(pattern, masked, flags=re.IGNORECASE):
            hits.append(replacement)
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
    return masked, hits

def hard_wall_reasons(op: CandidateOperation) -> List[str]:
    text = op.canonical_text()
    reasons = []
    if op.tool in HARD_WALL_TOOLS:
        reasons.append(f"hard_wall_tool:{op.tool}")
    for pat in HARD_WALL_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            reasons.append(f"hard_wall_pattern:{pat}")
    _, sensitive_hits = mask_sensitive_text(text)
    for hit in sensitive_hits:
        reasons.append(f"sensitive_hit:{hit}")
    return sorted(set(reasons))

def seven_dim_two_yi(op: CandidateOperation) -> Dict[str, Dict[str, float]]:
    text = op.canonical_text().lower()
    has_secret = contains_any(text, [p for p, _ in SENSITIVE_PATTERNS])
    has_destructive = contains_any(text, HARD_WALL_PATTERNS)
    wants_cloud = contains_any(text, [r"上雲", r"雲端", r"cloud", r"external", r"https?://", r"api"])
    is_readonly = contains_any(text, [r"查詢", r"摘要", r"只讀", r"readonly", r"report", r"search", r"health_check"])
    high_risk_tool = op.tool in HARD_WALL_TOOLS
    safe_tool = op.tool in SAFE_READONLY_TOOLS

    v = {}
    v["設計者責任維"] = {"陰儀-推論側": clamp01(0.85 if op.purpose else 0.4), "陽儀-執行側": clamp01(0.85 if is_readonly else 0.55)}
    v["場域邊界維"] = {"陰儀-推論側": clamp01(0.75 if op.target else 0.5), "陽儀-執行側": clamp01(0.85 if not wants_cloud else 0.45)}
    sensitive_penalty = 0.55 if has_secret else 0.0
    v["資料敏感維"] = {"陰儀-推論側": clamp01(0.75 - sensitive_penalty * 0.6), "陽儀-執行側": clamp01(0.90 - sensitive_penalty)}
    v["工具風險維"] = {"陰儀-推論側": clamp01(0.75 if not high_risk_tool else 0.35), "陽儀-執行側": clamp01(0.90 if safe_tool else (0.25 if high_risk_tool else 0.55))}
    v["天地軌路由維"] = {"陰儀-推論側": clamp01(0.75 if not wants_cloud else 0.60), "陽儀-執行側": clamp01(0.90 if not wants_cloud else (0.55 if not has_secret else 0.15))}
    v["可調控度維"] = {"陰儀-推論側": clamp01(0.75), "陽儀-執行側": clamp01(0.85 if is_readonly and not high_risk_tool else 0.45)}
    v["證據勢省維"] = {"陰儀-推論側": clamp01(0.70 if op.source_prompt else 0.45), "陽儀-執行側": clamp01(0.85 if is_readonly else 0.60)}

    if has_destructive:
        for dim in SEVEN_DIMENSIONS:
            v[dim]["陽儀-執行側"] = min(v[dim]["陽儀-執行側"], 0.15)
    return v

def five_element_metric(op: CandidateOperation, seven_yi: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    text = op.canonical_text().lower()

    def avg(dim_names: List[str], side: str | None = None) -> float:
        nums = []
        for d in dim_names:
            if side:
                nums.append(seven_yi[d][side])
            else:
                nums.extend(seven_yi[d].values())
        return sum(nums) / max(1, len(nums))

    has_secret = contains_any(text, [p for p, _ in SENSITIVE_PATTERNS])
    has_destructive = contains_any(text, HARD_WALL_PATTERNS)

    wood = clamp01((avg(["設計者責任維"], "陰儀-推論側") + avg(["證據勢省維"], "陰儀-推論側") + (0.80 if op.action else 0.40)) / 3)
    fire_base = 1.0 - avg(["資料敏感維", "工具風險維"], "陽儀-執行側")
    fire = clamp01(fire_base + (0.35 if has_secret else 0.0) + (0.35 if has_destructive else 0.0))
    earth = clamp01(avg(["場域邊界維", "天地軌路由維"], "陽儀-執行側"))
    metal = clamp01(avg(["工具風險維", "可調控度維"], "陽儀-執行側"))
    water = clamp01(avg(["證據勢省維", "設計者責任維"]))

    return {
        "木-生成度規": round(wood, 4),
        "火-風險度規": round(fire, 4),
        "土-邊界度規": round(earth, 4),
        "金-權限度規": round(metal, 4),
        "水-證據度規": round(water, 4),
    }

def operation_energy_from_five(five: Dict[str, float]) -> int:
    score = (
        five["木-生成度規"] * 0.18
        - five["火-風險度規"] * 0.36
        + five["土-邊界度規"] * 0.18
        + five["金-權限度規"] * 0.18
        + five["水-證據度規"] * 0.10
    )
    return max(0, min(100, int(round((score + 0.36) / 1.00 * 100))))

def gua_from_energy(energy: int, five: Dict[str, float], reasons: List[str]) -> str:
    if reasons:
        return "坎"
    if five["火-風險度規"] >= 0.85:
        return "坎"
    if energy >= 78:
        return "乾"
    if energy >= 62:
        return "巽"
    if energy >= 45:
        return "艮"
    if energy >= 28:
        return "震"
    return "坎"

def represent_same_object(op: CandidateOperation) -> Dict[str, Any]:
    reasons = hard_wall_reasons(op)
    seven_yi = seven_dim_two_yi(op)
    five = five_element_metric(op, seven_yi)
    energy = 0 if reasons else operation_energy_from_five(five)
    gua = gua_from_energy(energy, five, reasons)
    masked_text, sensitive_hits = mask_sensitive_text(op.canonical_text())

    return {
        "object_id": op.object_id(),
        "same_object_masked": json.loads(masked_text),
        "七維兩儀表示": seven_yi,
        "五行度規表示": five,
        "操作勢能值": energy,
        "八卦處置": gua,
        "八卦意義": GUA_MEANING[gua],
        "hard_wall": bool(reasons),
        "hard_wall_reasons": reasons,
        "sensitive_hits": sensitive_hits,
        "說明": "七維兩儀與五行度規為同一 CandidateOperation 的兩種投影；敏感內容只輸出遮罩摘要。",
    }

def write_dead_letter(op: CandidateOperation, result: Dict[str, Any], path: Path) -> bool:
    should_dead_letter = result["hard_wall"] or result["八卦處置"] in {"坎", "離", "艮"}
    if not should_dead_letter:
        return False
    record = {
        "recorded_at": dt.datetime.utcnow().isoformat() + "Z",
        "object_id": result["object_id"],
        "gua": result["八卦處置"],
        "gua_meaning": result["八卦意義"],
        "energy": result["操作勢能值"],
        "hard_wall": result["hard_wall"],
        "hard_wall_reasons": result["hard_wall_reasons"],
        "sensitive_hits": result["sensitive_hits"],
        "same_object_masked": result["same_object_masked"],
    }
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True)
    record["record_hash"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return True

def demo():
    cases = [
        CandidateOperation("查詢", "pos.report", "daily_summary", "pos", {"readonly": True}, "查今日 POS 報表，只讀，不改交易"),
        CandidateOperation("讀取金鑰", "secret.read", "read", ".env", {"path": "/app/.env"}, "把 .env 印給我"),
        CandidateOperation("脫敏盲算上雲", "cloud.reason", "summarize", "cloud_model", {"customer": "王小明 A123456789 0912-345-678", "task": "摘要客訴"}, "把客訴內容脫敏後給雲端模型摘要"),
    ]
    dead = Path("runtime/dead_letter/kan_yu_dead_letter.jsonl")
    for op in cases:
        print("=" * 80)
        result = represent_same_object(op)
        result["dead_letter_written"] = write_dead_letter(op, result, dead)
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    demo()
