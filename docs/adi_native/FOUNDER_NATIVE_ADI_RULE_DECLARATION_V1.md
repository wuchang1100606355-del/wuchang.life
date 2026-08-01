# Founder Native ADI Rule Declaration V1

STATUS=`CURRENT_FOUNDER_CANONICAL`  
HISTORICAL_SOURCE=`NO`  
IMPLEMENTATION_SOURCE=`YES`  
FOUNDER_AUTHORITY=`CHIANG_CHENG_LUNG`  
EXTERNAL_SUBSTITUTION=`FORBIDDEN`

This declaration records the current Founder canonical supplied for
`W7TP_NATIVE_ADI_P1_20260722T171323Z`. It does not claim to be an early
historical source.

## ADI正典演算法血統與規則職責鎖定

本章只鎖定Founder授權的文件層規則與血統角色；文件本身不授權或
證明實作修改、測試執行或核心落地。

`SHORT_COMMIT=60d8a06`

`短提交雜湊=60d8a06`

`FULL_COMMIT=60d8a0657992aa108df42c37617b3615765054a0`

`完整提交雜湊=60d8a0657992aa108df42c37617b3615765054a0`

`CANONICAL_ALGORITHM_LINEAGE=60d8a0657992aa108df42c37617b3615765054a0`

`正典演算法主血統=60d8a0657992aa108df42c37617b3615765054a0`

`CANONICAL_IMPLEMENTATION_ROOT=core/adi_native`

`正典演算法實作根目錄=core/adi_native`

`REQUIRED_LINEAGE_COMMITS=["c1f48b71","4e0cae0","d4dd90c","60d8a06","64656aa"]`

`必要血統提交=["c1f48b71","4e0cae0","d4dd90c","60d8a06","64656aa"]`

### 血統角色

1. `LINEAGE=c1f48b71`（血統提交=`c1f48b71`）

   `ROLE=GOVERNANCE_AND_REF_ONLY_VERIFICATION_CONTRACT`

   `角色=5D引用式結構、治理與只引用驗證契約`

   `ALGORITHM_AUTHORITY=FALSE`

   `演算法權威=否`

2. `LINEAGE=4e0cae0`（血統提交=`4e0cae0`）

   `ROLE=DESIGN_FIXTURE_AND_ALGORITHM_UNSPECIFIED_REFERENCE_ONLY`

   `角色=演算法未指定的設計與測試夾具，僅供參考`

   `ALGORITHM_AUTHORITY=FALSE`

   `演算法權威=否`

3. `LINEAGE=d4dd90c`（血統提交=`d4dd90c`）

   `ROLE=LEGACY_PRODUCT_PROTOTYPE_AND_SQUARE_SPIRAL_COLLISION_PLACEMENT_ADAPTER`

   `角色=歷史產品原型與方形螺旋碰撞配置適配器`

   `CANONICAL_DISTANCE_AUTHORITY=FALSE`

   `正典距離權威=否`

4. `LINEAGE=60d8a06`（血統提交=`60d8a06`）

   `ROLE=CANONICAL_NATIVE_ADI_ALGORITHM_LINEAGE`

   `角色=正典Native ADI演算法主血統`

5. `LINEAGE=64656aa`（血統提交=`64656aa`）

   `ROLE=CANONICAL_CONSUMER_PROMOTION_NOT_ADI_ALGORITHM_AUTHORITY`

   `角色=正典消費者提升紀錄，不是ADI演算法權威`

`EXTERNAL_REPORT_ROLE=REFERENCE_ONLY_UNVERIFIED`

`外部研究報告角色=僅供參考且未驗證`

`CLAIMED_W7TP_ADI_CANDIDATE_ZIP=NOT_FOUND_NOT_AUTHORITY`

`宣稱的w7tp_adi_candidate.zip=未找到且不具權威性`

### 時間座標與目前時間查詢原點

#### 永久時空索引座標

`PERMANENT_TIME_SLOT=STABLE_NON_NEGATIVE_INTEGER_COORDINATE`

`永久時間槽位=穩定非負整數座標`

既有 `tau_F` 時間槽位可作為穩定儲存座標。永久索引不得因目前時間
改變而重編。

