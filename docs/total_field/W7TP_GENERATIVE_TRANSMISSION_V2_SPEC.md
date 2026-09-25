# W7TP Generative Transmission v2.0
## W7TP 生成式傳輸技術版本升級書

STATE=GT_V2_SPEC
VERSION=W7TP_GENERATIVE_TRANSMISSION_V2
ALL_NODE_IP6_CLOSED_LOOP=TRUE

## 1. 核心定義

傳輸 = 將來源端檔案、資料物件或狀態物件，在目的端重現，並經驗證確認一致性或狀態等價性。

生成式傳輸 = 來源端不必傳送完整原始資料，而是傳送足以使目的端重構該資料、狀態視圖或結果封包之 packet / ref / hash / manifest / lookup key / reconstruction rule，並由目的端生成對應狀態，再經 verifier 驗證。

T_GT_TRANSFER_COMPLETE = 目的端完成重構 + hash / manifest / verifier 驗證通過。  
T_GT_PACKET_READY = 來源端封包生成完成，不等於傳輸完成。

## 2. GT v1 / GT v2

GT_V1 = 封包化減量傳輸。  
GT_V2 = 目的端可驗證重構傳輸。

GT v2 不以 raw bytes 全量搬移為完成標準，而以目的端重構並驗證通過為完成標準。

## 3. 工程實測

低頻寬 P0 文件集測試：

RAW_FULL_TRANSFER_BYTES=17863  
GT_PACKET_TRANSFER_BYTES=557  
reduction_ratio_x=32.07  
bandwidth_reduction_percent=96.8818  

雲端候選算力測試：

HTTP_STATUS=200  
CANDIDATE_SUMMARY=W7TP_CLOUD_CANDIDATE_OK  
candidate_only=true  
must_not_execute=true  
requires_total_field_verify=true  

## 4. 架構

SOURCE_OBJECT
→ CANONICALIZE / TRANSCODE
→ PACKETIZE
→ IPv6-GT / W7TP Transmission
→ DESTINATION_RECONSTRUCT
→ TOTAL_FIELD_VERIFY
→ RESULT_PACKET
→ SEAL
→ CAPABILITY_BORROW_LEDGER

## 5. 全節點 IPv6 閉環

ALL_NODE_IP6_CLOSED_LOOP=TRUE

所有節點必須有 IPv6 coordinate ref：

- TOTAL_FIELD_ROOT
- FIELD_GATEWAY_NODE
- FIELD_NODE_CONTAINER
- VPN_NODE_CONTAINER
- CLOUD_CANDIDATE_NODE
- GOOGLE_EPHEMERAL_COMPUTE_NODE
- STATIC_MODEL_NODE
- DEVICE_SURFACE_NODE

IPv6 僅為網路座標：

IPv6_ADDRESS != AUTHORITY  
IPv6_ADDRESS != IDENTITY  
IPv6_ADDRESS != FINAL_PERMISSION  
IPv6_ADDRESS == NETWORK_COORDINATE  

禁止公開真實 IPv6、真實 IP、node key、API key、private key、WHY_IT_RUNS、lookup table source。

## 6. IPv6-GT

IPv6 負責定位。  
VPN 容器負責隔離。  
W7TP 封包負責治理。  
生成式傳輸負責少量傳輸與重構。  
總場 verifier 負責准駁。  
seal 負責證據鏈。

IPv6-GT 只能傳 packet / ref / hash / manifest / projection / capability_ref / result_packet。  
不能傳 raw member data、secret、正式執行權或總場主權。

## 7. Google 免洗機規則

Google ephemeral compute node 可借能力封包，但不可保留總場權限。

可借：

- TASK_REF
- STATE_PROJECTION
- LOOKUP_KEY_HINT
- EVIDENCE_HASH
- POLICY_SCOPE
- CAPABILITY_REF
- FIELD_PROJECTION
- MEMBER_REF
- BENEFIT_REF
- OUTPUT_FORMAT
- VERIFIER_CONTRACT

不可借：

- 會員明文
- secret
- token
- private key
- 完整 lookup table
- WHY_IT_RUNS
- production DB permission
- POS final-write permission
- payment permission
- deploy permission
- final authority

雲端輸出必須為 CLOUD_CANDIDATE_RESULT_PACKET，且固定：

candidate_only=true  
must_not_execute=true  
requires_total_field_verify=true  
confidence_is_authority=false  

## 8. Capability Borrow Ledger

每次能力借用必須歸檔：

borrow_id  
ipv6_gt_session_ref  
source_node_ref  
target_node_ref  
source_ipv6_ref  
target_ipv6_ref  
borrower_type  
capability_ref  
input_packet_hash  
output_packet_hash  
allowed_scope  
forbidden_scope  
verifier_required  
verifier_result  
seal_ref  
ttl_seconds  
created_at  

歸檔不得包含 raw data、會員明文、secret、完整 lookup table 或 final authority。

## 9. 適用邊界

效果最佳：

文件包、大量 log、狀態快照、資料庫摘要、專利文件集、圖像辨識結果、影片事件封包、語音意圖封包、可由 manifest / hash / ref 重構的資料、已有共同基底的檔案。

效果有限：

完全隨機資料、已加密檔案、已壓縮且不可再推導的檔案、沒有共同基底的大型二進位、要求 byte-for-byte 完全一致的原始檔。

## 10. 專利公開版語言

本發明提供一種生成式傳輸方法，係將來源端檔案、資料物件或狀態物件轉換為封包、參照、雜湊、清單、查表鍵、能力參照或重構規則，使目的端不必接收完整原始資料，即可依該封包化表示重構對應之檔案、狀態視圖或結果封包，並經總場查表驗證器確認一致性或狀態等價性後產生封印資料。

本發明進一步提供一種全節點 IPv6 閉環生成式傳輸架構，使總場節點、分場節點、雲端臨時運算節點、VPN 節點容器及設備介面節點，均以 IPv6 座標參照進入 W7TP 封包治理網路；各節點不得因取得網路連線即取得資料權限或最終執行權限，而須依能力封包、狀態投影、TTL、nonce、風險旗標及總場驗證契約進行候選運算、結果回傳與封印歸檔。

## 11. 總場鐵律

先分層，後執行。  
先候選，後驗證。  
先封包，後傳輸。  
先總場准駁，後產品落地。  

Layer → Candidate → Packet → Transmission → Reconstruct → Verify → Seal → Archive

