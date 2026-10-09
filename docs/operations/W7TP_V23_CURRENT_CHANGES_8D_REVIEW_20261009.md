# W7TP／8D ADI V2.3｜未提交變更因果依賴與送審紀錄

**性質：** `CANDIDATE_ONLY_FOR_GIT_REVIEW`；不是 D8 正式裁決、正典升格、部署或營運驗收。
**觀測：** 2026-10-09 19:18–19:25（Asia/Taipei）；節點 taiji01。
**來源工作樹：** `/home/taiji_admin/Taiji_Hub`，原始 HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e`。
**審查基座：** 遠端主線 `be621d3c65068c2d7f502736305e46c37f4100a5`（已有 PR #24/#25 的菜單變更）。
**審查分支：** `review/w7tp-v23-current-changes-20261009`。原始工作樹、正典與服務均不隨本次 Git 提交改變。

## 同一動態狀態場的 D1–D8 耦合分析

- **D1 意圖：** 使用者要求分析目前變更的因果依賴，經既有規則送審、非強制推送；未授權正式部署／身分升格。
- **D2 狀態：** 原工作樹有 29 個追蹤檔案修改，另精確選入 17 個必要的新程式／測試。正式任務 `T-XIAOJ-LAUNCH` 與 `XJ-021` 為 DOING；`T-007` 已 DONE；`T-028` 有獨立安裝前置 HOLD，不併入本次變更。
- **D3 座標：** taiji01 → Git 審查分支 → origin；MSI 獨立啟動狀態符號連結不與伺服器來源同批；遠端主線 4 筆菜單提交與這 29 個路徑沒有重疊。
- **D4 證據：** 經既有 `tools/w7tp_bridge_dynamic_context_transport_v1.py` 取得任務 Context 候選；來源 46/46 檔案與隔離樹雜湊一致，Python AST／XML 靜態解析與值型憑證模式掃描未發現違規；32 項限定單元測試在隔離工作樹通過。
- **D5 執行／政策：** Git 審查分支提交與推送可進行；正式應用、Odoo 升級、網路切換、模型部署及財務／會員實體效果都未授權。審查失敗不得自動執行補救或自動合併。
- **D6 生成式狀態傳輸：** 本次 Git diff 是版本差異證據，**不是** D6 GST（生成式狀態傳輸）成果；不由 diff 或小封包推定原胞效果。核心橋接候選應維持指標優先取得與規則重構，不能用模型選路當事實。
- **D7 風險／隔離：** 不引入巢狀 worktree、壓縮候選、私密授權收據、舊版簽章、執行時符號連結或完整備份。會員身分綁定、票券實際核銷、外部 effect permit 和 VPN 候選順位仍需審查，不能由限定測試直接放行。
- **D8 封套／權威：** 唯一正式權威仍在 taiji01 V2.3 總場。這份 PR 僅請求工程審查，標記 `HOLD_FORMAL_D8_RELEASE_AND_PRODUCT_EFFECT`；不得宣稱 PR 提交代表正式 D8 PASS。

八維是八合一單一動態狀態場，以上只是同一候選變更的關聯投影，不是八步流水線。

## 變更群組與實際依賴

| 變更群組 | 主要來源／耦合依賴 | 限定驗證 | 未閉合事項 |
|---|---|---|---|
| A. 本地模型與規則匝道 | `core/msi_local_llm_route.py` ↔ `tools/w7tp_bridge_dynamic_context_transport_v1.py` ↔ `core/resource_arbitration.py`；`core/external_effect_gate.py`、既有 Gateway 與測試 | 規則上下文 8/8、模型路由 9/9、雲端代理發現 1/1、外部效果閘門 4/4 通過 | 目前路由候選有 LAN→Tailscale→SSH 順序，與「禁止主動 VPN」意圖需明確消歧；effect permit 的總場正式授權／簽章閉環未實測 |
| B. 會員與 Google／LINE 登入 | `external_signup.py` ↔ 會員控制器、身分紀錄 ↔ Google／LINE callback ↔ Odoo 容器 secret-file 對接 | 靜態語法通過 | 會員產品與登入來源檢查失敗；未證明實際 OAuth 端到端、會員身分不誤合併與 D8 授權 |
| C. 聊國票券與座位 | `capability_seat.py` ↔ masked lookup ↔ voucher checkout ↔ member voucher redeem guard ↔ XML 權限／員工介面 | 票券候選 8/8 通過 | 僅原始碼候選，未測真實會員／庫存／財務效果，不得將 10→9 單測當實際核銷 |
| D. 票券真實性與 Odoo 顯示 | ticket controller ↔ 真實商品來源；quota view 依賴現行父表單 XPath | 不虛構價格測試 2/2 通過，XML 解析通過 | Odoo 實際資產及升級、視圖載入效果未驗收 |

## 有實測失敗，禁止升格

來源驗證（原工作樹）：

- `verify_google_member_login_exact_remediation.py`：缺「登入後不需要再選角色」字串。
- `verify_sovereign_ai_member_product.py`：會員 UI 用語及 Google 歷史路由檢查失敗。
- `verify_sovereign_ai_member_local_completion.py`：會員 UI 用語檢查失敗。
- `verify_xiaoj_source_route_shell.py`：命中禁止的 `config_parameter` 來源字串。
- `verify_xiaoj_8d_total_system_assembly.py`：驗證器要求舊的 `D1_identity`；現行 V2.3 D1=Intent，不能為通過舊測試而回退定義。

上述五項為 **HOLD**，不得聲稱正式驗收或全面相容。額外的 JS 語法工具於 taiji01 未找到，僅核對了檔案存在及來源一致性。正式版本仍需 Odoo 執行時與授權路徑驗收。

## 既有專項 Commit Envelope Gate（提交封套檢查）結果

- `tools/w7tp_commit_envelope_gate.py` 對這批 **47 個審查檔案**回報 `HOLD_COMMIT_ENVELOPE_CLASSIFIER`；該專項分類器僅承認列舉的治理工具路徑，47 項業務／服務源碼全被分類為 `unknown`。**不可冒稱該閘門已 PASS**，也不得因此將未分類來源升格成正式變更。
- 值型秘密掃描回報 `REFINED_SECRET_VALUE_CHECK_HOLD`，位置 3 筆。AST 逐項核對：3 筆指定變數的右側均為 Call（函式呼叫），不是固定秘密字串；仍保留專項掃描的 HOLD 記錄。獨立憑證值模式掃描未發現實際硬編碼值。
- 本批只能作為 **Draft PR（草稿拉取要求）審查候選**，不能宣稱已通過 Commit Envelope 或 D8 正式封套；專項閘門未取得 PASS，不能以 Git 推送取代權威裁決。

## 明確排除及原因

- `Taiji_Governance/candidates/**`：含數百份隔離候選／壓縮檔及三份巢狀 Git 工作樹，需分案來源／保密／權威審查；本次不整包推送。
- `analysis/**`、`web/connect/**`：其他任務／設計候選，缺乏與本批核心修改的直接驗收依賴，暫保留原狀。
- `T-007` 的歷史授權收據及 `T-028` 安裝前置候選：前者已封口，後者有明確 HOLD，不重啟／偷渡。
- MSI 的 `W7TP_FIELD_ATLAS/runtime_status/latest_startup_state_packet.yaml`：執行時更新的符號連結，不作為本次正式 Git 來源；不回退、不清理。

## 送審的必要驗收條件

1. 重驗 V2.3 總場活躍指標與每個任務精確對應之 Dynamic Context。
2. 修復或清楚裁決五項來源驗證失敗；驗證新舊 8D 語義正確，不能只為綠燈改回舊映射。
3. 純 Git 提交與推送後，重新核對遠端分支 HEAD、檔案清單、非強制推送結果及原主線不變。
4. 任何正式 Odoo／模型／會員／票券部署與效果，另取 D8 有效收據與必要自然人核可。

**審查要求：** 請維持 Draft（草稿）；正式 D8 封套／權威與產品級效果均未核准。
