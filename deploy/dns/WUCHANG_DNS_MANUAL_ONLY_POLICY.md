# 五常智慧雲｜DNS 手動管理與 Google 非營利資格保護政策

## 核心政策

本系統不得使用 Cloudflare DNS API 自動新增、刪除或修改 DNS 紀錄。

原因：
過去 Cloudflare DNS API 自動化操作曾導致 Google 非營利組織資格或 Google Workspace 驗證狀態發生風險，因此 wuchang.life DNS 必須採人工審核與手動設定。

## 禁止事項

- 禁止使用 Cloudflare DNS API 修改 DNS
- 禁止腳本批量新增 DNS
- 禁止腳本覆蓋 DNS
- 禁止自動修改根網域
- 禁止自動修改 MX
- 禁止自動修改 SPF / DKIM / DMARC
- 禁止自動修改 google-site-verification
- 禁止自動修改 Google Workspace / Google Nonprofits 驗證紀錄

## 允許事項

- 可手動於 Cloudflare Dashboard 新增子域
- 新增前須截圖備份現有 DNS
- 新增後須再次截圖保存
- Google Workspace / Google 非營利相關紀錄不得更動
- Odoo / Gateway / AI / Voice / Admin 子域須優先使用 VPN / Tailscale 內網

## 公開子域

wuchang.life
www.wuchang.life
docs.wuchang.life
business.wuchang.life
property.wuchang.life
fund.wuchang.life
carbon.wuchang.life

## VPN 內網子域

api.wuchang.life
odoo.wuchang.life
ai.wuchang.life
spatial.wuchang.life
voice.wuchang.life
admin.wuchang.life

VPN 子域若使用 Tailscale IP，Cloudflare 必須設為 DNS only，不得 Proxied。

## Final Principle

DNS 是 Google 非營利資格與協會正式網域信任基礎。
五常智慧雲不得以自動化腳本任意修改 DNS。
所有 DNS 變更均須人工審核、手動設定、截圖備份與紀錄存檔。
