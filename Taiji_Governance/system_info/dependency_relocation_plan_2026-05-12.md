# Dependency Relocation Plan

Version: 2026-05-12

## Source

```text
/home/taiji_admin/Taiji_Hub
```

## Targets

```text
Cloud staging: /home/taiji_admin/Taiji_Hub_Org_Readonly_Cloud_Staging/Taiji_Dependency_Cloud_Readonly_20260512
Local dependency workspace: /home/taiji_admin/Taiji_Hub_Dependency_Local
D controlled folder: /mnt/d/taiji_lock
Google Drive target: https://drive.google.com/drive/folders/1PwybNATp-pPZ8DJiTEJbga3mJO1p4NCn
```

## Rule

```text
雙地五維碼映射，一處單向非同步寫入。
source -> targets only.
reverse sync is blocked.
```

## Plan JSONL

```text
/home/taiji_admin/Taiji_Hub/Taiji_Governance/system_info/dependency_relocation_plan_2026-05-12.jsonl
```

## Secret Handling

Secret-like paths, keys, env files, Odoo/Postgres live volumes, caches, and virtual environments are excluded.

