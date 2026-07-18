# W7TP Wi-Fi SUNMI and HomePad Inventory Report

RUN_ID=`WIFI_SUNMI_HOMEPAD_FIELD_INVENTORY_AND_CONTAINER_PROFILE_V0_1`

STATE=`HOLD_DEVICE_IDENTITY_MAPPING_UNRESOLVED`

## Read-only evidence

The current local subnet is `192.168.50.0/24` on `enp1s0`. `ip neigh show`
returned 10 IPv4 neighbours with MAC evidence. `nmap` and a Router client-list
reader were not available, so no active discovery or Router access was used.
The safe-field projection of `tailscale status --json` returned 12 devices,
including the local node. ADB was installed, but `adb devices -l` returned no
authorized device.

The LAN observation at `192.168.50.176` used MAC prefix `74:F7:F6`. The local
IEEE OUI database identifies that prefix as Shanghai Sunmi Technology Co.,Ltd.
Owner correction maps `V3_MIX_EDLA_GL` to the SUNMI POS and fixes its platform
as Android 13. The observed Tailnet address is `100.98.69.115`; the last safe
snapshot reported it offline. The manufacturer OUI and Owner mapping establish
the candidate identity, but model, authorized ADB evidence, container runtime,
and a formal deployment transport remain unavailable. The record therefore
remains deployment-ineligible.

Owner correction identifies `drallion` as ChromeOS. Tailscale reports Android,
which is preserved only as a possible ChromeOS Android/ARC layer observation.
It is explicitly excluded from the SUNMI role and is not assigned to either
HomePad without a separate direct role binding.

## Target result

- `SUNMI_POS`: `V3_MIX_EDLA_GL`, Android 13, Google commercial voice
  authorization confirmed, containerization supported. Status:
  `HOLD_NODE_OFFLINE_AND_DEPLOYMENT_TRANSPORT_UNAVAILABLE`.
- `HOME_PAD_1`: no exact manufacturer/model/address binding. Status:
  `HOLD_HOMEPAD_IDENTITY_UNRESOLVED`.
- `HOME_PAD_2`: kept as a separate record with no exact binding. Status:
  `HOLD_HOMEPAD_IDENTITY_UNRESOLVED`.
- `taiji01`: explicitly excluded and never treated as a target.

## SUNMI voice and container candidate

Owner statements are recorded only as
`SUNMI_GOOGLE_COMMERCIAL_VOICE_LICENSE=OWNER_CONFIRMED` and containerization
capability confirmed. The license reference is opaque. No ADC JSON, OAuth
token, API key, password, Google credential, or member plaintext was read,
copied, or packaged.

No authorized ADB device was available to verify Docker, Podman, containerd,
nerdctl, runc, CPU ABI, SELinux state, or storage. The resulting status is
`OWNER_CONFIRMED_RUNTIME_EVIDENCE_PENDING`. The candidate is non-root, has no
default network listener, embeds no credential, and requires Total Field
Gateway adjudication. D7 voice references produce a candidate only; formal
playback requires D8 ALLOW.

## Protected boundaries

REMOTE_WRITE=NO

DEPLOY=NO

RESTART=NO

DB_WRITE=NO

ROUTER_WRITE=NO

ACTIVE_CANONICAL_WRITE=NO

POINTER_WRITE=NO

No installation, container creation, service action, network route change,
firewall change, DNS change, Canonical change, Pointer change, DB write, or
Router write was performed.
