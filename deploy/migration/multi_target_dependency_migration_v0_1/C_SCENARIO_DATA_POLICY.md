# C Drive Scenario Data Policy

版本：2026-05-11  
定位：經常讀寫、個別需求之系統資料夾  
Windows 路徑：`C:/Users/o0930/Taiji_Data/`  
WSL 路徑：`/mnt/c/Users/o0930/Taiji_Data/`  

## 核心定義

C 磁碟資料區用於日常場景資料，不是無敏雲端區，也不是 D 磁碟高權限封存區。

可放：

- 團體會員作業資料
- 商家營業資料
- 管委會會議資訊
- 社區服務案件
- Odoo 匯入暫存
- POS 營業紀錄
- 待去敏後上雲候選資料

不可放：

- 一般散落的 private key
- 一般散落的 OAuth token
- 一般散落的 service account JSON
- 未分類的 secret
- 無審查直接上雲資料

## 建議資料夾

```text
C:/Users/o0930/Taiji_Data/
  group_members/
  merchant_operations/
  condo_committee_meetings/
  community_service_cases/
  odoo_import_staging/
  pos_business_records/
  meeting_minutes_private/
  export_review/
  redacted_cloud_candidates/
```

## 上雲前去敏流程

```text
原始資料
→ export_review
→ 去識別化 / 摘要化 / 移除營業機密
→ redacted_cloud_candidates
→ 本人審查
→ 組織雲端唯讀 staging
```

## 明文個資

明文個資包含：

- 姓名
- 身分證字號
- 電話
- Email
- 地址
- 會員個別進度
- 個別服務紀錄
- 可識別個人的會議紀錄或附件

規則：

```text
C 磁碟：可作為場景資料工作區，但需權限分窗。
雲端：禁止，除非已去識別化且經審查。
D 磁碟：特殊用途才可保存，需本人審查與 audit。
```

## 營業機密

營業機密包含：

- 供應商價格
- 成本結構
- POS 銷售明細
- 未公開營運策略
- 未公開合約
- 商家設備部署細節
- 高權限節點資訊

規則：

```text
C 磁碟：可作為日常業務資料區。
雲端：禁止，除非已摘要化且不含機密。
D 磁碟：高權限特殊用途才保存，需審查。
```

