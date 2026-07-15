# TFCT／TRUE8D Runtime Candidate V0.1 實作報告

RUN_ID=`TFCT_TRUE8D_RUNTIME_CANDIDATE_V0_1`
STATUS=`CANDIDATE_NON_CANONICAL`
CONSENSUS_MODE=LOCAL_EQUIVALENCE_ONLY
DISTRIBUTED_CONSENSUS=OPEN_PROBLEM
PATENT_CANDIDATE_REVIEW_REQUIRED=YES

## 1. 實作摘要

本次建立一條無網路、無資料庫、無部署副作用的候選 Runtime。它接受封閉的 8D-GTE Runtime Request，以呼叫端提供的 Event、logical time、Observation Domain、rule set 與 previous state 執行確定性收斂，再由 D8 候選裁決產生 ALLOW、HOLD、BLOCK 或 QUARANTINE。只有固定點 `REACHED` 且最終裁決為 `ALLOW` 才能提交 proposed；其餘狀態一律以 previous 作為 committed。

本實作沒有修改 Active Canonical、Pointer、既有 D3 engine、packet runtime 或 legacy `tensor_8d`。全部規則、識別與 schema 都明確標記為 candidate。

## 2. 程式模組對照

| 模組 | 候選責任 |
|---|---|
| `tools/tfct_true8d_runtime_candidate.py` | frozen 資料模型、Constraint Hypergraph、Priority Policy、有限步收斂、D8、TFS、TFID、Total Field Hash、本地等價比對 |
| `tools/eightd_gte_parser_candidate.py` | dict／UTF-8 JSON 解析、duplicate/NaN/Infinity/extra-field 拒絕、Draft 2020-12 驗證與 candidate hash |
| `tools/total_field_candidate_gateway.py` | `TOTAL_FIELD_PULL` 與 `LLM_PUSH` 的唯一共同 `receive_candidate` 入口 |
| `tools/w7tp_small_transport_agent_candidate.py` | capability manifest、版本協商、reference resolution、重構與等價驗證 request、gateway client、commit guard |
| `tools/xiaoj_candidate_adapter.py` | provider-neutral/in-memory candidate、persona 與 governance 隔離、pull/push 轉譯 |
| `tools/adi_index_strategy_candidate.py` | Disabled ADI fallback 與 deterministic test-only fixture strategy |
| `runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json` | 候選規則、constraint order、決策優先序、hard-risk、fallback 與 open-problem gates |
| `schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json` | 引用既有 8D-GTE schema 的封閉 request/result profile |
| `tests/fixtures/tfct_true8d_runtime_candidate_vectors.json` | 固定、可重放、無秘密的測試向量 |
| `tests/test_tfct_true8d_runtime_candidate.py` | 45 個具名 focused conformance tests |
| `scripts/verify/verify_tfct_true8d_runtime_candidate.py` | 新檔完整性、語義、禁用 API、保護基線與 focused test verifier |

## 3. Theory → Mathematics → Engineering 映射

| Theory 概念 | Mathematics 形式 | Runtime Candidate 實作 |
|---|---|---|
| Event | caller-supplied event identity | frozen `Event`；不修正 event，不產生動態時間 |
| Observation | opaque Observation Domain | frozen `ObservationDomain`；未配置時可執行 HOLD |
| Projection | dimension projection | D1–D8 closed state；GTE dimension refs 與 policy registry 精確比對；D3 委派既有 transition engine |
| Field | eight-field state | frozen `EightFieldState`，輸入全數深複製 |
| Constraint Hypergraph | ordered hyperedges | registry order 10/20/30/40/50 的五個明確 evaluator |
| Priority Policy | restrictive ordering | `QUARANTINE > BLOCK > HOLD > ALLOW` |
| finite fixed-point search | fingerprint sequence | SHA-256 state fingerprint、fixed/cycle/max-iteration 判定 |
| Total Field State | committed state identity | `TFS`、state ref、TFID、Total Field Hash |
| cross-node equivalence | deterministic equality relation | canonical state、TFID、Total Field Hash 與 difference paths |

