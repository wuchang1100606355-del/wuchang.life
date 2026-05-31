# M010 Git Status Cleanup Policy

Purpose:
Classify remaining untracked files after M001-M009 baseline without deleting or bulk-adding.

Current policy:
- No git add .
- No deletion.
- No service restart.
- No secret read.
- No raw Drive dump.
- No raw runtime state commit.

Remaining untracked categories:
- Odoo high-risk credential/OAuth/controller/data files
- Runtime generated state, outbox, metrics, mock, memos, reports
- Backup files and .bak files
- Deployment variants and legacy scripts
- Packaged evidence archives
- Cloud/import folders
- UI/web/site artifacts
- Model files and local runtime assets
- Topology/security/config candidates requiring separate review

Next action:
- Create category-specific include/exclude indexes.
- Only commit safe source, policy, template, or redacted files.
- Preserve raw evidence in D: cold storage or redacted evidence packs.
