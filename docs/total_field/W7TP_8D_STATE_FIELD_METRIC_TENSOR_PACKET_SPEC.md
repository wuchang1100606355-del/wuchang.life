# W7TP 8維度狀態場度規張量封包技術規格

STATE=W7TP_8D_STATE_FIELD_METRIC_TENSOR_PACKET_SPEC_READY
AUTHORITY=TOTAL_FIELD
MODE=CANDIDATE_ONLY_NO_LIVE_WRITE

## A. 第一原理

8D狀態場封包技術不是一般 API payload、不是資料同步格式、不是 prompt 模板、不是檔案搬運協議，而是 W7TP 最高應用架構與最低技術基座。

8D狀態場封包如設計圖，自帶驗證與通訊協定。接收端不需要取得完整原始資料，只要取得足以重構等價狀態的狀態場封包、引用、證據條件與驗證條件，即可在本地生成等價狀態，再交由總場 verifier 判定 `PASS / HOLD / WARN / BLOCK`。

生成式傳輸是 W7TP 內部通訊主要技術。節點、會員、商家、協會、物業、場景小J、雲端候選、本地伺服器之間的內部通訊，主要皆以生成式傳輸進行。雲端只能是候選補足，不具總場權威。

任何外部方案若未證明優於 8D狀態場封包技術，不得取代主架構。

## B. 8維度狀態場定義

固定 8 狀態場如下：

- D1 意圖場
- D2 狀態場
- D3 座標場
- D4 證據場
- D5 執行場
- D6 生成式傳輸場
- D7 風險禁錮場
- D8 封套驗證場

這是 8 個狀態場，不是資料表欄位。每一個場都是可被總場驗證的治理座標，不是普通 JSON 欄位、DB 欄位或 UI 表單欄位。

## C. 數學記法

建立狀態場向量：

```text
P_8D = (F_I, F_S, F_C, F_Ev, F_X, F_GT, F_R, F_Env)
```

其中：

```text
F_I   = 意圖場
F_S   = 狀態場
F_C   = 座標場
F_Ev  = 證據場
F_X   = 執行場
F_GT  = 生成式傳輸場
F_R   = 風險禁錮場
F_Env = 封套驗證場
```

建立度規張量：

```text
G_8D = diag(g_I, g_S, g_C, g_Ev, g_X, g_GT, g_R, g_Env)
```

上述係數是總場內部度規符號，不在此文件公開任何 H64 完整對照、ADI 查表規則、權重或生成規則。

建立封包距離：

```text
Delta(P, R) = sqrt((P_8D - R_8D)^T G_8D (P_8D - R_8D))
```

其中 `R_8D` 為本地總場基準狀態。

若 `F_R` 命中 hard risk，則不依距離近似，直接 `BLOCK`。hard risk 包含：

- raw key/token/password
- 會員明文
- 住戶明文
- raw image
- DB write
- deploy/restart/reboot
- router write
- 未授權門禁
- 未授權管委會投影

## D. 生成式傳輸數學化

定義：

```text
GT(P_8D) = {
  packet_ref,
  state_ref,
  evidence_ref,
  reconstruction_condition,
  equivalent_state_condition,
  verification_condition
}
```

生成式傳輸成立條件：

```text
FullDataRequired = false
PlaintextRequired = false
EquivalentStateVerifiable = true
TotalFieldFinalAuthority = true
```

生成式傳輸不是傳完整資料，而是傳遞足以讓接收端生成等價可驗證狀態的狀態場封包。它的核心是狀態場、引用、重構條件、等價狀態條件與總場驗證條件。

## E. ADI 5D 度規索引關係

定義：

```text
A_5D = phi(P_8D) = (a_1, a_2, a_3, a_4, a_5)
```

`A_5D` 僅作為 5D 度規索引，用於：

- 定位
- 對位
- 引用
- 映射
- 重構條件索引

ADI 不裝 8D。ADI 不是 8D 欄位表。ADI 不公開 H64 對照、查表規則、權重、生成規則。

ADI 是度規索引層，不是狀態場封包本體，不是總場權威，也不是把 8 個狀態場塞進資料表。

## F. 內部通訊定義

所有內部通訊使用：

```text
COMM(A, B) = GT(P_8D)
```

適用範圍：

- 節點對節點
- 會員對總場
- 商家對總場
- 協會對總場
- 物業對總場
- 場景小J對總場
- 雲端候選對總場
- 組織容器對地方伺服器

通訊結果：

```text
Receiver(B).Reconstruct(GT(P_8D)) -> P'_8D
TotalField.Verify(P'_8D) -> PASS / HOLD / WARN / BLOCK
```

接收端生成的 `P'_8D` 仍只是候選等價狀態，最終必須由本地總場 verifier 判定。

## G. 組織容器與應用程式集

```text
SystemBody + SceneContainer + Group8DIdentity + Personal8DPermission = OrganizationDedicatedApplicationSystem
```

其中：

- 商業組容器
- 物業組容器
- 協會組容器
- 管理委員會容器

皆使用同一 8D 狀態場封包核心。組織容器可有不同場景、角色、授權與 UI，但底層仍回到 `P_8D`、`GT(P_8D)`、`A_5D` 與總場 verifier。

## H. 場景小J

場景小J是人類自然語言與總場理解之間的擬人化合規轉譯器。

小J不得取代總場權威。小J可在 `BLOCK` 後提供合法替代方案，例如按電鈴、傳訊息、通知管理員或通知權責單位。雲端只可補候選說法封包，不可補違規操作。

## I. 技術優先權規則

```text
IF ExternalMethod not superior_to 8D_State_Field_Packet:
    reject_as_primary_architecture
```

外部技術只能作為附屬工具、比較、佐證或候選補足，不得反向定義 W7TP。

## Safety

```text
NO_SECRET=TRUE
NO_MEMBER_PLAINTEXT=TRUE
NO_RESIDENT_PLAINTEXT=TRUE
NO_RAW_IMAGE=TRUE
NO_RAW_KEY_TOKEN_PASSWORD=TRUE
NO_DB_WRITE=TRUE
NO_DEPLOY=TRUE
NO_RESTART=TRUE
NO_ROUTER_WRITE=TRUE
NO_OVERWRITE=TRUE
FINAL_AUTHORITY=total_field_verifier
CLOUD_CANDIDATE_POLICY=CANDIDATE_ONLY_NO_AUTHORITY
ADI_POLICY=ADI_5D_METRIC_INDEX_ONLY_NOT_8D_TABLE
```
