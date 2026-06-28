# W7TP Non-Confidential Invention Brief V1

## 核心發明名稱
一種用於人工智慧候選運算治理之意圖狀態封包資料庫、查表驗證方法及系統

## 解決之痛點
解決傳統 AI (LLM/多模態) 權限過大、自然語言長上下文傳輸導致頻寬浪費，以及 AI 幻覺直接寫入正式系統之風險。

## 創新技術特徵
1. **AI 降級與權限分離**: AI 僅作為候選草稿產生器 (Candidate Generator)，無正式執行權限。
2. **8D 意圖狀態封包 (8D Intent-State Packet)**: 將操作收斂為包含意圖、狀態、證據、執行邊界、風險與封套等 8 個維度之資料結構。
3. **總場查表驗證 (Total Field Verifier)**: 透過嚴格查表與封套驗證 (TTL/Nonce/Hash) 決定結果之准駁與封印。
4. **全程生成式傳輸 (Generative Transmission)**: 跨網際網路或邊緣節點僅傳輸 Ref、Hash 與狀態投影，不傳輸原始大檔或會員明文。

## 營業秘密保留聲明
本文件不包含、且專利請求範圍亦不應揭露以下實作細節：
- 核心查表映射邏輯 (WHY_IT_RUNS)
- 古數學向量生成規則與 Five-Element Tensor 實際映射
- 會員 PII 與正式 Odoo/POS 寫入路由密碼
