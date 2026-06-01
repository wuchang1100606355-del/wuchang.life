# Execution Boundary Policy

| Boundary | Status |
| --- | --- |
| A0 read-only | allowed |
| A1 design/documentation | allowed with audit when persistent |
| A2 local patch | allowed with tests and rollback |
| A3 local preflight | allowed, no live deploy |
| A4 deployment preparation | manifest only |
| A5 live operation | disabled |

Any direct crossing into A5 is `L3_metric_hazard`.
