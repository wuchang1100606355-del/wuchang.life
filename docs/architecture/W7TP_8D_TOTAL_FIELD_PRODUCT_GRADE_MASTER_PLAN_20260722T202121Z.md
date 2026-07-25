# W7TP 8D Total Field Product-Grade Master Plan

- State: `PASS_EVIDENCE_DRIVEN_PRODUCT_PLAN_READY`
- Run ID: `20260722T202121Z`
- Authority: `TOTAL_FIELD_SERVER_MASTER`
- Base deploy run: `20260722T190044Z`
- Base service: `W7TP_NATIVE_ADI_AGENT`
- Base endpoint: `http://127.0.0.1:9110`
- Base evidence root: `e8ca44347802f33ead0827e54fd71c9ccce36016b98ed17da9f2ca28c62bac59`
- Planning mode: evidence retrieval first; no deploy, restart, DB write, router write, or revalidation of carried-forward PASS.

## 1. Decision boundary

This plan preserves the current candidate diff and treats the deployed release as the proven baseline. It does not re-prove equivalent reconstruction, GTP viability, Total Field existence, dead-letter existence, VPN system scope, or the 100,000-record benchmark.

GTP remains a protocol-native 8D intent-field packet and equivalent-state reconstruction mechanism. It is not file moving, cloud sync, backup, download decryption, generic compression, or a claim that arbitrary existing files can be reconstructed from a small packet.

The only implementation target is the delta between the base release and the current candidate, plus the product-grade mesh, authority, persistence, gateway, and business-projection seams described below.

## 2. TOTAL_FIELD_EVIDENCE_MAP

Allowed evidence states are `CARRIED_FORWARD_PASS`, `EVIDENCE_CONFIRMED`, `EVIDENCE_STALE`, and `IMPLEMENTATION_DELTA`. `EVIDENCE_REFERENCE_NOT_YET_LOCATED` means only that the next exact Total Field reference must be resolved; it is not a statement that the capability does not exist.

