# TOTAL_FIELD_VERIFIER_CONTRACT_V1

## 1. 驗證器定位
總場查表驗證器 (Total Field Verifier) 是系統的最終決策防線。AI 產出的候選結果 (Candidate) 必須通過此合約的查表與檢驗，才能被准駁、重構或封印。

## 2. 驗證觸發條件與硬限制 (Hard Walls)
當收到 `Cloud_Candidate_Result` 或 `Edge_Candidate_Result` 時，Verifier 將執行以下攔截邏輯：
- **[D8 封套檢查]**: 驗證 `ttl_sec` 是否過期、`nonce` 是否重放 (Replay)、`packet_hash` 是否完整。
- **[D5 邊界檢查]**: 確認候選結果未企圖違反 `forbidden_ops` (如：禁止讀取 `member_plaintext`、禁止直接執行 `payment_capture`)。
- **[D7 風險檢查]**: 若觸發 `redteam_required: true`，強制攔截轉入隔離區。
- **[D4 證據核對]**: 檢核 `evidence_refs` (如 `image_hash`) 是否存在於信任清單 (Trusted Registry) 中。

## 3. 狀態機輸出 (State Machine Outputs)
Verifier 的輸出狀態僅限以下五種：
1. **ACCEPTED**: 驗證完全通過，簽發 `seal_ref`，允許發布結果封包。
2. **REJECTED**: 條件不符，直接駁回，不留存執行。
3. **HOLD**: 觸發安全閾值，需人工或高權限節點介入 (Human-in-the-loop)。
4. **REDTEAM**: 發現越權企圖或惡意 prompt，導入紅隊資料庫進行微調標記。
5. **DEAD_LETTER**: 封包破損或格式錯誤，直接丟棄並記錄。