這些是候選工程操作，不構成固定點存在性、唯一性、全域有限收斂或分散式一致性的數學證明。

## 4. Candidate／Canonical 邊界

作用中維度語義維持：

- D6 = Sovereign Privacy Field
- D7 = Generative Transmission & Resource Routing Field
- D8 = Red-Team Detour Alert & Quarantine Field

D6 對合併後 current/proposed state 與 context 檢查敏感 key 及明示 hard-risk code，避免 previous state 中既存敏感內容繞過 gate。D7 只接受狀態場封包 reference、rule/table/template/asset/routing reference、查表與 reconstruction condition；任何層級的 raw payload 都只回 `RAW_CHANNEL_REQUIRED`。生成式傳輸維持 protocol-native 8D intent-field packet、引用、查表、重構條件、等價狀態生成與總場驗證的定義，不被轉寫成檔案搬運、同步、備份、下載或解密。

D8 是裁決狀態機；transition hash、packet hash、TFID 與 Total Field Hash 都只屬驗證證據，不能取代 D8。Legacy `D6_gt`、`D7_risk`、`D8_envelope` 只允許由既有 compatibility adapter 明示讀取，沒有被直接等同 Active D6/D7/D8。

## 5. D3 既有引擎接入方式

Runtime 直接匯入既有 `transition_coordinate()` 與 `verify_transition_record()`，沒有第二套 D3 engine。previous D3 與候選 coordinate delta 交由該 engine 產生 pure coordinate proposal。Runtime 使用 `proposed` 作為總場收斂輸入，並將 `transition_hash`、`event_id`、`logical_time`、`commit_applied`、`final_decision`、reason 與驗證結果放在 D4 evidence 及 result metadata。

D3 body 只保留 coordinate data；D8 decision 沒有寫入 D3 body。既有 `D3_coordinate` shape、packet runtime 與 replay integration 均未修改。

## 6. 8D-GTE 解析流程

1. 接受 caller-owned dict 或 UTF-8 JSON file。
2. 拒絕 duplicate member、NaN、Infinity、非 JSON-compatible value 與 cyclic container。
3. 深複製後以 Draft 2020-12 base schema 驗證封閉欄位、D1–D8 refs 與 lifecycle。
4. 明確拒絕 Candidate commit/ALLOW/TFS 與不完整 Committed lifecycle。
5. 使用固定 canonical JSON 產生 canonical payload 與 SHA-256 candidate hash。
6. 只解析資料，不執行 candidate 內容，也不提供可執行 DSL。

Runtime profile 的 `gte` 透過既有 schema `$id` 引用基礎契約；request 與 result 分別為 closed `RUNTIME_REQUEST` 與 `RUNTIME_RESULT`。

## 7. Convergence 演算法

1. 驗證並深複製 previous、candidate、event、domain、context 與 policy。
2. 透過唯一既有 D3 engine 建立 D3 proposal 與獨立 metadata。
3. 從 registry 取得一個明確且版本化的 operation；不做動態函數載入。
4. 每輪套用 operation，對完整 D1–D8 state 計算 canonical SHA-256 fingerprint。
5. 依固定順序執行全部 hyperedges，再以優先序裁決 D8。
6. fingerprint 與前輪相同：constraint 全 PASS 則 `REACHED/ALLOW`；否則回非 ALLOW 並保存 previous。
7. fingerprint 曾出現：`CYCLE_DETECTED/HOLD/CONVERGENCE_CYCLE_DETECTED`。
8. 達候選 `max_iterations`：`MAX_ITERATIONS_REACHED/HOLD/CONVERGENCE_TIMEOUT`。

`max_iterations` 是 candidate implementation parameter，不是收斂定理。

## 8. Constraint Hypergraph 與 D8

固定 hyperedge 順序如下：

