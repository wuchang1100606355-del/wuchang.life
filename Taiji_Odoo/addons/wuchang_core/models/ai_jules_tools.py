# -*- coding: utf-8 -*-
from vertexai.preview import function_calling

# ==========================
# 住戶查詢類
# ==========================
get_resident_status_func = function_calling.FunctionDeclaration(
    name="get_resident_status",
    description="查詢住戶的綜合狀態，包含幸福幣餘額、管理費是否繳納、是否有待領包裹。",
    parameters={
        "type": "object",
        "properties": {
            "user_unit": {
                "type": "string",
                "description": "住戶的門牌號碼 (例如: '3F-2')"
            }
        },
        "required": ["user_unit"]
    }
)

# ==========================
# 幸福市集 (公益/新創)
# ==========================
list_charity_services_func = function_calling.FunctionDeclaration(
    name="list_charity_services",
    description="列出目前社區合作的新創服務或公益商品 (如洗冷氣、愛心待用餐)，並顯示其價格與幸福幣回饋。",
    parameters={
        "type": "object",
        "properties": {},
    }
)

book_charity_service_func = function_calling.FunctionDeclaration(
    name="book_charity_service",
    description="為住戶預約服務或認購愛心待用餐。交易成功後會回傳獲得的幸福幣數量。",
    parameters={
        "type": "object",
        "properties": {
            "user_unit": {
                "type": "string",
                "description": "住戶門牌"
            },
            "service_id": {
                "type": "string",
                "description": "服務或商品的ID (例如 's1')"
            }
        },
        "required": ["user_unit", "service_id"]
    }
)

# ==========================
# 許願樹系統
# ==========================
list_wishes_func = function_calling.FunctionDeclaration(
    name="list_wishes",
    description="列出目前許願樹上正在集氣或審核中的提案，包含目前票數與目標票數。",
    parameters={
        "type": "object",
        "properties": {},
    }
)

vote_wish_func = function_calling.FunctionDeclaration(
    name="vote_wish",
    description="住戶使用幸福幣對特定願望進行投票 (灌溉)。",
    parameters={
        "type": "object",
        "properties": {
            "user_unit": {
                "type": "string",
                "description": "住戶門牌"
            },
            "wish_id": {
                "type": "string",
                "description": "願望ID (例如 'w1')"
            },
            "coins": {
                "type": "integer",
                "description": "投入的幸福幣數量 (預設為 10)",
                "default": 10
            }
        },
        "required": ["user_unit", "wish_id"]
    }
)

create_wish_func = function_calling.FunctionDeclaration(
    name="create_wish",
    description="住戶消耗幸福幣提出一個新的社區願望。",
    parameters={
        "type": "object",
        "properties": {
            "user_unit": { "type": "string" },
            "title": { "type": "string", "description": "願望標題" },
            "description": { "type": "string", "description": "詳細說明" }
        },
        "required": ["user_unit", "title", "description"]
    }
)

# --- 彙整所有工具 ---
wuchang_ecosystem_tools = function_calling.Tool(
    function_declarations=[
        get_resident_status_func,
        list_charity_services_func,
        book_charity_service_func,
        list_wishes_func,
        vote_wish_func,
        create_wish_func
    ]
)
