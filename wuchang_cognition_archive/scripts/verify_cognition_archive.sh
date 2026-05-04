#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "===== 五常智慧雲認知存檔檢查 ====="
find . -type f | sort

echo
echo "===== 關鍵詞檢查 ====="
grep -RIn "小 J\|Sister J\|AI 小腦\|AI 海馬迴\|五維碼度規碳帳本\|開發期間\|非正式營運\|始祖開發平台\|本人度量規則\|雙層可究責\|無明文\|物理封存\|五常社區資訊發展基金" . || true

echo
echo "===== SHA256 ====="
find . -type f ! -path "./evidence/*" -print0 | sort -z | xargs -0 sha256sum
