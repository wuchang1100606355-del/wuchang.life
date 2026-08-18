# 小J本機 3D 互動核心

這是獨立本機成品；雙擊 `START_LOCAL.bat`（Windows）或 `start_local.sh`（Linux）即可啟動，服務只會繫結 `127.0.0.1:4173`。

核心模型的來源副本位於 `assets/xiaoj_single_core_geometry.glb`。原始來源未被覆寫；副本 SHA-256 與來源一致。

功能包含保留的 PBR 材質、即時七節骨架分區蒙皮、喜怒哀樂各三級、休止/A/E/I/O/U/M 嘴型、坐下/起立/步行/慢跑/跳躍，以及 `adi_mapping.json` 中的 8D ADI 0–1 浮點控制。

驗證回執：`receipts/LOCAL_VALIDATION_RECEIPT.json` 與 `receipts/BROWSER_SMOKE_RECEIPT.json`。
