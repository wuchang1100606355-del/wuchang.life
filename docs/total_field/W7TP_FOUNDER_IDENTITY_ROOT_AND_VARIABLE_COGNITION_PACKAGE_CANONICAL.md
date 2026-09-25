# Founder 自然人身分根與可變認知套件治理正典

STATE=CANONICAL_ACTIVE
RUN_ID=FOUNDER_IDENTITY_VARIABLE_COGNITION_20260716T070407Z
OWNER=江政隆
NODE=taiji01
SCOPE=FOUNDER_IDENTITY_ROOT_AND_VARIABLE_COGNITION_PACKAGE

## 1. 最高治理根

1. 江政隆本人是最高意志來源、總場唯一修改權人與最終可究責自然人。
2. 總場是 Founder 意志的最高系統權限具現，負責維護及執行 Founder 命令。
3. Founder 正式修改前，所有人員、管理員、節點、AI 與代理均受現行總場約束。
4. 被指定人員只能取得 Founder 明確授予的執行權，不得修改總場、授權來源或自身權限。
5. LLM 與其他代理只能產生候選，不具治理權、修改權或自行擴權能力。

## 2. CURRENT_IDENTITY_GATE

`CURRENT_IDENTITY_GATE=ALLOW` 必須由受 OS 保護、在請求外載入的 sealed Founder root 同時驗證：

- 裝置綁定 principal 的 `sha256:<64 lowercase hex>` 公鑰指紋與請求完全相符。
- Google OIDC `issuer` 與 `subject_sha256` 均與 root 完全相符；不保存或接收 email、access token、ID token、password、credential 或 refresh token。
- sealed root 的 schema、停用 adapter 狀態及 `root_sha256` 自我雜湊有效。
- 請求含明確 Founder 修改命令、非空 `founder_command_ref`，且 D8 決策為 `ALLOW`。

Founder 姓名、`Founder命令` 字串、舊 `founder:...` 字串或 opaque Google 帳號 reference 均不能提升權限。Google 管理員、Linux 管理員、Odoo 管理員或任何單一帳號也不等同 Founder。未找到已封存 root 時固定回 `HOLD_FOUNDER_ROOT_NOT_PROVISIONED_OR_INVALID`；root 存在但任一因子不符則 `BLOCK`。

未來身分介面只保留 adapter/schema，不宣稱已整合：

- `TW_MOI_DIGITAL_NATURAL_PERSON_ID=DISABLED_NOT_CONFIGURED`
- `PHYSICAL_NATURAL_PERSON_CERTIFICATE_CARD=DISABLED_NOT_CONFIGURED`

## 3. 可變認知套件

可變的是受治理的 cognition package，不是總場正典。生命週期固定為：

```text
DISCOVERED -> CANDIDATE -> VERIFIED -> ENABLED -> DISABLED -> QUARANTINED
```

AI、節點、一般人員及管理員只能提交 `CANDIDATE`。只有通過 `CURRENT_IDENTITY_GATE` 的 Founder 明確命令能安裝、啟用、更新、停用或移除套件。更新建立同一 `package_id` 的新版本候選並重新驗證；移除以 `QUARANTINED` tombstone 保留追溯證據，不物理刪除稽核紀錄。

安裝前必須驗證 manifest、SHA256、能力範圍、相依性、允許節點、封包自帶協定、封包自帶驗證與禁止行為。驗證失敗一律 `QUARANTINED`。套件不得修改：

- 總場正典
- Founder 身分根
- D8 規則
- 自身權限
- 雲端模型授權規則

套件執行必須留下 evidence refs、執行前狀態 SHA256、執行後狀態 SHA256 與 package SHA256。

### 3.1 能力疊加與融合

總場可把兩個以上已通過驗證且處於 `ENABLED` 的套件能力疊加／融合，產生新的 derived capability。融合結果必須：

- 建立新的 package/version 與 SHA256，不改寫來源套件。
- 記錄每一來源套件的 `package_id`、`version` 與 `sha256`。
- 權限不得超出全部來源套件 `requested_permissions` 的聯集。
- 先輸出 `CANDIDATE`，不得因融合成功而自動成為 `VERIFIED` 或 `ENABLED`。
- 再走完整 manifest、雜湊、相依性、禁止行為、總場驗證與 Founder identity gate。
- 來源未啟用時 `BLOCK`；來源驗證失敗或融合擴權時 `QUARANTINE`。

因此能力可組合形成新能力，但治理權、總場正典、Founder 身分根與 D8 規則不參與可變融合。

## 4. CPU/GPU 節點規則

`CPU_BASELINE` 永遠保留完整基準路徑。MSI RTX 4070 在線時加入 `FOUNDER_GPU_EXECUTION_NODE` 並回報 `GPU_SUPPORT`；離線時回報 `CPU_BASELINE_CONTINUES`，不得使系統停止。GPU 離線不構成雲端模型授權；雲端模型仍須同一 Founder identity gate 明確 `ALLOW`，否則 `BLOCK`。

## 5. 生成式傳輸邊界

可變認知套件不得曲解 W7TP 正典。生成式傳輸仍是 protocol-native 8D 狀態場封包，以引用、查表、重構條件、等價狀態生成、封包自帶協定、封包自帶驗證及總場驗證完成裁決；不是檔案搬運、雲端同步、備份、下載解密或模型猜測。

## 6. 實作綁定

- Identity schema: `schemas/field/founder_identity_gate.schema.json`
- Package schema: `schemas/field/variable_cognition_package_manifest.schema.json`
- Gate: `tools/total_field/founder_variable_cognition_gate.py`
- Tests: `tests/test_founder_variable_cognition_gate.py`
- 8D packet: `reports/w7tp_founder_identity_variable_cognition_8d_packet.json`
- Verification: `reports/w7tp_founder_identity_variable_cognition_verification_report.json`
- Hash manifest: `manifests/w7tp_founder_identity_variable_cognition_v0_1/SHA256_MANIFEST.json`
