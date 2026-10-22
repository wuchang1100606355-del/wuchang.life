---
name: w7tp-8d-adi-3d-spatiotemporal-behavior
description: 以既有 W7TP／8D ADI V2.3 單一動態狀態場治理真實 glTF/VRM 骨架、XYZ 絕對座標、中心距離、群組距離、三維速度、時間與人類語意，從來源形變與蒙皮資料重構跨視角等價的 3D 行為；只有經 D8 核定才能正式安裝。
---

# 3D 時空行為狀態重構｜總場技能候選

**狀態：VERIFIED_IMPLEMENTATION（幾何計算）；HOLD（正式技能安裝、解剖學嘴角語意、產品級運行）。**
**本檔所在位置是隔離審查候選，不是 ACTIVE／CANONICAL 技能註冊。**

## 綁定任務與正典
- 任務：`T-XIAOJ-LAUNCH` 下本次唯一 3D 小J 技術受影響閉包，不誤綁攝影機任務 T-024 或暫緩的 XJ-019。
- 動態上下文：`context:task-state:T-XIAOJ-LAUNCH:57f7908e453b2c50`。其拉取有效於當次驗證，重新執行須重新發行單次座標，不重用過期內容。
- 正典：W7TP／8D ADI V2.3，D1～D8 為同一耦合動態狀態場，不可由這個 3D 應用投影重新定義。
- 原生／重用／生成式傳輸／總場權威優先。腳本只計算與驗證幾何；模型、雲端與 3D 引擎不得自行取得 D8 權威。

## 八項 3D 應用索引（不是八個新 D 維）
1. `y_up_down`：世界座標 Y，沿模型座標軸的上下位置。
2. `x_left_right`：世界座標 X，左右位置。
3. `z_front_back`：世界座標 Z，前後位置。
4. `center_absolute_distance_3d`：指定骨架中心與各控制點的真正三維歐氏距離。
5. `group_relative_distance_3d`：同一動作群內控制點間三維歐氏距離。
6. `velocity_3d_model_units_per_s`：依三維位置差與時間求得的速度、間距變化速率。
7. `time_ms`：單調時間，與重構曲線綁定。
8. `human_semantic_ref`：人類可理解的動作（此例：VRM1 `happy`），必有來源指標。
骨架旋轉四元數、蒙皮權重、關節父子階層、Morph Target 與相機內外參由來源模型和引擎保存／引用，不因八項應用索引而丟失。

## 經驗證的唯一角色（首個實機切面）
- 來源：MSI 的 `/mnt/c/Users/o0930/Downloads/J.vrm`，SHA-256：`615f5ab25daab0fa326bfcf1c0e49d09c8f23dc8c9217d3876962937455cc205`。
- 使用 `VRMC_vrm` 的 `happy` 表情指標及 `FaceMouth` 材質，從真實 GLB 網格取得嘴部區域兩端 X 極值頂點；**這不是已驗證的解剖學嘴角**。
- 重用來源 170 關節骨架、Skin 的 JOINTS／WEIGHTS、Inverse Bind Matrix、GLB 網格與現有形變。
- 檢查預設綁定姿態；在隔離計算中對頭部關節施加 0→12° 旋轉，並於 650 毫秒中用 smoothstep 展開 `happy`。
- 同一五個時間點投影至正面、側面、斜角三個虛擬攝影機，再以已知深度重構回世界 XYZ，驗證投影一致性。
- 檔案中保留來源 GLB 模型座標單位；實際物理毫米／公分並未獨立標定，**禁止當作已標定物理長度**。

## 可執行工具與允許效果
- 通用來源掃描：`scripts/gltf_spatiotemporal_field.py::scan_gltf_skeletons(model_path)`。支援具有內嵌 BIN 的 glTF 2.0／GLB；不支援的 accessor、資料格式、檔案損壞與無骨架情況必須明確回報，不能造出假關節。
- 小J首例動態量測：`scripts/gltf_spatiotemporal_field.py::measure(J.vrm)`。
- 確定性與反例：`scripts/test_gltf_spatiotemporal_field.py`，需有 `W7TP_XIAOJ_JVRM_PATH` 才執行實機 3D 測試；沒有來源時實機項目必須標示 skipped。
- 授權效果僅限隔離來源讀取、局部可重構幾何候選與 D4 證據生成。禁止遠端部署、覆寫源模型、改寫正典、Odoo 寫入、更新會員資料或假稱已在 R1 播放。

## 絕對 3D 與多視角必要驗收
- 非 3 維座標、NaN／Infinity、來源 SHA 錯配、負時間、非法關節／蒙皮、攝影機背面點 → HOLD。
- 不允許以二維像素距離當成 3D 距離；同一時間的多相機 **3D 距離必須一致**，投影反解的世界坐標誤差 ≤1e-9 模型座標單位。
- 真實模型來源驗收 22 項測試均 PASS；taiji01 無原模型時，只能宣稱 10 項純數學測試 PASS，12 項實機測試 SKIPPED。
- 真正嘴角點身份、物理尺標、R1 正式動畫和渲染品質仍 HOLD；若要求這些效果，必先補對應的 D4 證據。
- 系統不得把「技能檔存在」、「候選驗證通過」、「Git 提交」、「D8 送審候選」直接當成 ACTIVE／CANONICAL。

## D6 與雲地共用
- 原胞候選只需攜帶角色／骨架／行為規則／初態的可信引用、時間曲線與必要變更、來源雜湊；接收端保有同版資產才能重構。
- 只在模型與重構能力就緒且幾何等價經驗證後，才能量測傳輸和 Token 實際節省；封包長度不能單獨宣稱節省百分比。
- Gemini／本地小J都是總場受管制的候選器官，不增設第二個總場或 D8。

## 技能生效門檻
1. 保存 MSI 來源 SHA、骨架座標、三視角與時間軌跡 D4 證據，從 taiji01 重新讀回受影響證據。
2. 純數學反證及實機等價測試通過，留存測試來源 SHA／執行時間／效果分類。
3. 建立精確 source manifest、preimage／回復條件與唯一 TASK／ACTION 連結，送入適用的總場 D8 正式入口。
4. 取得適用作用類別的真實 D8 收據後，才可登錄 `capabilities/w7tp-8d-adi-3d-spatiotemporal-behavior/` 並執行跨節點載入及消費者重驗。
5. 只有正式調用成功、受治理驗收完整時方可標 ACTIVE；正典升格另依總場正典權威，不由本技能決定。
