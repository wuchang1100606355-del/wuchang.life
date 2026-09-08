from __future__ import annotations

from fastapi import HTTPException
import pytest

from services.gateway.shared_resources import (
    _client_is_internal,
    _registered_node,
    _safe_metadata,
    _safe_relative_path,
)
from services.gateway.topology_router import topology, topology_summary


def test_internal_network_boundary() -> None:
    assert _client_is_internal("127.0.0.1") is True
    assert _client_is_internal("192.168.50.218") is True
    assert _client_is_internal("100.111.139.7") is True
    assert _client_is_internal("8.8.8.8") is False


def test_shared_drive_path_rejects_escape() -> None:
    assert _safe_relative_path("資料/比賽") == "資料/比賽"
    with pytest.raises(HTTPException):
        _safe_relative_path("../secret")
    with pytest.raises(HTTPException):
        _safe_relative_path("/absolute")


def test_registered_node_aliases_do_not_create_new_nodes() -> None:
    topology = {"nodes": {"msi_gpu_organ": {}, "taiji04_sunmi_pos": {}}}
    assert _registered_node(topology, "MSI") == "msi_gpu_organ"
    assert _registered_node(topology, "sunmi") == "taiji04_sunmi_pos"
    with pytest.raises(HTTPException):
        _registered_node(topology, "invented-node")


def test_sensitive_names_are_omitted() -> None:
    items, omitted = _safe_metadata(
        [
            {"Name": "competition", "Path": "competition", "IsDir": True},
            {"Name": ".env", "Path": ".env", "Size": 10},
            {"Name": "service_account.json", "Path": "service_account.json", "Size": 20},
        ]
    )
    assert [item["name"] for item in items] == ["competition"]
    assert omitted == 2


def test_topology_exposes_total_field_hardware_orchestration() -> None:
    observed = topology()
    control = observed["total_field_hardware_orchestration"]
    resources = observed["distributed_resource_field"]
    assert control["controller"] == "TOTAL_FIELD"
    assert control["observation_engine"] == "8D_STATE_FIELD"
    assert control["locator"] == "ADI_EXACT_NODE_CAPABILITY_AND_ROUTE_COORDINATE"
    assert control["internal_signal"] == "D6_GENERATIVE_TRANSMISSION"
    assert resources["aggregation_mode"] == "LOGICAL_SCHEDULABLE_POOL_NOT_PHYSICAL_SINGLE_MEMORY"
    assert resources["scheduler_owner"] == "TOTAL_FIELD"


def test_topology_summary_marks_scene_reusable_resource_pool() -> None:
    observed = topology_summary()
    assert observed["hardware_orchestration"] is True
    assert observed["distributed_resource_aggregation"] == (
        "LOGICAL_SCHEDULABLE_POOL_NOT_PHYSICAL_SINGLE_MEMORY"
    )
    assert observed["odoo_is_primary_application_capability_plane"] is True


def test_odoo_is_application_plane_not_total_field_authority() -> None:
    observed = topology()["odoo_capability_plane"]
    assert observed["role"] == (
        "PRIMARY_SYSTEM_DESCRIPTION_AND_APPLICATION_CAPABILITY_ARCHITECTURE"
    )
    assert observed["odoo_is_total_field_or_d8_authority"] is False
    assert observed["projection_scope"] == (
        "AFFECTED_MODELS_VIEWS_ACCESS_RULES_AND_WORKFLOWS_ONLY"
    )
    reuse = observed["module_reuse_policy"]
    assert reuse["8dadi_resolves_requirement_to_existing_module_capability_first"] is True
    assert reuse["duplicate_odoo_core_or_parallel_business_framework"] is False
