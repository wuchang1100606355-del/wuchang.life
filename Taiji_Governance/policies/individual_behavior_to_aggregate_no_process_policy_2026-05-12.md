# 個別會員行為資訊匯入總量計算之無過程公開政策

版本：2026-05-12  
適用：團體會員、個別會員行為資訊、本會總資料庫、社區向量資訊、無明文上下文  

## 核心規則

個別會員行為資訊可以匯入總量計算項目。

但公開端、AI 上下文、買方資料產品只允許：

```text
只見公式。
不見個別數字。
只見結果。
不見計算過程。
```

## 可用於總量計算

個別會員行為資訊可在本會受控資料庫中，用於：

- 公益服務總量
- 社區參與總量
- 服務觸達總量
- 設備互動總量
- 社區產業服務需求
- ESG 指標
- 社區向量資訊
- 五維度規行為向量

## 不可見內容

不可對公開端、AI 上下文、買方顯示：

- 個別會員行為紀錄
- 個別會員數值
- 個別會員計算中間值
- 個別會員貢獻量
- 個別會員排名
- 可逆推出個人的中間過程
- 可逆推出個人的細分統計

## 可見內容

可見：

- 公式
- 欄位定義
- 統計口徑
- 聚合方法
- 最後總量
- 趨勢
- 版本
- SHA256
- audit 摘要

## 無明文上下文模型

```text
個別會員行為資訊
→ 權限資料庫
→ 受控總量計算
→ 中間過程不可見
→ 最後結果
→ 五維度規向量
→ 無明文上下文
```

## 中間值保護

中間值包含：

- 單一會員貢獻值
- 單一會員權重
- 單一會員時間序列
- 單一會員行為次數
- 單一會員與商家/設備/服務之關聯

中間值不得：

- 出現在 AI prompt
- 出現在雲端公開資料
- 出現在買方交付資料
- 出現在 ESG 對外報告明細
- 作為外部 API payload

## ADI / Tensor 標記

```json
{
  "mapping_type": "individual_behavior_to_aggregate",
  "individual_behavior_used_in_calculation": true,
  "individual_number_visible": false,
  "process_visible": false,
  "formula_visible": true,
  "final_result_visible": true,
  "intermediate_values_exportable": false,
  "plaintext_context_allowed": false,
  "audit_required": true
}
```

## L3 Metric Hazard

以下一律封鎖：

- 公開個別會員行為數字
- 公開個別會員計算中間值
- 買方取得個別會員過程資料
- AI prompt 取得個別會員過程資料
- 以總量公式反推個別會員
- 小樣本統計導致可逆識別

## 最終原則

```text
個別行為可以進總量。
個別數字不能被看見。
計算過程不能被外露。
公開的是公式與結果。
保護的是人與過程。
```

