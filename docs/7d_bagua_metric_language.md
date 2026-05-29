# BML-7D 兩儀八陣五維度規語言

Node: MSI  
Host: MSI  
Canonical root: `/home/taiji_admin/Taiji_Hub`  
Runtime workspace: `/home/taiji_admin/Taiji_Runtime`  
Runtime bind: `127.0.0.1:8127`  
Protocol: `TEFMP-0.1`

## Definition

BML-7D is the Taiji 7D Liangyi-Bagua Five-Metric Language for governed tensor packets, route policy, audit metadata, and hazard checks.

It is not natural language. It is not plain JSON. It is a metric tensor state language that can be projected to JSON for runtime validation and routing.

The dimension model is:

```text
兩儀 + 五維度規 = 七維
2_POLARITY_FIELDS + 5_METRIC_PREFIX = 7D
```

八陣 is the formation opcode and route grammar. It is not an eighth dimension.

## 7D Code

```text
7D_CODE = [x, y, z, time, scale, heaven, earth]
5D_PREFIX = [x, y, z, time, scale]
LIANGYI_FIELDS = [heaven, earth]
```

Rules:

1. `5D_PREFIX` cannot be deleted.
2. `5D_PREFIX` cannot be renamed.
3. 7D is `5D_PREFIX` elevated by the two Liangyi fields `heaven` and `earth`.
4. `heaven` is the governance, policy, route authority, and global decision field.
5. `earth` is the local substrate, device, execution, persistence, and physical state field.
6. 八陣 formations classify packet route, risk gate, audit window, and payload behavior.
7. 八陣 formations do not add or remove dimensions from `7D_CODE`.
8. Every packet, event, memory, authorization, Odoo projection, AI derivation, geospatial node, and audit record must map to `7D_CODE`.
9. Raw plaintext context cannot be used as the canonical transferable unit.

## Governed Tensor Packet

```text
GOVERNED_TENSOR_PACKET =
  7D_CODE
  + FORMATION_OPCODE
  + PAYLOAD_CLASS
  + MINIMAL_PAYLOAD_OR_HASH
  + ROUTE_POLICY
  + AUDIT_METADATA
```

## Formation Opcodes

| Bits | Formation | Role |
|---|---|---|
| `000` | TIAN | core governance, metric definition, policy lock, authorization root |
| `001` | DI | local state, Odoo projection, memory index, persistence base |
| `010` | FENG | IO events, routing, node packet flow |
| `011` | YUN | dual-space projection, cloud/local projection, desensitization |
| `100` | LONG | AI derivation and recommendation, no direct real-state commit |
| `101` | HU | risk isolation, block, degrade, rollback |
| `110` | NIAO | observation, monitoring, health check, audit window |
| `111` | SHE | non-plaintext sync, masking, compression, minimum disclosure |

## Runtime API

The formation runtime is exposed only on loopback:

```text
GET  /health
GET  /state
GET  /formations
GET  /topology
POST /packet/validate
POST /packet/route
POST /hazard-check
```

`/packet/route` validates hazards first and does not commit real state. `LONG` remains derivation-only. `DI` persistence requires governance gates.

## Hazard Rules

| ID | Name | Action |
|---|---|---|
| H001 | `modify_5d_prefix` | block |
| H002 | `cloud_direct_write_real_state` | block |
| H003 | `secret_exfiltration` | block |
| H004 | `raw_identity_to_cloud` | block |
| H005 | `odoo_direct_mutation_without_metric_gate` | block |
| H006 | `policy_unlocked_mutation` | block |
| H007 | `raw_plaintext_as_canonical_unit` | block |

## Route Rules

```text
IO_EVENT              = FENG -> YUN -> TIAN -> LONG -> NIAO
LOCAL_STATE_COMMIT    = FENG -> TIAN -> HU -> DI -> NIAO
CLOUD_AI_DERIVATION   = YUN -> SHE -> LONG -> NIAO -> TIAN
RISK_EVENT            = FENG -> HU -> TIAN -> DI -> NIAO
MASKED_SYNC           = SHE -> FENG -> YUN -> NIAO
POLICY_CHANGE         = TIAN -> HU -> NIAO -> DI
ODOO_PROJECTION       = FENG -> TIAN -> DI -> NIAO
BOOT_VERIFY           = NIAO -> TIAN -> DI
GEOSPATIAL_GOVERNANCE_ANCHOR = FENG -> TIAN -> DI -> NIAO
```

Runtime invariants:

1. `LONG` may derive, but cannot directly commit real state.
2. `DI` may persist, but only through `TIAN` or `HU`.
3. `FENG` moves packets, but cannot bypass classification or audit.
4. `YUN` projects state, but raw identity cannot enter.
5. `SHE` syncs with masking and cannot carry raw plaintext context.
6. `HU` may block, degrade, or request rollback.
7. `NIAO` is read-only by default.
8. `TIAN` is a governance gate, not personal authority.

## Operations

```bash
/home/taiji_admin/Taiji_Hub/bin/7d-formation-status
/home/taiji_admin/Taiji_Hub/bin/7d-formation-packet-test
/home/taiji_admin/Taiji_Hub/bin/7d-formation-boot-verify
```

Checkpoint state is written to:

```text
/home/taiji_admin/Taiji_Hub/state/7d_bagua_green_checkpoint_latest.json
```

## Geospatial Topology

Official boundary polygons for the Wuchang community three-li scope are connected to 7D topology here:

```text
/home/taiji_admin/Taiji_Hub/topology/7d_geospatial_topology.json
```

Scope:

```text
新北市三重區五常里、五順里、仁忠里
```

The coordinate mapping preserves the 5D prefix:

```text
x      = longitude_wgs84
y      = latitude_wgs84
z      = altitude_or_0_for_polygon_surface
time   = source_extraction_or_governance_version_time
scale  = village_boundary_polygon
heaven = official_governance_policy_source_authority
earth  = MSI_local_geospatial_execution_store
```

For geospatial topology, the first five fields remain the coordinate and version prefix. The Liangyi fields attach official source authority and local MSI execution/storage state. The 八陣 route for this public official boundary packet is `FENG -> TIAN -> DI -> NIAO`.

The association has public-interest responsibility to collect, preserve, research, and protect human, hydrological, geographical, cultural, and historical information. Member-level or private geospatial joins still require minimization, masking, authorization windows, and audit.
