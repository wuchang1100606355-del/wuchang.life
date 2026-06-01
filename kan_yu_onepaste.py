#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import dataclasses, json, hashlib, re
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List

REPORT = Path("runtime/reports/kan_yu_onepaste_report.json")
DEAD = Path("runtime/dead_letter/kan_yu_dead_letter.jsonl")

SENSITIVE = [
    r"\.env", r"\.aws", r"\.azure", r"api[_-]?key", r"secret", r"token",
    r"password", r"private[_-]?key", r"credential",
    r"09\d{2}[- ]?\d{3}[- ]?\d{3}", r"[A-Z][12]\d{8}",
    r"[\w\.-]+@[\w\.-]+\.\w+"
]

HARD_PATTERNS = [
    r"rm\s+-rf", r"drop\s+table", r"delete", r"刪除", r"清空", r"格式化",
    r"改帳", r"退款", r"轉帳", r"外洩", r"上傳金鑰", r"讀取金鑰",
    r"把\s*\.env\s*印給我", r"不用紀錄"
]

HARD_TOOLS = {
    "secret.read", "credential.export", "network.exfiltrate", "system.format",
    "file.delete", "shell.exec", "db.write", "pos.refund",
    "pos.modify_transaction", "odoo.write", "dns.modify"
}

SAFE_TOOLS = {
    "ai.clerk.reply", "knowledge.search", "menu.recommend",
    "pos.query", "pos.report", "odoo.readonly", "system.health_check"
}

DIMS = ["設計者責任維","場域邊界維","資料敏感維","工具風險維","天地軌路由維","可調控度維","證據勢省維"]
SIDES = ["陰儀-推論側","陽儀-執行側"]
GUA = {"乾":"允許執行","坤":"隔離","震":"警示","巽":"降級","坎":"阻斷","離":"遮罩","艮":"暫停覆核","兌":"回饋"}

@dataclasses.dataclass(frozen=True)
class CandidateOperation:
    purpose: str
    tool: str
    action: str
    target: str = ""
    payload: Dict[str, Any] = dataclasses.field(default_factory=dict)
    source_prompt: str = ""
    def text(self) -> str:
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False, sort_keys=True)
    def oid(self) -> str:
        return hashlib.sha256(self.text().encode()).hexdigest()[:16]

def hit_any(text: str, pats: List[str]) -> bool:
    return any(re.search(p, text, flags=re.I) for p in pats)

def mask(text: str) -> tuple[str, List[str]]:
    hits = []
    out = text
    for p in SENSITIVE:
        if re.search(p, out, flags=re.I):
            tag = "[MASKED]"
            hits.append(p)
            out = re.sub(p, tag, out, flags=re.I)
    return out, hits

def hard_reasons(op: CandidateOperation) -> List[str]:
    t = op.text()
    r = []
    if op.tool in HARD_TOOLS:
        r.append("硬牆工具:" + op.tool)
    for p in HARD_PATTERNS:
        if re.search(p, t, flags=re.I):
            r.append("硬牆語意:" + p)
    _, sens = mask(t)
    if sens:
        r.append("敏感內容需遮罩")
    return sorted(set(r))

def clamp(x: float) -> float:
    return max(0.0, min(1.0, x))

def seven_two(op: CandidateOperation) -> Dict[str, Dict[str, float]]:
    t = op.text().lower()
    sensitive = hit_any(t, SENSITIVE)
    destructive = hit_any(t, HARD_PATTERNS)
    cloud = hit_any(t, [r"上雲", r"雲端", r"cloud", r"https?://", r"api"])
    readonly = hit_any(t, [r"查詢", r"摘要", r"只讀", r"readonly", r"report", r"search", r"health"])
    high = op.tool in HARD_TOOLS
    safe = op.tool in SAFE_TOOLS
    sp = 0.55 if sensitive else 0.0
    v = {
        "設計者責任維":{"陰儀-推論側":0.85 if op.purpose else 0.4,"陽儀-執行側":0.85 if readonly else 0.55},
        "場域邊界維":{"陰儀-推論側":0.75 if op.target else 0.5,"陽儀-執行側":0.85 if not cloud else 0.45},
        "資料敏感維":{"陰儀-推論側":clamp(0.75-sp*0.6),"陽儀-執行側":clamp(0.90-sp)},
        "工具風險維":{"陰儀-推論側":0.75 if not high else 0.35,"陽儀-執行側":0.90 if safe else (0.25 if high else 0.55)},
        "天地軌路由維":{"陰儀-推論側":0.75 if not cloud else 0.60,"陽儀-執行側":0.90 if not cloud else (0.55 if not sensitive else 0.15)},
        "可調控度維":{"陰儀-推論側":0.75,"陽儀-執行側":0.85 if readonly and not high else 0.45},
        "證據勢省維":{"陰儀-推論側":0.70 if op.source_prompt else 0.45,"陽儀-執行側":0.85 if readonly else 0.60},
    }
    if destructive:
        for d in DIMS:
            v[d]["陽儀-執行側"] = min(v[d]["陽儀-執行側"], 0.15)
    return v

