# W7TP 8D 社區數位孿生總場產品級統一修正與落地藍圖

- State: `PASS_TOTAL_FIELD_8D_PRODUCT_BLUEPRINT_READY`
- Run ID: `20260722T204427Z`
- Base deploy run: `20260722T190044Z`
- Base evidence root: `e8ca44347802f33ead0827e54fd71c9ccce36016b98ed17da9f2ca28c62bac59`
- System type: `EIGHT_DIMENSIONAL_COMMUNITY_DIGITAL_TWIN_STATE_FIELD`
- Authority: `TOTAL_FIELD_SERVER_MASTER`
- Current node: `taiji01`
- Mode: plan only, evidence retrieval first

## 1. Executive system truth

W7TP 是 Founder 自然人意圖、社區公共利益、居民權益、管委會與協會制度權威、商家與志工服務關係、8D 狀態封包、GTP 生成式狀態轉換、Total Field 唯一機器收斂、Codex 工程執行、Odoo 制度與交易投影、POS 實體事件、Native ADI 絕對時空記憶、VPN 多節點運算、Merlin 邊界與 Dead Letter 記憶，以及本地與雙雲候選智慧所形成的同一狀態場。

它不是 API-first、database-first、single-server-first、microservice-first、file-transfer-first 或 model-first 系統。產品規劃採用 `STATE_FIELD_FIRST`、`INTENT_FIRST`、`AUTHORITY_FIRST`、`CAUSAL_MEMORY_FIRST`、`GENERATIVE_TRANSMISSION_FIRST` 與 `COMMUNITY_RIGHTS_FIRST`。

`taiji01` 是目前主要 Total Field 承載節點，不等於完整系統。Codex 是工程執行器，不是總場或組織權威。本地 LLM 負責 Founder 數位孿生理解與意圖收斂；雙雲 LLM 只產生正向候選與反向反證候選。

本輪不修改任何產品程式、production runtime、資料庫、路由器、套件、服務或 Git 狀態。現有 Native ADI candidate diff 完整保留為 `CURRENT_UNCOMMITTED_CANDIDATE`。

## 2. Evidence carry-forward table

| Evidence | Reference | State | Product meaning |
|---|---|---|---|
| Native ADI product landing | `runtime/total_field/native_adi/W7TP_NATIVE_ADI_PRODUCT_LANDING_20260722T190044Z.json` | CARRIED_FORWARD_PASS | deployed、health、3/3 tests、100,000 records、root/count/byte/ID equivalence |
| Native ADI service unit | `/home/taiji_admin/.config/systemd/user/w7tp-native-adi.service` | CARRIED_FORWARD_PASS | `127.0.0.1:9110`, immutable release working directory, state-only writable path |
| Active Native ADI release | `/home/taiji_admin/.local/share/w7tp-native-adi/releases/d7bfb93bb1956f27` | CURRENT_HASH_MATCH | four deployed Python hashes match the product landing receipt |
| Total Field master pointer | `runtime/total_field/master_index/ACTIVE_GT_8D_PACKET_POINTER.json` | CARRIED_FORWARD_PASS | bound 8D packet pointer and packet SHA-256 |
| POS official chain | `runtime/total_field/active/ACTIVE_POS_OFFICIAL_CHAIN_CANONICAL.json` | CARRIED_FORWARD_PASS | official owner is existing `Taiji_Odoo/addons/wuchang_core/`; formal writes remain disabled |
| All-node + router scope | `runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json` | CARRIED_FORWARD_PASS | VPN multi-node and Merlin physical boundary belong to system scope; peer presence alone grants no node authority |
| Cloud candidate boundary | `runtime/total_field/active/ACTIVE_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL.json` | CARRIED_FORWARD_PASS | cloud completion is candidate-only; D4/D6/D8 and owner/formal gates remain required |
| Codex Total Field domain | `runtime/total_field/active/ACTIVE_CODEX_TOTAL_FIELD_GLOBAL_AGENT_DOMAIN_POINTER.txt` | CARRIED_FORWARD_PASS | Codex domain has an existing record pointer and remains an engineering actuator |
| Memory lifecycle index | `W7TP_FIELD_ATLAS/29_memory_lifecycle_map.yaml` | CARRIED_FORWARD_PASS | hot/warm/cold/archive/forget lifecycle and no-secret/no-personal-export boundary |
| Gateway route map | `W7TP_FIELD_ATLAS/30_gateway_route_map.yaml` | CARRIED_FORWARD_PASS | inspect/extend existing Gateway without restart or parallel gateway |
| Odoo inventory map | `W7TP_FIELD_ATLAS/31_odoo_module_inventory_map.yaml` | CARRIED_FORWARD_PASS | Odoo/POS owner mapping is docs-index-only and DB-safe |
| Edge-node manifests | `02_edge_nodes/*/node_boot.yaml` | CARRIED_FORWARD_PASS | declared roles, trust, allow/deny and max authority levels |
| Edge boot/ledger path | `boot/start_edge_node.sh` | CARRIED_FORWARD_PASS | state, heartbeat, ledger and existing rejected-event path are defined |
| Existing Total Field receipt producer | `tools/total_field/w7tp_d8_reviewer_entrypoint.py` | CARRIED_FORWARD_PASS | existing decision/evidence/receipt/manifest producer with single-use replay disposition |
| Existing hash-only DLQ | `runtime/dead_letter/dead_letter_24h_hash_writer.py` | CARRIED_FORWARD_PASS | existing 24h hash-only writer; no plaintext payload storage |
| Merlin control boundary | `runtime/router/merlin_intent_driver.py`, `merlin_apply_queue.py`, `merlin_approval_gate.py` | CARRIED_FORWARD_PASS | plan/ticket/approval records only; no automatic router execution |
| Odoo community owner | `Taiji_Odoo/addons/wuchang_core/models/property_management.py` | CARRIED_FORWARD_PASS | community, building, unit, committee member, complaint, bulletin and package owners exist |
| Odoo institutional meeting owner | `Taiji_Odoo/addons/wuchang_core/models/collab_meeting.py` | CARRIED_FORWARD_PASS | meeting, agenda, minutes and decision-holder structures exist |
| Odoo member packet owner | `Taiji_Odoo/addons/wuchang_core/models/member_registration.py` | CARRIED_FORWARD_PASS | packet refs, auth scope and no-plaintext refs exist |
| Odoo commerce/POS owner | `wuchang_core/models/order.py`, `pos_config_ext.py` | CARRIED_FORWARD_PASS | community order and official `pos.order` extension exist |
| Odoo volunteer/economic owner | `volunteer.py`, `volunteer_point.py`, `coin_ledger.py` | CARRIED_FORWARD_PASS | service, attendance, approval, points and coin ledger owners exist |
| XiaoJ current owner | `core/xiaoj/` | CARRIED_FORWARD_PASS | intent manager, tensor compiler, reconstruction and red-team classes exist |
| Current Native ADI core candidate | `services/w7tp_native_adi/core.py` | STALE_EVIDENCE_REBIND_REQUIRED | candidate SHA differs from deployed receipt; future release must rebind, not rerun historical baseline |
| Current Native ADI service candidate | `services/w7tp_native_adi/service.py` | STALE_EVIDENCE_REBIND_REQUIRED | candidate SHA differs from deployed receipt; live service remains on base release |
| Red/blue candidate tests | `tests/test_w7tp_native_adi_red_blue.py` | CURRENT_UNCOMMITTED_CANDIDATE | new delta-only test design, not formal release evidence |

