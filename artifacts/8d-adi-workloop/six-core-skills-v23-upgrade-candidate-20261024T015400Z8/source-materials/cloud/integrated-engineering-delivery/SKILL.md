---
name: integrated-engineering-delivery
description: 將使用者自創技術架構與自然語言意圖收斂成可執行、可回滾、可驗證、可稽核的整合式工程交付。用於系統盤點、故障修復、服務部署、容器與 Odoo 維運、8D/ADI 狀態場、主權 AI、生成式傳輸、跨節點協作、技術規格或一鍵命令；尤其適合要求最短路徑、合併指令、工程誠實、前後差異與證據成果的工作。不得以通用框架覆蓋使用者定義，也不得把效果相似判定為技術相同。
---

# 整合式工程交付

## 核心契約

- 先判斷可行性；可行才執行，不可行則指出缺口與最短解法。
- 以使用者自創架構、術語和權限邊界為設計權威；不得擅自套用既有產品分類取代原定義。
- 將「已證實事實、使用者定義、合理推論、待驗證主張、候選方案」分開標示。
- 效果等同不等於技術等同。涉及相同性、先前技術或結構性消除主張時，套用可用的技術身分稽核能力；不足即 HOLD，不推論專利性。
- 人格／表達層不得取得運算、資料或執行權；運算層只接收經授權的結構化主腦資訊。
- 高風險外部影響、不可逆變更、憑證、會員明文或跨節點寫入，必須先建立授權與回滾邊界。

## 執行流程

1. 用一句話重述預期產品效果與成功條件。
2. 盤點現況、真實名稱、路徑、服務、相依、權限與既有變更；禁止用示例值冒充實值。
3. 建立最小狀態表：`現況 | 目標 | 差距 | 證據 | 動作 | 回滾 | 驗證`。
4. 先做只讀探查；將未知值在同一工作流內動態取得，再交給後續命令。
5. 把相容的建立、修改、啟動與驗證收斂為一個可複製執行單元。加入 `set -Eeuo pipefail`、清楚錯誤出口及必要的備份或交易邊界。
6. 不將多個高風險變更藏進「一鍵」。遇到刪除、覆寫、正式服務停機、外傳或權限擴張時，先列出精確目標並取得必要授權。
7. 執行後同輪驗證語法、服務健康、產品輸出與不變條件；不能只以命令退出碼宣稱成功。
8. 交付人類易讀結果：結論、已完成、證據、未完成／HOLD、回滾點與下一個最有價值動作。

## 自創架構防誤譯閘門

每次處理使用者自創技術時，先讀取 [references/architecture-contract.md](references/architecture-contract.md)。

- 保留 8D/ADI、總場、主腦資訊、人格腦、小J、生成式傳輸、離散狀態查表、無浮點與驗證消除等原始語義。
- 可用既有技術作效果或介面比較，但須明示只是比較對象，不能改名、歸類或宣稱同源。
- 將「零浮點誤差」「免驗證」「降低傳輸量／成本」視為須由程式、測試或文件證據支持的技術主張。
- 零浮點應限於身分、裁決與重構核心，不能擴寫為所有資料運算禁用浮點。
- 「免驗證」須精確指出被結構性消除的驗證操作；封包完整性、權限與治理驗證不得一併取消。
- 不讀取原始敏感明文；需要時只處理最小化、脫敏、授權且可稽核的資料包。

## 一鍵產物標準

優先輸出一份完整執行檔或單一命令區塊，內含：

- 環境與真實目標探測
- 前置條件檢查
- 精確變更
- 錯誤即停與可恢復備份
- 健康檢查與產品級輸出驗證
- 前後狀態摘要

若未實際連上目標設備，只能交付「候選執行包」，並明確標記未執行，禁止寫成已修復。

## 人類易讀交付

- 優先使用短段落、編號與單行數據；只有精確映射確實更清楚時才用表格。
- 交付前檢查實際渲染或終端可讀性；不得把原始 Markdown、過寬表格或機器清單冒充完成品。
- 量化只限可重現的契約覆蓋、測試數、狀態差異與效能實測；不得把規則數增加包裝成速度、準確率或商業效益提升。
- 安裝可用、候選審查與正式啟用必須分開陳述。

## 完成定義

只有同時滿足下列條件才可宣告完成：

- 需求效果已出現，而非僅建立檔案。
- 使用者原定義與權限邊界未被破壞。
- 驗證證據可由人類快速閱讀。
- 失敗可定位，變更可回復或有明確恢復路徑。
- 未知與待證事項沒有被潤色成事實。

## Version and causal discipline

Read the installed `govern-total-field-skills` reference `references/version-observation-causality.md` before version migration, current-readiness claims, original-cell comparisons, or causal conclusions. Resolve the skill by name; do not invent a path if unavailable. Keep claims bound to node/object/state/time, distinguish queued from executed and queries from reconstruction, and keep unavailable guard execution as `NOT_RUN`. Preserve the interacting single 8D state field and the user's existing authorization.


## 治理定義

使用 `total-field-skill-manifest.json` 作為本技能候選定義。最高效果 E5 表示涵蓋受治理的正式變更，不是預先授權；每次依實際動作與既有授權判斷適用閘門。單純唯讀觀測不必先滿足部署前置條件。manifest 通過不等於總場正式啟用。

## Single current design

Use `govern-total-field-skills` → `references/current-design-contract.json` as the single Founder V2.3 design root. Read its `references/version-observation-causality.md` for causal-chain changes. Revalidate dependent references, validators and state indexes after changes; do not choose an older design as fallback. Historical evidence stays historical. ADI binds state, time, spatial/object location, relations, causality and reconstruction coordinates together. Preserve actual runtime schema differences as local migration gaps.

## Cross-runtime capability reuse

When MSI, servers, plugins or tool servers provide a needed capability, read the installed `govern-total-field-skills` reference `references/capability-interoperability.md`. Reuse observed existing providers through the exact authorized node and input/output contract. Preserve unfinished prior work and distinguish file presence, tool exposure, connectivity, execution and verified effect.

