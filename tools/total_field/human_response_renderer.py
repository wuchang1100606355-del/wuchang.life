#!/usr/bin/env python3
"""Human-facing renderer for Total Field gate results.

The renderer turns internal gate decisions into natural-language replies. It
does not expose raw D1-D8 fields, verifier internals, ADI rules, H64, or TD.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


PASS = "PASS"
HOLD = "HOLD"
BLOCK = "BLOCK"

INTERNAL_MARKERS = (
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7",
    "D8",
    "H64",
    "TD",
    "proof_D7",
    "env_D8",
    "trajectory_hmac",
    "nonce",
)

XIAOJ_PROJECTIONS = {
    "LINE": ("COMMUNITY_SERVICE_STAFF", "community"),
    "ODOO": ("MERCHANT_SERVICE_STAFF", "merchant"),
    "WEB": ("GENERAL_XIAOJ", "general"),
}

PASS_OPENERS = (
    "收到，你的需求很清楚。",
    "我先幫你整理一版可以直接對接的候選回覆。",
    "好的，我先把這段意圖安全包進總場候選流程。",
)

PASS_CLOSINGS = (
    "如果你要，我可以再提供 2 個不同語氣版本。",
    "你若要我再短一點，我可以立刻改成更精簡版。",
    "我先不做任何正式送件，先把候選版本卡在這裡。",
)

HOLD_OPENERS = (
    "我想先幫你保守一點。",
    "我會先按住節奏，不越權。",
    "我先保全邊界，避免先行做正式動作。",
)

HOLD_CLOSINGS = (
    "你可以補一個更清楚的邊界條件再繼續。",
    "我會等你確認後再重新跑一次。",
    "先這樣保全，等你回一句我就接著回。",
)

BLOCK_OPENERS = (
    "這個請求目前不能直接候選。",
    "我先暫停這次路徑。",
    "先不用做這件事比較安全。",
)

BLOCK_CLOSINGS = (
    "你可以改成確認用的條件再試。",
    "我保留為候選草稿，待總場核可。",
    "現在不會有正式權威動作。",
)

SCENARIO_KEYWORDS = {
    "member_registration": (
        "註冊",
        "註冊會員",
        "加入會員",
        "會員資料",
        "sign up",
        "signup",
        "register",
        "register me",
        "create account",
        "建立帳號",
    ),
    "support_complaint": (
        "抱怨",
        "問題",
        "故障",
        "退費",
        "退款",
        "退單",
        "無法",
        "help",
        "support",
        "客服",
        "申訴",
        "錯誤",
    ),
    "order_or_booking": (
        "訂單",
        "下單",
        "訂購",
        "點單",
        "order",
        "booking",
        "預約",
        "reserve",
        "預定",
        "菜單",
        "menu",
        "購買",
    ),
}

SCENARIO_LITERARY_HINT = {
    "member_registration": {
        "tone": "溫柔起步",
        "scene": "像迎接新夥伴入場，先把身份節點對齊再讓流程啟動。",
        "cta": "要不要我先幫你整理一版註冊流程的最小欄位清單？",
        "poetic_tail": "有了名字與同意，我們就能把第一道門打開。",
    },
    "order_or_booking": {
        "tone": "體貼服務",
        "scene": "像在櫃台逐筆確認需求，先對齊口味、時間與人數。",
        "cta": "我可以先整理 3 個可核對的候選方案給你。",
        "poetic_tail": "先把條件畫好線，下一步就能走到可送件。",
    },
    "support_complaint": {
        "tone": "誠懇穩定",
        "scene": "先把情緒平穩下來，將問題拆成可驗證步驟。",
        "cta": "你補齊發生時間與步驟，我幫你整理給總場。",
        "poetic_tail": "先把雜訊降到最低，證據與建議就能更精準。",
    },
}

MEMBER_VALUE_BRIEF = {
    "member_registration": (
        "把你的資料先整理成「可直接帶入」的會員最小欄位。",
        "同步建立偏好、同意紀錄與下次回訪權重。",
        "後續可直接用於預約、點餐與專屬建議，不再重複問資料。",
    ),
    "order_or_booking": (
        "先幫你整理可核對項目，讓下單/預約少一步折返。",
        "同時保留時間、口味、人數與配送邊界，方便你快速修正。",
        "候選答案會保持可追蹤版本，避免因一次訊息錯漏而中斷。",
    ),
    "support_complaint": (
        "把問題拆成可驗證步驟，先穩定情緒再往下判定。",
        "保留「時間／設備／重現步驟」作為後續處理素材。",
        "回報會有保全級封存邏輯，方便下一階段人工追蹤。",
    ),
    "general": (
        "先做可驗證的候選回覆，保留正式動作到人工確認。",
        "所有回應都保留安全邊界，避免越權寫入或自動送件。",
        "必要條件補齊後，可直接走到可執行的下一步。",
    ),
}


REGISTRATION_ACTION_DRAFT = {
    "mode": "registration_draft",
    "goal": "啟動會員最小入場流程（不觸發正式寫入）",
    "required_fields": (
        "顯示名稱",
        "聯絡方式",
        "同意隱私與會員規範",
    ),
    "optional_fields": (
        "生日",
        "偏好類型",
        "推薦訊息接受偏好",
        "是否加入回訪提醒",
    ),
    "verification_checks": (
        "欄位完整性",
        "同意條款核對",
        "避免重複帳號",
        "風險欄位已清空",
    ),
    "human_confirmation": "請回覆『我同意並補齊』進入下一輪候選核可。",
    "candidate_note": "僅保留草稿，不進行正式建立。",
}

BOOKING_ACTION_DRAFT = {
    "mode": "booking_draft",
    "goal": "整理可核對下單/預約參數（不送出正式單）",
    "required_fields": (
        "品項或服務",
        "時間",
        "人數",
        "聯絡方式",
    ),
    "optional_fields": (
        "口味",
        "備註",
        "是否外送",
        "預備替代時間",
    ),
    "verification_checks": (
        "時段可用性",
        "品項可提供性",
        "支付與憑證未觸發",
        "敏感條件未開啟",
    ),
    "human_confirmation": "請回覆核對欄位無誤後，才能進入正式流程。",
    "candidate_note": "預先整理候選路徑，避免一次訊息造成誤送。",
}

COMPLAINT_ACTION_DRAFT = {
    "mode": "complaint_draft",
    "goal": "固定問題重現步驟與時序（不介入正式作業）",
    "required_fields": (
        "發生時間",
        "裝置/通路",
        "問題重現步驟",
    ),
    "optional_fields": (
        "錯誤訊息截圖",
        "歷史訂單或紀錄編號",
        "期望解決結果",
    ),
    "verification_checks": (
        "情緒降溫語句已提示",
        "時間軸可重建",
        "回報內容可稽核",
    ),
    "human_confirmation": "請補齊時間與步驟後我再整理為最小風險候選。",
    "candidate_note": "先封存為可追蹤投訴草稿。",
}

GENERAL_ACTION_DRAFT = {
    "mode": "query_draft",
    "goal": "整理當下問題為可核對候選輸出",
    "required_fields": ("問題主題",),
    "optional_fields": ("時間", "情境", "偏好"),
    "verification_checks": ("邊界是否違規",),
    "human_confirmation": "補齊邊界條件後即可進一步候選。",
    "candidate_note": "保持可驗證、可追蹤，不直接落地。",
}


SOLUTION_SCENARIO_LIBRARY = {
    "member_registration": {
        "title": "會員註冊導向",
        "solve": "把自然語言快速轉為可核對的註冊條件草稿，先避開自動寫入。",
        "extend": "可延伸到名片導向、權益頁啟用、偏好預設。",
        "risk_prefix": "先補齊必要欄位與權益確認",
    },
    "order_or_booking": {
        "title": "預約與下單導向",
        "solve": "先抽取時間、品項、數量、偏好，生成可核對候選流程。",
        "extend": "可延伸到排程衝突檢查與外送條件提示。",
        "risk_prefix": "先補齊場景條件再進入候選",
    },
    "support_complaint": {
        "title": "客服支援導向",
        "solve": "把抱怨/問題先標準化為可回放的重現路徑，降低一次處理成本。",
        "extend": "可延伸到 SLA 建議與跨通路補件提醒。",
        "risk_prefix": "先補齊時間軸與重現步驟",
    },
    "risk_governance": {
        "title": "高風險請求守門",
        "solve": "先把高風險操作隔離，避免支付、寫入、部署、重啟誤觸。",
        "extend": "可延伸到權限審核清單與人確認雙簽流程。",
        "risk_prefix": "等待人工確認後再進入正式動作",
    },
    "general": {
        "title": "一般詢問導向",
        "solve": "先對齊語境與邊界，將可落地資訊整理成可理解回答。",
        "extend": "可延伸到「可執行清單化」與個人化語氣偏好。",
        "risk_prefix": "以 HOLD 優先，避免越權",
    },
}


def _action_draft_for_scenario(scenario: str, decision: str) -> dict[str, Any]:
    if decision != PASS:
        return {
            "mode": "hold_draft",
            "goal": "先保全決策邊界，等待條件補齊",
            "required_fields": (
                "邊界條件",
                "高風險確認",
            ),
            "optional_fields": ("備註",),
            "verification_checks": (
                "決策風險是否消除",
                "候選是否可重試",
            ),
            "human_confirmation": "條件補齊後再送一次。",
            "candidate_note": "暫停正式候選動作。",
        }

    if scenario == "member_registration":
        return dict(REGISTRATION_ACTION_DRAFT)
    if scenario == "order_or_booking":
        return dict(BOOKING_ACTION_DRAFT)
    if scenario == "support_complaint":
        return dict(COMPLAINT_ACTION_DRAFT)
    return dict(GENERAL_ACTION_DRAFT)


def _projection_for_channel(channel_name: str) -> tuple[str, str]:
    projection, service_context = XIAOJ_PROJECTIONS.get(channel_name, XIAOJ_PROJECTIONS["WEB"])
    return projection, service_context


def _voice_profile(decision: str, risk_level: str, channel_name: str) -> str:
    if decision == PASS:
        return "gentle_curator"
    if decision == BLOCK:
        return "firm_guard"
    if risk_level == "HIGH":
        return "steady_guarded"
    if channel_name == "LINE":
        return "line_careful"
    return "warm_boundary"


def _persona_traits(channel_name: str, decision: str) -> str:
    if channel_name == "LINE":
        base = "line_friend"
    elif channel_name == "ODOO":
        base = "odoo_partner"
    else:
        base = "web_host"
    if decision == BLOCK:
        return f"{base}_cautious"
    if decision == HOLD:
        return f"{base}_protective"
    return f"{base}_supportive"


def _seed_index(*parts: str, modulo: int) -> int:
    if modulo <= 0:
        return 0
    seed = "|".join(parts)
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % modulo


def _clean_text(text: Any, limit: int = 500) -> str:
    value = " ".join(str(text or "").split())
    for marker in INTERNAL_MARKERS:
        value = value.replace(marker, "[internal]")
    return value[:limit]


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("\n", " ").split())


def _classify_scenario(text: str) -> str:
    normalized = _normalize_text(text)
    for scenario, keywords in SCENARIO_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return scenario
    return "general"


def _build_solution_scenario(decision: str, scenario: str) -> dict[str, str]:
    key = scenario if scenario in SOLUTION_SCENARIO_LIBRARY else "general"
    profile = SOLUTION_SCENARIO_LIBRARY[key]
    decision_text = (
        "PASS：候選可交付「先行閱讀版」給客服。"
        if decision == PASS
        else ("先 HOLD：等待人工確認後再進入正式動作。" if key == "risk_governance" else f"HOLD：{profile['risk_prefix']}")
    )
    return {
        "key": key,
        "title": profile["title"],
        "solve": profile["solve"],
        "extend": profile["extend"],
        "risk": decision_text,
    }


def _hold_text(gate_result: dict[str, Any]) -> str:
    code = str(gate_result.get("gate_code") or "")
    if code == "HOLD_GT_DEFINITION_DRIFT":
        return "這個說法會混淆核心技術定義，我先暫停，只保留為候選內容，需人工確認後才能繼續。"
    if code == "HOLD_HARD_RISK_SIDE_EFFECT":
        return "這個要求涉及寫入、部署、重啟或正式送件等高風險操作，我先暫停，不會執行任何正式動作。"
    if code == "HOLD_ADI_5D_ABSOLUTE_INDEX":
        return "這個候選請求缺少必要索引條件，我先暫停，需補齊後再回覆。"
    return "這個候選需要再確認，我先暫停，不會執行任何正式動作。"


def _media_payload(
    decision: str,
    reply_text: str,
    risk_level: str,
) -> dict[str, Any]:
    if decision != PASS:
        return {
            "mode": "TEXT_ONLY",
            "audio_script": "",
            "voice_hint": "no_audio",
            "video_mode": "NONE",
            "video_hint": "高風險/待確認情況下不提供影像回覆。",
        }
    if risk_level == "HIGH":
        return {
            "mode": "TEXT_WITH_OPTIONAL_AUDIO",
            "audio_script": reply_text,
            "voice_hint": "慎重、停留確認步驟",
            "video_mode": "NONE",
            "video_hint": "高風險暫停中，不提供實際影像內容。",
        }
    return {
        "mode": "TEXT_WITH_AUDIO",
        "audio_script": reply_text,
        "voice_hint": "柔和、具同理的自然語氣",
        "video_mode": "STORYBOARD_HINT",
        "video_hint": "可由前端用文字分鏡做沉浸式展示；不涉及檔案搬運。",
    }


def _member_value_layer(decision: str, scenario: str) -> dict[str, Any]:
    values = MEMBER_VALUE_BRIEF.get(scenario, MEMBER_VALUE_BRIEF["general"])
    if decision != PASS:
        return {
            "mode": "候選保全",
            "highlighted_values": [
                "先保全決策邊界，避免在高風險動作中誤執行。",
                "保留完整場景脈絡，便於人工接續。",
            ],
            "next_readiness": [
                "補齊條件後可重新進入候選路徑。",
                "會在候選與正式權威隔離下保留可追蹤紀錄。",
            ],
        }
    return {
        "mode": "候選體驗",
        "highlights": [
            "對你可用的下一步是明確可選的。",
            f"{values[0]}",
            f"{values[1]}",
        ],
        "member_advantage": f"{values[2]}",
        "competitive_edge": "文學式回覆 + 低風險治理，讓對話更像顧客服務而非機器回報。",
    }


def _build_pass_text(
    base_body: str,
    channel_name: str,
    scenario: str = "general",
) -> tuple[str, str, str]:
    base = _clean_text(base_body)
    concise = f"{base}，我會先把候選保留在可追蹤狀態。"
    poetic = f"{base}。風景尚未定格，先讓安全感先落座，再把你的場景慢慢鋪開。"
    if channel_name == "LINE":
        friendly = f"收到！{base} 目前沒有執行付款、寫入、部署或重啟。我先幫你整理成可回覆版本。"
        concise = f"收到，我先整理了：{base}"
        poetic = f"{base}，讓一句可理解的文字先到位，先不做正式動作。"
    elif channel_name == "ODOO":
        friendly = f"已收到，先幫你整理可落地的候選回覆版本，並保持未執行正式提交。{base}"
        concise = f"{base}。我先卡在草稿階段，方便你核對。"
        poetic = f"{base}，如同簽呈前先做一次內部對齊。"
    else:
        friendly = f"{base} 目前沒有執行付款、寫入、部署或重啟。"

    if scenario in SCENARIO_LITERARY_HINT:
        hint = SCENARIO_LITERARY_HINT[scenario]
        poetic = f"{poetic}{(' ' + hint.get('poetic_tail', '')) if hint.get('poetic_tail') else ''}"
    return friendly, concise, poetic


def _literary_shape(
    decision: str,
    risk_level: str,
    channel_name: str,
    reply_text: str,
    scenario: str,
) -> dict[str, Any]:
    if decision == PASS and risk_level == "LOW":
        tone = "溫潤啟發"
        scene = "在清晨的服務廳裡，先做一個穩定且清楚的回應。"
        cta = "你如果想，我可以直接再補一版更有詩意的版本。"
        if scenario in SCENARIO_LITERARY_HINT:
            hint = SCENARIO_LITERARY_HINT[scenario]
            tone = hint.get("tone", tone)
            scene = hint.get("scene", scene)
            cta = hint.get("cta", cta)
        closing = "先把安全邊界保留在前面，回覆就能穩穩接上。"
        if channel_name == "LINE" and scenario in SCENARIO_LITERARY_HINT:
            cta = f"{cta} 你要我再用一句更短的口吻發給你？"
    elif decision == PASS and risk_level == "MEDIUM":
        tone = "溫和提醒"
        scene = "像在夜色裡調亮走廊，先避開高風險的門。"
        cta = "若你補齊條件，我會立刻回到候選路徑。"
        closing = "目前先保留可追蹤、可人工確認的答案。"
    else:
        tone = "克制等待"
        scene = "先按下保全紅線，待確認後再繼續展開。"
        cta = "你可補齊場景條件後再送出一則更精準訊息。"
        closing = "這一步不會觸發正式權威動作。"

    poetic_line = reply_text.replace("\n", " ")
    if len(poetic_line) > 120:
        poetic_line = poetic_line[:117] + "..."

    return {
        "brand_voice": "小J文學伴侶",
        "tone": tone,
        "scene": scene,
        "headline": "總場候選回覆" if decision == PASS else "總場保全回應",
        "poetic_line": f"《{poetic_line}》",
        "poem_line_2": closing,
        "next_action_hint": cta,
        "decision_aura": decision,
        "emotion": _seed_index(channel_name, decision, risk_level, reply_text, modulo=9) % 9,
    }


def _build_reply_variants(
    decision: str,
    risk_level: str,
    channel_name: str,
    reply_text: str,
    raw_body: str,
    scenario: str,
) -> dict[str, str]:
    scenario_open = {
        "member_registration": "先把最小欄位整理好：姓名、手機、同意條款。",
        "order_or_booking": "我先整理可核對項目：品項、時間、數量、到店/外送。",
        "support_complaint": "我先幫你抓住關鍵：時間、裝置、重現步驟。",
    }.get(scenario, "")
    poetic_tail = f" {SCENARIO_LITERARY_HINT[scenario]['poetic_tail']} {scenario_open}" if scenario in SCENARIO_LITERARY_HINT else ""

    if decision != PASS:
        return {
            "default": reply_text,
            "concise": reply_text[:220],
            "poetic": "我先把邊界保留在前，回覆會在你確認後接續完成。",
        }
    friendly, concise, poetic = _build_pass_text(raw_body, channel_name, scenario)
    if risk_level == "HIGH":
        return {
            "default": reply_text,
            "concise": concise,
            "poetic": f"{poetic}{poetic_tail}",
        }
    return {
        "default": reply_text,
        "concise": concise,
        "poetic": f"{poetic}{poetic_tail} {reply_text}",
    }


def _persona_voice_hint(risk_level: str) -> str:
    if risk_level == "HIGH":
        return "穩重、需要確認，避免先行承諾。"
    if risk_level == "MEDIUM":
        return "溫和提醒，先補齊條件再繼續。"
    return "熱情但不越權，用自然語言給出可落地候選。"


def render_human_response(gate_result: dict[str, Any] | None, channel: str = "web") -> dict[str, Any]:
    result = gate_result if isinstance(gate_result, dict) else {}
    decision = str(result.get("decision") or HOLD)
    risk_level = str(result.get("risk_level") or "MEDIUM")
    channel_name = str(channel or result.get("source_channel") or "web").upper()
    projection, service_context = _projection_for_channel(channel_name)
    scenario = "general"
    scenario_for_solution = "risk_governance" if decision != PASS else scenario

    if decision == PASS:
        reply_candidate = result.get("reply_candidate") if isinstance(result.get("reply_candidate"), dict) else {}
        body = _clean_text(reply_candidate.get("text") or "可以，我先提供候選回覆。")
        scenario = _classify_scenario(body)
        scenario_for_solution = scenario
        opener = PASS_OPENERS[_seed_index(channel_name, "PASS", risk_level, body, modulo=len(PASS_OPENERS))]
        closing = PASS_CLOSINGS[
            _seed_index(channel_name, "PASS", risk_level, body, modulo=len(PASS_CLOSINGS),)
        ]
        base_reply = f"{opener} {body} 目前沒有執行付款、寫入、部署或重啟。{closing}"
        reply_text, _concise_reply, _poetic_reply = _build_pass_text(base_reply, channel_name, scenario)
        requires_confirmation = False
    elif decision == BLOCK:
        opener = BLOCK_OPENERS[_seed_index(channel_name, "BLOCK", risk_level, "", modulo=len(BLOCK_OPENERS))]
        closing = BLOCK_CLOSINGS[
            _seed_index(channel_name, "BLOCK", risk_level, "", modulo=len(BLOCK_CLOSINGS))
        ]
        reply_text = f"{opener}這個請求目前不能繼續，我已停止候選流程，沒有執行任何正式動作。{closing}"
        requires_confirmation = True
    else:
        opener = HOLD_OPENERS[_seed_index(channel_name, "HOLD", risk_level, str(result), modulo=len(HOLD_OPENERS))]
        closing = HOLD_CLOSINGS[
            _seed_index(channel_name, "HOLD", risk_level, str(result), modulo=len(HOLD_CLOSINGS))
        ]
        reply_text = f"{opener}{_hold_text(result)}{closing}"
        requires_confirmation = risk_level != "LOW"

    reply_text = _clean_text(reply_text, limit=700)
    response_voice = _media_payload(decision, reply_text, risk_level)
    aesthetic = _literary_shape(
        decision,
        risk_level,
        channel_name,
        reply_text,
        scenario,
    )
    reply_variants = _build_reply_variants(
        decision,
        risk_level,
        channel_name,
        reply_text,
        reply_candidate.get("text", reply_text) if decision == PASS else reply_text,
        scenario,
    )

    response = {
        "state": "HUMAN_RESPONSE_RENDERED",
        "decision": decision,
        "risk_level": risk_level,
        "channel": channel_name,
        "reply_text": reply_text,
        "member_facing_message": reply_text,
        "requires_confirmation": requires_confirmation,
        "response_profiles": {
            "voice": _voice_profile(decision, risk_level, channel_name),
            "persona": _persona_traits(channel_name, decision),
            "selected": "default",
            "selected_variant": "default",
        },
        "response_variants": reply_variants,
        "required_member_confirmation": requires_confirmation,
        "agent_name": "小J",
        "role": "service_persona_language_layer",
        "persona_projection": projection,
        "service_context": service_context,
        "authority": "candidate_only",
        "scenario": scenario_for_solution,
        "solution_scenarios": _build_solution_scenario(decision, scenario_for_solution),
        "requires_total_field_verify": True,
        "intent_packet": {
            "requires_member_confirmation": requires_confirmation,
            "requires_total_field_verify": True,
        },
        "candidate_reply_only": True,
        "formal_send_executed": False,
        "line_reply_sent": False,
        "db_write": False,
        "odoo_write": False,
        "deploy": False,
        "restart": False,
        "persona_voice_hint": _persona_voice_hint(risk_level),
        "media_response": response_voice,
        "value_layer": _member_value_layer(decision, scenario),
        "action_pack": _action_draft_for_scenario(scenario, decision),
        "aesthetic": aesthetic,
        "redaction": {
            "raw_d_dimensions_exposed": False,
            "verifier_internals_exposed": False,
            "h64_td_exposed": False,
        },
    }
    return response


def main() -> int:
    sample = {"decision": PASS, "risk_level": "LOW", "reply_candidate": {"text": "可以，我先整理候選回覆。"}}
    print(json.dumps(render_human_response(sample), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