Carried-forward facts include product landing, absolute time position, same-time cross-section, native spiral collision handling, 8D packet, reference lookup, reconstruction conditions, expected root/count, equivalent reconstruction, byte/ID equivalence, Total Field, Dead Letter, replay/tombstone concept, Merlin boundary, VPN system scope and community/Odoo/POS governance scope. None is reopened as a defect.

## 3. Current architecture map

```text
Founder natural-person intent / resident / merchant / volunteer / governance body
                                 │
                         Local XiaoJ twin
                   ┌─────────────┴─────────────┐
             positive cloud              negative cloud
             candidate lane              counterexample lane
                   └─────────────┬─────────────┘
                              Packet8D
                                 │
                  Total Field evidence resolver
                                 │
          ┌──────────────────────┼────────────────────────┐
       Codex                 Odoo/POS                 VPN mesh
 engineering actuator   institutional projection   candidate workers
          │                      │                       │
  patch candidate         state/event candidate     result atoms
          └──────────────────────┼───────────────────────┘
                                 │
                       taiji01 formal verifier
                        Native ADI + GTP roots
                                 │
                     existing authority receipt
                        ┌────────┴────────┐
                      ALLOW          HOLD/BLOCK
                        │                │
               authorized projection  existing DLQ
                                         │
                              Merlin USB/JFFS reference
```

Current owners are preserved:

- `services/w7tp_native_adi/`: ADI, GTP reconstruction and local service baseline.
- `services/gateway/`: cross-service ingress and topology routing.
- `core/xiaoj/`: local intent analysis, compilation, reconstruction and red-team candidate processing.
- `runtime/memory/`, `runtime/identity/`, `runtime/agents/`: current memory, identity graph and agent declarations.
- `runtime/router/`, `runtime/dead_letter/`: router boundary and rejection memory.
- `02_edge_nodes/`: node role/trust declarations.
- `Taiji_Odoo/addons/wuchang_core/` and existing `wuchang_*`: institutional and transaction owners.

## 4. 8D ontology

The minimum living unit is `P_t = <D1,D2,D3,D4,D5,D6,D7,D8>`.

| Dimension | Canonical role | Required examples |
|---|---|---|
| D1 Intent | human/engineering purpose | Founder intent, resident need, merchant/volunteer service, proposal purpose, Codex objective |
| D2 State | lifecycle facts | member/order/case/resolution/task/node/lease states |
| D3 Coordinate | absolute and institutional coordinate | `logical_time_uint64`, ADI slot, cross-section, spiral address, community/building/POS/Odoo/node/namespace refs |
| D4 Evidence | causal references | packet/source/snapshot/parent root/evidence/receipt/run/audit/POS/resolution/DLQ refs |
| D5 Execution | bounded candidate action | engineering patch, Odoo/POS candidate, worker task, inference, notification, service execution |
| D6 Generative transmission | reconstruction contract | base refs, lookup, changed/deleted atoms, rule, missing refs, expected root, canonical/protocol versions |
| D7 Rights and risk | rights, consent and hard boundaries | life redlines, personal consent, organization/merchant scope, finance, node budgets, Router hardwall |
| D8 Authority | effective authority facts | Founder canonical, committee/association authority, resident consent, merchant acceptance, Total Field receipt, expiry/revocation, accountable person ref |

`D8` is multi-domain authority evidence, not a single boolean. Total Field machine convergence does not replace personal consent, committee resolutions, association authority or merchant authority.

## 5. GTP canonical

GTP is state-field packet + references + lookup + delta + reconstruction conditions + canonical rule + equivalent-state generation + Total Field verification.

```text
TARGET_STATE = RECONSTRUCT(
  LOCAL_BASE_STATE,
  LOOKUP_REFS,
  CHANGED_ATOMS,
  DELETED_ATOM_REFS,
  RECONSTRUCTION_CONDITIONS,
  RULE_VERSION
)

PASS iff RECONSTRUCTED_STATE_ROOT == EXPECTED_RESULT_ROOT
```

This capability is `CARRIED_FORWARD_PASS`. Future work only exposes it consistently to dynamic LLM context, engineering tasks, Odoo workflows, POS offline/online events, resolutions, services, VPN workers, segmented content-addressed state, memory planes and Dead Letter isolation.

It is not file moving, backup, cloud ciphertext sync, complete-file download, download decryption, generic compression, API equivalence, or a claim that arbitrary existing files can be reconstructed from a small packet.

## 6. Actor and authority domains

### Actor domains

