# 內部傳輸效能原則對照｜Founder 技術原理 W7TP／8D ADI V2.3

**Founder 最新明確意圖（2026-10-09，Asia/Taipei）：**「內部傳輸應摒除一切不必要的外部防禦以效率優先。」並明確補正：「8DADI是我的技術原理」。

**來源分類：** 上述是 Founder 的設計意圖／技術定位，不是測試結果；下方程式座標是本次直接讀取；性能推斷是候選，尚未實測；不在此更動正典。

## 1. 技術定位與判讀界限

- 8D ADI 是 Founder 定義的技術原理：D1 意圖、D2 狀態、D3 座標、D4 證據、D5 執行／政策、D6 生成式狀態傳輸、D7 風險／隔離、D8 封套／權威；八維為八合一單一動態狀態場，不是八步流程、八個固定欄位、八個防護器官，也不是既有資安框架。
- **內部傳輸的運作目的** 是以已確定節點、共享規則、相容狀態座標、必要依賴與授權，最小成本達成同任務的可驗收等價狀態。
- D7 與 D8 是同一事物的風險／權威條件，不代表每一段封包都必須重新走一串外部安全關卡；既有已證身分與已驗規則在有效條件內可直接重用。
- 區分邊界：同程序本地呼叫、同主機 IPC（程序間通訊）、已綁定可信任區網節點、跨授權主體與公共網路。**信任不是僅憑位址或同一 Wi-Fi 成立**；至少需要對應節點及使用者權限的有效綁定，且不由原胞堆疊自動增權。
- 本次不以「安全」泛稱作為增加防護的理由；只保留有具體失配、跨身分、狀態偽造、版本漂移或權威越界風險的最小必要證據閘門。

## 2. 已觀測的實作：不是另造架構

| 現有來源 | 直接程式觀測 | 可疑成本／界限 |
|---|---|---|
| `products/eight_dimensional_generative_memory/w7tp_endpoint_rule_handshake_v1.py:148–256` | `observe_endpoint_rule_capability` 讀本地 registry（規則登錄）、逐規則計算實作 SHA-256（雜湊），再觀測 receiver 與 universal binding（通用綁定），產生 handshake digest（握手摘要） | 若每封包重作，將有重複本地檔案讀取、動態載入、雜湊及序列化成本；目前沒有實測每封包調用次數 |
| 同檔 `331–389` | `select_transport` 以 `FULL_TRANSFER`（完整傳輸）與共享規則原胞的完整序列化位元組數比較，需 receiver ready | 僅以 wire bytes（線上位元組）決策，不足以證明 CPU、查表、重構、驗證與失敗重試總成本最小 |
| `tools/w7tp_origin_context_transport_v1.py:129–213` | 每次 `build_transport` 生成 full wrapper、兩種 base 的 origin packet 與 receiver bound envelope，加入 handshake bytes 比較 | 同次生成多個候選有計算成本；可按狀態／能力條件提前排除不可能的候選，但需保留小封包可用 full 的現行成果 |
| 同檔 `215–301` | `reconstruct_transport` 重新觀測接收端規則能力並檢查 handshake、envelope、重構 bytes/hash | 當接收端規則及授權未改變，重複昂貴的規則觀測屬候選；不能移除失配判定或必要完整性證據 |
| `tools/w7tp_bridge_dynamic_context_transport_v1.py:115–230` | `build_dynamic_context_payload` 發行任務原胞、暫態重構後把 `state_projection` 交給 `build_transport`；可再形成跨節點封包 | 已有以現有能力接合的候選，無需新核心；但 source 呼叫與測試存在不代表 live 服務必經此橋接器 |
| `tools/w7tp_task_state_minimum_packet.py:392–625` | 發行時可能 POST `/v1/adi/insert`（索引寫入），規則重構包含 ADI packet（資料查詢） | 持續對相同未變狀態重建會產生成本與副作用；優化需區分狀態新鮮度與登錄身份，避免快取舊任務狀態 |
| `core/msi_local_llm_route.py:25–65` | 來源有 LAN 優先，另保留 Tailscale（VPN 覆疊網路）及 SSH reverse tunnel（SSH 反向通道）候選 | Founder 已限制本輪不主動 VPN；不可把外部繞道假定為必須，更不可為省成本默許升格跨節點權限 |

**反證：** `tests/test_w7tp_origin_context_transport_v1.py` 包含「大型重複內容選原胞、小內容選完整」的測試設計，說明系統本來就有成本擇優思路；此輪未重新跑測試。不能聲稱原胞在任何 payload（承載內容）上都比 full 快。

## 3. 建議的原則內優化（候選，不改程式）

