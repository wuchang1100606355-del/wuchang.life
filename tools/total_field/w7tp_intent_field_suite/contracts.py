"""Non-authoritative field-completion contracts for the five shared profiles."""

from __future__ import annotations

from dataclasses import dataclass

from tools.total_field.w7tp_field_application_runtime import FieldApplicationError


@dataclass(frozen=True)
class QuestionContract:
    field: str
    question_id: str
    prompt: str
    reason: str
    options: tuple[str, ...]


@dataclass(frozen=True)
class ProfileContract:
    profile: str
    packet_type: str
    questions: tuple[QuestionContract, ...]


def _q(field: str, profile: str, prompt: str, reason: str, *options: str) -> QuestionContract:
    return QuestionContract(field, f"{profile.casefold()}.{field}", prompt, reason, tuple(options))


CONTRACTS = {
    "ASSOCIATION": ProfileContract(
        "ASSOCIATION",
        "ASSOCIATION_SERVICE_PACKET",
        (
            _q("service_goal", "ASSOCIATION", "這次社區服務希望達成什麼目標？", "建立服務候選所需的最小目標。", "活動規劃", "資訊公告", "志工協作"),
            _q("activity_type", "ASSOCIATION", "請選擇活動類型。", "確認安全的服務場景。", "社區活動", "教育課程", "關懷服務"),
            _q("time_range", "ASSOCIATION", "希望處理的時間範圍是？", "建立不含個資的時間限制。", "本週", "本月", "自訂期間"),
            _q("audience_category", "ASSOCIATION", "服務對象的非識別化分類是？", "只使用群體分類，不收集姓名。", "一般居民", "志工", "高齡友善對象"),
        ),
    ),
    "PROPERTY": ProfileContract(
        "PROPERTY",
        "PROPERTY_SERVICE_PACKET",
        (
            _q("device_anonymous_id", "PROPERTY", "請提供設備匿名代碼。", "定位設備但不詢問住戶姓名。", "公共設備-A", "公共設備-B"),
            _q("inspection_scope", "PROPERTY", "本次檢查範圍是？", "限定候選檢查邊界。", "外觀", "運轉狀態", "安全項目"),
            _q("risk_level", "PROPERTY", "目前風險等級是？", "決定候選的風險提示。", "低", "中", "高"),
        ),
    ),
    "CAFE_POS": ProfileContract(
        "CAFE_POS",
        "CAFE_POS_SERVICE_PACKET",
        (
            _q("product_candidate", "CAFE_POS", "要建立哪一個商品候選？", "只建立商品候選，不下單或收款。", "飲品候選", "餐點候選", "其他商品候選"),
            _q("category", "CAFE_POS", "商品候選分類是？", "建立一致的分類候選。", "咖啡", "非咖啡飲品", "餐食"),
            _q("price_candidate", "CAFE_POS", "請提供價格候選。", "價格僅供候選預覽，不執行交易。", "待確認", "依現有價目", "自訂候選"),
        ),
    ),
    "HOUSEHOLD": ProfileContract(
        "HOUSEHOLD",
        "HOUSEHOLD_SERVICE_PACKET",
        (
            _q("reminder_content", "HOUSEHOLD", "需要提醒什麼事項？", "建立不含家庭成員明文的提醒候選。", "日常事項", "健康關懷", "家庭行程"),
            _q("reminder_time", "HOUSEHOLD", "希望何時提醒？", "建立提醒時間條件。", "今天", "明天", "自訂時間"),
            _q("anonymous_role", "HOUSEHOLD", "提醒對象的匿名角色是？", "只保存匿名角色，不保存姓名。", "本人", "家人角色-A", "照顧角色"),
        ),
    ),
    "GENERIC": ProfileContract(
        "GENERIC",
        "GENERIC_INTENT_PACKET",
        (
            _q("requested_result", "GENERIC", "你希望得到什麼結果？", "明確定義 D1 requested result。", "分析候選", "內容候選", "流程候選"),
            _q("constraints", "GENERIC", "這個結果必須遵守哪些限制？", "建立可驗證的執行邊界。", "只讀", "本機處理", "候選輸出"),
            _q("evidence_refs", "GENERIC", "可引用的證據來源是？", "總場只接受有來源的候選。", "repo 正典", "既有 PASS 紀錄", "使用者提供資料"),
        ),
    ),
}


def get_contract(profile: str) -> ProfileContract:
    contract = CONTRACTS.get(profile)
    if contract is None:
        raise FieldApplicationError("SCENARIO_NOT_REGISTERED")
    return contract
