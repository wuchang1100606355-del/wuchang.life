# -*- coding: utf-8 -*-
"""
Wuchang 7D-8Z-5Code State Tensor Network
五常七維八陣五維碼狀態張量網

Safety:
- readonly logic core only
- no SSH
- no process kill
- no auto-start
- no system modification
- no secret reading
- no .env/token/private-key access
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
from time import time
from typing import Dict, List, Tuple, Any


READONLY_POLICY = {
    "readonly_only": True,
    "no_ssh": True,
    "no_process_kill": True,
    "no_auto_start": True,
    "no_secret_read": True,
    "human_operator_required": True,
}


@dataclass(frozen=True)
class SevenDField:
    """
    七維天地維方位狀態碼

    D1 heaven    天維：上層政策、不可違反規則
    D2 earth     地維：本地硬體、能源、網路條件
    D3 direction 方維：來源、流向、目的
    D4 position  位維：節點位置、服務層級
    D5 state     狀維：目前模式
    D6 tendency  態維：趨勢、風險斜率
    D7 code      碼維：不可逆索引參照
    """

    heaven: int
    earth: int
    direction: int
    position: int
    state: int
    tendency: int
    code: int

    def as_tuple(self) -> Tuple[int, int, int, int, int, int, int]:
        return (
            self.heaven,
            self.earth,
            self.direction,
            self.position,
            self.state,
            self.tendency,
            self.code,
        )

    def normalized(self) -> "SevenDField":
        return SevenDField(*[clamp_0_100(v) for v in self.as_tuple()])

    def risk_score(self) -> int:
        s = self.normalized()
        risk = (
            0.20 * (100 - s.heaven)
            + 0.15 * (100 - s.earth)
            + 0.10 * s.direction
            + 0.10 * s.position
            + 0.20 * s.state
            + 0.20 * s.tendency
            + 0.05 * s.code
        )
        return clamp_0_100(risk)


class EightFormation(str, Enum):
    """
    八陣 / 八卦作為工程狀態分類，不作占卜用途。
    """

    QIAN = "qian_admin_policy"
    DUI = "dui_comm_feedback"
    LI = "li_semantic_display"
    ZHEN = "zhen_event_trigger"
    XUN = "xun_route_flow"
    KAN = "kan_risk_isolation"
    GEN = "gen_boundary_gate"
    KUN = "kun_storage_local_field"


def classify_formation(field: SevenDField) -> EightFormation:
    s = field.normalized()
    risk = s.risk_score()

    if s.heaven < 40:
        return EightFormation.QIAN
    if s.state >= 80 or risk >= 80:
        return EightFormation.KAN
    if s.tendency >= 75:
        return EightFormation.ZHEN
    if s.direction >= 70:
        return EightFormation.XUN
    if s.position >= 70:
        return EightFormation.GEN
    if s.code >= 70:
        return EightFormation.KUN
    if s.earth >= 70:
        return EightFormation.DUI
    return EightFormation.LI


@dataclass(frozen=True)
class FiveCodeInput:
    """
    五維碼輸入。
    不放真實姓名、電話、地址、token、private key。

    subject_ref: 人/設備/事件的低敏參照
    device_ref: 裝置或節點參照
    context_ref: 場景/任務/服務參照
    authority_ref: 權限/角色/範圍參照
    time_state_ref: TTL/時間/生命週期參照
    """

    subject_ref: str
    device_ref: str
    context_ref: str
    authority_ref: str
    time_state_ref: str


def make_five_code(inp: FiveCodeInput, namespace: str = "wuchang") -> str:
    raw = "|".join([
        namespace,
        safe_token(inp.subject_ref),
        safe_token(inp.device_ref),
        safe_token(inp.context_ref),
        safe_token(inp.authority_ref),
        safe_token(inp.time_state_ref),
    ])
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class TensorNode:
    node_id: str
    five_code: str
    field_7d: SevenDField
    formation: EightFormation
    role: str
    ts: float

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "five_code_prefix": self.five_code[:12],
            "field_7d": asdict(self.field_7d.normalized()),
            "formation": self.formation.value,
            "risk_score": self.field_7d.risk_score(),
            "role": self.role,
            "ts": self.ts,
            "policy": READONLY_POLICY,
        }


@dataclass
class TensorEdge:
    src: str
    dst: str
    relation: str
    weight: float
    allowed: bool


class StateTensorNetwork:
    """
    狀態張量網：
    node = 事件 / 設備 / 服務 / 人類操作參照
    edge = 關係 / 流向 / 權限 / 風險
    """

    def __init__(self, name: str = "wuchang_7d8z_5code_tensor"):
        self.name = name
        self.nodes: Dict[str, TensorNode] = {}
        self.edges: List[TensorEdge] = []

    def add_node(
        self,
        node_id: str,
        five_input: FiveCodeInput,
        field_7d: SevenDField,
        role: str,
    ) -> TensorNode:
        five_code = make_five_code(five_input)
        formation = classify_formation(field_7d)

        node = TensorNode(
            node_id=safe_token(node_id),
            five_code=five_code,
            field_7d=field_7d.normalized(),
            formation=formation,
            role=safe_token(role),
            ts=time(),
        )
        self.nodes[node.node_id] = node
        return node

    def connect(
        self,
        src: str,
        dst: str,
        relation: str,
        weight: float = 1.0,
        allowed: bool = True,
    ) -> TensorEdge:
        edge = TensorEdge(
            src=safe_token(src),
            dst=safe_token(dst),
            relation=safe_token(relation),
            weight=max(0.0, min(1.0, float(weight))),
            allowed=bool(allowed),
        )
        self.edges.append(edge)
        return edge

    def decide(self, node_id: str) -> Dict[str, Any]:
        node_id = safe_token(node_id)
        node = self.nodes[node_id]
        risk = node.field_7d.risk_score()

        if risk >= 85:
            mode = "S4_LIFE_SAFETY_OR_BROWNOUT"
            action = "HUMAN_REVIEW_REQUIRED"
        elif risk >= 65:
            mode = "S3_BROWNOUT"
            action = "SUGGEST_RATE_LIMIT_OR_ISOLATE"
        elif risk >= 45:
            mode = "S2_DEGRADED"
            action = "SUGGEST_WATCH_AND_SUMMARIZE"
        elif risk >= 25:
            mode = "S1_WATCH"
            action = "OBSERVE_ONLY"
        else:
            mode = "S0_NORMAL"
            action = "NO_ACTION"

        return {
            "node": node.to_public_dict(),
            "mode": mode,
            "suggested_action": action,
            "readonly_enforced": True,
            "must_not_execute": [
                "ssh",
                "kill_process",
                "auto_start",
                "systemctl_start_stop_restart",
                "docker_start_stop_restart",
                "read_env_or_tokens",
            ],
        }

    def public_snapshot(self) -> Dict[str, Any]:
        return {
            "network": self.name,
            "policy": READONLY_POLICY,
            "nodes": [n.to_public_dict() for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges],
        }


def clamp_0_100(v: int | float) -> int:
    try:
        return max(0, min(100, int(v)))
    except Exception:
        return 0


def safe_token(value: str) -> str:
    value = str(value).strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.:/"
    cleaned = "".join(c for c in value if c in allowed)
    return cleaned[:128] if cleaned else "unknown"


def print_json(obj: Any) -> None:
    import json
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def demo() -> None:
    net = StateTensorNetwork()

    taiji01 = net.add_node(
        node_id="taiji01",
        five_input=FiveCodeInput(
            subject_ref="service-node",
            device_ref="taiji01",
            context_ref="ollama-local",
            authority_ref="readonly",
            time_state_ref="20260523",
        ),
        field_7d=SevenDField(
            heaven=90,
            earth=75,
            direction=30,
            position=60,
            state=25,
            tendency=20,
            code=50,
        ),
        role="ollama_node",
    )

    webui_closed = net.add_node(
        node_id="openwebui_3000_closed",
        five_input=FiveCodeInput(
            subject_ref="service-state",
            device_ref="taiji01",
            context_ref="openwebui",
            authority_ref="readonly",
            time_state_ref="closed",
        ),
        field_7d=SevenDField(
            heaven=95,
            earth=70,
            direction=35,
            position=55,
            state=55,
            tendency=30,
            code=45,
        ),
        role="webui_state",
    )

    net.connect(
        src=taiji01.node_id,
        dst=webui_closed.node_id,
        relation="same_host_service_state",
        weight=0.8,
        allowed=True,
    )

    print("=== NODE DECISION ===")
    print_json(net.decide("taiji01"))

    print("\n=== SNAPSHOT ===")
    print_json(net.public_snapshot())


if __name__ == "__main__":
    demo()
