#!/bin/bash
set -euo pipefail
mkdir -p evidence

python3 -c 'import json,traceback; mods=["google.generativeai","google","requests","pydantic"]; r={}; \
for m in mods:
    try:
        __import__(m); r[m]="present"
    except Exception as e:
        r[m]=traceback.format_exc()
print(json.dumps(r, ensure_ascii=False, indent=2))' > evidence/module_check_detailed.json 2> evidence/module_check_detailed_err.log

python3 -c "import subprocess,sys
try:
    print(subprocess.check_output([sys.executable,'-m','pip','freeze']).decode())
except Exception as e:
    print('PIP_FREEZE_ERROR: '+str(e))" > evidence/pip_freeze_full.txt 2> evidence/pip_freeze_full_err.log

grep -E '^[[:space:]]*(import |from )' taiji_hub.py > evidence/taiji_imports.txt 2>&1 || true

echo "EVIDENCE_COLLECTED: $(date -u +%Y-%m-%dT%H:%M:%SZ)" > evidence/COLLECT_TIMESTAMP.txt
