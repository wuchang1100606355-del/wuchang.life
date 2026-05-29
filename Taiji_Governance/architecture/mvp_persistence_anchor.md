# Taiji MVP Persistence Anchor

created_at: 2026-05-18T10:06:50+08:00
classification: non_secret_governance_marker
purpose: keep the four-folder MVP architecture resumable after shutdown or partial environment loss

## Four-folder continuity model

1. WSL Live Hub
   path: /home/taiji_admin/Taiji_Hub
   role: primary Linux-native MVP worktree, runtime integration, fast scan/diff/test path

2. Windows Formal Hub
   path: C:\Users\o0930\Taiji_Hub
   role: formal mirror, clean governance/schema/deploy reference, Windows-accessible archive

3. Wuchang Core
   path: C:\wuchang_8_0_core
   role: legacy engine and gateway source, recoverable runtime/gateway reference

4. WSL Live Root
   path: /home/taiji_admin
   role: live environment root, systemd/Ollama/Caddy/audit evidence, not a clean source repository

## Resume order after shutdown

1. Start from /home/taiji_admin/Taiji_Hub for Linux-native work.
2. Read Taiji_Governance/architecture and reports before changing runtime files.
3. Compare against C:\Users\o0930\Taiji_Hub as formal mirror.
4. Pull legacy runtime/gateway evidence from C:\wuchang_8_0_core only after comparison.
5. Treat /home/taiji_admin as live evidence root; do not promote secrets, DBs, model weights, logs, or volumes into formal architecture.

## MVP extraction rule

- identical files across folders: stable inherited core
- unique files: folder-specific capability
- same-name different-content files: feature comparison and merge decision required

## Safety boundary

No secrets, keys, database contents, model weights, logs, or runtime volumes are stored in this marker.
This file is safe to copy, hash, diff, and delete.