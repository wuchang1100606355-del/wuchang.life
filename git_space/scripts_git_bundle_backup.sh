#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub

TS="$(date +%Y%m%d_%H%M%S)"
OUT="git_space/bundles"
mkdir -p "$OUT" evidence/git

BUNDLE="$OUT/taiji_hub_${TS}.bundle"
SHA="$BUNDLE.sha256"

git bundle create "$BUNDLE" --all
sha256sum "$BUNDLE" | tee "$SHA"

cat > "evidence/git/git_bundle_record_${TS}.md" <<MD
# Git Bundle Record

time: $TS
bundle: $BUNDLE
sha256: $SHA

storage_targets:
- D:\Taiji_Git_Space
- Google Shared Drive / W7TP_GIT_BACKUP
MD

echo "BUNDLE=$BUNDLE"
echo "SHA=$SHA"
