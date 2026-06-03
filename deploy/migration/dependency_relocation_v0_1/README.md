# Taiji Dependency Relocation v0.1

Purpose: move and map system dependency files into three governed locations:

1. Organization cloud readonly staging
2. Local Linux dependency workspace
3. D drive controlled folder `D:\taiji_lock`

## Core Rule

雙地五維碼映射，一處單向非同步寫入。

In this package:

- authoritative source: `/home/taiji_admin/Taiji_Hub`
- one-way write direction: source -> staging/archive targets
- no reverse sync from cloud/D/local dependency copy back into source
- every copied file gets SHA256 and a five-metric mapping record

## Targets

```text
Cloud staging:
/home/taiji_admin/Taiji_Hub_Org_Readonly_Cloud_Staging/Taiji_Dependency_Cloud_Readonly_20260512

Local dependency workspace:
/home/taiji_admin/Taiji_Hub_Dependency_Local

D controlled folder:
/mnt/d/taiji_lock
```

## Safety

Excluded from cloud/local/D copies:

- keys/
- .secrets/
- data/secrets/
- service account JSON
- OAuth files
- private keys
- tokens
- .env and *.env
- Odoo/Postgres live volumes
- virtual environments
- node_modules
- runtime caches

## Commands

```bash
cd /home/taiji_admin/Taiji_Hub
bash deploy/migration/dependency_relocation_v0_1/BUILD_DEPENDENCY_PLAN.sh
bash deploy/migration/dependency_relocation_v0_1/APPLY_RELOCATION.sh
bash deploy/migration/dependency_relocation_v0_1/VERIFY_RELOCATION.sh
```

Cloud Drive folder requested by owner:

```text
https://drive.google.com/drive/folders/1PwybNATp-pPZ8DJiTEJbga3mJO1p4NCn
```

Current connector status: folder not accessible to the connected Google Drive tool. Upload must be performed manually or after granting the connector access.

