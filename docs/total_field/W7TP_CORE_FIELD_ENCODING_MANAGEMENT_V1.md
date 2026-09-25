# W7TP 核心場編碼與場邊碼管理 V1

## 核心定義

場編碼不是只替資料編號。它把「事物本體、所在語義位置、與其他事物的關係、證據及權限邊界」轉為可驗證的參照，使同一套 8D 封包能處理不同場域，而不改動總場核心規則。

底層固定流程：

```text
穩定來源座標
→ 本體碼（它是什麼）
→ D1–D8 槽位（它位於哪個語義位置）
→ 場邊碼（它與其他本體有何方向性關係）
→ 內容雜湊
→ 本地總場驗證
→ D8 候選封套
```

編碼只能建立候選身分與關係，不能自行取得 D8、正式交易、付款、資料庫寫入或總場修改權。

## 三層編碼

| 層級 | 格式 | 用途 |
|---|---|---|
| 來源座標 | `QUICKCLICK:{menu_id}:{entity_coordinate}` | 由最底層來源身分定位商品、問題與選項 |
| 本體碼 | `W7TP_THING_REF:v1:{thing_class}:sha256:{digest}` | 將人、物、事件、規則、證據、狀態或服務等事物轉為權威範圍內的穩定參照 |
| 場邊碼 | `W7TP_FIELD_EDGE_REF:v1:{dimension}:{relationship}:sha256:{digest}` | 表達兩個本體之間具方向性的 D1–D8 關係 |

Odoo 人類操作面與 ADI AI 操作面另有不洩漏內部索引的表面綁定碼；兩者最終必須解析回同一來源座標及同一語義雜湊。

## D1–D8 位置與意義

| 位置 | 本體角色 | 場邊關係 | 人類意義 |
|---|---|---|---|
| D1 | `INTENT` | `HAS_INTENT` | 希望得到什麼結果 |
| D2 | `STATE` | `HAS_STATE` | 目前狀態與連續狀態身分 |
| D3 | `COORDINATE` | `LOCATED_AT` | 位於哪個場域、profile 或實體座標 |
| D4 | `EVIDENCE` | `SUPPORTED_BY` | 由哪些可核驗來源支持 |
| D5 | `EXECUTION` | `PROPOSES_EXECUTION` | 僅表示候選執行路徑，不授權執行 |
| D6 | `GENERATIVE_TRANSMISSION` | `RECONSTRUCTS_AS` | 依封包協定、引用及查表重構所需狀態 |
| D7 | `RISK` | `EXPOSES_RISK` | 風險、紅隊漂移與安全邊界 |
| D8 | `ENVELOPE` | `ENVELOPED_BY` | 總場候選封套；正式裁決仍需既有 Founder 根驗證 |

## 碼位範例

`QUICKCLICK:M387676:O7835309:Q1:O2`：

1. `QUICKCLICK`：來源權威命名空間。
2. `M387676`：菜單身分。
3. `O7835309`：規格群組身分。
4. `Q1`：群組內問題位置。
5. `O2`：問題內選項位置。

原始選項代碼不可單獨作唯一身分；完整來源位置才是底層座標。

## 增刪與版本規則

- 新增實體：只配置新增實體的來源碼與表面綁定碼。
- 刪除實體：只從新版本的有效登錄表撤除該碼；舊版內容定址封包保留歷史證據。
- 修改名稱或價格：來源身分不變時，既有碼不變，只更新快照與登錄表雜湊。
- 修改來源身分：建立新碼；舊碼只能作歷史退役證據，不得靜默轉指。
- 快照 SHA：封存整份版本，不參與未變實體的本體碼，避免全表重編。

## 管理入口

輸出核心登錄表：

```bash
python3 tools/total_field/w7tp_field_application_runtime.py suite encoding-registry
```

查詢任一受管理碼的逐段意義：

```bash
python3 tools/total_field/w7tp_field_application_runtime.py suite encoding-explain QUICKCLICK:M387676:O7835309:Q1:O2
```

建立兩個分離的唯讀操作面綁定檔：

```bash
python3 tools/total_field/w7tp_field_application_runtime.py suite cafe-pos-bindings ODOO_HUMAN
python3 tools/total_field/w7tp_field_application_runtime.py suite cafe-pos-bindings ADI_AI
```

兩個操作面都只產生 L3 候選。未取得既有總場驗證的正式綁定 seal 前，必須維持 `HOLD`。

## 正式綁定 seal 邊界

正式 Odoo／ADI 對照表不能靠把 JSON 的 `state` 改成已驗證而生效。總場依序檢查：

1. 商品、問題及選項完整覆蓋目前 QuickClick 來源座標。
2. 表面碼沒有重複、跨類型錯置或使用預覽命名空間冒充正式 Odoo 綁定。
3. 菜單快照、route table、capability registry 與核心編碼登錄表 SHA-256 一致。
4. ADI 僅保留不透明參照，沒有揭露內部索引規則。
5. 建立 `W7TP-CAFE-POS-BINDING-SEAL-REQUEST/1.0` 候選。
6. 沿用既有 `authorize_total_field_change()` 驗證裝置 principal 與 Google OIDC subject hash 雙根。

沒有 OS 保護的本機 Founder root 時固定回傳 `HOLD_FOUNDER_ROOT_NOT_PROVISIONED_OR_INVALID`。公開 CLI 不接受 root、token、password 或 OIDC credential；root ceremony 必須在既有受保護的本機程序完成。

產生待驗證 seal 請求：

```bash
python3 tools/total_field/w7tp_field_application_runtime.py suite cafe-pos-binding-seal-request --bindings /path/to/read-only-production-bindings.json
```

seal 通過只代表 Odoo／ADI 對照表可用於 L3 唯讀整流，不代表正式 POS 訂單、付款或 D8 核准。
