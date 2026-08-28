# 真實使用者旅程收據硬閘

## 最低旅程集合

至少建立宣告執行收據：

1. `HAPPY_PATH`：合法角色從可理解入口達成目標並取得明確回饋。
2. `DENIAL_OR_RECOVERY`：未授權、輸入錯誤、服務失敗或中途退出時，系統清楚拒絕或可回復，不產生隱性效果。

硬閘情境必須覆蓋：

- `FIRST_TIME`
- `RETURNING`
- `LOW_PERMISSION`
- `PENDING_REVIEW`
- `APPROVED`
- `REVOKED_OR_EXPIRED`
- `ERROR_OR_TIMEOUT_RECOVERY`

宣告介面必須覆蓋 `DESKTOP` 與 `MOBILE`；若產品沒有其中一種介面，必須以 `NOT_APPLICABLE_WITH_EVIDENCE` 及證據參照說明。

涉及多角色時，為管理者、待審核者、一般使用者及被拒絕者分別檢查權限與資訊可見性；不得用管理員成功旅程代表會員成功。

## 每條旅程必備

- 去識別化角色與目標。
- 可找到且可理解的入口。
- 有界步驟與每步可見回饋。
- 成功訊號與退出條件。
- 錯誤說明、回復方式及重試邊界。
- 鍵盤、螢幕閱讀、色彩或等價可及性證據。
- 不誤導、不強迫、不預勾選、不隱藏代價的檢查。
- 權威與效果邊界：登入或持有封包不得自動升權。
- 主線旅程、關係模擬與修改影響只可在隔離虛擬空間推演；主線只讀，不得因旅程宣告而接線、合併、覆蓋、部署或啟用。
- runner verdict 只能是 `UNVERIFIED`；`executed=true` 只是 claimed execution，不是實際旅程證明。
- 收據必須是 worktree-local 普通檔 ref、stage receipt 與 detached 實算 SHA-256。
- 同版本測試或執行證據參照。
- 對 `semantic`、`structure_contract`、`dependency`、`tests`、`runtime_wiring`、`data_migration`、`governance_authority`、`security`、`cross_node`、`recovery` 十軸接續距離的影響；每軸列 `state` 與 `evidence_refs`，任一 `UNKNOWN` 即回填 `HOLD`、第一斷點、必要閘與最短接續路線。
- 對供需密合的影響：逐項回填 `old_demand_set` → `new_supply_mapping`、`uncovered_demands`、`extra_side_effects`、`unknown_dynamic_consumers`、`dependency_cycles`、`authority_conflicts`、`recovery_route`。

## 結構閉合條件

detached verifier 只能確認旅程收據的結構、引用、stage receipt、SHA-256 鏈、十軸影響回填與供需密合回填是否閉合。即使全部閉合，所有輸出最高仍只能是 `STRUCTURE_AND_HASH_CHECK_PASS`，且必須同時保留 `RUNTIME_EVIDENCE_UNVERIFIED`、`USER_JOURNEY_EVIDENCE_UNVERIFIED`、`CROSS_NODE_REPLAY_UNVERIFIED`、`AUTHENTICITY_UNVERIFIED`、`ACTIVATION_NOT_AUTHORIZED`；本版不能驗證 runner 是否真的完成真實使用者旅程，不能宣告實際旅程完成，也不能由旅程收據推出正式權威、跨節點真實性、部署或啟用。

以下任一項立即 `HOLD`：

- 旅程只能在管理員或開發者手動介入下完成。
- 拒絕後仍留下部分寫入、假成功畫面或不可回復狀態。
- 介面以模糊文字取得超出使用者明說的效果。
- 無障礙使用者無法取得等價結果或錯誤回復。
- 不同角色看見不該看見的資料或可跨越審核。
- 旅程結果由與被測程式相同的單一假設自我宣告，沒有 worktree-local 收據與 detached hash。
- 以商業價值、留存、成本或營運好處壓過人類入口、撤銷、低權限或錯誤回復。

## 紅隊回修

在 `HUMAN_JOURNEY` 段檢查誤導、弱權限、撤銷、桌機／行動差異、可及性、錯誤回復及角色隔離。可修問題回到介面、契約或程式環節修正後重跑全部下游；最多三輪，超限保留第一斷點並停止該相依群組。
