# 度規資訊識別暗碼與外流稽核政策

版本：2026-05-12  
適用：本會所轄度規資訊、社區向量資訊、ESG 指標資料、公開摘要、授權資料產品  
定位：可稽核浮水印 / canary code / 版本暗碼  

## 核心規則

本會所轄度規資訊，得加註識別暗碼。

目的：

```text
若資料外流、轉載、未授權散布或被買方違約使用，
可依識別暗碼、版本 hash、授權紀錄與 audit chain 回溯來源。
```

識別暗碼不是個資，不得包含會員、商家、設備或個人可識別資訊。

## 可加註對象

可加註識別暗碼：

- 社區向量資訊資料產品
- ESG 指標摘要
- 公益帳戶公開摘要
- 無敏統計報表
- 組織雲端唯讀文件
- 買方授權資料包
- 研究資料去識別版本
- 對外簡報 / 白皮書 / API export

不可加註於：

- 會員明文資料
- D 磁碟會員資訊庫原始檔
- secret / token / key
- 會造成個人可識別之欄位
- 未審查的 raw behavior log

## 識別暗碼設計

識別暗碼建議包含：

```text
org_id
dataset_id
dataset_version
license_id
recipient_class
release_window
salted_hash
sha256_baseline
```

不得包含：

```text
姓名
電話
Email
身分證字號
會員編號明文
設備唯一識別明文
service account
API key
token
private key
```

## 範例

```json
{
  "audit_watermark": {
    "org": "wuchang.life",
    "dataset_id": "community_vector_esg_v1",
    "dataset_version": "2026-05-12_v01",
    "license_id_hash": "sha256:<hash>",
    "recipient_class": "esg_partner",
    "release_window": "2026Q2",
    "canary_code": "wm_<short_hash>",
    "sha256_baseline": "sha256:<dataset_hash>"
  }
}
```

## 外流稽核鏈

每次發布需留下：

```text
資料版本
識別暗碼
授權對象類別
授權契約
SHA256 baseline
發布時間
用途
禁止再識別條款
禁止轉售條款
audit record
```

外流查核流程：

```text
疑似外流資料
→ 擷取識別暗碼
→ 比對 SHA256 / canary code
→ 對應授權版本
→ 對應授權對象
→ 檢查契約限制
→ 產生外流稽核事件
→ 啟動撤銷授權 / 法務 / 通知流程
```

## 與無明文上下文的關係

識別暗碼只標記資料產品版本與授權鏈，不揭露個別資料。

正式原則：

```text
個別資訊不可見。
過程不可見。
結果可見。
暗碼可稽核。
```

## L3 Metric Hazard

以下一律封鎖：

- 以識別暗碼暗藏個資
- 以識別暗碼追蹤個別會員
- 識別暗碼可逆推出會員、商家或設備
- 買方移除識別暗碼後再散布
- 將識別暗碼當成唯一安全措施
- 暗碼資料包未建立 audit / SHA256

## 最終原則

```text
度規資訊可以流通，但不可斷鏈。
識別暗碼不是監控人，而是追溯資料包。
若資料流出，必須逃不出稽核。
```

