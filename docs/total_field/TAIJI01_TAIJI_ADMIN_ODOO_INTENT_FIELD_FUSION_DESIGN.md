# taiji01 / taiji_admin Odoo 意圖場融合重構設計

status: `FUSED_LIVE`

本文件定義可審查的融合與重構邊界，並記錄 Stage B 至 Stage F 的保存、候選驗證、最終 freeze、live 切換及帳號退役。Stage F 已由 Owner 明確核准；live Odoo／PostgreSQL 已切換至通過驗證的融合 runtime，服務與路徑依賴已解除，`taiji_01` 帳號已在零依賴檢查後刪除。

## 1. 判定

融合可行，但必須採用混合式重構：

- `taiji_admin/Taiji_Hub/Taiji_Odoo` 是程式碼與目標 Compose 的基線。
- taiji01 live PostgreSQL、Odoo filestore 與必要執行狀態是必須另外保存及驗證的實體證據。
- D8 PostgreSQL 維持獨立資料庫與獨立生命週期，不與 Odoo PostgreSQL 實體合併。
- 意圖場封包只攜帶引用、座標、規則、重構條件、驗證方法與證據雜湊；不把資料庫、filestore 或任意既有檔案改稱為可由極小封包無條件還原。
- 缺失的 live Compose、來源專有 addon 與共享模組差異只能先形成 L3 candidate，通過本地狀態機、相容性測試及人工確認後，才能成為正式結果。

## 2. 已核對狀態

### 2.1 taiji_admin 基線

- 目標 Compose：`Taiji_Odoo/docker-compose.yml`。
- 目標 addon 目錄有 15 個模組目錄，包含 PM3、member login、fund、knowledge、property、wish tree 與既有 Wuchang 模組。
- `taiji_d8_db` 使用獨立 `pgvector/pgvector:pg16`，狀態 healthy；`taiji_d8` 有 8 張業務表。此資料庫不屬於 Odoo 帳號搬移範圍。
- 目標 Compose 把 Odoo 固定到 `postgres` database；這與目前 live Odoo 實際使用 `wuchang_odoo` 不等價，不能直接切換。

### 2.2 taiji01 live 狀態

- `wuchang_os_odoo_18` 正在使用 taiji01 的 `addons` 與 `odoo_data` bind mounts。
- `wuchang_os_pg` 的主要資料位於 Docker named volume；`wuchang_odoo` 約 95 MB、680 張表，且有 live Odoo connection。
- `wuchang_os` 約 21 MB、120 張表，應先保存為獨立資料庫備份候選，不得與 `wuchang_odoo` 直接混表。
- `quarantine_wuchang_os_pg_20260508_200520` 只有預設資料庫且沒有業務表，可列為驗證後淘汰候選。
- live Odoo 有 8 個已安裝的 Wuchang 自訂模組；其中 `wuchang_association_member_trust` 不在 taiji_admin addon 基線。
- live container metadata 指向的 `/home/taiji_01/Taiji_Hub/Taiji_Odoo/docker-compose.yml` 已不存在；其他路徑中的 Compose 只能當候選證據，不能直接宣告為 live authority。

### 2.3 addon 差異

| 模組 | taiji_admin 檔案 | taiji01 檔案 | 共同且相同 | 共同但不同 | 僅 taiji_admin | 僅 taiji01 |
|---|---:|---:|---:|---:|---:|---:|
| `wuchang_cafe_ai_gateway` | 43 | 32 | 22 | 10 | 11 | 0 |
| `wuchang_cafe_menu_options` | 6 | 6 | 6 | 0 | 0 | 0 |
| `wuchang_core` | 166 | 316 | 150 | 10 | 6 | 156 |
| `wuchang_google_member_login` | 13 | 9 | 5 | 4 | 4 | 0 |
| `wuchang_line_login` | 6 | 6 | 6 | 0 | 0 | 0 |
| `wuchang_member_registration` | 15 | 15 | 11 | 4 | 0 | 0 |
| `wuchang_pos_topology` | 4 | 4 | 4 | 0 | 0 | 0 |

因此禁止整目錄覆蓋。完全相同模組可直接引用 taiji_admin 基線；有差異模組必須逐檔做語義與相容性審查；`wuchang_association_member_trust` 必須隔離為來源專有候選。

## 3. 融合後責任邊界

