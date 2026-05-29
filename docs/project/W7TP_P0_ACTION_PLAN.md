# W7TP P0 行動計畫

## P0-1：確認 missing 是真缺檔還是路徑不一致

目標：先找是否有同名檔存在於其他目錄，而不是立即重做。

只允許：
- find 檔名
- 不讀 secrets/logs/memory/vault/backup
- 不修改檔案

## P0-2：若確認真缺，按順序補檔

順序：
1. Context Cache 三檔
2. Fusion design
3. Fusion 三 schema
4. Fusion 四 mock
5. Fusion dry-run report
6. Redteam v0.4

## P0-3：Open WebUI 3000

目前狀態：
- `127.0.0.1:3000` 無法連線
- docker ps 清單未見 open-webui container
- 先做檔案/compose/volume 位置清查
- 不啟動、不拉 image、不刪容器

## P0-4：Gateway / Claw endpoint

目前：
- Gateway `9002/health` OK
- Gateway `9002/healthz` 404
- Claw Safe `9004/healthz` OK
- Claw Safe `9004/health` 404

決策：
- 先建立 endpoint contract
- 不改服務
