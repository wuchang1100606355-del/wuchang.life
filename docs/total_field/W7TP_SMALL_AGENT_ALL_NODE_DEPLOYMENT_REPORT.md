# W7TP Small Agent All-Node Deployment Report

RUN_ID=`W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_V0_1_D27230ABA7A4`

STATE=`HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED`

## Scope and authority

The deterministic candidate release and its controlled deployment tooling were
built and verified. The only formal node source used was:

- `runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json`
- `runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt`

Owner confirmation was present for remote node write, deployment, and a user
service start or restart only when content changed. Router write, database
write, reboot, Canonical write, Pointer write, Runtime Policy write, D3 write,
and Packet Runtime write remained prohibited.

No formal node supplied the complete `hostname`, `address`, `authority`,
`observation_domain`, and `connection_method` record required by the controlled
deployer. The deploy entrypoint therefore stopped before constructing an SSH or
SCP executor. No remote command, installation, service change, or healthcheck
was attempted on a formal node.

## Release

- Version: `v0.1-d27230aba7a4`
- Manifest: `manifests/w7tp_small_agent_release_v0_1_d27230aba7a4/release_manifest.json`
- Release SHA-256: `5d7f220b1716d0d496cd016c962b295b96654faff0fccb96e7c6eadee2cddc2a`
- Runtime Policy SHA-256: `d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960`
- Status: `CANDIDATE_DEPLOYABLE`; this is not a claim of completed production deployment.

The package contains the candidate agent/runtime components, read-only policy
reference, capability schema and template, deterministic fixed vector,
healthcheck, launcher, install manifest, rollback manifest, file hashes, and
uninstall/rollback instructions. It contains no LLM model, production API key,
database credential, member data, or enabled test ADI strategy.

## Package validation

- Python compilation: `PASS`
- Strict JSON parsing: `PASS`
- Release builder replay: `PASS_W7TP_SMALL_AGENT_RELEASE_VERIFIED`
- Focused deployment tests: `30/30 PASS`
- Deployment verifier: `PASS_VERIFY_W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_PACKAGE`
- Raw-secret scan: `PASS`
- Protected-file SHA-256 baselines: `PASS`
- Remote commands executed by verifier: `0`

The fixed-vector package self-test passed D1 projection, candidate replay,
TOTAL_FIELD_PULL and LLM_PUSH test-only ingress, common receive path, ALLOW-only
commit, non-ALLOW preservation of `previous`, persona/governance separation,
D7 reference-only enforcement, and LLM direct-commit blocking. The fixture has
no production Gateway profile, so production TOTAL_FIELD_PULL and LLM_PUSH
remain `HOLD_VECTOR_GATEWAY_PROFILE_NOT_CONFIGURED` and were not presented as
node-level PASS results.

## Formal node results

| node_id | kind | result |
|---|---|---|
| `taiji01` | `linux` | `HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED` |
| `MSI` | `windows` | `HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED` |
| `penguin` | `linux` | `HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED` |
| `localhost` | `iOS` | `HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED` |
| `DESKTOP-OHE05SC` | `linux` | `HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED` |
| `wuchang-us-free-node` | `linux` | `HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED` |
| `V3_MIX_EDLA_GL` | `android` | `HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED` |
| `RT-BE86U-7428` | `ASUSWRT-Merlin router` | `HOLD_ROUTER_WRITE_NOT_AUTHORIZED` |

Totals: 8 formal nodes, 0 eligible, 0 already PASS, 0 installed, 0 restarted,
8 held, including 1 Router held by policy.

## Owner-provided context not promoted to the formal node registry

During execution, the owner described `taiji01` as a VPN server and `penguin`
as a customer display whose external screen shows AI imagery. The owner also
described a SUNMI POS service-person interface and `taiji03` as the responsible
controller. These statements are preserved as non-canonical context only:

- They do not establish `authority`, `observation_domain`, or
  `connection_method` for `taiji01` or `penguin`.
- The exact mapping from the SUNMI POS description to an Active node ID is not
  formally established.
- `taiji03` is not present in the eight-node Active list used for this run and
  was not added, contacted, or deployed.

## Deployment and equivalence status

The authorized deploy command was invoked after package tests and verifier
PASS. It returned `HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED` before any formal
node connection. Consequently, node healthchecks and cross-node canonical TFS,
TFID, and Total Field Hash comparison were not run. The consensus boundary
remains `LOCAL_EQUIVALENCE_ONLY`; distributed consensus remains an Open Problem.

Rollback assets and test-only rollback behavior are verified and ready, but no
node rollback was necessary because no installation began.

## Protected state

`ACTIVE_CANONICAL_WRITE=NO`, `POINTER_WRITE=NO`,
`RUNTIME_POLICY_WRITE=NO`, `D3_WRITE=NO`, `PACKET_RUNTIME_WRITE=NO`,
`DB_WRITE=NO`, `ROUTER_WRITE=NO`, `REBOOT=NO`.

## Next gate

An independently authorized formal-node registration process must establish
the exact Active node ID, hostname/address, deployment authority, Observation
Domain reference, and existing connection method for each intended target.
Only after that formal evidence exists may this same release be replay-verified
and deployed to eligible nodes. No value may be inferred from the descriptive
owner context above.