| 層 | 正式責任 | 禁止事項 |
|---|---|---|
| 程式基線 | `taiji_admin/Taiji_Hub/Taiji_Odoo` | 不以 taiji01 整包覆蓋 |
| Odoo 業務資料 | `wuchang_odoo` 邏輯備份及其驗證雜湊 | 不直接複製 live PostgreSQL data directory 作為唯一備份 |
| 歷史／次要資料 | `wuchang_os` 獨立邏輯備份 | 不與主資料庫直接混表 |
| Odoo filestore | 與資料庫一致時間點的封存及雜湊 | 不把 session token 當一般可散佈資料 |
| 自訂 addon | taiji_admin 基線加通過審查的差異 | 不自動安裝或升級 module |
| D8 | 現有獨立 D8 DB 與既有 bridge／runtime contract | 不把 D8 tables 併入 Odoo PostgreSQL |
| 憑證 | 切換時重新配置並輪替 | 不把明文憑證寫入意圖場封包、文件或 Git |

融合發生在意圖、路由、狀態、驗證與服務契約層，不發生在 PostgreSQL physical cluster 或資料表的直接拼接層。

## 4. 8D 意圖場重構封包

| 維度 | 本次內容 |
|---|---|
| D1 Intent | 保留有效 Odoo 與 D8 能力，解除對 `taiji_01` home 的執行依賴，最後才允許退休帳號。 |
| D2 State | live container、database、installed module、filestore、addon baseline 與 HOLD 狀態引用。 |
| D3 Coordinate | taiji01 source mounts、taiji_admin target repo、Docker named volume、local-only Odoo endpoint。 |
| D4 Evidence | `docker inspect` 摘要、module state、逐檔雜湊、DB dump hash、filestore archive hash、驗證報告引用。 |
| D5 Execution | 先保存，後形成候選；先離線驗證，後切換；先解除所有 path reference，後刪帳號。 |
| D6 Generative Transmission | 以 canonical packet、reference、lookup、reconstruction condition 與 verifier 重構必要狀態；raw DB／filestore 走受控資料通道。 |
| D7 Risk | database 選擇不一致、Compose authority 缺失、module drift、session、credential、live write 與 rollback 風險。 |
| D8 Envelope | owner authorization、TTL、nonce、SHA-256、來源／目標座標、HOLD／PASS、rollback reference。 |

## 5. 重構層級

### L1 full reconstruction

只適用於封包明確定義完整結果且可做 hash／bit-level 比對的項目：

- 經一致性程序產生的 PostgreSQL logical dump。
- 與該 dump 對應的 filestore 封存。
- 經選定的 addon 原始檔案集合。
- Compose candidate 與設定模板的確定版本。

封包引用 L1 artifact 及其 SHA-256；artifact 本身不因被引用而變成小封包內容。

### L2 equivalent reconstruction

適用於服務效果與治理契約：

- Odoo 只綁定本機 endpoint。
- Odoo 能連到指定 PostgreSQL database。
- 必要 installed module 集合、routes、權限及 filestore relationship 等價。
- D8 維持獨立，既有 gateway／bridge contract 不被改成第二套 server。
- 任務、狀態、控制、效果及 rollback 行為等價，不要求路徑或 byte identity 相同。

### L3 candidate reconstruction

下列內容目前只能是候選：

- 由 live inspect 與現有模板重建的 Compose。
- `wuchang_association_member_trust` 導入 taiji_admin 基線的候選 patch。
- 四個共享但有內容差異的模組融合 patch。
- `wuchang_core` 中 156 個 taiji01-only 檔案的保留／淘汰分類。
- `wuchang_os` 是否保留為可啟動歷史資料庫。

L3 不得自動執行、安裝、升級、切換或封印。

## 6. 融合流程與閘門

### Stage A — authority freeze

- 固定 taiji_admin 程式基線 commit。
- 記錄 live image digest、mount、network、database 與 module state。
- 排除 `.pyc`、cache、session 及 credential literal，不把它們當 source code 融合內容。

### Stage B — exact artifact preservation

- 在明確核准的維護窗口產生 `wuchang_odoo` 與 `wuchang_os` logical dumps。
- 產生一致時間點 filestore archive。
- 建立 SHA-256 manifest，並在不同路徑做 readback verification。
- 保留 Docker named volume，直到新 runtime 驗證及 rollback window 結束。

### Stage C — addon candidate fusion

- 完全相同的三個共享模組沿用 taiji_admin 基線。
- 四個有差異的共享模組逐檔審查 models、controllers、security、views 與 manifest。
- `wuchang_core` 的來源專有檔案先分類為 source、generated、backup、runtime residue 或 unknown；只有 source 且有引用證據者能進候選 patch。
- `wuchang_association_member_trust` 先做 model／ACL／view／dependency 靜態驗證，不自動安裝。

