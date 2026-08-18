# W7TP 移動式 V 字預載保護與未命中清理 V1（候選）

狀態：`CANDIDATE_ONLY`  
權限：不具執行、刪除、部署、路由、模型載入或正式 ADI 規則變更權限  
創辦人本輪語義：V 字尖端對準現在；開口朝未來；V 內為預載資料；尖端後方為過去資料；V 側為未命中資料；越往未來，預載範圍擴大，側邊清理範圍縮小。

## 1. 校正後的核心圖形

```text
                          未來時間 +Δt
                                →
                 側邊預測未命中     側邊預測未命中
                         \           /
過去安全清理候選  ←──────  ＜  V 內預載保護
                         /           \
                 側邊預測未命中     側邊預測未命中
                           尖端 Tₑ=對齊後的現在
```

圖形名稱中的「V」只描述時間與狀態範圍的包絡，不以歐氏距離、向量相似度或最近鄰取代原生 ADI。狀態距離只接受由創辦人原生 ADI 唯一規則路徑產生的非負整數 `delta_F`，本候選不計算也不重定義 ADI。

## 2. 三個不可混淆的概念

1. **幾何／時間分類**：資料位於過去、現在保護帶、V 內、V 側或視窗外。
2. **實體存放層級**：`VRAM → RAM → STATIC_PACKET → ADI_INDEX_ONLY → EVICTED_REFERENCE`。
3. **清理動作**：保護、停止預載、軟卸載、隔離；本候選永不永久刪除 canonical source。

分類不是刪除授權。尤其 V 側只能稱為「預測未命中」；未來無法先驗保證。V 側資料可退出 RAM／VRAM，但須留下可驗證來源及 ADI/GTP 重建參照。當時間通過且實際未使用，才成為已確認的過去未命中。

## 3. 形式模型

每個不可變預測世代 `e` 定義：

- `Tₑ`：經時間對齊且單調前進的 V 尖端。
- `Δt(r)=need_time(r)-Tₑ`。
- `event_time(r)`：來源事件發生時間；`ingest_time(r)`：本節點接收時間。兩者不得以 logical time 互相冒充。
- `δF(r)`：由創辦人原生 ADI 唯一規則路徑取得的非負整數絕對距離。
- `Pₑ(Δt)`：V 內預載保護半徑。
- `Rₑ(Δt)`：該時間切片受本機制管理的有限候選半徑。
- `Cₑ(Δt)=Rₑ(Δt)-Pₑ(Δt)`：V 側可軟清理寬度。
- `H`：有限未來預載視窗；超出 H 代表尚未評估，不等於未命中。
- `Wsafe`：所有參與節點水位的最小值；節點斷線或不確定時不得任意越過。

創辦人語義轉為下列可驗證不等式：

```text
0 ≤ Δt₁ < Δt₂ ≤ H
Pₑ(Δt₂) ≥ Pₑ(Δt₁)             # 朝未來，V 內預載保護擴大
Cₑ(Δt₂) ≤ Cₑ(Δt₁)             # 朝未來，V 側清理寬度縮小
0 ≤ Pₑ(Δt) ≤ Rₑ(Δt)            # 管理範圍有限且不反轉
```

只規定 `P` 變大仍不足以保證清理區縮小；若 `R` 增長更快，`C` 仍會變大。因此契約同時固定 `R` 與 `C` 的單調條件。

V 內判斷（邊界採保護側）：

```text
0 < Δt ≤ H  且  δF(r) ≤ Pₑ(Δt)
```

V 側預測未命中：

```text
0 < Δt ≤ H  且  Pₑ(Δt) < δF(r) ≤ Rₑ(Δt)
```

## 4. 完整狀態分類

| 狀態 | 條件 | 安全處理 |
|---|---|---|
| `PAST_HOLD` | 已在尖端後方，但未越過安全水位／延遲期或仍被引用 | 保留 |
| `PAST_ELIGIBLE` | 已越過安全水位與延遲期 | 僅進入隔離候選 |
| `CURRENT_GUARD` | `abs(Δt) ≤ ε` | 強制保護 |
| `FUTURE_PROTECTED` | `0 < Δt ≤ H` 且 `δF ≤ P` | V 內預載保護 |
| `FUTURE_PREDICTED_MISS` | `0 < Δt ≤ H` 且 `P < δF ≤ R` | V 側；僅可軟卸載 |
| `OUT_OF_HORIZON` | `Δt > H` | 不預載、保留參照；不得當作未命中 |
| `OUTSIDE_MANAGED_ENVELOPE_HOLD` | `δF > R` | 設定異常／未受管理，關閉式保留 |
| `UNALIGNED_HOLD` | 時間、ADI、版本、世代或雜湊缺失／衝突 | 關閉式保留 |

