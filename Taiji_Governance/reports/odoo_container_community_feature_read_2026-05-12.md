# Odoo 容器社區特徵檔案只讀盤點

日期：2026-05-12  
模式：容器只讀閱讀；未讀取會員資料列；未輸出 secret；未修改 Odoo；未重啟容器  
節點：MSI / WSL native Taiji_Hub  

## 結論

已發現社區特徵的 Odoo 檔案與模組，但目前資料庫中尚未生效。

| 項目 | 結果 |
| --- | --- |
| Odoo container | `wuchang_os_odoo_18` running |
| PostgreSQL container | `wuchang_os_pg` running |
| Odoo bind | `127.0.0.1:8069` |
| DB 名稱 | `odoo`、`postgres` |
| 社區主模組檔案 | 已找到 `wuchang_core` |
| POS 菜單選項模組檔案 | 已找到 `wuchang_cafe_menu_options` |
| Odoo DB 模組狀態 | `wuchang_core=uninstalled`、`wuchang_cafe_menu_options=uninstalled` |
| Odoo 標準 POS/account/product | `uninstalled` |
| 會員明文資料 | 未讀取 |

## 發現的社區特徵 Odoo 模組

### `wuchang_core`

路徑：

- `Taiji_Odoo/addons/wuchang_core/__manifest__.py`
- `Taiji_Odoo/addons/wuchang_core/models/wuchang_matrix.py`
- `Taiji_Odoo/addons/wuchang_core/views/wuchang_views.xml`
- `Taiji_Odoo/addons/wuchang_core/security/ir.model.access.csv`

特徵：

- 模組名稱：`Wuchang Core (0 EPS & Wish Tree)`
- 摘要：五常主權經濟體核心引擎
- 依賴：`base`、`point_of_sale`、`account`
- 模型：`wuchang.wish.project`、`wuchang.bank.clearance`、`wuchang.ai.verification`
- 繼承：`pos.order`
- UI：許願樹基金池、AI 2FA 審核

紅隊判斷：

- 屬於社區治理 / 基金池 / AI 危險操作攔截場景。
- 目前 DB 未安裝，因此是「檔案存在、未生效」。
- 若要生效，必須先通過會計分窗、AI 危險操作人類確認、rollback、audit。

### `wuchang_cafe_menu_options`

路徑：

- `Taiji_Odoo/addons/wuchang_cafe_menu_options/__manifest__.py`
- `Taiji_Odoo/addons/wuchang_cafe_menu_options/models/menu_options.py`
- `Taiji_Odoo/addons/wuchang_cafe_menu_options/views/menu_option_views.xml`
- `Taiji_Odoo/addons/wuchang_cafe_menu_options/security/ir.model.access.csv`

特徵：

- 模組名稱：`WuChang Cafe Menu Options`
- 類別：Point of Sale
- 摘要：POS menu normalization、option groups、price deltas、W5C codes
- 模型：option group、question、item
- 擴充：`product.template`
- 五維碼欄位：`w5c_code`、`w5c_domain`、`w5c_entity`、`w5c_topology`、`w5c_time_state`、`w5c_authority`

紅隊判斷：

- 屬於「主權 AI 商業用 POS 系統」的菜單/選項資料模型。
- 目前 DB 未安裝，因此是「檔案存在、未生效」。
- manifest 依賴 `wuchang_cafe_ai_gateway`，但本次掃描未在 addons 中找到該依賴模組，因此目前不宜直接安裝。

## 容器狀態摘要

| container | 狀態 | 觀察 |
| --- | --- | --- |
| `wuchang_os_odoo_18` | running | Odoo 主場景容器，localhost 8069 |
| `wuchang_os_pg` | running | DB 僅容器網路 |
| `taiji_audit` / `taiji_progress` / `taiji_worklist` / `taiji_syslog` | running | 治理輔助容器 |
| `taiji_voice_gateway` | running | localhost 9201 |
| `taiji_claw_safe` | running | localhost 9004 |
| `open-webui` | running | `0.0.0.0:3000`，需視網路邊界標記 L2 |
| `wuchang_gpu_brain` | running | Ollama 容器，未讀模型內容 |

## 風險表

| 風險 | 等級 | 說明 | 建議 |
| --- | --- | --- | --- |
| Odoo 社區模組未安裝 | L1_near | 檔案已在 addons，但 DB 未生效 | 可先做 dry-run manifest |
| POS 模組依賴缺失 | L2_drift | `wuchang_cafe_ai_gateway` 未找到 | 補齊依賴或調整依賴 |
| Odoo 標準 POS/account/product 未安裝 | L2_drift | `wuchang_core` 依賴未生效 | 不能直接安裝，需先規劃 DB baseline |
| Open WebUI 0.0.0.0 暴露 | L2_drift | 若非受控內網，可能擴大入口 | 建議綁 localhost 或走 VPN/Gateway |
| compose 檔 ports 與實際 bind 不一致 | L1_near | compose 顯示 `8069:8069`，容器實際為 `127.0.0.1:8069` | 啟動前需固定 compose 為 localhost |

## 下一步建議

1. 建立 Odoo 模組生效前 manifest，不直接安裝。
2. 補或確認 `wuchang_cafe_ai_gateway` 模組來源。
3. 建立 Odoo DB baseline：只記模組狀態、DB 名稱、SHA256，不讀業務資料列。
4. 將 `wuchang_core` 的基金池與 AI 2FA 權限分窗對齊會計/公益治理規範。
5. 將 `wuchang_cafe_menu_options` 正式標記為「主權 AI 商業用 POS 系統」菜單選項模型。

## 禁止行為

- 不得直接安裝 Odoo 模組。
- 不得直接改 DB。
- 不得查詢會員、客戶、訂單明細資料列。
- 不得輸出 DB 密碼或容器 env。
- 不得把未生效檔案當成正式營運狀態。
