# W7TP Community Field / Property / Association Merge Relation Map

Status: draft for review  
Scope: merge and relation map for community field, property, commerce, territory, association, XiaoJ scene context, and 8D identity feature markers

## Purpose

本文件把既有「社區、物業、商業、地域、協會、創辦人推算與社區文獻」合併成可追溯的關聯圖。合併只代表服務視圖、候選路由與設計依據可共同整理，不代表身份、權限、DB 寫入、會員記憶或正式決策被合併。

Core rule:

```text
這是社區總場，不只是物業加協會。
社區可包含物業、商業、地域、協會、創辦人推算與社區文獻庫。
物業角色、商業角色、地域座標、協會角色、不可變更創辦人標記，必須保留各自 ref / evidence_ref / verifier_ref。
關聯圖只做 candidate relation，不做正式身份裁決。
```

## Source Conversation Refs

| Source ref | Thread | Main relation |
| --- | --- | --- |
| `CODEX_SESSION_REF:2026-06-28/019f0ec4-e4b8-7bf0-8075-a57447908611` | Read pasted text file | Defines `PROPERTY_CONTEXT` and `ASSOCIATION_CONTEXT` for Scene Context Router |
| `CODEX_ATTACHMENT_REF:f3769bdf-07e2-4c75-9e2b-506b6b7160b6` | Scene Context Router request | Lists property / association aliases, allowed scopes, forbidden scopes, and UI badge needs |
| `CODEX_SESSION_REF:2026-06-26/019f0526-d478-7ea3-912a-3f17ad165396` | 規劃會員功能介面 | Plans AI Browser membership UI across property, association, merchant, family, and personal scenes |
| `CODEX_ATTACHMENT_REF:57cd58f5-7309-40c0-b7f2-550106bc5eee` | AI Browser member UI planning | Defines product planning inputs for property management organization and association unit |
| `CODEX_SESSION_REF:2026-06-30/019f18ea-cdde-78c3-87d3-9c4e73669257` | 生成可上傳四個檔案 | Adds operator handoff refs for `association_sovereign_member` and `resident_property_management` |
| `CODEX_SESSION_REF:2026-07-02/019f22d3-901a-7672-b5b1-72a21b67018c` | 修正小J角色命名 | Adds XiaoJ role naming, 8D identity feature markers, property roles, association roles, and immutable founder |
| `CODEX_ATTACHMENT_REF:e937fc0a-516c-40d6-8a00-fc9c5ec2bd45` | Member AI fallback request | Establishes member AI fallback, LLM prefix policy, and association-hosted candidate route boundary |
| `REPO_DOC_REF:Taiji_Governance/system_info/wuchang_jurisdiction_coordinate_analysis_2026-05-12.md` | 五常社區轄區圖座標精密分析 | Territory anchor and local metric coordinate basis |
| `REPO_DOC_REF:Taiji_Governance/system_info/community_branch_group_member_mapping_2026-05-12.md` | Community branch group member mapping | Separates association, property platform, commerce platform, and branch service windows |
| `REPO_DOC_REF:docs/strategy/wuchang_sovereign_economic_engine_v8_zh.md` | Wuchang sovereign economic engine | Defines commerce serving public-interest community service with accounting windows |
| `REPO_DOC_REF:docs/total_field/WUCHANG_PROPERTY_MANAGEMENT_TOTAL_FIELD_INFORMATION_SYNTHESIS.md` | Wuchang property synthesis | Connects property, committee, resident service, merchant service, evidence seal, and 8D packets |
| `REPO_DOC_REF:docs/total_field/ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE.md` | Association patent and revenue governance | Captures founder/community design intent and public-interest governance boundary |

These refs are local conversation pointers. They are evidence anchors for design continuity, not authority records.

## Community Field Composition

The top-level field is:

```text
WUCHANG_COMMUNITY_TOTAL_FIELD
```

It contains six ref-only design dimensions:

| Dimension | Meaning | Ref boundary |
| --- | --- | --- |
| `PROPERTY_DIMENSION` | 物業、管委會、住戶、公設、修繕、設備設施 | property refs, resident no-plaintext refs |
| `COMMERCE_DIMENSION` | 商家、POS、商業協力、社區商家會員、基金池營運訊號 | commerce refs, aggregate accounting refs |
| `TERRITORY_DIMENSION` | 五常社區地域、轄區、地理座標、服務範圍 | territory refs, coordinate refs |
| `ASSOCIATION_DIMENSION` | 協會會務、公益、會員治理、志工、補助、活動 | association refs, member no-plaintext refs |
| `FOUNDER_CALCULATION_DIMENSION` | 創辦人對社區系統的細緻推算、技術路線、治理判準 | founder calculation refs, not plaintext memory |
| `COMMUNITY_LITERATURE_CORPUS_DIMENSION` | 社區設計文獻、政策、策略、總場文件、證據封條 | corpus refs, hash/evidence refs |