### Stage D — Compose candidate reconstruction

- 以 live inspect 作 current-state evidence，以 taiji_admin Compose 作 proposed-state template。
- 明確選定 `wuchang_odoo`，不得沿用目前 `postgres` 固定值而假裝等價。
- credential 只使用外部 secret reference；不在 command、Compose、packet 或 Git 中保存 literal。
- target path 不再引用 `/home/taiji_01`。

### Stage E — isolated verification

- 使用不衝突的 project、container、network、port 與資料副本。
- 驗證 schema、module import、ACL、route、database selection、filestore relationship、local endpoint 與 rollback。
- 不接 production route，不寫 live DB，不升級 live module。

### Stage F — authorized cutover

Owner 已明確核准停止 live、最終一致性保存、切換、啟動、回復驗證及零依賴後刪除帳號。Stage F 已完成；如 fused runtime 驗證失敗則使用保留的 final-freeze logical dumps、filestore seal 與舊 volume 回復，本次未觸發 rollback。

## 7. 現在的閘門狀態

| Gate | State | 原因 |
|---|---|---|
| read-only inventory | PASS | live container、mount、database 與 module 已核對。 |
| taiji_admin baseline identified | PASS | 現有 repo 與 Compose 已定位。 |
| D8 isolation | PASS | D8 使用獨立 DB／volume／network。 |
| live Compose authority | PASS | repo Compose 已成為 authority，固定 `wuchang_odoo`、外部 mode-600 env、穩定 addon／data path 與 localhost endpoint。 |
| database target equivalence | PASS | Stage C Compose 已固定 `wuchang_odoo`，Stage D 亦成功還原並連線至該 database。 |
| database logical backups | PASS | Stage B 已建立兩個 custom-format logical dumps，並通過 `pg_restore -l` inventory 驗證。 |
| filestore consistency seal | PASS | coordinated final freeze 後，來源與目標 580 個檔案的 SHA-256 manifests 完全一致。 |
| addon runtime compatibility | PASS | Stage D2 在候選 DB 完成四個差異模組 upgrade，124 modules 載入、七個 schema 欄位補齊，內部 HTTP 回應 200。 |
| association ACL policy | PASS | Owner 接受建議政策；Stage E2 候選為 reader `1/0/0/0`、manager 與 admin `1/1/1/1`，3 models／9 ACL 實測通過，manager 尚未指派使用者。 |
| Compose candidate structure | PASS | Stage C 候選使用獨立名稱、內部網路、本機候選 port、外部 credential contract 與 `candidate-only` profile；`docker compose config -q` 通過。 |
| credential isolation | PASS | DB 與 PM3 使用外部 mode-600 production env；既有 rclone／code-server 設定已安全遷移且 Git 無 credential literal。外部供應商端輪替不屬於本機切換證明。 |
| session invalidation | PASS | final freeze 後 target session files 為 0，舊登入與帳號 processes 已終止。 |
| isolated candidate verification | PASS | Stage D2 upgrade 後 schema missing 0、124 modules loaded、兩個 filestore missing 0，candidate internal `/web/login` 回應 200。 |
| isolated rollback verification | PASS | Stage E 將 pre-upgrade dump 還原至暫存候選 DB；凍結來源載入 124 modules、HTTP 200、704 filestore references missing 0，測試資源已清除。 |
| candidate host binding | PASS | promoted Odoo 僅綁定 `127.0.0.1:8069`，`/web/login` 回應 200。 |
| live cutover authorization | PASS | Owner 明確核准 Stage F 並已完成切換及驗證。 |
| runtime path dependencies | PASS | Docker mounts、systemd units、cron 與 active services 對 `/home/taiji_01`／UID 1000 的依賴均為 0。 |
| taiji01 account retirement | PASS | home 已移至受限 evidence payload，process／mount／service／cron 零依賴後，user 與 private group 已刪除。 |

## 8. 封印條件

只有下列條件同時成立，融合結果才可由 `CANDIDATE` 進入 `VERIFIED`：

1. L1 artifact hashes 全部 readback 一致。
2. L2 service contract、module set、database selection 與 filestore relationship 全部等價。
3. 每個 L3 candidate 都有接受或拒絕決定，不存在 unknown source file。
4. 沒有 credential、member plaintext 或 session material 進入 Git／packet／report。
5. target runtime 不再引用 `/home/taiji_01`。
6. rollback 已在隔離環境驗證。
7. Owner 明確核准 live cutover。

