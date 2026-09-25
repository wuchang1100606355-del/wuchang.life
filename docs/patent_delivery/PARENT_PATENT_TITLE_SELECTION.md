# Parent Patent Title Selection

CHECK_DATE=2026-06-27
REPO_SCOPE=Taiji_Hub
LEGAL_REVIEW_NEEDED=TRUE

## Recommended Title

用於人工智慧候選運算之八維狀態封包生成、分段傳輸、本地重構與執行驗證方法及系統

## Core Invention Theme

本案母項應聚焦在技術手段，而非單純 AI 平台、社區管理、POS 應用或古數學概念。repo 內已整理出的可支撐母案主題為：

- 以 8D state packet / D8 envelope 表示意圖、座標、證據、執行、隱私、生成式傳輸、資源路由與紅隊邊界。
- 將任務或狀態轉為封包、參照、摘要、清單、查表鍵與重構規則，而非傳送完整原始資料。
- 透過分段傳輸與本地重構，讓遠端或雲端只產生候選運算結果，不取得最終權限。
- 由 Total Field Verifier / verifier gate 檢查封包完整性、權限邊界、證據參照與風險狀態後，才允許輸出、封印或執行。
- 以 local-first governance、hard walls、blinded remote candidate compute 和 evidence chain 維持資料主權。
- 可覆蓋 POS、社區治理、瀏覽器 LLM、OpenWebUI 候選運算、D8 DB、證據鏈與總場/分場治理，但母案題名不直接綁死單一產品場景。

## Scoring Weights

| Criterion | Weight |
| --- | ---: |
| 技術準確性 | 30 |
| 台灣發明專利適配性 | 20 |
| 可涵蓋母案與後續子案 | 20 |
| 避免過度抽象或純商業方法 | 10 |
| 能凸顯技術手段而非效果口號 | 10 |
| 能避開「古數學」單獨作為專利主體的風險 | 10 |

## Title Score Table

| ID | Candidate Parent Title | Accuracy 30 | TW Invention Fit 20 | Parent/Child Coverage 20 | Not Abstract 10 | Technical Means 10 | Avoid Ancient-Math Risk 10 | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| F | 用於人工智慧候選運算之八維狀態封包生成、分段傳輸、本地重構與執行驗證方法及系統 | 29 | 19 | 19 | 9 | 9 | 10 | 95 |
| B | 用於生成式傳輸之八維狀態封包生成、本地重構與驗證執行方法及系統 | 29 | 18 | 18 | 9 | 9 | 9 | 92 |
| A | 用於人工智慧候選運算之狀態封包生成、分段傳輸、本地重構與執行驗證方法及系統 | 28 | 18 | 18 | 9 | 9 | 8 | 90 |
| D | 用於資料主權人工智慧之狀態封包傳輸、查表重構與執行驗證方法及系統 | 27 | 18 | 18 | 8 | 8 | 9 | 88 |
| G | 用於本地優先人工智慧之八維狀態封包傳輸、候選運算隔離與驗證執行方法及系統 | 27 | 18 | 18 | 8 | 8 | 9 | 88 |
| C | 用於人工智慧服務流程之八維狀態封包治理、候選運算隔離與本地驗證方法及系統 | 26 | 17 | 17 | 8 | 8 | 9 | 85 |
| E | 用於本地優先人工智慧候選輸出之八維封包治理與驗證執行方法及系統 | 25 | 17 | 16 | 8 | 8 | 9 | 83 |

## Selection

PRIMARY=用於人工智慧候選運算之八維狀態封包生成、分段傳輸、本地重構與執行驗證方法及系統

BACKUP_1=用於生成式傳輸之八維狀態封包生成、本地重構與驗證執行方法及系統

BACKUP_2=用於資料主權人工智慧之狀態封包傳輸、查表重構與執行驗證方法及系統

## Why This Title Is Best For The Parent Case

主推題名比 A 多出「八維」，可直接銜接 V4_TRUE8D_TIPO_MAIN、8D packet schema、Total Field Verifier 與 D8 envelope 證據；比 B 多出「人工智慧候選運算」與「分段傳輸」，可涵蓋 blinded remote candidate compute、OpenWebUI/browser LLM/POS/cloud candidate 場景；比 C/E 更聚焦封包生成、傳輸、重構、驗證等可申請的技術手段；比 D 不易落入「資料主權」效果口號，仍保留 local-first governance 的技術範圍。

## Taiwan Patent Type Recommendation

PRIMARY_TW_PATENT_TYPE=發明專利

理由：本案核心是方法及系統，涵蓋封包生成、分段傳輸、本地重構、候選運算隔離、查表/證據驗證與執行閘門，較符合發明專利對技術思想、方法、系統與用途的保護範圍。

SECONDARY_OPTION=新型專利只適合在後續存在具體物品形狀、構造或組合時拆出，例如專用邊緣盒、路由裝置、POS 安全橋硬體模組或封包驗證設備。純方法、雲端候選運算、治理流程與軟體協定不宜以新型作為主案。

DESIGN_PATENT=非主線。若後續有可公開的操作介面、圖形化使用者介面或設備外觀，可另評估設計案，但不應承載本案技術核心。

DIVISIONAL_OR_CHILD_CASES=可由專利師評估母案/子案或分割策略：1) 8D 狀態封包與生成式傳輸核心；2) verifier-gated output 與 hard walls；3) cloud blind compute/local authority boundary；4) POS/社區/瀏覽器 LLM 應用；5) D8 evidence ledger 與 post-commit verification chain。

## Naming Guardrails

- 不以「古數學」單獨作為專利主體；若保留其脈絡，只作為內部概念或實施例背景。
- 不使用「AI 系統」「智慧平台」「社區管理系統」等泛名。
- 題名應能支撐「方法及系統」兩類請求項。
- 公開文本不放入 WHY_IT_RUNS lookup details、codebooks、私有治理鏈、未公開營收治理敏感內容、任何 live credential 或 endpoint token。
