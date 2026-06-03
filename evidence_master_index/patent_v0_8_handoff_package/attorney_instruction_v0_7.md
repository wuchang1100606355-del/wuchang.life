# Patent Attorney Instruction v0.7

## 案件定位

本案請以「跨系統人工智慧任務執行治理系統及方法」審查，而非以一般 AI Agent、RAG、intent-driven networking 或 metric tensor 技術審查。

## 核心發明句

AI 產生之候選操作意圖不得直接觸發外部系統操作，必須先被轉換為多維狀態封包，映射至受控陣型工作區，經策略閘道產生 allow / warn / block / rollback 判斷後，方得透過受控連接器操作 ERP、組織帳號、通訊平台或邊緣節點，且所有判斷與結果均需稽核回放。

## 主請求項應鎖定

1. 候選意圖封包化。
2. 多維狀態封包欄位。
3. 陣型工作區映射。
4. 策略閘道 allow / warn / block / rollback。
5. 跨系統受控連接器。
6. 稽核回放與證據鏈。

## 不應寫成

- 不應主張「發明 metric tensor 本身」。
- 不應主張「發明 RAG 本身」。
- 不應主張「發明意圖驅動網路本身」。
- 不應主張「發明 generic AI Agent routing 本身」。
- 不應把 Odoo、Google Workspace、LINE 寫成唯一限制。

## 實施例定位

Odoo、Google Workspace、LINE、論壇系統、Edge runtime、本地 AI runtime，均應作為實施例與落地場景。保護核心應保持在「AI 執行治理層」。

## 審查策略

主張範圍應窄而硬，先保護可落地的 execution-governance layer，再視 prior art 檢索結果拆分子案。
