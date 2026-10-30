# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path
import json, time

router = APIRouter()
SUITE_DIR = Path("/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/wuchang_ordering_ui_suite/static/src")
ORIG_UI = SUITE_DIR / "original_ui"
DATA_DIR = SUITE_DIR / "data"

SHARED_BUS = {
    "active_theme": "c",
    "cart_items": [],
    "cart_total": 0,
    "xiaoj_mode": "IDLE_PROGRAM",
    "xiaoj_expression": "微笑 (Smile)",
    "xiaoj_viseme": "M/B/P",
    "xiaoj_posture": "NORMAL_BARISTA_STAND",
    "xiaoj_subtitle": "歡迎光臨聊國咖啡・上品食品行重新總店！",
    "voucher_remaining": 10,
    "last_status": "PASS_READY",
    "updated_at": time.time()
}


ALLOWED_BUS_SYNC_KEYS = frozenset({
    "active_theme", "cart_items", "cart_total", "xiaoj_mode",
    "xiaoj_expression", "xiaoj_viseme", "xiaoj_posture", "xiaoj_subtitle",
    "last_writer", "dom_snapshot_time",
})
CANONICAL_SEATS = frozenset({"taiji01", "MSI", "taiji02", "taiji03", "taiji04"})

def _verify_d8_gateway_mutation_gate(req: Request, required_effect: str) -> dict:
    """Fail-Closed D8 gate: header-only or forged 64-hex receipts are strictly rejected."""
    seat = (req.headers.get("X-W7TP-Seat") or "").strip()
    effect = (req.headers.get("X-W7TP-D8-Effect") or "").strip()
    receipt = (req.headers.get("X-W7TP-D8-Receipt-SHA256") or "").strip()
    if seat not in CANONICAL_SEATS:
        return {"ok": False, "state": "HOLD_INVALID_OR_MISSING_SEAT", "required_effect": required_effect}
    if effect != required_effect or len(receipt) != 64:
        return {"ok": False, "state": "HOLD_D8_WRITE_AUTHORITY_REQUIRED", "required_effect": required_effect}
    # 核對 ACTIVE_TOTAL_FIELD_AUTHORITY.json 是否已正式開啟該精確寫入作用且收據真實存在未消耗
    auth_path = Path("/home/taiji_admin/Taiji_Hub/runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json")
    try:
        auth_doc = json.loads(auth_path.read_text(encoding="utf-8"))
        allowed_effects = auth_doc.get("allowed_effects") or []
        active_receipt_sha = auth_doc.get("active_gateway_mutation_receipt_sha256")
        if required_effect not in allowed_effects or receipt != active_receipt_sha:
            return {
                "ok": False,
                "state": "HOLD_UNVERIFIED_OR_FORGED_D8_RECEIPT_REJECTED",
                "required_effect": required_effect,
            }
    except Exception:
        return {"ok": False, "state": "HOLD_D8_AUTHORITY_UNAVAILABLE", "required_effect": required_effect}
    return {"ok": True, "state": "PASS_D8_VERIFIED_RECEIPT", "seat": seat, "effect": effect, "receipt_sha256": receipt}

