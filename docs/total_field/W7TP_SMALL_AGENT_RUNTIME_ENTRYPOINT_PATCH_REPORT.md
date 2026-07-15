# W7TP Small Agent Runtime Entrypoint Patch Report

## Execution identity

- RUN_ID: `W7TP_SMALL_AGENT_RUNTIME_ENTRYPOINT_PATCH_V0_1_1`
- Deployment continuation: `W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_V0_1_D27230ABA7A4`
- Owner confirmation: `YES`
- Owner authority scope: `W7TP_SMALL_AGENT_INSTALL_V0_1_ONLY`
- Report status: `PARTIAL_PASS_W7TP_SMALL_AGENT_DEPLOYED_WITH_HELD_NODES`

## Original HOLD and bounded resolution

The previous Release `v0.1-d27230aba7a4` had no executable runtime entrypoint, so deployment stopped before node writes with `HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING`. The previous Release remains byte-for-byte unchanged. This patch creates a separate immutable Release and does not promote it to Active Canonical.

The executable resolves its Release root from its own path and does not require the caller's working directory or `PYTHONPATH`. It packages the existing candidate engine; it does not create a second engine. Generative transport remains a protocol-native 8D intent-field packet flow based on references, reconstruction conditions, equivalent-state generation, and Total Field verification.

## Runtime entrypoint

Entrypoint: `bin/w7tp-small-agent`

Supported commands:

- `version`: emits the fixed agent, Release, Policy, and schema identity.
- `health`: verifies immutable files, Policy, imports, capability manifest, 8D-GTE parser, Total Field gateway, ALLOW-only commit guard, and disabled production ADI.
- `self-test`: runs the fixed D1, replay, source-mode, adjudication, persona separation, direct-commit blocking, and raw-secret vectors.
- `capabilities`: emits the non-secret capability manifest.
- `receive-candidate`: accepts one closed UTF-8 JSON envelope and routes it through schema validation, the shared Total Field gateway, D8, and the ALLOW-only commit guard.
- `service-run`: runs in the foreground, reaches `IDLE_READY`, opens no external listening port, performs no real LLM call, and exits normally on SIGTERM or SIGINT.

Service mode is user-level systemd. `ExecStart` resolves to `%h/.local/share/w7tp-small-agent/current/bin/w7tp-small-agent service-run`. No root service, `/etc` write, firewall change, or new network listener is used.

## Immutable Release

- Old Release version: `v0.1-d27230aba7a4`
- Old Release identity: `5d7f220b1716d0d496cd016c962b295b96654faff0fccb96e7c6eadee2cddc2a`
- Old Release tree baseline: `2f5a47fbee773d70c94dc4f90f64c040866639f29b43eedf5c2cd57c9c2a1312`
- Old Release unchanged: `YES`
- New Release version: `v0.1.1-d27230aba7a4`
- New Release identity: `9c836304a49c10a9443264000784010804535789c916d1ae9d6c8c11443f06b6`
- Policy identity: `d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960`
- Entrypoint mode: executable (`0755` at build)
- Packaged Policy mode: read-only (`0444` at build)

The deterministic builder reproduced the same Release identity. The Release identity contains no time, process ID, random value, UUID, or local build path.

## Validation

- Python compilation: `PASS` for the five implementation files, focused test, and verifier.
- Focused suite: `30/30 PASS`.
- Runtime entrypoint verifier: `PASS_VERIFY_W7TP_SMALL_AGENT_RUNTIME_ENTRYPOINT`.
- Direct `version`: `PASS`.
- Direct `health`: `PASS_W7TP_SMALL_AGENT_HEALTH`.
- Direct `self-test`: `PASS_W7TP_SMALL_AGENT_SELF_TEST`.
- Authority registry SHA-256: unchanged (`753bd1e693caefc83a21815a1fce431347eba2d2f31b0e5df808c62fb18060c9`).
- Active Canonical, Pointer, D3 engine, and packet runtime protected hashes: unchanged.
- Raw-secret scan: `PASS`.

## Deployment replay

The authority registry continued to identify two eligible nodes: `taiji01` and `penguin`. No other node was added.

### taiji01