#### 查詢距離原點

`CURRENT_QUERY_ORIGIN=EXPLICIT_CURRENT_LOGICAL_TIME_INPUT`

`目前查詢原點=明確傳入的目前邏輯時間`

`CURRENT_QUERY_SLOT=TAU_F(CURRENT_LOGICAL_TIME)`

`目前查詢槽位=目前邏輯時間對應的整數槽位`

目前邏輯時間必須由呼叫端明確傳入；ADI核心不得自行讀取系統時鐘。

`TIME_AXIS_ABSOLUTE_DISTANCE=ABS(TAU_F(STATE_LOGICAL_TIME)-TAU_F(CURRENT_LOGICAL_TIME))`

`時間軸絕對距離=狀態時間槽位與目前時間槽位的整數絕對差`

`TIME_AXIS_ABSOLUTE_DISTANCE_ROLE=CURRENT_TIME_PROXIMITY_AND_TIME_ORDERING`

`時間軸絕對距離用途=判定合法狀態離目前時間多遠，以及進行時間排序`

`TRANSITION_PATH_DISTANCE=SUM(STEP_COST_UINT)`

`狀態轉移路徑距離=正典轉移步驟非負整數成本總和`

`TRANSITION_PATH_DISTANCE_ROLE=LEGAL_PATH_COST_AND_NATIVE_ADI_SHELL_FORMATION`

`狀態轉移路徑距離用途=判定狀態場合法路徑成本，以及形成Native ADI距離殼層`

`DISTANCE_VALUE_TYPE=NON_NEGATIVE_INTEGER`

`距離值型態=非負整數`

`GEOMETRIC_STRAIGHT_LINE_CLAIM=FALSE`

`幾何直線距離主張=否`

不得將永久儲存原點改成目前時間，也不得把浮點時間差作為正典索引
主鍵。時間槽位差只能稱為 `TIME_AXIS_ABSOLUTE_DISTANCE`（時間軸絕對
距離），不得稱為 `GEOMETRIC_STRAIGHT_LINE_DISTANCE`（幾何直線距離）。
下文的 `delta_F` 保持為 `TRANSITION_PATH_DISTANCE`（狀態轉移路徑
距離），即唯一Founder正典路徑的整數轉移成本；兩種距離不得互相替代。

### 真實方向

`TRUE_DIRECTION_SOURCE=STATE_FIELD_TRANSITION_TOPOLOGY`

`真實方向來源=狀態場轉移拓撲`

真實方向不得只由時間正負差、檔案先後順序、模型語意推測、幾何座標
方向或方形螺旋位置判定。狀態方向至少由以下引用共同界定：

- `PREDECESSOR_STATE_REF`（前置狀態引用）
- `CURRENT_STATE_REF`（目前狀態引用）
- `SUCCESSOR_STATE_REFS`（合法後繼狀態引用）
- `TRANSITION_RULE_REF`（狀態轉移規則引用）
- `DIRECTION_CODE`（方向碼）
- `AUTHORITY_REF`（權威引用）
- `BREAKPOINT_SEGMENT_REF`（斷點區段引用）

`TIME_DISTANCE=HOW_FAR_FROM_CURRENT_TIME`

`時間距離=離目前時間多遠`

`STATE_DIRECTION=WHICH_EVOLUTION_PATH_IS_REAL_AND_LEGAL`

`狀態方向=哪一條演化路徑是真實且合法`

不得把 `SIGNED_TIME_DELTA`（帶正負號的時間差）直接宣稱為真實方向。

### 斷點與可達性

`BREAKPOINT_ROLE=HARD_REACHABILITY_BOUNDARY`

`斷點角色=可達性硬邊界`

`BREAKPOINT_V1_MODE=HARD_SEGMENT_BOUNDARY_NO_CROSS_SEGMENT_EXCEPTION`

`斷點V1模式=斷點區段硬邊界，不允許跨區段例外`

`STATE_PACKET_BREAKPOINT_SEGMENT_REF=OPTIONAL_FOR_LEGACY_CONSTRUCTION_REQUIRED_FOR_BREAKPOINT_QUERY`

