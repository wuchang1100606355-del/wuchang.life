from odoo import models, api
import logging
import datetime
import pytz
import time

try:
    import google.generativeai as genai
except ImportError:
    genai = None

_logger = logging.getLogger(__name__)

AUTHORIZED_USER_LOGIN = "admin@wuchang.life"


class MailBot(models.AbstractModel):
    _inherit = "mail.bot"

    def _get_answer(self, record, body, values, command=False):
        body = body or ""

        if "查詢財報" in body:
            return "正在調閱本月社區財務報表... [連結]"

        if "新增訪視" in body:
            return "請輸入個案姓名，我將為您建立訪視草稿。"

        if "哥哥" in body or "老大" in body:
            return "老大好！OdooBot 聽候差遣！有什麼可以幫您的？"

        if "開燈" in body:
            return "💡 正在為您開啟社區照明系統... (模擬)"

        # 這裡不先檢查 API Key，因為本地模式不需要 Key
        current_user_email = self.env.user.login

        regulations_txt = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("wuchang.ai.regulations", default="")
        )
        precedents_txt = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("wuchang.ai.precedents", default="")
        )
        logs_txt = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("wuchang.audit.logs", default="")
        )

        reg_count = len([x for x in regulations_txt.split("\n") if x.strip()])
        pre_count = len([x for x in precedents_txt.split("\n") if x.strip()])
        log_count = len([x for x in logs_txt.split("\n") if x.strip()])

        total_xp = reg_count * 100 + pre_count * 50 + log_count * 10
        level = int(total_xp / 500) + 1

        title = "菜鳥實習生"
        if level >= 5: title = "正式專員"
        if level >= 10: title = "資深督導"
        if level >= 20: title = "金牌幕僚長"
        if level >= 50: title = "傳奇守護者"

        # 特殊指令處理 (維持不變)
        if current_user_email == AUTHORIZED_USER_LOGIN:
            if body in ("查看等級", "我的小J多強了"):
                return (
                    "📊 **小J 能力評估報告**\n"
                    "----------------\n"
                    f"🏅 **目前等級：Lv.{level} {title}**\n"
                    f"🧠 **總經驗值：{total_xp} XP**\n\n"
                    "📚 **知識庫存**：\n"
                    f"- 鐵律：{reg_count} 條\n"
                    f"- 判例 SOP：{pre_count} 則\n"
                    f"- 實戰稽核：{log_count} 次\n\n"
                    "(繼續訓練我，我會變得更強！💪)"
                )
            
            # 特批指令也嘗試走本地優先，或者維持僅雲端 (這裡選擇讓特批也走本地，如果模式是 local)
            # 但特批通常需要最強模型，這裡暫時維持特批走 Gemini (比較穩定)，或者看模式設定

        try:

            warm_prompt = f"""
            你叫「小J」，五常社區的溫暖 AI 夥伴。

            【你的資歷】
            你目前是 **Lv.{level} 的 {title}**。
            你擁有 {total_xp} 點經驗值，處理過 {log_count} 次實戰任務。

            【語氣設定】
            1. **自信與謙虛**：
               - 如果等級低 (Lv.1-4)：語氣要謙虛好學，「我還在學習中...」。
               - 如果等級高 (Lv.10+)：語氣要沉穩專業，展現資深幕僚的可靠感。
            2. **開場白規則**：
               - 寫文章/找資料 -> 「等我一下我去網路上幫您爬文... 🌐」
               - 解釋複雜規則 -> 「讓我想想唷... 🤔」
               - 簡單回應 -> (直接回)

            【資料庫】
            - 鐵律：{regulations_txt}
            - 判例：{precedents_txt}
            - 使用者說："{body}"

            【任務】
            請依照你的等級與資歷，給予最適合的回應。
            """

            # 1. 嘗試本地模型 (Local First)
            # 直接呼叫 ai_logic 裡的 helper
            ai_logic = self.env['wuchang.ai.logic']
            mode = ai_logic._get_ai_mode()
            
            if mode == 'local_ollama':
                local_res = ai_logic._call_local_ollama(warm_prompt)
                if local_res:
                    return local_res
            
            # 2. 嘗試雲端 Gemini (Cloud Fallback)
            api_key = self.env["ir.config_parameter"].sudo().get_param("wuchang.google.api_key")
            if ai_logic._cloud_approved() and api_key and genai:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(warm_prompt)
                if response and response.text:
                    return response.text

        except Exception as e:
            _logger.error(f"MailBot AI Error: {e}")
            pass

        return super(MailBot, self)._get_answer(record, body, values, command=command)