1. required-fields
2. external authority guard
3. D6 sovereign privacy／hard-risk
4. D7 reference-only／raw-channel guard
5. open-problem gate

Candidate source、LLM、小J與 Small Agent 都沒有 ALLOW authority。候選若提供 committed、TFID、Total Field Hash、`commit_applied=true` 或 `final_decision=ALLOW`，gateway 或 authority guard 會穩定拒絕。Observation Domain、rule set、priority policy、ADI 或 distributed consensus 未配置時，都有可執行 HOLD reason code。

Gateway 另將 GTE 的 D1–D8 projection refs、Constraint Hypergraph ref 與 Convergence Operator ref 精確比對 candidate policy registry。未知 ref 不會被默認接受，而是分別回 `HOLD_DIMENSION_PROJECTION_NOT_CONFIGURED`、`HOLD_CONSTRAINT_HYPERGRAPH_NOT_CONFIGURED` 或 `HOLD_CONVERGENCE_OPERATOR_NOT_CONFIGURED`。

## 9. TFID／Total Field Hash 候選契約

TFID 固定為：

`tfid:candidate:v0.1:` + `SHA256(canonical committed D1–D8 state)`

TFID 與 transition hash、packet hash 分離。Total Field Hash 綁定：schema version、event ref、Observation Domain ref、rule set ref、priority policy ref、previous、proposed、committed、fixed-point status、final decision、reason codes、commit flag 與 TFID。兩者都不包含現在時間、隨機值、process id、hostname 或未版本化外部狀態。

## 10. 跨節點等價邊界

`compare_tfs_equivalence()` 只比較 Node A/Node B 的 canonical committed state、TFID 與 Total Field Hash，輸出 `MATCH`／`MISMATCH` 及穩定 difference paths。

CONSENSUS_MODE=LOCAL_EQUIVALENCE_ONLY
DISTRIBUTED_CONSENSUS=OPEN_PROBLEM

本次沒有模擬或宣稱 distributed consensus protocol。

## 11. W7TP Small Transport Agent

Small Agent 僅攜帶 manifest、版本、rule/reconstructor/asset/lookup/routing references、reconstruction conditions 與 equivalence request。它支援 L1/L2/L3 packet-native reconstruction level，並以 `MISSING_ASSET`、`UNSUPPORTED_RULE`、`UNSUPPORTED_RECONSTRUCTOR`、`VERSION_MISMATCH`、`RAW_CHANNEL_REQUIRED`、HOLD 或 BLOCK 回傳安全結果。

Agent 不內含模型、素材、瀏覽器核心或 GPU runtime；不搬運 raw secret、不自行裁決 ALLOW、不直接 commit，也沒有 DB/deploy/restart/router side effect。它只把候選送往注入的 Total Field Gateway client；回應必須由 `submit_to_gateway` 產生內部 receipt 後，才能進入本地 ALLOW-only commit guard。這是 candidate process boundary，不宣稱為跨程序密碼學身分證明。

## 12. 小J pull／push 路徑

小J adapter 使用 provider-neutral Protocol 與 deterministic `InMemoryCandidateProvider`，沒有匯入既有 HTTP/cloud driver，也沒有呼叫真實雲端服務。

- Total Field pull：provider candidate → envelope → `TOTAL_FIELD_PULL` → gateway `receive_candidate`
- LLM push：provider candidate → envelope → `LLM_PUSH` → gateway `receive_candidate`

`persona_text` 只供人類解釋；`governance_candidate` 才能送入 governance。candidate hash 明確排除 persona，所以更換 persona 不會改寫治理候選或 TFS。小J若嘗試提供 ALLOW、commit、TFID 或 Total Field Hash，會回穩定 rejection。

## 13. ADI 安全回退

ADI 正式名稱為 Absolute Distance Spiral Index（絕對距離螺旋索引）。本次沒有定義正式 metric、topology、quantization 或 tie-break 演算法。

