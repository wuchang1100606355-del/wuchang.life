# Windows Drive spool projector（W7TP GT Mesh v2.1）

此元件把本機 append-only spool 中的單檔 JSON envelope 投影到**既有**的
`J:\...\8D_ADI_INDEX`。它只建立 bytes 投影與收據，不讀取 Git，也不把 Drive、
Git 座標、receipt、檔名、時間或 hash 升格成 authority 或 live effect。

## 固定邊界

- Python standard library only。
- spool 預設：`%LOCALAPPDATA%\W7TP\gt_mesh_v21\drive_spool`。
- 本機 immutable receipts 預設：`%LOCALAPPDATA%\W7TP\gt_mesh_v21\receipts\<receipt_id>.json`。
- spool envelope 永不刪除、搬移或覆寫。
- 已成功 receipt 綁定的 spool 檔名若之後呈現不同 bytes，立即 HOLD，不投影新內容。
- Drive 檔案使用 exclusive create；目標已存在時逐 bytes 相等才接受。
- 程式不刪除或覆寫任何 Drive 檔案；寫入中斷時保留 HOLD，不做清理。
- Drive root 與第一層 allowlist 分區都必須已存在；程式只可在既有分區下建立子目錄。
- setup 會在建立 receipt 目錄前先證明其位於 Drive root 外；錯誤座標不會造成 Drive 誤寫。
- 成功投影會建立本機 immutable `CLOUD_WRITE_RECEIPT`，再把完全相同的 receipt bytes
  以 exclusive create 寫到 `08_RECEIPTS/CLOUD_WRITE_RECEIPT_<receipt_id>.json`。
- receipt 直寫到 `08_RECEIPTS`，不建立新 spool envelope，避免 receipt 遞迴。

允許的第一層分區：

```text
00_CONTROL
01_NODE_INDEX
02_FILE_INDEX
03_LINEAGE
04_EVIDENCE
05_CONFLICT
06_RECONSTRUCTION
07_GITHUB
08_RECEIPTS
99_QUARANTINE
```

`07_GITHUB` 只接受 D4 evidence 投影；artifact 必須精確包含：

```json
{
  "dimension": "D4_EVIDENCE",
  "authority_state": "EVIDENCE_ONLY",
  "live_effect_state": "NOT_ESTABLISHED_BY_GIT"
}
```

其他欄位可存在，但上述三個 gate 不得缺少或改值。

## Envelope v2.1

spool 可使用 producer 的巢狀分區樹；projector 會遞迴讀取每個 `*.json` envelope，
但不跟隨 symlink/reparse directory。每個 envelope 欄位必須恰為：

```json
{
  "schema_id": "W7TP_DRIVE_PROJECTION_ENVELOPE_V21",
  "projection_relative_path": "04_EVIDENCE/example.json",
  "artifact_sha256": "<canonical artifact bytes 的 lowercase SHA-256>",
  "artifact": {"example": true},
  "source_node_ref": "<opaque node reference>",
  "packet_id": "<packet id>",
  "logical_time": 1,
  "created_at": "2026-08-29T12:00:00+08:00",
  "envelope_sha256": "<排除 envelope_sha256 後的 canonical SHA-256>"
}
```

Canonical JSON 固定為 UTF-8、Unicode NFC、key 排序、compact separators、禁止
NaN/Infinity。artifact 寫入 Drive 的 bytes 就是這組 canonical bytes，不加換行。

`projection_relative_path` 必須是 NFC POSIX relative path；禁止 absolute path、`..`、
backslash、Windows device name、ADS colon、reparse/symlink escape，以及非 allowlist
第一層。spool 不可投遞 projector 保留的
`08_RECEIPTS/CLOUD_WRITE_RECEIPT_*.json`。

## Windows 啟動

先由治理或操作者提供**精確且已存在**的 Drive root；程式不猜測省略的 `...`：

```powershell
& '<projector-dir>\start_drive_spool_projector.ps1' `
  -DriveRoot 'J:\<既有路徑>\8D_ADI_INDEX'
```

持續監看：

```powershell
& '<projector-dir>\start_drive_spool_projector.ps1' `
  -DriveRoot 'J:\<既有路徑>\8D_ADI_INDEX' `
  -Watch -PollSeconds 5
```

若作為登入啟動項，Windows Task Scheduler 的 action 可設為：

```text
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "<projector-dir>\start_drive_spool_projector.ps1" -DriveRoot "J:\<既有路徑>\8D_ADI_INDEX" -Watch
```

Task 可設「At log on」並在失敗時重新啟動；Drive 尚未掛載或任何第一層分區缺失時，
projector 會 `HOLD_SETUP`／`HOLD_PROJECTION` 退出或持續回報，不會自行建立 Drive root。

直接執行：

```powershell
py -3 .\drive_spool_projector.py `
  --drive-root 'J:\<既有路徑>\8D_ADI_INDEX'
```

程序 exit code：`0` 代表本輪全部 bytes 投影已建立或已確認同 bytes；`2` 代表至少一個
envelope HOLD；`3` 代表啟動座標不安全或缺失。`0` 不代表 authority、activation、
deployment 或 live effect。

## 測試

```powershell
py -3 -m unittest discover -s .\tests -v
```

測試只使用 temporary directories，不需要 J: 或網路。