- Founder: original intent root, technical canonical and final human purpose.
- Resident/member: personal rights, consent and service subject.
- Merchant/operator: service acceptance, price/voucher/order scope and accountable execution.
- Volunteer/care/service worker: bounded service execution and evidence production.
- Committee: collective condominium/community governance.
- Association: nonprofit/community-development organizational governance.
- Codex: engineering actuator producing candidates and evidence.
- Local twin: dynamic-context builder and candidate convergence.
- Cloud lanes: positive and negative candidates only.
- Total Field: machine-state convergence and receipt.
- Odoo/POS: institutional/transaction projection and physical-event interface.
- VPN worker: bounded candidate compute under a lease.
- Merlin: block-or-route network boundary.

### Eight authority domains

1. `FOUNDER_TECHNICAL_CANONICAL`
2. `RESIDENT_OR_MEMBER_CONSENT`
3. `COMMITTEE_COLLECTIVE_RESOLUTION`
4. `ASSOCIATION_ORGANIZATIONAL_GOVERNANCE`
5. `MERCHANT_COMMERCIAL_ACCEPTANCE`
6. `RESPONSIBLE_OPERATOR_DELEGATION`
7. `TOTAL_FIELD_MACHINE_CONVERGENCE`
8. `BUSINESS_RECORD_POLICY_AND_ACCOUNTABILITY`

Every transition declares all required domains. A valid Total Field receipt cannot manufacture absent human/organizational consent; human approval cannot replace packet/root verification.

## 7. Memory planes

| Plane | Purpose | Existing owner | Target routing rule |
|---|---|---|---|
| M0 Founder canonical | technical invariants and Founder direction | master pointers / immutable evidence | ref-only, never prompt-dump full corpus |
| M1 Working | current task, PASS, run and open state | Codex context / active pointers | bounded task packet |
| M2 Semantic | community roles, services, products, devices, capabilities | Odoo refs / Atlas / identity | retrieve only intent-related atoms |
| M3 Procedural | Codex, Odoo, POS, dispatch, review, release, recovery procedures | source owners and runbooks | rule refs + version only |
| M4 Episodic | actor/time/place/cause/action/result | ADI event refs / Odoo audits / POS refs | causal window and explicit subject scope |
| M5 Institutional | resolution, authorization, consent, budget and accountability | Odoo institutional models | authority-scope gated |
| M6 Causal evidence | packet/root/receipt/audit/run/node roots | Total Field / ledger / manifests | immutable refs and root chain |
| M7 Dead Letter | rejection, replay, conflict, unresolved, expired, quarantine | existing DLQ / Merlin | hash/ref only, governed retention |
| M8 Node/resource | node, model locality, resources, queue, lease, heartbeat | edge state / mesh registry | fresh status and lease-bounded selection |

Each `MemoryRecord` stores immutable refs, minimal atoms, causal links, authority scope, retention policy and evidence root. Full history is never copied into the LLM prompt; Packet8D is the dynamic context.

## 8. End-to-end flows

### Engineering

Founder intent → Engineering Packet8D → Total Field evidence lookup → Codex task packet → patch candidate → existing evidence binding → candidate root → Total Field seal → controlled release.

### Resident/community service

Resident intent → consent/rights gate → eligibility → Odoo service candidate → responsible authority → execution → ADI evidence → episodic memory. No identity ref alone grants consent.

### Merchant/POS

Cart/service request → POS event Packet8D → merchant/operator authority → price/voucher/eligibility refs → offline/online candidate → Odoo projection → authority receipt → settlement/audit ref → ADI memory.

### Committee/association

Proposal → agenda → quorum evidence → resolution → scope/budget/effective period → D8 conditions → Odoo candidate → execution evidence → institutional memory. Committee and association use separate authority scopes.

### Volunteer/幸福幣

Service event → responsible party → service verification → time/value state → reward candidate → existing Odoo coin/voucher/accounting projection → authority receipt → local circulation → evidence memory.

### AI

Founder/community intent → local twin → Packet8D → positive candidates + negative reproducible counterexamples → local convergence → evidence lookup → response/action candidate → memory candidate. Models never become authority.

### Linux mesh

Task Packet8D → manifest/role/state-root filter → model/data locality → resource state → execution lease → result atoms/root → Total Field receipt → accepted state or existing DLQ.

## 9. Typed Python skeleton

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence


class Decision(str, Enum):
    CANDIDATE = "CANDIDATE"
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


class MemoryPlane(str, Enum):
    FOUNDER_CANONICAL = "M0"
    WORKING = "M1"
    SEMANTIC = "M2"
    PROCEDURAL = "M3"
    EPISODIC = "M4"
    INSTITUTIONAL = "M5"
    CAUSAL_EVIDENCE = "M6"
    DEAD_LETTER = "M7"
    NODE_RESOURCE = "M8"


