# 獨立驗證與收據綁定

結構建構器只可產生 `CANDIDATE` 與 `ACTIVATION_NOT_AUTHORIZED`。detached verifier 只能重算結構、canonical serialization、SHA-256、stage receipt 與 hash chain；本版最高只可加入 `STRUCTURE_AND_HASH_CHECK_PASS`，且必須同時列出 `RUNTIME_EVIDENCE_UNVERIFIED`、`USER_JOURNEY_EVIDENCE_UNVERIFIED`、`CROSS_NODE_REPLAY_UNVERIFIED`、`AUTHENTICITY_UNVERIFIED`、`ACTIVATION_NOT_AUTHORIZED`。

十二段、四功能、旅程與傳輸收據即使閉合，也不能證明實際 runner 旅程、跨節點真實性、authority、DB 寫入、生產部署或正式啟用。producer、runner、caller 自報的 executed、`FIELD_EVIDENCE` 或 verifier_result 不採信。

## 完整來源標籤

每次建構必須存在且分開：

- `USER_EXPLICIT`
- `AI_COMPLETION_HYPOTHESIS`
- `FIELD_EVIDENCE`
- `EXTERNAL_PRIMARY_SOURCE`
- `MODEL_PRIOR_CANDIDATE`
- `AUTHORITY_DECISION_REQUIRED`

所有標籤只保存參照與雜湊，且 `grants_authority=false`。`AUTHORITY_DECISION_REQUIRED` 表示仍需決定，不是已有授權。效果白名單要附不可變來源鏈，逐項綁定 `USER_EXPLICIT` 的識別、敘述雜湊與來源參照。

`FIELD_EVIDENCE` 必須是 worktree-local 普通檔 ref、stage receipt 與 detached 實算 SHA-256；名稱、規則、文件敘述、placeholder、env_ref、key_ref 與 weight 參數名可保存，但秘密值、會員明文、私有查表、真實權重資料、相位映射、真正 `WHY_IT_RUNS` 與內部推理不得入封包或報告。

## 正典 8D 與四功能

驗證器必須確認 `HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD` 只被用作正典八面動態選用，不是第九維，也沒有授權效果。八面必須 exact 為 `identity_source`、`authority_governance`、`structure_contract`、`supply_dependency`、`function_execution`、`causality_validation`、`sequence_version`、`risk_boundary`。

3D-7D 只可出現在無效果預分析候選。身分角色權威治理、秘密／隱私／會員／營業秘密、跨節點正式 runtime／DB／部署／路由、外部不可逆效果或不確定前沿任一存在時，必須完整 8D。

四功能 `ANALYSIS`、`TRANSFER`、`CONSTRUCTION`、`ADDRESSING` 必須存在，且狀態只能是 `UNVERIFIED`。`enabled` 不是證據。

`ANALYSIS` 與 `ADDRESSING` 共同承擔主線關係與接續距離，不得新增第五功能。驗證器必須拒絕只停在檔名、相似度或表面結構的分析；所有推演、模擬、候選組合與修改影響只能標為隔離虛擬空間結果，主線保持只讀，且不得授權接線、合併、覆蓋、部署或啟用。

每一分析／定址階段都必須有 `candidate_relation`、`continuation_distance`、`missing_gates`、`first_breakpoint`、`shortest_continuation_route`。`candidate_relation` 只能是 `CONTINUE`、`FUSE`、`REPLACE`、`PARALLEL_SHADOW`、`ISOLATE`、`HOLD`。

`continuation_distance` 必須逐軸列 `semantic`、`structure_contract`、`dependency`、`tests`、`runtime_wiring`、`data_migration`、`governance_authority`、`security`、`cross_node`、`recovery`，且每軸有 `state` 與 `evidence_refs`。`state` 只能是 `ALIGNED`、`DELTA`、`UNKNOWN`。不得加總為單一分數，不得用檔案數、coverage 百分比或相似度冒充接續距離。任一軸 `UNKNOWN` 立即 `HOLD`，並列第一斷點、必要閘與最短接續路線。