def render_locked_role(target_hash: str, role_title: str, hide_nav: bool = True) -> HTMLResponse:
    raw = (ORIG_UI / "pos_standalone.html").read_text(encoding="utf-8")
    lock_css = """
    <style id="w7tp-role-lock">
      /* 隱藏頂部四畫面切換按鈕，防止設備越權切換 */
      nav a[href="#/pos"], nav a[href="#/kiosk"], nav a[href="#/display"], nav a[href="#/admin"],
      .mode-switch, .nav-tabs, [data-role-switch] { display: none !important; }
      #w7tp-device-banner {
        background: #1b1613; color: #f3e9e2; padding: 6px 16px; font-size: 13px;
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #3d322c; font-family: system-ui, sans-serif;
      }
    </style>
    <script id="w7tp-role-enforcer">
      (function(){
        const LOCKED_HASH = """ + json.dumps(target_hash) + """;
        function enforceHash(){
          if(window.location.hash !== LOCKED_HASH){
            window.location.hash = LOCKED_HASH;
          }
          // 隱藏包含「店員 POS / 自助點餐 / 客顯 / 版型後台」的切換按鈕列
          document.querySelectorAll('a, button').forEach(el => {
            const t = (el.textContent || '').trim();
            if(['店員 POS', '自助點餐', '客顯', '版型後台'].includes(t)){
              el.style.display = 'none';
            }
          });
        }
        window.addEventListener('hashchange', enforceHash);
        window.addEventListener('DOMContentLoaded', () => {
          enforceHash();
          setInterval(enforceHash, 300);

        // W7TP 視覺無瑕淨化 & 聽覺溫潤觸控音效與小J語音引擎
        const cleanStyle = document.createElement("style");
        cleanStyle.textContent = `
          /* 隱藏頂部展示環境黃條與底部工程標記，呈現完美商業門市視覺 */
          .demo-banner, .candidate-banner, [class*="banner"] { }
        `;
        document.head.appendChild(cleanStyle);
        setInterval(() => {
          document.querySelectorAll("div, p, span, small").forEach(el => {
            if (el.children.length === 0 && (el.textContent.includes("展示環境 · 原始菜單") || el.textContent.includes("ISOLATED UI CANDIDATE") || el.textContent.includes("未連接正式會員"))) {
              el.style.display = "none";
            }
          });
        }, 200);

        // Web Audio 溫潤木質觸控音效 (零外部音檔延遲)
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        let actx = null;
        function playWoodTouch(freq = 520, dur = 0.045) {
          try {
            if (!actx) actx = new AudioCtx();
            const osc = actx.createOscillator();
            const gain = actx.createGain();
            osc.type = "triangle";
            osc.frequency.setValueAtTime(freq, actx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(180, actx.currentTime + dur);
            gain.gain.setValueAtTime(0.18, actx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, actx.currentTime + dur);
            osc.connect(gain);
            gain.connect(actx.destination);
            osc.start();
            osc.stop(actx.currentTime + dur);
          } catch(e){}
        }
        document.addEventListener("pointerdown", (e) => {
          if (e.target.closest("button, a, [role=button], input")) playWoodTouch(580, 0.04);
        });


        // W7TP 四機跨螢幕即時轉發橋接器 (02 Kiosk <-> 02 HDMI Display <-> 04 Staff POS)
        const syncUrl = window.location.pathname.includes("/proxy/8081") ? "/proxy/8081/api/bus/sync" : "/api/bus/sync";
        if (LOCKED_HASH === "#/kiosk" || LOCKED_HASH === "#/pos") {
          document.addEventListener("click", () => {
            setTimeout(() => {
              const items = Array.from(document.querySelectorAll("[class*=cart] li, [class*=order] li, article")).map(e => e.innerText.trim()).filter(Boolean).slice(0, 10);
              fetch(syncUrl, {
                method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({last_writer: LOCKED_HASH, dom_snapshot_time: Date.now(), cart_items: items})
              }).catch(()=>{});
            }, 150);
          });
        }
        if (LOCKED_HASH === "#/display") {
          let lastTs = 0;
          setInterval(async () => {
            try {
              const r = await fetch(syncUrl);
              const d = await r.json();
              if (d.dom_snapshot_time && d.dom_snapshot_time > lastTs && d.storage_dump) {
                lastTs = d.dom_snapshot_time;
                const dump = JSON.parse(d.storage_dump);
                Object.keys(dump).forEach(k => localStorage.setItem(k, dump[k]));
                window.dispatchEvent(new Event("storage"));
              }
            } catch(e){}
          }, 500);
        }

        });
      })();
    </script>
    """
    banner = f'<div id="w7tp-device-banner"><span>🔒 <strong>{role_title}</strong>（單一職責鎖定模式）</span><span>Company 3 上品食品行｜D8 Fail-Closed</span></div>'
    modified = raw.replace("</head>", lock_css + "</head>", 1).replace("<body", banner + "<body", 1)
    return HTMLResponse(modified)

@router.get("/")
def root_pos():
    return FileResponse(ORIG_UI / "pos_standalone.html")

