# W7TP Small Agent Node Authority and Deployment Replay Report

RUN_ID=`W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_V0_1_D27230ABA7A4`

STATE=`HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING`

## Authority registration

The owner grant was registered at
`manifests/w7tp_small_agent_node_authority_v0_1/node_authority_registry.json`.
For every non-Router formal node it records
`authority=OWNER_AUTHORIZED` and
`authority_scope=W7TP_SMALL_AGENT_INSTALL_V0_1_ONLY`. The scope does not grant
database, Canonical, Pointer, firewall, Router, reboot, or any unrelated system
authority. The Router remains unconditionally ineligible.

The registry contains exactly the eight nodes in the Active TRUE8D node list.
`taiji03` and `商米 POS` are recorded separately as
`NOT_IN_ACTIVE_CANONICAL`; neither is a registry node or deployment target.

## Narrow evidence resolution

Only the permitted sources and commands were used: Active TRUE8D Canonical and
Pointer, `hostname`, `hostnamectl`, `tailscale status --json`, and `ssh -G` for
the fixed node names. No network-range scan or secret/configuration-content
dump was performed.

- `taiji01`: local hostname and hostnamectl evidence both matched exactly;
  Tailscale Self also matched. Registered as `LOCAL_SHELL`, eligible.
- `penguin`: one exact Online Tailscale match plus parsed `ssh -G` evidence.
  Registered as `SSH`, eligible.
- `MSI`: two exact Online Tailscale records made the address ambiguous; held.
- `localhost`: evidence identified an independent iOS peer, not the taiji01
  physical host. It is not an alias and has no supported deployment transport.
- `DESKTOP-OHE05SC`: two exact but offline records; address remains ambiguous.
- `wuchang-us-free-node`: exact record was offline; held unreachable.
- `V3_MIX_EDLA_GL`: Android has no established supported deployment transport.
- `RT-BE86U-7428`: held by `ROUTER_WRITE=NO` without any Router mutation.

Unique physical node count is 8 and aliases deduplicated is 0. The registry
resolver recomputes eligibility from evidence and does not trust the boolean
field alone.

## Focused validation

- Authority/deployer focused tests: `15/15 PASS`
- Authority verifier: `PASS_VERIFY_W7TP_SMALL_AGENT_NODE_AUTHORITY`
- Formal nodes: 8
- Eligible nodes before Release preflight: 2
- Router nodes held: 1
- Raw-secret scan over the new authority artifacts: `PASS`
- Existing 30-case package suite: deliberately not rerun
- Existing Release: not rebuilt or modified

Tests used temporary registries and Fake executors. They covered exact node
membership, no extra node, local identity, alias deduplication, exact Tailscale
evidence, parsed `ssh -G` evidence, unknown address/method rejection, Router
boundary, owner scope, no database or protected-file writes, per-node failure
isolation, already-PASS behavior, and stable reason codes.

## Deployment replay

The authorized deploy command was invoked with the existing immutable Release:

- Release version: `v0.1-d27230aba7a4`
- Release SHA-256:
  `5d7f220b1716d0d496cd016c962b295b96654faff0fccb96e7c6eadee2cddc2a`
- Policy SHA-256:
  `d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960`

The Release does not contain the executable path referenced by its user-level
systemd service contract: `bin/w7tp-small-agent`. The updated deployer checks
this immutable entrypoint before any local directory creation, executor
command, SSH/SCP operation, version switch, or service action.

Consequently both otherwise eligible nodes, `taiji01` and `penguin`, returned
`HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING`. No node was installed, restarted,
or modified. No rollback was required because no deployment mutation began.

## Final node results

| node_id | eligibility | deployment result |
|---|---:|---|
| `taiji01` | true | `HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING` |
| `MSI` | false | `HOLD_AMBIGUOUS_VERIFIED_ADDRESS` |
| `penguin` | true | `HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING` |
| `localhost` | false | `HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT` |
| `DESKTOP-OHE05SC` | false | `HOLD_AMBIGUOUS_VERIFIED_ADDRESS` |
| `wuchang-us-free-node` | false | `HOLD_NODE_UNREACHABLE` |
| `V3_MIX_EDLA_GL` | false | `HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT` |
| `RT-BE86U-7428` | false | `HOLD_ROUTER_WRITE_NOT_AUTHORIZED` |

## Runtime validation status

Because no node installation began, node-level `AGENT_PROCESS`, capability
manifest, Policy SHA, D1 projection, candidate replay, TOTAL_FIELD_PULL,
LLM_PUSH, common receive path, ALLOW-only commit, persona separation, direct
commit blocking, service health, and cross-node equivalence were not run. No
package-only fixture result is substituted for a node-level result.

`ACTIVE_CANONICAL_WRITE=NO`, `POINTER_WRITE=NO`, `DB_WRITE=NO`,
`ROUTER_WRITE=NO`, `REBOOT=NO`, `DEPLOY=NO_NODE_MUTATION`, `RESTART=NO`.

## Next gate

A separately authorized Release revision must include a deterministic,
executable `bin/w7tp-small-agent` whose service behavior and healthcheck are
covered by focused tests and hashes. After that Release receives its own
version and SHA-256, replay this unchanged authority registry; do not mutate the
locked Release used in this run.
