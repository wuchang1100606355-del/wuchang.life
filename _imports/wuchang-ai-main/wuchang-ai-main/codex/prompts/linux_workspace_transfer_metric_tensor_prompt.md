# Codex Prompt: Transfer Taiji Runtime to the Correct Linux Canonical Workspace

You are Codex operating under the user's highest technical authorization for their own Taiji / Wuchang AI runtime workspace.

Do **not** invent new architecture. Do **not** expose, print, commit, or copy real secrets. Do **not** move Odoo filestore, database dumps, `.env*`, API keys, OAuth secrets, tokens, logs, cache, `.venv*`, or generated runtime data into Git.

Your task is to migrate and stabilize the active workspace into the correct Linux canonical location while preserving the system's current design state.

---

## 0. System State Summary

Current system identity:

- Project family: Taiji / Wuchang AI Runtime
- Current Linux root visible in Windows Explorer: `\\wsl.localhost\Ubuntu\`
- Correct Linux user workspace root: `/home/taiji_admin`
- Preferred canonical project path: `/home/taiji_admin/Taiji_Hub`
- Optional repo path if separated: `/home/taiji_admin/Taiji_Hub/wuchang-ai`
- Windows path previously used: `C:\Taiji_Runtime`

Current architecture intent:

- Local-first sovereign AI runtime
- Linux-first canonical runtime workspace
- Windows only as VS Code / browser / control surface
- Odoo / PostgreSQL / Redis / gateway / webhook / AI services should run from Linux
- GitHub is documentation and source-control layer, not runtime-data storage

Current known risks:

- P0 secret exposure was reported for `taiji_hub.py`
- LINE secret was previously pasted and must be treated as exposed
- Git workspace had a report of 44 tracked files and 8779 untracked files
- Full `pytest` collection hit Odoo filestore permission errors
- `jules_cloud_api.py` reportedly has broad CORS and hard-coded auth paths
- Gateway has a docker-exec fallback that should be isolated as a runtime adapter

GitHub issue for stabilization:

- `o970106-dev/wuchang-ai#7`
- Title: `P0/P1 security stabilization from Taiji_Hub cognitive scan`

---

## 1. Metric Tensor / Non-Plaintext State Encoding

Use this compact non-secret system-state record as the transfer anchor:

```yaml
metric_packet:
  id: taiji.workspace.transfer.2026-05-17
  frame: FiveDimensionalCode
  dims: [x, y, z, time, scale]
  x: linux_canonical_workspace
  y: runtime_governance_boundary
  z: source_control_cleanliness
  time: 2026-05-17T00:00:00+08:00
  scale: local_user_node_to_github_repo
  node:
    os: Ubuntu_WSL
    user: taiji_admin
    canonical_path: /home/taiji_admin/Taiji_Hub
  external_control_surface:
    windows_path: C:\Taiji_Runtime
    role: deprecated_control_surface_only
  governance:
    no_secret_commit: true
    no_runtime_data_commit: true
    rotate_exposed_credentials: manual_required
    issue_ref: o970106-dev/wuchang-ai#7
  allowed_artifacts:
    - source_code
    - docs
    - tests
    - config_templates
    - scripts_without_secrets
  forbidden_artifacts:
    - .env
    - .env.*
    - api_keys
    - oauth_secrets
    - tokens
    - service_account_json
    - logs
    - cache
    - .venv
    - venv
    - Odoo filestore
    - database_dumps
    - backup_archives
    - release_archives_with_secrets
```

---

## 2. Required Operating Principle

The correct source of runtime truth is Linux:

```text
Windows VS Code / Browser
→ Remote WSL or Remote SSH
→ /home/taiji_admin/Taiji_Hub
→ GitHub clean source repository
```

Avoid this drift pattern:

```text
C:\Taiji_Runtime copy
+
/home/taiji_admin/Taiji_Hub copy
+
manual drag-and-drop movement
```

The goal is not to blindly copy all files. The goal is to identify clean source, move only safe source artifacts, and keep runtime data outside Git.

---

## 3. First-pass Actions

Run from Linux shell, not Windows PowerShell, unless explicitly needed.

```bash
set -euo pipefail

CANON="/home/taiji_admin/Taiji_Hub"
WIN_MNT="/mnt/c/Taiji_Runtime"

mkdir -p "$CANON"
cd "$CANON"

printf '\n=== NODE ===\n'
uname -a
whoami
pwd

printf '\n=== GIT STATUS ===\n'
git status --short || true

printf '\n=== TOP LEVEL ===\n'
find . -maxdepth 2 -type f | sed 's#^./##' | sort | head -200

printf '\n=== POSSIBLE WINDOWS SOURCE ===\n'
if [ -d "$WIN_MNT" ]; then
  find "$WIN_MNT" -maxdepth 2 -type f | sed "s#^$WIN_MNT/##" | sort | head -200
else
  echo "Windows source path not found: $WIN_MNT"
fi
```

---

## 4. Create / Verify `.gitignore`

