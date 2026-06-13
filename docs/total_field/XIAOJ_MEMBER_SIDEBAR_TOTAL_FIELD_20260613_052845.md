# XiaoJ Member-Owned Sidebar Total Field Design
# 小J會員專屬側邊欄總場設計

## 0. Total Field Write-In Statement（總場寫入聲明）

本設計正式寫入 W7TP / XiaoJ Total Field（總場）。

核心產品句：

> 本會提供 No-Plaintext Context（無明文上下文）與 8D Secure Browser（八維安全瀏覽器），小J真正屬於會員；會員可用自己的 AI KEY 與 API，把雲端 AI 變成受保護、可節費、可治理的個人代理。本會看統計，不看個資。

---

## 1. Product Identity（產品身份）

產品名稱：

- Member-Owned Sidebar XiaoJ（會員專屬側邊欄小J）
- XiaoJ Member Browser AI Cockpit（小J會員瀏覽器 AI 駕駛艙）
- Personal 8D Encrypted Agent AI（個人會員八維度加密個人代理 AI）

定位：

> 會員登入後，可透過本會提供之小J瀏覽器或瀏覽器側邊欄，使用真正屬於會員自己的小J。  
> 小J具備本會 8D / 7D Privacy Technology（八維／七維私隱保護技術），可接入會員自己的 AI KEY、會員自己的 API、商家 API、管委會 API，並以無明文上下文進行 AI 節費與治理。

---

## 2. Ownership Principle（會員擁有原則）

Member-Owned XiaoJ（會員擁有的小J）必須滿足：

1. 會員可啟用 / 停用小J。
2. 會員可連接 / 撤銷自己的 AI KEY。
3. 會員可連接 / 撤銷自己的 API。
4. 會員可選擇允許的瀏覽器輔助範圍。
5. 會員可查詢使用量。
6. 會員可清除或匯出自己的 Personal Context（個人上下文）。
7. 會員可撤銷小J在特定網站或功能上的權限。
8. 會員敏感資料不得被本會取得。

核心句：

> 協會造車與安全系統，會員拿自己的鑰匙與能源；小J是會員自己的駕駛助手。

---

## 3. Association-Admin-Blind Rule（本會管理端盲化硬規則）

硬規則：

> 連本會都不能取得會員敏感資訊。  
> 本會僅可取得 Desensitized No-PII Behavioral Statistics（脫敏、無個資行為統計）。

本會不得取得：

- 會員 AI KEY 明文
- 會員 API token 明文
- 會員瀏覽器原始資料
- 會員完整個資
- 會員敏感上下文
- 會員私密對話全文
- 會員完整文件內容
- 會員密碼
- cookie
- localStorage
- 可識別個人身分的原始紀錄

本會可取得：

- 匿名功能使用次數
- 脫敏錯誤類型
- 模型用量統計
- 封包成功 / 失敗率
- 功能類別統計
- 成本區間統計
- 安全風險類型統計
- 無個資效能資料
- 服務營運必要的 aggregate / anonymous usage metrics（彙總／匿名使用指標）

核心句：

> 會員擁有資料，本會提供保護技術；本會看統計，不看個資。

---

## 4. 8D Packet Governance（八維封包治理）

每次會員小J行動皆必須形成 8D Packet（八維封包）。

| Dimension | English | 中文 | 用途 |
|---|---|---|---|
| D1 | Identity | 身份 | member_ref、merchant_ref、committee_ref、device_ref、role，不使用明文身份 |
| D2 | Intent | 意圖 | 查詢、瀏覽器協助、生活知識、填表草稿、點餐、報修、公告、摘要 |
| D3 | State | 狀態 | session、sidebar、page access mode、member service、order/service/task state |
| D4 | Topology | 拓樸 | member browser、side panel、counter、merchant、committee、site、channel、device |
| D5 | Resource | 資源 | system/member/merchant/committee key_ref、api_ref、model tier、cache、tools、cost policy |
| D6 | Governance | 治理 | allowed / forbidden actions、no plaintext、no direct backend write、confirmation rules |
| D7 | Verification | 驗證 | redaction check、leak check、allowlist check、response verify、usage logging |
| D8 | Envelope | 封套 | nonce、counter、TTL、hash、HMAC/signature、key_ref/api_ref binding、replay protection |

---

## 5. Hybrid Key Mode（混合金鑰模式）

小J會員系統必須支援：

1. System Key（本會系統 KEY）  
   用於公共服務、基礎服務、補助型服務、低風險小J功能。

2. Member Key（會員 KEY）  
   用於會員個人深度 AI、個人化對話、個人 API 能力、個人付費模型。

3. Merchant Key（商家 KEY）  
   用於商家客服、菜單、POS、庫存、訂單、商家自有 AI/API。

4. Committee Key（管委會 KEY）  
   用於公告、報修、會議摘要、社區文件、管委會自有 AI/API。

硬規則：

