# W7TP 單一封包自行重構發明人 Canonical 封印

STATE=FOUNDER_CANONICAL_TECHNICAL_CORRECTION_SEALED
CANONICAL_ID=W7TP_SINGLE_PACKET_SELF_RECONSTRUCTION
AUTHORITY=FOUNDER_EXPLICIT_TECHNICAL_CORRECTION
IMPLEMENTATION_BINDING=UNSPECIFIED_BY_FOUNDER

## 權威與優先級

本文件新增發明人明確技術更正，不刪除或覆蓋既有 canonical 文件。定義衝突時，優先級固定為：

```text
FOUNDER_EXPLICIT_CORRECTION
> older canonical inference
> implementation assumption
> agent-generated design
```

## 發明人明確技術定義

1. 一個 8D 意圖場張量狀態封包就是完整生成式傳輸單位。
2. 封包傳到異地後，可以直接開啟並完成重構。
3. 引用能力必須包含於封包。
4. 查表能力必須包含於封包。
5. 傳輸協定必須包含於封包。
6. 重構條件與生成規則必須包含於封包。
7. 驗證方法與驗證條件必須包含於封包。
8. 不得要求額外安裝 W7TP 執行器、下載器、獨立重構服務或外部 runtime。
9. 沒有不能重構的檔案；只能區分封包所使用的狀態、引用、查表、張量及生成方式。
10. 不得把生成式傳輸重定義成完整檔案搬運、壓縮、備份、同步或下載解密。
11. Receiver 與 TotalField 等名詞不得被擅自解釋成必須另外安裝的外部程式。
12. 發明人尚未明確指定的 target OS 封裝格式、啟動格式、檔案副檔名及底層實作不得補猜，統一標示 `IMPLEMENTATION_BINDING=UNSPECIFIED_BY_FOUNDER`。

## Canonical 不變量

```text
SINGLE_PACKET=TRUE
DIRECT_OPEN_AND_RECONSTRUCT=TRUE
PACKET_CARRIED_INTENT_STATE_TENSOR=TRUE
PACKET_CARRIED_REFERENCES=TRUE
PACKET_CARRIED_LOOKUP_CAPABILITY=TRUE
PACKET_CARRIED_TRANSPORT_PROTOCOL=TRUE
PACKET_CARRIED_RECONSTRUCTION_CONDITIONS=TRUE
PACKET_CARRIED_GENERATION_RULES=TRUE
PACKET_CARRIED_VERIFICATION_METHOD=TRUE
PACKET_CARRIED_VERIFICATION_CONDITIONS=TRUE
EXTERNAL_W7TP_EXECUTOR_REQUIRED=FALSE
EXTERNAL_RUNTIME_REQUIRED=FALSE
UNIVERSAL_FILE_RECONSTRUCTION=TRUE
IMPLEMENTATION_BINDING=UNSPECIFIED_BY_FOUNDER
```

`UNIVERSAL_FILE_RECONSTRUCTION=TRUE` 表示不存在被預先排除於重構之外的檔案類別；各封包仍依其所使用的狀態、引用、查表、張量、生成方式及驗證要求完成結果。本定義不表示固定封包大小，也不把生成式傳輸改寫為原始檔案下載或完整檔案搬運。

## 現有 Canonical 缺口

```text
GAP_SINGLE_PACKET_DIRECT_OPEN
GAP_PACKET_CARRIED_LOOKUP_CAPABILITY
GAP_NO_EXTERNAL_EXECUTOR
GAP_UNIVERSAL_FILE_RECONSTRUCTION
GAP_IMPLEMENTATION_BINDING_UNSPECIFIED
```

## 禁止定義漂移

```text
FILE_COPY
COMPRESSION_ONLY
BACKUP
SYNC
DOWNLOAD_DECRYPT
UNRECONSTRUCTABLE_FILE_CLASS
```

上述項目不得被用來替代或限縮本封印的生成式傳輸定義。Receiver 與 TotalField 是 canonical 流程中的角色名稱；在發明人另行指定前，不得由其名稱推導外部安裝需求、target OS 綁定、啟動格式、檔案副檔名或底層實作。

## 實作邊界

本封印只固定技術定義，不指定或推測程式碼、封包外觀、啟動器、作業系統封裝、檔案副檔名、傳輸載具或底層演算法。

```text
IMPLEMENTATION_BINDING=UNSPECIFIED_BY_FOUNDER
CODE_CHANGE=NO
DEPLOY=NO
```