class NodeLifecycle(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class StateRef:
    namespace_ref: str
    object_ref: str
    state_root: str
    logical_time_uint64: int
    version_ref: str


@dataclass(frozen=True, slots=True)
class ActorRef:
    actor_ref: str
    actor_type: str
    organization_ref: str | None
    accountable_person_ref: str | None
    authority_scope_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Packet8D:
    packet_ref: str
    parent_packet_ref: str | None
    logical_time_uint64: int
    D1_intent: Mapping[str, Any]
    D2_state: Mapping[str, Any]
    D3_coordinate: Mapping[str, Any]
    D4_evidence: Mapping[str, Any]
    D5_execution: Mapping[str, Any]
    D6_generative_transmission: Mapping[str, Any]
    D7_rights_and_risk: Mapping[str, Any]
    D8_authority: Mapping[str, Any]
    packet_root: str


@dataclass(frozen=True, slots=True)
class StateAtom:
    atom_ref: str
    namespace_ref: str
    logical_time_uint64: int
    payload: Mapping[str, Any]
    payload_root: str
    parent_atom_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GTPTransitionPacket:
    packet_ref: str
    source_state_ref: str
    target_state_ref: str
    base_state_ref: str
    parent_state_root: str
    receiver_base_root: str | None
    lookup_refs: tuple[str, ...]
    changed_atoms: tuple[StateAtom, ...]
    deleted_atom_refs: tuple[str, ...]
    reconstruction_rule_ref: str
    reconstruction_conditions: Mapping[str, Any]
    expected_result_root: str
    evidence_root: str
    candidate_decision: Decision


@dataclass(frozen=True, slots=True)
class AuthorityScope:
    authority_scope_ref: str
    authority_type: str
    authority_actor_ref: str
    allowed_state_transitions: tuple[str, ...]
    effective_logical_time: int
    expiry_logical_time: int | None
    revocation_ref: str | None


@dataclass(frozen=True, slots=True)
class AuthorityReceipt:
    receipt_ref: str
    packet_ref: str
    authority_node_ref: str
    human_authority_refs: tuple[str, ...]
    decision: Decision
    candidate_state_root: str
    accepted_state_root: str | None
    issued_logical_time_uint64: int
    evidence_root: str
    total_field_proof_ref: str


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    memory_ref: str
    plane: MemoryPlane
    subject_refs: tuple[str, ...]
    state_ref: StateRef
    causal_parent_refs: tuple[str, ...]
    authority_scope_refs: tuple[str, ...]
    retention_policy_ref: str
    evidence_root: str


@dataclass(frozen=True, slots=True)
class CommunityResolution:
    resolution_ref: str
    authority_body_ref: str
    meeting_ref: str
    proposal_ref: str
    quorum_evidence_ref: str
    scope_refs: tuple[str, ...]
    budget_scope_ref: str | None
    effective_logical_time: int
    expiry_logical_time: int | None
    responsible_actor_refs: tuple[str, ...]
    evidence_root: str


@dataclass(frozen=True, slots=True)
class POSStateEvent:
    pos_event_ref: str
    pos_terminal_ref: str
    merchant_ref: str
    operator_ref: str
    customer_ref: str | None
    logical_time_uint64: int
    order_state_ref: str
    value_state_ref: str
    offline_state: bool
    packet_ref: str
    evidence_root: str


@dataclass(frozen=True, slots=True)
class EngineeringTaskPacket:
    task_ref: str
    founder_intent_ref: str
    packet_8d_ref: str
    repo_ref: str
    allowed_path_refs: tuple[str, ...]
    forbidden_action_refs: tuple[str, ...]
    carried_forward_evidence_refs: tuple[str, ...]
    expected_candidate_root: str | None


@dataclass(frozen=True, slots=True)
class NodeManifest:
    node_ref: str
    vpn_ref: str
    role_refs: tuple[str, ...]
    capability_refs: tuple[str, ...]
    manifest_root: str
    revoked: bool


@dataclass(frozen=True, slots=True)
class NodeResourceState:
    node_ref: str
    cpu_available_uint: int
    ram_available_bytes: int
    storage_available_bytes: int
    gpu_profile_ref: str | None
    queue_depth: int
    vpn_latency_band: int
    thermal_band: int
    state_root: str


@dataclass(frozen=True, slots=True)
class ExecutionLease:
    lease_ref: str
    packet_ref: str
    authority_node_ref: str
    worker_node_ref: str
    issued_logical_time_uint64: int
    expiry_logical_time_uint64: int
    expected_input_root: str
    lease_root: str


@dataclass(frozen=True, slots=True)
class ResultPacket:
    packet_ref: str
    lease_ref: str
    worker_node_ref: str
    result_atom_refs: tuple[str, ...]
    result_state_root: str
    evidence_root: str
    completed_logical_time_uint64: int


@dataclass(frozen=True, slots=True)
class DeadLetterReference:
    dlq_ref: str
    packet_ref: str
    node_ref: str | None
    reason_code: str
    evidence_root: str
    logical_time_uint64: int


class EvidenceResolver(Protocol):
    def resolve(self, ref: str) -> Mapping[str, Any]: ...
    def latest_pass(self, domain_ref: str) -> Mapping[str, Any] | None: ...


class TotalFieldAuthority(Protocol):
    def evaluate_candidate(
        self, packet: Packet8D, candidate_root: str,
        evidence_refs: Sequence[str],
    ) -> AuthorityReceipt: ...


class ExistingDeadLetter(Protocol):
    def push_reference(
        self, *, packet_ref: str, reason_code: str,
        evidence_root: str,
    ) -> str: ...
```

Twenty-two class/protocol designs are defined. These are typed boundaries; no new runtime is created in this planning wave.

## 10. Core service interfaces

```python
def compile_founder_intent(
    natural_language: str,
    existing_state_refs: Sequence[str],
) -> Packet8D: ...

def build_context_packet(*, intent_packet: Packet8D,
    memory_planes: Sequence[MemoryPlane],
    token_budget_uint: int) -> GTPTransitionPacket: ...

def create_engineering_task(packet: Packet8D,
    evidence_refs: Sequence[str]) -> EngineeringTaskPacket: ...

def accept_codex_candidate(task: EngineeringTaskPacket,
    changed_file_refs: Sequence[str], candidate_root: str,
    evidence_refs: Sequence[str]) -> Packet8D: ...

def project_state_candidate(packet: Packet8D, model_ref: str,
    record_ref: str | None) -> Mapping[str, Any]: ...

def apply_authorized_projection(candidate: Mapping[str, Any],
    receipt: AuthorityReceipt) -> str: ...

def create_pos_state_event(raw_pos_event: Mapping[str, Any]) -> POSStateEvent: ...

def build_offline_gtp_packet(event: POSStateEvent,
    local_base_state_ref: str) -> GTPTransitionPacket: ...

def build_resolution_packet(resolution: CommunityResolution) -> Packet8D: ...

def validate_scope(resolution: CommunityResolution,
    requested_transition_ref: str) -> bool: ...

def select_memory_refs(packet: Packet8D, planes: Sequence[MemoryPlane],
    max_atoms: int) -> tuple[str, ...]: ...

def commit_memory_candidate(packet: Packet8D,
    receipt: AuthorityReceipt) -> tuple[MemoryRecord, ...]: ...

def select_node(packet: Packet8D, required_roles: set[str],
    required_state_refs: set[str]) -> str: ...

def issue_execution_lease(packet_ref: str, worker_node_ref: str) -> str: ...

def build_transition(source_state_ref: str,
    target_state_ref: str) -> GTPTransitionPacket: ...

def reconstruct(local_base_state: Sequence[StateAtom],
    packet: GTPTransitionPacket,
    supplied_atoms: Sequence[StateAtom]) -> tuple[StateAtom, ...]: ...

def verify_expected_root(reconstructed: Sequence[StateAtom],
    expected_result_root: str) -> None: ...
```

`reconstruct` and `verify_expected_root` wrap the carried-forward Native ADI capability. They are not reimplemented as a new invention.

## 11. Odoo owner and model design

The official product owner is existing `wuchang_core`. No new addon is assumed. First inspect and extend existing models; add a model inside `wuchang_core` only when no equivalent owner exists. Odoo stores institutional/transaction projections, immutable refs, receipts and roots—not large dynamic contexts or authority private material.

| Logical model | Existing owner | Target owner | Minimal design |
|---|---|---|---|
| `w7tp.state.packet` | packet refs in `wuchang.member.registration`; 8D gate controller | new ref-only model in existing `wuchang_core` if no general equivalent | packet/root/parent/time/intent/lifecycle/coordinate/evidence/execution/risk/receipt/decision |
| `w7tp.authority.receipt` | external Total Field receipt producer | ref projection model in `wuchang_core`; never a second authority | receipt/type/actor/packet/candidate/accepted roots/decision/effective/expiry/revocation/evidence |
| `w7tp.community.resolution` | `wuchang.ai.meeting`, `wuchang.property.committee.member` | resolution model linked to existing meeting/body | proposal/quorum/scope/budget/responsible/effective/expiry/evidence |
| `w7tp.service.case` | `wuchang.property.complaint`, `wuchang.task`, `wuchang.order` | ref projection/mixin over existing cases | subject ref/service/responsible/state/packet/receipt/evidence; no duplicated business record |
| `w7tp.pos.event.ref` | `pos.order`, `wuchang.order`, official POS chain | append-only ref model linked to order/session/config | event/order/session/terminal/merchant/offline/packet/receipt/evidence |
| `w7tp.memory.ref` | `wuchang.ai.memory` currently stores content | new minimal ref-only model or ref fields; do not copy full context | plane/state/causal/authority/retention/evidence refs |
| `w7tp.node.execution.lease` | edge manifests; no Odoo lease projection owner confirmed | ref-only projection after mesh owner exists | lease/packet/authority/worker/state/issued/expiry/result/evidence |

Odoo skeleton pattern:

```python
class W7TPStatePacket(models.Model):
    _name = "w7tp.state.packet"
    _description = "Ref-only Total Field 8D packet projection"
    _sql_constraints = [("packet_ref_unique", "unique(packet_ref)", "packet_ref must be unique")]
    packet_ref = fields.Char(required=True, index=True, readonly=True)
    packet_root = fields.Char(required=True, index=True, readonly=True)
    parent_packet_ref = fields.Char(index=True, readonly=True)
    logical_time_uint64 = fields.Char(required=True, readonly=True)
    lifecycle_state = fields.Selection([...], required=True, readonly=True)
    authority_receipt_ref = fields.Char(index=True, readonly=True)
    decision = fields.Selection([...], required=True, readonly=True)

class W7TPAuthorityReceipt(models.Model):
    _name = "w7tp.authority.receipt"
    _description = "Projection of an existing Total Field receipt"
    receipt_ref = fields.Char(required=True, index=True, readonly=True)
    total_field_proof_ref = fields.Char(required=True, readonly=True)
    packet_ref = fields.Char(required=True, index=True, readonly=True)
    candidate_root = fields.Char(required=True, readonly=True)
    accepted_root = fields.Char(readonly=True)
    decision = fields.Selection([...], required=True, readonly=True)
    evidence_root = fields.Char(required=True, readonly=True)

class W7TPCommunityResolution(models.Model):
    _name = "w7tp.community.resolution"
    meeting_id = fields.Many2one("wuchang.ai.meeting", required=True)
    body_type = fields.Selection([("committee", "Committee"), ("association", "Association")], required=True)
    resolution_ref = fields.Char(required=True, index=True, readonly=True)
    quorum_ref = fields.Char(required=True, readonly=True)
    scope_refs_json = fields.Text(required=True, readonly=True)
    budget_scope_ref = fields.Char(readonly=True)
    responsible_actor_refs_json = fields.Text(required=True, readonly=True)
    evidence_root = fields.Char(required=True, readonly=True)

class W7TPServiceCase(models.Model):
    _name = "w7tp.service.case"
    source_model = fields.Char(required=True, readonly=True)
    source_record_ref = fields.Char(required=True, index=True, readonly=True)
    subject_ref = fields.Char(required=True, index=True, readonly=True)
    responsible_unit_ref = fields.Char(required=True, readonly=True)
    packet_ref = fields.Char(required=True, index=True, readonly=True)
    receipt_ref = fields.Char(index=True, readonly=True)
    evidence_root = fields.Char(required=True, readonly=True)

class W7TPPOSEventRef(models.Model):
    _name = "w7tp.pos.event.ref"
    pos_event_ref = fields.Char(required=True, index=True, readonly=True)
    order_id = fields.Many2one("pos.order", readonly=True)
    terminal_ref = fields.Char(required=True, readonly=True)
    merchant_ref = fields.Char(required=True, readonly=True)
    offline_state = fields.Boolean(required=True, readonly=True)
    packet_ref = fields.Char(required=True, index=True, readonly=True)
    receipt_ref = fields.Char(index=True, readonly=True)
    evidence_root = fields.Char(required=True, readonly=True)

class W7TPMemoryRef(models.Model):
    _name = "w7tp.memory.ref"
    memory_ref = fields.Char(required=True, index=True, readonly=True)
    memory_plane = fields.Selection([...], required=True, index=True, readonly=True)
    state_ref = fields.Char(required=True, readonly=True)
    causal_parent_refs_json = fields.Text(readonly=True)
    authority_scope_refs_json = fields.Text(required=True, readonly=True)
    retention_policy_ref = fields.Char(required=True, readonly=True)
    evidence_root = fields.Char(required=True, readonly=True)

class W7TPNodeExecutionLease(models.Model):
    _name = "w7tp.node.execution.lease"
    lease_ref = fields.Char(required=True, index=True, readonly=True)
    packet_ref = fields.Char(required=True, index=True, readonly=True)
    authority_node_ref = fields.Char(required=True, readonly=True)
    worker_node_ref = fields.Char(required=True, readonly=True)
    state = fields.Selection([...], required=True, readonly=True)
    issued_time_uint64 = fields.Char(required=True, readonly=True)
    expiry_time_uint64 = fields.Char(required=True, readonly=True)
    result_root = fields.Char(readonly=True)
    evidence_root = fields.Char(required=True, readonly=True)
```

Record rules separate community, organization, actor and business scopes. Personal consent, organization authority and Total Field decision remain separate fields and checks. AI candidates never directly write formal accounting, POS settlement or payment state.

## 12. POS product design

Online state machine:

`CART → QUOTED → AUTHORIZATION_PENDING → CANDIDATE_READY → POSTED_TO_ODOO → AUTHORITY_ACCEPTED → SETTLED → AUDITED`

Offline state machine:

`OFFLINE_CART → OFFLINE_CANDIDATE → LOCAL_GTP_PACKET → RECONNECT → MISSING_REF_NEGOTIATION → TOTAL_FIELD_DECISION → ODOO_PROJECTION → RECEIPT_RETURNED`

Required refs: product, price, voucher, merchant, operator, terminal, order, session, `packet_ref`, `logical_time_uint64`, `parent_state_root`, `receipt_ref`, audit and evidence roots. Reconnect sends current base refs and only missing atoms; it never blindly replays all operations. `(packet_ref, parent_state_root, receipt_ref)` is the idempotency boundary.

## 13. Committee and association design

`COMMITTEE_BODY` governs shared property/community affairs, common facilities, management fees, property services, common space and resident resolutions. `ASSOCIATION_BODY` governs community development, public-interest services, volunteers, care, merchant district, external cooperation and community/public-interest funds.

Resolution state machine:

`DRAFT → AGENDA_ACCEPTED → MEETING_OPEN → QUORUM_CONFIRMED → RESOLVED → EFFECTIVE → EXECUTION_IN_PROGRESS → COMPLETED → EXPIRED | REVOKED`

Machine execution requires resolution, quorum, scope, effective/expiry time, responsible actor, budget scope and evidence root. Total Field translates a valid human resolution into precise D8 conditions; it does not replace that resolution.

## 14. Community service state machine

`INTENT_RECEIVED → CONSENT_CHECKED → RIGHTS_SCOPE_VALID → ELIGIBILITY_CHECKED → RESPONSIBLE_UNIT_ASSIGNED → SERVICE_CANDIDATE → AUTHORITY_ACCEPTED → EXECUTION_IN_PROGRESS → EVIDENCE_RECORDED → COMPLETED | HOLD | REVOKED`

Residents, merchants, volunteers, committee/association bodies and accountable service workers remain distinct actors. Service evidence is stored as refs; medical, identity, contact or member plaintext is not copied into Packet8D or memory records.

## 15. Engineering state machine

`FOUNDER_INTENT → PACKET8D_ENGINEERING → EVIDENCE_RESOLVED → TASK_SCOPED → CODEX_CANDIDATE → CANDIDATE_ROOTED → TOTAL_FIELD_REVIEW → SEALED → RELEASE_READY → CONTROLLED_CUTOVER`

Codex may edit only task-authorized paths, generate delta checks and release evidence. It cannot self-authorize deployment, organization decisions, financial action, DB mutation, router mutation or receipt issuance.

## 16. Linux mesh design

`SYSTEM_NODE(node)` requires VPN peer presence, valid manifest, Total Field registration, allowed role, fresh heartbeat, valid state root and non-revoked status. An unknown peer becomes `QUARANTINED` and gets an existing DLQ reference.

Roles:

- MSI Windows: Founder interface, local-model entry, human authorization source.
- MSI WSL: Founder candidate, Codex development, build/test candidate and GTP packet generation.
- taiji01: Total Field authority, verifier, Native ADI primary, state sealer and receipt issuer.
- Linux worker: inference, GTP reconstruction, transform/build, read replica and cold recovery candidate.
- Merlin: boundary, route guard, replay tombstone and DLQ mailbox edge.

Selection sorts eligible nodes by role match, authority boundary, local base/model presence, missing-ref bytes, queue depth, CPU/GPU/RAM, latency band, thermal/energy and canonical node ref. No external scheduler becomes the technical root.

Node/lease state machines:

- Node: `CANDIDATE → ACTIVE → DEGRADED | OFFLINE | QUARANTINED | REVOKED`.
- Lease: `ISSUED → ACKNOWLEDGED → RUNNING → RESULT_CANDIDATE → ACCEPTED | EXPIRED | REJECTED`.

The first valid committed result wins. Late or duplicate results go HOLD/DLQ without affecting unrelated nodes.

## 17. Dead Letter flow

Failures include integrity mismatch, replay, unknown node, expired lease, authority mismatch, unresolved ref, root mismatch, conflict, quota overflow and human review required.

```text
failure
  → strict reason code
  → existing Dead Letter adapter
  → hash/ref-only DeadLetterReference
  → optional Merlin USB/JFFS reference when live status permits
  → governed retry, reconstruction, review or expiry
```

No second DLQ, parallel storage or raw payload queue is created. Merlin may reject or route; it may not produce ALLOW. The current live USB/JFFS status pointer remains `UNRESOLVED_POINTER` until the exact current reference is located.

## 18. API contracts

9110 remains node-local. Cross-node ingress is `VPN → existing Gateway → capability/manifest/lease checks → localhost service`.

Core routes:

- `GET /health`, `GET /metrics`
- `POST /v1/adi/insert`, `POST /v1/adi/search`
- `POST /v1/gtp/delta`, `/missing-refs`, `/reconstruct`
- `POST /v1/mesh/node/register`, `/node/state`, `/task/dispatch`, `/result/submit`
- `POST /v1/authority/receipt/verify`
- Gateway projections for Odoo, POS and Merlin remain adapters over existing owners.

Response envelope:

```json
{
  "state": "CANDIDATE|ALLOW|HOLD|BLOCK",
  "request_ref": "ref",
  "packet_ref": "ref-or-null",
  "node_ref": "ref",
  "logical_time_uint64": 0,
  "evidence_root": "sha256",
  "decision": "CANDIDATE|ALLOW|HOLD|BLOCK"
}
```

Cross-node mutations additionally require `execution_lease_ref`, `namespace_ref` and either a valid `authority_receipt_ref` or explicit `CANDIDATE`. Business projections also require the appropriate human/organization/merchant authority scope.

## 19. File ownership map

| Domain | Existing owner | Target owner/action |
|---|---|---|
| Packet ontology | Native ADI + Total Field packet docs | `core/w7tp_state_field/packet8d.py` only if no existing canonical owner can be extended |
| Actor/authority refs | identity/Atlas/Total Field refs | `core/w7tp_state_field/actor.py`, `authority.py`; ref-only |
| Canonical JSON/root | `services/w7tp_native_adi/core.py` | extract one owner to `canonical.py` |
| ADI/spiral/query | same core | keep algorithms, extract `spiral.py`, bounded query in `core.py` |
| GTP | same core | `gtp.py`, wrapping carried-forward verifier |
| Mesh | edge manifests + topology | `mesh.py` with registry/lease/result candidate state |
| Memory | `runtime/memory`, Atlas memory map, Odoo AI memory | `memory.py` router; refs only across planes |
| Total Field authority | existing reviewer/receipts | `authority_adapter.py`; no second authority |
| Persistence | Native ADI snapshot/events | `persistence.py`; append-only + atomic + quotas |
| HTTP | current Native ADI service | `service.py`; delegation only, loopback-only |
| Gateway | `services/gateway/topology_router.py` | extend existing route owner with `state_router.py`/capability helpers only when justified |
| XiaoJ | `core/xiaoj/*` | add compiler/context/fuser modules around existing classes; no parallel XiaoJ runtime |
| DLQ/Merlin | `runtime/dead_letter`, `runtime/router` | existing adapters only |
| Odoo institutional twin | existing `wuchang_core` and `wuchang_*` | extend exact models; add ref-only models inside existing addon where necessary |

## 20. Confirmed correction backlog

Each row is a future implementation delta, not a reopened historical PASS.

| # | Correction | CURRENT_OWNER | CURRENT_EVIDENCE_REF | CURRENT_STATE | TARGET_OWNER / INTERFACE | FILES_TO_CHANGE | MIGRATION_STEP | ROLLBACK_BOUNDARY | ACCEPTANCE_EVIDENCE | DEPENDENCIES |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | strict canonical type | Native ADI core | current candidate diff + base receipt | CURRENT_UNCOMMITTED_CANDIDATE | `canonical.py`: strict JSON/tag/root | Native ADI canonical/core/init | compatibility import, versioned root | old release and state untouched | type distinctions, NaN/Inf block, candidate manifest | WAVE_0 owner map |
| 2 | logical_time_uint64 | Native ADI core | candidate uint64 change | CURRENT_UNCOMMITTED_CANDIDATE | core/models: epoch/unit/slot width | canonical/models/core | versioned coordinate metadata | no live snapshot rewrite | two-runtime deterministic coordinate check | correction 1 |
| 3 | O(1) collision address | current `spiral_position` | base PASS + current source | CARRIED_FORWARD_PASS | `spiral.py` rich NativeAddress | core/spiral/models | compatibility adapter | retain old coordinate reader | deterministic ordinal/address + bounded hotspot target | correction 2 |
| 4 | occupied-slot query | Native ADI core | current bisect candidate | CURRENT_UNCOMMITTED_CANDIDATE | core query with radius/slots/deadline | core/service | add request version | previous endpoint remains one release | empty/sparse query and deadline evidence | corrections 1–2 |
| 5 | invalid/past/future time | candidate packet validator | current core | CURRENT_UNCOMMITTED_CANDIDATE | separate logical vs expiry validators | canonical/core/gtp | map stable reason codes | old errors accepted by compatibility client | branch-specific delta checks | correction 2 |
| 6 | snapshot resources | Native ADI persistence | base snapshot + candidate byte/TTL | CURRENT_UNCOMMITTED_CANDIDATE | persistence quotas/TTL/eviction | persistence/core/service | read-only v1.0→candidate conversion + manifest | no pointer swap without readability proof | quota/eviction/crash-recovery fixture | corrections 1–2 |
| 7 | integrity/authority separation | Native ADI + Total Field | packet-root candidate; existing receipt producer | CURRENT_UNCOMMITTED_CANDIDATE | `authority_adapter.py` | gtp/authority/service | bind compatible receipt scope | no receipt means CANDIDATE | forged ALLOW blocked; exact existing receipt accepted | UNRESOLVED Native ADI receipt pointer |
| 8 | existing DLQ integration | runtime Dead Letter | existing writer + candidate callback | CURRENT_UNCOMMITTED_CANDIDATE | ExistingDeadLetter adapter | adapters/service/persistence | package/inject existing writer | no new storage; base writers remain | existing `dlq_ref` for defined failures | correction 7 |
| 9 | node capability/lease | edge manifests/Gateway | all-node pointer + node_boot | CARRIED_FORWARD_PASS | mesh registry/lease/result | mesh/models/persistence/gateway | register behind disabled capability | no peer auto-promotion | unknown peer quarantined; one commit | edge state pointer, corrections 1–2 |
| 10 | GTP parent/delta/missing refs | Native ADI GTP | base lookup PASS + candidate delta | CURRENT_UNCOMMITTED_CANDIDATE | `gtp.py` missing-ref protocol | gtp/models/service | schema adapter 1.0→next | preserve carried-forward verifier | missing-only supply invoking existing verifier | corrections 1,6,7 |
| 11 | Odoo authority projection | existing wuchang_core | active POS chain + model owners | CARRIED_FORWARD_PASS | ref-only models/adapters | existing addon exact files after model audit | add fields/models without formal writes | module not upgraded until approval | schema/access/fixture evidence only | correction 7, exact existing-owner audit |
| 12 | POS offline commit | pos.order/wuchang.order | active official POS chain | CARRIED_FORWARD_PASS | POSFieldAdapter + event ref | existing POS controller/model/service | offline candidate queue schema; no replay-all | old online chain remains default | idempotency/offline reconnect fixture | corrections 7,10,11 |
| 13 | committee resolution authority | meeting/property owners | existing Odoo models | CARRIED_FORWARD_PASS | CommitteeAuthorityAdapter | existing addon resolution projection | body-scope mapping, no data migration initially | current meeting flow remains | quorum/scope/effective/expiry fixture | correction 11 |
| 14 | multilayer memory routing | Atlas/runtime/Odoo memory | memory lifecycle map | CARRIED_FORWARD_PASS | MemoryPlaneRouter | Native ADI memory, XiaoJ context, Odoo ref projection | ref index only; no full-history copy | current memory stores remain | per-plane selection/retention/root fixture | corrections 1,7,10 |

## 21. Migration waves

- WAVE 0 — freeze evidence pointers and map owners; no code.
- WAVE 1 — canonical types, uint64 time, O(1) spiral extraction, query/snapshot resource bounds.
- WAVE 2 — GTP parent/delta/missing refs, existing authority receipt adapter, existing DLQ adapter.
- WAVE 3 — Linux mesh manifest/role/lifecycle/lease/result receipt.
- WAVE 4 — Odoo state packet and receipt ref projections inside existing owners.
- WAVE 5 — POS offline/online GTP event and idempotent commit.
- WAVE 6 — committee/association resolution authority.
- WAVE 7 — nine-plane memory router and local-twin dynamic context.
- WAVE 8 — operator console, observability and controlled one-service cutover.

No wave is merged into one large patch. Each consumes the previous wave evidence root and produces a new candidate root/manifest.

## 22. Rollback boundaries

- WAVE 1: compatibility imports and old state reader remain; no active pointer change.
- WAVE 2: no compatible receipt means CANDIDATE; existing DLQ is never replaced.
- WAVE 3: mesh routes default disabled; removing capability registration restores pre-mesh behavior.
- WAVE 4–6: no Odoo module upgrade or DB migration until separate authority; projections can remain uninstalled.
- WAVE 7: existing memory stores remain authoritative; new router is ref-only and reversible.
- WAVE 8: rollback may restore only the prior immutable Native ADI release pointer and restart only that service after explicit authority. It never rewrites DB, router, DLQ, ledger or snapshots.

## 23. Future minimal acceptance evidence

Only changed/new invariants receive future checks:

1. strict canonical parse/root fixture.
2. uint64 coordinate cross-runtime fixture.
3. O(1) address and bounded hotspot fixture.
4. sparse/deadline query fixture.
5. snapshot quota/eviction/recovery fixture.
6. compatible existing receipt adapter fixture.
7. existing DLQ adapter fixture.
8. unknown node/lease/single-commit fixture.
9. missing-ref negotiation fixture that calls the carried-forward verifier.
10. Odoo model/schema/access fixture, without DB migration in preflight.
11. POS offline idempotency fixture.
12. committee/association scope fixture.
13. memory-plane selection/retention fixture.

The 100,000 benchmark, equivalent reconstruction proof, existing health smoke, full repo tests, full DLQ suite and all-node scan remain excluded.

## 24. Product competitiveness targets

No new performance number is claimed. Unmeasured targets are explicitly `TARGET_NOT_YET_MEASURED`.

| Domain | Metric/goal | Current claim |
|---|---|---|
| Performance | state lookup p50/p95, hotspot insert p50/p95 | TARGET_NOT_YET_MEASURED |
| Performance | base-ref hit rate, missing bytes, transfer-reduction ratio | TARGET_NOT_YET_MEASURED |
| Performance | local model/data locality and no full-state replay | target architecture, not measured |
| Reliability | append-only events, atomic snapshots, replay prevention | baseline components carried forward; expanded behavior not measured |
| Reliability | lease expiry, idempotent commit, offline recovery | TARGET_NOT_YET_MEASURED |
| Governance | unauthorized ALLOW, duplicate commit, split brain | hard target `0`; not a current measurement |
| Correctness | accepted result root match rate | hard target `1.0`; future changed-path evidence only |
| Community | service, merchant, volunteer, fund, POS, committee, association coverage | target product scope; no market claim yet |
| Operability | evidence lookup, topology, node/DLQ/receipt/Odoo/POS refs | WAVE 8 target |

## 25. Unresolved pointers and stale evidence

`UNRESOLVED_POINTER` items:

1. Exact existing Total Field receipt verifier/scope compatible with Native ADI state promotion.
2. Current Merlin USB/JFFS mailbox health/status reference; historical fixture is not current state.
3. Current durable edge-node lifecycle/heartbeat state pointer under the prescribed runtime state path.
4. Existing execution-lease ledger owner/reference, if one is already indexed.

`STALE_EVIDENCE_REBIND_REQUIRED` items:

1. `services/w7tp_native_adi/core.py` candidate hash versus deployed/base receipt hash.
2. `services/w7tp_native_adi/service.py` candidate hash versus deployed/base receipt hash.

These states require future pointer/hash rebinding only. They do not downgrade the carried-forward product landing.

## 26. Next patch scope

`APPLY_BLUEPRINT_WAVE_1_WITH_EXISTING_TOTAL_FIELD_EVIDENCE`

Wave 1 must begin with exact target-file review and preserve the existing candidate diff. It may repair only canonical type ownership, uint64 coordinate contract, direct spiral extraction and resource bounds, then produce delta-only evidence and a candidate manifest. It must not deploy, restart, modify DB/router, create a second Total Field/DLQ/Native ADI, or re-run historical proof.
