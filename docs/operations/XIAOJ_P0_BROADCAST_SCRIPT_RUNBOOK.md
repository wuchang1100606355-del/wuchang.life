# XiaoJ P0 Broadcast Script Runbook

STATE=XIAOJ_P0_BROADCAST_SCRIPT_RUNBOOK_READY
RUN_ID=D8_MANDATORY_TASK_20260624_134610_XIAOJ_P0_ONSITE_SHADOW_BROADCAST_CANDIDATE_ORDER_REHEARSAL

## Broadcast Rule

P0 broadcast is local text rehearsal only. No Google STT/TTS call occurs in this run.

## Broadcast Schema

```json
{
  "mode": "broadcast_rehearsal",
  "script_type": "welcome | menu_intro | queue_guidance | closing | community_notice",
  "script_text": "",
  "speaker": "小J",
  "public_safe": true,
  "member_plaintext": false,
  "payment_instruction": false,
  "tts_engine": "local_text_only_this_run"
}
```

## Approved P0 Script Types

| Type | Use |
| --- | --- |
| `welcome` | greet customers |
| `menu_intro` | introduce real P0 menu refs only |
| `queue_guidance` | guide waiting customers |
| `closing` | closing reminder |
| `community_notice` | public-safe community notice |

## Example Welcome

```text
歡迎光臨聊國咖啡館重新總店。小J今天只做演練與複誦，正式點餐與收銀請以店員 POS 為準。
```

## Example Menu Intro

```text
今日 P0 演練品項以店內 POS 可見品項為準：美式咖啡、拿鐵、卡布奇諾、紅茶、早餐套餐。小J只會產生候選單，不會寫入 POS。
```

## Forbidden Broadcast

- Do not promise payment capture.
- Do not claim live AI ordering is released.
- Do not mention member plaintext.
- Do not use invented products.
- Do not say Google TTS is active this run.

## Safety Flags

SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
RAW_AUDIO_SAVED=FALSE
RAW_VIDEO_SAVED=FALSE
EXTERNAL_API_CALL=FALSE
GOOGLE_STT_CALL=FALSE
GOOGLE_TTS_CALL=FALSE
