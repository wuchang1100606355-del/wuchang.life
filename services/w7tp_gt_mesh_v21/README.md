# W7TP V2.1 incremental generative-transmission mesh

This is a Python 3.11+, standard-library-only node adapter for the locked W7TP V2.1 canonical. It does not modify Taiji_Hub and it does not implement a parallel canonical core.

Pinned canonical:

- ID: `W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1`
- path: `docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md`
- SHA-256: `e960d14254df083ffed711e2c44b76fc2075541716881bc3d1034cb26cffbaba`
- machine schema SHA-256: `cf3df7380e70d0b4bb21635ddc6f1f097713cf94fbf8428966713c949ff1d135`

The adapter must be deployed together with the existing subset that provides:

- `w7tp_runtime.state_field.canonical.canonical_json_bytes` and `sha256_ref`
- `w7tp_runtime.state_field.object_packet_store.ObjectPacketStore`
- `w7tp_runtime.state_field.controlled_experiment_v1.bridge.build_delta/apply_delta`

If any dependency is absent, startup returns `HOLD_W7TP_CORE_SUBSET_UNAVAILABLE`; there is no hidden fallback.

## Closed flow

`cycle` performs one bounded metadata collection, stores an immutable snapshot, evaluates exact wire payload sizes, builds an interactive coupled 8D packet, emits local Drive projections when configured, and sends the carrier to every configured peer. Failed sends enter an append-only outbox and `retry` replays them without deleting history.

The economic gate compares exact mode-specific marginal object-packet bytes for:

1. direct canonical snapshot;
2. the established single-delta bridge;
3. the observed US VM ADI known/novel V3 block-token packet.

The smallest exact reconstructable representation wins; ties choose the mode with fewer reconstruction dependencies. The V3 cost therefore includes its independently hashed lookup-profile CAS object and the extra object wrapper, not only `body_hex`. V3 carries per-block coordinates, known token IDs, novel residual bytes, source binding, and exact target SHA-256. No synthetic GiB/s result is produced.

The observed W7G3 wire layout, decoder rules, source SHA, and fixed US `:8082` vector are exact compatibility evidence. They are not an end-to-end benchmark for this mesh: the V2.1 profile, packet, lookup, canonical `body_hex` wrapper, carrier, HTTP stack, and receipts add distinct bytes and latency. The economic gate is an object-packet cost decision, not a complete HTTP throughput measurement.

The receiver validates canonical root shape, no-float canonical JSON, payload/profile/lookup hashes, interactive 8D closure, all shared packet/profile replay coordinates, TTL, nonce, monotonic logical time, parent/base identity, and reconstructed target hash. It appends packet, lineage, reconstructed state, and receipt. HTTP or Tailscale is carrier only and has authority `NONE`; reconstructed metadata remains packet evidence until a Total Field decision.

## Authority and scheduler boundary

`authority:TOTAL_FIELD` is the sole logical authority. `8D_ADI` is the `PRIMARY_DECISION_ENGINE` and explicitly has authority state `NOT_AUTHORITY`. The pinned V2.1 root retains the canonical `LOCAL_TOTAL_FIELD` boundary labels required by the machine schema; every mutable authority reference in the packet is cross-bound to `authority:TOTAL_FIELD`.

The canonical role coordinate binds `node:taiji01` as Total Field verifier, Native ADI primary, state sealer, and receipt issuer. MSI remains Founder interface/build/test/GTP source plus Drive projection; neither its receiver nor Drive projection is authority. The mesh transport stays symmetric, while remote deployment routes directly to both taiji01 and MSI.

Each carrier includes immutable scheduler capability and control-contract objects. CPU, GPU, RAM, disks, node/container targets, and container-runtime counts are available for scheduling decisions. `build_task_envelope` validates an extensible node/container task envelope, but every such envelope remains `HOLD_UNTIL_TOTAL_FIELD_AUTHORIZATION_VERIFIED` and `execution_permitted=false`. This package has no service/container/hardware executor and does not mutate existing services.

On taiji01 only, optional `native_adi_url=http://127.0.0.1:9110` sends a bounded append-only record to `/v1/adi/insert` after local verification or remote exact reconstruction. The absolute integer `time_slot` is derived from the snapshot's observed UTC time; node-local logical time remains a separate payload coordinate. The payload contains only bounded references, hashes, and that local coordinate, stays below 64 KiB, and never embeds a snapshot. Exact retries are idempotent, divergent `422` records are conflicts, and availability failures enter an append-only Native ADI outbox.

## Indexed metadata

- node OS/Python/CPU/RAM/disk/GPU/IP/Tailscale/virtualization coordinates;
- bounded `tailscale status --json` discovered-node evidence containing only node ID/name/DNS/OS/addresses/online/active/key-expiry fields;
- configured system or user services;
- containers plus images, volumes, and networks without environment or mount secret content;
- listeners;
- explicitly curated file metadata and optional explicitly requested SHA-256;
- optional exact-root Git root/branch/HEAD/remote locator hash/diff count as `D4_EVIDENCE`, `EVIDENCE_ONLY`, `NOT_ESTABLISHED_BY_GIT`.

Git dirtiness never blocks the collector and Git never establishes authority or live effect.

## Drive spool

`drive_spool_root` is a low-cost projection root. Every artifact is one canonical JSON envelope with:

`schema_id`, `projection_relative_path`, `artifact_sha256`, embedded `artifact`, `source_node_ref`, `packet_id`, `logical_time`, `created_at`, and `envelope_sha256` computed with the self-hash field excluded.

Projection roots are `01_NODE_INDEX`, `02_FILE_INDEX`, `03_LINEAGE`, `04_EVIDENCE`, `06_RECONSTRUCTION`, `07_GITHUB`, and `08_RECEIPTS`. Scheduler capabilities and safe discovered-node evidence are projected beneath `01_NODE_INDEX`; `07_GITHUB` accepts only the exact three-field D4 evidence gate. Drive presence is not canonical authority, activation, or live effect.

## Commands

```text
python3 -m w7tp_gt_mesh --config config.json doctor
python3 -m w7tp_gt_mesh --config config.json collect --spool
python3 -m w7tp_gt_mesh --config config.json cycle
python3 -m w7tp_gt_mesh --config config.json retry
python3 -m w7tp_gt_mesh --config config.json serve
```

Install the service and timer templates under the target user's systemd user directory only after setting the real subset path, config path, node ID, Tailscale peer addresses, runtime root, and MSI-visible spool root. Service installation, start, restart, deployment, activation, and routing remain separate authorized operations.

## Verification

Run the complete suite against the live pinned schema:

```text
W7TP_V21_SCHEMA_PATH=/path/to/schemas/versioned/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.cf3df7380e70d0b4bb21635ddc6f1f097713cf94fbf8428966713c949ff1d135.json \
PYTHONPATH=/path/to/existing-core-subset:. \
python3 -m unittest discover -s tests -v
```

The suite covers exact machine schema validation, Total Field/decision-engine boundaries, non-executing task envelopes, capability CAS objects, baseline and single-delta reconstruction, V3 live vectors and mixed known/novel coordinates, strict V3 numeric/header binding, lookup-inclusive economic selection, full replay-coordinate binding, TTL, replay/idempotence, HTTP receive-to-MSI spool, Native ADI record hooks, observed round-trip integers, user-service scope, container subobjects, bounded safe Tailscale discovery, Drive gates, and multi-peer cycle.
