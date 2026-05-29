# Five-Metric Formal Notation Runtime Refactor Report

Date: 2026-05-11
Mode: local-governance-refactor-only
Execution boundary: no live deploy, no SSH, no SCP, no service restart, no external API

## Purpose

This report records the Taiji Runtime refactor toward a five-metric formal notation protocol.

The core correction is:

- Natural language is a human interface and explanation layer.
- Runtime transport must prefer structured TensorPacket state.
- Gateway, POS, Voice, LINE, Odoo, Browser Runtime, Replay, Deadbox, and Audit flows must exchange governed YAML/JSON state rather than free-form prompt authority.

## Canonical Symbols

| Symbol | ASCII field | Runtime meaning |
|---|---|---|
| tau | tau | Five-Metric Tensor State |
| pi | pi | Payload |
| omega | omega | Result |
| mu | mu | Runtime Metadata |
| sigma | sigma | Continuity State |
| delta | delta | State Transition |
| lambda | lambda | Route Vector |
| gamma | gamma | Governance Vector |
| rho | rho | Replay Vector |
| kappa | kappa | Cache Vector |
| epsilon | epsilon | Entropy / Usage Cost Vector |
| zeta | zeta | Deadbox State |
| alpha | alpha | Audit Snapshot |

## Generated Or Updated Runtime Assets

The formal notation refactor adds or expects these local-only assets:

- `docs/taiji_five_metric_formal_notation_runtime_zh.md`
- `schemas/formal_tensor_packet.schema.json`
- `Taiji_Governance/runtime/packet/formal_notation_protocol.yaml`
- `Taiji_Governance/runtime/packet/formal_tensor_state_machine.md`
- `Taiji_Governance/runtime/packet/formal_event_flow.md`
- `services/gateway/policies/formal_tensor_validator.py`
- `tests/test_formal_tensor_validator.py`

## Runtime Contract

Every executable runtime operation must be represented as:

```yaml
TensorPacket:
  packet_id: tp_<timestamp>_<hash>
  schema: taiji.formal_tensor_packet.v0.1
  tau:
    I: {}
    R: {}
    T: {}
    A: {}
    P: {}
  pi: {}
  sigma: {}
  lambda: {}
  gamma: {}
  rho: {}
  kappa: {}
  epsilon: {}
  zeta: {}
  alpha: {}
```

No raw natural language command may directly mutate POS, Odoo, Google, payment, deployment, browser admin session, or production databases.

## L3 Metric Hazard Rules

The following are blocked:

- Direct production mutation from natural language.
- Payment execution without human decision.
- Refund, discount override, or manager override without governed runtime.
- Credential, token, service account JSON, OAuth secret, private key, password, or cookie exposure.
- Google/Odoo live API mutation without manifest, Gateway, audit, rollback, and human decision where required.
- Browser admin-session automation that changes high-privilege settings without policy gating.
- Replay of stale shell, deployment, payment, or authority packets.
- Any route that bypasses Five Metric Gate, Taiji Gateway, Replay Governance, Deadbox, or Audit Runtime.

## Validator Expectations

The local validator must:

- Validate required TensorPacket sections.
- Validate tau.I, tau.R, tau.T, tau.A, and tau.P.
- Reject raw plaintext runtime memory.
- Reject secret or credential access.
- Reject payment execution by default.
- Require human decision, audit, and rollback for L2/L3 actions.
- Mark production overwrite, deployment, and credential boundaries as blocked unless a separate governed runtime exists.
- Never call external APIs.
- Never execute deployment commands.

## Verification Status

Local execution could not be completed in this session because the Codex exec launcher returned:

```text
CreateProcess ... No such file or directory (os error 2)
```

No successful syntax check, pytest run, grep scan, or YAML/JSON parse result is claimed in this report.

## Required Verification Commands

Only run these as local read-only or local test commands:

```bash
python3 -m json.tool schemas/formal_tensor_packet.schema.json
python3 -m py_compile services/gateway/policies/formal_tensor_validator.py
PYTHONPATH=. pytest -q tests/test_formal_tensor_validator.py
python3 -c "import yaml; yaml.safe_load(open('Taiji_Governance/runtime/packet/formal_notation_protocol.yaml', encoding='utf-8')); print('yaml ok')"
rg -n --pcre2 '-----BEGIN|private_key\s*[:=]|client_secret\s*[:=]|oauth_token\s*[:=]|api_key\s*[:=]|AIza[0-9A-Za-z_-]{20,}|ya29\.|password\s*[:=]' docs schemas services tests Taiji_Governance/runtime
rg -n --pcre2 'docker compose up|docker compose down|systemctl restart|taiji-guarded-run|--execute|\bssh\b|\bscp\b' docs schemas services tests Taiji_Governance/runtime
```

## Forbidden Commands

Do not run:

```bash
ssh
scp
systemctl restart
docker compose up
docker compose down
taiji-guarded-run
legacy_core/wuchang_tailscale_deployer.py --execute
```

Do not read or print:

- GCP key files
- service account JSON content
- OAuth token
- API key
- private key
- password
- browser session cookie

## Rollback Plan

Because this refactor is local documentation/schema/policy/test work, rollback is file-level:

1. Remove the formal notation documentation file.
2. Remove the formal TensorPacket schema.
3. Remove the formal protocol/state/event-flow files.
4. Remove the local validator and its tests.
5. Restore any governance index references that point to these files.
6. Append a rollback audit record indicating local-only rollback and no runtime deployment.

## Risk Rating

| Area | Rating | Reason |
|---|---|---|
| Runtime operation | L0_exact_match | No live runtime execution is introduced. |
| Local schema/doc change | L1_near | Adds governance structure and validator skeleton only. |
| Verification status | L2_drift | Local commands could not run due exec launcher failure. |
| External exposure | L0_exact_match | No secret access and no external API use. |
| Deployment hazard | L0_exact_match | No SSH/SCP/restart/compose/live execute path is used. |

