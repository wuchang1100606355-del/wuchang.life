# D8 Demo Q&A And Objection Handling

## 這跟普通 RAG 差在哪？

普通 RAG 多半是查資料再回答。D8 的重點不是回答，而是治理：先看狀態、紅隊錯誤經驗、可能告警與 guard decision，再決定任務能不能進行，並產生 seal。

## 這跟 Cursor / Codex / Claude Code 差在哪？

Cursor、Codex、Claude Code 主要幫助 agent 做事。D8 是做事前後的治理操作台：先判斷是否可以做，做完留下 sealed evidence，失敗則回寫成未來防線。

## 這會不會讀我的機密？

公開 demo 不讀 secret、不讀 config password、不讀 token。任何需要 secret 的行為都必須另開任務封包並由人類授權。

## 這能不能操作 POS？

公開 demo 不操作 POS 寫入。MVP 只展示 read-only POS/Odoo evidence bridge。

## 這能不能下單付款？

不能。公開 demo 和 cafe pilot scope 都禁止 POS order write 和 payment capture。

## 這有專利了嗎？

目前只有 invention disclosure draft 和初步 prior-art check，不是法律意見，也不是專利保證。正式專利判斷需要專利律師審查。

## 這是否已可正式上線？

不是。現在是 public-safe demo ready 和 controlled pilot ready。Production release 需要後續測試、人審與 release gate。

## 為什麼咖啡館需要這個？

咖啡館也有多角色營運、POS、Odoo、會員、報表、店務決策。D8 提供一個保守的 AI 操作邊界，讓團隊知道哪些可以展示、哪些要 HOLD、哪些必須人審。

## 紅隊資料會不會污染主線？

D8 的 redteam 設計是 non-executable、redteam-only、pollution guard、reverse-index isolation。公開 demo 只講安全概念，不展示敏感事件內容。

## 如果 AI 做錯怎麼辦？

停止動作、產生 HOLD/BLOCK、保存 report/seal，並把錯誤轉成未來告警。這是 D8 的核心價值：錯誤不被忽略，而是變成下一次任務前的防線。