關係硬閘：`CONTINUE` 必驗輸入輸出契約、依賴、版本；`FUSE` 必驗重疊供給、優先序、雙執行風險、權威衝突；`REPLACE` 必驗所有消費者覆蓋、行為等價、資料遷移、退場與回復；`PARALLEL_SHADOW` 只能隔離、無效果、不影響主線；`ISOLATE` 用於無關或風險邊界；`HOLD` 用於未知軸或必要閘未閉合。相似度不得升格任何關係，未閉合只能 `PARALLEL_SHADOW`、`ISOLATE` 或 `HOLD`。

供需依存必須密合列出 `old_demand_set` → `new_supply_mapping`、`uncovered_demands`、`extra_side_effects`、`unknown_dynamic_consumers`、`dependency_cycles`、`authority_conflicts`、`recovery_route`。任一必要缺口非空不得 `REPLACE` 或覆蓋，只能 `PARALLEL_SHADOW` 或 `HOLD`。安全順序固定 `expand` → `migrate` → `deprecate`，且每步必須有回復。

三欄 detached 證據必須符合 [relational-closure.schema.json](relational-closure.schema.json)。verifier 不得呼叫 producer 的三欄 validator 作為判定；必須獨立核對 exact keys、關係 hard gates、十軸、缺閘／第一斷點／最短路線、供需 mapping、五種缺口、三步 recovery、evidence artifact 原始 SHA-256 與 stage receipt。candidate 三欄、producer relational hash、evidence artifact 或 stage receipt 任一不一致即 `HOLD`。通過只代表 `STRUCTURE_AND_HASH_CHECK_PASS`，不授權主線、canonical 或 D8。

## 固定人格與產品全貌矩陣

必須同時存在 `REAL_HUMAN_USER` 與 `SILICON_VALLEY_DIGITAL_STARTUP_DIRECTOR_PRODUCT_OWNER`。兩者都只能提出候選。產品矩陣至少核對：使用者問題、價值、角色、需求、供給、成本、營運、留存、擴充、風險、成功量測、退出與回復；任一項缺證據即 `HOLD`。商業價值不得取代人類入口、實際收據或權威。

## 十二段初掃收據

只接受下列 exact order：

1. `RUNTIME_GAP_LOCALIZATION`
2. `STATE_FIELD_ANALYSIS`
3. `HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD`
4. `ADI_COORDINATE_INDEX`
5. `CAUSAL_RELATIONAL_SUPPLY_DEPENDENCY_GROUP_FUNCTION_ANALYSIS`
6. `CODE_LOOP_CLOSURE`
7. `SECOND_SCAN_DIFF`
8. `GENERATIVE_TRANSFER_ANALYSIS`
9. `PROGRAM_TRANSFER_RUBBING`
10. `RECEIVER_RECONSTRUCTION`
11. `EQUIVALENT_STATE_VERIFICATION`
12. `REAL_HUMAN_USER_JOURNEY`

每段都必須有嘗試收據、輸入 hash、輸出 hash、stage receipt、runner state `UNVERIFIED` 與 producer state `UNVERIFIED`。十二段全嘗試且留下已知證據缺口後，才可受限引用 `MODEL_PRIOR_CANDIDATE` 或 `EXTERNAL_PRIMARY_SOURCE` 補缺；補缺不得改寫 `USER_EXPLICIT`、正典、權威或效果。補後形成 worktree-local `FIELD_EVIDENCE`，從最早受影響段重跑全部下游。

## 真實旅程收據

每個宣告旅程都要有收據，至少綁定：旅程識別、情境、介面、角色、入口、`claimed_execution_state`、執行器與版本、`runner_verdict=UNVERIFIED`、專案版本、步驟結果、可及性、權威邊界、錯誤回復、十軸接續距離影響、供需密合影響及產物 SHA-256。主線旅程、關係模擬與修改影響只可在隔離虛擬空間推演；runner 不可信。拒絕／回復旅程另須宣告沒有部分效果。驗證器從 worktree 內以拒絕符號連結的方式重算產物雜湊；缺少首次、回訪、低權限、待審、核准、撤銷或過期、錯誤或逾時回復，或缺少桌機與行動且無有證據的不適用，即 `HOLD`。

