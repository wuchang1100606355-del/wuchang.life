---
name: w7tp-8d-adi-adaptive-network
description: Observe and resolve per-intent W7TP network bindings across local, LAN, Tailscale, qualified IPv6, guest-service, IoT, and WAN-publication zones. Use when a task needs concurrent path sets, zone-aware service resolution, binding-local failover, drift diagnosis, or auditable candidate healing without granting router, publication, or D8 authority.
---

# W7TP 8D ADI Adaptive Network

Build one coupled network state field, then make independent intent-scoped path bindings. Multiple legal paths and bindings may coexist. Do not reduce the result to host online/offline, a host-global three-way selector, or let an address, route, score, ping, DNS answer, or Tailscale peer state decide alone.

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
- D5 Policy: `MULTI_PATH_CONCURRENT_FIELD`; qualify `AVAILABLE_PATH_SET`, `QUALIFIED_PATH_SET`, `ACTIVE_PATH_SET`, `DENIED_PATH_SET`, and `STALE_PATH_SET` per intent. Any fallback order is local to one binding.
- D6 Reconstruction: reconstruct target-native service reachability, not only packet arrival.
- D7 Risk: drift, stale identity/address, binding, tunnel, DNS, route, asymmetric return, collision, and namespace risks.
- D8 Decision: selection is phase one only. Phase two must bind source, source zone, interface, route, target, target zone, service, application, and verified response before `D8_ALLOW_FOR_THIS_INTENT`; otherwise that binding is `HOLD`, `DENY`, or `LOCALIZED_UNKNOWN`.

Closure requires an intent, non-conflicting target identity, current route evidence, service-level probe, applicable policy, reconstruction result, and reviewed risks. Missing closure fails closed.

## Workflow

1. Reconfirm node, repository, branch, HEAD, tree, worktree, and current intent before discovery.
2. Reuse current evidence when it is fresh and scope-matched. Historical IPs, hashes, receipts, and reports are evidence only.
3. Run local discovery. Keep host, WSL, container, LAN, Tailscale, and native IPv6 observations separate.
4. Use the Merlin adapter only through an existing strict SSH alias. It runs a fixed allowlist of read-only commands and selected `nvram get` calls; it never dumps NVRAM.
5. Resolve identities without treating an IP as a permanent node identity. Preserve duplicates or contradictions as conflicts.
6. Probe the requested service with more than ICMP: route lookup plus TCP, HTTP(S), SSH banner, application health, DNS, or Tailscale ping as applicable.
7. Qualify every AAAA answer separately against all eight gates: address, default route, source selection, next hop, target, TCP service, return path, and formally TLS-verified application response. Never create a global IPv6 pass.
8. Score candidates for comparison, then apply only the current intent's zone policy and path preference. Score and another intent's result have no authority.
9. Verify the selected chain: source -> source zone -> interface -> route -> target -> target zone -> service -> application -> response. Evidence past `expires_at` is stale and not selectable.
10. Write candidate evidence with the common envelope and a hash manifest. Never label it Canonical or Total Field PASS.

## Path and zone model

- Path records require a stable `path_id`; multiple `NATIVE_IPV6` or other same-type candidates may coexist.
- Applications call `resolve_service(intent_id, source_node, target_node, service_identity, ...)` and do not choose LAN, Tailscale, IPv6, guest, IoT, or WAN carriers directly.
- `GUEST_SERVICE_PATH`, `IOT_SERVICE_PATH`, and `WAN_PUBLICATION_PATH` are service-zone paths, never host-global fallback paths.
- External users originate in `ZONE_WAN` and may target only `ZONE_FUTURE_PUBLIC_SERVICE` through an explicit `WAN_PUBLICATION_PATH`. They do not directly reach core, management, IoT, database, Total Field, SSH, or router administration.
- `selected_path`, `alternate_paths`, and `concurrent_paths` are represented independently. This candidate does not implement bonding or packet duplication.
- Failover evaluates one binding at a time. A `HOLD` or failure for one intent never disables otherwise qualified paths for another intent.

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
  --source-zone ZONE_MANAGEMENT \
  --target-zone ZONE_MANAGEMENT \
  --ipv6-host example.com \
  --ipv6-port 443 \
  --probe-external-ipv6
```

Validate deterministic behavior without network access:

```bash
python3 capabilities/w7tp-8d-adi-adaptive-network/tests/run_tests.py
```

## Healing boundary

First-stage healing may only propose or perform a task-authorized refresh observation, refresh DNS state, refresh peer state, re-probe an alternate path, switch one application binding's candidate path, or restart this skill's own observer. The rollback guard rejects global IPv6 disable, route deletion, firewall flush, Tailscale reset, router/service restart, WAN/DHCP/DNS mutation, public-service activation, or host reboot.

Read `schemas/network_state.schema.json` when validating output contracts. Read `manifest.json` when reviewing provenance, reused components, files, and authority limits.

## System-level runtime binding (v0.2.0-candidate.1)

The owner is W7TP 8D ADI at Taiji Hub system scope. XiaoJ is eligible only as a consumer. The minimal adapter at `scripts/network_runtime.py` verifies manifest source hashes and exposes a local Unix socket runtime API. The observer retains only fresh local evidence, clears decisions before every refresh and fails closed during recovery. The read-only Native ADI health consumer uses `resolve_service`. This limited local binding cannot establish multi-carrier failover; do not label it ACTIVE until real alternate-path and Total Field runtime gates pass. Port 9002 is an edge gateway and is not D8.

MSI observes two real source interfaces against the existing read-only Native ADI health endpoint using already authorized SSH transport. MSI submits bounded TTL evidence over authenticated SSH; the system-level observer resolves its independent intent and fails closed when MSI evidence expires. A one-cycle MSI LAN probe suppression tests only the application binding; it never disables a network interface or router.
