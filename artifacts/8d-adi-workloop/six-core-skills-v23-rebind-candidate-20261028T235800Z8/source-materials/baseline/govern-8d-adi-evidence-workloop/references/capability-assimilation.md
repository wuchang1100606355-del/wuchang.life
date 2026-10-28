# Capability assimilation and source lineage

## Purpose

This skill internalizes workflow capabilities into an 8D ADI-native contract. It does not install, invoke, depend on, rename, or claim technical identity with the external source project.

## External workflow source

- Repository: `3xachris/3xa-harness`
- Inspected ref: `bundle-v0.1.0`
- Licence observed in repository: MIT
- Source: `https://github.com/3xachris/3xa-harness/tree/bundle-v0.1.0`
- Inspection date: `2026-08-23`

Observed workflow effects: scope freezing, append-only decisions, cross-session handoff, identified human sensory review, staged diagnosis, evidence-bearing closeout, unsupported-claim detection, and record-decay checks.

## User-supplied 8D/W7TP sources

The uploaded collection had SHA-256:

```text
c31aab9f050f4cd73038c79268ba2742c3439c1df1474a7ce32d740600844972
```

Relevant extracted sources:

| Source | SHA-256 | Evidence state |
|---|---|---|
| `GPT_WORK_MODE_8D_ADI_TOTAL_FIELD_V2_CANDIDATE.md` | `9b3e18cf25961ad2656949b8e1363594e6c6f7d459a4b60c65b3e3b059cdb1e4` | candidate 2.1.0, inactive |
| `W7TP_V2_1_TO_3_0_GOVERNED_BRIDGE_CANDIDATE_v1.json` | `066e39cd2abad3d4ed713e4f7ecb7f220d4651d9f7624f5b48d13c4781be7890` | candidate, not canonical |
| `W7TP_SKILL_AUDIT_BUNDLE_20260820_164609_359.zip` | `29bd4b78ad523ae2a10e7fc5e3e75a2fe3579b185e2703198ca115a594405793` | audit bundle candidate |

The bridge sidecar verified its candidate JSON. Its evidence reports `PASS_PORTABLE_CANDIDATE_ARTIFACT_VERIFICATION`, while `total_field_decision` remains absent. It explicitly forbids deployment, activation, canonical/pointer mutation, DB/ADI writes, historical-receipt fabrication, and final authority.

The audit bundle reported 285 included files, no excluded files, original files unmodified, no raw secret values detected by its pattern scan, and many duplicated skill source trees. Those are bundle claims plus extracted-file evidence, not a promotion decision. Installed current personal skills remain the operational references; duplicated audit copies are lineage evidence only.

## Assimilation mapping

| Source capability effect | 8D ADI-native mechanism |
|---|---|
| Freeze task scope | D1 product intent plus one D1-D8 state snapshot and hash-bound `ORDER_FROZEN` event |
| Preserve decisions | append-only events with logical time, provenance, evidence label, observation status, supersession, and authority state |
| Handoff | candidate 8D state snapshot with member/Seat/profile boundary and one exact next action |
| Human visual/audio review | D7 sensory risk gate plus D8 identified human disposition; empty rejects never equals approval |
| Diagnose failures | D2 observed failure, D4 causal evidence, D5 minimum fix candidate, D7 two-attempt confinement, and regression evidence |
| Honest closeout | stable acceptance IDs, fresh independent functional verification, protected-state record, and D8 receipt boundary |
| Unsupported-claim audit | D4 candidate check resolved by source, `[UNVERIFIED]`, deletion, or written dismissal |
| Record-decay audit | provenance pointer, hash, repeated-correction, non-empty-input, and stale-evidence checks |

## Non-identity boundary

No claim is made that this skill and the external project use the same mechanism. Similar product effects are not technical identity. This skill adds identity/Seat prerequisites, one coordinated D1-D8 run, ADI range/exact resolution, evidence and observation labels, candidate/canonical separation, Total Field D8 authority, natural-language HOLD, protected-data rules, Main Brain/personality separation, minimum-delta reuse, and W7TP carrier/reconstruction separation.

If a future request asks whether the two technologies are technically the same, route that separate question through `audit-technology-identity`. Do not infer patentability, infringement, novelty, or superiority from this assimilation record.

## Screenshot evidence

The user supplied a Windows File Explorer screenshot on `2026-08-23`. Visible names included W7TP/8D candidates and skill artifacts. It proves visible filenames and UI state at capture time only. Encode governed target-state claims as `DECLARED_ONLY` until an authorized probe observes the named device. The screenshot does not prove file content, hash, current existence, canonical status, installation, or authority.