## 5. 清理提交閘門

任何 RAM／VRAM 軟清理提案，除幾何分類合格外，提交當下仍須全部成立：

```text
no_live_reference
AND no_active_lease
AND not_pinned
AND record_version == expected_record_version
AND prediction_epoch == expected_prediction_epoch
AND durable_source_verified
AND reconstruction_reference_exists
AND observed_source_hash == expected_source_hash
AND target_is_not_canonical_source
```

清理器必須以 `prediction_epoch + record_version` 做 CAS。分類後若讀者取得 lease、記錄更新或預測世代切換，舊提案必須失效。這同時防止雙重回收與 ABA 型誤清。

本候選只允許：

- `FUTURE_PREDICTED_MISS → SOFT_EVICT_RECONSTRUCTIBLE`
- `PAST_ELIGIBLE → MOVE_TO_QUARANTINE`

不產生永久刪除指令，`canonical_delete_allowed` 固定為 `false`。

## 6. 時間滑動與非同步併發

```text
FUTURE_PROTECTED
    → CURRENT_GUARD
    → PAST_HOLD
    → PAST_ELIGIBLE
    → QUARANTINE
    → ADI_INDEX_ONLY / EVICTED_REFERENCE
```

```text
FUTURE_PREDICTED_MISS
    → 軟卸載為 STATIC_PACKET / ADI_INDEX_ONLY
    → 若後來實際命中，依 GTP/ADI 參照重建
    → 驗證預期雜湊
    → 記錄 false_miss
```

- 尖端與安全水位只能單調前進；系統時鐘倒退須 HOLD。
- `CURRENT_GUARD` 至少覆蓋已知時鐘不確定度；分類快照之後才抵達的資料不得倒灌進舊 epoch。
- 安全水位取活躍必要節點回報的最小值；網路分割時停止永久回收進度。
- 預測更新建立新 epoch；新舊 V 短暫重疊，舊讀者 lease 結束後才回收。
- 重複、亂序或遲到事件先去重並進入 `PAST_HOLD`，不得直接清理。
- 所有動作必須冪等並留下審計收據。

## 7. 記憶體壓力策略

候選配置以 2 GiB 作為第一個合成驗證起點；它不是固定上限、創辦人常數、已配置、已預留或已徵用的記憶體。包括記憶體預算、未來視窗、V 寬、時間保護帶、水位寬限及效能門檻在內的所有數值都可依證據調整。本檔不啟用任何 cgroup、服務或模型設定。

數值調整的目的函數依序為：資料完整與保護區安全、任務效果與回應品質、人類可感知延遲及不卡頓、重建可靠度、預載命中與 false miss、無 OOM／swap thrashing，最後才是 RAM／VRAM／傳輸節省。不得為追求單一記憶體數字犧牲整體使用體驗。

任何預算增減都只先產生候選判斷，至少需要足夠觀察樣本、主機保留量、p95 延遲變化、命中／false miss、OOM、swap、受保護工作集大小及重建 hash 證據。門檻尚未由 shadow/canary 校準前一律 HOLD，不自動套用。

壓力順序：

1. 通過全部重建閘門的 V 側 `FUTURE_PREDICTED_MISS`。
2. 通過全部閘門的 `PAST_ELIGIBLE`，先隔離再回收。
3. 若仍無法降至低水位，回傳 `BACKPRESSURE_REQUIRED`。

禁止為達記憶體目標而改判 `CURRENT_GUARD` 或 `FUTURE_PROTECTED`。可採取的安全降載是縮短新一代預載視窗、減少新工作接收或讓上游背壓；不得從既有 V 內保護集任意挑資料敲掉。

## 8. ADI、GTP 與生成式傳輸接合