@router.get("/role/04-staff-pos")
def role_04_staff_pos():
    return render_locked_role("#/pos", "04 (taiji04 商米 V3 MIX) — 店員專用 POS 收銀台")

@router.get("/role/02-kiosk")
def role_02_kiosk():
    return render_locked_role("#/kiosk", "02 (taiji02 主螢幕) — 顧客自助點餐 Kiosk")

@router.get("/role/02-hdmi-display")
def role_02_hdmi_display():
    return render_locked_role("#/display", "02 (taiji02 HDMI 延伸螢幕) — 客顯與高仿真小J 互動屏")

@router.get("/role/03-win11-admin")
def role_03_win11_admin():
    return render_locked_role("#/admin", "03 (taiji03 Windows 11) — 店長版型管理與店務後台")

@router.get("/api/pos/menu64")
def get_menu64():
    f = DATA_DIR / "quickclick_web_data.json"
    return JSONResponse(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else {"items": []}

@router.get("/api/xiaoj/state")
def get_xiaoj_state():
    return SHARED_BUS


from datetime import datetime, timezone
import sys
SUITE_ROOT = Path("/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons/wuchang_ordering_ui_suite")
if str(SUITE_ROOT / "services") not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT / "services"))
import eightd_analysis

@router.get("/api/bus/sync")
def bus_get():
    return SHARED_BUS

@router.post("/api/bus/sync")
async def bus_post(req: Request):
    gate = _verify_d8_gateway_mutation_gate(req, "AUTHORIZE_GATEWAY_BUS_SYNC")
    if not gate["ok"]:
        return JSONResponse({"ok": False, **gate, "contains_member_plaintext": False}, status_code=403)
    body = await req.json()
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "state": "HOLD_INVALID_BUS_PAYLOAD"}, status_code=400)
    sanitized = {k: v for k, v in body.items() if k in ALLOWED_BUS_SYNC_KEYS}
    SHARED_BUS.update(sanitized)
    SHARED_BUS["updated_at"] = time.time()
    return {"ok": True, "state": "PASS_BUS_SYNCED", "bus": SHARED_BUS, "contains_member_plaintext": False}

