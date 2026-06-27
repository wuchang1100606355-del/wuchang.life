# INTENT_STATE_PACKET_LEDGER_SPEC_V1

## 1. 架構定位
意圖狀態封包資料庫 (Intent-State Packet Database) 是本系統的 AI 運行底座。它揚棄了傳統關聯式資料庫直接被 AI 讀寫的作法，改採 Append-only (僅限附加) 的不可變帳本 (Immutable Ledger) 設計。

## 2. 儲存單元與狀態流轉
- **儲存單元**: 唯一合法寫入單位為 `W7TP_8D_INTENT_STATE_PACKET` 及其衍生之 Result Packet。
- **狀態流轉 (State Transitions)**: 封包的生命週期嚴格遵循 `DRAFT -> BROKERED -> CANDIDATE_READY -> VERIFIED -> SEALED / REDTEAM`。
- **主索引 (Master Index)**: 維護 `ACTIVE_GT_8D_PACKET_POINTER`，確保所有分場重構與總場驗證皆基於最新的合法封印狀態。

## 3. 隔離性與一致性
- 任何未經總場 Verifier 簽發 `seal_ref` 的封包，皆無法進入最終帳本。
- 資料庫層級禁止任何 `UPDATE` 或 `DELETE` 操作，確保完整可稽核性 (Auditability)。