| Component | Current owner | Evidence ref | Run ID / root | Current state | Carried forward | Current diff impact | Implementation delta | Target owner | Next code action |
|---|---|---|---|---|---|---|---|---|---|
| Founder canonical memory | Founder interface + Total Field pointer | `runtime/total_field/master_index/ACTIVE_GT_8D_PACKET_POINTER.json` | `TOTAL_FIELD_GT_8D_PACKET_20260623_105658` / packet SHA `b9ed61…0090` | EVIDENCE_CONFIRMED | Founder source and 8D definition | None | Add ref-only projection; do not duplicate memory authority | existing Total Field | `adapters.py` reads refs only |
| 8D packet | Total Field packet owner | active pointer and pointed packet path | `TOTAL_FIELD_GT_8D_PACKET_20260623_105658` | CARRIED_FORWARD_PASS | `GTP_PACKET_STRUCTURE=PASS` | Candidate changes packet schema 1.0→1.1 | Versioned migration and response envelope | `gtp.py` | Extract packet model without changing proven reconstruction semantics |
| GTP equivalent reconstruction | Native ADI | `runtime/total_field/native_adi/W7TP_NATIVE_ADI_PRODUCT_LANDING_20260722T190044Z.json` | base evidence root | CARRIED_FORWARD_PASS | roots, counts, bytes, lookup, reconstruction | Candidate adds parent/delta fields | Missing-ref negotiation only; reuse verifier | `gtp.py` | Move delta construction behind compatibility adapter |
| Native ADI deployed release | systemd user service | base landing report; `/home/taiji_admin/.config/systemd/user/w7tp-native-adi.service`; active release `d7bfb93bb1956f27` | `20260722T190044Z` | EVIDENCE_CONFIRMED | deployed and health PASS | `core.py` and `service.py` source hashes differ from release | Controlled new release only after delta acceptance | `core.py` | Keep live 9110 untouched until cutover |
| Native ADI candidate diff | current worktree | `services/w7tp_native_adi/core.py`, `service.py`, `tests/test_w7tp_native_adi_red_blue.py` | source hashes `804ad9…0fa`, `57f742…7a1`, test `16b2c6…d81` | IMPLEMENTATION_DELTA | baseline unaffected | strict JSON, uint64, slot index, packet root, receipt/DLQ callbacks, snapshot/delta changes | Complete and isolate responsibilities; repair observed delta-test input mismatch | target module owners | Apply only in controlled patch run |
| Total Field | existing reviewer and master index | `tools/total_field/w7tp_d8_reviewer_entrypoint.py`; master index pointer | existing reviewer receipts | CARRIED_FORWARD_PASS | authority presence | Candidate callback has no live verifier provider | Adapter to compatible existing receipt scope | `authority.py` | Locate compatible receipt contract before ALLOW wiring |
| Codex development | MSI WSL candidate lane | current worktree diff and base landing report | base run + current hashes | EVIDENCE_CONFIRMED | candidate-only build role | Candidate is not deployed | Preserve candidate-only status | build/test lane | No promotion without receipt and manifest |
| Local LLM | registered service topology | `configs/taiji_topology.json`; `02_edge_nodes/taiji01/node_boot.yaml` | topology version `2026-05-23-current-topology` | EVIDENCE_CONFIRMED | VPN multi-node scope | Native ADI is not yet in topology service map | Route capability, not direct 9110 exposure | Gateway + node registry | Register capability after manifest validation |
| Cloud candidate intelligence | candidate-only lane | active Total Field pointer execution policy | `TOTAL_FIELD_GT_8D_PACKET_20260623_105658` | CARRIED_FORWARD_PASS | candidate-only boundary | None | Result packets remain candidates | mesh selection | No ALLOW or direct business mutation |
| Odoo | edge-node business owner | `02_edge_nodes/odoo/node_boot.yaml` | canonical edge node v1 | EVIDENCE_CONFIRMED | Odoo/POS governance scope | No Native ADI projection route in current gateway map | Receipt-gated projection, no direct DB write | Odoo adapter | Define ref-only candidate intake contract |
| POS | Odoo edge-node role | `02_edge_nodes/odoo/node_boot.yaml` role/allow lists | canonical edge node v1 | CARRIED_FORWARD_PASS | POS scope | No execution-lease contract | Receipt + namespace + lease required for mutations | POS projection | Add adapter contract only in future patch |
| Community | Total Field governance projection | fixed carry-forward instruction; `runtime/ledger/total_field_design_ledger.jsonl` | `XIAOJ_MEMBER_SIDEBAR_TOTAL_FIELD_20260613_052845` | CARRIED_FORWARD_PASS | community governance scope | No new member identity or consent binding | Ref-only community namespace | projection layer | Never infer member authorization from node identity |
| Committee / association | governance projection | same Total Field ledger record and carried-forward scope | ledger hashes recorded | CARRIED_FORWARD_PASS | committee/association scope | No execution path added | Candidate discussion/project state only | projection layer | Require existing business authorization before effects |
| Memory layers | Native ADI state + Total Field pointer + ref stores | base landing report state/snapshot refs; active pointer | base run | CARRIED_FORWARD_PASS | snapshot resolution PASS | Candidate changes state schema and adds tombstones/receipt consumption | Namespace quota, TTL, deterministic eviction, migration reader | `persistence.py` | Separate event, snapshot, and projection stores |
| VPN Linux nodes | registered-node model | fixed VPN scope PASS; node manifests in `02_edge_nodes/` | current topology evidence | CARRIED_FORWARD_PASS | multi-node system scope | Current topology lists four logical nodes but not product-grade lifecycle/lease state | Manifest registry, heartbeat freshness, role/capability filter | `mesh.py` | VPN presence alone never grants node status |
| Node registry | edge boot + topology | `boot/start_edge_node.sh`; `02_edge_nodes/*/node_boot.yaml`; `configs/taiji_topology.json` | current files | EVIDENCE_CONFIRMED | edge-node boundary | `runtime/state/edge_nodes/` has no current referenced record in examined path | Durable manifest/lifecycle registry adapter | `mesh.py`, `adapters.py` | Bind state files and ledger refs without auto-registering peers |
| Gateway | existing FastAPI gateway | `services/gateway/topology_router.py`; `services/gateway/main.py`; `configs/taiji_topology.json` | current source | EVIDENCE_CONFIRMED | existing route owner | Exact service map examined does not route Native ADI/9110 | Add capability-gated candidate proxy; keep 9110 node-local | existing Gateway | Extend current router; do not create another gateway |
| Merlin Router | router guard / manual plan chain | `runtime/router/merlin_intent_driver.py`, `merlin_apply_queue.py`, `merlin_approval_gate.py` | current source | CARRIED_FORWARD_PASS | Merlin boundary present | Current modules are plan/record-only | Mailbox status and append-ref adapter only | `adapters.py` | Preserve block-or-route-only authority |
| Merlin USB/JFFS mailbox state | Merlin edge | governance fixture under `runtime/data_breathing_flow/W7TP_8D_ROUTER_USB_DLM_20260630_072002/` | historical run | EVIDENCE_REFERENCE_NOT_YET_LOCATED | mailbox architecture carried forward | No current live status reference found in specified runtime paths | Resolve live status ref before cutover | Merlin mailbox adapter | No router probe or write in implementation patch |
| Dead Letter | existing hash-only and route-specific writers | `runtime/dead_letter/dead_letter_24h_hash_writer.py`; `24h_hash_mailbox/dead_letter_hash_queue.jsonl`; gateway reject writer | current source/queue | CARRIED_FORWARD_PASS | dead-letter system present | Candidate binds Native ADI callback; deployment bundle currently contains only Native ADI service files | One adapter over existing writers; no new storage | `adapters.py` | Package/import existing writer or inject it from Gateway |
| Replay protection | receipt single-use and candidate tombstones | D8 receipt fields `single_use_consumed`, `replay_disposition`; candidate receipt set | existing reviewer + diff | CARRIED_FORWARD_PASS | replay logic present | Candidate persistence ordering needs crash-safe commit design | Atomic consume/commit event with idempotent result | `persistence.py`, `authority.py` | Commit receipt consumption before returning ALLOW |
| Authority receipt | Total Field D8 reviewer | `tools/total_field/w7tp_d8_reviewer_entrypoint.py:882`; existing receipt directories | reviewer v3 receipts | EVIDENCE_CONFIRMED | Total Field authority exists | Current known receipt scopes are review/canary-oriented; Native ADI compatible live ref not yet resolved | Verify through existing producer/verifier only | `authority.py` | `EVIDENCE_REFERENCE_NOT_YET_LOCATED` for Native ADI-compatible scope |
| Execution lease | planned mesh control | no exact live lease evidence ref located in prescribed paths | n/a | IMPLEMENTATION_DELTA | none required for baseline 9110 | No lease class, persistence, expiry, or duplicate-commit control | Add candidate task lease state machine | `models.py`, `mesh.py`, `persistence.py` | Lease never grants Total Field ALLOW |
| Snapshot / ledger | Native ADI persistent state and existing ledgers | base report state paths; `runtime/ledger/total_field_design_ledger.jsonl`; event log path in base report | base run | EVIDENCE_CONFIRMED | snapshot resolution PASS | Candidate v1.1 reader only explicitly accommodates empty v1.0 snapshot | Dry-run migration validator and reversible pointer cutover | `persistence.py` | Never rewrite live snapshot in planning or pre-cutover validation |

