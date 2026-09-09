# 咖啡館服務員影音 AI 小 J — 2026 參賽候選 Demo

狀態固定為：

```text
STATE=VIRTUAL_CANDIDATE_READY
CANDIDATE=true
CANONICAL=false
ACTIVE=false
DEPLOYED=false
LIVE_EFFECT=false
```

## 用途

這是 8D ADI 完整 AI 應用系統的非生產展示介面。咖啡館是參賽主場景，管委會、協會及個人主權 AI 是同一系統掛載的靜態 Odoo 場景。

Demo 可展示：

- 影像、聲音、網路狀態與設備能力的本機觀測。
- 離散精準索引與高維浮點理解候選的受控融合。
- D1 至 D8 數位腦細胞。
- 動態上下文與最小必要資訊的生成式傳輸。
- 分散式算力及可替換 Gemini／GPT 綁定概念。
- 地震特殊狀態的隔離演練與總場效果閘門。

## 安全邊界

- 不連接正式國家警報。
- 不把演練資料聲稱為 NCDR 或中央氣象署正式訊息。
- 不寫入 Odoo、POS、資料庫或 ADI。
- 不控制瓦斯、電源、門鎖、電梯或其他設備。
- 不上傳影像；只在瀏覽器本機計算短雜湊參照。
- 不做人臉、年齡、性別或人口屬性推論。
- 瀏覽器語音辨識不可用時保持未知，不自動改送雲端。

## 本機啟動

以任一靜態檔案伺服器提供本目錄後開啟 `index.html`。正式掛載時可由既有 Odoo addon 靜態路徑提供，不需要新增 listener 或平行 API。

## 核心檔案

- `index.html`：展示頁。
- `xiaoj_competition.css`：視覺樣式。
- `xiaoj_competition.js`：純瀏覽器候選互動。
- `xiaoj-codex-v2.webp`：既有本機驗證過的自訂 Codex 小 J v2 圖集。
- `sovereign_xiaoj_scene_pack.json`：同一 8D ADI 系統的場景與能力定義。
