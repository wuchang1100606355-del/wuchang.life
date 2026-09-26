# W7TP／8D ADI 音效開源市場物件媒合 V1

STATE=PASS_RESEARCH_MATCH_CANDIDATE_ONLY
ROLE=8D ADI（八維自適應意圖）單一狀態場的開源能力媒合，不是第二套音效權威。
RUNTIME_INSTALL=FALSE（尚未安裝任何外部模組）

## 1. Founder Intent（創辦人意圖）觀測結果

不是「找一套播放器」；真正需求是把 Nahimic（音效處理套件）、Apple Music（蘋果音樂）、HomePod（蘋果智慧喇叭）與所有節點的**效果語義、播放來源、輸出座標、設備狀態、音量／增益、場景、稽核收據**拆成可替換能力，最後由 8D ADI（八維自適應意圖）／Total Field（總場）決定何時、在哪個節點、使用哪個 provider（供應者）產生效果。

Odoo Community（Odoo 社群開源版）只做 control surface（控制介面）、device registry（設備登錄）、job queue（工作佇列）、audit evidence（稽核證據）與狀態投影；不能成為音效權威。

## 2. 8D 同時媒合條件

- D1 Intent（意圖）：Nahimic 等價效果、Apple Music 來源、HomePod／多房播放、全節點音效控制。
- D2 State（狀態）：既有 Audio Field（音效場）與 topology（拓撲）已存在；Odoo 音效模型仍不足。
- D3 Coordinate（座標）：taiji01 為 broker（仲介）／總場入口；MSI、taiji03 為 Windows 音效工作站；HomePod 為網路輸出；taiji04／drallion 尚有 HOLD（暫停）。
- D4 Evidence（證據）：現有 Nahimic 能力證據、全節點拓撲、Odoo wuchang.device.audio、開源專案程式庫與授權。
- D5 Policy（政策）：local-first（本地優先）、provider replaceable（供應者可替換）、不建立第二權威、不預設把 raw audio（原始音訊）送雲端。
- D6 GST（生成式狀態傳輸）：跨節點預設傳 state refs（狀態參照）、rule refs（規則參照）、receipt（收據），不是把原始音訊當成治理資料。
- D7 Risk（風險）：Apple Music DRM（數位版權管理）／服務條款、GPL／AGPL 授權邊界、Windows APO（Windows 音訊處理物件）相容性、AirPlay（隔空播放）配對與服務發現。
- D8 Authority（權威）：僅 taiji01 Total Field（taiji01 總場）。

## 3. 媒合結果

