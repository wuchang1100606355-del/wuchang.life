# W7TP Controlled Experiment V1

Candidate-only Phase B evidence loop for fixed synthetic byte workloads. It reuses exactly one existing Receiver implementation, `w7tp_runtime.gt_packet_v2.PacketV2.isolated_receive`, and does not import or call Total Field authority, canonical pointer, promotion, Odoo, member, nonce, deployment, or production-session modules.

## Run and verify

```bash
python3 tools/run_w7tp_controlled_experiment_v1.py run
python3 tools/run_w7tp_controlled_experiment_v1.py verify /tmp/w7tp_controlled_experiment_v1/<run-directory>
```

Each run creates a new directory under `/tmp/w7tp_controlled_experiment_v1/`. Files are created exclusively and never overwrite an earlier run. The run contains a resource catalog, five packet/receiver/reconstruction evidence sets, five immutable receipts, a static candidate UI, and a self-excluding SHA-256 manifest.

The core candidate intentionally excludes process probes and the optional
loopback HTTP API. GPU metadata therefore remains `UNKNOWN_UNVERIFIED`; the
static candidate UI is an output artifact, not deployment evidence.

## Evidence states

- CPU, RAM, and `/tmp` storage: `OBSERVED_DIRECT`, candidate-local lease only.
- GPU/VRAM: `UNKNOWN_UNVERIFIED`, `NOT_AUTHORIZED`.
- GPU reconstruction and pinned RAM modes: explicit `SIMULATED` implementations.
- Founder, member, identity root, 9107 session, 8D binding, Total Field decision, production canonical, and live Receiver authority: unchanged and not inferred.

Phase B proves functionality and byte identity for one fixed synthetic scenario. It does not satisfy Phase C paired A/B, failure-injection, p50/p95, real GPU, or quantitative reduction gates.
