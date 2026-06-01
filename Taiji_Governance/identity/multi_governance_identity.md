# Multi-Governance Identity Holder

## Identity Separation

The same natural person may hold multiple governance identities, but runtime must treat them as separate authority vectors.

```mermaid
flowchart TB
    HOLDER["Multi-Governance Identity Holder"]
    OWNER["Runtime Owner"]
    ARCH["System Architect"]
    GOV["Community Governor"]
    SPONSOR["Technology Sponsor"]
    OPS["Runtime Operator"]
    COMM["Private Commercial Operator"]
    IND["Community Industry Operator"]
    GATE["Five Metric / Replay / Deadbox / Audit / Human Decision"]

    HOLDER --> OWNER --> GATE
    HOLDER --> ARCH --> GATE
    HOLDER --> GOV --> GATE
    HOLDER --> SPONSOR --> GATE
    HOLDER --> OPS --> GATE
    HOLDER --> COMM --> GATE
    HOLDER --> IND --> GATE
```

## Forbidden Collapse

The system must not collapse these roles into one super-admin. Any role confusion that can affect assets, data, accounting, or production mutation is at least `L2_drift`; asset privatization or governance bypass is `L3_metric_hazard`.
