# W7TP / 8DADI / GST / Origin Cell — Total Field Results Freeze Candidate

**Session window:** 2026-09-17 → 2026-09-18 (Asia/Taipei)  
**State:** `CANDIDATE_FOR_TOTAL_FIELD_REVIEW`  
**Authority:** Founder-declared architecture + observed experiment evidence only  
**Canonical write:** `NONE`  
**Runtime activation:** `NONE`  
**Deployment / restart / DB write:** `NONE`  

This document freezes the results and Founder intent formed in the session without silently promoting them to canonical or runtime authority. Observed evidence, reconstructed interpretation, Founder intent, and unresolved items are kept separate.

## 1. Founder intent frozen in this candidate

The system is not LLM-centric. The intended architecture is:

```text
NATURAL PERSON / MEMBER INTENT
          |
          v
      INTENT FIELD
          |
          v
 ORIGIN-CELL CONTROLLER
          |
          v
    TOTAL FIELD AUTHORITY
          |
   +------+------+-------------------+
   |             |                   |
   v             v                   v
LOCAL SMALL LLM  DISTRIBUTED ORGANS  CLOUD LLM
NEURAL CONDUCTION CPU/GPU/NPU/IO      REPLACEABLE LOW-COST LIBRARY
   |             |                   |
   +-------------+-------------------+
                 |
                 v
        D6 / GST NEURAL LINK
                 |
          +------+------+
          |             |
          v             v
     LOCAL MEMORY   CLOUD MEMORY
      NEAR / HOT     EXTENSION / COLD
```

Founder-defined role boundaries:

- **Intent Field** is the continuously operating intent/state field; it is not an LLM session or prompt.
- **Origin Cell** is the minimum indivisible carrier of a complete D1–D8 state, and the Origin-Cell Controller is responsible for state decomposition, reuse, completion, transition, reconstruction, and convergence.
- **Total Field** is the unique authority for identity, evidence, policy, risk, state acceptance, and external effect. A model output cannot become authority by itself.
- **Local small LLM** is a neural-conduction organ: natural-language / voice / perception translation, candidate generation, local presentation, and signal routing. It is not the sovereign brain.
- **Cloud LLM** is a replaceable low-cost external library. It supplies knowledge or candidate reasoning only and may be replaced by another provider without moving identity or authority.
- **Distributed compute devices** retain their strongest local capabilities but are downgraded in authority to organs of the same Total Field.
- **Execution may be asynchronous while authority remains unified**: `ASYNCHRONOUS_EXECUTION + UNIFIED_STATE_AUTHORITY`.

## 2. Member-bound shared capability architecture

The intended member product is capability sharing without cross-member plaintext mixing.

```text
MEMBER / NATURAL PERSON
        |
        v
IDENTITY + SEAT + ACCESS PROFILE
        |
        v
MEMBER-BOUND INTENT FIELD
        |
        +--> shared local compute / small LLM
        +--> shared GST transport capability
        +--> shared cloud-LLM provider pool
        +--> local memory references
        +--> cloud memory references
```

Invariants frozen here:

- Shared endpoint or compute does not merge member identity, memory, or authority.
- Account is an authentication channel, not the natural-person root.
- One active member/XiaoJ/Seat/access-profile binding is required for governed context.
- Cross-member plaintext is forbidden unless separately and explicitly authorized by policy.
- Read permission does not imply write, execution, deployment, canonical, or decision permission.
- External effect remains under Total Field / D8 authority.

## 3. Cross-system / cross-language / cross-carrier interpretation

Founder intent: 8DADI is a state interoperability layer rather than a single-language or single-system runtime.

The same logical 8DADI state packet may be reconstructed by different target-native systems and languages when they satisfy the same state, evidence, policy, risk, authority, and verification contract.

```text
SAME INTENT / SAME STATE CONTRACT
       |
       +--> Python / Linux receiver
       +--> Android receiver
       +--> Odoo receiver
       +--> other target-native receiver
```

The carrier is not the authority and is not D6 by itself. Sea cable, fixed IP, 5G, Wi-Fi, Bluetooth, microwave, and satellite may carry the same **logical canonical packet identity** through carrier-specific transport envelopes.

Desired principle:

`CARRIER_AGNOSTIC_STATE_PACKET + CARRIER_AWARE_TRANSMISSION_OPTIMIZATION`

This means the core state contract remains stable while MTU, fragmentation, retransmission, FEC, latency handling, cost policy, and route selection may vary by carrier.

**Current evidence boundary:** direct cross-node IPv6 transport has been exercised. Dedicated 5G, submarine-cable-specific, and satellite-carrier tests are not yet established by this candidate.

## 4. D6 / GST frozen construction rule

D6 Generative Transmission is target-aware:

```text
TARGET_BASE_STATE
+ MINIMUM_REQUIRED_DELTA
+ REFERENCES
+ COORDINATES
+ RECONSTRUCTION_RULES
+ VERIFICATION_RULES
```