Stage F 封印後的正式結論為：

```text
STATE=PASS
decision=Coordinated final freeze, fused live cutover, runtime verification, dependency migration, session invalidation, and taiji01 retirement are sealed.
next=Retain the Stage F evidence and rollback volume through the owner-defined retention window.
```

## 9. Stage B 執行紀錄

- run_id: `TAIJI01_ODOO_FUSION_STAGE_B_20260715T104039Z`
- evidence_root: `/home/taiji_admin/migrated_from_taiji_01_20260715/TAIJI01_ODOO_FUSION_STAGE_B_20260715T104039Z`
- database: `wuchang_odoo` 與 `wuchang_os` logical dumps 已建立，且 `pg_restore -l` 可讀。
- filestore: 580 個來源檔案在封存前後雜湊一致；session 與 cache 未納入。
- addons: taiji01 397 個來源檔案與 taiji_admin 327 個基線檔案已分別封存；Python cache 未納入。
- runtime evidence: 三個 container 結構與三份 Compose 候選已去敏保存。
- live runtime: 未 stop、restart、deploy、upgrade 或切換。

Stage B 完成的是個別 artifact 的保存與驗證。由於沒有協調式 database／filestore freeze，跨 artifact 交易一致性與 live fusion seal 仍為 `HOLD`。

## 10. Stage C 執行紀錄

- candidate_root: `/home/taiji_admin/migrated_from_taiji_01_20260715/TAIJI01_ODOO_FUSION_STAGE_B_20260715T104039Z/candidate_stage_c`
- baseline: Stage B 的 taiji_admin addon artifact，327 個檔案雜湊維持一致。
- source addition: `wuchang_association_member_trust` 七個凍結檔案，雜湊與 Stage B taiji01 evidence 一致。
- merged candidate: 16 個 addon 模組目錄、334 個檔案。
- exclusion: 來源 backup files、Python cache 與 `wuchang_core/wuchang_core` 的 156 檔巢狀重複目錄未進 active candidate。
- shared drift: 四個有差異的共享模組沿用 taiji_admin authority；taiji01 版本只保留在 `source_review` 雜湊證據。
- Compose: `candidate-only` profile、獨立 container／volume／network、local candidate port、internal network、read-only addon mount 與 external credential contract。
- validation: 186 個 Python、16 個 manifest、104 個 XML、association ACL CSV 與 Compose config 靜態驗證通過。
- no runtime mutation: 未建立 candidate container、volume 或 network，亦未 stop、restart、deploy、restore、install、upgrade 或切換 live runtime。

Stage C 已完成可審查的 addon／Compose 靜態融合候選。association ACL 治理風險、Odoo registry 載入、database restore、filestore relationship 與 live cutover 仍為 `HOLD`。

## 11. Stage D 執行紀錄

- run_id: `TAIJI01_ODOO_FUSION_STAGE_D_20260715T105759Z`
- evidence_root: `/home/taiji_admin/migrated_from_taiji_01_20260715/TAIJI01_ODOO_FUSION_STAGE_B_20260715T104039Z/TAIJI01_ODOO_FUSION_STAGE_D_20260715T105759Z`
- database restore: `wuchang_odoo` 680 張 public tables、`wuchang_os` 120 張 public tables，candidate PostgreSQL healthy。
- registry: addon 權限修正採獨立 runtime copy，不降低 frozen evidence 權限；Odoo registry 已載入 124 modules。
- installed state: 8 個 `wuchang_*` modules、3 個 association models、6 個 association ACL records 可由 restored database 查得。
- filestore: `wuchang_odoo` 704 個與 `wuchang_os` 195 個 stored attachments 均無缺檔。
- schema drift: taiji_admin `wuchang_core` 所需的七個 `res_partner` columns 在 restored database 全部不存在，`/web/login` 因此回 HTTP 500。
- host binding: Compose 解析候選 port `28069`，但 internal-only network 下未實際發布；沒有解除 internal network。
- cleanup: candidate containers 與 network 已停止並移除；candidate PostgreSQL volume 保留；private candidate env 保持 mode 600 且不進 evidence manifest。
- live runtime: start time 與 restart count 未改變。

Stage D 證明資料與 filestore 可重建，但程式與 schema 尚未達 L2 equivalent reconstruction。除非另案明確核准 candidate-only Odoo module upgrade／schema migration 及 association ACL policy，禁止進入 live cutover。

## 12. Stage D2 執行紀錄

