---
name: audit-technology-identity
description: Audit whether two technologies are technically identical, partially overlapping, effect-only equivalent, different, or insufficiently evidenced by comparing mechanism, causal path, dependencies, eliminated operations, cost topology, and carrier/reconstruction/verification semantics. Use for W7TP comparisons, zero-float or verification-elimination claims, prior-art and architecture comparisons, structural-elimination claims, or any request asking whether one technology is the same as, better than, derived from, or technically equivalent to another. Operate read-only, use discrete evidence decisions without weighted similarity scores, and never infer patentability, infringement, legal status, or global superiority from the gate.
---

# Audit Technology Identity

## Preserve the comparison boundary

Treat effect equivalence as a comparison trigger, never as proof of technical equivalence. Compare exactly six evidence-bearing axes:

1. `MECHANISM`
2. `CAUSAL_PATH`
3. `DEPENDENCIES`
4. `ELIMINATED_OPERATIONS`
5. `COST_TOPOLOGY`
6. `CARRIER_RECONSTRUCTION_VERIFICATION`

Read [references/technology-identity-contract.md](references/technology-identity-contract.md) before returning a decision. Keep observed facts, source-grounded reconstruction, inference, conflicts, and unknowns separate.

## Apply the gate only when relevant

Apply this skill when a request:

- asks whether two technologies are the same, equivalent, superior, derived, copied, or merely similar;
- compares W7TP with transfer, sync, compression, encryption, delta encoding, prompt generation, model reconstruction, or another carrier or reconstruction mechanism;
- claims that an operation, verification step, storage object, computation, or cost was structurally eliminated;
- claims zero floating point, exact reconstruction, equivalent-state reconstruction, or verification elimination;
- prepares prior-art, patent, copyright, trade-secret, licensing, or technical-positioning evidence.

Do not apply it to ordinary memory recall, file inventory, or product comparison when no technical-identity claim is present.

## Build the smallest sufficient evidence set

For each technology, resolve only evidence needed for the six axes. Prefer primary specifications, source code, reproducible execution evidence, official receipts, and declared architecture over marketing language or model summaries. Preserve exact source references and dates. Treat missing evidence as `UNKNOWN`; never fill gaps with analogy.

Use this evidence maturity scale:

- `EV0_UNSUPPORTED`
- `EV1_ASSERTION`
- `EV2_SECONDARY_SOURCE`
- `EV3_PRIMARY_DOCUMENT`
- `EV4_IMPLEMENTATION_EVIDENCE`
- `EV5_REPRODUCIBLE_CAUSAL_EVIDENCE`

These are evidence labels, not Total Field E0-E5 effect classes. Never calculate a weighted identity score, similarity percentage, confidence average, or float-derived identity value.

## Preserve W7TP technical scope

Keep carriers and protocols separate from state-field reconstruction and verification semantics. Ordinary SSH, Tailscale, SMB, copy, sync, compression, encryption, file transfer, or model generation does not become W7TP by producing a similar effect.

When zero-float is claimed, identify its exact domain. A packet-level irreversible decision index and system-level lineage network may remain integer and authority-bearing while a separately declared floating-point data index supplies bounded non-authoritative data. Do not broaden a core zero-float claim into a claim that every system computation forbids floating point.

When verification elimination is claimed, identify the exact operation allegedly eliminated. Structural elimination of post-hoc file comparison does not eliminate integrity, identity, authority, envelope, receipt, or packet-carried verification unless direct evidence proves each category absent by design.

## Run the deterministic decision gate

Prepare a JSON assessment conforming to the reference contract, then run:

```bash
python3 scripts/technology_identity_gate.py assessment.json
```

Use `--self-test` for the bundled deterministic checks. The script validates the six axes, EV evidence labels, references, and observable-effect relation before returning one discrete candidate decision.

The script does not search the web, interpret raw prose, decide patentability, or become Total Field authority. A model or analyst prepares axis relations from cited evidence; the deterministic gate only validates and converges the declared assessment.

## Decide conservatively

Use only:

- `SAME_MECHANISM`
- `PARTIAL_MECHANISM_OVERLAP`
- `EFFECT_ONLY_EQUIVALENT`
- `DIFFERENT_TECHNOLOGY`
- `INSUFFICIENT_EVIDENCE`