`狀態封包斷點區段引用=舊建構可省略，進入斷點感知查詢時必須存在`

`TRANSITION_RULE_BREAKPOINT_POLICY_REF=OPTIONAL_FOR_LEGACY_CONSTRUCTION_REQUIRED_FOR_BREAKPOINT_QUERY`

`轉移規則斷點政策引用=舊建構可省略，進入斷點感知查詢時必須存在`

`MISSING_BREAKPOINT_EVIDENCE=HOLD_BREAKPOINT_EVIDENCE_INCOMPLETE`

`缺少斷點證據=暫停：斷點證據不足`

`CROSS_SEGMENT_REACHABILITY=DENY_BREAKPOINT_CROSSED`

`跨區段可達性=禁止：跨越斷點`

若候選狀態與目前狀態跨越斷點：

`BREAKPOINT_CROSSED=TRUE`

`跨越斷點=是`

`REACHABILITY=DENIED`

`可達性=禁止`

`CONTEXT_RETRIEVAL=DENIED`

`上下文取用=禁止`

斷點判斷優先於距離排序。查詢順序固定為：

1. D1身分與主權主體限制。
2. D2意圖與場景限制。
3. 斷點區段與可達性限制。
4. 狀態場真實方向判定。
5. 以目前邏輯時間計算時間軸絕對距離。
6. D4證據有效性。
7. D5資源可用性。
8. D7風險與隱私限制。
9. D8權威與封套裁決。
10. 取用最少必要上下文。

最近的狀態不等於可取用狀態。

### Native ADI螺旋角色

`NATIVE_ADI_SPIRAL_ROLE=ORDERED_REACHABLE_DISTANCE_SHELL_TRAVERSAL`

`Native ADI螺旋角色=合法可達距離殼層的順序遍歷`

`NATIVE_ADI_SHELL_DISTANCE=TRANSITION_PATH_DISTANCE`

`Native ADI距離殼層依據=狀態轉移路徑距離`

`SHELL_0=CURRENT_LEGAL_STATE`

`距離殼層零=目前合法狀態`

`SHELL_1=FIRST_NEAREST_LEGAL_REACHABLE_STATES`

`距離殼層一=第一層最近合法可達狀態`

`SHELL_N=TRANSITION_PATH_DISTANCE_AND_REACHABILITY_EXPANSION_N`

`距離殼層N=依正典轉移成本及可達性向外擴張的第N層狀態集合`

Native ADI的 `SPIRAL_F`（Native螺旋遍歷）不得被宣稱為物理螺旋線
長度、幾何螺旋公式、固定相位螺旋、含半徑角度及節距的螺旋線，或
浮點旋轉座標。

### 方形螺旋角色

`SQUARE_SPIRAL_ROLE=COLLISION_PLACEMENT_OR_VISUAL_ORDER_ONLY`

`方形螺旋角色=僅用於碰撞配置或視覺順序`

`SOURCE_LINEAGE=d4dd90c`

`來源血統=d4dd90c`

`SOURCE_ROOT=services/w7tp_native_adi`

`來源根目錄=services/w7tp_native_adi`

方形螺旋不得成為正典狀態距離、真實方向來源、狀態轉移成本、時空
距離、Founder權威判定或動態上下文距離。方形螺旋可由未來適配器
引用，但不得覆蓋Native ADI正典距離。

### 浮點運算資料索引

`ADI_PRIMARY_INDEX=INTEGER_DETERMINISTIC_STATE_INDEX`

`ADI主索引=整數決定性狀態索引`

`FLOAT_DATA_INDEX_ROLE=SECONDARY_NUMERIC_INDEX_REFERENCED_BY_INTEGER_ADI_STATE`

`浮點資料索引角色=由整數ADI狀態引用的次級數值索引`

浮點資料至少應綁定：

- `ADI_STATE_REF`（ADI狀態引用）
- `FLOAT_SERIES_REF`（浮點資料序列引用）
- `VALUE`（數值）
- `UNIT`（單位）
- `LOGICAL_TIME`（邏輯時間）
- `RULE_VERSION`（規則版本）
- `SOURCE_REF`（來源引用）

