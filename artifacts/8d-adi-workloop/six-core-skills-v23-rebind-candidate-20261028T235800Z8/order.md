# 8D ADI Order: 六大技能 V2.3 隔離升級候選

Run-ID: six-core-skills-v23-upgrade-candidate-20261024T015400Z8
Lifecycle: CANDIDATE_FOR_TOTAL_FIELD_REVIEW
Frozen: 2026-10-24T01:54:45+08:00
Owner-ref: Founder current user instruction; Seat UNKNOWN_UNVERIFIED
Effect-class: E2

## D1 Intent
沿既有來源建立六大技能升級候選及驗證器，不更新現用技能與正式系統。

## Verified facts
- [FACT|OBSERVED_DIRECT] taiji01 V2.3 contract hash matched | source: evidence/coordinate.json | hash: 2d4fda7e6a3a59787d9ff1a6e6eec426dd435c71e2dd3c873b8b7036c2dbd715
- [FACT|OBSERVED_DIRECT] audio candidate records located; execution not rerun | source: evidence/audio-source-bindings.json | hash: cdf3bf40b46e58380a95ccc8c5724c1c78c38c812dbbfb0eb5b21e8c9c6b47af

## Materials
- Allowed: user-owned skill text and deidentified project code | licence: USER_AUTHORIZED_CANDIDATE_USE_ONLY | checked: 2026-10-24T01:54:45+08:00
- Excluded: credentials, member plaintext, private selectors, sound playback

## Build specification
- canonical_ref = manifests/total_field/w7tp_8d_adi_v2_3_canonical/CONTRACT.json | source: live canonical pointer
- canonical_sha256 = e3c5439657bb4cb97f466ea096d20f8e68ca60307286f01f9c66da0eb120dd2c
- authority_sha256 = ee86873a0d4c2e0f2e7a780d80961a191f366b1a673cce20e4427f60e3248700 | observed binding only; no new effect grant
- cloud SKILL.md plus explicitly identified executor resources; no claim of cloud-resource equality
- derive six candidate definitions and add shared evolution contract; preserve existing effect-class ceilings

## Budget fuse
- Limit: 2 attempt
- Stop condition: stop on two failed candidate validation attempts or protected-source drift

## Acceptance
- [ ] AC-1: 六大技能候選與清單完整、舊原件不覆寫 | evidence: evidence/acceptance.json
- [ ] AC-2: 現行 V2.3 契約綁定與六份清單驗證零失敗 | evidence: evidence/acceptance.json
- [ ] AC-3: 三項能力契約與負向邊界測試完成 | evidence: evidence/acceptance.json
- [ ] AC-4: 來源差異、未驗證節點與正式權威缺口如實交接 | evidence: evidence/acceptance.json
- [ ] AC-5: 既有變更、正典、服務與 Git 狀態保護驗證 | evidence: evidence/acceptance.json

## Non-goals
- no deployment, service restart, audio output, identity/Seat mutation, canonical writes, Git commit/push or cloud skill installation

## D2-D8 projection
- D2 STATE: six source versions become new candidates; runtime unverified
- D3 COORDINATE: taiji01, exact branch/HEAD and source refs in evidence/coordinate.json
- D4 EVIDENCE: historical records, current artifact hashes and validators kept distinct
- D5 EXECUTION_POLICY: new candidate directory only; rollback by retiring this unpromoted directory
- D6 GENERATIVE_TRANSMISSION: NOT_CLAIMED for this package transport; existing reconstruction protocol reused by reference
- D7 RED_TEAM_RISK_CONFINEMENT: reject authority inflation, zero-total-I/O and total-verification-elimination claims
- D8 ENVELOPE_AUTHORITY: CANDIDATE_ONLY; receipt NOT_REVIEWED; no Seat invented