旅程收據閉合後仍只能保留 `USER_JOURNEY_EVIDENCE_UNVERIFIED`；`claimed_execution_state` 不能證明實際人類旅程，也不能宣告實際旅程完成。

## 七段紅隊收據

只接受七個正式段名，不接受缺少或多餘段。每輪綁定輸入雜湊、輸出雜湊、發現問題數、已修數、修正動作、實際重跑、執行器、產物與結果。若發現問題：

1. 已修數必須覆蓋發現數。
2. 輸入與輸出雜湊必須改變。
3. 必須記錄 `claimed_rerun_state`，但該狀態仍為未驗證聲稱。
4. 所有下游段必須在同一最終候選上重新驗證。
5. 最多三輪，超限 `HOLD`。

最後一段輸出雜湊必須等於最終候選封包 SHA-256，防止紅隊通過後又替換候選。

七段檢查重點固定為：

- `INTENT`：補 `FIELD_EVIDENCE` 偽裝、秘密混入、需求與使用價值誤導。
- `SOURCE`：來源投毒、版本漂移、授權、完整性、真實性與來源權威混淆。
- `ARCHITECTURE`：動態 8D 自授權、越權、隱私、擴充、單點失敗與成本失控。
- `CODE`：注入、路徑逃逸、資源耗盡、重放、偽造驗證與秘密外洩。
- `HUMAN_JOURNEY`：人類誤導、弱權限、撤銷、桌機／行動差異、可及性與錯誤回復。
- `CROSS_NODE_TRANSFER`：transfer invariant、接收 hash、receiver reconstruction、equivalent state、污染、節點漂移、竄改與回復。
- `PRE_ACTIVATION`：假結果、真實性混淆、權威失效、效果越界、回復失效與證據過期。

## 跨節點收據

綁定協定與版本、邏輯根、來源／目標節點、專案版本、候選封包 SHA-256、來源與目標快照 SHA-256、傳輸物件參照與重算 SHA-256、claimed nonce、簽發時間、到期時間、來源／目標平台、平台相容性、污染／漂移／竄改／回復閘、`claimed_signature_state` 及 `claimed_authority_state`。

驗證器拒絕：邏輯根或版本不一致、同節點冒充跨節點、TTL 過期或超限、物件雜湊不符、平台相容性未知、任何防護未閉合。此技能沒有原子 nonce ledger，不得宣稱全域重放排除。跨節點完整性與真實性分開輸出；真實性保持 `AUTHENTICITY_UNVERIFIED`，且必須保持 `ACTIVATION_NOT_AUTHORIZED`。

transfer invariant 必須 exact 為 `protocol=IFGC-GTP`、`protocol_version=1.0.0`、`recipe_semantics=STABLE`、`canonical_serialization=UTF8_SORTED_KEYS_COMPACT`、`hash_method=sha256`、`full_source_embedded=false`、`receiver_reconstruction_required=true`、`equivalent_state_verification_required=true`、`activation_boundary=NOT_AUTHORIZED`、`dynamic_depth_may_change_semantics=false`。diff receipt、rubbing receipt、receiver reconstruction receipt、equivalent state receipt 與 hash chain 必須逐段重算。

## 路徑與內容安全

輸入、收據、實際產物及輸出都必須位於指定 worktree。逐層以不跟隨符號連結方式開啟；輸出使用同一已開啟父目錄的檔案描述元建立暫存目錄、排他寫入、同步後原子改名，縮小檢查與使用間競態。

敏感判斷檢查實際型態與值：原始私鑰、權杖、密碼、會員明文或大段可執行／編碼來源才 HOLD。`placeholder`、`${ENV}`、`env_ref`、`key_ref`、雜湊、欄位名稱及規則名稱不得只因字樣被誤判。
