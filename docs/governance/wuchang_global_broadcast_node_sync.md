# 五常全域廣播與節點同步設計

## 定版
全系統以 W7TP 七維張量封包作為應用層通訊語言。底層仍走 LAN / Tailscale / TCP / HTTP / WebSocket。

## 節點分工
- msi：主控節點、正式工作區、指揮官、9002 Gateway、Odoo、Ollama。
- taiji01：邊緣備援、證據鏈鏡像、社區節點候選。
- msi-win11-in：Windows 宿主、C:\Taiji_Runtime、商用瀏覽器與登入回報。
- Android / iPhone：影音入口、POS/會員端、只送 W7TP 封包。
- penguin：唯讀備援索引。
- wuchang-us-free-node-2：離線雲端肌肉候選。

## 同步原則
同步文件、規則、封包、報告；不同步 secret、DB volume、token、private key、client_secret。

## 命令原則
全域廣播可自動產報告；跨節點命令先乾跑。正式執行需本人確認。