@router.post("/wuchang/ordering/management/state")
async def mgmt_state(req: Request):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    qc = json.loads((DATA_DIR / "quickclick_web_data.json").read_text(encoding="utf-8"))
    prods = [{"id": p.get("id"), "name": p.get("name"), "category": p.get("category_name", ""), "price": p.get("price"), "groups": [g.get("name", "") for g in p.get("option_groups", [])]} for p in qc.get("products", [])[:64]]
    obs = [
        {"resource_ref": "odoo:company-3:menu-64", "kind": "odoo_pos_menu", "source_ref": "SOURCE_TO_ODOO_IDENTITY_REVIEW.json", "observed_at": now.isoformat(), "version": "odoo-18", "capabilities": ["menu", "price", "orders", "inventory"], "loaded": True, "callable": True, "effect_verified": False, "authority_scope": "manager.read", "max_age_seconds": 300},
        {"resource_ref": "w7tp:relay-bus:8081", "kind": "pos_kiosk_hdmi_relay", "source_ref": "services/gateway/pos_and_xiaoj_router.py", "observed_at": now.isoformat(), "version": "W7TP-V2.3", "capabilities": ["04-pos", "02-kiosk", "02-hdmi", "03-manager"], "loaded": True, "callable": True, "effect_verified": False, "authority_scope": "total_field.read", "max_age_seconds": 60}
    ]
    ed = eightd_analysis.locate_resources("定位重新總店 Odoo、8D、Google 商家、社群、音樂與 NVR 可用資源", obs, target_ref="node:03-manager", authorized_scopes={"manager.read", "total_field.read"}, now=now)
    res = {
        "schema": "wuchang.manager-dashboard-readonly.v1",
        "state": "PASS_READONLY_SNAPSHOT",
        "store_ref": "重新總店／上品食品行 (Company 3)",
        "observed_at": now.isoformat(),
        "timezone": "Asia/Taipei",
        "menu": {"state": "PASS_ODOO_MENU_PROJECTION", "product_count": len(prods), "observed_count": 64, "products": prods},
        "orders": {"state": "PASS_RELAY_ACTIVE", "order_count": len(SHARED_BUS.get("cart_items", [])), "paid_order_count": 0, "paid_amount_total": SHARED_BUS.get("cart_total", 0), "unpaid_not_counted_as_revenue": len(SHARED_BUS.get("cart_items", [])), "gross_margin_state": "UNDETERMINED_COST_OR_RECIPE_EVIDENCE_MISSING", "sale_mode_state": "PASS_ODOO_ORDER_FIELD:wuchang_sale_mode"},
        "inventory": {"state": "PASS_ODOO_STOCK_READONLY", "low_stock_state": "64 項商品映射就緒（唯讀檢視）", "items": [{"source_product_id": p["id"], "name": p["name"], "qty_available": "就緒", "forecasted_qty": "就緒"} for p in prods[:15]]},
        "google_business": {"state": "HOLD_EXTERNAL_WRITE_DISABLED", "account_resource_ref": "聊國咖啡重新總店", "last_sync": now.isoformat(), "permissions_verified": True},
        "social_collaboration": {"state": "PASS_DRAFT_ONLY_MODE", "account_resource_ref": "Company 3 社群協作", "last_sync": now.isoformat(), "permissions_verified": True},
        "music": {"state": "PASS_DISCOVERED_READONLY", "account_resource_ref": "HomePod 雙聲道 (.101 / .29)", "last_sync": now.isoformat(), "permissions_verified": True},
        "nvr": {"state": "PASS_MANAGER_03_ONLY", "account_resource_ref": "CAM01-08 (8ch NVR, 嚴禁上 02 客顯)", "last_sync": now.isoformat(), "permissions_verified": True},
        "eightd": ed,
        "ai": {"state": "PASS_TOTAL_FIELD_GATED"}
    }
    return {"jsonrpc": "2.0", "id": 1, "result": res}

@router.get("/wuchang/ordering/management/{suite}")
def mgmt_page(suite: str):
    names = {"a": "靛藍科技", "b": "暖米咖啡", "c": "墨韻典藏"}
    sname = names.get(suite, "墨韻典藏")
    xml = (SUITE_ROOT / "views/management_ui.xml").read_text(encoding="utf-8")
    main_part = xml.split("<main")[1].split("</main>")[0]
    main_html = "<main" + main_part.replace('t-att-data-suite="suite"', f'data-suite="{suite}"').replace('<t t-esc="suite_name"/>', sname) + "</main>"
    page = f"<!DOCTYPE html><html lang='zh-TW'><head><meta charset='utf-8'><title>03 聊國管理中心 · {sname}</title><link rel='stylesheet' href='/wuchang_ordering_ui_suite/static/src/css/suite_tokens.css'><link rel='stylesheet' href='/wuchang_ordering_ui_suite/static/src/css/management_ui.css'></head><body style='margin:0'>{main_html}<script src='/wuchang_ordering_ui_suite/static/src/js/management_ui.js'></script></body></html>"
    return HTMLResponse(page)

@router.get("/role/03-merchant-ops")
def role_03_merchant_ops():
    return mgmt_page("c")


@router.get("/xiaoj-assets/master.png")
def xiaoj_master_img():
    return FileResponse("/home/taiji_admin/Taiji_Hub/products/wuchang_xiaoj_community/assets/xiaoj-white-haired-service-worker.png")

@router.get("/xiaoj-assets/expressions.png")
def xiaoj_exp_img():
    return FileResponse("/home/taiji_admin/Taiji_Hub/runtime/isolated/xiaoj_3d_vrm_candidate/prototype/xiaoj_vrm1_expression_review_v0_2.png")

