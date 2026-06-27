# Dead Mailbox 24H Hash Rule

STATE=DEAD_MAILBOX_24H_HASH_RULE_LOCKED

## Physical paths

OFFICIAL_DEAD_MAILBOX_ROOT=runtime/dead_letter
OFFICIAL_24H_HASH_MAILBOX=runtime/dead_letter/24h_hash_mailbox
OFFICIAL_EXPIRED=runtime/dead_letter/expired
OFFICIAL_QUARANTINE=runtime/dead_letter/quarantine

POS_SANDBOX_DEAD_LETTER=runtime/sandbox/pos_mvp_autodev/dead_letter/dead_letter_queue.jsonl
POS_RUN_DEAD_LETTER=runtime/sandbox/pos_mvp_autodev_run/dead_letter/dead_letter_queue.jsonl

## Rule

當開發者本機外接式硬碟或本機總場暫時不在線時，系統得將待驗證事件寫入死信箱；該死信箱僅保存 24 小時內可用之雜湊規則、封包參照、清單宣告檔參照、失敗收據、重試範圍及到期時間。

## Allowed fields

packet_ref
manifest_ref
hash_ref
failure_receipt
retry_scope
route_ref
timestamp
expiry_at
quarantine_state
reconstruction_required

## Forbidden fields

會員明文
完整個資
營業秘密
WHY_IT_RUNS
古數學展開規則
總場特徵碼生成規則
生成碼推導規則
原始影音
完整對話
付款資料
API key
token
password
router secret

## Expiry

TTL=24h

超過 24 小時未完成驗證者，應轉入 expired 或 quarantine，並要求重新取得總場特徵碼與接收端生成碼。

## Safety

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
PRODUCTION_RELEASE=FALSE

NEXT_ACTION=PATCH_DEAD_LETTER_WRITER_TO_24H_HASH_ONLY
