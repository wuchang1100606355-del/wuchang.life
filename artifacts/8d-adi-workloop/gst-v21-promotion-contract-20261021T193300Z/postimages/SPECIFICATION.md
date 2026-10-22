# Origin-Cell GST V2.1：Founder 正典規格與總場證據登錄

## 登錄目的與母技術關係

本文件執行 Founder 本輪明示的正典定義與證據登錄指令。母技術為 **W7TP／8D ADI V2.3 單一耦合動態狀態場**；Origin-Cell Generative State Transmission（原胞狀態生成式傳輸，GST）是其 **D6 衍生子能力**。D1–D8 共同約束同一狀態，不是八條獨立管線。

| 耦合維度／角色 | 本輪精確定位 |
|---|---|
| D1 意圖 | Founder 指定 V2.1 定義、四通道唯一標準基線與證據登錄 |
| D2 狀態 | 分開已觀測原件、程式定義、歷史測例、候選及正式權威 |
| D3 座標 | taiji01 主權節點、MSI 探針、美國／巴西節點、精確版本與路徑 |
| D4 證據 | 原有 hash-chain ledger 與 native ADI 唯加證據，不另建權威帳本 |
| D5 執行 | 本輪僅規格、引用及證據登錄；重構 C1 保持 CANDIDATE_ONLY |
| D6 生成式狀態傳輸 | 原胞規則、LUT／模板、冷啟動、暖多工、稀疏修補；擴展版本另綁原件 |
| D7 風險禁錮 | 實作版本與來源完整性、明文秘密、候選越權及不實觀測標籤 |
| D8 封套／權威 | taiji01 既有本地裁決與權威閘門；本文件、模型和雜湊均不自行授權 |

本地 LLM（大型語言模型）、雲端 Gemini／GCP、分散式算力節點可產生或處理候選。能力與算力分散不移交本地正式放行權威。Merchant OS 的 POS、影音、動作與營運應用可使用這個 D6 子能力；重構資料仍須經本地 D8 與既有證據／業務閘門。`Reconstructed != Executed`。本文件不公開 6 位元路由之 64 類秘密命名／權重矩陣；該狀態分類與 64-bit 串流計數是不同的技術欄位。

## 精確程式與證據錨點

```
/home/taiji_admin/Taiji_Hub/runtime/total_field/conversation_intake/universal_origin_cell_codec_v2.py
SHA-256 345af4963feb2fd88c684a96c505aafae63ad46c2c16e5c4dd13722eb3c7a23b

SPARSE_ADI_V21_VERIFIED_20261021.zip
SHA-256 bc8cf05402847c4723bcdb4d822e44ff53335a93cdbf65066658463f8d303c50
```

已核對 taiji01 當前碼源與驗證包中的精確程式。保留前輪已修復並驗證的 256 修補點 `[255,1]` 分批、邊界長度，以及冷包尾綴拒絕／cache 更新原子性；本次登錄不重跑那些已通過階段，也不修改碼源。

## 錨定版本的實際微指令表

| Opcode | 實作符號 | 主要資料欄位 |
|---|---|---|
| `0x01` | `OP_TEMPLATE_SEQ` | LUT／模板識別、列與欄座標、重複次數；uint8 欄位 |
| `0x02` | `OP_LUT_RUN` | LUT 識別／座標 uint8，重複次數 uint16 |
| `0x03` | `OP_LUT_PATTERN_2D` | LUT 識別、段數、列數與段座標／長度 |
| `0x04` | `OP_RAW_REPEAT` | 封包帶入 pattern，pattern 長度 uint8、重複次數 uint16 |
| `0x05` | `OP_RAW_ARITH_2D` | start／step／row length／rows uint8，位元組值模 256 |
| `0x06` | `OP_RAW_LITERAL` | uint16 長度與原文字節 |
| `0x07` | `OP_SPARSE_PATCH` | uint8 修補數，每點 uint16 座標與 uint8 值 |

Founder 指令中的 `OP_SPARSE_PATCH=0x06` 在此精確 SHA 下須校正為 **`0x07`**；`0x06` 已由 literal 使用。這是規格與實作的版本對照，沒有改寫歷史成功結果。每批最多 255 點，256 點拆成 `[255,1]`。motion encoder 的明確上界為 65,535 bytes，超出回報 `HOLD_CHANNEL_EXCEEDS_UINT16_OFFSET_SPACE`；不把此上界誤推為每種 decoder 輸出的共同上限。