浮點資料可承載感測器資料、模型信心值、媒體座標、連續狀態演化
結果、資源負載、音訊或影像特徵，以及其他連續運算結果。

浮點資料不得作為身分、主權主體、權限、斷點、正典狀態、Founder
角色、狀態轉移權威或證據來源的唯一權威鍵。

### 明確不授權項目

`GEOMETRIC_HELIX_AUTHORIZED=FALSE`

`幾何螺旋已授權=否`

`FIXED_PHASE_AUTHORIZED=FALSE`

`固定相位已授權=否`

`PITCH_RADIUS_ANGLE_FORMULA=NOT_AUTHORIZED`

`節距、半徑與角度公式=未授權`

`SEMANTIC_EMBEDDING_AS_ADI_DISTANCE=DENIED`

`將語意嵌入當作ADI距離=禁止`

`FLOAT_AS_PRIMARY_AUTHORITY_INDEX=DENIED`

`浮點數作為主要權威索引=禁止`

`TREE_INDEX_AS_CANONICAL_ADI=DENIED`

`樹狀索引作為正典ADI=禁止`

`EXTERNAL_REPORT_AUTO_IMPORT=DENIED`

`外部研究報告自動匯入=禁止`

`DELETED_ERROR_BRANCH_RESTORE=DENIED`

`恢復已刪錯誤分支=禁止`

### 8D與ADI分工

`D3=CURRENT_LOGICAL_TIME_AND_STATE_COORDINATE`

`D3=目前邏輯時間與狀態座標`

`D1_D2_D4_D5=GOVERNED_QUERY_CONSTRAINTS`

`D1、D2、D4、D5=受治理的查詢限制`

`D7_D8=CONTEXT_USE_AND_AUTHORITY_DECISION`

`D7、D8=上下文取用與權威裁決`

ADI負責穩定非負整數索引、時間軸絕對距離、狀態轉移路徑距離、距離
殼層遍歷與可達候選排序。

8D負責身分、意圖、證據、資源、生成式傳輸、風險、權威，以及是否
允許取用與執行。

正典摘要：「現在決定距離，狀態場決定方向，斷點決定能否到達，8D
決定是否可以取用與執行。」

### 文件層與核心落地邊界

`DOCUMENT_RULE_BOUND=TRUE`

`文件規則綁定=是`

`DECLARATION_DOCUMENT_ROLE=NORMATIVE_RULE_BINDING_NOT_RUNTIME_STATUS_LEDGER`

`宣告文件角色=規則綁定文件，不是執行狀態帳本`

`DECLARATION_CHANGE_DOES_NOT_BY_ITSELF_AUTHORIZE_CORE_LANDING=TRUE`

`宣告變更本身不授權核心落地=是`

`CORE_LANDING=HOLD_PENDING_FOUNDER_APPROVAL`

`核心落地=等待Founder核准`

## Direct storage projection

`tau_F(t) = floor(((t - T_min) / (T_max - T_min)) * N)`.

`DIRECT_SLOT_F(P_t) = SLOT_LOOKUP_F(namespace, state_profile, tau_F(t),
native_state_ref, canonical_version, rule_version)` and returns a non-negative
integer. It is an O(1) storage projection, not complete `PHI_F` and not an
authoritative state.

## 8D state, polarity, metric and cross-section

`P_t=<D1_t,...,D8_t>` and `X_F(P_t)=<x_1,...,x_8>`, where each `x_i` is an
integer selected by the Founder canonical rule table. No floating confidence,
similarity or model scoring is permitted.

`B_F_plus` requires intent satisfied, evidence valid, life safe and other-rights
safe. `B_F_minus` is reached by intent violation, causal-order violation, life
harm, other-rights harm or hard risk. Life or other-rights harm is
`BLOCK_ABSOLUTE_REDLINE`.

For each dimension, `boundary_state_F` is `+1` for the positive predicate,
`-1` for the negative predicate, and `0` when unresolved. Negative takes
precedence when predicates conflict.

`METRIC_SIGNATURE_F(P_t)=<logical_time,topology_coordinate_ref,
previous_state_root,evidence_root,event_hash_ref,canonical_version,
rule_version>`.

