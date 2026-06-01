#!/usr/bin/env bash
set -euo pipefail

cd ~/Taiji_Hub

PROJECT_NAME="wuchang-homepage"
SITE_DIR="site/wuchang_homepage"
TS="$(date +%Y%m%d_%H%M%S)"

echo "===== 五常智慧雲首頁部署：不修改 DNS ====="
echo "Project: $PROJECT_NAME"
echo "Site: $SITE_DIR"
echo "Policy: NO Cloudflare DNS API, NO DNS mutation"

if ! command -v wrangler >/dev/null 2>&1; then
  echo "wrangler 未安裝，開始安裝..."
  npm install -g wrangler
fi

test -d "$SITE_DIR" || {
  echo "找不到 $SITE_DIR"
  exit 1
}

mkdir -p logs wuchang_cognition_archive/deploy wuchang_cognition_archive/evidence

echo "===== SHA256 before deploy ====="
sha256sum "$SITE_DIR/index.html" "$SITE_DIR/assets/css/style.css" | tee "logs/wuchang_homepage_sha256_${TS}.txt"

echo "===== Deploy to Cloudflare Pages only ====="
wrangler pages deploy "$SITE_DIR" \
  --project-name "$PROJECT_NAME" \
  --branch main \
  | tee "logs/wuchang_pages_deploy_${TS}.log"

cat > "wuchang_cognition_archive/deploy/WUCHANG_PAGES_NO_DNS_DEPLOY_${TS}.txt" <<EOF
【五常智慧雲｜首頁部署紀錄】

部署方式：
Cloudflare Pages / wrangler pages deploy

部署專案：
$PROJECT_NAME

部署目錄：
$SITE_DIR

DNS 政策：
不使用 Cloudflare DNS API。
不修改任何 DNS。
不修改 MX / SPF / DKIM / DMARC。
不修改 Google Workspace / Google Nonprofits 驗證紀錄。
不新增或覆蓋 wuchang.life 子域。

目前狀態：
開發期間、原型驗證期間、公益實證準備期間，非正式營運期間。
EOF

sha256sum \
  "logs/wuchang_homepage_sha256_${TS}.txt" \
  "logs/wuchang_pages_deploy_${TS}.log" \
  "wuchang_cognition_archive/deploy/WUCHANG_PAGES_NO_DNS_DEPLOY_${TS}.txt" \
  > "wuchang_cognition_archive/evidence/SHA256_WUCHANG_PAGES_NO_DNS_DEPLOY_${TS}.txt"

echo "✅ 部署完成：只更新 Pages，不修改 DNS"
echo "請查看 logs/wuchang_pages_deploy_${TS}.log 取得 pages.dev URL"
