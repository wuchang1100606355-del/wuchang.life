# Node To Storage Topology

版本：2026-05-11

## Primary Nodes

| Node | Role |
|---|---|
| `taiji_01@taiji01` | primary system node |
| `taiji_admin@MSI:~/Taiji_Hub` | responsible officer workstation |

## Storage Boundaries

| Storage | Role |
|---|---|
| `/home/taiji_admin/Taiji_Hub` | Linux native development/runtime workspace |
| `/mnt/c/Users/o0930/Taiji_Data` | C drive frequently read/write scenario data |
| `/mnt/d/Taiji_Hub_Archive` | D drive high-authority special-purpose reviewed archive |
| `/home/taiji_admin/Taiji_Hub_Org_Readonly_Cloud_Staging` | organization cloud readonly staging |

## Rule

`taiji_admin@MSI` may prepare, test, package, hash, and review.

`taiji_01@taiji01` is the primary governed runtime target.

No node may bypass:

- Taiji Gateway
- Five Metric Gate
- Audit Runtime
- Rollback plan
- Human Decision Boundary where required