The first local installation exposed a deployment-layer conflict: an installer-only `.release_sha256` marker was written inside the closed immutable Release inventory. Runtime health correctly rejected the extra file. The deployment tool was minimally corrected to keep the installed Release identical to the package, a focused installed-health regression assertion was added, and all 30 tests plus the verifier passed again. The marker created by this failed attempt was removed, and the changed user service was restarted under the explicit owner authorization.

Final replay result: `RELEASE_ALREADY_INSTALLED_AND_HEALTHY` (`ALREADY_PASS`).

- Agent process: `PASS`
- Entrypoint and version: `PASS`
- Capability manifest: `PASS`
- Release and Policy identities: `PASS`
- Health and self-test: `PASS`
- D1 projection: `PASS`
- Candidate replay: `PASS`
- `TOTAL_FIELD_PULL`: `PASS`
- `LLM_PUSH`: `PASS`
- Common receive path: `PASS`
- ALLOW-only commit: `PASS`
- Persona/governance separation: `PASS`
- LLM direct commit: `BLOCKED`
- Raw-secret scan: `PASS`
- Service health: `PASS`

The first failure had no previous Release link, so rollback was not available. Recovery retained only the verified v0.1.1 Release and produced a healthy user service.

### penguin

Both the deployment attempt and the single permitted replay were stopped before transfer because the formal SSH transport returned exit code `255`. Final reason code: `HOLD_DEPLOYMENT_COMMAND_FAILED`. No Release transfer, service change, or remote write completed, so rollback was not required. No further retry was made.

### Other formal nodes

- `MSI`: `HOLD_AMBIGUOUS_VERIFIED_ADDRESS`
- `localhost`: `HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT`
- `DESKTOP-OHE05SC`: `HOLD_AMBIGUOUS_VERIFIED_ADDRESS`
- `wuchang-us-free-node`: `HOLD_NODE_UNREACHABLE`
- `V3_MIX_EDLA_GL`: `HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT`
- `RT-BE86U-7428`: `HOLD_ROUTER_WRITE_NOT_AUTHORIZED`

These nodes were not deployed. Router write remained prohibited.

## Cross-node equivalence

`CROSS_NODE_EQUIVALENCE=NOT_RUN_INSUFFICIENT_PASS_NODES`. Only `taiji01` reached the full PASS state, so no cross-node equality or distributed-consensus claim is made.

## Protected boundaries

- Active Canonical write: `NO`
- Pointer write: `NO`
- Database write: `NO`
- Router write: `NO`
- Reboot: `NO`
- Root systemd write: `NO`
- Firewall or DNS write: `NO`

## Next action

Restore the already-authorized formal SSH transport to `penguin`, then open a separate deployment replay limited to that held node. Do not rebuild either Release or expand the authority scope.

## Penguin SSH recovery attempt

- Target node: `penguin`
- SSH alias: `penguin`
- Resolved SSH Host: `penguin`
- Resolved SSH User: `taiji_admin`
- Resolved SSH Port: `22`
- `ssh -G penguin`: `PASS`
- Authority registry address: `100.111.139.7`
- Tailscale exact hostname match: `penguin`
- Tailscale address match: `PASS`
- Tailscale online evidence: `true`
- Authority registry modified: `NO`
- Bounded connection-test exit code: `255`
- Masked stderr summary: `***@penguin: Permission denied (publickey,password).`
- Stable failure reason: `HOLD_PENGUIN_SSH_AUTHORITY_OR_KEY_UNAVAILABLE`
- SSH channel repaired: `NO`
- Node installation performed: `NO`
- Service restart performed: `NO`
- Health/self-test/capabilities: `NOT_RUN_SSH_CHANNEL_HELD`
- Cross-node equivalence: `NOT_RUN_INSUFFICIENT_PASS_NODES`
- Consensus mode: `LOCAL_EQUIVALENCE_ONLY`
- Rollback status: `NOT_REQUIRED_NO_REMOTE_WRITE`

The formal node and address evidence are consistent. The failure is confined to non-interactive SSH authentication; it is not an alias, reachability, service-port, or host-key-verification failure. No SSH configuration, key, known-hosts entry, Release, registry, taiji01 service, or other node was changed. Deployment did not begin because the authenticated SSH channel was unavailable.

