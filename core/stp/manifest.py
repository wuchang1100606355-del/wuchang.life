import json
from pathlib import Path

MANIFEST = Path(
    "manifests/stp/genesis_manifest.json"
)

def load_manifest():

    return json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

def save_manifest(data):

    MANIFEST.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )
