# W7TP HA Mesh Plan-Only Governance
# W7TP 高可用網格備援治理規格

Status: plan-only / no execution
Scope: Wuchang Smart Cloud / XiaoJ Intent Field / W7TP / EAMTP-7D / Merlin Physical Router Field

## 1. Purpose

This document absorbs the useful parts of legacy HA mesh shell designs into W7TP governance without executing unsafe commands.

Useful concepts:

- LAN IPv4 first, Tailscale/IPv6 backup
- physical + cloud node inventory
- hot memory field and warm disk field
- delta sync concept
- HA node health check
- Merlin router QoS/firewall as plan-only intent
- cron-like scheduling as reviewed task schedule
- multi-node public-service compute fabric

## 2. Canonical Mapping

Legacy concept to W7TP mapping:

1. CLOUD_VMS
   → W7TP_CLOUD_REDACTED_COMPUTE_NODE

2. HYBRID_VMS
   → W7TP_HYBRID_EDGE_NODE

3. LAN IPv4 first
   → preferred_path = lan_ipv4

4. Tailscale / IPv6 fallback
   → fallback_path = tailnet_ipv6

5. RAM_CORE
   → HOT_MEMORY_FIELD

6. HOT_DISK / data_core
   → WARM_STATE_FIELD

7. delta_sync.sh
   → plan-only job manifest / not direct rsync

8. rsync --delete
   → high risk; must be replaced by signed manifest + dry-run + human review

9. ssh-copy-id / root@
   → hardwall; no automatic credential propagation

10. crontab every 15 minutes
   → reviewed schedule proposal only

11. iptables / Merlin firewall-start
   → Merlin Intent Driver plan-only ticket

## 3. Allowed Plan-Only Behaviors

W7TP may:

- maintain redacted node inventory
- classify node path preference
- generate HA job manifest drafts
- generate dry-run sync plans
- classify LAN/Tailscale fallback path
- generate human-review Merlin QoS/firewall checklist
- record result after human action
- create audit reports

## 4. Forbidden Direct Behaviors

W7TP must not directly:

- run sudo
- write /etc/fstab
- mount tmpfs
- run ssh-copy-id
- create root trust paths
- run rsync --delete
- write crontab
- write iptables
- modify Merlin router firmware
- disable firewall
- expose core services to WAN
- copy credentials, keys, tokens, or private keys
- perform automatic cross-node deletion

## 5. HA Mesh Safety Rules

1. Node inventory must be redacted.
2. Raw IP/device identity can be local-only when needed, not cloud.
3. Cloud lanes receive only redacted EAMTP packets.
4. Remote nodes receive minimal signed job manifests, not full Taiji_Hub.
5. No raw PII is sent to cloud or edge nodes.
6. No remote shell automation without explicit human approval.
7. Deletion sync must require human review.
8. Failover must prefer read-only or idempotent jobs.
9. Result packets must be signed/hash-recorded.
10. Dead-letter must catch credential propagation, root trust, and unrestricted WAN exposure.

## 6. Canonical Statement

舊版 HA mesh 腳本的有用部分是「高可用拓撲思想」，
不是可直接執行的自動化命令。

小J / W7TP 可吸收其：
區網優先、暗網備援、節點名冊、hot/warm 記憶場、多節點備援、Merlin 網路場策略。

但不得直接執行：
sudo、ssh-copy-id、root SSH、rsync --delete、crontab、iptables、fstab、Merlin 設定變更。
