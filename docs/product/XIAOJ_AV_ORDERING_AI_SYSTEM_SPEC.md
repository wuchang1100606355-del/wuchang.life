# XiaoJ Sovereign Audio-Video Ordering AI System Spec

## State

```text
STATE=XIAOJ_AV_ORDERING_AI_RECONSTRUCTED_WITH_HOLD_ON_VRM_FILE
TRACK_A_LIVE_OPERATION=HUMAN_ONLY
TRACK_B_XIAOJ_SHADOW=CANDIDATE_ONLY
POS_WRITE_BLOCKED=TRUE
PAYMENT_BLOCKED=TRUE
DEPLOY=FALSE
EXTERNAL_API_CALL=FALSE
```

XiaoJ is reconstructed as a sovereign audio-video ordering AI for cafe onsite
shadow rehearsal. It is not a single cloud model. It is a local Total Field
pipeline that uses D8 reports, sealed operating rules, real menu references,
training corrections, and human verification.

## Coordinate

Core surfaces:

| Module | Role | P0 Boundary |
| --- | --- | --- |
| Transcript intake | Accept typed or local STT transcript text | Raw audio is not saved |
| Menu understanding | Match transcript to locked real menu refs | No invented menu |
| Candidate order builder | Produce shadow candidate packets | No POS write |
| Broadcast script runner | Prepare store-safe announcements | No external TTS call this run |
| Avatar visual carrier | Bind candidate state to `J.vrm` | Visual only, license hold for commercial release |
| Human correction recorder | Store approved/corrected shadow data | No member plaintext |
| Total Field verifier | Final authority for promotion | P2 release required for live actions |

## Evidence Inputs

The reconstruction uses these sealed local sources:

- `docs/operations/XIAOJ_FIELD_PRACTICUM_DUAL_TRACK_RULE.md`
- `docs/operations/TODAY_CAFE_POS_CASHIER_QUICKSTART.md`
- `docs/operations/XIAOJ_STAFF_VOICE_POS_GRAMMAR_RULE.md`
- `runtime/xiaoj_practicum/p0_shadow_rehearsal/p0_shadow_menu_refs.json`
- `runtime/xiaoj_practicum/p0_shadow_rehearsal/training_candidates.jsonl`
- `docs/total_field/XIAOJ_AVATAR_LICENSE_AND_GOVERNANCE_BOUNDARY.md`

## Real Menu Lock

P0 accepts only human-provided QuickClick screenshot rows currently recorded in
the correction report. Prices are not guessed; until a full QuickClick export
or complete screenshots with prices are provided, price authority remains false.

| Menu Ref | Display Name | Price Ref |
| --- | --- | --- |
| `quickclick_49180031` | 招牌咖啡 | pending QuickClick authority |
| `quickclick_49180033` | 小沙彌素齋飯 | pending QuickClick authority |
| `quickclick_49180034` | 耶加雪夫 / 單品手沖 | pending QuickClick authority |
| `quickclick_49180035` | 黃金曼特寧 / 濾掛咖啡 | pending QuickClick authority |
| `quickclick_49180036` | 耶加雪夫 / 咖啡豆 | pending QuickClick authority |
| `quickclick_49180038` | 檸檬汁 | pending QuickClick authority |

Forbidden invented items:

```text
三明治
蛋餅
美式咖啡
拿鐵
卡布奇諾
紅茶
早餐套餐
```

If an utterance cannot match the locked menu, the state is:

```text
HOLD_REAL_MENU_SOURCE_LOCK
```

## Voice Grammar

Canonical staff speech order:

```text
尺寸 -> 溫度 -> 甜度 -> 品項
```

Example:

```text
大冰少糖招牌咖啡
```

If the order is reversed or mixed, XiaoJ can normalize and repeat for human
confirmation, but must not write POS:

```text
我聽到像是「大冰少糖招牌咖啡」，請店員或店長確認。
```

## Packet Shape

Candidate order packets are local, non-executable, and verification-bound:

```json
{
  "packet_type": "XIAOJ_AV_CANDIDATE_ORDER_P0",
  "mode": "shadow_candidate_only",
  "utterance_text": "大冰少糖招牌咖啡",
  "slots": {
    "size": "大",
    "temperature": "冰",
    "sweetness": "少糖",
    "item": "招牌咖啡"
  },
  "candidate_items": [
    {
      "menu_ref": "quickclick_49180031",
      "display_name": "招牌咖啡",
      "qty": 1,
      "needs_human_review": true
    }
  ],
  "write_to_odoo": false,
  "payment_capture": false,
  "member_plaintext": false,
  "raw_audio_saved": false,
  "raw_video_saved": false
}
```

## Avatar Layer

`J.vrm` is the visual carrier only:

```text
AVATAR_ROLE=VISUAL_CARRIER_ONLY
IDENTITY_AUTHORITY=FALSE
GOVERNANCE_AUTHORITY=FALSE
COMMERCIAL_RELEASE=FALSE
LICENSE_REVIEW_REQUIRED=TRUE
```

If the file is missing at `assets/xiaoj/avatar/J.vrm`, the AV engine can still
run in text-only shadow mode, but visual avatar readiness remains HOLD.

## Local AV Model Resources

Generated resources live under:

```text
runtime/xiaoj_practicum/av_model/
```

Files:

- `menu_lexicon.json`
- `broadcast_scripts.json`
- `candidate_order.schema.json`
- `local_text_shadow_infer.py`
- `README.md`

## Promotion Boundary

P0/P1 can rehearse and collect corrections. Live POS order creation, payment
capture, Odoo DB write, service restart, deployment, external API calls, and
commercial avatar release require separate human release packets.
