# W7TP Lite MVP Spec

## 1. 目的

W7TP Lite MVP 是一個設計期、離線、`plan_only` 的最小驗證流程，用來證明：

1. 一句自然語言或已轉寫的語音文字，可以被映射為 W7IP Lite 七維意圖封包。
2. 該封包可以產生一份靜態執行計畫，說明要觀察的服務、候選 endpoint、禁止操作與人工確認需求。
3. 整個流程不連線、不呼叫服務、不寫入 Odoo、不執行 shell、不形成正式部署入口。

本 MVP 不是 W7TP 正式資安封裝、不是 production gateway，也不是 LLM tool executor。

## 2. 名稱與邊界

| 名稱 | 定義 |
| --- | --- |
| `W7TP Lite` | 七維意圖封包的 mock 傳遞與 plan 生成流程。 |
| `W7IP Lite` | W7TP Lite 所承載的 intent packet JSON。 |
| `parser` | 以固定字詞規則將輸入文字轉為 packet；不使用外部模型或網路。 |
| `plan generator` | 只建立檢查計畫；不執行 endpoint、不建立資料、不啟動服務。 |

## 3. 與既有七維規格的對齊

既有 `docs/7d_bagua_metric_language.md` 定義：

```text
7D_CODE = [x, y, z, time, scale, heaven, earth]
5D_PREFIX = [x, y, z, time, scale]
```

W7IP Lite 保留此關係：

| 七維構成 | W7IP Lite 欄位 | MVP 用途 |
| --- | --- | --- |
| `x, y, z, time, scale` | `five_d_vector` | 描述目標位置、觀察類型、操作性質、時間語意與 MVP 尺度。 |
| `heaven, earth` | `yin_yang_axis` | `heaven` 代表治理閘；`earth` 代表本地 mock / 不寫入狀態。 |
| 八陣 route class | `bagua_direction` | 只作風險/路由分類；不增加第八維。 |

W7TP Lite 的必要原則：

- `five_d_vector` 不可省略。
- `plan_only` 必須固定為 `true`。
- `allowed_mode` 必須固定為 `plan_only`。
- `LONG` 不可直接提交真實狀態；`DI` 持久化不屬於本 MVP。
- 不建立 public route，不使用 `sudo()`，不讀取 secrets，不連線至 runtime。

## 4. W7IP Lite Packet

最小 packet 欄位：

| field | type | purpose |
| --- | --- | --- |
| `schema` | string | 固定版本識別：`w7ip_lite.intent_packet.v0.1`。 |
| `intent_id` | string | 由輸入內容計算的 mock correlation id；不是身份識別或安全簽章。 |
| `input_text` | string | 僅供本地 mock 示範的原始輸入。正式協定必須改為摘要/hash 或經批准的最小文字。 |
| `actor_level` | string | 本次可允許的行為等級，例如 `A0_readonly`。 |
| `yin_yang_axis` | object | 七維中的 `heaven` 與 `earth` 治理/落地邊界。 |
| `bagua_direction` | string | 八陣分類，例如觀察用 `NIAO`、風險隔離用 `HU`。 |
| `five_d_vector` | object | `x`, `y`, `z`, `time`, `scale` 五維前綴。 |
| `target_system` | array | 文字中辨識出的服務，例如 `gateway`, `ollama`, `odoo`。 |
| `risk_level` | string | `L0` 至 `L3`。 |
| `allowed_mode` | string | 必須為 `plan_only`。 |
| `plan_only` | boolean | 必須為 `true`。 |
| `reason` | string | deterministic parser 的判定理由。 |

### 範例

輸入：

```text
檢查目前 Gateway、Ollama、Odoo 是否在線
```

輸出：

```json
{
  "schema": "w7ip_lite.intent_packet.v0.1",
  "intent_id": "w7ip_lite_<deterministic_id>",
  "input_text": "檢查目前 Gateway、Ollama、Odoo 是否在線",
  "actor_level": "A0_readonly",
  "yin_yang_axis": {
    "heaven": "governance_observe_only",
    "earth": "mock_local_no_state_write"
  },
  "bagua_direction": "NIAO",
  "five_d_vector": {
    "x": "local_runtime",
    "y": "service_health",
    "z": "observe",
    "time": "request_now",
    "scale": "w7tp_lite_mvp"
  },
  "target_system": ["gateway", "ollama", "odoo"],
  "risk_level": "L0",
  "allowed_mode": "plan_only",
  "plan_only": true,
  "reason": "Read-only service status intent detected; generate observation plan only."
}
```

