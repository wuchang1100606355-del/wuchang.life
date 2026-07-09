# W7TP Association Digital Resident Identity Code Spec

STATE=W7TP_ASSOCIATION_DIGITAL_RESIDENT_IDENTITY_CODE_SPEC_READY
AUTHORITY=TOTAL_FIELD
MODE=CANDIDATE_ONLY_NO_LIVE_WRITE

## Purpose

This specification defines the association digital resident identity code as a sovereign individual identity packet for W7TP. It repairs the specification layer only. It does not modify live Odoo, live DB, router, deployment, or service state.

## Core Definition

信箱只是聯絡入口。信箱可以接收通知、驗證訊息或候選聯絡需求，但信箱不是居民身份本體，也不是總場權威。

數位居民身分碼代表個體主權身分。它是一個本地總場可驗證的個體身份封包 ref，並可在同一個體上掛載多個角色。

本地明文身份根只在地方本地伺服器或協會授權本地服務邊界。總場封包、雲端候選、公開 UI、schema sample 只保留 ref、hash、seal、policy ref、去識別摘要與候選需求。

## One Person, Multiple Role Mounts

一人一個體，多角色掛載。

角色不是多帳號。`resident_role`、`member_role`、`merchant_responsible_person_role`、`association_responsible_person_role`、`consumer_role`、`developer_role` 都是同一個體的角色掛載，不代表多個登入帳號或多份身份根。

使用者系統才是硬前端。UI 是主權身份場，不是多帳號切換器。UI 可顯示目前角色投影與可用能力，但不得把角色切換當作權限來源。

## 8D State Fields

8D 狀態場固定為：

- 意圖場
- 狀態場
- 座標場
- 證據場
- 執行場
- 生成式傳輸場
- 風險禁錮場
- 封套驗證場

這些是狀態場，不是資料表欄位。每一個場都必須能被總場 verifier 對應、重構、檢查與封套驗證。

## Generative Transport

生成式傳輸是內部通信主要技術。8D狀態場封包如設計圖，自帶驗證與通訊協定。

不完整資訊即可傳輸。接收端依 `packet_ref`、`state_ref`、`evidence_ref`、`reconstruction_condition`、`equivalent_state_condition` 與 `verification_condition` 生成等價狀態，再由總場 verifier 逐動作裁決 `PASS / HOLD / WARN / BLOCK`。

雲端只接收 ref、去識別摘要、候選需求與安全語氣需求，不得接收任何可識別明文。雲端不可成為權威，也不可補違規操作。

## Privacy Boundary

Required boundary:

```text
privacy_boundary=ALL_IDENTIFIABLE_PLAINTEXT_LOCAL_ONLY
cloud_candidate_policy=CANDIDATE_ONLY_NO_AUTHORITY_NO_PLAINTEXT
final_authority=total_field_verifier
```

Allowed cloud-facing material:

- resident_identity_ref
- contact_ref
- association_ref
- merchant_ref
- property_ref
- evidence_ref
- seal_ref
- policy_ref
- de-identified summary
- candidate requirement

Blocked cloud-facing material:

- identifiable identity root
- private contact value
- raw image
- raw voice
- raw credential value
- internal review note
- private household detail

## Role Mounting Model

The digital resident identity code may mount:

- `resident_role`
- `member_role`
- `merchant_responsible_person_role`
- `association_responsible_person_role`
- `consumer_role`
- `developer_role`

Each role mount carries role refs, capability refs, evidence refs, seal refs, and policy refs. Role mounts do not duplicate identity roots.

## Total Field Decision

The Total Field verifier decides each action:

```text
TotalField.Verify(action_packet) -> PASS / HOLD / WARN / BLOCK
```

No role mount, cloud candidate, scene XiaoJ, UI surface, mailbox contact, Odoo view, or local helper can bypass that verifier.

## Safety Flags

```text
NO_SECRET=TRUE
NO_MEMBER_PLAINTEXT=TRUE
NO_RESIDENT_PLAINTEXT=TRUE
NO_RAW_IMAGE=TRUE
NO_RAW_VOICE=TRUE
NO_RAW_KEY_TOKEN_PASSWORD=TRUE
NO_DB_WRITE=TRUE
NO_DEPLOY=TRUE
NO_RESTART=TRUE
NO_ROUTER_WRITE=TRUE
NO_OVERWRITE_OTHER_FILES=TRUE
```
