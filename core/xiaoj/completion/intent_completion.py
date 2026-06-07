import yaml
from pathlib import Path

ROOT_IDENTITY = Path(
    "configs/identity/WUCHANG_ROOT_IDENTITY.yaml"
)

class IntentCompletion:

    def __init__(self):

        self.identity = {}

        if ROOT_IDENTITY.exists():
            with open(
                ROOT_IDENTITY,
                encoding="utf-8"
            ) as f:

                data = yaml.safe_load(f)

                self.identity = data

    def complete(self,payload):

        root = self.identity.get(
            "identity_root",
            {}
        )

        payload.setdefault(
            "identity",
            root.get(
                "organization_id",
                "unknown_identity"
            )
        )

        payload.setdefault(
            "resource",
            "odoo+ollama+xiaoj"
        )

        payload.setdefault(
            "governance",
            root.get(
                "governance_framework",
                "W7TP"
            )
        )

        payload.setdefault(
            "authority",
            "chairperson"
        )

        payload.setdefault(
            "context",
            root.get(
                "legal_name",
                ""
            )
        )

        return payload
