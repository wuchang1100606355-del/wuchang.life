import json
from pathlib import Path


MANIFEST = Path("Taiji_Governance/system_info/wuchang_life_system_scope_nodes.manifest.json")


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_scope_domain_and_status():
    data = load_manifest()
    assert data["schema"] == "taiji.wuchang_life_system_scope.v1"
    assert data["status"] == "ACTIVE"
    assert data["domain"] == "wuchang.life"
    assert data["default_write_permission"] == "blocked_until_gateway_authorized"


def test_all_nodes_are_write_blocked_by_default():
    data = load_manifest()
    assert len(data["nodes"]) >= 11
    assert {node["write_permission"] for node in data["nodes"]} == {
        "blocked_until_gateway_authorized"
    }


def test_known_core_nodes_present():
    data = load_manifest()
    machines = {node["machine"]: node for node in data["nodes"]}
    assert machines["taiji01"]["tailscale_ip"] == "100.71.224.18"
    assert "governance_node" in machines["taiji01"]["scope_role"]
    assert machines["msi"]["tailscale_ip"] == "100.107.187.77"
    assert "development_node" in machines["msi"]["scope_role"]


def test_domain_routes_include_public_and_vpn_boundaries():
    data = load_manifest()
    routes = {route["host"]: route for route in data["domain_routes"]}
    assert routes["fund.wuchang.life"]["exposure"] == "public_summary_only"
    assert routes["admin.wuchang.life"]["exposure"] == "vpn_only"
    assert routes["odoo.wuchang.life"]["exposure"] == "vpn_only"


def test_security_invariants_block_sensitive_shortcuts():
    invariants = load_manifest()["security_invariants"]
    assert invariants["service_object_not_remote_control"] is True
    assert invariants["secret_material_allowed"] is False
    assert invariants["member_plaintext_cloud_allowed"] is False
    assert invariants["direct_production_write_allowed"] is False
    assert invariants["gateway_required"] is True
    assert invariants["audit_required"] is True
