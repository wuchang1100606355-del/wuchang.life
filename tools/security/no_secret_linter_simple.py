import pathlib, re, sys

ROOT = pathlib.Path(".")
PATTERNS = [
    r"sk-[A-Za-z0-9_\-]{20,}",
    r"OPENAI_API_KEY\s*=",
    r"GOOGLE_CLIENT_SECRET\s*=",
    r"LINE_CHANNEL_SECRET\s*=",
    r"PRIVATE KEY",
    r"BEGIN RSA PRIVATE KEY",
    r"BEGIN OPENSSH PRIVATE KEY",
    r"password\s*[:=]\s*['\"][^'\"]{6,}",
    r"token\s*[:=]\s*['\"][^'\"]{12,}",
]

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}

hits = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if any(part in SKIP_DIRS for part in p.parts):
        continue
    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".tar", ".gz", ".zip", ".sqlite", ".db"}:
        continue
    try:
        text = p.read_text(errors="ignore")
    except Exception:
        continue
    for pat in PATTERNS:
        if re.search(pat, text, re.I):
            hits.append((str(p), pat))

print("NO_SECRET_LINTER_REPORT")
print(f"files_scanned=done")
print(f"hits={len(hits)}")
for path, pat in hits:
    print(f"HIT\t{path}\t{pat}")

sys.exit(1 if hits else 0)
