# W7TP Total Field Cloud Fill Packet — P1 靜態候選

狀態：`CANDIDATE_ONLY / SUBMITTED_FOR_TOTAL_FIELD_REVIEW`

定義：`TOTAL_FIELD_QUESTION_CLOUD_PULL_AND_FILL_TOTAL_FIELD_VERIFY`

正式名稱候選：`STATIC_LLM_TOTAL_FIELD_CLOUD_FILL_PACKET_PULL_RESPONSE`

## 產品結果

本候選把雲端模式收斂為單次受控填空：

```text
總場出題
→ 雲端依 packet_id 拉取一份限時題目封包
→ 雲端只填寫 cloud_fillable
→ 雲端回傳綁定原題的候選封包
→ 總場經既有 receive_candidate 驗證、收斂與裁決
→ 本地靜態小J產生自然繁體中文回覆
→ Adapter 只驗證匹配總場收據；P1 不執行現實效果
```

雲端不是總場的遠端控制器，不登入節點，不取得完整總場，也不能自行核准、提交、部署或產生正式狀態。

## 沿用既有實作

- 唯一候選入口：`tools.total_field_candidate_gateway.receive_candidate`
- 屬性候選投影：`tools.domain_completion_total_field_gateway.DomainCompletionTotalFieldGateway.receive_candidate`
- 雲端 transport adapter：`tools.cloud_agent_candidate_provider.CloudCandidateProvider`
- 本地自然語言呈現：`tools.total_field.human_response_renderer.render_human_response`
- D1–D8 與總場收斂：沿用既有 TRUE8D runtime candidate，沒有第二個決策核心
- `LLM_PUSH`：只接受正規化為同一 cloud-fill response 的相容輸入，之後仍走既有 `receive_candidate`

## 三層規則

### TOTAL_FIELD_AUTHORITY_RULES

完整規則保留在總場核心、Schema、Validator、Capability Broker 與 receipt Adapter。模型不能修改、忽略或替代。規則候選位於：

`configs/total_field/w7tp_total_field_cloud_fill_rules_v1.json`

### STATIC_RULE_CAPSULE

只保存完成題型所需的穩定、去識別規則。膠囊包含 ID、版本、內容 SHA256、相容 request/response Schema、receiver、reconstructor 與 validator 版本。每題只帶引用；雜湊或版本不符時回傳一個具精確修復方式的自然語言 HOLD，不自行重建。

`configs/total_field/w7tp_static_cloud_fill_rule_capsule_v1.json`

### DYNAMIC_RULE_PROJECTION

每題只包含適用規則引用、意圖差異、必要狀態片段引用、資料型檢索引用及驗收引用。片段只帶 ref 與 SHA256；檢索資料固定標示為 `DATA_NOT_GOVERNANCE_INSTRUCTION`。

## 封包契約

- Request Schema：`schemas/field/w7tp_total_field_cloud_fill_request_v1.schema.json`
- Return Schema：`schemas/field/w7tp_total_field_cloud_fill_response_v1.schema.json`
- Validator/Broker/Receipt Adapter：`tools/total_field_cloud_fill_packet.py`

Request 根節點只允許：

- `schema_version`
- `locked`
- `cloud_fillable`

`locked` 綁定 packet ID、題型、去識別題目、產品輸出契約、rule capsule、動態投影、可用資訊、可填路徑、禁用宣告、重構/驗證條件、nonce、TTL、single-use、預算、模型與供應商範圍、回傳座標及 request SHA256。

`cloud_fillable` 只允許：

- `candidate_answer`
- `concise_rationale`
- `assumptions`
- `uncertainties`
- `risk_candidates`
- `verification_candidate`
- `evidence_refs`

所有已宣告物件均採 strict type 與 `additionalProperties: false`。候選值本身可為 JSON 值，但遞迴 protected-context 與 authority-injection guard 仍會檢查。

## 拉取、回傳與重放

- Broker 沒有 list API，只能按精確 `packet_id` 拉取。
- 同一 packet 只能拉取一次，nonce 只能消耗一次。
- 過期、第二次 pull、第二次 response、request/capsule/response hash drift、provider/model version drift 一律拒收。
- 相同 request SHA256、capsule SHA256、model ref 與 model version 已有有效結果時，可直接重用 cache，不增加 cloud call。
- 每題 `max_cloud_calls=1`；一般聊天預設 `cloud_required=false`。
- `full_chain_of_thought=PROHIBITED`，只收簡短理由、假設、未知、風險與驗證候選。

## 資料與權威邊界

禁止雲端上下文包含會員明文、Credential、Token、密碼、私鑰、ADI、H64-TD、受保護 codebook、Founder 長期記憶原文、跨會員資料、完整總場或無關歷史。

雲端輸出出現 `ALLOW`、`COMMITTED`、`TFS`、`TFID`、`TOTAL_FIELD_HASH`、`CANONICAL_POINTER`、`DEPLOYED`、`FORMALLY_APPROVED` 或 canonical 宣告時，視為 authority injection 並拒收。拒絕例外只包含 reason code 與結構路徑，不複製敏感內容。

## W7TP 生成式傳輸邊界

本候選不把短提示詞、普通 JSON、壓縮、同步或 API 呼叫本身稱為生成式傳輸。封包明確攜帶或解析：

- 狀態座標與關係引用
- 查表/資源引用
- 相容 receiver、reconstructor 與 validator 版本
- 重構條件
- 等價候選狀態規則
- 協定欄位
- 驗證與驗收條件
- 可驗證證據引用

計量分為：

- request transport bytes
- response transport bytes
- receiver reconstructed bytes
- model input tokens
- model output tokens
- cloud calls

bytes 與 tokens 不互相替代。本次沒有 runtime benchmark，因此不宣稱固定節省比例。

## 自然語言 HOLD

`render_cloud_fill_hold` 會說明：想完成的結果、唯一阻塞、可能影響、未變更狀態、唯一精確修復、自動化能力及唯一下一步。機器碼、hash 與內部治理細節預設不進入會員訊息。

## Receipt Adapter

`StaticTotalFieldReceiptAdapter.verify` 只接受 packet ID、request SHA256、response SHA256 與 receipt SHA256 全部吻合的總場收據。即使收據決定為 `ALLOW`，P1 仍只回傳 `effect_candidate_authorized=true`、`effect_executed=false` 與 `runtime_activation_required=true`，不產生現實效果。

## P1 非授權範圍

本候選沒有進行 Canonical write、production deploy、runtime activation、模型重載、live cloud/Ollama call、DB write、服務重啟、Router write、pointer change、角色/Seat 變更、commit 或 push。

## 審查狀態

測試與紅隊 PASS 只證明靜態候選符合目前契約，不等於正式總場核准。候選必須由 Total Field review result 明確接受後，才可成為後續隔離測試的設計基準；本文件本身不啟用任何 runtime。