The founder calculation and literature corpus are design evidence sources. They do not become automatic authority, identity proof, or member memory.

## Canonical Merge

The merged service view has a community root plus two current service branches:

0. `COMMUNITY_TOTAL_FIELD_ROOT`
   - field type: `community_total_field`
   - includes: property, commerce, territory, association, founder calculation, community literature corpus
   - output mode: ref-only candidate relation map
   - verifier: total field

1. `PROPERTY_SERVICE_BRANCH`
   - scene context: `PROPERTY_CONTEXT`
   - XiaoJ projection: `BUILDING_DIGITAL_SECRETARY`
   - service name: 大樓數位秘書小J
   - identity marker domain: `feature_domains.property`
   - handoff group: `resident_property_management`

2. `ASSOCIATION_SERVICE_BRANCH`
   - scene context: `ASSOCIATION_CONTEXT`
   - XiaoJ projection: `COMMUNITY_SERVICE_STAFF`
   - service name: 社區服務員小J
   - identity marker domain: `feature_domains.association`
   - handoff group: `association_sovereign_member`

The word `社區` can appear in both branches. It must not collapse property authority and association authority into one role.

Commerce and territory are first-class dimensions of the same community field. They can route service context, but they must not override property or association role verification.

## 8D Sovereign AI Community XiaoJ

The soul anchor of the merged community field is:

```text
8D_SOVEREIGN_AI_COMMUNITY_XIAOJ
8維碼主權 AI 社區小J
```

This anchor is not a UI label and not a generic assistant name. It is the sovereign AI community intent field that binds social work governance, caregiver execution, elder participation, property context, merchant context, public-interest fund flow, and no-delete evidence.

Required interpretation:

- 社工是意圖場的人類治理責任人與社區知能中樞。
- 照服員是照護執行員工，負責高齡/弱勢服務陪同、觀察與回報留痕。
- 長輩不是被動受管理對象，而是退而不休、參與社區生活與公益造血的主體。
- 商業志工隊外送不是單純物流；它是物業、商業、協會、照護與公益造血的候選服務閉環。
- 任何涉及長者、弱勢、健康訪視、住戶明文或精確位置的外送/服務，必須由社工治理責任人與照服員員工進入總場驗證。

## Public-Interest Commerce Beachhead

產品落地不是附屬任務，而是公益商業能否普及的第一條防線。若產品體驗、營運效率、會計留痕、社工治理、照服員執行、長者參與與商家收益不能同時成立，公益商業無法勝過傳統商業，也無法代表社區與中心化平台談判。

Required rule:

```text
生活必須與合理補償先被看見；
剩餘利益、資料治理權、服務入口與造血能力回到社區；
社區以產品力形成對中心化巨頭的集體談判力。
```

This means the relation map may include commerce and revenue strategy as first-class design refs, but it must still block private extraction, payment execution, investment language, and unreviewed accounting conclusions.

## Relation Rules

### Property branch

Property roles include:

- `PROPERTY_CHAIRPERSON`
- `PROPERTY_VICE_CHAIRPERSON`
- `PROPERTY_TREASURER`
- `PROPERTY_GENERAL_MANAGER`
- `PROPERTY_UNIT_OWNER`
- `PROPERTY_RESIDENT`
- `PROPERTY_VEHICLE_TYPE`
- `PROPERTY_VEHICLE_COLOR`
- `PROPERTY_EQUIPMENT`
- `PROPERTY_FACILITY`

Allowed candidate routing examples:

- repair request candidate
- announcement draft
- resident no-plaintext context
- facility / equipment service candidate

Forbidden:

- resident plaintext read
- building access grant without verification
- payment capture
- property role elevation without verifier

### Association branch

Association roles include:

- `ASSOCIATION_IMMUTABLE_FOUNDER`
- `ASSOCIATION_CHAIRPERSON`
- `ASSOCIATION_SECRETARY_GENERAL`
- `ASSOCIATION_VICE_CHAIRPERSON`
- `ASSOCIATION_EXECUTIVE_DIRECTOR`
- `ASSOCIATION_DIRECTOR`
- `ASSOCIATION_EXECUTIVE_SUPERVISOR`
- `ASSOCIATION_SUPERVISOR`
- `ASSOCIATION_SECRETARY`
- `ASSOCIATION_STAFF`
- `ASSOCIATION_MEMBER`