| 開源物件 | 在你系統中的角色 | 直接可用能力 | 目前判定 |
|---|---|---|---|
| Music Assistant（音樂助理） | Media broker（媒體仲介） | Apple Music provider（蘋果音樂供應者）、AirPlay 1/2（隔空播放 1/2）、HomePod、多房同步、metadata（中繼資料）、WebSocket／HTTP JSON-RPC API（網頁插座／HTTP JSON-RPC 介面） | PRIMARY_CANDIDATE（主要候選） |
| CamillaDSP（Camilla 數位訊號處理） | DSP engine（數位訊號處理引擎） | IIR／FIR（無限脈衝／有限脈衝濾波）、convolution（卷積）、gain（增益）、volume（音量）、loudness（響度）、limiter（限制器）、compressor（壓縮器）、noise gate（雜訊閘）、mixer（混音器）、WebSocket（網頁插座） | PRIMARY_CANDIDATE（主要候選） |
| pyCamillaDSP（CamillaDSP Python 控制庫） | Total Field → DSP adapter（總場到 DSP 轉接器） | Python（Python 程式語言）控制與狀態回讀 | PRIMARY_ADAPTER_CANDIDATE（主要轉接候選） |
| Equalizer APO（等化器音訊處理物件） | Windows local DSP（Windows 本機數位訊號處理） | system-wide（全系統）parametric／graphic EQ（參數／圖形等化器）、convolution（卷積）、VST plugin（VST 外掛）、低延遲 | WINDOWS_PROVIDER_CANDIDATE（Windows 供應者候選） |
| EasyEffects（簡易音效） | Linux PipeWire effect provider（Linux PipeWire 音效供應者） | EQ、compressor、limiter、convolver、noise reduction、speech processor 等 | SECONDARY_LINUX_PROVIDER（次要 Linux 供應者） |
| Snapcast（同步音訊廣播） | 非 Apple 多房同步 | 多節點時間同步、FLAC／Opus、HTTP／WebSocket／JSON-RPC 控制、Linux／Android／Windows client（客戶端） | SECONDARY_MULTIROOM_CANDIDATE（次要多房候選） |
| pyatv（Apple 裝置 Python 控制庫） | HomePod 輕量備援 adapter（轉接器） | Zeroconf（零組態）發現、metadata、volume（音量）、AirPlay stream file（隔空播放檔案串流） | FALLBACK_ADAPTER_CANDIDATE（備援轉接候選） |
| Shairport Sync（AirPlay 同步接收器） | Apple 音訊 ingress（輸入） | 把 iPhone／Mac AirPlay 音訊接入本地音效場 | INGRESS_CANDIDATE（輸入候選） |
| OCA iot_oca（OCA 物聯網基座） | Odoo Community（Odoo 社群開源版）設備基座 | iot.device、device group、tag、communication system、device action | PRIMARY_ODOO_BASE_CANDIDATE（主要 Odoo 基座候選） |
| OCA Connector／Components（OCA 連接器／元件） | Odoo provider adapter layer（Odoo 供應者轉接層） | decoupled components（解耦元件）、events（事件）、connector pattern（連接器模式） | PRIMARY_ODOO_ADAPTER_CANDIDATE（主要 Odoo 轉接候選） |
| OCA queue_job（OCA 工作佇列） | 非同步效果請求 | job queue（工作佇列）、retry（重試）、batch（批次）、cron（排程） | PRIMARY_ODOO_ASYNC_CANDIDATE（主要 Odoo 非同步候選） |
| OCA auditlog（OCA 稽核紀錄） | D4 Evidence（第四維證據） | model audit（模型稽核）、HTTP session／request（HTTP 工作階段／請求）紀錄 | PRIMARY_ODOO_AUDIT_CANDIDATE（主要 Odoo 稽核候選） |

## 4. 最吻合你設計的組合

```text
Apple Music（蘋果音樂）／本地媒體
        │
        ▼
Music Assistant（音樂助理）
        │
        ├── AirPlay 1/2（隔空播放 1/2）→ HomePod（蘋果智慧喇叭）
        ├── Snapcast（同步音訊廣播）→ Android／Windows／Linux 節點
        └── Audio state（音訊狀態）→ Total Field（總場）
                                  │
                                  ▼
                         8D ADI（八維自適應意圖）
                                  │
                         ┌────────┴────────┐
                         ▼                 ▼
              CamillaDSP（數位訊號處理）  Odoo Community（Odoo 社群開源版）
                         │                 │
                 effect execution       iot_oca（物聯網基座）
                 （效果執行）             Connector（連接器）
                                           queue_job（工作佇列）
                                           auditlog（稽核紀錄）
```

Odoo Community（Odoo 社群開源版）不直接承載 Apple Music DRM（蘋果音樂數位版權管理）或 DSP（數位訊號處理）演算法；它只持有 reference（參照）、desired state（期望狀態）、observed state（觀測狀態）、request（請求）與 receipt（收據）。

## 5. Nahimic（音效處理套件）等價重構

Nahimic 的 10-band EQ（10 段等化器）、bass（低頻）、treble（高頻）、voice clarity（語音清晰）、surround（環繞）、microphone processing（麥克風處理）不再綁定 A-Volute（A-Volute 供應者）。

