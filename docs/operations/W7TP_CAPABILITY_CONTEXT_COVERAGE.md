# W7TP 能力承接與動態上下文覆蓋契約

此文件記錄既有能力登錄、來源索引、任務狀態原胞與模型交付的接合；不建立第二核心、第二總場或正典。

## 來源與權威

以 taiji01 的 ACTIVE_W7TP_CANONICAL_POINTER.json 解析當前契約並驗證來源雜湊。八維為八合一單一動態狀態場；登錄類別數、索引條目數均不是八維定義。模型、節點、測試與雜湊不因上下文交付取得權威。

## 能力保留及有限覆蓋

- 保留原能力登錄的八類與各自狀態，包括 NVR_READ 的來源相容傳輸狀態；登錄狀態不冒充當前執行驗收。
- 沿既有 source_registry_refs 列出原生技能、次級雲能力、商家能力及 ADI 來源規則的識別碼；不匯入舊權威宣告、舊維度映射或原始規則內容。
- REQUIRED_CAPABILITY_IDS 與明示來源座標決定本任務必要能力，依既有 requires_capability_ids 追蹤必要依賴。未解析的必要能力只阻擋受影響任務上下文。
- 任何覆蓋聲明均綁定來源及範圍。未展開的來源、未量測的節點效果及未索引的外部內容保持明示未知；不得聲稱全部技術均已驗收。

## 指標優先與防遺漏

同一任務快照綁定能力投影、來源雜湊、已選證據與現行契約。模型啟動內容仍僅含單次拉取座標；本地暫態重構後才產生最小可見投影。任務不符、必要依賴遺漏、來源漂移、投影重算竄改或過期重放必須拒絕；不能靜默退回舊任務。

## 實作接點

- core/capability_internalization.py：登錄契約、來源索引與任務能力投影。
- tools/w7tp_task_state_local_rule.py：把能力投影納入同一快照與重構工作集。
- tools/w7tp_task_state_minimum_packet.py：對照封包綁定並形成模型投影。
- tools/total_field_dynamic_context_pull.py：單次取用、任務／能力綁定與回執。
- tools/w7tp_bridge_dynamic_context_transport_v1.py：精確匹配所有已登錄任務命名空間，不因旧 T-/XJ-模式退回其他任務。

## 生效及沿革

本文件不是上線證明。實際來源差異裁決、前後像、測試、發布與生效回觀測存於現有 runtime/developer_memory/CAPABILITY_CONTEXT_INTEGRATION_20261015，並由既有 WORK_LEDGER／ACTION_LEDGER 引用。若原有來源改變，只使受影響能力快照失效，不重開已完成的歷史工作。

升級前後均應核對能力識別、必要依賴、消費者與同任務效果，防止無授權淘汰能力。若回觀測失敗，以本次保存前像回復；不清理其他工作樹成果。
