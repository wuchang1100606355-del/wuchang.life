# TFCT／TRUE8D Runtime Policy 正典升格報告

RUN_ID=`TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_PROMOTION_V0_1`
STATE=`PASS_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_PROMOTED`
OWNER_CONFIRMATION=`YES`
PATENT_CANDIDATE_REVIEW_REQUIRED=YES

## Owner 確認

Owner 已明確決定升格，授權範圍僅限已通過驗證的 TFCT／TRUE8D Runtime Policy 與工程契約。此次授權包含建立獨立 `TFCT_TRUE8D_RUNTIME_POLICY` 正典鏈、專用 Active Canonical mirror 與專用 Pointer；不授權修改既有 D1～D8 Active Canonical 或其他 Pointer。

## 升格範圍

- TFCT／TRUE8D Runtime Policy。
- 8D-GTE Runtime 工程契約。
- 有限步收斂、固定點偵測、循環偵測、超時偵測與 D8 裁決規則。
- `ALLOW`-only commit。
- TFID／Total Field Hash 的既有候選工程契約。
- Small Transport Agent 與 LLM／小J 的 candidate-only authority boundary。
- `LOCAL_EQUIVALENCE_ONLY` 的確定性本地等價驗證。

## 未升格範圍

固定點存在性、固定點唯一性、全域有限收斂、Observation Domain 完整性與分散式 Consensus Protocol 均未被宣稱為已證明。生產級 ADI 演算法、正式 TFID／Hash 契約、代理封裝、2435 倍普遍效能、光學防偽生產聲明與其他效能證據亦未升格。

## 候選來源與 Policy 身份

- tracked candidate source：`manifests/tfct_true8d_runtime_candidate_v0_1/policy.json`
- runtime candidate source：`runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json`
- canonical SHA-256：`d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960`
- source equivalence：`MATCH`

原始 policy 內容未改寫；其內部 `status=CANDIDATE`、candidate-only source 與 Open Problem 邊界均被完整保留。正典狀態由外層 canonical manifest 與 runtime canonical envelope 表達，未建立第二套治理規則。

## 正典版本與位置

- canonical scope：`TFCT_TRUE8D_RUNTIME_POLICY`
- canonical version：`v0.1`
- tracked canonical：`manifests/tfct_true8d_runtime_policy_canonical_v0_1/policy.json`
- runtime canonical：`runtime/total_field/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_V0_1_D27230ABA7A4/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json`
- Active Canonical：`runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json`
- Active Pointer：`runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt`
- Pointer target：`/home/taiji_admin/Taiji_Hub/runtime/total_field/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_V0_1_D27230ABA7A4/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json`

Tracked policy、runtime envelope 的 policy body、Active mirror 及其對應 manifest／evidence equivalence classes 均為 `MATCH`。Pointer 已解析至存在的版本化正典實體。

## 語義鎖

- D6 = `Sovereign Privacy Field`
- D7 = `Generative Transmission & Resource Routing Field`
- D8 = `Red-Team Detour Alert & Quarantine Field`
- commit rule = `ALLOW_ONLY`
- consensus mode = `LOCAL_EQUIVALENCE_ONLY`

生成式傳輸維持 protocol-native 8D intent-field packet、引用、查表、重構條件、等價狀態生成與總場驗證邊界；本次沒有把它改寫為傳統資料搬運類流程。

## 測試與 Verifier 證據

- promotion focused tests：`25/25 PASS`
- source verification：`PASS_VERIFY_SOURCE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL`
- promotion：`PASS_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_PROMOTED`
- active verification：`PASS_VERIFY_ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL`
- canonical verifier：`PASS_VERIFY_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL`

本次沿用既有已接受的 D3、runtime、replay、package 與文件整合 PASS 證據，未重跑那些既有 suites，也未執行全倉庫測試。

## Open Problems

下列項目仍明確保留：`OBSERVATION_DOMAIN_COMPLETENESS`、`FIXED_POINT_EXISTENCE_THEOREM`、`FIXED_POINT_UNIQUENESS_THEOREM`、`GLOBAL_FINITE_CONVERGENCE_THEOREM`、`DISTRIBUTED_CONSENSUS_PROTOCOL`、`CANONICAL_TFID_HASH_CONTRACT`、`PRODUCTION_ADI_ALGORITHM`、`AGENT_PACKAGING`、`PERFORMANCE_EVIDENCE`。

## 回退方案

`manifests/tfct_true8d_runtime_policy_canonical_v0_1/rollback_manifest.json` 記錄升格前專用 Active Canonical 與 Pointer 均不存在，並鎖定本次 promoted pointer 與 versioned canonical。`rollback-plan` 僅能產生唯讀步驟，不執行回退；任何實際回退必須重新取得 Owner 明確確認。

## 未執行事項

本次沒有 deploy、restart、DB write、router write、全節點安裝、遠端安裝、git commit 或既有正典刪除／移動。其他 Active Canonical、其他 Pointer、D3 engine 與 packet runtime 經精準 verifier 確認未修改。專利檢索與專利審查仍須另案進行。
