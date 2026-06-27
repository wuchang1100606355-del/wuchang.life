# XiaoJ P0 Candidate Order And Human Correction Flow

STATE=XIAOJ_P0_CANDIDATE_ORDER_AND_HUMAN_CORRECTION_FLOW_READY
RUN_ID=D8_MANDATORY_TASK_20260624_134610_XIAOJ_P0_ONSITE_SHADOW_BROADCAST_CANDIDATE_ORDER_REHEARSAL

## Candidate Order Schema

```json
{
  "mode": "shadow_candidate_only",
  "utterance_text": "顧客說的文字或人工輸入",
  "candidate_items": [
    {
      "menu_ref": "real_menu_ref_only",
      "display_name": "品項名稱",
      "qty": 1,
      "confidence": 0.0,
      "needs_human_review": true
    }
  ],
  "human_correction": {
    "approved": false,
    "corrected_items": [],
    "reason": ""
  },
  "write_to_odoo": false,
  "payment_capture": false,
  "training_use": true
}
```

## Non-Float Anti-Hallucination Rule

Confidence is not transaction truth.

```text
floating confidence -> never writes POS
symbolic menu_ref -> must match P0 real menu refs
human correction -> required before any future release
```

## Human Correction Fields

| Field | Required | Rule |
| --- | --- | --- |
| `accepted_text` | yes | what XiaoJ repeated |
| `corrected_menu_ref` | when needed | must come from P0 menu refs |
| `quantity` | yes | integer greater than 0 |
| `rejection_reason` | when rejected | short public-safe reason |
| `operator_name_or_ref` | yes | role/ref only; no member plaintext |
| `timestamp` | yes | ISO-like local time |

## Flow

1. Enter utterance text.
2. Match only against P0 menu refs.
3. If no match, create rejected candidate with `needs_human_review=true`.
4. Repeat candidate to staff/customer.
5. Human confirms or corrects.
6. Store as training candidate.
7. Keep `write_to_odoo=false`.
8. Keep `payment_capture=false`.

## Stop Conditions

- Candidate contains menu item outside P0 refs.
- Candidate tries to write Odoo.
- Candidate tries to capture payment.
- Candidate asks for member name/phone/private data.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
RAW_VIDEO_SAVED=FALSE
ODOO_DB_WRITE=FALSE
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