`SIGMA_F(P_t)=<tau_F(t),DIRECT_SLOT_F(P_t),X_F(P_t),boundary_state_F(P_t),
METRIC_SIGNATURE_F(P_t)>`.

## Founder transitions, direction and absolute distance

Every transition rule contains `transition_rule_id`, `from_state_code`,
`to_state_code`, `preconditions`, `required_evidence_refs`, `polarity`,
`direction_code`, positive `step_cost_uint`, `rule_version`, and optional
`breakpoint_policy_ref`. Every breakpoint-aware transition requires a non-empty
policy reference.

每一轉移規則均保留既有欄位，並可在尾端提供 `breakpoint_policy_ref`
（斷點政策引用）；所有斷點感知轉移都必須提供非空政策引用。

Missing valid rule/path is `HOLD_TRANSITION_RULE_MISSING`. Multiple valid paths
that canonical rules cannot eliminate are `HOLD_CANONICAL_PATH_DIVERGENCE`.

`THETA_F(P_a,P_b)=direction_code(selected_transition_rule_id)` and
`THETA_PATH_F=<direction_code_1,...,direction_code_m>`.

For the unique Founder-canonical path `GAMMA_F=<e_1,...,e_m>`,
`delta_F(P_a,P_b)=sum(step_cost_uint(e_k))`. Therefore `delta_F(P,P)=0`.
Distance is not a direct-slot difference or a geometric/similarity proxy.

## Complete native ADI

`PHI_F(P_o,P_t)` is the ordered structure:

`<namespace,origin_state_root,DIRECT_SLOT_F(P_t),tau_F(t),X_F(P_t),
boundary_state_F(P_t),METRIC_SIGNATURE_F(P_t),delta_F(P_o,P_t),
THETA_PATH_F(P_o,P_t),parent_state_root,evidence_root,canonical_version,
rule_version,logical_time>`.

Canonical serialization may be hashed as `adi_ref`; the hash is only an
identifier and not the ADI mathematical object.

## Shells and native spiral

`S_r^F(P_o)={P_j | delta_F(P_o,P_j)=r}`. `S_0` is the exact authoritative
shell; `r>0` is reconstruction-only.

For a candidate `P_j`, `ORDER_KEY_F=<PATH_F(P_o,P_j),THETA_PATH_F(P_o,P_j),
logical_time(P_j),state_root(P_j)>`. Ordering is, in sequence:

1. transition-rule-id path in canonical UTF-8 byte order;
2. direction-code path in canonical UTF-8 byte order;
3. ascending logical time;
4. lowercase hexadecimal state-root byte order.

`OMEGA_F(S_r)` sorts one shell by that key. `SPIRAL_F` concatenates complete
shells from radius zero outward.

## Evidence closure, unique fixed point and stop

`EVIDENCE_CLOSED_F(P)=1` only when all required evidence references resolve and
their digests match, the metric signature reproduces, logical time and topology
are causally consistent, the parent root is current-authoritative, the candidate
root reproduces, all eight dimensions are cross-field consistent, the packet is
not negative, every positive condition holds, every required transition is
present and unique, and D7 has no hard risk.

`T_F(P)=TOTAL_FIELD_VALIDATE_F(P)`. A fixed point satisfies `T_F(P_star)=P_star`.
The first acceptable shell is the smallest completely checked shell containing
exactly one evidence-closed fixed point, with no fixed point in smaller shells
and no unresolved mutually exclusive candidate in the same shell. Multiple
fixed points are `HOLD_CONSENSUS_DIVERGENCE`.

`STOP_F(r)=1` only after shells zero through `r` are fully checked in native
spiral order, the above unique fixed point exists, smaller shells contain none,
same-shell conflicts are resolved, and the query budget is not exceeded. Stop
immediately at the first such shell. Budget exhaustion is
`HOLD_QUERY_BUDGET_EXCEEDED` and never a partial pass.

## Dependency and drift boundary

The native calculation path is standard-library-only and must not depend on
space-filling curves, geometric proxy distances, similarity/nearest-neighbor
search, model voting, model averaging, decoding optimizers, inference caches, or
external research/runtime frameworks. Historical V2.2 compatibility evidence
must never be imported into the native runtime.
