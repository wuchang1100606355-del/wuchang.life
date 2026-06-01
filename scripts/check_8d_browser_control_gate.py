#!/usr/bin/env python3
import hashlib, json, sys
from pathlib import Path

identity = Path("runtime/identity_codes/W7ID_admin_superadmin_001.json")
encrypted = Path("runtime/identity_codes/W8D_admin_superadmin_001.json.gpg")
digest = Path("runtime/identity_codes/W8D_admin_superadmin_001.json.gpg.sha256")

if not identity.exists():
    print("DENY: missing 7D identity code")
    sys.exit(1)

if not encrypted.exists():
    print("DENY: missing 8D encrypted identity envelope")
    sys.exit(1)

if not digest.exists():
    print("DENY: missing 8D sha256 file")
    sys.exit(1)

actual = hashlib.sha256(encrypted.read_bytes()).hexdigest()
expected = digest.read_text(encoding="utf-8").split()[0].strip()

if actual != expected:
    print("DENY: 8D sha256 mismatch")
    sys.exit(1)

data = json.loads(identity.read_text(encoding="utf-8"))

if data.get("subject", {}).get("role") != "single_seat_superadmin":
    print("DENY: identity role not superadmin")
    sys.exit(1)

print("ALLOW: 8D identity gate passed for AI browser control")
