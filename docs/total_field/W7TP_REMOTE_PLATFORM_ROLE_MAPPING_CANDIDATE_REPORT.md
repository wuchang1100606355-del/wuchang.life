# W7TP Remote Platform and Role Mapping Candidate Report

STATE=`PASS_REMOTE_PLATFORM_ROLE_MAPPING_CANDIDATE_UPDATED`

## Scope

This candidate update records only two remote platform/role mappings. It does
not rescan the network, contact a remote node, or modify the formal Active node
set. `taiji01` is outside the mapping scope and its authority node record is
unchanged.

## V3_MIX_EDLA_GL

- node role: `SUNMI_POS`
- physical platform: `ANDROID_13`
- voice capability: `GOOGLE_COMMERCIAL_VOICE_AUTHORIZED`
- containerization: `SUPPORTED`
- container transport: Android-compatible container or an existing formal
  application channel only
- Linux systemd Release: not supported
- current connectivity: offline
- deployment eligibility: false
- hold reason: `HOLD_NODE_OFFLINE`

The voice authorization is capability metadata only. No credential, key, or
token is present. Any future credential binding must use an opaque reference.

## drallion

- node role: `CHROMEOS_NODE`
- physical platform: `CHROMEOS`
- observed Tailscale variant: `ANDROID_ARC_CLIENT_VISIBLE_TO_TAILSCALE`
- container transport: `CHROMEOS_CROSTINI_OR_EXISTING_CONTAINER_ONLY`
- formal status: `NONFORMAL_MAPPING`
- current connectivity: offline
- deployment eligibility: false
- hold reason: `HOLD_NODE_OFFLINE`

The Tailscale Android value is treated only as the visible ARC client layer;
it is not treated as the physical device OS and does not map drallion to SUNMI.

## Protected boundaries

- `TAIJI01_WRITE=NO`
- `ACTIVE_CANONICAL_WRITE=NO`
- `POINTER_WRITE=NO`
- `DB_WRITE=NO`
- `ROUTER_WRITE=NO`
- `DEPLOY=NO`
- `RESTART=NO`

The candidate schema permits optional platform/role metadata. The detailed
drallion mapping remains outside `formal_node_ids` and the formal `nodes` list.