| 擴展族 | 本輪登錄範圍 |
|---|---|
| `0x11–0x15` 32-bit | Founder／Gemini 歷史描述保留；不在以上 SHA 的碼源內，須補精確擴展原程式與封包錨點 |
| `0x21–0x25` 64-bit | 保留擴展設計及 5 GiB 檔案實證；美國存在 `us_5gb_test.py`（2,272 B），原碼／指令映射另依讀取證據判定 |

以上主錨點使用完整 channel bytearray／bytes；沒有 64 MB streaming 或 `fsync()` 實作。不得將後續擴展包裝成這個原件已具備的程式。

## 兩項範圍註記結案

### 1. 唯一 V2.1 基線與 Brazil 歷史基線

Founder 指定且本次可重現的 V2.1 標準為 **24,658 B**：C1=6,480、C2=12,288、C3=3,120、C4=2,770。

Cloud Shell 歷史程式的 Brazil 測例實際為 **24,523 B**：C1=6,345、C2=12,288、C3=3,120、C4=2,770。差的 **135 B 全部來自 C1**；C4 長度在兩版相同。Brazil JSON 保留為異地歷史佐證，並標清其 `163eee…b4aa` 指紋對象是 **座標 1500 改成 `0xFE` 的 3,120 B C3**，不是四通道串接檔。

Brazil 舊測例使用 ASCII `RAW_ARITH_2D_3120_64` 與 `0x7F` 修補標記，接收端以程式硬編碼公式生成基底。其 570 B 欄位是報告常數，`BYTE_EXACT_MATCH` 只比較 C3。因此其成功範圍為歷史 C3 稀疏修補演示；V2.1 四通道冷啟動成功另由精確 codec／驗證包支持。

### 2. 冷啟動與接收端狀態依賴

`0x8E` 的 570 B 組成為 **4 B 封頭 + 487 B 壓縮 LUT／模板束 + 79 B 首幀四通道指令**。接收端可無預置資料集 LUT／模板開始，但仍需相容 decoder、Python 與 zlib 執行環境。`0x8D` 的 79 B 暖同步依賴已建立的相容 LUT／模板。

C3 由 `RAW_REPEAT` + `RAW_ARITH_2D` 在本次解碼中建立基底，再由實際 `0x07` 做座標修補；**不讀取前一版完整 C3**。單點修補為 25 B channel，加 2 B mux 封頭後 27 B packet。兩項範圍註記均以這個精確定義結案。

## 三級距實證與證據成熟度

| 級距 | 原始 bytes | 冷／暖 bytes | 本輪可證實的範圍 |
|---|---:|---:|---|
| Tier 1 | 24,658 | 570／79 | taiji01 exact source 與本地限定重建的三個指紋吻合；承接前輪 byte-exact regression。美國端原件與歷史 fsync 時間本輪未取到 |
| Tier 2 | 25,165,072 | 590／99 | 保留 Founder 報告的 hash 與 15.1 ms；32-bit 原碼、美國原件與原始執行紀錄仍待綁定，未自行標為 OBSERVED_VERIFIED |
| Tier 3 | 5,368,709,120 | 478／46 | **美國既存檔存在、大小、原生 sha256sum 已於本輪 OBSERVED_VERIFIED**；冷暖包及 50.85 s／fsync 為歷史報告，分欄保留 |

### Tier 1 指紋

```
raw 24658B  19ca8e115a5e402b9be21b6d914ee0f6775ca8869f145776d3f6243b66e8d8d6
cold 570B  269c30081074ac2d7f660315c742d912b257c40bc15e093f2f3134cf6ba889d4
warm 79B   c4c43e2583c4044caa852bd2dd126d960e02bbdb333e9d899e7462fad809a87e
```

79 B 相對原始資料量縮減 99.679617%，相對此 fixture 的 `gzip -9` 662 B 縮減 88.066465%；570 B 冷包相對原始資料量縮減 97.688377%。各百分比使用對應的分母與封包版本。

### Tier 2 報告指紋（尚待原件綁定）

```
raw 25165072B  89195bec856d9e8fdfaa99272beb027348c03655d84eb4431cc4e08f8c2c7dff
warm 99B       3161b8b1653aa9148e8cfb41679bd016a03ce944bdbb5ee0265a30f6aaaa0e86
```

25,165,072 / 99 = 254,192.646 倍是載荷大小比值；不是本次量到的線路頻寬提升倍數。

### Tier 3 美國原件落盤核對

