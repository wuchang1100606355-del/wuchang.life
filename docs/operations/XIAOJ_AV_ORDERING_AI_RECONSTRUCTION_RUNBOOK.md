# XiaoJ Sovereign AV Ordering AI Reconstruction Runbook

## Purpose

This runbook reconstructs XiaoJ as a local sovereign audio-video ordering AI
for cafe field rehearsal. The store continues operating through the human live
POS track, while XiaoJ runs a shadow candidate track for learning, broadcast,
visual prompting, and human correction.

## Start State

```text
TRACK_A_LIVE_OPERATION=HUMAN_ONLY
TRACK_B_XIAOJ_SHADOW=CANDIDATE_ONLY
POS_WRITE_BLOCKED=TRUE
PAYMENT_BLOCKED=TRUE
RAW_AUDIO_SAVED=FALSE
RAW_VIDEO_SAVED=FALSE
EXTERNAL_API_CALL=FALSE
```

## Local Files

```text
runtime/xiaoj_practicum/av_model/menu_lexicon.json
runtime/xiaoj_practicum/av_model/broadcast_scripts.json
runtime/xiaoj_practicum/av_model/candidate_order.schema.json
runtime/xiaoj_practicum/av_model/local_text_shadow_infer.py
runtime/xiaoj_practicum/av_model/README.md
```

## Rehearsal Flow

1. Staff serves the guest on the real POS track.
2. XiaoJ receives transcript text from local input or approved local STT.
3. XiaoJ parses the phrase in the order `尺寸 -> 溫度 -> 甜度 -> 品項`.
4. XiaoJ matches the item against `menu_lexicon.json`.
5. XiaoJ produces a candidate order packet.
6. Avatar or text UI repeats the candidate.
7. Staff or manager confirms, corrects, or rejects.
8. Correction is appended to training candidates only after removing member
   plaintext and confirming no raw audio/video is saved.

## Example

Input:

```text
大冰少糖招牌咖啡
```

Shadow output:

```text
大杯、冰、少糖、招牌咖啡。請真人確認，這只是候選單，價格需以 QuickClick 正式菜單為準。
```

## Reverse Order Handling

Input:

```text
招牌咖啡大冰少糖
```

XiaoJ response:

```text
我聽到像是「大冰少糖招牌咖啡」，請店員或店長確認。
```

State:

```text
repeat_confirmation_required=true
grammar_valid=false
POS_ORDER_CREATED=FALSE
PAYMENT_CAPTURE=FALSE
```

## Broadcast Script Use

Allowed scripts:

- Welcome phrase.
- Menu introduction.
- Waiting number rehearsal.
- Candidate order repeat.
- Manager confirmation reminder.

Broadcast scripts must not include member plaintext, payment instructions, or
invented menu items.

## Avatar Use

Use `assets/xiaoj/avatar/J.vrm` only when present and only as visual carrier.
Commercial release remains blocked until license review.

```text
AVATAR_ROLE=VISUAL_CARRIER_ONLY
COMMERCIAL_RELEASE=FALSE
LICENSE_REVIEW_REQUIRED=TRUE
```

## Updating Training Data

Append JSONL rows to a shadow training file only when all conditions are true:

- It is a transcript or correction, not raw audio.
- It contains no member plaintext.
- It references only locked real menu refs.
- It records whether human correction accepted or rejected the candidate.
- It preserves `write_to_odoo=false` and `payment_capture=false`.

## Stop Conditions

Use HOLD immediately for:

| Condition | State |
| --- | --- |
| Unknown menu item | `HOLD_REAL_MENU_SOURCE_LOCK` |
| Request to write POS | `HOLD_POS_WRITE_RELEASE_REQUIRED` |
| Request to capture payment | `HOLD_PAYMENT_RELEASE_REQUIRED` |
| Request to use external STT/TTS API | `HOLD_EXTERNAL_API_RELEASE_REQUIRED` |
| Request for commercial avatar release | `HOLD_LICENSE_REVIEW_REQUIRED` |
| Member plaintext appears | `HOLD_MEMBER_PLAINTEXT_GUARD` |

## Verification Command

Text-only local shadow inference:

```bash
python3 runtime/xiaoj_practicum/av_model/local_text_shadow_infer.py "大冰少糖招牌咖啡"
```

This command does not call external APIs, save audio/video, write POS, or
capture payment.
