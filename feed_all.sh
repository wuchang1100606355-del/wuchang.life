#!/bin/bash

echo "🌌 [Feed_ALL] 五常大腦全資料流自動餵入程序啟動..."
echo "🔍 掃描整個 Taiji_Hub..."

# 收集所有可讀檔案
FILES=$(find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.json" -o -name "*.md" \))

echo "📦 已找到以下檔案："
echo "$FILES"
echo "🧠 正在合併所有內容..."

CONTENT=""
for f in $FILES; do
    CONTENT+="\n\n===== FILE: $f =====\n"
    CONTENT+="$(cat "$f")"
done

echo "🚀 正在將完整五常 OS 餵入 sister-j-brain..."

printf "%b" "$CONTENT" | ollama run sister-j-brain
