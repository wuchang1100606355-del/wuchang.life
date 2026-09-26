---
name: w7tp-8d-adi-audio-field
description: Resolve and control W7TP audio input/output state as one 8D ADI audio field. Use for endpoint open/close, output volume, input gain, mute, scene/DSP intent, Siri-triggered audio control, HomePod routing, and cross-node audio governance. Siri, apps, devices, providers, and DSP engines are capability sources only and never create D8 authority.
---

# W7TP 8D ADI Audio Field（W7TP 八維自適應意圖音效場）

Treat audio as one coupled 8D state field, not as independent sliders.

## Hard rules

- 8D ADI = 8_IN_1_SINGLE_STATE_FIELD（八合一單一狀態場）.
- Siri（蘋果語音助理） is a D1 intent trigger only, never D8 authority.
- Nahimic is a capability provider/evidence source only, never authority.
- Every selectable audio input or output MUST expose readable, adjustable, verifiable, rollback-capable Volume/Gain（音量／增益） control.
- An endpoint without proven volume/gain control is HOLD and not selectable.
- OUTPUT_CLOSE（輸出關閉） means remove from active route + mute while preserving the last non-zero level. It does not disable or uninstall the operating-system device.
- OUTPUT_OPEN（輸出開啟） means route-selectable + unmute + restore the last valid level.
- Input gain and output volume are distinct controls.
- Raw microphone audio remains local by default.

## Siri trigger contract

Supported intent classes:
- OUTPUT_OPEN（輸出開啟）
- OUTPUT_CLOSE（輸出關閉）
- SET_OUTPUT_VOLUME（設定輸出音量）
- SET_INPUT_GAIN（設定輸入增益）
- MUTE_OUTPUT（輸出靜音）
- UNMUTE_OUTPUT（取消輸出靜音）
- GROUP_SET_VOLUME（群組音量）
- GROUP_OPEN（群組開啟）
- GROUP_CLOSE（群組關閉）
- STATUS（查詢狀態）

Examples:
- 「Siri，把辦公室音效打開」
- 「Siri，把辦公室音量調到 35%」
- 「Siri，把 MSI 麥克風調到 70%」
- 「Siri，全部靜音」

Siri Shortcut（Siri 捷徑） or App Intent（應用意圖） produces structured fields. The voice phrase itself is not effect authorization.

## 8D projection

- D1 Intent（意圖）: target, operation, requested level.
- D2 State（狀態）: route, mute, current volume/gain, scene and DSP state.
- D3 Coordinate（座標）: node, endpoint ID, zone, backend and group membership.
- D4 Evidence（證據）: control range, current level, provider/version, health and receipts.
- D5 Execution/Policy（執行／政策）: eligibility, bounds, open/close semantics and rollback preimage.
- D6 Generative Transmission（生成式傳輸）: bounded audio-state/control references and reconstruction conditions when used; raw audio transport is not implied.
- D7 Risk/Quarantine（風險／隔離）: stale endpoint identity, uncontrolled volume, >100 backend gain, excessive jump, held node, route conflict.
- D8 Envelope/Authority（封套／權威）: Total Field（總場） decision for the exact effect.

## Nahimic-equivalent capability model

Model effects, not proprietary algorithms:
- scene: MUSIC / MOVIE / COMMUNICATION / GAMING / SMART
- ten-band EQ（十段等化器）: 32, 64, 125, 250, 500 Hz, 1, 2, 4, 8, 16 kHz
- spatial/surround intent（空間／環繞意圖）
- voice clarity（語音清晰度）
- bass shaping（低頻塑形）
- treble shaping（高頻塑形）
- microphone processing（麥克風處理）
- mirroring/share-audio intent（鏡射／共享音訊意圖）
- endpoint routing（端點路由）
- endpoint Volume/Gain（音量／增益）

Backends（後端） may be Nahimic, Windows Core Audio（Windows 核心音訊）, PulseAudio（脈衝音訊）, RAOP/AirPlay（遠端音訊輸出／隔空播放）, or another qualified DSP（數位訊號處理） provider.

## Volume contract

Normalize human-facing controls to 0..100.

- Windows output/input: Core Audio scalar 0.0..1.0 + readback.
- PulseAudio output/input: sink/source percent + readback.
- HomePod: pyatv set_volume 0..100 + readback.
- Endpoint open/close preserves last_nonzero_volume and rollback preimage.
- Group operations require every member to pass the control gate; hidden partial success is forbidden.
- Backend values over 100% are D7 risk and may not be selected as normalized target state.

## Runtime boundary

Candidate planning and deterministic validation may run without D8. Live volume, gain, route or mute mutation requires the exact Total Field decision and endpoint-specific rollback preimage.
