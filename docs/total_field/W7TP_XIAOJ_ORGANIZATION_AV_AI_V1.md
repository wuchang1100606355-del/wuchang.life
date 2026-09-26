# 組織影音 AI 小J場控架構 V1

STATE=PASS_FOUNDER_INTENT_ORGANIZATION_SCENE_CONTROL

## 定義修正

影音 AI 小J不是「幾個影音器官的集合」而已。

**影音 AI 小J本身就是 Organization AI（組織 AI）**，服務一個組織場域，必須能在組織授權範圍內直接做場控，包括播放音樂、停播、切歌、調整區域音量、切換場景、控制 HomePod（蘋果智慧喇叭）、顯示畫面、播報及影音同步。

```text
Organization（組織）
        │
        ▼
Organization Policy（組織政策）
        │
        ▼
影音 AI 小J
        │
        ▼
8D ADI（八維自適應意圖，八合一單一狀態場）
        │
        ▼
Total Field（總場）
        │
        ├─ Music / Playlist（音樂／播放清單）
        ├─ DSP（數位訊號處理）
        ├─ HomePod / Speakers（HomePod／喇叭）
        ├─ TTS / Announcement（文字轉語音／播報）
        ├─ Display / Avatar（顯示／虛擬人）
        └─ Scene Transition（場景切換）
```

## 場控不是「每一首歌都人工批准」

低風險、可逆、已由組織預先授權的場控效果，可在既定 Policy Envelope（政策封套）內直接執行：

- PLAY_MUSIC（播放音樂）
- PAUSE_MUSIC（暫停音樂）
- STOP_MUSIC（停止音樂）
- NEXT_TRACK（下一首）
- PREVIOUS_TRACK（上一首）
- SET_ZONE_VOLUME（設定區域音量）
- SET_GROUP_VOLUME（設定群組音量）
- MUTE_ZONE（區域靜音）
- UNMUTE_ZONE（取消區域靜音）
- SELECT_PLAYLIST_REF（選擇播放清單參照）
- SELECT_AUDIO_SCENE（選擇音效場景）
- ROUTE_AUDIO_TO_ZONE（將音訊路由到區域）
- SHOW_PUBLIC_DISPLAY_SCENE（顯示公開場景）
- RUN_APPROVED_ANNOUNCEMENT_REF（執行已核准播報）
- DUCK_MUSIC_FOR_APPROVED_ANNOUNCEMENT（播報時降低音樂）
- RESTORE_PREVIOUS_SCENE（恢復前一場景）

每次仍必須留下 readback（回讀）與 receipt（收據），效果不符就 rollback（回復）。

會員明文、付款、敏感個資、法律／組織決策、權威變更等不屬於這個可逆場控授權。

## 組織場景

小J應把場域視為 Scene State（場景狀態），不是單一播放器：

```text
organization_ref（組織參照）
venue_ref（場域參照）
zone_ref（區域參照）
scene_ref（場景參照）
time_window_ref（時間窗參照）
audio_source_ref（音訊來源參照）
playlist_ref（播放清單參照）
now_playing_ref（目前播放參照）
output_group_ref（輸出群組參照）
volume_state（音量狀態）
dsp_scene_ref（音效場景參照）
display_scene_ref（顯示場景參照）
announcement_ref（播報參照）
policy_ref（政策參照）
effect_receipt_ref（效果收據參照）
```

可建立：

- CAFE_OPENING（咖啡館開店場景）
- CAFE_NORMAL（咖啡館一般營業場景）
- QUIET_SERVICE（安靜服務場景）
- EVENT_MODE（活動場景）
- ANNOUNCEMENT（播報場景）
- CLOSING（打烊場景）
- EMERGENCY_DUCK_AND_ANNOUNCE（緊急降音量與播報場景）

## 開源能力在小J體內的位置

### Music Assistant（音樂助理）
不是小J本體；是小J的 media/music organ（媒體／音樂器官）候選。負責播放清單、目前播放狀態、Apple Music（蘋果音樂）候選來源、HomePod／AirPlay（隔空播放）與多房輸出。

### CamillaDSP（Camilla 數位訊號處理）
是 audio DSP organ（音效處理器官）候選。承接從 Nahimic（音效處理套件）觀測出的 EQ（等化）、空間音效、語音清晰、低頻、高頻、增益、壓縮、限制、卷積等**效果語義**。

### Odoo Community（Odoo 社群開源版）
不是小J的大腦，而是 organization operation surface（組織操作表面）：

```text
wuchang.xiaoj.av.scene
wuchang.xiaoj.av.zone
wuchang.xiaoj.av.device
wuchang.xiaoj.av.provider
wuchang.xiaoj.av.desired.state
wuchang.xiaoj.av.observed.state
wuchang.xiaoj.av.effect.request
wuchang.xiaoj.av.effect.receipt
wuchang.xiaoj.av.playlist.policy
wuchang.xiaoj.av.announcement.policy
```

因此管理者可在 Odoo Community（Odoo 社群開源版）設定「營業時間播放哪一類音樂、各區最大音量、活動場景、播報優先權」，但真正 effect（效果）仍由 8D ADI（八維自適應意圖）／Total Field（總場）裁決與回讀。

## 節點角色

- taiji01：Total Field（總場）＋組織影音 broker（仲介）
- MSI：Founder（創辦人）影音工作站＋本地媒體來源
- taiji03：組織超級管理員控制設備
- taiji04：SUNMI POS（商米銷售時點系統）＋商用語音硬體候選
- drallion：組織服務台影音 AI 執行點
- HomePod 01／02：組織聲音輸出區域
- penguin：不承擔使用者影音角色

## 真正產品閉環

```text
組織政策
→ 小J場景意圖
→ 8D ADI
→ Total Field
→ 器官／供應者選擇
→ 播音樂／調音量／切場景／播報／顯示
→ 回讀
→ 驗證
→ 收據
→ Odoo Community 狀態投影
```

這才是「組織影音 AI 小J」：不是一個會聊天的播放器，而是一個在被授權的組織場域裡，能看、能聽、能說、能播、能切場景、能協調設備，而且每個效果可驗證、可稽核、可回復的場控 AI。
