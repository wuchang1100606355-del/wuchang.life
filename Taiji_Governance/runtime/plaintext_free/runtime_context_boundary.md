# Runtime Context Boundary

| Boundary | Allowed | Blocked |
| --- | --- | --- |
| L0 read-only | metadata, hashes, file paths | secret content |
| L1 draft | redacted summaries, manifests | raw customer private data |
| L2 guarded | human-confirmed packet references | payment execution |
| L3 blocked | redacted audit only | production mutation, credential issuance |

All context crossing a boundary must be represented by a TensorPacket.
