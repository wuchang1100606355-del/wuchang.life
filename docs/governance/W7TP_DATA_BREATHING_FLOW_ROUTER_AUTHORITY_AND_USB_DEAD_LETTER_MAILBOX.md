# W7TP Data Breathing Flow, Router Authority, and USB Dead-Letter Mailbox

## 1. 一句話說明

本設計把路由器納入總場管理的 edge node，讓資料呼吸流中的失敗候選封包可被本地離散狀態核心驗證、隔離、封印，並在 USB 空間持久化為 dead-letter mailbox records。

## 2. 要解決的問題

候選封包可能來自 UI、Open WebUI、Odoo、POS、AI Browser 或雲端候選腦。當候選封包缺少證據、驗證失敗、不可執行或必須隔離時，系統不能 silent fail，也不能把失敗封包丟失。失敗候選必須進入 USB dead-letter mailbox，或在 USB backend 不健康時明確 HOLD。

## 3. 路由器為何要納入總場權限

路由器位於本地網路邊界，能承載 edge status、USB mailbox health、JFFS pointer health 與封包隔離狀態。納入總場權限的目的不是讓路由器成為雲端權威，而是讓總場取得安全、風險、證據、驗證與落地閘口所需的 edge-node evidence。

## 4. 路由器的權限邊界

路由器是 Total Field managed edge node，但不是 cloud authority。允許的能力限於 readonly probe、status report、USB dead-letter write、JFFS health check、USB health check，以及經人工批准後的 JFFS pointer write。禁止 direct cloud control、secret read、member plaintext read、未審計 config write 與未審計 restart。

路由器能否承擔 USB dead-letter mailbox 不是預設成立。任何寫入或常駐流程前，必須先以只讀探測確認 CPU、RAM、USB I/O、USB 可用空間、JFFS 可用空間、JFFS 寫入壓力、溫度與系統負載。若路由器負載能力不足或無法驗證，狀態必須 HOLD_ROUTER_CAPACITY_NOT_VERIFIED，不得把總場治理核定解讀成路由器可承擔。

## 5. 資料呼吸流

資料呼吸流分為 intake、redact、packetize、verify、route、materialize、exhale、expire。來源必須先 redacted，候選封包必須 candidate_only，雲端只提供候選多樣性。local_authority 必須是 discrete_state_core，負責查表、驗證、隔離、封印與執行准駁。

## 6. USB 死信箱

USB dead-letter mailbox 是 failed candidate packet records 的持久化主體。mailbox_backend 必須為 usb。當候選封包缺 evidence、execution_allowed=false、verifier 不放行或需要隔離時，系統應把去識別化摘要、packet hash、failure stage、failure reason、evidence ref 與 recommended next action 寫入 USB mailbox record。若 USB 不健康，狀態必須 HOLD，不得 silent fail。

## 7. JFFS 與 USB 如何配合

JFFS 只保存 pointer、status、小型 metadata 與開機恢復狀態。USB 保存 dead-letter mailbox records。當 JFFS 與 USB 都健康，狀態為 USB_MAILBOX_OK_JFFS_POINTER_OK。當 USB 健康但 JFFS degraded，USB mailbox 仍可生效，狀態為 USB_MAILBOX_OK_JFFS_DEGRADED，並在 JFFS metadata 中標記 degraded。當 USB 不健康，狀態為 HOLD_USB_DEAD_LETTER_BACKEND_UNAVAILABLE。

## 8. 為何 dead-letter mailbox 主體必須在 USB 空間生效

JFFS 空間小、寫入壽命有限，適合保存 pointer/status，不適合作為 failed packet records 的主體。USB 提供更合適的持久化空間，可承載多筆 redacted dead-letter records、evidence refs 與重試狀態。這也避免 JFFS 被大量失敗封包寫滿而影響路由器基本運作。

## 9. 雙腦安全 AI 關係

雲端候選腦只提供候選多樣性，不是權威。本地離散狀態核心才負責驗證、隔離、封印與執行准駁。Cloud candidate brain 不得直接成為 router、Odoo、POS、Open WebUI 或 AI Browser 的執行權威。

## 10. UI 如何呈現

UI 應呈現 router edge node status、USB mailbox health、JFFS pointer health、dead-letter count、latest evidence ref 與 HOLD reason。若 USB 不健康，UI 必須顯示 HOLD_USB_DEAD_LETTER_BACKEND_UNAVAILABLE。若 USB 健康但 JFFS degraded，UI 必須顯示 USB_MAILBOX_OK_JFFS_DEGRADED，而不是隱藏降級狀態。

UI 也應顯示 router_capacity_status。若尚未完成只讀探測，顯示 HOLD_ROUTER_CAPACITY_NOT_VERIFIED。若 CPU/RAM/USB I/O/JFFS 壓力超過門檻，顯示 HOLD_ROUTER_CAPACITY_INSUFFICIENT，並禁止任何 mailbox 寫入推進。

## 11. Odoo / POS / Open WebUI / AI Browser 如何接

Odoo、POS、Open WebUI 與 AI Browser 只能提交 redacted candidate packet 或讀取去識別化 mailbox status。它們不得讀取 secrets、env、會員明文、raw audio 或 router password。Odoo production DB write、POS payment capture、module upgrade、service restart 與 deploy 都必須保留在獨立 release gate 之後。

## 12. 路由器 SSH 只讀探測安全規則

需要 SSH 時只能使用互動輸入：提示使用者輸入路由器 SSH 主機/IP、帳號與密碼，帳號預設 coffeeboss，密碼輸入不可回顯。不得把密碼放進命令列、檔案、env、log、report、chat、router script 或 git tracked file。本階段不執行 router SSH、不寫 router config、不 restart router、不 reboot router。

只讀探測的最小指標包含 uptime/load average、free memory、USB mount status、USB free space、USB write health indicator、JFFS free space、JFFS write pressure、kernel storage errors 摘要與溫度狀態。探測結果只能寫入去識別化 runtime report，不得保存密碼、env、secret、會員明文或 raw audio。

## 13. 不主張事項

本設計不主張雲端直接控制路由器，不主張 JFFS 作為 dead-letter mailbox records 主體，不主張任何候選腦成為權威，不主張自動部署、DB write、module upgrade、restart 或 router reboot。

## 14. 安全聲明

SECRET_READ=false、ENV_DUMP=false、MEMBER_PLAINTEXT_READ=false、RAW_AUDIO_READ=false、DB_WRITE=false、DEPLOY=false、SERVICE_RESTART=false、PRODUCTION_RELEASE=false、EXTERNAL_CLOUD_CALL=false。總場守安全，Odoo 承載流程，會員守主權。總場是 execution、risk、evidence、seal authority，但不是 member-sovereignty authority。

## 15. Runtime Evidence Reference

Runtime evidence is written under `runtime/data_breathing_flow/<RUN_ID>/`. It includes inventory, fixtures, validation output, linter decisions, and final validation reports. Runtime evidence is not staged unless separately approved.