The target should reuse verified target-native resources and receive only state that evidence proves cannot already be satisfied or reconstructed locally.

The system is therefore not defined as ordinary full-copy transfer or ordinary differential synchronization. The transfer cost is intended to track destination-unknown / unreconstructable state rather than total target size when a verified reusable base exists.

## 5. Observed GST evidence retained without rerun

### 5.1 Existing replaceable / Chunk-GST evidence

`OBSERVED`

- Complex 1 GiB-class target:
  - `TARGET_BYTES=1076912128`
  - `TARGET_FILES=4099`
  - `TARGET_MANIFEST_SHA256=d81f931f9dfd1c4e650681dad3527c5d3812bbd54049b4363c264f4e0a419e9a`
- Full packet:
  - `FULL_BYTES=1083217920`
  - `FULL_MEDIAN_MS=228324.528268`
- Chunk-GST packet:
  - `GST_BYTES=49459200`
  - `GST_CHANGED_CHUNKS=226`
  - `GST_CHANGED_CHUNK_PAYLOAD_BYTES=47996928`
  - `GST_MEDIAN_MS=12896.093234`
- Measured comparison:
  - `PAYLOAD_SAVINGS_PERCENT=95.434049`
  - `MEDIAN_TIME_CHANGE_PERCENT=94.351858`
- Cross-node verification:
  - `REMOTE_FULL_MANIFEST_MATCH=True`
  - `REMOTE_GST_MANIFEST_MATCH=True`
  - `REMOTE_GST_RECONSTRUCT_MS=83138.357885`
  - `REMOTE_GST_MAXRSS_KB=31860`
- Direct IPv6 underlay check:
  - `DIRECT_IPV6_UNDERLAY=PASS`
  - observed direct endpoint `[2600:1900:4001:b37::]:41641`
- Adapter SHA-256:
  - `218ee34874c4ceecdc29ed2697d41ad45ef845bd334cb6bb8611b66131bcea69`
- Receipt SHA-256:
  - `bac73e87dc79e3d55133d22b57f9e189eaad46dad8c880d248fed3b75d69595e`
- Known receipt naming defect: the 1 GiB run retained a hard-coded `COMPLEX_IPV6_256M_...` filename. The recorded `dataset_mib_requested=1024` / 1 GiB values remain the meaningful run data. Do not rerun solely to fix the filename.

Interpretation boundary: this is a warm-base reconstruction benchmark, not a cold-start benchmark.

### 5.2 Origin-Cell construction evidence

`OBSERVED`

Origin-cell adapter SHA-256:

`8ff6cb34dca458a33c108b7ae53acd3ac23cf38a8e8ceb67c40fd55ae68cdef1`

32 MiB isolated self-test:

```text
SELFTEST=PASS
ORIGIN_PACKET_BYTES=11540480
ORIGIN_CELLS=1564
ORIGIN_CELL_PAYLOAD_BYTES=7192576
MANIFEST_MATCH=True
```

1 GiB same-target Origin-Cell candidate construction:

```text
BASE_BYTES=1075847168
TARGET_BYTES=1076912128
TARGET_FILES=4099
TARGET_MANIFEST_SHA256=d81f931f9dfd1c4e650681dad3527c5d3812bbd54049b4363c264f4e0a419e9a
CHUNK_GST_BYTES=49459200
ORIGIN_GST_BYTES=13107200
ORIGIN_CELLS=1566
ORIGIN_CELL_PAYLOAD_BYTES=7200768
ORIGIN_METADATA_BYTES=3544155
ORIGIN_VS_CHUNK_SAVINGS_PERCENT=73.498965
```

Important observed scaling fact for this fixed-mutation workload:

- 32 MiB self-test: 1564 cells / 7,192,576 payload bytes.
- 1 GiB candidate: 1566 cells / 7,200,768 payload bytes.

The target size increased strongly while Origin-Cell payload increased only by two cells / 8,192 bytes in this benchmark because the mutation workload was intentionally near-fixed. This supports the hypothesis that packet cost can track changed-state complexity rather than total target size **for this workload**.

### 5.3 Origin-Cell unresolved cross-node boundary

`UNKNOWN / NOT YET PROMOTED`

At the point of this freeze, this candidate does **not** promote the 1 GiB Origin-Cell cross-node run to `CROSS_NODE_PASS` or `END_TO_END_PASS` unless target-emitted evidence separately records at least:

```text
REMOTE_ORIGIN_MANIFEST_MATCH=True
ORIGIN_TRANSFER_MEDIAN_MS=<observed>
ORIGIN_MEDIAN_TAILSCALE_TX_DELTA=<observed>
REMOTE_ORIGIN_RECONSTRUCT_MS=<observed>
REMOTE_ORIGIN_MAXRSS_KB=<observed>
```

The already-proven IPv6 carrier capability is reused evidence; it is not a new uncertainty requiring another carrier proof.

## 6. Total Field organ model

The distributed-node relationship frozen by Founder intent is:

```text
TOTAL FIELD
   |
   +--> perception organs
   +--> compute organs
   +--> storage organs
   +--> execution organs
   +--> communication organs
   +--> local model organs
```

Each organ may execute independently and asynchronously, but may not create a second sovereign Total Field or promote a local candidate to global authority.

Capability union is preferred over weakest-common-denominator execution:

```text
C_total = union(verified organ capabilities needed by current intent)
```

The shared object is the state/intent contract, not identical OS, CPU, model, language, or carrier.

## 7. Neural-link and dual-memory model

Founder intent freezes the following product metaphor and system boundary:

- **GST / D6** = governed neural link between organs.
- **Local small LLM** = neural conduction / translation layer.
- **Local disk / local state stores** = near / hot memory.
- **Cloud disk / remote object stores** = expandable / cold memory.
- **Cloud LLM** = external library, not memory root, identity root, or authority.

Local and cloud storage should be exposed as one logical memory namespace through references, coordinates, hashes, logical time, policy, and evidence rather than by mandatory full mirroring.

A device replacement should not require identity migration into the new model. A newly authorized member device should be able to reconstruct only the member-bound state it is permitted to use from memory references + current state + minimum required delta.

## 8. Coffee-shop member low-cost AI product direction

`FOUNDER_INTENT / PRODUCT_DIRECTION`

Goal: provide coffee-shop members with very low-cost AI without requiring every member to purchase an independent premium cloud-AI subscription.

Cost-control order:

```text
1. local neural layer
2. governed local/cloud memory retrieval
3. target-native reuse / GST
4. cloud LLM only when the task exceeds local capability
```

Shared resources may include local CPU/GPU, small LLM, GST transport, cloud-provider pool, and memory infrastructure. Member identity, allowed memory, state, and authority remain separate.

This product direction is not yet a production-cost guarantee. A member-level cost benchmark and privacy/security acceptance test remain future evidence.

## 9. Patent evidence boundary frozen from the same session

`OBSERVED FROM USER-SUPPLIED TIPO RECEIPT AND FILING PACKAGE`

- TIPO invention application has been received.
- Application number: `115127138`.
- Filing date: `2026-07-08`.
- Filed title: `多維度結構封包及其安全裁決方法與應用程式`.
- The supplied filing package contained `ABST.docx`, `CLMS.docx`, `DESC.docx`, and drawing material.
- The filed claims/specification include the eight-dimensional packet and D6 generative-transmission terminology, including reference / local reconstruction concepts.

`LEGAL INTERPRETATION CANDIDATE, NOT LEGAL AUTHORITY`

The session review did not establish that current Origin-Cell / receiver-base / minimum-required-delta transmission optimization is expressly claimed in the filed independent claims. Preserve this as an IP follow-up question; do not rewrite filing history.

## 10. Evidence and governance invariants

The following remain fixed:

```text
SOURCE_SIDE_EVIDENCE != TARGET_PASS != CROSS_NODE_PASS != END_TO_END_PASS
```

- Carrier success alone is not reconstruction success.
- Source-side construction cannot manufacture target evidence.
- Target-only state must be preserved unless an exact authorized transition says otherwise.
- LLM output is candidate material.
- Cloud provider availability does not grant authority.
- Member access scope follows identity + active Seat + access profile, not prompt text.
- Historical evidence is append-only.
- No canonical promotion, runtime activation, deployment, restart, DB write, route change, or patent filing change is authorized by this freeze candidate.

## 11. Candidate status matrix

| Item | State at freeze |
|---|---|
| 8DADI D1–D8 state contract | `EXISTING / REUSED` |
| D6 target-aware GST construction | `EXISTING / REUSED` |
| 1 GiB Chunk-GST cross-node reconstruction | `OBSERVED PASS` |
| 32 MiB Origin-Cell isolated self-test | `OBSERVED PASS` |
| 1 GiB Origin-Cell packet construction | `OBSERVED PASS` |
| Origin vs Chunk packet reduction (same 1 GiB workload) | `OBSERVED 73.498965%` |
| 1 GiB Origin-Cell remote reconstruction | `UNKNOWN UNTIL TARGET EVIDENCE` |
| Satellite carrier proof | `UNKNOWN / NOT TESTED HERE` |
| Dedicated 5G carrier proof | `UNKNOWN / NOT TESTED HERE` |
| Coffee-shop member low-cost AI production economics | `PRODUCT DIRECTION / NOT YET BENCHMARKED` |
| Total Field canonical promotion of this document | `NONE` |
| Runtime activation from this document | `NONE` |

## 12. Frozen architectural sentence

> **8DADI runs the Intent Field; Origin Cells are the controllable complete-state units; the Total Field holds unique authority; local small LLMs act as neural conduction; cloud LLMs are replaceable low-cost libraries; distributed devices are asynchronous organs; GST is the governed neural link; member identity bounds shared capability; and local/cloud stores form an expandable logical memory while authority remains unified.**

This sentence is frozen as Founder intent in this candidate. It is not itself proof of every runtime capability.