### Penguin SSH recovery recheck

The bounded recovery check was repeated without changing configuration. `ssh -G penguin` again resolved Host `penguin`, User `taiji_admin`, and Port `22`; Tailscale again provided one exact, online `penguin` match whose address equals the authority registry. The required BatchMode connection test again exited `255` with masked stderr `***@penguin: Permission denied (publickey,password).`

- Stable failure reason: `HOLD_PENGUIN_SSH_AUTHORITY_OR_KEY_UNAVAILABLE`
- Authority registry modified: `NO`
- SSH channel repaired: `NO`
- Node installation performed: `NO`
- Service restart performed: `NO`
- Health/self-test/capabilities: `NOT_RUN_SSH_CHANNEL_HELD`
- Cross-node equivalence: `NOT_RUN_INSUFFICIENT_PASS_NODES`
- Rollback status: `NOT_REQUIRED_NO_REMOTE_WRITE`

No deployment retry was started because authenticated SSH remained unavailable. No taiji01, other-node, Release, SSH configuration, key, known-hosts, Canonical, Pointer, database, or Router write occurred.

## Penguin authenticated deployment completion

The owner confirmed `taiji_02` as the formal penguin SSH user. The bounded BatchMode check returned `PENGUIN_SSH_PASS`. Only the penguin authority record was updated with `ssh_user=taiji_02`, `connection_method=SSH`, `deployment_eligibility=true`, and `reason_code=READY_FOR_DEPLOYMENT`. Owner authority and authority scope were preserved.

The existing deployer was minimally extended to consume the validated SSH user and to support `--node-id penguin`; this prevented any taiji01 or other-node deployment action. The fixed Release `v0.1.1-d27230aba7a4` was not rebuilt or changed.

The first authenticated deployment installed and activated the versioned Release, then held at remote health because penguin's Python 3.13 user environment lacked `jsonschema`. No previous Release target existed for rollback. Fixed versions `jsonschema==4.10.3` and `pyrsistent==0.20.0`, matching the validated runtime environment, were installed only in the `taiji_02` user site without sudo or root. Remote health and self-test then passed, the changed user service was restarted, and the single permitted deployment retry returned `RELEASE_ALREADY_INSTALLED_AND_HEALTHY`.

- SSH channel: `PASS`
- Registry modification: `PENGUIN_ONLY`
- Node installed: `YES`
- Node restarted: `YES`
- Entrypoint/version: `PASS`
- Release SHA-256: `MATCH`
- Policy SHA-256: `MATCH`
- Health: `PASS_W7TP_SMALL_AGENT_HEALTH`
- Self-test: `PASS_W7TP_SMALL_AGENT_SELF_TEST`
- Capability manifest: `PASS`
- D1 projection: `PASS`
- Candidate replay: `PASS`
- `TOTAL_FIELD_PULL`: `PASS`
- `LLM_PUSH`: `PASS`
- Common receive path: `PASS`
- ALLOW-only commit: `PASS`
- HOLD/BLOCK/QUARANTINE preserve previous: `PASS`
- Persona/governance separation: `PASS`
- LLM direct commit: `BLOCKED`
- Raw-secret scan: `PASS`
- Service health: `PASS`
- Final deployment result: `ALREADY_PASS`
- Rollback status: `NOT_AVAILABLE_NO_PREVIOUS_RELEASE_THEN_RECOVERED`

### taiji01/penguin local equivalence

Both nodes evaluated the same packaged fixed vector through the existing runtime path.

- Canonical TFS: `{"coordinate":{"x":2,"y":3}}`
- Canonical TFS SHA-256: `8e90dda4f223a6ceec407f1ed8687e36d18bcca449ccc0e4414e2120b949ae74`
- TFID: `tfid:test:w7tp-small-agent:allow`
- Total Field Hash: `d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960`
- Cross-node equivalence: `MATCH`
- Difference paths: `[]`
- Consensus mode: `LOCAL_EQUIVALENCE_ONLY`
- Distributed consensus: `OPEN_PROBLEM`

No taiji01 write or restart occurred. Active Canonical, Pointer, database, Router, SSH configuration, SSH keys, and known-hosts entries were not modified.
