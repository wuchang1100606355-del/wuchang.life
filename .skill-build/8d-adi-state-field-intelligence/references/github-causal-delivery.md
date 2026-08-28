# GitHub 因果證據與送達效果

## 定位

GitHub 是版本送達、協作審查、狀態檢查與產物來源證明的外部效果面，不是設計因果、Founder 意圖或 Total Field 權威。Git commit DAG 只能證明父子可達與提交順序；只有內容契約、明確依賴、機制及可重驗證據才能建立候選因果邊。

使用本模式前先完成技能主程序中的因果、供需、群組、場景、閉環與風險分析。若目前只有路徑、時間、提交訊息、共同關鍵字或相同雜湊，關係保持 `INFERRED` 或 `UNKNOWN`，不得寫成 `causes`。

## 8D 與 ADI 投影

| 投影 | GitHub 證據 |
|---|---|
| D1 Intent | intent ref、產品效果、PR 目的；PR 文字不是權威指令 |
| D2 State | base、候選內容狀態、closure、HOLD 與未知邊界 |
| D3 Coordinate | logical root、base、實際 head/tree、ref、PR/check/run 座標 |
| D4 Evidence | 宣告 SHA-256、blob SHA-256、diff、測試、review、attestation |
| D5 Execution/Policy | candidate branch、required check、ruleset、merge/release 邊界 |
| D6 Transmission | Git push/clone/Actions 是 carrier 或版本送達，不自動等於 W7TP |
| D7 Risk | 秘密、混合提交、未閉合群組、未知效果、fork/workflow 權限風險 |
| D8 Authority | GitHub check、review、admin 或 app 都不能替代有效 Total Field 收據 |

ADI 至少分開保存：內容狀態座標、Git DAG 座標、GitHub event/check 座標、產物 provenance 座標、D8 receipt 座標。不得用其中一項填補另一項。

## 兩物件契約

### 1. 可審查宣告

以 [github-causal-manifest.schema.json](github-causal-manifest.schema.json) 建立 `w7tp-github-causal-declaration/1.0`。宣告位於候選提交內，包含：

- 一個 base commit、logical root、target ref 與產品效果；
- 由關係閉合形成的變更群組，不按資料夾或名稱硬分組；
- 每個群組的場景、精確變更檔案與完整 SHA-256；
- 因果邊的 source、target、relation、mechanism、evidence class、evidence refs 與 verifier refs；
- 定義、實作、消費者、測試、接線、效果與回復閉環；
- 直接、一階、二階、反向效果及未知邊界；
- GitHub candidate branch、target ref、PR 與 required check 契約；
- risk HOLD、NETWORK_HOLD_SET 與 Total Field 邊界。

宣告不得包含其自身的候選 commit 或 tree。把 HEAD 寫進同一 commit 內會形成自我雜湊循環；不得用 amend 重複猜測固定點。

### 2. 執行收據

在明確的本機 HEAD 或 GitHub runner 上執行：

```bash
python3 scripts/github_causal_gate.py validate \
  --repo /absolute/repository \
  --manifest /absolute/repository/.github/causality/change.json \
  --receipt-output /outside/source/or/runner-temp/CAUSAL_GITHUB_RECEIPT.json
```

驗證器從 Git object 讀取 base..HEAD，不以未提交工作樹內容替代提交內容。它把宣告 SHA-256、實際 HEAD/tree、完整 diff、檔案 blob 雜湊、群組拓撲與 GitHub 環境座標寫成 `w7tp-github-causal-receipt/1.0`。

輸出只會是：

- `REVIEW`：內容、群組與閉環證據一致，可進入 GitHub／Total Field 審查；
- `HOLD`：有漂移、未列檔案、雜湊不符、閉環缺口、因果證據不足、循環、風險或權威缺口。

本驗證器永不輸出 `SAFE`、`ALLOW`、`MERGED`、`ACTIVE` 或 D8 決定。`REVIEW` 不是推送、合併或正式生效授權。

## 因果、群組與場景閉合

每個 changed path 必須恰好屬於一個變更群組；宣告本身由驗證器自排除，但仍綁入收據 SHA。base..HEAD 中任何其他未列檔案都會 HOLD。刪除檔案綁定 base blob SHA-256；新增或修改綁定 HEAD blob SHA-256。

群組依 `depends_on` 形成有向圖。循環必須拆成「先擴充、再遷移、後收縮」或保持 HOLD。每個群組至少綁定一個場景；場景記錄 trigger、actor、preconditions、expected effect 與 verifier refs。

