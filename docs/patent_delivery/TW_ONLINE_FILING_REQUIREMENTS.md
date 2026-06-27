# Taiwan Online Filing Requirements

OFFICIAL_SOURCE_CHECKED=TRUE
CHECK_DATE=2026-06-27
LEGAL_REVIEW_NEEDED=TRUE
UNCERTAINTY=Official filing rules and fees can change; re-check TIPO before live submission and have patent counsel confirm claim strategy, applicant ownership, priority, grace-period, and trade-secret boundaries.

## Official Sources Checked

- TIPO Patent Q&A, 發明專利、新型專利、設計專利有何不同？ https://www.tipo.gov.tw/tw/patents/546-7271.html
- MOEA Laws and Regulations, 專利法 https://law.moea.gov.tw/LawContent.aspx?id=FL011249
- TIPO e網通, 電子申請 https://tiponet.tipo.gov.tw/030_OUT_V1/caseApplication/prepare.do
- TIPO e網通, 電子申請約定 https://tiponet.tipo.gov.tw/020_OUT_V1/econtractAgree
- TIPO 電子申請 FAQ, 如何使用 e網通專利線上申請進行線上申請專利案件 https://www.tipo.gov.tw/tw/tipo1/241-55714.html
- TIPO 電子申請 FAQ, 智慧財產局提供哪些方式編寫電子申請案件 https://www.tipo.gov.tw/tw/tipo1/241-2013.html
- TIPO 專利申請表格暨申請須知 https://www.tipo.gov.tw/tw/patents/469.html
- TIPO 專利規費清單 https://www.tipo.gov.tw/tw/patents/482.html
- TIPO 專利 Q&A, 專利申請規費有何減收規定？ https://www.tipo.gov.tw/tw/patents/546-6827.html

## Patent Type Fit

發明專利：保護利用自然法則之技術思想的創作，標的可涵蓋方法、系統、物品、用途等。W7TP / 小J / 8D / 生成式傳輸的核心在封包生成、分段傳輸、本地重構、候選運算隔離、查表驗證與執行閘門，主線應採發明專利。

新型專利：限於物品形狀、構造或組合。若後續要保護專用邊緣盒、路由裝置、POS 安全橋或硬體化 verifier 模組，可另案評估；不建議作為本案主申請。

設計專利：保護視覺外觀或 GUI 等視覺創作。若後續有公開 GUI 或設備外觀，可另案評估；不承載本案技術核心。

## Online Filing Availability And Setup

發明專利可透過 TIPO e網通與專利線上申請/新電子申請系統進行電子申請。送件前應完成：

- e網通會員註冊並啟用帳戶。
- 準備可用憑證；TIPO 頁面列出政府機關核發憑證與智慧財產憑證等選項。
- 於 e網通會員中心上傳憑證。
- 依案件量與環境選擇專利線上申請或新電子申請系統。
- 填寫申請書資料、說明書資料，匯入或上傳規定文件。
- 以 TIPO 指定方式繳納規費並保留收據/電子回執。

## Invention New Application Required Documents

| Item | Required For This Case | Status |
| --- | --- | --- |
| 發明專利申請書 | YES | NEEDS_APPLICANT_INVENTOR_DATA |
| 說明書 | YES | DRAFT_EXISTS: docs/patent_delivery/V4_TRUE8D_TIPO_MAIN.md |
| 申請專利範圍 | YES | DRAFT_EXISTS: docs/patent_delivery/V4_TRUE8D_CLAIMS.md |
| 摘要 | YES | DRAFT_EXISTS: docs/patent_delivery/V4_TRUE8D_ABSTRACT.md |
| 必要圖式 | LIKELY_YES | NEEDS_FIGURE_FINALIZATION; if counsel confirms no drawing is necessary, mark NOT_APPLICABLE in filing package |
| 指定代表圖 | IF_DRAWINGS_FILED | NEEDS_SELECTION_AFTER_FIGURE_LIST |
| 發明名稱英文翻譯 | OPTIONAL_BUT_FEE_RELEVANT | NEEDS_TRANSLATION_CHECK |
| 申請人姓名或名稱英文翻譯 | OPTIONAL_BUT_FEE_RELEVANT | NEEDS_APPLICANT_INPUT |
| 發明人姓名英文翻譯 | OPTIONAL_BUT_FEE_RELEVANT | NEEDS_INVENTOR_INPUT |
| 摘要英文翻譯 | OPTIONAL_BUT_FEE_RELEVANT | NEEDS_TRANSLATION_CHECK |
| 委任證明文件 | IF_AGENT | NOT_APPLICABLE_UNLESS_AGENT_USED |
| 優先權證明文件 | IF_PRIORITY_CLAIMED | NOT_APPLICABLE_UNLESS_PRIORITY_CLAIMED |
| 優惠期證明文件 | IF_GRACE_PERIOD_CLAIMED | NEEDS_LEGAL_REVIEW |
| 生物材料寄存證明 | NO | NOT_APPLICABLE |
| 序列表或生物相關附件 | NO | NOT_APPLICABLE |
| 規費繳納證明或電子繳費紀錄 | YES | NEEDS_LIVE_FILING_STEP |

## Fee And Reduction Notes

- TIPO patent fee page lists invention patent application fee as NTD 3,500 and invention substantive examination fee as NTD 7,000 when the specification, claims, abstract and drawings are within the listed page/claim threshold.
- TIPO fee reduction Q&A states electronic patent application can reduce the fee by NTD 600 when complete electronic documents are submitted; for invention/new utility applications, complete documents include abstract, specification, claims and drawings, with invention drawings omitted only when there are no drawings.
- TIPO fee reduction Q&A states that if an invention application is not filed in English, adding English translations for invention title, applicant name, inventor name and abstract can reduce the application fee by NTD 800. This reduction does not apply the same way to new utility or design applications.
- Payment methods should be selected from the current TIPO fee page or e網通 payment flow at filing time.

## Public Data And Redaction Rule

TIPO application forms page warns that published or announced patent files may be available for public inspection, and that personal or non-public data should not be placed in documents such as specification, claims, drawings, amendment reasons or response reasons. For this case:

- Do not put member plaintext, phone numbers, addresses, national IDs, raw audio, credentials, endpoint tokens, private governance chain, WHY_IT_RUNS lookup details, codebooks or sensitive revenue/governance details in public filing documents.
- Applicant and inventor data should be handled only in official application forms or counsel-controlled working sheets, not in repo public drafts.
- Any evidence excerpt copied into the specification should use sealed references, hashes, and high-level technical descriptions only.

## Current Filing Readiness

READY_FOR_COUNSEL_REVIEW=TRUE
READY_FOR_LIVE_ONLINE_SUBMISSION=FALSE

Blocking live-submission data not collected in repo:

- Applicant legal name, address, nationality, representative, entity type and authority to file.
- Inventor names, nationalities and assignment/ownership confirmation.
- Decision on agent use and power-of-attorney document.
- Decision on priority, grace period and any earlier disclosure dates.
- Final figure set and representative drawing.
- Final TIPO-format application forms and live fee payment.
