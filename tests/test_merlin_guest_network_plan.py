from runtime.router.merlin_apply_queue import make_ticket
from runtime.router.merlin_human_execution_checklist import manual_steps_for_intent
from runtime.router.merlin_intent_driver import build_merlin_plan


def test_firewall_segmentation_plan_is_high_risk_and_plan_only() -> None:
    plan = build_merlin_plan(
        "firewall_segmentation_plan",
        note=(
            "Reviewed target: guest VLAN 52, interface tun22, "
            "guest subnet 192.168.52.0/24, trusted LAN 192.168.50.0/24."
        ),
    )

    assert plan["risk"] == "high"
    assert plan["decision"] == "pending_review"
    assert plan["safety"]["no_router_login"] is True
    assert plan["safety"]["no_ssh"] is True
    assert plan["safety"]["no_firewall_change"] is True
    assert "192.168.52.0/24" in plan["eamtp_packet"]["d2_intent"]["summary"]


def test_firewall_segmentation_ticket_never_becomes_executable() -> None:
    ticket = make_ticket(
        "firewall_segmentation_plan",
        note="Reviewed guest isolation policy; human application only.",
    )

    assert ticket["ticket_status"] == "awaiting_human_review"
    assert ticket["review_required"] is True
    assert ticket["executable"] is False
    assert ticket["safety"]["no_firewall_change"] is True


def test_firewall_segmentation_manual_steps_cover_guest_boundaries() -> None:
    steps = manual_steps_for_intent("firewall_segmentation_plan", [])
    joined = "\n".join(steps)

    assert "可信任 LAN" in joined
    assert "WAN" in joined
    assert "DHCP、DNS" in joined
    assert "Captive Portal" in joined
    assert "SSH" in joined
    assert "不得 flush" in joined
    assert "HTTPS 上網正常" in joined


def test_https_edge_routing_plan_is_high_risk_and_plan_only() -> None:
    plan = build_merlin_plan(
        "https_edge_routing_plan",
        note=(
            "Reviewed evidence: active port 443 reaches the Caddy host; "
            "a stale first port 80 rule shadows the later Caddy port 80 rule."
        ),
    )

    assert plan["risk"] == "high"
    assert plan["decision"] == "pending_review"
    assert plan["safety"]["no_router_login"] is True
    assert plan["safety"]["no_firewall_change"] is True
    assert any("exactly one port 80" in step for step in plan["steps"])
    assert any("Do not flush" in step for step in plan["steps"])


def test_https_edge_manual_steps_preserve_management_boundary() -> None:
    steps = manual_steps_for_intent("https_edge_routing_plan", [])
    joined = "\n".join(steps)

    assert "TCP 443" in joined
    assert "TCP 80" in joined
    assert "TCP 8443" in joined
    assert "HTTP 導向 HTTPS" in joined
    assert "includeSubDomains" in joined
    assert "不得 flush" in joined


def test_dns_service_naming_plan_blocks_control_plane_mismatch() -> None:
    plan = build_merlin_plan(
        "dns_service_naming_plan",
        note=(
            "Reviewed evidence: one public AI hostname reaches a Kubernetes API "
            "with a non-matching certificate; another POS hostname times out."
        ),
    )

    assert plan["risk"] == "medium"
    assert plan["decision"] == "pending_review"
    assert plan["safety"]["no_router_login"] is True
    assert plan["safety"]["no_firewall_change"] is True
    assert any("raw Kubernetes" in step for step in plan["steps"])
    assert any("DNSSEC" in step for step in plan["steps"])


def test_dns_service_naming_manual_steps_hold_unverified_hosts() -> None:
    steps = manual_steps_for_intent("dns_service_naming_plan", [])
    joined = "\n".join(steps)

    assert "權威 DNS" in joined
    assert "Kubernetes API" in joined
    assert "必須維持 HOLD" in joined
    assert "includeSubDomains" in joined
    assert "外部網路重新驗證" in joined
