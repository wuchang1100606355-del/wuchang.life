#!/usr/bin/env python3
import importlib.util
import os
import json

mods = [
    "google",
    "google.auth",
    "google.cloud",
    "google.cloud.aiplatform",
    "google.cloud.secretmanager"
]

result = {
    "state": "GOOGLE_ORG_BRAIN_READINESS_CHECK",
    "imports": {},
    "env_refs": {
        "GOOGLE_CLOUD_PROJECT": bool(os.environ.get("GOOGLE_CLOUD_PROJECT")),
        "GOOGLE_APPLICATION_CREDENTIALS": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")),
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY"))
    },
    "raw_secret_printed": False,
    "authority": "CANDIDATE_ONLY_NO_TOTAL_FIELD_AUTHORITY"
}

for m in mods:
    try:
        result["imports"][m] = importlib.util.find_spec(m) is not None
    except Exception:
        result["imports"][m] = False

print(json.dumps(result, ensure_ascii=False, indent=2))
