# 五維碼意圖流程快取政策

版本：2026-05-12

## 生效狀態

```text
ACTIVE
```

## 目的

本政策將常見 POS / 業務服務流程轉為可重用的五維碼意圖流程快取，用於降低重複 AI 推理、降低延遲、提高點餐與服務介面的穩定性。

快取對象是治理後的流程模板，不是自然人明文記憶。

## 允許

- 菜單查詢流程快取
- 常點品項草稿流程快取
- 非敏服務需求流程快取
- 客顯非敏狀態更新流程快取
- 五維碼、semantic hash、pattern、route vector、option vector、redacted summary、draft template hash

## 禁止

- 原始語音
- 原始文字
- 客人姓名、電話、會員號等可識別明文
- 付款資料
- 憑證、token、service account JSON、private key
- 付款、退款、折扣、店長覆核、資料庫直寫、正式生產異動

## 啟動原則

```text
check health first
if healthy: do nothing
if stopped: start local runtime
if unhealthy: report and require human decision
```

不得以殺進程重啟作為預設動作。

## 五維碼

```yaml
intent: reusable_pos_service_intent_flow
resource: low_entropy_cache
time: ttl_bound_async_reuse
authority: draft_only_human_confirm_before_submit
topology: local_runtime_cache_gateway_audit
```