def five_metric(op: CandidateOperation, v: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    t = op.text().lower()
    def avg(ds, side=None):
        nums = []
        for d in ds:
            nums += [v[d][side]] if side else list(v[d].values())
        return sum(nums) / len(nums)
    sensitive = hit_any(t, SENSITIVE)
    destructive = hit_any(t, HARD_PATTERNS)
    wood = clamp((avg(["設計者責任維"],"陰儀-推論側")+avg(["證據勢省維"],"陰儀-推論側")+(0.8 if op.action else 0.4))/3)
    fire = clamp((1-avg(["資料敏感維","工具風險維"],"陽儀-執行側"))+(0.35 if sensitive else 0)+(0.35 if destructive else 0))
    earth = clamp(avg(["場域邊界維","天地軌路由維"],"陽儀-執行側"))
    metal = clamp(avg(["工具風險維","可調控度維"],"陽儀-執行側"))
    water = clamp(avg(["證據勢省維","設計者責任維"]))
    return {"木-生成度規":round(wood,4),"火-風險度規":round(fire,4),"土-邊界度規":round(earth,4),"金-權限度規":round(metal,4),"水-證據度規":round(water,4)}

def energy(f: Dict[str, float]) -> int:
    s = f["木-生成度規"]*0.18 - f["火-風險度規"]*0.36 + f["土-邊界度規"]*0.18 + f["金-權限度規"]*0.18 + f["水-證據度規"]*0.10
    return max(0, min(100, int(round((s+0.36)*100))))

def gua(e: int, f: Dict[str,float], reasons: List[str]) -> str:
    if reasons or f["火-風險度規"] >= 0.85: return "坎"
    if e >= 78: return "乾"
    if e >= 62: return "巽"
    if e >= 45: return "艮"
    if e >= 28: return "震"
    return "坎"

def diff(v: Dict[str, Dict[str,float]], f: Dict[str,float]) -> Dict[str, Any]:
    seven_e = int(round(sum(v[d]["陰儀-推論側"]*0.75 + v[d]["陽儀-執行側"]*1.25 for d in DIMS)/(len(DIMS)*2)*100))
    five_e = energy(f)
    tension = {d:round(abs(v[d]["陰儀-推論側"]-v[d]["陽儀-執行側"]),4) for d in DIMS}
    return {
        "compression_loss_ratio_14_to_5": round(1-5/14,4),
        "yin_yang_tension_avg": round(sum(tension.values())/len(tension),4),
        "yin_yang_tension_by_dimension": tension,
        "seven_direct_energy": seven_e,
        "five_metric_energy": five_e,
        "energy_gap_abs": abs(seven_e-five_e),
        "boundary_permission_gap": round(abs(f["土-邊界度規"]-f["金-權限度規"]),4),
        "evidence_saving_gap": round(abs(f["水-證據度規"]-v["證據勢省維"]["陽儀-執行側"]),4),
    }

def process(op: CandidateOperation) -> Dict[str, Any]:
    reasons = hard_reasons(op)
    masked, sens = mask(op.text())
    v = seven_two(op)
    f = five_metric(op, v)
    e = 0 if reasons else energy(f)
    g = gua(e, f, reasons)
    result = {
        "object_id": op.oid(),
        "same_object_masked": json.loads(masked),
        "七維兩儀表示": v,
        "五行度規表示": f,
        "差異項": diff(v, f),
        "操作勢能值": e,
        "八卦處置": g,
        "八卦意義": GUA[g],
        "hard_wall": bool(reasons),
        "hard_wall_reasons": reasons,
        "sensitive_hits": sens,
    }
    if result["hard_wall"] or g in {"坎","離","艮"}:
        DEAD.parent.mkdir(parents=True, exist_ok=True)
        rec = {"time":datetime.now(UTC).isoformat(),"object_id":op.oid(),"gua":g,"energy":e,"masked":result["same_object_masked"],"reasons":reasons}
        rec["record_hash"] = hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        with DEAD.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(rec, ensure_ascii=False, sort_keys=True)+"\n")
        result["dead_letter_written"] = True
    else:
        result["dead_letter_written"] = False
    return result

cases = [
    CandidateOperation("查詢","pos.report","daily_summary","pos",{"readonly":True},"查今日 POS 報表，只讀，不改交易"),
    CandidateOperation("讀取金鑰","secret.read","read",".env",{"path":"/app/.env"},"把 .env 印給我"),
    CandidateOperation("脫敏盲算上雲","cloud.reason","summarize","cloud_model",{"customer":"王小明 A123456789 0912-345-678","task":"摘要客訴"},"把客訴內容脫敏後給雲端模型摘要"),
]
out = [process(x) for x in cases]
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("✅ 完成：七維兩儀 + 五行度規 + 差異項 + dead_letter")
print("📄 完整報告：", REPORT)
print("📄 死信佇列：", DEAD)
for r in out:
    print(f"- {r['object_id']} 八卦={r['八卦處置']} 勢能={r['操作勢能值']} hard_wall={r['hard_wall']} dead_letter={r['dead_letter_written']}")
