#!/usr/bin/env python3
"""System total probe with hardware-bound one-time decrypt envelopes.

The probe never prints raw hardware identifiers. Decryption is local-only,
hardware-bound, audited, and one-time by marker file.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from system_total_probe_8d_adi.capabilities import (
    command_decrypt_once,
    command_probe,
    command_seal,
    command_self_test,
)
from system_total_probe_8d_adi.cli import (
    add_human_decision_arg,
    add_local_auth_args,
    build_parser,
)
from system_total_probe_8d_adi.contract import (
    ADI_CAPABILITY_COORDINATES,
    CRITICAL_FILES,
    DECISION_SCHEMA,
    DEFAULT_AUDIT,
    DEFAULT_DECISION_DIR,
    DEFAULT_RESCUE_DIR,
    DEFAULT_USED_DIR,
    FORBIDDEN_PATTERNS,
    KDF_ITERATIONS,
    KDF_NAME,
    KEY_BYTES,
    LOCAL_AUTH_MIN_LENGTH,
    NONCE_BYTES,
    ROOT_DIR,
    SALT_BYTES,
    SCHEMA,
)
from system_total_probe_8d_adi.crypto import derive_key, envelope_id, used_marker_path
from system_total_probe_8d_adi.foundation import (
    b64d,
    b64e,
    local_json_get,
    run_status_check,
    safe_text_excerpt,
    sha256_bytes,
    sha256_file,
    utc_now,
    write_json,
)
from system_total_probe_8d_adi.governance import (
    append_audit,
    authorize_local_use,
    create_human_decision,
    human_decision_id,
    read_passphrase,
    read_secret,
    verify_human_decision,
)
from system_total_probe_8d_adi.hardware import (
    commandless_hardware_signals,
    hardware_fingerprint,
    read_signal,
)
from system_total_probe_8d_adi.rescue import (
    build_rescue_snapshot,
    command_rescue_snapshot,
    critical_file_manifest,
    scan_file_forbidden,
)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