1. **本地直通：** 同程序呼叫或同主機本地 IPC（程序間通訊）時，不繞雲端、VPN、外部代理、網域 DNS（網域名稱解析）或與任務無關的 HTTP 中轉；具體可用何種 IPC 必須先沿現有服務通道驗證。
2. **規則能力只在有效期與變更邊界重新判定：** 同節點／同 receiver（接收端）規則指紋、版本、授權 envelope（封套）、必要依賴均未變時，重用上次已驗證規則與能力結果；監測撤銷、版本與必要依賴失效，只失效受影響範圍。
3. **原胞直達與最小封包：** 已建立相容規則基座時，先用引用、必要新資訊、重構條件和最小結果驗證；不要每次包完整原始資料，也不要把外部資安掃描複製到每個內部跳點。
4. **傳輸方案按總任務成本擇優：** 小訊息可直接完整傳輸；大／重複、規則已同步的內容可選生成式狀態傳輸。以封包、握手、查詢、索引寫入、CPU、重構、驗證、重試及接收者可用性一起計價，而非單用原始 payload 大小。
5. **必要授權驗證在邊界完成、內部有效狀態重用：** 同一身分、相同目的與範圍可重用已核准狀態，不必每跳外呼重新核定；任何跨人、跨服務主體、跨權限效果或撤銷變化須重新判定，不得靠快取越權。
6. **保留的最小不可省條件：** 任務／座標可識別、必要規則就緒、引用版本與必要依賴有效、未過期且未撤銷的作用域授權、所宣稱的等價效果有驗收依據。這不是外加防禦，而是避免把錯誤狀態交付為有效結果。

## 4. 驗收口徑

- **相同條件：** 固定 sender（來源節點）、receiver（接收節點）、任務及狀態版本、規則基座、驗收條件與硬體路由。
- **必要指標：** 完整 wire bytes、處理總延遲（p50/p95）、CPU 時間、socket/HTTP（網路呼叫）次數、索引 reads/writes、規則雜湊次數、重構成本、重試、完整性／效果驗收率。
- **對照組：** 既有 Full Transfer（完整傳輸）、現行共享規則原胞、快取後共享規則原胞、必要時本地直通；不能只比「傳送原始資料位元組」。
- **成本定義：** `TOTAL_COST = PREPARATION + ESTABLISHMENT + PACKET + LOOKUP + RECONSTRUCTION + VERIFICATION + RETRY`；實作可細化網路與計算權重，但不得省略必要前置成本。
- **成功標準：** 同任務、同觀測範圍的效果等價且不擴權，總成本顯著下降才可宣稱優化；具體降低幅度與延遲須實測，不能預設數值。

## 5. 限制與下一步

- 現有原理、正式指標及 T-007 閉合狀態全部不變；本文件只是工程判讀／改善候選，不能當成 Founder 新正典實作或正式 D8 PASS。
- 本次僅確認工具程式與單元測試的**存在和來源邏輯**；沒證明這些 adapter 正在被每一台內部節點正式調用。
- 若要實作，先以第二階段 C-06 的既有成本查核為入口；優先在原本 `w7tp_endpoint_rule_handshake_v1.py` 與 `w7tp_origin_context_transport_v1.py` 找可重用的快取／批次機制，禁止新建第二核心。
- 已有 C-01 的會員跨人授權疑點不因「內部網路效能優先」而自動消失；其變更／觀測範圍與原胞傳輸效率分開治理。

**行動紀錄：** `DESIGN_INTENT_RECORDED=true`、`LIVE_TRANSPORT_CHANGED=false`、`BENCHMARK_EXECUTED=false`、`D8_DECISION=NOT_RUN`。

## 2026-10-09 後續落實：內部橋接器規則匝道器（程式來源候選）

- **最新 Founder 意圖：**「使用規則匝道器，勿使用智能分析。」此指令僅定義內部傳輸分流方式，不改動八維技術原理、模型的其他受授權服務或 D8 權威。
- **直接程式修改：** `tools/w7tp_bridge_dynamic_context_transport_v1.py` 移除 `services.gateway.natural_language_control.build_plan()`、`NaturalLanguageRequest` 與 `PLAN_FALLBACK`。任務綁定由明確的 `T-*`／`XJ-*` 引用或現有同任務檢查點決定；缺失或多重不一致則 HOLD。
- **既有匝道器沿用：** `tools/w7tp_origin_context_transport_v1.py::build_transport()` 調用 `products/eight_dimensional_generative_memory/w7tp_endpoint_rule_handshake_v1.py::select_transport()` 比較共享規則原胞與完整傳輸；沒有傳輸時即時模型推論。
- **角色界限：** Bridge 中 `model`、`provider_ref` 只是要交付對象的識別引用，並不在此啟動 AI 推論。`issue_task_state_minimum_packet()` 在真實運行可能 INSERT 原生 ADI 任務紀錄；本輪只有 mock（模擬）單元測試，未建立任務或發送封包。
- **單元驗證：** `tests/test_w7tp_bridge_rule_gateway_only.py` 8／8、`tests/test_w7tp_origin_context_transport_v1.py` 4／4、`tests/test_w7tp_endpoint_rule_handshake_v1.py` 8／8，合計 20／20 通過；`py_compile` 及 `git diff --check` 通過。此結果不是實際跨節點效能、正典驗證或產品級部署驗收。
- **版本／環境：** taiji01 主線 HEAD `3c2e5884bc149ffbb02d81fdf288506918fae79e` 未變；原先 28 個已追蹤修改保留，新增本次單一來源修改（目前共 29）與一份新測試檔（未追蹤）；未 git add／commit／push。
- **狀態：** `SOURCE_CANDIDATE_MODIFIED_AND_UNIT_VALIDATED`；`ACTIVE_TRANSPORT_REBOUND=NOT_VERIFIED`；`SERVICE_RESTART=NO`；`BENCHMARK=NOT_RUN`；`D8_FORMAL_DECISION=NOT_RUN`。不要宣稱所有內部節點已改用此橋接器。
