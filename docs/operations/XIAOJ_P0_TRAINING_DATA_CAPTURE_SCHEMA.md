# XiaoJ P0 Training Data Capture Schema

STATE=XIAOJ_P0_TRAINING_DATA_CAPTURE_SCHEMA_READY
RUN_ID=D8_MANDATORY_TASK_20260624_134610_XIAOJ_P0_ONSITE_SHADOW_BROADCAST_CANDIDATE_ORDER_REHEARSAL

## JSONL Row Schema

Each line in `training_candidates.jsonl` should use:

```json
{
  "schema_version": "p0_shadow_training_v1",
  "created_at": "2026-06-24T00:00:00+08:00",
  "site_ref": "liaoguo_rexin_store",
  "mode": "shadow_candidate_only",
  "utterance_text": "",
  "normalized_repeat": "",
  "candidate_items": [],
  "human_correction": {
    "approved": false,
    "accepted_text": "",
    "corrected_items": [],
    "rejection_reason": "",
    "operator_name_or_ref": ""
  },
  "training_use": true,
  "write_to_odoo": false,
  "payment_capture": false,
  "member_plaintext": false,
  "raw_audio_saved": false,
  "raw_video_saved": false
}
```

## Allowed Training Content

- utterance text typed by operator.
- normalized repeat text.
- candidate menu refs.
- correction reason.
- role/ref of operator.

## Forbidden Training Content

- customer member name.
- customer phone.
- LINE private identifiers.
- payment card data.
- raw audio file.
- raw video file.
- secret values.

## Storage Location

P0 local rehearsal files:

```text
runtime/xiaoj_practicum/p0_shadow_rehearsal/
```

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
RAW_VIDEO_SAVED=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
