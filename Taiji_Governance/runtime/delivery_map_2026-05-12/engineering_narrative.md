# Taiji Runtime 工程敘事收斂

本交付將象徵式度規語言收斂為可維護的工程 runtime 定義。

## 核心命名

- 主系統：五常智慧社區雲
- 治理總成：Taiji Hub 五維度規 AI 治理總成
- Odoo 主體：新北市三重區五常社區發展協會
- Odoo 社區主模組：`Taiji_Odoo/addons/wuchang_core`
- POS 正式名稱：主權 AI 商業用 POS 系統
- AI 呈現：一座小J，不拆成兩座 LLM

## 小J LLM 統一原則

小J在物理、外觀與使用者心智模型上是一座 AI。0.5B 小模型與較大工程模型不是兩個人格或兩個主體，而是同一個小J identity 內的分窗狀態。

分窗之間不得交換完整明文上下文。可交換的是座標化 `MetricPacket`，也就是高維度張量場狀態：

`μ = ⟨intent, node, auth, hazard, memory_ref, event_ref, output_contract, curvature⟩`

其中 `memory_ref` 使用 hash 或治理索引，不保存原始文字。

## 工程語彙替換

| 原始象徵語言 | 工程語彙 |
| --- | --- |
| 時空系統 | temporal event runtime |
| 量子態 | distributed state window |
| 度規張量場 | high-dimensional metric state |
| 匝道器語言 | coordinate MetricPacket protocol |
| 無文字記憶 | hash/reference-only context policy |

## 安全邊界

本交付不部署 production、不刪除容器、不清理 volume、不讀取 env secret、不將明文資料送往雲端。

所有高風險動作仍需：

- Five Metric Gate
- Taiji Gateway
- Audit record
- Rollback plan
- Human decision