- raw_key 不得出現在 browser JavaScript。
- raw_key 不得出現在 prompt。
- raw_key 不得出現在 logs。
- raw_key 不得進 Git。
- raw_key 不得進 Odoo normal fields。
- raw_key 不得被送給另一個 AI。
- 封包內只能使用 key_ref。
- API 只能使用 api_ref。
- key_ref / api_ref 必須綁定 scope、allowed_actions、usage_limit、revocation_status、audit ledger。

核心句：

> AI KEY 是能源，不是權限。

---

## 6. No-Plaintext Context（無明文上下文）

No-Plaintext Context（無明文上下文）不是沒有上下文，而是不送原始敏感明文。

允許送給 AI 的內容：

- member_ref
- alias / display name after masking
- redacted summary
- service tags
- task context
- risk flags
- allowed actions
- forbidden disclosures
- packet metadata

禁止送給 AI 的內容：

- full name
- phone
- address
- ID number
- welfare status detail
- raw internal notes
- full member record
- raw browser page
- private document full text
- raw API key/token

---

## 7. Browser Action Bus（瀏覽器動作匯流排）

小J可協助瀏覽器，但必須透過 allowlisted action packet（白名單動作封包）。

允許：

- read_selected_text
- summarize
- explain
- translate
- draft_fill
- show_card
- show_warning
- ask_member_confirm
- call_staff_or_member_service
- display_xiaoj_ui

禁止：

- free mouse control
- read all tabs
- read passwords
- read cookies
- read localStorage
- silent form submit
- direct payment submit
- export raw page data
- access admin pages
- direct Odoo admin write
- hidden recording

核心句：

> 小J可以幫會員操作瀏覽器，但會員永遠坐在駕駛座。

---

## 8. Member Service Functions（會員服務功能）

會員登入後可使用：

- 個人小J對話
- 普通生活知識問答
- 瀏覽器選取文字摘要
- 表單草稿協助
- 會員服務查詢
- 活動狀態查詢
- 訂單 / 服務卡片查詢
- 個人 AI KEY 使用量查詢
- 個人 API 能力連接
- 個人上下文清除 / 匯出
- 權限撤銷

敏感細節顯示需會員再次確認，並且不得被本會後台讀取。

---

## 9. Merchant Special Functions（商家特殊功能）

商家會員可連接：

- POS API_ref
- menu API_ref
- inventory API_ref
- order API_ref
- customer-service API_ref
- merchant AI key_ref

商家小J可：

- 回答客人問題
- 解釋商品
- 產生客服草稿
- 生成商品推薦話術
- 顯示商品卡片

但：

- SKU 必須來自 POS/API。
- price 必須來自 POS/API。
- stock 必須來自 POS/API。
- order facts 必須來自 POS/API。
- 寫入與成交需客人 / 店員確認。

---

## 10. Committee Special Functions（管委會特殊功能）

管委會可連接：

- announcement API_ref
- repair API_ref
- community document API_ref
- meeting record API_ref
- committee AI key_ref

管委會小J可：

- 草擬公告
- 摘要會議
- 分類報修
- 去識別化住戶意見
- 文件問答
- 活動通知

禁止：

- 公開住戶 PII
- 自動處罰
- 自動判定責任
- 自動公開敏感紀錄
- 未經人審發布高風險內容

---

## 11. AI Cost Saving（AI 節費設計）

節費原則：

- 不該叫 AI 的，不叫 AI。
- 能快取的，用快取。
- 能用模板的，用模板。
- 能用小模型的，不用大模型。
- 能用摘要的，不送全文。
- 能用 ref 的，不送明文。
- 能用 POS/API 事實的，不讓 LLM 猜。
- 深度個人任務用 Member Key。
- 商家深度任務用 Merchant Key。
- 管委會深度任務用 Committee Key。
- 公共與補助服務用 System Key。

核心句：

> LLM 處理語意，工具處理事實，8D 封包處理治理。

---

## 12. MVP Scope（第一版範圍）

第一版建議完成：

1. 會員登入
2. 側邊欄小J UI
3. 8D Personal Agent Packet
4. No-Plaintext Context Broker
5. Hybrid Key Broker：System Key + Member Key
6. 選取文字摘要 / 解釋
7. 會員服務查詢卡片
8. Browser Action Allowlist
9. 脫敏無個資統計 ledger
10. 權限撤銷 / 清除上下文

第二版：

1. Merchant API_ref
2. Committee API_ref
3. 表單草稿填寫
4. 商家小J客服
5. 管委會公告 / 報修摘要
6. 個人小J記憶匯出 / 刪除
7. 更完整 usage billing governance

---

## 13. Final Total Field Sentence（總場核心句）

本會提供無明文上下文與 8D 安全瀏覽器，小J真正屬於會員；會員可用自己的 KEY 與 API，把雲端 AI 變成受保護、可節費、可治理的個人代理。本會看統計，不看個資。