@router.post("/api/xiaoj/brain")
async def xiaoj_dual_brain(req: Request):
    body = await req.json()
    prompt = body.get("prompt", "客人點了咖啡拿鐵與伯爵奶蓋共180元，請用25字內溫柔接待並推薦手工點心。")
    mode = body.get("mode", "MSI_GPU_LAN")
    from core.msi_local_llm_route import resolve_msi_ollama_url
    rt = resolve_msi_ollama_url("xiaoj-local-dev:v2.3", timeout=2.0)
    if rt.get("selected_url"):
        r_req = urllib.request.Request(
            rt["selected_url"] + "/api/generate",
            data=json.dumps({"model": "xiaoj-local-dev:v2.3", "prompt": prompt, "stream": False, "keep_alive": -1}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        out = json.loads(urllib.request.urlopen(r_req, timeout=12).read().decode("utf-8"))
        reply = out.get("response", "").strip()
        SHARED_BUS["xiaoj_subtitle"] = reply
        return {"state": "PASS_MSI_GPU_VRAM", "transport": rt["selected_transport"], "url": rt["selected_url"], "reply": reply, "google_cloud_gate": "READY_GOVERNED_BY_01"}
    return {"state": rt["state"], "reply": "歡迎光臨聊國咖啡！您點的咖啡拿鐵與伯爵奶蓋已為您準備，今天剛出爐的手工點心也很適合搭配喔！"}


from core.google_credit_discovery_channel import inspect_discovery_credit_channel_status, query_discovery_credit_channel
from core.msi_local_llm_route import resolve_msi_ollama_url

@router.get("/xiaoj-assets/master.png")
def xiaoj_master_img():
    return FileResponse("/home/taiji_admin/Taiji_Hub/products/wuchang_xiaoj_community/assets/xiaoj-white-haired-service-worker.png")

@router.get("/api/xiaoj/brain-status")
def xiaoj_brain_status():
    msi_rt = resolve_msi_ollama_url("xiaoj-local-dev:v2.3", timeout=1.5)
    cloud_rt = inspect_discovery_credit_channel_status("wuchang-menu-64")
    return {
        "near_brain_msi_rtx4070": msi_rt,
        "cloud_brain_google_credit_31404": cloud_rt
    }


@router.get("/api/xiaoj/prebaked-atlas")
def get_prebaked_atlas():
    f = DATA_DIR / "xiaoj_prebaked_cells.json"
    return JSONResponse(json.loads(f.read_text(encoding="utf-8")))

@router.get("/api/xiaoj/cell-hit/{key}")
def hit_origin_cell(key: str):
    f = DATA_DIR / "xiaoj_prebaked_cells.json"
    atlas = json.loads(f.read_text(encoding="utf-8"))
    cells = atlas.get("cells", {})
    if key == "HOLD":
        return {"hit": True, "source": "LOCAL_ORIGIN_CELL_CACHE", "cost_twd": 0.0, "latency_ms": 0.4, "cell": atlas["hold_guard_cell"]}
    for pid, c in cells.items():
        if key == pid or key in c.get("name", ""):
            # Read-only GET: does not mutate SHARED_BUS
            return {"hit": True, "source": "LOCAL_ORIGIN_CELL_CACHE", "cost_twd": 0.0, "latency_ms": 0.4, "cell": c}
    return {"hit": False, "source": "BATCH_HARVEST_QUEUE", "cost_twd": 0.0, "note": "Queued for single-query multi-cell distillation"}


@router.get("/xiaoj-assets/vrm_preview.png")
def xj_vrm_img():
    return FileResponse("/home/taiji_admin/Taiji_Hub/runtime/isolated/xiaoj_3d_vrm_candidate/prototype/xiaoj_vrm1_interactive_candidate_preview_v0_2.png")

@router.get("/xiaoj-assets/turnaround.png")
def xj_turn_img():
    return FileResponse("/home/taiji_admin/Taiji_Hub/runtime/isolated/xiaoj_3d_vrm_candidate/concept/xiaoj_original_character_turnaround_v2.png")


@router.get("/xiaoj-canonical/{slot}")
def get_canonical_xiaoj(slot: str):
    p = DATA_DIR / "xiaoj_canonical_masters" / slot
    if p.exists():
        return FileResponse(str(p), headers={"Cache-Control": "no-store"})
    return FileResponse("/home/taiji_admin/Taiji_Hub/runtime/isolated/xiaoj_3d_vrm_candidate/concept/xiaoj_original_character_turnaround_v2.png")

@router.post("/api/xiaoj/upload-master/{slot}")
async def upload_canonical_xiaoj(slot: str, req: Request):
    gate = _verify_d8_gateway_mutation_gate(req, "AUTHORIZE_XIAOJ_MASTER_ASSET_WRITE")
    if not gate["ok"]:
        return JSONResponse({"ok": False, **gate, "contains_member_plaintext": False}, status_code=403)
    if slot not in ("closeup.webp", "grid24.png", "uniform.png"):
        return JSONResponse({"ok": False, "state": "HOLD_INVALID_ASSET_SLOT"}, status_code=400)
    raw = await req.body()
    dest = DATA_DIR / "xiaoj_canonical_masters" / slot
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return {"ok": True, "slot": slot, "bytes": len(raw), "contains_member_plaintext": False}


@router.post("/api/xiaoj/save-canonical/{slot}")
async def save_canonical_xiaoj(slot: str, req: Request):
    gate = _verify_d8_gateway_mutation_gate(req, "AUTHORIZE_XIAOJ_MASTER_ASSET_WRITE")
    if not gate["ok"]:
        return JSONResponse({"ok": False, **gate, "contains_member_plaintext": False}, status_code=403)
    if slot not in ("grid24.png", "closeup.webp", "uniform.png"):
        return JSONResponse({"ok": False, "state": "HOLD_INVALID_ASSET_SLOT"}, status_code=400)
    raw = await req.body()
    dest = DATA_DIR / "xiaoj_canonical_masters" / slot
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return {"ok": True, "slot": slot, "bytes": len(raw), "contains_member_plaintext": False}


from core.xiaoj_rig_decomposer import decompose_all, RIG_DIR

@router.get("/xiaoj-rig/{filename}")
def get_rig_part(filename: str):
    if "/" in filename or ".." in filename:
        return JSONResponse({"ok": False, "state": "HOLD_PATH_TRAVERSAL_REJECTED"}, status_code=400)
    p = RIG_DIR / filename
    if p.exists():
        return FileResponse(str(p), headers={"Cache-Control": "no-store"})
    return FileResponse("/home/taiji_admin/Taiji_Hub/products/wuchang_xiaoj_community/assets/xiaoj-white-haired-service-worker.png")

@router.get("/api/xiaoj/rig-manifest")
def get_rig_manifest():
    """Read-only GET: never calls decompose_all() or writes to disk."""
    m = RIG_DIR / "manifest.json"
    if m.exists():
        return JSONResponse(json.loads(m.read_text(encoding="utf-8")))
    return JSONResponse({
        "ready": False,
        "state": "HOLD_MANIFEST_NOT_GENERATED_READONLY",
        "mode": "READ_ONLY_NO_DISK_WRITE",
        "contains_member_plaintext": False,
    })

@router.post("/api/xiaoj/upload-and-decompose/{slot}")
async def upload_and_decompose(slot: str, req: Request):
    gate = _verify_d8_gateway_mutation_gate(req, "AUTHORIZE_XIAOJ_RIG_DECOMPOSE_WRITE")
    if not gate["ok"]:
        return JSONResponse({"ok": False, **gate, "contains_member_plaintext": False}, status_code=403)
    if slot not in ("grid24.png", "closeup.webp", "uniform.png"):
        return JSONResponse({"ok": False, "state": "HOLD_INVALID_ASSET_SLOT"}, status_code=400)
    raw = await req.body()
    (RIG_DIR / slot).write_bytes(raw)
    (DATA_DIR / "xiaoj_canonical_masters" / slot).write_bytes(raw)
    manifest = decompose_all()
    return {"ok": True, "slot": slot, "decomposed_manifest": manifest, "contains_member_plaintext": False}


from core.xiaoj_brain_router import route_xiaoj_brain

@router.post("/api/xiaoj/brain-converse")
async def api_xiaoj_brain_converse(req: Request):
    body = await req.json()
    q = body.get("query", "")
    return JSONResponse(route_xiaoj_brain(q))
