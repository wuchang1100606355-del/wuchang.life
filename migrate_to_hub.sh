#!/bin/bash

echo "================================================="
echo "☯️ [Jules 中樞] 接收神諭：啟動元開發工作區精準搬移..."
echo "================================================="

# 定義維度座標 (來源與目的地)
SOURCE_DIR="/home/taiji_admin/wuchang_8_0_core"
DEST_DIR="/mnt/c/Users/o0930/Taiji_Hub"

# 檢查來源地是否存在
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ [引力異常] 找不到舊核心資料夾 $SOURCE_DIR，請確認路徑！"
    exit 1
fi

echo "🛡️ [架構生成] 正在 Taiji_Hub 內展開標準化防禦陣地結構..."
mkdir -p "$DEST_DIR/keys"          # 存放 GCP JSON、.env 等機密
mkdir -p "$DEST_DIR/data"          # 存放 SQLite 資料庫
mkdir -p "$DEST_DIR/models"        # 存放 Ollama Modelfile 靈魂設定檔
mkdir -p "$DEST_DIR/legacy_core"   # 備份舊版 Python 程式碼供未來查閱

echo "⏳ [資產躍遷] 開始將有價值的實體資料複製至聖地 (Taiji_Hub)..."
# 注意：使用 cp (複製) 而不是 mv (移動)，確保舊資料安全，落實「可猜測但須驗證」

# 1. 搬移金鑰與機密憑證 (Keys)
echo "   -> 正在萃取 [金鑰與環境變數]..."
cp "$SOURCE_DIR"/*.json "$DEST_DIR/keys/" 2>/dev/null
cp "$SOURCE_DIR"/.env "$DEST_DIR/keys/" 2>/dev/null

# 2. 搬移五維知識庫與記憶 (Databases)
echo "   -> 正在萃取 [知識庫與記憶流形]..."
cp "$SOURCE_DIR"/*.db "$DEST_DIR/data/" 2>/dev/null

# 3. 搬移靈魂模型設定檔 (Modelfiles)
echo "   -> 正在萃取 [大腦皮層靈魂模型]..."
cp "$SOURCE_DIR"/*.Modelfile "$DEST_DIR/models/" 2>/dev/null

# 4. 搬移舊版核心代碼 (作為歷史知識庫)
echo "   -> 正在萃取 [舊版奇異點代碼]..."
cp "$SOURCE_DIR"/wuchang_*.py "$DEST_DIR/legacy_core/" 2>/dev/null
cp "$SOURCE_DIR"/taiji_*.py "$DEST_DIR/legacy_core/" 2>/dev/null
cp "$SOURCE_DIR"/sister_*.py "$DEST_DIR/legacy_core/" 2>/dev/null

echo "================================================="
echo "✅ [歸宗完成] 歷史資產已成功分類並降臨 Taiji_Hub！"
echo "⚠️ [維和提醒] 舊的 .venv 結界與過期日誌已無情拋棄，維持大陣純淨。"
echo "================================================="
ls -l "$DEST_DIR"
