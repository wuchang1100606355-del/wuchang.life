from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEMO = (
    ROOT.parent.parent
    / "Taiji_Odoo"
    / "addons"
    / "wuchang_cafe_ai_gateway"
    / "static"
    / "src"
    / "competition_2026"
)


def read(name: str) -> str:
    return (DEMO / name).read_text(encoding="utf-8")


def test_demo_uses_same_scene_pack_as_complete_system_core():
    core_pack = json.loads((ROOT / "sovereign_xiaoj_scene_pack.json").read_text(encoding="utf-8"))
    demo_pack = json.loads(read("sovereign_xiaoj_scene_pack.json"))
    assert demo_pack == core_pack
    assert demo_pack["system_definition"]["system_kind"] == "8D_ADI_COMPLETE_AI_APPLICATION_SYSTEM"
    assert demo_pack["system_definition"]["complete_ai_application_system"] is True


def test_demo_has_custom_codex_pet_and_no_rejected_geometric_placeholder():
    html = read("index.html")
    css = read("xiaoj_competition.css")
    assert "自訂 Codex 小 J" in html
    assert 'url("xiaoj-codex-v2.webp")' in css
    assert (DEMO / "xiaoj-codex-v2.webp").stat().st_size > 1_000_000
    assert "geometric" not in html.lower()


def test_demo_covers_multimodal_state_and_complete_d1_d8_loop():
    html = read("index.html")
    js = read("xiaoj_competition.js")
    for text in ("影像", "聲音", "網路狀態", "設備能力", "離散精準索引", "高維浮點理解"):
        assert text in html
    for dimension in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"):
        assert f'["{dimension}"' in js
    assert "總場裁決效果" in js
    assert "重新觀測與記錄" in js


def test_demo_has_no_outbound_transport_or_live_write_api():
    combined = "\n".join(read(name) for name in ("index.html", "xiaoj_competition.css", "xiaoj_competition.js"))
    forbidden = (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "sendBeacon",
        "/web/dataset/call_kw",
        "/api/control",
        "http://",
        "https://",
    )
    for token in forbidden:
        assert token not in combined


def test_earthquake_path_is_explicitly_simulation_and_effects_are_proposals():
    html = read("index.html")
    js = read("xiaoj_competition.js")
    assert "這是隔離模擬資料，不是國家警報" in html
    assert "設備控制只形成提案" in js
    assert "趴下、掩護、穩住" in html
    assert "趴下、掩護、穩住" in js


def test_image_and_voice_fallbacks_stay_local_and_fail_closed():
    js = read("xiaoj_competition.js")
    assert "file.arrayBuffer()" in js
    assert 'crypto.subtle.digest("SHA-256", buffer)' in js
    assert "不做人臉年齡或性別推論" in js
    assert "保持未知，不改送雲端" in js


def test_browser_online_signal_is_not_relabelled_as_verified_lan():
    js = read("xiaoj_competition.js")
    assert "瀏覽器回報線上（路徑未驗證）" in js
    assert "LAN／網際路徑可用" not in js
    assert "路徑待驗證" in js


def test_yaml_contract_has_required_complete_system_and_d6_boundaries():
    contract = (ROOT / "8d_adi_complete_system_contract.yaml").read_text(encoding="utf-8")
    assert "\t" not in contract
    for required in (
        "state: CANDIDATE",
        "canonical: false",
        "active: false",
        "live_effect: false",
        "final_authority: false",
        "kind: 8D_ADI_COMPLETE_AI_APPLICATION_SYSTEM",
        "smallest_complete_unit: D1_D8_DIGITAL_BRAIN_CELL",
        "D1: INTENT",
        "D2: MULTIMODAL_AND_SYSTEM_STATE",
        "D3: COORDINATE",
        "D4: EVIDENCE",
        "D5: EXECUTION_AND_POLICY",
        "D6: GENERATIVE_TRANSMISSION",
        "D7: RISK_AND_QUARANTINE",
        "D8: ENVELOPE_AND_AUTHORITY",
        "TARGET_BASE_STATE: REQUIRED",
        "MINIMUM_REQUIRED_DELTA: REQUIRED",
        "REFERENCES: REQUIRED",
        "COORDINATES: REQUIRED",
        "RECONSTRUCTION_RULES: REQUIRED",
        "VERIFICATION_RULES: REQUIRED",
        "output_authority: false",
        "bypass_allowed: false",
    ):
        assert required in contract