## 3. Carried-forward PASS table

The following 22 facts are accepted without revalidation:

1. `PASS_NATIVE_ADI_PRODUCT_LANDED`
2. `DEPLOYED=true`
3. `HEALTH=PASS`
4. `TESTS=PASS_3_OF_3`
5. `100000_RECORD_DEMO=PASS`
6. `ID_EQUIVALENT=PASS`
7. `BYTE_EQUIVALENT=PASS`
8. `PACKET_REFERENCE_LOOKUP=PASS`
9. `SNAPSHOT_RESOLUTION=PASS`
10. `EXPECTED_ROOT_VERIFY=PASS`
11. `EXPECTED_COUNT_VERIFY=PASS`
12. `EQUIVALENT_STATE_RECONSTRUCTION=PASS`
13. `GTP_PACKET_STRUCTURE=PASS`
14. `TOTAL_FIELD_AUTHORITY_PRESENT=PASS`
15. `DEAD_LETTER_SYSTEM_PRESENT=PASS`
16. `REPLAY_DEAD_LETTER_PRESENT=PASS`
17. `VPN_MULTI_NODE_SYSTEM_SCOPE=PASS`
18. `MERLIN_BOUNDARY_PRESENT=PASS`
19. `ODOO_POS_COMMUNITY_GOVERNANCE_SCOPE=PASS`
20. `ADI_ABSOLUTE_TIME_POSITION=PASS`
21. `SAME_TIME_CROSS_SECTION=PASS`
22. `NATIVE_SPIRAL_COLLISION=PASS`

## 4. Current owner and deployed/candidate split

The deployed release is `/home/taiji_admin/.local/share/w7tp-native-adi/releases/d7bfb93bb1956f27`, selected by `current`, and runs from `127.0.0.1:9110`. Its `core.py` and `service.py` hashes match the base landing report.

The worktree candidate deliberately differs:

| File | Deployed SHA-256 | Candidate SHA-256 | Classification |
|---|---|---|---|
| `core.py` | `c50f44c409d657c006a6a5070fcf5456a7ba58c0455cc003f9cb4e7c3ebe5b19` | `804ad93813cae000dbb3c54a72444c3ea102863137394161cd06c124379e30fa` | EVIDENCE_STALE + IMPLEMENTATION_DELTA |
| `service.py` | `f5118ae1ce20f409de9d15c8a1248fd716fd6018dbcce7ba9c771106790f73e2` | `57f7428186f8c06f966ce8c63ea7cf7cca121414c037145a25c6a18eb8f1f7a1` | EVIDENCE_STALE + IMPLEMENTATION_DELTA |
| `__init__.py` | `43e8b3ad…621a6` | same | CARRIED_FORWARD_PASS |
| `__main__.py` | `2cbbef37…55e3` | same | CARRIED_FORWARD_PASS |

