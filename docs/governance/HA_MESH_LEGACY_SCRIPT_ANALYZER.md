# HA Mesh Legacy Script Analyzer
# 舊版 HA Mesh 腳本安全分析器

Status: analyzer only
Scope: Legacy bash script to W7TP plan-only report

## Purpose

Analyze legacy shell scripts that contain HA mesh, sync, node, router, RAM disk, and failover ideas.

The analyzer extracts useful architecture signals and marks unsafe execution commands.

## It must not

- execute the script
- run sudo
- run SSH
- run ssh-copy-id
- run rsync
- write crontab
- write /etc/fstab
- run iptables
- modify Merlin router
- store credentials

## Risk Classification

allow_low_risk:
- comments
- array names
- topology labels
- redacted node roles
- plan-only memory field names

pending_review:
- LAN/IPv6 fallback design
- RAM disk design
- sync schedule proposal
- Merlin QoS/firewall proposal
- node inventory conversion

dead_letter:
- ssh-copy-id
- root SSH automation
- StrictHostKeyChecking=no
- rsync --delete automation
- crontab write
- /etc/fstab write
- iptables direct apply
- credential propagation