- run_id: `TAIJI01_ODOO_FUSION_STAGE_D2_20260715T122436Z`
- evidence_root: `/home/taiji_admin/migrated_from_taiji_01_20260715/TAIJI01_ODOO_FUSION_STAGE_B_20260715T104039Z/TAIJI01_ODOO_FUSION_STAGE_D2_20260715T122436Z`
- rollback: module upgrade 前建立 `wuchang_odoo` custom-format dump；SHA-256 為 `91655b32a7f1bea4352d9787f54023c3461f5f28b260f2a01b21333606e6d7c9`。
- runtime compatibility: 只在 Stage D runtime addon copy 移除 `order_website.xml` 不符合本機 Odoo 18 RelaxNG 的巢狀 `<data>` 與 `page="True"`；Stage C frozen candidate 與 repo source 未修改。
- candidate upgrade: `wuchang_core`、`wuchang_cafe_ai_gateway`、`wuchang_google_member_login`、`wuchang_member_registration` upgrade exit 0；124 modules loaded，upgrade log 無 ERROR／CRITICAL／Traceback。
- schema: 七個預期 `res_partner` columns 由 missing 7 變為 missing 0。
- association: 3 models、6 ACL records 維持不變；ACL policy 未在本次授權中變更。
- filestore: `wuchang_odoo` 704 references 與 `wuchang_os` 195 references 均 missing 0、unsafe path 0。
- HTTP: internal-only candidate `/web/login` 回應 200；未發布 host port、未解除 internal network。
- cleanup: candidate containers 與 network 已停止並移除；升級後 candidate PostgreSQL volume 保留。
- live isolation: `wuchang_os_odoo_18` 與 `wuchang_os_pg` 的 start time 及 restart count 前後一致。

Stage D2 已通過 candidate-only schema、registry、filestore、ACL inventory 與 internal HTTP 驗證。整體融合仍維持 `HOLD`，直到協調式最終 freeze、credential rotation、session invalidation、ACL policy 決定、rollback window 與 Stage F live cutover 明確核准完成；不得據此自動刪除 `taiji_01` 帳號。

## 13. Stage E rollback／Stage F preflight 執行紀錄

- run_id: `TAIJI01_ODOO_FUSION_STAGE_E_PREFLIGHT_20260715T124248Z`
- evidence_root: `/home/taiji_admin/migrated_from_taiji_01_20260715/TAIJI01_ODOO_FUSION_STAGE_B_20260715T104039Z/TAIJI01_ODOO_FUSION_STAGE_E_PREFLIGHT_20260715T124248Z`
- rollback restore: Stage D2 pre-upgrade dump 還原至暫存候選 DB，680 tables、704 stored attachments、124 installed modules、8 installed `wuchang_*` modules。
- rollback source: Stage B 凍結 taiji01 addons 共 397 source files；registry 載入 124 modules，internal `/web/login` 回應 200。
- rollback filestore: 704 references、missing 0、unsafe path 0。
- rollback cleanup: 暫存 web container、database、runtime copies 與 internal network 已移除；升級後 candidate volume 保留。
- live parity snapshot: 主 DB 680 tables／704 stored attachments、歷史 DB 120 tables／195 stored attachments；因 live 未停止，這只證明計數一致，不是協調式 final freeze。
- account dependencies: 3 個 live bind mounts 指向 `/home/taiji_01`；帳號仍有 7 個 processes、1 個 login session、linger、user service、code-server 與 2 個 cron entries。
- service dependencies: active／enabled system services 仍引用 retiring user identity、home path、rclone config 或 credential file。
- session／credential: live 有 12 個 Odoo session files；credential 只做非空存在性分類，未讀入報告且尚未輪替。
- live isolation: live Odoo／PostgreSQL start time 與 restart count 前後一致，restart count 皆為 0。

Stage E 的 isolated rollback gate 已轉為 `PASS`。當時 Stage F 仍受 live Compose authority、協調式 final freeze、credential rotation、session invalidation、association ACL policy、path／service dependency 與明確 cutover authorization 阻擋；不得停止 live 或刪除 `taiji_01`。

## 14. Stage E2 association ACL 執行紀錄

