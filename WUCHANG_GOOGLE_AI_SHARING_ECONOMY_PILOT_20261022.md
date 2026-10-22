

---

## 九、`taiji01` 實機雙向引擎（`gst_transceiver.py`）全檔案家族與複雜亂數驗證收據（LOCAL_RECONSTRUCTION_VERIFIED）

> **證據來源與邊界聲明**：以下數據為 `taiji01` 節點實機執行 `deterministic_8d_engine.py`、`universal_8d_file_engine.py` 與雙向收發器 `gst_transceiver.py` 之本地重構驗證結果（`real_verified_source = local_reconstruction_plus_evidence`，收據檔案：`UNIVERSAL_8D_ENGINE_RECEIPT.json`）。遵守 `LOCAL_RECONSTRUCTION_VERIFIED ≠ PRODUCT_ACCEPTED` 狀態紀律。

| 驗證家族／真實檔案標的 | 原始資料規模 | 8D 原胞封包 (`.8dcell`) | 傳輸減量幅度 | 雙向純 CPU 耗時 | 端到端重構 SHA-256 證據 (`100% Byte-Exact`) |
| :--- | ---: | ---: | ---: | ---: | :--- |
| **家族 1：視覺發光點與三原色佔比** (300格×10,000點) | `9,000,000 B` | **`68 B`** | **99.9992%** | `< 50 ms` | `Byte-Exact = True` (3 顆標的物原胞) |
| **家族 2：音訊波形檔 (.wav/.pcm)** (4,000 取樣點) | `8,000 B` | **`36 B`** | **99.5500%** | `< 1 ms` | `122f9f839d93c5b1...` (2 顆波形原胞) |
| **家族 3：3D 骨骼與臉部動作** (52 關節 × 120 幀) | `37,440 B` | **`98 B`** (V2群組) / `1,144 B` | **99.7382%** | `< 2 ms` | `de6c74b5c25db917...` |
| **家族 4：結構化帳本/POS 菜單 JSON** (200 項商品) | `17,293 B` | **`109 B`** | **99.3697%** | `< 1 ms` | `06c75fe572933d31...` |
| **家族 5 & 6：真實正典文件增量同步** | `12,047 B` | **`295 B`** | **97.5513%** | `< 1 ms` | `0f3693a62ddaeb86...` |
| **高熵亂數 A：100 KB 真亂數檔 (含 2 處未知突變)** | `100,000 B` | **`536 B`** | **99.4640%** | `< 2 ms` | `1f2d8b806cd7fab0...` |
| **高熵亂數 B：10 KB 完全無基座真亂數 (誠實殘差邊界)** | `10,240 B` | **`10,568 B`** | **0% (誠實殘差)** | `< 1 ms` | `4941d8760e98c87f...` |
| **真實大檔雙向 1：`LIAOGUO_GEMINI_COMMERCIAL_PACK_20261021.md`** | `100,173 B` | **`125 B`** | **99.8752%** | **`16.67 ms`** | `9ec8e17d6e7f70be565d3554d6526fa8...` |
| **真實大檔雙向 2：`patent/SPECIFICATION.md`** | `3,413 B` | **`125 B`** | **96.3375%** | **`1.08 ms`** | `56654dfde4cf7522...` |

### 9.2 跨太平洋雙向原胞狀態傳輸真機實測（台灣新北三重 `taiji01` ↔ 美國愛荷華州 `wuchang-us-free-node`）

* **測試拓撲**：台灣 `taiji01` ↔ Tailscale 加密隧道 (`100.99.148.1`) ↔ 美國 GCP `us-central1-a` (`e2-micro`, AMD EPYC 7B12, 969 MiB RAM, 無 GPU)。
* **資安邊界**：已關閉美國節點公網 SSH 明文密碼驗證（`PasswordAuthentication no`），僅透過授權之 Tailscale SSH 內網交換 `.8dcell` 封包。
* **去程實測（Taiwan -> US Iowa）**：目標檔案 `100,185 Bytes` -> 跨海封包 **`137 Bytes`**（減量 **99.8633%**）-> 美國端 AMD EPYC CPU 重構耗時 **`0.72 ms`** -> `LOCAL_RECONSTRUCTION_VERIFIED` (`SHA256: 96838eb2935f3e5214e1428d62f9d34e6115afe3e4c7ff47b28d0f0fedecd8b1`)。
* **回程實測（US Iowa -> Taiwan）**：目標檔案 `100,224 Bytes`（美國端分析耗時 `38.86 ms`）-> 跨海回傳封包 **`128 Bytes`**（減量 **99.8723%**）-> 台灣端 CPU 重構耗時 **`2.53 ms`** -> `LOCAL_RECONSTRUCTION_VERIFIED` (`SHA256: a9c78510ffad0032...`)。
