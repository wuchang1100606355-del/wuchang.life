# Distributed Compute Boundary

版本：2026-05-11

## Current Phase

先打通分散式算力架構。

算力如何流動、如何計量、如何排程，容後再議。

## Boundary

The organization compute container zone and member device zone must remain strictly separated.

Allowed flow:

```text
member device
→ low-privilege request / capability signal
→ Taiji Gateway
→ Five Metric Gate
→ container compute service
→ result summary
→ audit
→ member device
```

Blocked flow:

```text
member device → direct container shell
container → member private files
member device → production DB write
container/member device → secret exchange
```

## Rule

Compute may flow.

The following may not flow:

- credentials
- secrets
- member plaintext
- private device files
- production write authority
- unmanaged remote-control authority