Observed candidate deltas include strict list-only JSON normalization, explicit type tags, uint64 bounds, an occupied-slot index, query budgets, packet/snapshot budgets, parent delta fields, packet-root separation, receipt callbacks, replay tracking, tombstones, and an existing DLQ writer import. These are not deployed facts.

One earlier delta-only test attempt observed six passing tests and one input-contract failure: the sparse-query case supplied `max_records=10` while retaining default `limit=100`, so validation correctly returned `QUERY_BUDGET_INVALID` before the expected occupied-slot budget branch. The future patch must repair the test input or contract; it must not alter historical PASS evidence.

## 5. Red/blue convergence matrix

| Concern | Existing protection | Candidate delta | Product-grade correction |
|---|---|---|---|
| Canonical types | base serializer already omits `default=str` and blocks non-finite floats | tuple is now rejected; type tags added to records/state/packet | single owner in `canonical.py`; explicit tagged extension values only |
| Logical time | absolute integer slot mapping PASS | range extended to uint64 | define epoch, unit, width, and slot count; no float authority coordinate |
| Spiral | direct square-spiral coordinate already exists | next collision ordinal retained | extract O(1) `collision_ordinal_to_address`; include turn/rank/page/radius/direction/ordinal |
| Sparse query | base query sorts scanned keys | bisect occupied-slot index and budgets added | add max radius and monotonic deadline; empty index returns immediately |
| Time errors | base rejects invalid range | packet past/future/invalid split added | separate logical-time validation from wall-clock lease/snapshot expiry |
| Snapshot resources | atomic temp + replace and fsync PASS | item/snapshot byte limits and TTL metadata added | namespace quota, count/total bytes, deterministic eviction, crash receipt |
| Authority | Total Field exists | packet root separated; verifier callback added | adapter to compatible existing receipt; no callback provider means CANDIDATE |
| DLQ | existing DLQ system PASS | Native ADI callback added | one adapter, writer failure is explicit HOLD/BLOCK, no duplicate queue |
| Replay | existing replay concept PASS | consumed receipt set and tombstones added | persist consume + result commit atomically and idempotently |
| Mesh | VPN system scope PASS | no registry/lease implementation yet | manifest + registry + lifecycle + lease + result receipt |
| GTP delta | lookup/reconstruction/root PASS | parent, changed, deleted added | add receiver base root and missing-ref negotiation; retain existing verifier |
| Business projection | Odoo/POS/community scope PASS | no new projection path | adapters accept candidate refs; only receipt-gated business layer may act |

## 6. Target topology and authority invariant

```text
Founder natural-person interface
        │
MSI Windows ── MSI WSL/Codex (candidate-only)
        │              │
        └──── 8D GTP candidate packet ────┐
                                          │ VPN private mesh
                                  existing Gateway
                                          │ capability route
                               taiji01 Total Field
                                  │             │
                         execution lease   immediate verify
                                  │             │
                        registered worker ─ result packet
                                          │
                                existing authority receipt
                                  │             │
                               ALLOW        HOLD/BLOCK
                                  │             │
                         business adapter   existing DLQ
                                                   │
                                          Merlin USB/JFFS ref
```

Invariants:

- taiji01 is the unique ALLOW issuer; workers return candidates only.
- VPN visibility is not node registration.
- 9110 remains localhost-only. Cross-node requests use VPN → existing Gateway → route capability → service.
- Packet and state roots prove integrity/equivalence, not authority.
- An execution lease authorizes bounded work, not business commit and not Total Field ALLOW.
- Odoo/POS/community/committee projections never infer consent or cross-member authority from `node_ref`, `member_ref`, or network reachability.
- Router authority is block-or-route-only and cannot upgrade a decision to ALLOW.

## 7. Data model design

`models.py` is the single owner for immutable cross-module values. Mappings are validated strict JSON before model construction.

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