既有瀏覽器 SSH 指向 `my-j-483304 / us-central1-a / wuchang-us-free-node`。遠端讀取開始時間：**2026-10-21T16:39:56.727554+00:00**（台灣 2026-10-22 00:39:56）。

```
path /home/admin_wuchang_life/US_RECONSTRUCTED_5GB_COMPLEX.bin
size 5368709120
3718f1d9e142658b1f0dfdc835ac3c6d407ed8e443fe33920d071898a5430d07  /home/admin_wuchang_life/US_RECONSTRUCTED_5GB_COMPLEX.bin
```

原生 `sha256sum` 完成後已回讀 `EVIDENCE_US_END` 及正常 shell prompt；使用者新附截圖亦顯示相同結果。本次只讀既有原件，沒有重新生成 5 GiB 檔案。**這是已落盤檔案證據，應保留 OBSERVED_VERIFIED 標註。**

50.85 秒是本輪收到的歷史重構／落盤耗時；由顯示數字計算為 100.6883 MiB/s（四捨五入 100.69）。本次 sha256sum 計時不代替原來的 decoder／fsync 計時；也沒有證據可單憑該速率斷言磁碟物理上限。

## Gemini 歷史承接與鏈路模型

已翻閱旁邊「W7TP 8D ADI Transmission Milestone」Gemini 對話並保存帶來源雜湊的相關摘錄。它描述先前左右視窗各自重構對帳，將真實 TCP／SSH 傳包與 RTT 留為後續測試。5 GiB 測例在該對話被描述為四類高規律週期原胞基元展開；這是設計／歷史陳述來源，不能單獨充當程式或執行證明。

固定 64,000 bit/s、只計 payload 的公式：`seconds = bytes × 8 / 64000`。以下全部標為 **DERIVED_LINK_MODEL**：

| 級距 | 原始 payload 秒 | 冷包秒 | 暖包秒 |
|---|---:|---:|---:|
| 1 | 3.08225 | 0.07125 | 0.009875 |
| 2 | 3145.634 | 0.07375 | 0.012375 |
| 3 | 671088.64 | 0.05975 | 0.00575 |

模型排除傳輸封頭、RTT、重試、decoder 配送、重構與 fsync；Tier2/3 封包大小仍以已標明來源的報告值為輸入。沒有把模型數值寫成跨洋實測速度，也沒有把規律測例比值外推為任意外部檔案的保證。

## 既有總場登錄、回執與執行紅線

本輪沿既有 `CAP_INTERNAL_ORIGIN_CELL_V1` 追加 codec／本規格／內容 manifest 的精確 `source_refs`，保留原 owner、八類 capability、selection tags、D5／D7／D8 與 `canonical=false`。context consumer 只做引用／雜湊／依賴投影，`effect_authorization=NOT_GRANTED_BY_CONTEXT`。

證據沿既有 `services/w7tp_d4_adi_v2_bridge.py` 附加至：

- `runtime/ledger/w7tp_ui_events.jsonl`
- `/home/taiji_admin/W7TP_AUDIT_SNAPSHOTS/w7tp_ui_events_adi_v2.jsonl`

本文件是 Founder 規格及事實登錄輸入。寫入、回讀、preimage／postimage、原始 event hash、ADI correlation 與鏈驗證結果以同目錄 **`CANONICAL_PROMOTION_RECEIPT.json`** 為準。ledger commit 是證據附加，不能冒稱新的 D8 裁決。現行 generic promotion 入口硬綁另一候選；本輪沒有借用或改寫它，也沒有變更母技術正典指標、權威根或發行新簽章。

**C1 = CANDIDATE_ONLY；Reconstructed != Executed。** 測例文字中即使含 `PASS_EFFECT_VERIFIED`，也只是資料內容，不能證明實際 Odoo 交易、核銷或部署已獲權威。

## 可追溯證據

所有登錄來源的相對路徑、byte size 與 SHA-256 列於 `CONTENT_MANIFEST.json`。重點包括 `TIER1_ANCHOR_VERIFICATION.json`、`SCOPE_RESOLUTION.json`、`THREE_TIER_EVIDENCE_MATRIX.json`、`US_TIER3_FRESH_NATIVE_HASH_OBSERVATION.json`、`SCREENSHOT_ATTACHMENT_REFERENCE.json`、`BRAZIL_HISTORICAL_SCOPE_RESOLUTION.json` 及 `CANONICAL_REGISTRATION_ROUTE_REVIEW.json`。資料引用或技術摘要與執行指令分開，外部對話 `instruction_capability=false`。
