# W7TP／8D ADI V2.3｜原胞已驗證重構快路徑候選

狀態：CANDIDATE_NOT_CANONICAL

## 承接既有總場

本候選不重造 Origin-Cell GST。直接綁定既有：

- `runtime/total_field/conversation_intake/universal_origin_cell_codec_v2.py`
- 錨定 SHA-256：`345af4963feb2fd88c684a96c505aafae63ad46c2c16e5c4dd13722eb3c7a23b`
- `services/w7tp_state_hash.py` 的 canonical hashing（正規化雜湊）
- 現有 Total Field（總場）D8 權威鏈維持分離

## 本輪把討論轉成的程式能力

### 1. Reconstruction Key（重構鍵）

相同：

- source state digest（來源狀態摘要）
- source size（來源大小）
- Origin-Cell packet（原胞封包）
- codec SHA-256
- executor contract（執行器契約）
- base cache digest（基座快取摘要）
- namespace（命名空間）
- reconstruction contract（重構契約）
- route ref（路由引用）

必須得到相同重構鍵。

節點、時間、D4 本次收據、D8 當次授權不進入重構鍵，因此 A→B 與重播可以共用同一邏輯重構身分。

### 2. Verified Reconstruction Trust Seal（已驗證重構信任標章）

首次完整 byte-exact（位元組完全一致）驗證通過後，可形成一筆可重用的 D4 證據候選。

它明確：

- 不等於 D8 權威
- 不授權部署／執行／交易
- `Reconstructed != Executed`
- 新的外部效果仍須當次 D8

### 3. Deterministic Fast Path（確定性快路徑）

已存在相同重構鍵的有效標章時：

`lookup → decode → digest compare → PASS`

不需要模型重新分析、不需要重新判斷拆解方式、不需要完整語義驗證。

只要 packet、source、base、route 或 contract 任一漂移，就回：

`HOLD_FULL_VERIFICATION_REQUIRED`

### 4. Model Integration Reasoning Candidate（模型整合推理候選）

模型只允許提出：

- SAME_STATE
- SUPPLEMENTS
- VERSION_SUCCESSOR
- CONFLICTS
- DEPENDS_ON
- PARENT_OF
- CHILD_OF
- OBSERVES_SAME_EVENT

等資訊關係候選。

模型不得在候選中夾帶 authority、execute、shell、deploy、restart、write、signature 等效果／權威欄位。

模型輸出固定：

`CANDIDATE_ONLY`

後續必須編譯成既有受限 Origin-Cell opcode（操作碼）集合，再做確定性重構與 D4 驗證。

## 8D ADI 對應

- D1：本次意圖＝將已討論之「已知狀態快路徑」形成可執行候選
- D2：CANDIDATE_NOT_CANONICAL；11/11 隔離測試 PASS
- D3：taiji01；既有主線與精確 codec SHA 綁定
- D4：byte-exact + SHA-256 + unittest
- D5：只建立隔離候選；不部署、不修改 codec、不啟用服務
- D6：沿既有 Origin-Cell GST V2.1 packet／rule decoder
- D7：任何身分、規則、封包、基座漂移 fail-closed
- D8：Trust Seal 只屬 D4 重用證據；外部效果仍需當次 Total Field 權威

## 執行測試

```bash
cd /home/taiji_admin/Taiji_Hub/artifacts/8d-adi-workloop/origin-cell-verified-reconstruction-candidate-20261023T233100Z8
python3 -m unittest discover -s tests -v
```

目前結果：11/11 PASS。
