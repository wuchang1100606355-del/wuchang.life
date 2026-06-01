# rsync code 23 handling

If migration reports:

```text
failed to set times on ".../Taiji_Odoo/postgres_data": Operation not permitted
rsync error: some files/attrs were not transferred (code 23)
```

This usually means rsync tried to preserve file attributes on a database volume
directory that is owned or protected by PostgreSQL/Docker.

Do not force-copy live database volume files as a normal project migration step.

Recommended recovery:

```bash
cd /mnt/c/Users/o0930/Taiji_Hub
APPLY=1 bash deploy/migration/wsl_native_migration_v0_1/MIGRATE_APPLY_NO_DB_VOLUMES.sh
bash deploy/migration/wsl_native_migration_v0_1/SYNC_RUNTIME_ARTIFACTS_ONLY.sh
TARGET=/home/taiji_admin/Taiji_Hub bash deploy/migration/wsl_native_migration_v0_1/POST_MIGRATION_RUNTIME_CHECK.sh
```

Database migration should be handled separately with:

- PostgreSQL dump/restore, or
- Docker volume backup/restore while containers are stopped, or
- Odoo-managed export/import,

and only after an explicit human decision.

