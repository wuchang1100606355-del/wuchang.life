# 五常指揮官專用虛擬環境

狀態：COMMANDER_VENV_ONLY

用途：
- 指揮官健康檢查
- 七維 Gateway 對接
- Open WebUI / Odoo / Ollama / Claw 狀態整合
- 影音 AI 前台後續接入

硬牆：
- 不存 secret
- 不 kill process
- 不 auto-start
- 不直接改 Odoo DB
- 不直接執行高權限命令