Allowed candidate routing examples:

- association service admission candidate
- activity RSVP candidate
- volunteer service candidate
- no-plaintext member context

Forbidden:

- member plaintext read
- subsidy approval without verification
- formal association notice without verifier
- association role elevation without verifier

### Immutable founder

`ASSOCIATION_IMMUTABLE_FOUNDER` is not a rotating association office. It can be associated with the association branch, but it cannot be overridden by chairperson, secretary general, board, supervisor, secretary, staff, or member role rotations.

Required boundary:

- `immutable_founder_marker=true`
- `founder_marker_mutable=false`
- `role_rotation_can_override=false`
- `founder_ref` only, no plaintext identity
- `requires_total_field_verify=true`

### Founder calculation and literature corpus

創辦人的細緻推算與社區大量文獻，是本社區總場設計的高價值證據來源。它們應以 `FOUNDER_CALCULATION_REF`、`COMMUNITY_LITERATURE_CORPUS_REF`、`EVIDENCE_REF`、`HASH_REF` 或 `REPO_DOC_REF` 進入關聯圖。

Forbidden:

- 將文獻全文塞入會員記憶庫
- 將推算直接升格為正式身份裁決
- 將商業資料、住戶資料或會員資料明文混入文獻關聯圖
- 以 LLM 摘要取代總場 verifier

## Relation Graph

```text
WUCHANG_COMMUNITY_TOTAL_FIELD
  -> PROPERTY_DIMENSION
  -> COMMERCE_DIMENSION
  -> TERRITORY_DIMENSION
  -> ASSOCIATION_DIMENSION
  -> FOUNDER_CALCULATION_DIMENSION
  -> COMMUNITY_LITERATURE_CORPUS_DIMENSION
  -> total field verifier

Scene Context Router
  -> PROPERTY_CONTEXT
      -> BUILDING_DIGITAL_SECRETARY / 大樓數位秘書小J
      -> feature_domains.property
      -> resident_property_management refs
      -> total field verifier

Scene Context Router
  -> ASSOCIATION_CONTEXT
      -> COMMUNITY_SERVICE_STAFF / 社區服務員小J
      -> feature_domains.association
      -> association_sovereign_member refs
      -> total field verifier

ASSOCIATION_IMMUTABLE_FOUNDER
  -> association branch evidence
  -> immutable founder boundary
  -> total field verifier
  -x property role overwrite
  -x association rotating role overwrite

FOUNDER_CALCULATION_REF + COMMUNITY_LITERATURE_CORPUS_REF
  -> design evidence
  -> relation hints
  -> total field verifier
  -x member memory authority
  -x final decision

8D_SOVEREIGN_AI_COMMUNITY_XIAOJ
  -> social worker governance center
  -> caregiver employee execution
  -> elder active participation
  -> volunteer delivery candidate
  -> property / commerce / association / public value relation
  -> total field verifier
  -x AI replaces social worker
  -x volunteer self-dispatch
  -x elder as passive managed object
  -x caregiver as ungoverned labor
```

## Merge Boundary

Merged:

- service dashboard grouping
- XiaoJ member-facing language style
- candidate routing hints
- ref-only handoff groups
- UI context badges
- no-plaintext evidence refs
- community field dashboard
- property / commerce / territory / association relation hints
- founder calculation refs
- community literature corpus refs
- 8D sovereign AI community XiaoJ anchor
- social worker governance responsibility
- caregiver employee execution refs
- elder active participation refs
- volunteer delivery candidate relation

Not merged:

- role authority
- identity proof
- Odoo DB write permission
- resident/member plaintext
- secrets
- payment authority
- formal notice authority
- founder immutability
- legal / accounting authority
- social worker professional judgment
- caregiver employment responsibility
- elder consent and agency
- community territory proof without official verifier
- founder calculations as direct execution authority
- community literature corpus as member memory

## Output Contract

Any packet using this merge relation must keep:

- `merge_mode=candidate_relation_only`
- `authority=candidate_only`
- `requires_total_field_verify=true`
- `contains_member_plaintext=false`
- `db_write=false`
- `secret_read=false`
- `final_decision=false`
- `founder_calculation_ref_only=true`
- `community_literature_corpus_ref_only=true`

## Final Rule

這是一個社區總場：有物業、有商業、有地域、有協會，也有創辦人細緻推算與大量社區設計文獻。它們可以在小J服務視圖中合併呈現，但身份特徵、權限驗證、地域證據、商業會計窗、文獻證據與創辦人不可變更標記必須分開保存、分開驗證、不得互相覆蓋；權威仍回總場。
