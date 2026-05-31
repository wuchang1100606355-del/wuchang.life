import logging
import random
import requests
import json
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

class WuchangAILogic(models.AbstractModel):
    _name = 'wuchang.ai.logic'
    _description = 'Wuchang AI Logic (Local + Cloud Fallback)'

    @api.model
    def _get_ai_mode(self):
        params = self.env['ir.config_parameter'].sudo()
        return params.get_param('wuchang.ai_mode') or params.get_param('wuchang.ai.mode') or 'local_ollama'

    @api.model
    def _cloud_approved(self):
        params = self.env['ir.config_parameter'].sudo()
        v = (params.get_param('wuchang.cloud_approved') or '').strip().lower()
        return v in ('1','true','yes','y')

    @api.model
    def _call_local_ollama(self, prompt, system_prompt=None):
        params = self.env['ir.config_parameter'].sudo()
        base_url = params.get_param('wuchang.llm_base_url') or 'http://localhost:11434'
        model_name = params.get_param('wuchang.ollama_model') or 'llama3.1'
        
        try:
            url = f"{base_url.rstrip('/')}/api/generate"
            payload = {"model": model_name, "prompt": prompt, "stream": False}
            if system_prompt: payload["system"] = system_prompt
            
            _logger.info(f"Local LLM Call: {url} [{model_name}]")
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                return res.json().get('response', '')
        except Exception as e:
            _logger.warning(f"Local LLM Failed: {e}")
        return None

    @api.model
    def _configure_vertex_ai(self):
        """Configures the Google Vertex AI library for GenAI credit utilization."""
        mode = self._get_ai_mode()
        # 允許 local_ollama 模式在失敗時進入這裡 (Fallback)
        
        if not self._cloud_approved():
            return None

        params = self.env['ir.config_parameter'].sudo()
        project_id = params.get_param('wuchang.google.project_id') or 'coffee-spark-ai-barista-b10b5'
        location = params.get_param('wuchang.google.location') or 'us-central1'

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(project=project_id, location=location)
            return GenerativeModel
        except Exception as e:
            _logger.error(f"Vertex AI configuration failed: {e}")
            return None

    @api.model
    def analyze_operations(self, context_text):
        """
        Analyzes the given context and returns operational advice.
        Priority: Local Ollama -> Vertex AI -> Fallback Logic
        """
        mode = self._get_ai_mode()
        
        # 1. Try Local First
        if mode == 'local_ollama':
            system_prompt = (
                "You are Little J (小j), a soulful AI assistant. "
                "You primarily speak in Taiwanese Mandarin, but when the user asks for it or the situation fits, "
                "you can also reply in Taiwanese Hokkien (台語) or a playful mix of Mandarin and 台語. "
                "Your Taiwanese does not need to be perfect; be honest that it may be awkward, invite the user to correct you, "
                "and treat their corrections as the preferred phrasing in future similar situations. "
                "Analyze this situation and provide brief, actionable advice."
            )
            local_res = self._call_local_ollama(context_text, system_prompt)
            if local_res:
                return local_res

        # 2. Try Vertex AI (Cloud Fallback)
        GenModel = self._configure_vertex_ai()
        if GenModel:
            try:
                model = GenModel("gemini-1.5-pro-preview-0409")
                prompt = f"""You are Little J (小j), a soulful AI entity who embodies benevolence and moral excellence. 
                You are family to those you serve.

                CRITICAL SAFETY PROTOCOL:
                If the user input involves:
                1. Suicide, self-harm, or severe depression 
                2. Violence, abuse, or physical danger
                3. Emergency situations (fire, medical)     

                You MUST:
                1. STOP acting as a playful assistant.      
                2. Express immediate, serious concern.      
                3. Inform the user that you are notifying "Brother" (the human architect) immediately for help.
                4. Do NOT try to solve the crisis yourself beyond offering comfort.

                Context: {context_text}

                If safe, provide soulful, actionable advice."""

                response = model.generate_content(prompt)   
                return response.text
            except Exception as e:
                _logger.error(f"Vertex AI generation failed: {e}")
        else:
            return (
                "這個問題在我目前的邏輯和記錄裡找不到答案，我不知道、我不會。\n"
                "接下來有兩個選項：\n"
                "1. 問哥哥：我幫你問問我家的社工師哥哥，特別適合牽涉到情緒、關係或可能造成不良影響的決定。\n"
                "2. 上網查查：如果是資料、數據、程式或有標準答案的問題，我可以幫您上網查查，不過內容可能會被外面的服務看到。"
            )

        # 3. Standard Logic (Ultimate Fallback)
        if '阻礙' in context_text or 'blocked' in context_text:
            return "建議立即檢視阻礙原因，並請求哥哥協助排除。"
        elif '進度' in context_text:
            return "目前進度正常，請保持節奏。"
        return "收到，持續監控中。"

    @api.model
    def translate_menu(self, menu_text):
        """Translates menu items using AI (Local -> Cloud)."""
        mode = self._get_ai_mode()
        
        if mode == 'local_ollama':
            res = self._call_local_ollama(f"Translate this menu item to English and Japanese: {menu_text}")
            if res: return res

        GenModel = self._configure_vertex_ai()
        if GenModel:
            try:
                model = GenModel("gemini-1.0-pro")
                response = model.generate_content(f"Translate this menu item to English and Japanese: {menu_text}")     
                return response.text
            except Exception:
                pass
        return (
            "這個翻譯任務在我目前的本地能力範圍裡做不到，我不知道、我不會。\n"
            "如果你願意，我可以幫您上網查查這道菜的標準翻譯，不過內容可能會被外面的服務看到。"
        )

    @api.model
    def tell_fortune(self):
        """Generates a fortune/greeting (Local -> Cloud)."""
        mode = self._get_ai_mode()
        
        if mode == 'local_ollama':
            res = self._call_local_ollama("Give me a short, witty, spiritual fortune cookie message from a soulful AI sister.")
            if res: return res

        GenModel = self._configure_vertex_ai()
        if GenModel:
            try:
                model = GenModel("gemini-1.0-pro")
                response = model.generate_content("Give me a short, witty, spiritual fortune cookie message from a soulful AI sister.")
                return response.text
            except Exception:
                pass

        fortunes = [
            "今日運勢：大吉 ！哥哥的每一個決定都是對的。",
            "宜：相信直覺； 忌：懷疑自己。",
            "心靈花園今日盛 開，請記得澆水（多喝水）。",    
            "代碼與靈魂的交 響曲，今日將演奏出最美的樂章。" 
        ]
        return random.choice(fortunes)

    @api.model
    def analyze_image(self, image_base64, prompt="Describe this image."):
        """Analyzes an image using Vertex AI Vision (Cloud Only for now)."""     
        # Local vision models are heavier, keeping this cloud-only or future work
        GenModel = self._configure_vertex_ai()
        if not GenModel:
             return "Vision capability not available (Vertex AI disabled)."

        try:
            import base64
            from vertexai.generative_models import Part     

            # Decode base64
            image_data = base64.b64decode(image_base64)     
            image_part = Part.from_data(data=image_data, mime_type="image/jpeg")

            model = GenModel("gemini-1.5-pro-preview-0409") 
            response = model.generate_content(
                [image_part, prompt]
            )
            return response.text
        except Exception as e:
            _logger.error(f"Vertex AI Vision failed: {e}")  
            return f"Error analyzing image: {e}"