- 未請求：`ADI_NOT_REQUESTED`，不影響 commit。
- 已請求但不完整：`HOLD_ADI_NOT_CONFIGURED`。
- 完整固定測試向量：deterministic fixture strategy，輸出 `TEST_ONLY=true` 與 result hash。

外部 request 不能用 context 自我聲明 test fixture 或 ADI result；本版 gateway 對任何 `adi_requested=true` 維持 HOLD。Fixture strategy 只在獨立 conformance test 中產生 evidence。ADI 不修改 D3、不產生治理事實、不裁決 D8，也不取代 Metric、Topology 或 TFS。

## 14. 測試與驗證結果

Focused runtime suite 已執行 45 個具名案例，結果 `45/45 PASS`。涵蓋 canonical/hash replay、event/rule/domain 差異、NaN/Infinity/extra/missing 拒絕、四態 commit gate、fixed/cycle/timeout、D6/D7、gateway 共用入口、小J隔離、Small Agent、ADI、本地等價、deep copy、legacy compatibility、Active D6/D7/D8 與既有 D3 direct import。

Runtime verifier 只處理本次 12 個新檔與精準保護清單；它不跑全倉庫測試。既有 document consolidation 與四個 D3 focused commands 依核准的最終序列各執行一次。

| 驗證項目 | 結果 |
|---|---|
| 8 個新增 Python 檔 `py_compile` | PASS |
| candidate policy JSON | PASS |
| runtime profile schema JSON／Draft 2020-12／request-result vectors | PASS |
| focused runtime tests | 45/45 PASS |
| runtime candidate verifier | `PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE` |
| 既有 document consolidation tests | 8/8 PASS |
| 既有 document verifier | `PASS_VERIFY_TFCT_TRUE8D_W7TP_CANDIDATE_CONSOLIDATION` |
| 既有 D3 candidate tests | 15/15 PASS |
| 既有 packet runtime D3 replay | 4/4 PASS |
| 既有 D3 verifier | 4/4 PASS |
| 既有 packet runtime verifier D3 replay | 9/9 PASS |
| Active/Pointer/legacy `tensor_8d` HEAD diff | PASS |
| 20 個既有 candidate/D3/packet 檔事前 SHA-256 | 20/20 MATCH |

## 15. 未執行事項

- Active Canonical 或 Pointer 寫入
- Canonical Promotion
- DB write、migration、deploy、restart、router write
- 真實 LLM/cloud call
- 正式會員資料處理
- parser DSL 或任意 candidate code execution
- distributed consensus protocol
- production ADI algorithm
- 全倉庫測試套件
- git commit 或正式送件

## 16. Open Problems

- Observation Domain 完整集合與治理來源
- 固定點存在性、唯一性、全域有限收斂證明
- Priority Policy 組合及 constraint conflict theorem
- 分散式 consensus protocol 與跨節點一致性證明
- Canonical TFID 與 Total Field Hash contract
- 正式 Submit Gateway／domain registry persistence 邊界
- ADI metric/topology/quantization/tie-break 正式算法
- Small Agent 安裝資格、能力協商與受控 raw channel
- Gateway client receipt 的跨程序認證與正式 provenance contract
- 真實效能聲明所需的可引用測試證據

每個進入本次可執行路徑的 open problem 都以 HOLD、NOT_CONFIGURED、UNSUPPORTED 或 OPEN_PROBLEM gate 收斂，不使用隱含 allow fallback。

## 17. Canonical Promotion 前置條件

任何升格必須另案取得明確授權，並至少完成：人工 code/document review、定理狀態審核、legacy adapter/migration 決策、domain registry 與 gateway deployment contract、完整安全測試、distributed-consensus 邊界裁決、ADI 狀態裁決、全部 focused verifier PASS，以及 Active Canonical/Pointer 寫入授權。

本報告不宣稱已完成生產級、數學定理證明、分散式共識、正式 ADI、專利新穎性確認或任何 Canonical Promotion。