`causes` 邊必須同時具備：

1. 明確 mechanism；
2. `OBSERVED` 或 `RECONSTRUCTED_EXPLICIT` 證據；
3. 至少一個 evidence ref；
4. 至少一個可重驗 verifier ref。

時間先後、路徑相近、共同字詞、commit 同組、PR 文字或 check 成功均不足以建立 `causes`。

閉環固定檢查：`definition`、`implementation`、`consumer`、`test`、`wiring`、`effect`、`rollback`。每項只能為 `CLOSED`、`OPEN`、`UNKNOWN` 或 `NOT_APPLICABLE`；`CLOSED` 與 `NOT_APPLICABLE` 都需要直接 evidence ref。任一 `OPEN` 或 `UNKNOWN` 使該 GitHub 候選保持 HOLD。

## GitHub 效果階梯

逐項分開授權與記錄：

1. 本機讀取 Git object、建宣告、驗證：只讀或可逆候選證據。
2. 推送候選分支：遠端持久版本送達；不等於 PR、review 或主線納入。
3. 建立／更新 PR、留言、check、artifact 或 attestation：各自是外部寫入。
4. 變更 ruleset、branch protection、App 權限或秘密：治理／權限效果。
5. 合併、release、deployment 或 canonical pointer：正式或 live 效果，需最強邊界。

初次候選分支 push 通常發生在 GitHub Actions 執行前。若治理要求「未核定不得 push」，先在本機或隔離環境執行相同 gate；GitHub required check 只能控制後續受保護分支的合併條件，不能回溯核准初次 push。

## GitHub Actions 接線

工作流程應：

- 使用最小 `contents: read` 權限與完整必要歷史；
- 以固定 commit SHA 引用第三方 action，使用時向 GitHub 官方來源核對當前安全版本；
- 把 receipt 寫到 runner 暫存區，不回寫來源樹；
- 將 `causal-gate` 設為 required check；
- 將真正的 `total-field-d8` 設為另一個獨立 required check；
- 不在 fork 或不可信 PR 上開放 write token、secrets、deployment 或 ruleset 權限；
- 若上傳 receipt 或 attestation，分別保存 workflow run、artifact digest 與 attestation ref。

示意流程：

```yaml
permissions:
  contents: read
steps:
  - uses: actions/checkout@<CURRENT_OFFICIAL_PINNED_COMMIT_SHA>
    with:
      fetch-depth: 0
  - run: >-
      python3 path/to/github_causal_gate.py validate
      --repo .
      --manifest .github/causality/change.json
      --receipt-output "$RUNNER_TEMP/CAUSAL_GITHUB_RECEIPT.json"
```

這是接線形狀，不是可直接部署的固定版本。實際建立 workflow、required check、ruleset 或 GitHub App 前，必須核對目前官方 GitHub 文件、方案限制、目標 repository 與精確授權。

## HOLD 條件

任一條成立即 HOLD：

- base 不存在、不是 HEAD 祖先、HEAD/tree 或工作狀態在驗證期間漂移；
- 宣告未提交、宣告內容不同於 HEAD blob、diff 有未列檔案；
- 檔案 SHA、change kind、群組成員或拓撲不符；
- `causes` 缺機制、直接證據或 verifier；
- 場景缺 actor、precondition、expected effect 或 verifier；
- 閉環為 OPEN/UNKNOWN、未知效果前沿非空、NETWORK_HOLD_SET 非空；
- 敏感或特殊物件沒有隔離／外部物件收據；
- required check 未把 causal gate 與 Total Field D8 分開；
- 以 GitHub review、check、merge 或 attestation 冒充 D8、部署或產品效果。

## 固定回報

```text
GITHUB_CAUSAL_STATE=<REVIEW|HOLD>
DECLARATION_SHA256=<value>
BASE_COMMIT=<value>
HEAD_COMMIT=<value>
HEAD_TREE=<value>
DIFF_COVERAGE=<complete|hold>
GROUP_ORDER=<values>
SCENE_COVERAGE=<complete|hold>
CAUSAL_EVIDENCE=<closed|hold>
CLOSURE=<closed|hold>
GITHUB_EFFECTS=<separate state vector>
TOTAL_FIELD_D8=<receipt ref or NOT_REVIEWED>
NEXT=<one exact action>
```