- ADI 提供 `delta_F`、狀態根、事件時間、logical time、規則版本及證據根。
- GTP／8D 靜態封包只保存最小可重建參照、來源雜湊及允許填補路徑，不在快取契約內存放完整個資或秘密。
- 小模型只拿當前 V 內預載投射及必要的現在保護集；未命中時按索引重建。
- 生成式重建不是權威來源。輸出雜湊不符合預期時 HOLD，回退至已驗證來源。
- 原生 ADI 規則血統尚未經總場確認時，本機制保持 candidate/reference-only。
- 原生 ADI 的 `deleted_refs` 若代表永久 tombstone，不得用來表達 RAM／VRAM 快取卸載；本候選另用 `materialization_evictions`，且 `canonical_action` 永遠為 `RETAIN`。

## 9. 必須永遠成立的不變量

1. `CURRENT_GUARD` 與 `FUTURE_PROTECTED` 的回收違規數為零。
2. `δF=P` 一律屬 V 內保護。
3. 未知時間、距離、epoch、版本或雜湊一律 HOLD。
4. 相同分類 epoch 與 CAS epoch 才能提交。
5. 清理提交前重查引用、lease、pin 與版本。
6. 尖端、安全水位不得倒退。
7. 所有卸載資料均有可驗證的 ADI/GTP 重建參照。
8. canonical source 永不由本候選永久刪除。
9. 重跑同一工作不得 double-free。
10. V 內超出預算時使用背壓，不能破壞保護。
11. false miss 必須可重建、驗證並計數。
12. 所有提案可稽核，且不得把候選自我提升為總場決策。

上列安全規則是固定不變量；2 GiB、60 秒、各 ADI 半徑及其他數字只是合成測試值，不是固定發明限制。

核心零容忍指標：

```text
protected_eviction_violation = 0
current_eviction_violation = 0
canonical_source_deleted = 0
double_reclaim = 0
unaudited_reclaim = 0
hash_mismatch_consumed = 0
```

另量測 `preload_hit_rate`、`false_miss_rate`、重建 p50/p95、RAM/VRAM 釋放量、GTP 傳輸量、背壓時間與水位停滯時間。

## 10. 邏輯驗證矩陣

| 編號 | 情境 | 必須結果 |
|---|---|---|
| G01 | 過去但有引用 | `PAST_HOLD` 或清理閘門 HOLD |
| G02 | `Δt=0` | `CURRENT_GUARD` |
| G03 | 未來且 `δF<P` | `FUTURE_PROTECTED` |
| G04 | 未來且 `δF=P` | 仍為 `FUTURE_PROTECTED` |
| G05 | 未來且 `P<δF≤R` | `FUTURE_PREDICTED_MISS` |
| G06 | 比較未來各切片 | `P` 不減、`R-P` 不增 |
| G07 | `Δt>H` | `OUT_OF_HORIZON`，不可稱 miss |
| T01 | 尖端前進 | 未來→現在→過去依序轉換 |
| T02 | 時鐘／水位倒退 | 拒絕 |
| C01 | 分類後取得 lease | 提案取消 |
| C02 | 兩清理器競爭 | 僅相同 CAS 版本可提交 |
| C03 | 預測 epoch 更新 | 舊 epoch 提案取消 |
| M01 | RAM/VRAM 壓力 | 先 V 側，再安全過去 |
| M02 | 候選不足 | 背壓；不得選 V 內資料 |
| R01 | 軟卸載後重新命中 | 可重建且雜湊一致 |
| R02 | 無可靠來源或雜湊不符 | HOLD |
| P01 | 大量組合測試 | 所有被選資料皆符合清理謂詞 |

## 11. 範圍與審查狀態

參考實作 `tools/total_field/moving_v_preload_cleanup_candidate.py` 是純函式決策器：不讀系統時鐘、不讀模型內容、不寫檔、不連網、不清理記憶體。配置、Schema、測試及證據包都必須先經總場審查；在正式決策前不得接入服務、cgroup、Ollama、Codex、小模型路由或遠端節點。

本設計不得以「既有元件名稱相近」推論它們已可共同運作。ADI、GTP、既有動態上下文、2 GiB 上限、裝置韌性與多節點時間對齊目前皆是分離的候選或既有構件；其整合狀態與逐階段證據門檻另見 `W7TP_MOVING_V_COMPATIBILITY_MATRIX_V1_CANDIDATE.md`。