- run_id: `TAIJI01_ODOO_FUSION_STAGE_E2_ACL_20260715T124956Z`
- evidence_root: `/home/taiji_admin/migrated_from_taiji_01_20260715/TAIJI01_ODOO_FUSION_STAGE_B_20260715T104039Z/TAIJI01_ODOO_FUSION_STAGE_E2_ACL_20260715T124956Z`
- policy: ordinary internal users 為 read-only；專用 `Wuchang Association Manager` 與 system admin 為 read／write／create／unlink。
- source: 在新的 Stage E2 runtime addon copy 新增 group XML、將 ACL 由 6 增為 9 並把 module version 提升至 `18.0.1.1.0`；未覆寫 Stage C／Stage D 或 repo source。
- rollback: candidate DB upgrade 前建立 custom-format dump；SHA-256 為 `5325f84fcd32ff96b3918f650bd929984f4bbbf839ec7d186f2deb9f799a9e35`，15,406 TOC entries 可讀。
- post-upgrade seal: post-ACL custom-format dump SHA-256 為 `d509597578552ab7448cda7e5cfc1db0f21b9a05fe0894c170e0f784c64367fd`，15,406 TOC entries 可讀。
- upgrade: 只升級候選 `wuchang_association_member_trust`，exit 0、124 modules loaded，upgrade log 無 ERROR／CRITICAL／Traceback。
- effective probe: reader `1/0/0/0`、manager `1/1/1/1`、admin `1/1/1/1`，三個 models 全部符合；manager group assigned users 為 0。
- probe cleanup: temporary users／partners 全部刪除；6 個由 probe 產生且 DB 無引用的候選 filestore files 已精確移除。
- candidate health: internal `/web/login` HTTP 200；filestore 維持 704 references、missing 0、519 physical files。
- cleanup: candidate containers 與 network 已移除；升級後 candidate volume 保留；live start time／restart count 未改變。

Stage E2 已把 association ACL policy gate 轉為 `PASS`。當時 Stage F 仍受 live Compose authority、協調式 final freeze、credential rotation、session invalidation、path／service dependency 與明確 cutover authorization 阻擋；manager 身分不得在未核准名單下自動指派。這些 Stage F 本機閘門的最終結果記錄於下一節。

## 15. Stage F live cutover／帳號退役執行紀錄

- run_id: `TAIJI01_ODOO_FUSION_STAGE_F_20260715T133252Z`
- evidence_root: `/home/taiji_admin/migrated_from_taiji_01_20260715/TAIJI01_ODOO_FUSION_STAGE_B_20260715T104039Z/TAIJI01_ODOO_FUSION_STAGE_F_20260715T133252Z`
- maintenance window: `2026-07-15T13:34:02Z` 開始 final freeze；`2026-07-15T13:34:30Z` 完成 live PostgreSQL freeze。
- final database seal: `wuchang_odoo` dump SHA-256 `05db748921ade3038210f4ad3ffe23745dbdeaaf3dab4b19a45c9fc42075cfb7`；`wuchang_os` dump SHA-256 `f8acbadf0e82dd66607b4a82c53be4a5a360354d6455a48d198d38795804b0b4`。
- final filestore seal: 來源與目標各 580 個檔案，逐檔 SHA-256 manifest 完全一致；target session files 為 0。
- promoted runtime: `wuchang_os_odoo_18` 與 healthy `wuchang_os_pg` 使用融合 addon／data 路徑及外部 candidate volume；Odoo 僅發布 `127.0.0.1:8069`。
- module upgrade: 經核准的五個 module upgrade exit 0；124 modules 載入，log 無 ERROR／CRITICAL／Traceback。
- application verification: `/web/login` HTTP 200；主 DB 696 tables、704 stored attachments、124 installed modules、9 association ACL、預期 schema missing 0；歷史 DB 120 tables、195 stored attachments。
- filestore verification: 主 DB 704 references、歷史 DB 195 references，兩者 missing 0、unsafe path 0。
- service migration: rclone mount、Ollama、edge gateway 與 `code-server@taiji_admin` 均通過 active／endpoint／owner 檢查；缺失來源或依賴的 legacy units 已停用，不作虛假重建。
- account payload: `/home/taiji_01` 原有 32,967,639,990 bytes／97,074 files 已同檔案系統移至 mode-700 evidence payload，ownership 轉為 `taiji_admin`，UID 1000 殘留為 0。
- account retirement: Docker mount、systemd reference、cron reference、UID 1000 process、原 home、user 與 private group 均為 0。
- rollback: final dumps、filestore manifests 與舊 PostgreSQL volume 已保留；promoted runtime 全部 gate 通過，未觸發 rollback。

Stage F 已完成 live 融合與 `taiji_01` 退役。外部服務供應商端 credential 輪替可在其各自控制面另行執行；本機 production 設定已受 mode 600 保護，且不進 Git 或 evidence manifest。
