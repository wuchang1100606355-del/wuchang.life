# Indexed proven facts

This file is a durable retrieval index for facts already established by direct implementation and execution. Re-check the original coordinates when drift matters; do not downgrade these facts merely because a new model has not loaded them yet.

## 1 GiB Origin Cell two-node reconstruction

```text
STATE=PROVEN_HISTORICAL_PASS
EXPERIMENT_ID=ORIGIN_CELL_IPV6_1024M_20260917T151904Z
SOURCE_NODE=taiji01
DESTINATION_NODE=wuchang-us-free-node
WARM_BASE=true
DATASET_MIB_REQUESTED=1024
TARGET_BYTES=1076912128
TARGET_FILES=4099
ORIGIN_PACKET_BYTES=13107200
ORIGIN_CELLS=1566
ORIGIN_CELL_PAYLOAD_BYTES=7200768
REMOTE_ORIGIN_MANIFEST_MATCH=true
ORIGIN_TRANSFER_MEDIAN_MS=2577.933825
ORIGIN_MEDIAN_TAILSCALE_TX_DELTA=15403232
REMOTE_ORIGIN_RECONSTRUCT_MS=109934.145708
REMOTE_ORIGIN_MAXRSS_KB=40884
SOURCE_NODE_COMPLETED=YES
DESTINATION_NODE_COMPLETED=YES
CROSS_NODE_PASS=YES
END_TO_END_EXPERIMENT_PASS=YES
RUNTIME_ACTIVATION=false
CANONICAL_WRITE=false
```

Target manifest:

```text
d81f931f9dfd1c4e650681dad3527c5d3812bbd54049b4363c264f4e0a419e9a
```

Original coordinates on `taiji01`:

- program: `/tmp/gst_origin_cell_ipv6_bench_v1_bundle/gst_origin_cell_ipv6_bench_v1.py`
- locked base program: `/tmp/gst_origin_cell_ipv6_bench_v1_bundle/gst_complex_ipv6_bench_v1.py`
- receipt: `/home/taiji_admin/Taiji_Hub/runtime/candidates/gst_replaceable_v1/receipts/ORIGIN_CELL_IPV6_1024M_20260917T151904Z.json`
- raw log: `/tmp/gst_origin_cell_1g_20260917T151100Z.log`
- Total Field registration receipt: `/home/taiji_admin/Taiji_Hub/runtime/candidates/gst_replaceable_v1/receipts/TOTAL_FIELD_REGISTRATION_20260917T133106Z.json`

Content identities:

- Origin Cell program SHA-256: `8ff6cb34dca458a33c108b7ae53acd3ac23cf38a8e8ceb67c40fd55ae68cdef1`
- base program SHA-256: `218ee34874c4ceecdc29ed2697d41ad45ef845bd334cb6bb8611b66131bcea69`
- receipt file SHA-256: `a5459ea4edae607ee691844130639f76a822151d14e7a3cf25e9897cdb66e23e`
- receipt canonical-body SHA-256: `dc38b90d71f80705e9fca78134196a49f1042a3da6bec3d0173ee3eec5e337fe`
- raw log SHA-256: `860570099234422dca430c4bff792a97be320e0880b4008835e000f337bc18c7`
- Total Field registration receipt file SHA-256: `6046c37db24e2c054bd8135d9ba3f6ec22d63829093fe21da307e2a9473cdda8`

Program closure:

- receiver reconstruction and verification: `gst_origin_cell_ipv6_bench_v1.py:321-365`
- source invokes receiver and fail-closes unless `ok=true`: lines `564-567`
- target result is embedded and sealed into the source receipt: lines `571-597`
- target temporary directory is cleaned only afterward: lines `621-623`

The cleanup of `/tmp/gst-origin-cell-ipv6-v1` is a post-success cleanup operation. It does not negate destination completion. A separately retained target-side JSON file was not part of the run's success contract.

Chunk-GST statistics in the receipt are a comparison reference only. The successful Origin Cell packet and reconstruction must not be replaced by, or reported as, the chunk-transfer result.

## PR #21 relationship

Public PR: `wuchang1100606355-del/wuchang.life#21`.

The frozen candidate document at commit `afc9152dec202a32b4fc6683334473dc3b01c4d3` retained an older documentation state:

- lines `204-216`: Origin Cell cross-node result listed as unresolved;
- line `320`: 1 GiB remote reconstruction listed as `UNKNOWN UNTIL TARGET EVIDENCE`.

The original target-emitted result and sealed receipt close the experiment result. Therefore:

```text
PR21_DOCUMENTATION_EVIDENCE_GAP=YES
EXPERIMENT_EXECUTION_GAP=NO
```

Preserve the old freeze as historical text. Any correction should be append-only and separately authorized; do not retroactively rewrite the historical state.

## Downloadable original bundle

Local bundle:

`FOUNDER_LOCAL_ARTIFACT_ROOT/ORIGIN_CELL_IPV6_1024M_20260917T151904Z_bundle.zip`

ZIP SHA-256:

`03be937e6f2aff5c5438f1d7f1b65c7e6213704f98037f38ef694336b77a1ac7`

The bundle contains the two original Python programs, raw run log, experiment receipt, and Total Field registration receipt. It is an ordinary preserved copy for inspection, not a new D6 transmission, deployment, rerun, or canonical promotion.

## Patent filing boundary

Historical filing coordinates recorded in the 2026-09-17/18 candidate:

- application number: `115127138`
- filing date: `2026-07-08`
- title: `多維度結構封包及其安全裁決方法與應用程式`

This supports existence of a filing. Do not infer current examination status, grant, enforceability, or exact claim coverage without current official patent evidence.
