---
name: w7tp-8d-adi-adaptive-network
description: Observe and evaluate W7TP network paths across local LAN, Tailscale, containers, WSL, Merlin routers, and explicitly qualified IPv6. Use when a task needs identity-aware path selection, service-level reachability, drift diagnosis, fail-closed route decisions, or auditable candidate healing without granting router or D8 authority.
---

# W7TP 8D ADI Adaptive Network

Build one coupled network state field, then make an intent-scoped candidate path decision. Do not reduce the result to host online/offline or let an address, route, score, ping, DNS answer, or Tailscale peer state decide alone.

## Authority boundary

- Default to read-only observation and candidate evidence.
- This skill has no Founder, Canonical, router, firewall, service, or D8 authority.
- `score != authority`, `reachable != service healthy`, and `candidate decision != Total Field decision`.
- Learning may append candidate history and evidence only. It must not rewrite Founder Authority, Canonical, or D8 authority.
- Never mutate WAN, DHCP, DNS, IPv6, firewall, policy routes, port forwarding, NVRAM, JFFS, Tailscale, or a service unless the current task grants that exact effect and a rollback preimage exists.

## Joint 8D state contract

Keep these as coupled projections in one `NETWORK_STATE_FIELD`; the Python modules are physical implementation boundaries, not eight independent services.

- D1 Intent: source node, target node, service, and whether crossing networks is necessary.
- D2 State / identity binding: within this network task projection, bind node, host, machine, Tailscale, MAC, address, service, role, and owner observations. Identity remains an envelope prerequisite and is not redefined as canonical D2. Conflicts stay `CONFLICT`.
- D3 Current Field: host, WSL, container, LAN, Tailscale, native IPv6, interface, route, DNS, neighbor, listener, process, and namespace observations.
- D4 Evidence: timestamped raw-result summaries and hashes. No single probe creates authority.
- D5 Policy: `LAN_IPV4` -> `TAILSCALE_IPV4` -> explicitly qualified IPv6 -> `HOLD`.
- D6 Reconstruction: reconstruct target-native service reachability, not only packet arrival.
- D7 Risk: drift, stale identity/address, binding, tunnel, DNS, route, asymmetric return, collision, and namespace risks.
- D8 Decision: only `ALLOW_LAN_IPV4`, `ALLOW_TAILSCALE_IPV4`, `ALLOW_QUALIFIED_IPV6`, `HOLD`, `DENY`, or `LOCALIZED_UNKNOWN`.

Closure requires an intent, non-conflicting target identity, current route evidence, service-level probe, applicable policy, reconstruction result, and reviewed risks. Missing closure fails closed.

## Workflow

1. Reconfirm node, repository, branch, HEAD, tree, worktree, and current intent before discovery.
2. Reuse current evidence when it is fresh and scope-matched. Historical IPs, hashes, receipts, and reports are evidence only.
3. Run local discovery. Keep host, WSL, container, LAN, Tailscale, and native IPv6 observations separate.
4. Use the Merlin adapter only through an existing strict SSH alias. It runs a fixed allowlist of read-only commands and selected `nvram get` calls; it never dumps NVRAM.
5. Resolve identities without treating an IP as a permanent node identity. Preserve duplicates or contradictions as conflicts.
6. Probe the requested service with more than ICMP: route lookup plus TCP, HTTP(S), SSH banner, application health, DNS, or Tailscale ping as applicable.
7. Qualify each IPv6 path against all eight gates: address, default route, source selection, next hop, target, TCP service, return path, and application response.
8. Score candidates for comparison, then apply the fixed priority policy independently of score.
9. Verify the selected chain: source -> interface -> route -> target -> service -> application -> response.
10. Write candidate evidence with the common envelope and a hash manifest. Never label it Canonical or Total Field PASS.

## Existing capability reuse

Use these sources when available instead of rebuilding their bounded functions:

- `configs/merlin/router_inventory_redacted.template.json` and `tools/merlin_inventory_validator.py` for redacted Merlin inventory rules.
- `docs/governance/W7TP_HA_MESH_PLAN_ONLY.md` and `configs/w7tp/ha_mesh_inventory.template.json` for LAN-first, plan-only mesh boundaries.
- `scripts/tailscale_mesh_probe.sh` as historical probe evidence only; its recommendations do not create a current route decision.
- Router `/jffs/scripts/w7tp-8dadi-link-sensor.sh status` and capability snapshot `status`, when present, as D4 evidence only. Carrier-up does not prove service reachability.

## Commands

Run current discovery only when the task authorizes live probes:

```bash
python3 capabilities/w7tp-8d-adi-adaptive-network/scripts/network_skill.py discover \
  --output-dir runtime/network \
  --router-alias asus-router \
  --intent-id OBSERVE_MERLIN_ROUTER \
  --ipv6-host example.com \
  --ipv6-port 443 \
  --probe-external-ipv6
```

Validate deterministic behavior without network access:

```bash
python3 capabilities/w7tp-8d-adi-adaptive-network/tests/run_tests.py
```

## Healing boundary

First-stage healing may only propose or perform a task-authorized refresh observation, refresh DNS state, refresh peer state, re-probe an alternate path, switch an application candidate path, or restart this skill's own observer. The rollback guard rejects global IPv6 disable, route deletion, firewall flush, Tailscale reset, router/service restart, WAN/DHCP/DNS mutation, or host reboot.

Read `schemas/network_state.schema.json` when validating output contracts. Read `manifest.json` when reviewing provenance, reused components, files, and authority limits.