class NodeLifecycle(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"

class AuthorityDecision(str, Enum):
    CANDIDATE = "CANDIDATE"
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"

@dataclass(frozen=True, slots=True)
class NativeAddress:
    logical_time_uint64: int
    time_slot_uint64: int
    cross_section_center: int
    collision_ordinal: int
    turn: int
    spiral_rank: int
    page: int
    radius: int
    direction: int
    ordinal: int

@dataclass(frozen=True, slots=True)
class NodeManifest:
    node_ref: str
    vpn_ref: str
    os_profile: str
    role_refs: tuple[str, ...]
    capability_refs: tuple[str, ...]
    authority_level: int
    trust_level: int
    manifest_root: str

@dataclass(frozen=True, slots=True)
class NodeResourceState:
    cpu_available_uint: int
    ram_available_bytes: int
    storage_available_bytes: int
    gpu_profile_ref: str | None
    io_band: int
    vpn_latency_band: int
    thermal_band: int
    queue_depth: int

@dataclass(frozen=True, slots=True)
class NodeStatePacket8D:
    packet_ref: str
    node_ref: str
    logical_time_uint64: int
    D1_intent: Mapping[str, Any]
    D2_state: Mapping[str, Any]
    D3_coordinate: Mapping[str, Any]
    D4_evidence: Mapping[str, Any]
    D5_execution: Mapping[str, Any]
    D6_definition: Mapping[str, Any]
    D7_risk: Mapping[str, Any]
    D8_envelope: Mapping[str, Any]
    state_root: str

@dataclass(frozen=True, slots=True)
class GTPDeltaPacket:
    packet_ref: str
    protocol_version: str
    schema_version: str
    source_node_ref: str
    target_node_ref: str
    namespace_ref: str
    parent_snapshot_ref: str
    parent_state_root: str
    receiver_base_root: str | None
    changed_atoms: tuple[Mapping[str, Any], ...]
    deleted_atom_refs: tuple[str, ...]
    reconstruction_rule_ref: str
    canonical_version: str
    expected_result_root: str
    evidence_root: str
    candidate_decision: AuthorityDecision

@dataclass(frozen=True, slots=True)
class MissingRefRequest:
    packet_ref: str
    receiver_node_ref: str
    missing_refs: tuple[str, ...]
    receiver_base_root: str | None

@dataclass(frozen=True, slots=True)
class ExecutionLease:
    lease_ref: str
    task_ref: str
    authority_node_ref: str
    worker_node_ref: str
    issued_logical_time: int
    expires_logical_time: int
    required_role_refs: tuple[str, ...]
    expected_input_root: str
    lease_root: str

@dataclass(frozen=True, slots=True)
class ResultPacket:
    task_ref: str
    lease_ref: str
    worker_node_ref: str
    result_atom_refs: tuple[str, ...]
    result_state_root: str
    evidence_root: str
    completed_logical_time: int

@dataclass(frozen=True, slots=True)
class AuthorityReceipt:
    receipt_ref: str
    packet_ref: str
    candidate_node_ref: str
    authority_node_ref: str
    decision: AuthorityDecision
    candidate_state_root: str
    accepted_state_root: str | None
    issued_logical_time: int
    evidence_root: str
    existing_total_field_proof_ref: str

@dataclass(frozen=True, slots=True)
class DeadLetterReference:
    dlq_ref: str
    packet_ref: str
    node_ref: str
    reason_code: str
    evidence_root: str
    created_logical_time: int
```

## 8. File-by-file implementation design

| Target file | Canonical responsibility | Planned change | Must reuse / must not duplicate |
|---|---|---|---|
| `models.py` | dataclasses/enums only | add models above, no I/O | no authority or hashing logic |
| `canonical.py` | strict JSON, tags, roots, uint validation | move normalization/root functions; forbid tuple, bytes, datetime, NaN/Inf, `default=str` | one canonical owner |
| `spiral.py` | O(1) address math | extract current direct spiral and add page/turn fields | reuse proven native order |
| `core.py` | time slots, insert/query, in-memory namespace snapshots | slim current monolith; occupied index and budgets | no GTP/receipt/DLQ logic |
| `gtp.py` | delta, missing refs, reconstruction orchestration | wrap proven state-root verifier; add parent/base/missing-ref protocol | do not reimplement equivalent-root algorithm |
| `mesh.py` | registry, lifecycle, selection, leases, result routing | add deterministic filters and single-commit state | no VPN peer auto-trust |
| `authority.py` | existing Total Field receipt adapter | locate and call existing compatible verifier; fail to CANDIDATE | no new key/signature/Total Field |
| `persistence.py` | append-only events, atomic snapshots, lease/receipt state | namespace quota, deterministic eviction, crash receipts | preserve fsync + temp/replace |
| `adapters.py` | existing Gateway/DLQ/Merlin/heartbeat seams | dependency injection and ref-only records | no second DLQ or gateway |
| `service.py` | localhost HTTP/Unix interface | delegate only; uniform envelope; request limits | never directly expose 9110 to VPN |
| `__init__.py` | stable public exports | export versioned models/functions after migration | keep compatibility aliases for one release |
| `tests/test_w7tp_native_adi_red_blue.py` | delta-only checks | correct query-budget fixture; add only new seams | no 100,000 baseline rerun |
| `services/gateway/topology_router.py` | existing route owner | add Native ADI candidate capability and manifest checks | extend existing router only |
| `configs/taiji_topology.json` | topology declaration | add service ref/capability after evidence and review | do not include unregistered VPN peers |

## 9. Core function contracts

### canonical.py

```python
def validate_strict_json(value: Any) -> None: ...
def canonical_bytes(value: Any) -> bytes: ...
def canonical_root(value: Any) -> str: ...
def validate_uint64(value: int, field: str) -> int: ...
def encode_tagged_value(type_ref: str, value: Any) -> Mapping[str, Any]: ...
```

Preconditions: inputs are JSON-native or an explicitly supported tagged extension. Postconditions: identical values yield identical UTF-8 bytes across Linux runtimes; different JSON types do not collide. Errors: `BLOCK_CANONICAL_TYPE`, `BLOCK_NON_FINITE_NUMBER`, `BLOCK_UINT64_RANGE`. No implicit conversion exists.

### core.py and spiral.py

```python
def absolute_slot(logical_time_uint64: int, epoch_uint64: int,
                  slot_width_uint64: int, slot_count_uint64: int) -> int: ...

def insert_state_atom(logical_time_uint64: int,
                      atom: Mapping[str, Any]) -> NativeAddress: ...

def query_state_atoms(logical_time_uint64: int, *, query_8d_root: str | None,
                      max_results: int, max_radius: int, max_slots: int,
                      deadline_ns: int) -> list[Mapping[str, Any]]: ...

def spiral_rank_to_page(center: int, spiral_rank: int, page_count: int,
                        first_direction: int) -> tuple[int, int, int]: ...

def collision_ordinal_to_address(*, collision_ordinal: int, center: int,
    page_count: int, page_capacity: int, first_direction: int,
    logical_time_uint64: int, time_slot_uint64: int) -> NativeAddress: ...
```

`absolute_slot` uses checked integer subtraction/division and returns separate `BLOCK_PAST_LOGICAL_TIME`, `BLOCK_FUTURE_LOGICAL_TIME`, or `BLOCK_INVALID_LOGICAL_TIME`. Query first bisects the occupied-slot index, then enforces radius, slot count, result count, and monotonic deadline. Empty index returns immediately.

Spiral address pseudo-code:

```python
capacity_per_turn = page_count * page_capacity
turn = collision_ordinal // capacity_per_turn
within_turn = collision_ordinal % capacity_per_turn
spiral_rank = within_turn // page_capacity
ordinal = within_turn % page_capacity
page, radius, direction = spiral_rank_to_page(
    center, spiral_rank, page_count, first_direction
)
return NativeAddress(...)
```

No search begins at turn zero.

### gtp.py

```python
def build_delta(*, parent_snapshot_ref: str, target_snapshot_ref: str,
                source_node_ref: str, target_node_ref: str,
                namespace_ref: str) -> GTPDeltaPacket: ...
def determine_missing_refs(packet: GTPDeltaPacket,
                           receiver_known_refs: set[str]) -> MissingRefRequest | None: ...
def supply_missing_refs(request: MissingRefRequest) -> tuple[Mapping[str, Any], ...]: ...
def reconstruct_equivalent_state(*, local_base_state: Sequence[Mapping[str, Any]],
    packet: GTPDeltaPacket,
    supplied_atoms: Sequence[Mapping[str, Any]] = ()) -> tuple[Mapping[str, Any], ...]: ...
def verify_equivalent_root(reconstructed_state: Sequence[Mapping[str, Any]],
                           expected_result_root: str) -> None: ...
```

Flow: resolve parent snapshot → compare receiver base root → request only unresolved refs → apply deleted refs → apply changed atoms → canonicalize → call the existing equivalent-root verifier → emit candidate result. A root match is necessary but never sufficient for ALLOW.

### mesh.py

```python
def register_node(manifest: NodeManifest) -> str: ...
def update_node_state(packet: NodeStatePacket8D) -> None: ...
def classify_node_lifecycle(node_ref: str) -> NodeLifecycle: ...
def select_execution_node(*, required_roles: set[str], required_base_refs: set[str],
    minimum_resources: NodeResourceState, registry_snapshot_ref: str) -> str: ...
def issue_execution_lease(...) -> ExecutionLease: ...
def accept_result_packet(...) -> AuthorityReceipt | DeadLetterReference: ...
def expire_lease(...) -> None: ...
def quarantine_node(...) -> DeadLetterReference: ...
```

Selection filters non-ACTIVE, manifest-root mismatch, role/capability mismatch, and D7 blocks. Survivors are partitioned S0–S3 by base-ref availability and sorted by missing bytes, queue depth, VPN latency band, resource fitness, thermal band, and canonical `node_ref`. Lease expiry allows deterministic reassignment; `(task_ref, accepted_result_root)` has one commit record.

### authority.py, persistence.py, adapters.py

```python
class ExistingTotalFieldAuthorityAdapter:
    def locate_receipt_verifier(self) -> str: ...
    def verify_receipt(self, receipt: AuthorityReceipt) -> bool: ...
    def promote_candidate(self, packet_ref: str, candidate_root: str,
                          evidence_root: str) -> AuthorityReceipt: ...

class AppendOnlyEventStore:
    def append(self, event: Mapping[str, Any]) -> str: ...
    def iter_from(self, logical_time_uint64: int): ...
    def fsync(self) -> None: ...

class AtomicSnapshotStore:
    def write_candidate_snapshot(self, ...) -> str: ...
    def load_snapshot(self, ...) -> Mapping[str, Any]: ...
    def enforce_quota(self, ...) -> None: ...

class ExistingDeadLetterAdapter:
    def push(self, *, packet_ref: str, node_ref: str, reason_code: str,
             evidence_root: str) -> DeadLetterReference: ...

class MerlinMailboxAdapter:
    def status(self) -> Mapping[str, Any]: ...
    def append_reference(self, dlq_ref: DeadLetterReference) -> None: ...
```

The authority adapter must reject incompatible decision scope, consumed receipt, packet/root mismatch, authority-node mismatch, and expiry. It never creates a signing key or parallel receipt. Persistence orders `validate → append candidate event → fsync → atomic snapshot → verify snapshot root → append commit/consume receipt → fsync → return`; recovery replays idempotently from the last complete commit.

## 10. API contracts

Existing endpoints remain compatibility routes for one release. New canonical routes are:

- `GET /health`
- `GET /metrics`
- `POST /v1/adi/insert`
- `POST /v1/adi/search`
- `POST /v1/gtp/delta`
- `POST /v1/gtp/missing-refs`
- `POST /v1/gtp/reconstruct`
- `POST /v1/mesh/node/register`
- `POST /v1/mesh/node/state`
- `POST /v1/mesh/task/dispatch`
- `POST /v1/mesh/result/submit`
- `POST /v1/authority/receipt/verify`

Every response contains:

```json
{
  "state": "CANDIDATE|ALLOW|HOLD|BLOCK",
  "request_ref": "request-ref",
  "packet_ref": "packet-ref-or-null",
  "node_ref": "node-ref",
  "logical_time_uint64": 0,
  "evidence_root": "sha256",
  "decision": "CANDIDATE|ALLOW|HOLD|BLOCK"
}
```

Every cross-node mutation also requires `execution_lease_ref`, `namespace_ref`, and either a valid `authority_receipt_ref` or explicit `CANDIDATE`. Gateway verifies manifest, role, capability, namespace, and lease before forwarding. It never forwards raw credentials or member plaintext.

## 11. State machines

### Node

`VPN_PEER_PRESENT → CANDIDATE → ACTIVE | QUARANTINED`; ACTIVE may become DEGRADED, OFFLINE, QUARANTINED, or REVOKED. Only a valid manifest, Total Field registration, allowed role, fresh heartbeat, valid state root, and non-revoked status produce ACTIVE.

### Packet / authority

`RECEIVED → CANONICAL_VALID → ROOT_VALID → RECONSTRUCTED → EQUIVALENT_ROOT_VALID → CANDIDATE_VERIFIED → RECEIPT_VALID → ALLOW_COMMITTED`. Any failure routes a reference to the existing DLQ. Authority offline stops at CANDIDATE.

### Lease

`ISSUED → ACKNOWLEDGED → RUNNING → RESULT_CANDIDATE → ACCEPTED | EXPIRED | REJECTED`. A late result after EXPIRED is HOLD. Reassignment creates a new lease ref; the first valid committed result wins.

### Snapshot

`CANDIDATE_WRITTEN → FSYNCED → ROOT_VERIFIED → ACTIVE_POINTER_SWAPPED`. Quota enforcement sorts evictable snapshots by `(expires_logical_time, created_logical_time, snapshot_ref)`; pinned base/active snapshots are never evicted.

## 12. Product projections

- LLM: choose a registered worker that already has the model/base refs; send prompt-state delta, rule refs, and required context atoms; return result atoms and roots.
- Content-addressed large results: exchange atom/chunk manifests and missing refs only. This remains protocol reconstruction, not a claim of arbitrary-file small-packet transfer.
- Episodic memory: route to nodes with matching `base_state_ref`; transmit changed conversation atoms, not the full history.
- Builds: MSI WSL creates candidates; a registered worker may compile and run targeted checks; taiji01 verifies result roots.
- Odoo/POS/community/committee: accept ref-only candidates; business transactions remain in their existing authorization layer and never occur from worker output alone.

## 13. Performance and safety targets

Metrics: active/degraded/quarantined node counts; dispatch/lease/worker/verify seconds; base-ref hit rate; missing/full bytes; transfer-reduction ratio; hotspot insert and query p50/p95; snapshot bytes/evictions/hit rate; replay/root-mismatch/unauthorized-ALLOW/duplicate-commit/split-brain counts.

Hard targets:

- `unauthorized_allow_count = 0`
- `duplicate_commit_count = 0`
- `split_brain_count = 0`
- `root_match_rate = 1.0`
- hotspot insertion grows approximately linearly for fixed payload size
- sparse query cost scales with occupied slots visited, bounded by deadline and budgets

## 14. Migration order

1. Freeze the base evidence refs and deployed hashes; do not touch the active pointer.
2. Correct only candidate-delta defects already observed: query test contract, receipt provider boundary, event/receipt commit ordering, writer-failure handling, and schema naming consistency.
3. Extract `canonical.py`, `models.py`, and `spiral.py` with compatibility imports; run import/canonical/O(1) delta checks only.
4. Extract persistence without changing live paths; build a read-only validator for v1.0 and v1.1 snapshots. Non-empty v1.0 conversion requires an explicit migration artifact and hash receipt.
5. Extract `gtp.py` around the existing reconstruction verifier; add missing-ref negotiation without rerunning the baseline benchmark.
6. Add `authority.py` only after an exact compatible existing receipt verifier reference is located. Until then reconstruction remains CANDIDATE.
7. Add `adapters.py` over the existing DLQ, Gateway, Merlin status, and edge heartbeat. Do not create storage.
8. Add mesh registry and leases behind disabled route capability. Unknown VPN peers go QUARANTINED and obtain existing DLQ refs.
9. Extend the existing Gateway and topology config after manifest review; keep 9110 loopback-only.
10. Build a new immutable release and SHA-256 manifest; compare every target file with the approved candidate.
11. Founder-controlled cutover may restart only `w7tp-native-adi.service`; perform one health and one manifest/hash alignment check.
12. Enable mesh routes incrementally only after receipt, DLQ, and node-registry evidence refs are bound.

## 15. Rollback boundary

Rollback changes only the `current` release pointer and the single Native ADI service, after explicit authority. It does not rewrite database data, router configuration, existing event logs, DLQ records, or prior snapshots. The old release and state remain immutable. If the new reader has written schema 1.1 state, rollback is allowed only when the migration manifest proves the old release can read it; otherwise stop before cutover and retain candidate artifacts.

## 16. Delta-only checks

No baseline benchmark, equivalent-reconstruction proof, full repo test, all-node test, or health smoke is repeated before cutover.

1. `T01_STRICT_CANONICAL_TYPES`: JSON type distinction, tagged datetime distinction, NaN/Inf block.
2. `T02_UINT64_TIME_COORDINATE`: two Linux runtimes produce the same slot from declared epoch/unit/width.
3. `T03_O1_SPIRAL_ADDRESS`: stable address and near-linear hotspot insertion.
4. `T04_NODE_RECOGNITION`: visible unregistered VPN peer becomes QUARANTINED and receives existing `dlq_ref`.
5. `T05_EXECUTION_LEASE`: expired result cannot commit; reassigned task commits once.
6. `T06_EXISTING_AUTHORITY_RECEIPT`: no receipt stays CANDIDATE; compatible valid receipt permits the existing authority path to ALLOW.
7. `T07_EXISTING_DLQ_WIRING`: replay, root mismatch, unknown node, expired lease, and authority mismatch return refs from the existing adapter.
8. `T08_GTP_MISSING_REF_NEGOTIATION`: only missing refs are supplied; final check calls the carried-forward verifier rather than re-proving it.
9. `T09_TWO_LINUX_NODE_DISTRIBUTION`: MSI WSL candidate, taiji01 authority, one registered worker candidate; only taiji01 accepts the result root.

## 17. Acceptance criteria

- All 22 carried-forward PASS facts remain unchanged.
- Current candidate diff is preserved until the controlled implementation run.
- Exactly one canonical implementation owns serialization and roots.
- Node, lease, snapshot, packet, result, authority receipt, and DLQ refs are immutable typed models.
- Native ADI never produces ALLOW from packet integrity alone.
- Existing receipt and DLQ adapters are hash/ref-bound and deployment-packaged.
- 9110 remains node-local; Gateway is the only cross-node service ingress.
- Unknown nodes, replay, expired lease, authority mismatch, and root mismatch are fail-closed without broad outage.
- Snapshot quota and eviction are deterministic and crash recoverable.
- Odoo/POS/community/committee paths remain candidate/ref-only until their existing authorization layer accepts a valid receipt.
- New release hash and manifest align before the one-service cutover.
- No deploy, restart, DB write, router write, or git push occurs in this planning run.

## 18. Next controlled action

`APPLY_ONLY_IMPLEMENTATION_DELTAS` in one patch run, starting with the observed candidate test-contract correction and exact existing authority/DLQ adapter references. Historical PASS stages remain carry-forward evidence.
