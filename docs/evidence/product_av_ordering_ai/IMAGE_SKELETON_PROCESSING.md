# Image Skeleton Processing

STATE=IMAGE_SKELETON_PROCESSING_SPEC_READY

## Direction

小J 影像不應先依賴第三方數位人平台成為主體。影像層應拆成可由 W7TP 8D packet 控制的骨架播放系統：

- skeleton track: 身體骨架與姿態節點。
- face track: 頭部方向、眼睛、表情。
- mouth track: 口型或 viseme 時序。
- gesture track: 招呼、點餐提示、確認、等待、推薦。
- scene track: 客顯背景、菜單、跑馬燈、候選訂單、證據徽章。
- audio track: SUNMI/iPhone/HomePod/browser TTS 或預生成音訊。

## Product Principle

數位人或影像骨架只是展示層，不是決策層。

```text
8D packet -> approved script_ref -> audio/viseme/skeleton timeline -> browser display -> evidence seal
```

Cloud may help generate candidate poses, mouth timing, or video assets, but local W7TP remains authority.

## Minimum Technical Shape

P1 uses pre-rendered or browser-played timeline clips:

- Input: `script_ref`, `voice_ref`, `pose_ref`, `scene_ref`.
- Output: browser video/canvas playback candidate.
- Gate: only approved script can be played.
- Evidence: record skeleton packet hash and playback state.

P2 adds semi-real-time mouth movement:

- Convert safe text/audio into viseme timeline.
- Drive mouth track in browser or cloud anchor adapter.
- Keep menu/order/payment/member decisions outside the avatar layer.

P3 adds pose/skeleton processing:

- Extract skeleton landmarks from approved source footage.
- Store compact pose refs, not bulky raw video as authority.
- Replay gestures with XiaoJ display state.

## 8D Mapping

- D1_IDENTITY: `avatar_ref`, `operator_ref`, `display_device_ref`.
- D2_INTENT: `avatar.play_script`, `avatar.play_menu_intro`, `avatar.play_order_candidate`.
- D3_STATE: `idle`, `speaking`, `confirming`, `hold`, `offline`.
- D4_TOPOLOGY: `store_ref`, `screen_ref`, `audio_ref`, `customer_display_ref`.
- D5_RESOURCE: `skeleton_ref`, `face_ref`, `mouth_ref`, `audio_ref`, `scene_ref`.
- D6_GOVERNANCE: no member plaintext, no payment data, no secret, approved script only.
- D7_VERIFICATION: script hash, audio hash, pose hash, ttl, human gate.
- D8_ENVELOPE: packet hash, hmac_ref, seal_ref, version.

## Open Source Candidate Review

Do not install or run unknown packages in production. Candidate categories to review:

- browser canvas/WebGL skeleton renderer.
- MediaPipe-style pose/face landmark extraction.
- Rhubarb-style lip sync / viseme extraction.
- lightweight Web Speech API viseme approximation.
- ffmpeg-only offline clip pipeline.

Review required before use: license, commercial use, browser support, GPU/CPU load, privacy, whether raw video/member plaintext leaves the store.

## Safety

- `FORMAL_DB_WRITE=FALSE`
- `FORMAL_POS_WRITE=FALSE`
- `PAYMENT_CAPTURE=FALSE`
- `SERVICE_RESTART=FALSE`
- `DEPLOY=FALSE`
- `PRODUCTION_RELEASE=FALSE`
- `SECRET_READ=FALSE`
- `MEMBER_PLAINTEXT_READ=FALSE`

