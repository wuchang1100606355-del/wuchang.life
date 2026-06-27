# XiaoJ P0 Onsite Shadow Rehearsal Runbook

STATE=XIAOJ_P0_SHADOW_REHEARSAL_RUNBOOK_READY
RUN_ID=D8_MANDATORY_TASK_20260624_134610_XIAOJ_P0_ONSITE_SHADOW_BROADCAST_CANDIDATE_ORDER_REHEARSAL

## Today XiaoJ Can Do

- Speak broadcast rehearsal text.
- Repeat a staff/customer order back in normalized wording.
- Create a shadow candidate order JSON.
- Ask the human operator to correct the candidate.
- Store training candidates for later review.
- Use only the P0 POS-visible menu refs listed in `runtime/xiaoj_practicum/p0_shadow_rehearsal/p0_shadow_menu_refs.json`.

## Today XiaoJ Cannot Do

- Write a real POS order.
- Capture payment.
- Change Odoo products, prices, sessions, or payments.
- Read member plaintext.
- Save raw audio.
- Save raw video.
- Call Google STT/TTS.
- Invent menu items.

## A Track: Real Human POS

Track A remains the only live business path:

1. Human cashier listens to the customer.
2. Human cashier uses Odoo POS.
3. Human cashier receives cash.
4. Human cashier completes real receipt and cash accountability.
5. Manager handles refunds, voids, price changes, and abnormal orders.

## B Track: XiaoJ Shadow

Track B is training and rehearsal only:

1. Staff types or speaks a phrase, then enters the transcript as text.
2. XiaoJ parses the utterance against P0 menu refs.
3. XiaoJ creates a candidate order.
4. XiaoJ repeats the candidate.
5. Human accepts, corrects, or rejects.
6. Candidate and correction become training material.
7. No Odoo write occurs.

## Onsite Quick Script

```text
小J現在只做演練，不會寫入 POS。
請用真人 POS 結帳；小J只複誦候選單，讓店長或店員校正。
```

Vietnamese manager helper:

```text
XiaoJ chi dien tap, khong ghi POS, khong thu tien.
Quan ly xac nhan ban nhap truoc.
```

## Stop Conditions

Stop immediately if:

- XiaoJ asks to write true POS.
- XiaoJ asks to capture payment.
- XiaoJ generates non-real menu items.
- XiaoJ asks for member plaintext.
- XiaoJ asks to read secrets.
- XiaoJ treats confidence as transaction truth.
- Raw audio/video is being saved.

## Evening Training Cleanup

At closing:

1. Review `training_candidates.jsonl`.
2. Keep accepted/corrected/rejected candidate rows.
3. Do not add member names, phone, or private notes.
4. Summarize mismatch patterns.
5. Keep P0 as shadow until release gates pass.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
RAW_VIDEO_SAVED=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
GOOGLE_STT_CALL=FALSE
GOOGLE_TTS_CALL=FALSE
