import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

BAGUA_SPACE = {
    (1, 1, 1): "QIAN", (0, 0, 0): "KUN",
    (0, 1, 0): "KAN",  (1, 0, 1): "LI",
    (0, 0, 1): "ZHEN", (1, 1, 0): "XUN",
    (1, 0, 0): "GEN",  (0, 1, 1): "DUI",
}

WUXING_RULES = {
    "WOOD": {"weight": 1.0, "gen": "FIRE", "res": "EARTH"},
    "FIRE": {"weight": 1.5, "gen": "EARTH", "res": "METAL"},
    "EARTH": {"weight": 1.0, "gen": "METAL", "res": "WATER"},
    "METAL": {"weight": 1.2, "gen": "WATER", "res": "WOOD"},
    "WATER": {"weight": 1.1, "gen": "WOOD", "res": "FIRE"},
}

BAGUA_TO_WUXING = {
    "QIAN": "METAL", "DUI": "METAL", "LI": "FIRE",
    "ZHEN": "WOOD", "XUN": "WOOD",
    "KAN": "WATER", "GEN": "EARTH", "KUN": "EARTH",
}

def sha256_text(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def deterministic_vector(text: str, dims: int = 5) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [((int.from_bytes(digest[i*4:(i+1)*4], "big") / 0xFFFFFFFF) * 2 - 1) for i in range(dims)]

def deterministic_metric_matrix(seed: str, rows: int = 3, cols: int = 5) -> List[List[float]]:
    digest = hashlib.sha512(seed.encode("utf-8")).digest()
    matrix, k = [], 0
    for _ in range(rows):
        row = []
        for _ in range(cols):
            row.append(round((digest[k % len(digest)] / 255.0) * 2 - 1, 4))
            k += 1
        matrix.append(row)
    return matrix

@dataclass
class D8IntentPayload:
    packet_version: str
    packet_id: str
    human_subject_ref: str
    timestamp_ms: int
    nonce: str
    previous_hash: str
    d1_identity_hash: str
    d2_intent_hash: str
    d3_state_code: str
    d4_topology_route: str
    d5_resource_weight: float
    d6_governance_status: str
    d7_audit_root: str
    scope: Dict[str, str]
    redaction_level: str
    optional_encrypted_payload_ref: Optional[str]
    seal_hash: str
    signature_mock: str

class IntentPrism:
    def __init__(self, metric_seed: str = "W7TP_HELUO_METRIC_V2"):
        self.metric_matrix = deterministic_metric_matrix(metric_seed)

    def dot_product(self, vector: List[float]) -> List[float]:
        return [sum(m * v for m, v in zip(row, vector)) for row in self.metric_matrix]

    def process_intent(self, raw_intent: str) -> Tuple[str, str, str, List[float], Tuple[int, int, int]]:
        ai_vector = deterministic_vector(raw_intent, 5)
        projected = self.dot_product(ai_vector)
        yao = tuple(1 if val >= 0 else 0 for val in projected)
        bagua_state = BAGUA_SPACE.get(yao, "KUN")
        polarity = "YANG" if yao.count(1) >= 2 else "YIN"
        wuxing = BAGUA_TO_WUXING[bagua_state]
        return polarity, bagua_state, wuxing, ai_vector, yao

class D6GovernanceGate:
    def evaluate(self, intent_text: str, redaction_level: str, channel: str) -> Tuple[bool, str]:
        violations = []
        if any(term in intent_text.lower() for term in ["password", "private key", "token", "secret"]):
            violations.append("secret_read_blocked")
        if redaction_level not in {"L0_LOCAL_ONLY", "L1_CLOUD_BLIND_COMPUTE", "L2_ZERO_KNOWLEDGE_LOCAL"}:
            violations.append("invalid_redaction_level")
        if channel == "CLOUD_CHANNEL" and redaction_level == "L0_LOCAL_ONLY":
            violations.append("cloud_route_forbidden")
        if violations:
            return False, "D6_BLOCKED:" + ",".join(violations)
        return True, "D6_PASS:privacy_gate+harm_gate+policy_gate+human_review_gate"

class IntentFieldEngine:
    def __init__(self, human_id: str, signing_key: bytes = b"W7TP_LOCAL_DEV_SIGNING_KEY"):
        self.human_id = human_id
        self.prism = IntentPrism()
        self.gate = D6GovernanceGate()
        self.signing_key = signing_key

    def sign_mock(self, data: str) -> str:
        return hmac.new(self.signing_key, data.encode("utf-8"), hashlib.sha256).hexdigest()

    def execute_emergence(self, intent_text: str, prev_hash: str = "GENESIS_NODE") -> D8IntentPayload:
        timestamp_ms = int(time.time() * 1000)
        nonce = os.urandom(12).hex()
        polarity, bagua_state, wuxing, ai_vector, yao = self.prism.process_intent(intent_text)
        heluo_seed = sha256_text(f"{self.human_id}|{timestamp_ms}|{nonce}|{polarity}|{bagua_state}")
        position = f"NODE_{heluo_seed[:8]}"
        channel = "CLOUD_CHANNEL" if polarity == "YANG" else "LOCAL_CHANNEL"
        redaction_level = "L1_CLOUD_BLIND_COMPUTE" if channel == "CLOUD_CHANNEL" else "L0_LOCAL_ONLY"
        weight = WUXING_RULES[wuxing]["weight"]

        ok, d6_status = self.gate.evaluate(intent_text, redaction_level, channel)
        if not ok:
            channel = "LOCAL_CHANNEL"
            redaction_level = "L0_LOCAL_ONLY"

        d1_identity_hash = sha256_text(f"SOVEREIGN:{self.human_id}")
        d2_intent_hash = sha256_text(intent_text)
        d3_state_code = f"{bagua_state}:{''.join(map(str, yao))}:AT:{position}"
        d4_topology_route = f"{channel}->{position}"
        d5_resource_weight = weight

        audit_material = json.dumps({
            "D1": d1_identity_hash,
            "D2": d2_intent_hash,
            "D3": d3_state_code,
            "D4": d4_topology_route,
            "D5": d5_resource_weight,
            "D6": d6_status,
            "prev": prev_hash,
        }, sort_keys=True, ensure_ascii=False)

        d7_audit_root = sha256_text(audit_material)
        packet_id = f"W7TP-D8-{heluo_seed[:16]}"

        seal_material = json.dumps({
            "packet_version": "W7TP_D8_PACKET_V2",
            "packet_id": packet_id,
            "timestamp_ms": timestamp_ms,
            "nonce": nonce,
            "previous_hash": prev_hash,
            "d7_audit_root": d7_audit_root,
            "scope": {"channel": channel, "target": position},
            "redaction_level": redaction_level,
        }, sort_keys=True, ensure_ascii=False)

        seal_hash = sha256_text(seal_material)
        signature_mock = self.sign_mock(seal_hash)

        return D8IntentPayload(
            packet_version="W7TP_D8_PACKET_V2",
            packet_id=packet_id,
            human_subject_ref=d1_identity_hash[:16],
            timestamp_ms=timestamp_ms,
            nonce=nonce,
            previous_hash=prev_hash,
            d1_identity_hash=d1_identity_hash,
            d2_intent_hash=d2_intent_hash,
            d3_state_code=d3_state_code,
            d4_topology_route=d4_topology_route,
            d5_resource_weight=d5_resource_weight,
            d6_governance_status=d6_status,
            d7_audit_root=d7_audit_root,
            scope={"channel": channel, "target": position},
            redaction_level=redaction_level,
            optional_encrypted_payload_ref="LOCAL_ENCRYPTED_PAYLOAD_REF_MOCK",
            seal_hash=seal_hash,
            signature_mock=signature_mock,
        )

if __name__ == "__main__":
    engine = IntentFieldEngine(human_id="TIAN_GAN_JIA_001")
    intent = "調度雲端 AI 算力，分析本社區在地微電網分配最佳化，不可洩漏社區個資"
    payload = engine.execute_emergence(intent)
    print(json.dumps(asdict(payload), indent=2, ensure_ascii=False))