Create or update `.gitignore` before staging anything.

Required patterns:

```gitignore
# Secrets and env
.env
.env.*
*.pem
*.key
*.p12
*.pfx
*secret*
*token*
*credential*
service_account*.json
*-service-account.json

# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
.venv*/
venv/
env/

# Runtime data
logs/
log/
cache/
.cache/
runtime/*.pid
runtime/*.sock
*.log
*.sqlite
*.db

# Odoo / DB / filestore
Taiji_Odoo/odoo_data/
odoo_data/
filestore/
*.dump
*.sql
*.sql.gz
*.bak

# Build / release / archive
backup/
backups/
release/
releases/
archive/
archives/
dist/
build/
*.zip
*.tar
*.tar.gz
*.7z

# OS / editor
.DS_Store
Thumbs.db
.vscode/settings.json
```

---

## 5. Create `pytest.ini`

If missing, add:

```ini
[pytest]
testpaths = tests
norecursedirs = .git .venv .venv* venv env Taiji_Odoo/odoo_data odoo_data filestore logs log cache backup backups release releases archive archives dist build __pycache__
addopts = -q
```

Then run:

```bash
python3 -m pytest
```

Expected baseline from scan: restricted tests should pass around `38 passed`.

---

## 6. Secret Remediation Rules

Do not print secret values.

Search only for presence indicators:

```bash
printf '\n=== SECRET INDICATOR SCAN ===\n'
grep -RInE "(API_KEY|CLIENT_SECRET|GEMINI|LINE_CLIENT_SECRET|BEGIN PRIVATE KEY|oauth|token)" \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude-dir=venv \
  --exclude-dir=Taiji_Odoo \
  --exclude='*.zip' \
  --exclude='*.tar' \
  --exclude='*.gz' \
  . || true
```

When a secret is found:

- Replace hard-coded value with `os.environ[...]` or `os.getenv(...)`.
- Put only placeholder examples in `.env.example`.
- Record the file path and line number without reproducing the secret.
- Require manual provider-console rotation.

---

## 7. Safe Migration from Windows Path

If `C:\Taiji_Runtime` contains newer source files, do not copy everything.

Use this allowlist approach:

```bash
SAFE_IMPORT_DIR="$CANON/_incoming_windows_source_review"
mkdir -p "$SAFE_IMPORT_DIR"

if [ -d "$WIN_MNT" ]; then
  rsync -av --dry-run \
    --include='*/' \
    --include='*.py' \
    --include='*.md' \
    --include='*.json' \
    --include='*.yaml' \
    --include='*.yml' \
    --include='*.toml' \
    --include='*.ini' \
    --include='*.sh' \
    --exclude='.env*' \
    --exclude='*secret*' \
    --exclude='*token*' \
    --exclude='*.log' \
    --exclude='.venv*/' \
    --exclude='venv/' \
    --exclude='logs/' \
    --exclude='cache/' \
    --exclude='odoo_data/' \
    --exclude='filestore/' \
    --exclude='backup*/' \
    --exclude='release*/' \
    --exclude='archive*/' \
    --exclude='*' \
    "$WIN_MNT/" "$SAFE_IMPORT_DIR/"
fi
```

Only after reviewing the dry-run output should actual copy happen.

---

## 8. Expected Output Back to User

Report in this format:

```text
NODE: <hostname/user/path>
CANONICAL_WORKSPACE: /home/taiji_admin/Taiji_Hub
WINDOWS_SOURCE_FOUND: yes/no
GIT_STATUS_SUMMARY: <tracked/untracked/modified counts>
SECRET_INDICATORS_FOUND: <count, paths only, no values>
PYTEST_RESULT: <pass/fail and reason>
MIGRATION_ACTION: <none/dry-run/copied reviewed safe source>
NEXT_REQUIRED_MANUAL_ACTION: rotate Gemini and LINE credentials if not already done
```

---

## 9. Interpretation Rule

If ambiguity exists, do not guess. Prefer no file movement over unsafe movement.

Priority order:

1. Prevent secret leakage.
2. Preserve Linux canonical workspace.
3. Keep Git auditable.
4. Keep runtime data out of repo.
5. Stabilize tests.
6. Then refactor gateway/auth/runtime adapters.

---

## 10. Short English Instruction for Codex

Transfer the active Taiji / Wuchang runtime into the Linux canonical workspace at `/home/taiji_admin/Taiji_Hub`. Treat Windows `C:\Taiji_Runtime` only as a deprecated control-surface source to review, not as source of truth. Do not copy secrets, env files, logs, Odoo filestore, database dumps, venvs, backups, caches, or archives. Add/verify `.gitignore` and `pytest.ini`, scan for secret indicators without printing values, and report only paths and counts. Preserve the current architecture: local-first sovereign AI, governed runtime, gateway boundary, Five-Dimensional Code signing, Odoo/Redis/GitHub integration, and Linux-first deployment. Reference GitHub issue `o970106-dev/wuchang-ai#7` for P0/P1 stabilization context.
