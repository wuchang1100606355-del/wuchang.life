【五常智慧雲｜動態 QR 載入資訊與範圍化語音服務條款】

動態 QR 是短效、可撤銷、可稽核的資訊載入入口；它載入的是服務範圍與權益片段，不是會員完整明文。

Dynamic_QR(q)=true

iff:

Short_Lived=true
AND One_Time_or_Limited_Use=true
AND Revocable=true
AND Payload_Minimized=true
AND No_Plaintext_Identity=true
AND Gateway_Audited=true
AND Meter_User_Rule=true
AND Expiry_Defined=true

允許載入：
qr_session_id、voice_service_token、object_token、member_token 或 entity_token、五維碼權益片段、票券庫狀態、手機末 4 碼驗證狀態、年齡層、性別範圍、服務類型、公益服務資格狀態、Odoo 權益檔案索引、是否需人工轉接、到期時間、request_id、sha256_hash。

不得載入：
完整姓名、完整手機、完整身分證字號、完整生日、完整住址、住戶門牌、私人 Email、LINE ID、會員名冊明文、完整票券金流明細、Odoo 內部備註、AI 海馬迴可重組明文分片、OAuth token、API key、service account key。

語音服務流程：
掃描動態 QR → 載入 qr_session_id → Taiji Gateway 查詢 Odoo 權益片段 → AI 取得範圍化資料 → 使用者提供手機末 4 碼 → 低風險服務由 AI 提示 → 高風險轉人工或二次驗證。

Final Principle:
動態 QR 用來載入服務範圍，不用來暴露自然人完整身分。
AI 語音服務只取得必要的權益片段、票券狀態、手機末 4 碼驗證結果與服務範圍。
完整會員明文仍由我方統管，採物理封存與可究責程序。
