from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_AUDIT = ROOT_DIR / "Taiji_Governance" / "logs" / "system_total_probe_audit.jsonl"
DEFAULT_USED_DIR = ROOT_DIR / "Taiji_Governance" / "one_time_decrypt" / "used"
DEFAULT_RESCUE_DIR = ROOT_DIR / "Taiji_Governance" / "rescue_snapshots"
DEFAULT_DECISION_DIR = ROOT_DIR / "Taiji_Governance" / "human_decisions"
SCHEMA = "taiji.hardware_bound_one_time_envelope.v1"
DECISION_SCHEMA = "taiji.human_decision_receipt.v1"
KDF_NAME = "pbkdf2_hmac_sha256"
KDF_ITERATIONS = 390_000
LOCAL_AUTH_MIN_LENGTH = 8
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32
CRITICAL_FILES = [
    "legacy_core/wuchang_tailscale_deployer.py",
    "services/gateway/app.py",
    "Taiji_Odoo/docker-compose.yml",
    "Taiji_Vector_Runtime_Lite/manifest.yml",
    "Taiji_Vector_Runtime_Lite/app/main.py",
    "Taiji_Governance/worklist/worklist.md",
    "Taiji_Governance/progress/progress.md",
    "Taiji_Governance/identity/digital_identity.yml",
    "Taiji_Governance/architecture/layers_standards.yml",
    "Taiji_Governance/deployments/cafe_main_redeploy_status.md",
    "Taiji_Governance/deployments/tailscale_deployment_manifest.json",
    "Taiji_Governance/deployments/tailscale_preflight_record.json",
    "Taiji_AutoBuild/scripts/00_readonly_probe.sh",
    "Taiji_AutoBuild/scripts/03_collect_runtime_snapshot.sh",
    "Taiji_AutoBuild/scripts/04_system_total_probe.py",
]
FORBIDDEN_PATTERNS = [
    r"taiji-guarded-run",
    r"--execute",
    r"StrictHostKeyChecking=no",
    r"systemctl\s+restart",
    r"docker\s+compose\s+up",
    r"docker\s+compose\s+down",
    r"create_subprocess_shell",
    r"os\.system",
    r"\bPopen\b",
    r"\bscp\b",
]

ADI_CAPABILITY_COORDINATES = {
    "human-decision": "system_total_probe.governance.human_decision",
    "probe": "system_total_probe.state.probe",
    "seal": "system_total_probe.transition.seal",
    "decrypt-once": "system_total_probe.transition.decrypt_once",
    "self-test": "system_total_probe.evidence.self_test",
    "rescue-snapshot": "system_total_probe.evidence.rescue_snapshot",
}