Require primary-document-or-stronger evidence on every axis before declaring `SAME_MECHANISM`. A strongly evidenced difference on any causal axis blocks that decision. If the visible effect is the same but a strongly evidenced axis differs, return `EFFECT_ONLY_EQUIVALENT`.

Treat structural elimination as different from ordinary optimization: elimination removes a required operation or dependency from the causal path; optimization retains it while changing speed, scale, placement, or cost.

## Protect authority and intellectual-property boundaries

Operate read-only. Do not write to ADI, a database, canonical state, a patent filing, or a live system. Do not expose credentials, protected codebooks, member plaintext, trade-secret payloads, or unrelated source content.

A gate result is technical-comparison evidence only. It never proves novelty, inventive step, patent eligibility, infringement, validity, authorship, ownership, legal status, or global superiority. Route those questions to a separately scoped, source-grounded legal or patent audit.

## Return one compact result

Use:

```text
STATE=<PASS_TECHNOLOGY_IDENTITY_CANDIDATE|PRECONDITION_MISSING|BLOCK_EFFECT_EQUIVALENCE_SHORTCUT|HOLD_TRUE_HARD_RISK>
DECISION=<SAME_MECHANISM|PARTIAL_MECHANISM_OVERLAP|EFFECT_ONLY_EQUIVALENT|DIFFERENT_TECHNOLOGY|INSUFFICIENT_EVIDENCE>
OBSERVABLE_EFFECT_RELATION=<SAME|DIFFERENT|UNKNOWN>
SIX_AXIS_RESULT=<relation and EV evidence for every axis>
STRUCTURAL_ELIMINATION=<supported|optimization_only|unknown>
CARRIER_RECONSTRUCTION_BOUNDARY=<preserved|conflict|unknown>
EVIDENCE=<source references and fact/inference boundary>
PATENT_OR_LEGAL_CONCLUSION=NOT_DETERMINED
AUTHORITY=CANDIDATE_ONLY
NEXT=<one shortest missing evidence action or NONE>
```

Lead with the decision and its decisive axis. Do not claim technical identity when any required axis is missing or weakly evidenced.

## Single current design

Use `govern-total-field-skills` → `references/current-design-contract.json` as the single Founder V2.3 design root. Read its `references/version-observation-causality.md` for causal-chain changes. Revalidate dependent references, validators and state indexes after changes; do not choose an older design as fallback. Historical evidence stays historical. ADI binds state, time, spatial/object location, relations, causality and reconstruction coordinates together. Preserve actual runtime schema differences as local migration gaps.



## V2.3 六大技能共用升級條款（隔離候選）

依 taiji01 活躍指標解析現行 V2.3 契約並核對 SHA-256；引用本次快照，不把快照當授權。八維為八合一單一動態狀態場；D5 執行／政策與 D8 封套／權威分離。身分與角色席位約束整個封套。

重用已驗證重構信任標章時，首次須有逐位元組一致證據，重用須核對 reconstruction_key、封包、規則、LUT、基底及結果摘要；effect_authorization 永遠為 false。快路徑可省去不必要的重複模型推理，不能取消完整性、身分、封套或當次效果授權。

模型只提供語義槽位與 emotion_code；音訊參數由版本化 LUT 決定。生成音訊使用 CPU 記憶體 io.BytesIO 完成合成與 SHA-256，不寫出暫存 WAV。既有語音基底、程式與 LUT 的讀取成本須揭露；575 位元組只是一個已記錄範例，非所有原胞固定大小。浮點聲學運算須另列數值與重播契約，跨平台位元組一致性未驗不得宣稱。

依創辦人指定分工建立候選：03 管秩序及原胞發行、02 負責影音重構投射、taiji01 沿既有 HomePod 受控路由。02 身分與各節點當前授權未核對前，維持候選；不得由角色名稱取得超管權。

只產生候選、證據與有界交接；未取得精確總場收據，不部署、不改正典、不變更席位、不自授 D8。文字更新不等於已載入、運行或效果驗收。

完整機讀候選契約：`references/evolution-contract.json`。本技能作用：精確區分省推理、保留驗證、輸出零落盤的主張範圍。
