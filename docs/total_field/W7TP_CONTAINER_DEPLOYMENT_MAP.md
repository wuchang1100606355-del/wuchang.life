# W7TP Container Deployment Map (Min Source Only)

STATE=W7TP_CONTAINER_DEPLOYMENT_MAP_LOCKED
AUTHORITY=LOCAL_HOST_TAIJI01
NATURE=SOURCE_DOCUMENTATION_ONLY
EXECUTION_CAPABILITY=NONE

## 1. 物理隔離原則 (Air-Gap Principles)
本對映圖僅為拓樸紀錄。W7TP 總場嚴格遵守「容器非權威」原則：
* 容器（Docker/LXD）僅為執行與隔離載體（Execution Vessels）。
* 所有的 8D 狀態驗證、金鑰管理、源碼庫（Taiji_Hub）與最終決策，皆鎖定在 Host OS (Taiji01) 或特定實體節點。
* 容器內禁止存放未加密的 Master Keys 或進行跨界權威越權。

## 2. 核心容器拓樸 (Core Container Topology)

### 2.1 總場資料庫 (Total Field D8 Database)
* **Container Name:** taiji_d8_db
* **Status:** Up (Healthy)
* **Role:** PostgreSQL 資料庫載體。負責儲存 Odoo 商業邏輯與 8D/7D 狀態場資料。
* **Network Boundary:** 僅允許 Host 與 Odoo 容器內部橋接，禁止外部直接存取。

### 2.2 商業後端與運算引擎 (Business & Computing Engine)
* **Container Name:** wuchang_os_odoo_18
* **Status:** Up (Running)
* **Role:** Odoo 18 核心應用、AV 點餐 AI 邏輯、商業後端最佳化模組載體。
* **Network Boundary:** 對內橋接 taiji_d8_db，對外接受 Dispatcher 或特定 Proxy 傳入的已驗證封包。

### 2.3 隔離檢疫區 (Quarantine Zone)
* **Container Name:** quarantine_wuchang_os_pg_20260508_200520
* **Status:** Up (Isolated)
* **Role:** 舊有資料或具風險之狀態庫，物理封存在檢疫區，僅供 Audit 或回滾參考，不參與主線自動化。

## 3. 跨節點映射 (Cross-Node Edge Mapping)
雖不在 Taiji01 容器池內，但隸屬總場治理的邊緣實體：
* **Taiji03 (Edge VM):** Windows WSL Ubuntu 環境，作為前端固定 IP 承接點 (HTTP P0)。
* **Router (RT-BE86U):** 負責 NAT 轉發 (TCP 80 -> 192.168.50.150)，擔任公網火力接觸的第一道物理閘門。

## 4. 防禦性限制 (Defensive Constraints)
* **Deploy 限制:** 任何針對上述容器的 docker-compose up, docker restart, docker rm 動作，均必須通過 taiji_8d_canonical_verifier.py 驗證與人類 (Super Admin) 實體批准。