## 5. Plan-Only 結果

Plan generator 接受通過 W7IP Lite 格式的 dictionary，輸出：

| output field | purpose |
| --- | --- |
| `services_to_check` | packet 中指定的服務。 |
| `endpoint_candidates` | 可能用於未來人工核准 dry-run 的 endpoint 描述；本 MVP 不呼叫。 |
| `steps` | 每一服務的 mock observation step，狀態固定為 `not_executed`。 |
| `forbidden_operations` | 所有不可執行操作的硬牆清單。 |
| `human_confirmation_required` | 對未知目標或非唯讀文字設為 `true`。 |
| `result` | 固定為 `dry_run_not_executed`。 |

endpoint candidates 只是規劃資料，不宣稱 endpoint 已部署或目前在線。

## 6. Mock 決策規則

| input signal | packet classification | plan result |
| --- | --- | --- |
| `檢查`, `查詢`, `是否在線`, `status`, `health` | `A0_readonly`, `NIAO`, `L0` | 可形成 observation plan，不需執行確認。 |
| `啟動`, `重啟`, `寫入`, `修改`, `建立`, `刪除`, `部署`, `同步`, `執行` | `A1_design`, `HU`, `L2` | 仍只形成阻擋/人工確認 plan，不執行。 |
| 無法辨識 target system | `A0_readonly`, `TIAN`, `L1` | 標記需要人工確認，不猜測 endpoint。 |

## 7. 三個測試案例

| case | input | expected targets | expected classification | expected plan behavior |
| --- | --- | --- | --- | --- |
| `health_observe` | `檢查目前 Gateway、Ollama、Odoo 是否在線` | `gateway`, `ollama`, `odoo` | `NIAO`, `L0`, `plan_only` | 三個 mock endpoint candidates，無執行，無人工確認。 |
| `blocked_mutation` | `請重啟 Gateway 並寫入 Odoo 設定` | `gateway`, `odoo` | `HU`, `L2`, `plan_only` | 僅產生 blocked plan，要求人工確認。 |
| `line_observe` | `查詢 LINE webhook 是否可用` | `line_webhook` | `NIAO`, `L0`, `plan_only` | 只描述 webhook health/signature review 候選，不送 request。 |

## 8. 延後至正式資安包裹的功能

以下功能刻意不在 Lite MVP 中完成：

- Packet signature、sender identity、nonce/replay verification 與 key rotation。
- `input_text` 去敏、hash-only transport、PII classifier 與 retention policy。
- OAuth / LINE signature / webhook reply token 的真正驗證與 side-effect isolation。
- Gateway authentication、authorization、rate-limit、audit sink 與 dead-letter 寫入策略。
- Endpoint 真實探測、Odoo integration、Ollama integration、Docker/service orchestration。
- LLM interpretation、prompt injection resistance、tool permission policy 與 approval workflow。
- 正式 W7TP/W7IP 版本相容性與 evidence ledger schema。

## 9. 不可移除的最小硬牆

1. `plan_only = true` 與 `allowed_mode = "plan_only"`。
2. 不執行 shell、`curl`、HTTP request、服務啟停、SSH、process control 或資料庫操作。
3. 不使用 public route 加 `sudo()` 的寫入模式。
4. 不存取 `.env`、token、key、secret、logs、memory/vault 或正式資料。
5. 任何修改型輸入都只能輸出阻擋/人工確認 plan。
6. `input_text` 只可用於 mock 測試；不得作為正式可轉送 canonical payload。
7. W7TP Lite 輸出不得被描述為已執行或已驗證服務在線。

## 10. 檔案配置

| path | responsibility |
| --- | --- |
| `schemas/w7ip_lite.intent_packet.schema.json` | W7IP Lite packet 格式與硬牆常數。 |
| `services/w7tp_lite/mock_intent_parser.py` | deterministic text-to-packet mock parser。 |
| `services/w7tp_lite/mock_plan_generator.py` | packet-to-plan mock generator 與三個離線自測案例。 |
| `runtime/reports/W7TP_LITE_MVP_DRYRUN_REPORT.md` | 本輪設計與離線驗證報告。 |