建議語義層固定為既有 8D ADI Audio Field（8D ADI 音效場），provider（供應者）按座標選擇：

- MSI／taiji03：Equalizer APO（等化器音訊處理物件）或 CamillaDSP（Camilla 數位訊號處理）。
- taiji01：CamillaDSP（Camilla 數位訊號處理）做 headless DSP（無介面數位訊號處理）／broker-side DSP（仲介端數位訊號處理）。
- Linux PipeWire（Linux PipeWire 音訊系統）節點：EasyEffects（簡易音效）可作本機 provider（供應者）。
- HomePod：Music Assistant AirPlay provider（音樂助理隔空播放供應者）；pyatv 作小型備援。

## 6. Apple Music（蘋果音樂）邊界

Music Assistant（音樂助理）目前程式庫內已有 stable Apple Music provider（穩定版蘋果音樂供應者），但其播放路徑使用 pywidevine（Widevine Python 庫），專案文件也要求使用者自行提供 CDM（內容解密模組）材料。

因此目前只把它列為 capability candidate（能力候選），**不自動啟用 Apple Music provider（蘋果音樂供應者）**。在 D7（第七維風險）完成授權／服務條款／技術邊界確認以前，可先保留現行 MSI Apple Music（MSI 蘋果音樂）本機來源，再把已允許的播放狀態送入音效場。

## 7. Odoo Community（Odoo 社群開源版）落地方式

不找「一顆萬能 Odoo 音效外掛」。應用 OCA（Odoo 社群協會）的四個成熟基座，把你現有 `wuchang.device.audio` 從簡單的播放／音量模型升級成 provider-neutral audio state surface（供應者中立音訊狀態表面）：

```text
iot_oca（物聯網基座）
  └─ device / group / communication system / action

component + component_event + connector（元件＋元件事件＋連接器）
  └─ Music Assistant / CamillaDSP / pyatv adapters（轉接器）

queue_job（工作佇列）
  └─ 非同步 request（請求），不阻塞 Odoo

auditlog（稽核紀錄）
  └─ D4 Evidence（第四維證據）
```

正式 effect（效果）仍必須：

```text
Odoo request（Odoo 請求）
→ 8D ADI（八維自適應意圖）
→ Total Field（總場）
→ provider adapter（供應者轉接器）
→ runtime effect（執行環境效果）
→ readback（回讀）
→ receipt（收據）
→ Odoo observed state（Odoo 觀測狀態）
```

## 8. 目前不做的事

- 不直接把外部專案 install（安裝）到 production runtime（正式執行環境）。
- 不讓 Music Assistant（音樂助理）、CamillaDSP（數位訊號處理）、Odoo Community（Odoo 社群開源版）或任何裝置取得 D8 Authority（第八維權威）。
- 不把 raw audio（原始音訊）當成跨節點治理預設資料。
- 不因為找到 Apple Music provider（蘋果音樂供應者）就繞過 DRM（數位版權管理）或服務條款。
- taiji04／drallion 的 D3（第三維座標）與 runtime（執行環境）HOLD（暫停）未閉合前，不納入正式音效輸出。

## 9. 結論

這次媒合不是找單一替代 Nahimic 的軟體，而是找到可拼成你原設計的開源 capability fabric（能力織網）：

**Music Assistant（音樂助理）負責媒體與 HomePod；CamillaDSP（數位訊號處理）負責 Nahimic 等價效果語義執行；Equalizer APO（等化器音訊處理物件）補 Windows 系統級音效；Snapcast（同步音訊廣播）補非 Apple 多房節點；OCA iot／connector／queue_job／auditlog（OCA 物聯網／連接器／工作佇列／稽核紀錄）把能力收納進 Odoo Community（Odoo 社群開源版）控制與證據表面；8D ADI（八維自適應意圖）／Total Field（總場）保持唯一裁決。**
