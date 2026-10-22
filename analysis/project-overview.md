# Taiji_Hub 程式庫總覽（第一階段）

- 查核節點：taiji01；觀測區間：2026-10-09 14:02–14:06（Asia/Taipei）。
- 工作目錄：`/home/taiji_admin/Taiji_Hub`。
- Git 分支：`codex/current-live-state-consolidation-20260915`；觀測 HEAD：`3c2e5884bc149ffbb02d81fdf288506918fae79e`。
- 範圍：既有索引、明示正典指標、核心程式入口與有限本機健康探測；未全面逐檔審查、未執行測試、未改動程式、未部署。
- 變更保護：觀測時有 28 個已追蹤但未提交修改（`git status --porcelain -uno`）；未追蹤項目不包含在該數字。
- 分類：`READ_ONLY_SOURCE_ARCHITECTURE_REVIEW`；本文件為分析，不是 D8（封套／權威）正式裁決。

## 工程基準與版本

- 正式定義遵循 Founder 的 W7TP／8D ADI V2.3：八維是八合一單一動態狀態場，不是八步流程或八個固定欄位。
- `runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json` 宣告 `W7TP_8D_ADI_V2_3`、`ACTIVE_CANONICAL`、版本 `2.3`。
- 指標指向 `manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json`，其契約註明 Founder 授權、Total Field 審查及禁止模型自我提升權威。
- `runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_CANONICAL.json` 宣告 `ACTIVE_TRUE8D_V23`；`ACTIVE_PRODUCT_SYSTEM_ROOT_POINTER.json` 指定同 lineage（沿襲鏈）產品根。
- `Taiji_Governance/candidates/t007_v23_global_successor_20261002T124541Z/global_closure_20261004T2248Z/TOTAL_FIELD_GLOBAL_CLOSURE_REGISTRATION.json` 為 T-007 歷史閉合登錄；本次僅複核其引用之現行檔案。
- 本次 SHA-256（安全雜湊演算法）檢查：正典指標 `74752efc...`、產品指標 `53411d0e...`、全節點場 `3faa27ef...`、路由場 `3b3d64bd...`、Total Field 權威檔 `990f06c9...`，與上述歷史閉合登錄所列一致；一致不等於 runtime／端到端效果驗收。

## 程式庫領域地圖（依功能，不是新核心）

| 區域 | 可直接定位的用途 | 來源 |
|---|---|---|
| `runtime/total_field/` | 正典、權威、Current Field、收據與工作狀態的現存工件 | 現行指標與 `active/` |
| `services/gateway/` | FastAPI（Python 非同步網頁介面）閘道、服務路由、治理自然語言控制器 | `main.py`、`natural_language_control.py` |
| `services/w7tp_native_adi/` | 原生 ADI（時空狀態索引資料庫）服務、索引／封包／重構介面 | `service.py`、`core.py` |
| `services/w7tp_gst_v23_runtime.py` | V2.3 生成式狀態傳輸的契約／規則檢查與交付入口 | 同名 Python 檔 |
| `tools/total_field_dynamic_context_pull.py` | 指標優先 Dynamic Context（動態上下文）拉取及本地暫態重構 | 同名 Python 檔 |
| `core/`、`tools/w7tp_local_model_agent.py` | 本地模型路由、資源決策與可用工具候選 | `core/msi_local_llm_route.py`、`core/resource_arbitration.py` |
| `Taiji_Odoo/` | Odoo 18 容器定義、PostgreSQL（關聯式資料庫）15 與業務附加模組 | `docker-compose.yml`、`addons/` |
| `products/wuchang_xiaoj_community/` | 小J社區服務隔離候選產品介面 | `README.md`、`src/` |
| `docs/`、`Taiji_Governance/` | 既有工程文件、候選、審核證據及治理資訊 | 現存目錄及 T-007 登錄 |

## 規模（狹義實測）

- `git ls-files` 追蹤檔案 3,865 個；不等於磁碟上全部檔案。
- `Taiji_Odoo/addons/` 下直接子目錄 16 個；目錄存在不等於模組已安裝、啟用或完成驗收。
- `tests/` 下 `test_*.py` 166 個；未實際運行，因此沒有新的測試通過結論。

## 設計／安裝／即時運作界限

- 原始碼明示 Gateway 路徑 `services.gateway.main:app`；`systemd/taiji-gateway.service` 定義本機 8081。
- 在 2026-10-09 約 14:05，本機只讀健康探測：`127.0.0.1:8081/health` HTTP 200；`8082/healthz` HTTP 200；`9110/health` HTTP 200。
- Odoo Compose 宣告僅綁定 `192.168.50.249:8069`，在該 LAN（區域網路）位址 `GET /web/login` 為 HTTP 200；不能因 localhost:8069 無回應而判斷 Odoo 離線。
- `9110` 的程序 PID 1557 處於 `/user.slice/user-1002.slice/user@1002.service/app.slice/w7tp-native-adi.service`；系統層 `systemctl` 同名單元 inactive，不能以其代替使用者層服務觀測。使用者層 manager 此工作階段未取得可讀狀態。
- `8099` localhost 本次探測無法連線；僅此目標／座標無法確認，不推廣為整個 runtime 失效。
- `127.0.0.1:11435` 在 taiji01 沒有本機回應，不足以推論 MSI 的橋接模型不在線。

## 已知限制

- `SYSTEM_CURRENT_STATE.md`、`AI_BOOTSTRAP.json` 等含較早 MSI／MTL-AI 假設；只能作歷史入口，不可蓋過當前 V2.3 指標。
- 小J候選 README 明示不接正式 Odoo API、模型或部署；候選介面不可當成正式商業上線。
- 後續以最小範圍追查呼叫鏈與重要介面語義；避免再造核心、擴張權威、重做 T-007。

## 續讀

- 呼叫關係與候選疑點：`architecture-analysis.md`。
- 任務續接與階段狀態：`codebase-analysis-progress.md`。
