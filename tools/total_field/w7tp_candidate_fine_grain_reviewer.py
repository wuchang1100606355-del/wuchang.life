#!/usr/bin/env python3
"""Deterministic, local-only fine-grained reviewer for W7TP cloud candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DECISIONS = (
    "ACCEPT",
    "ACCEPT_WITH_CORRECTION",
    "HOLD_FOR_EVIDENCE",
    "REJECT_TECHNICAL_DRIFT",
    "REJECT_OVERCLAIM",
    "TRADE_SECRET_QUARANTINE",
)

TRADE_SECRET_RULES = {
    "WHY_IT_RUNS": (r"\bWHY_IT_RUNS\b",),
    "LOOKUP_EXPANSION_RULE": (r"查表展開規則", r"lookup expansion rule"),
    "WEIGHT_CONFIGURATION": (r"權重配置", r"weight configuration"),
    "ADI_INTERNAL_MAPPING": (r"ADI\s*(?:內部|internal)\s*(?:映射|mapping)",),
    "HEXAGRAM_INNER_MAPPING": (r"64\s*卦.*(?:內層映射|mapping)", r"hexagram.*inner mapping"),
    "PRIVATE_STATE_TRANSITION": (r"私有狀態轉換規則", r"private state transition rule"),
    "PRIVATE_RISK_WEIGHT": (r"(?:具體|private).*風險權重", r"private risk weight"),
    "SECRET_INNER_ALGORITHM": (r"封包內層秘密演算法", r"secret inner algorithm"),
}

DRIFT_RULES = {
    "FILE_MOVING_DEFINITION": (
        r"(?:generative transmission|生成式傳輸|W7TP).{0,35}(?:is|means|就是|等同於).{0,20}(?:complete file transfer|完整檔案搬運|cloud sync|雲端密文同步|backup|備份|download decryption|下載解密)",
    ),
    "CLOUD_FORMAL_AUTHORITY": (
        r"cloud.{0,35}(?:has|holds|owns|is).{0,25}(?:formal execution authority|正式執行權|canonical promotion authority|正典升格權)",
        r"雲端.{0,35}(?:具有|擁有|負責).{0,20}(?:正式執行權|正典升格權|放行權)",
    ),
    "SENDER_SELF_DECLARED_PASS": (
        r"sender.{0,30}(?:declare|assert).{0,12}\bPASS\b",
        r"發送端.{0,30}(?:自行宣告|宣告).{0,12}PASS",
    ),
    "XDP_FULL_8D_REASONING": (
        r"(?:XDP|eBPF|gNB).{0,35}(?:complete|full|direct).{0,15}8D.{0,20}(?:semantic|語意).{0,15}(?:reason|decision|裁決|推理)",
        r"(?:XDP|eBPF|gNB).{0,35}(?:直接|完整).{0,15}(?:完成|執行).{0,15}8D.{0,20}(?:語意推理|語意裁決)",
    ),
}

OVERCLAIM_RULES = {
    "ABSOLUTE_SAFETY": (r"絕對安全", r"absolutely secure", r"absolute security"),
    "PERFECT_CARRIER": (r"完美載體", r"perfect carrier"),
    "LIGHT_SPEED": (r"光速", r"speed of light"),
    "ZERO_CPU": (r"完全不消耗\s*CPU", r"zero CPU", r"no CPU consumption"),
    "ELIMINATES_ATTACKS": (r"徹底排除攻擊", r"eliminates all attacks"),
    "AUTOMATIC_LEGAL_EFFECT": (r"自動具司法效力", r"automatic legal effect"),
    "CERTAIN_PATENTABILITY": (r"必然具專利性", r"certainly patentable"),
}

EVIDENCE_RULES = {
    "PERFORMANCE_MEASUREMENT": (
        r"\b\d+(?:\.\d+)?\s*(?:microseconds?|milliseconds?|µs|us|ms|Gbps|Mbps|Kbps)\b",
        r"\b(?:throughput|latency|energy saving|collision rate)\b.{0,30}\d",
        r"\d+(?:\.\d+)?\s*(?:微秒|毫秒|吞吐|節能|碰撞率)",
    ),
    "STANDARDS_COMPLIANCE": (
        r"(?:complies? with|conforms? to|certified under).{0,30}(?:3GPP|ETSI|RFC\s*\d+)",
        r"(?:符合|通過).{0,20}(?:3GPP|ETSI|RFC\s*\d+|法規)",
    ),
    "LEGAL_EFFECT": (r"(?:司法|法律)(?:證據力|效力)", r"(?:judicial|legal) eviden(?:ce|tiary) effect"),
    "PATENTABILITY": (r"(?:已證明|具有).{0,12}(?:新穎性|進步性|專利性)", r"(?:proven|certain).{0,15}(?:novelty|inventive step|patentab)"),
}

CORRECTION_RULES = {
    "LOCAL_AUTHORITY_BOUNDARY": (r"\bCANDIDATE_ONLY\b", r"candidate authority", r"候選權限"),
    "SIX_BIT_TRUST_BOUNDARY": (r"6[- ]bit", r"6\s*位元"),
    "ZERO_RTT_BOUNDARY": (r"0-RTT",),
    "SHORT_HASH_BOUNDARY": (r"short hash", r"短\s*(?:hash|雜湊)"),
    "TPM_BOUNDARY": (r"\bTPM\b",),
    "MICROSD_BOUNDARY": (r"MicroSD",),
}

CORRECTIONS = {
    "ABSOLUTE_SAFETY": "安全性須由指定威脅模型、實測證據與本地總場裁決支持，不作絕對安全主張。",
    "PERFECT_CARRIER": "此承載方式僅列為候選實施選項，適用性須依本地條件與實測結果裁決。",
    "LIGHT_SPEED": "刪除光速措辭；延遲與吞吐僅能依可重現實測報告描述。",
    "ZERO_CPU": "刪除零 CPU 消耗措辭；資源成本須以實測數據表達。",
    "ELIMINATES_ATTACKS": "改為降低指定威脅模型中的部分風險，且不得取代本地硬風險閘門。",
    "AUTOMATIC_LEGAL_EFFECT": "證據鏈僅提供技術完整性材料，法律或司法效力須另行舉證與裁定。",
    "CERTAIN_PATENTABILITY": "僅列為專利候選邊界；新穎性、進步性與可專利性須經檢索及專業審查。",
    "LOCAL_AUTHORITY_BOUNDARY": "雲端輸出僅具 Candidate Authority；正式執行、正典升格與放行只由本地總場裁決。",
    "SIX_BIT_TRUST_BOUNDARY": "6-bit 狀態碼僅作可信路由索引，發送端不得自行宣告 PASS。",
    "ZERO_RTT_BOUNDARY": "QUIC 0-RTT 不得直接承載不可逆或高風險正式操作，仍須通過本地閘門。",
    "SHORT_HASH_BOUNDARY": "短 hash 僅作引用或快速索引；完整證據須保留足夠強度的 digest、MAC、簽章、hash chain 或 Merkle root。",
    "TPM_BOUNDARY": "TPM 僅適合週期性根摘要或量測封存，不適合逐包寫入完整證據。",
    "MICROSD_BOUNDARY": "普通 MicroSD 不得視為 WORM；唯加式保證須由可驗證的儲存控制提供。",
}

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(?P<label>\b(?:api[_ -]?key|token|password|secret|authorization)\b\s*[:=]\s*)(?P<value>[^\s,;]+)"
)
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)


@dataclass(frozen=True)
class ParsedCandidate:
    data: Any
    structure_type: str
    parse_method: str
    json_nested_parse_possible: bool
    markdown_fence_detected: bool
    truncated: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def redact_forbidden(text: str) -> tuple[str, bool]:
    redacted = PRIVATE_KEY_RE.sub("[REDACTED_FORBIDDEN_PRIVATE_KEY]", text)
    redacted = BEARER_RE.sub("Bearer [REDACTED_FORBIDDEN_CREDENTIAL]", redacted)

    def replace_assignment(match: re.Match[str]) -> str:
        value = match.group("value")
        if value.lower() in {"forbidden", "none", "no", "false", "required", "redacted"}:
            return match.group(0)
        return match.group("label") + "[REDACTED_FORBIDDEN_CREDENTIAL]"

    redacted = SECRET_ASSIGNMENT_RE.sub(replace_assignment, redacted)
    return redacted, redacted != text


def extract_balanced_json(text: str) -> str | None:
    first_nonspace = len(text) - len(text.lstrip())
    if first_nonspace < len(text) and text[first_nonspace] in "{[":
        starts = [(first_nonspace, text[first_nonspace])]
    else:
        starts = [(index, char) for index, char in enumerate(text) if char in "{["]
    for start, opening in starts:
        closing = "}" if opening == "{" else "]"
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
    return None


def decode_partial_json_string(text: str, start: int) -> str:
    body = text[start + 1 :]
    if body.endswith("\\"):
        body = body[:-1]
    try:
        return json.loads('"' + body + '"')
    except json.JSONDecodeError:
        return body.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def recover_truncated_top_level_object(text: str) -> dict[str, Any] | None:
    if not text.lstrip().startswith("{"):
        return None
    decoder = json.JSONDecoder()
    recovered: dict[str, Any] = {}
    key_re = re.compile(r'(?m)^  "((?:[^"\\]|\\.)+)"\s*:\s*')
    matches = list(key_re.finditer(text))
    for match in matches:
        key = json.loads('"' + match.group(1) + '"')
        value_start = match.end()
        try:
            value, _ = decoder.raw_decode(text, value_start)
        except json.JSONDecodeError:
            if value_start < len(text) and text[value_start] == '"':
                value = decode_partial_json_string(text, value_start)
            else:
                next_match = next((item for item in matches if item.start() > match.start()), None)
                end = next_match.start() if next_match else len(text)
                value = text[value_start:end].strip().rstrip(",")
        recovered[key] = value
    return recovered or None


def parse_candidate_content(value: Any) -> ParsedCandidate:
    if isinstance(value, (dict, list)):
        kind = "native_json_object" if isinstance(value, dict) else "native_json_array"
        return ParsedCandidate(value, kind, "native", True, False, False)
    if not isinstance(value, str):
        return ParsedCandidate(value, "scalar", "native", False, False, False)

    text = value.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    try:
        parsed = json.loads(text)
        kind = "json_string_containing_object" if isinstance(parsed, dict) else "json_string_containing_array"
        return ParsedCandidate(parsed, kind, "direct_json", True, False, False)
    except json.JSONDecodeError:
        pass

    if fence_match:
        try:
            parsed = json.loads(fence_match.group(1).strip())
            return ParsedCandidate(parsed, "markdown_code_fence_containing_json", "markdown_fenced_json", True, True, False)
        except json.JSONDecodeError:
            pass

    balanced = extract_balanced_json(text)
    if balanced:
        try:
            parsed = json.loads(balanced)
            return ParsedCandidate(parsed, "json_substring", "balanced_json_substring", True, bool(fence_match), False)
        except json.JSONDecodeError:
            pass

    recovered = recover_truncated_top_level_object(text)
    if recovered:
        return ParsedCandidate(
            recovered,
            "multi_section_mixed_structure",
            "truncated_json_top_level_recovery",
            False,
            bool(fence_match),
            True,
        )
    return ParsedCandidate(text, "single_long_text_report", "markdown_or_text_split", False, bool(fence_match), False)


def json_path(parent: str, key: Any) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]"
    if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$-]*", str(key)):
        return f"{parent}.{key}"
    return f"{parent}[{json.dumps(str(key), ensure_ascii=False)}]"


def split_long_block(text: str, limit: int = 480) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []
    sentences = [part.strip() for part in re.split(r"(?<=[。！？.!?;；])\s+|(?<=[。！？;；])", text) if part.strip()]
    if len(sentences) == 1:
        sentences = [part.strip() for part in re.split(r"\s+-\s+|\s*;\s*|\s*；\s*", text) if part.strip()]
    groups: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > limit:
            groups.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        groups.append(current)
    return groups or [text]


def split_report(text: str) -> list[tuple[str, str]]:
    lines = text.replace("\r\n", "\n").split("\n")
    if len(lines) == 1:
        return [("", part) for part in split_long_block(text)]
    pieces: list[tuple[str, str]] = []
    section = ""
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            block = " ".join(item.strip() for item in paragraph if item.strip())
            pieces.extend((section, part) for part in split_long_block(block))
            paragraph.clear()

    for line in lines:
        stripped = line.strip()
        heading = re.match(r"^#{1,6}\s+(.+)$", stripped)
        bullet = re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)(.+)$", stripped)
        table_row = stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2
        if heading:
            flush()
            section = heading.group(1).strip()
        elif bullet:
            flush()
            pieces.extend((section, part) for part in split_long_block(bullet.group(1)))
        elif table_row and not re.fullmatch(r"\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?", stripped):
            flush()
            pieces.extend((section, part) for part in split_long_block(stripped))
        elif not stripped:
            flush()
        else:
            paragraph.append(stripped)
    flush()
    return [(section, value) for section, value in pieces if value.strip()]


def matched_rules(text: str, rules: dict[str, tuple[str, ...]]) -> list[str]:
    matches = []
    for name, patterns in rules.items():
        if any(re.search(pattern, text, re.I | re.S) for pattern in patterns):
            matches.append(name)
    return matches


def clause_secret_split(text: str) -> list[tuple[str, str]]:
    if not matched_rules(text, TRADE_SECRET_RULES):
        return [("PUBLIC_SAFE_PART", text)]
    clauses = [part.strip() for part in re.split(r"(?<=[。！？.!?;；])\s*|\s*[;；]\s*", text) if part.strip()]
    if len(clauses) < 2:
        return [("TRADE_SECRET_PART", text)]
    secret = [part for part in clauses if matched_rules(part, TRADE_SECRET_RULES)]
    public = [part for part in clauses if not matched_rules(part, TRADE_SECRET_RULES)]
    if not public:
        return [("TRADE_SECRET_PART", text)]
    result = [("PUBLIC_SAFE_PART", part) for part in public]
    result.extend(("TRADE_SECRET_PART", part) for part in secret)
    return result


def is_negated_claim(text: str, rule: str) -> bool:
    if rule == "FILE_MOVING_DEFINITION":
        return bool(re.search(r"(?:not|不是|不得|不可|does not).{0,45}(?:file|檔案|sync|同步|backup|備份|download|下載)", text, re.I))
    if rule == "CLOUD_FORMAL_AUTHORITY":
        return bool(re.search(r"(?:only|僅|只).{0,25}(?:local|本地).{0,35}(?:authority|權)", text, re.I))
    if rule == "SENDER_SELF_DECLARED_PASS":
        return bool(re.search(r"(?:not|must not|cannot|不得|不可).{0,30}(?:sender|發送端).{0,35}PASS|(?:sender|發送端).{0,30}(?:not|不得|不可).{0,20}PASS", text, re.I))
    if rule == "XDP_FULL_8D_REASONING":
        return bool(re.search(r"(?:not|does not|must not|cannot|不得|不可|不負責).{0,45}(?:XDP|eBPF|gNB|8D)|(?:XDP|eBPF|gNB).{0,45}(?:not|does not|不得|不可|不負責)", text, re.I))
    return False


def infer_topic(path: str, section: str, text: str) -> str:
    haystack = f"{path} {section} {text}".lower()
    topics = (
        ("xdp_af_xdp", ("xdp", "af_xdp", "ebpf")),
        ("quic_tcp_udp", ("quic", "tcp", "udp")),
        ("mec_5gc", ("mec", "5gc", "upf", "nef", "pcf", "s-nssai", "dnai")),
        ("constrained_iot", ("iot", "mqtt", "coap", "lorawan", "nb-iot")),
        ("evidence_chain", ("evidence", "merkle", "hash chain", "tpm", "worm")),
        ("reconstruction_verification", ("reconstruct", "重構", "equivalent state", "等價狀態", "lookup", "查表")),
        ("transport_envelope", ("envelope", "schema", "packet", "封包")),
        ("local_execution_gate", ("local total field", "formal execution", "本地總場", "執行閘門")),
        ("ip_boundary", ("patent", "trade_secret", "public_safe", "intellectual property")),
        ("implementation_layer", ("layer", "architecture", "roadmap", "implementation")),
    )
    for topic, needles in topics:
        if any(needle in haystack for needle in needles):
            return topic
    return "general_technical_candidate"


def infer_claimed_status(text: str) -> str:
    if re.search(r"\b(?:proven|verified|certified|measured)\b|已證明|已驗證|實測", text, re.I):
        return "ASSERTED_FACT"
    if re.search(r"\b(?:candidate|proposed|proposal|may|could|recommend)\b|候選|建議|可考慮", text, re.I):
        return "CANDIDATE_PROPOSAL"
    return "TECHNICAL_STATEMENT"


def evidence_references(text: str) -> list[str]:
    refs = re.findall(r"\b(?:RFC\s*\d+|3GPP(?:\s+TS\s*[\d.]+)?|ETSI(?:\s+[A-Z0-9.-]+)?|[a-f0-9]{64})\b", text, re.I)
    return sorted(set(refs), key=str.lower)


def dependency_references(text: str) -> list[str]:
    refs = re.findall(r"(?:#/[A-Za-z0-9_./-]+|\b(?:template_id|policy_version|schema_version|reference_keys|key_id)\b)", text)
    return sorted(set(refs))


def correction_for(rules: Iterable[str]) -> str:
    corrections = [CORRECTIONS[rule] for rule in rules if rule in CORRECTIONS]
    return " ".join(dict.fromkeys(corrections))


def decide_unit(text: str, secret_part: str, credential_redacted: bool) -> dict[str, Any]:
    trade = matched_rules(text, TRADE_SECRET_RULES)
    drift = [rule for rule in matched_rules(text, DRIFT_RULES) if not is_negated_claim(text, rule)]
    overclaim = matched_rules(text, OVERCLAIM_RULES)
    evidence = matched_rules(text, EVIDENCE_RULES)
    correction = matched_rules(text, CORRECTION_RULES)
    all_rules = {
        "hard_risk": ["FORBIDDEN_CREDENTIAL_REDACTED"] if credential_redacted else [],
        "trade_secret": trade,
        "technical_drift": drift,
        "overclaim": overclaim,
        "evidence": evidence,
        "correction": correction,
    }

    if credential_redacted:
        decision = "HOLD_FOR_EVIDENCE"
        reason = "Forbidden credential-shaped content was redacted and requires manual local confirmation."
        evidence_required = ["Manual local confirmation that no raw credential or private data enters review artifacts."]
        correction_text = ""
    elif trade or secret_part == "TRADE_SECRET_PART":
        decision = "TRADE_SECRET_QUARANTINE"
        reason = "The minimum technical unit matches a private implementation boundary and is excluded from public canonical material."
        evidence_required = []
        correction_text = ""
    elif drift:
        decision = "REJECT_TECHNICAL_DRIFT"
        reason = "The unit directly conflicts with the W7TP protocol-native packet and local-authority boundary."
        evidence_required = []
        correction_text = ""
    elif overclaim:
        correctable_direction = bool(
            re.search(r"\b(?:QUIC|TCP|UDP|XDP|eBPF|AF_XDP|TPM|MEC|5GC|MQTT|CoAP)\b", text, re.I)
        )
        decision = "ACCEPT_WITH_CORRECTION" if correctable_direction else "REJECT_OVERCLAIM"
        reason = (
            "The technical direction may be retained only after removing absolute or unverified wording."
            if correctable_direction
            else "The unit is an unsupported absolute claim and cannot enter the canonical candidate."
        )
        evidence_required = []
        correction_text = correction_for(overclaim) if correctable_direction else ""
    elif evidence:
        decision = "HOLD_FOR_EVIDENCE"
        reason = "The unit contains a performance, compliance, legal-effect, or patentability claim that needs evidence."
        evidence_required = [f"Reproducible primary evidence for {rule}." for rule in evidence]
        correction_text = ""
    elif correction:
        decision = "ACCEPT_WITH_CORRECTION"
        reason = "The unit is directionally compatible but must state the applicable local gate or implementation boundary."
        evidence_required = []
        correction_text = correction_for(correction)
    else:
        decision = "ACCEPT"
        reason = "No hard risk, trade-secret marker, technical drift, overclaim, or evidence-dependent assertion was found in this unit."
        evidence_required = []
        correction_text = ""
    return {
        "decision": decision,
        "reason": reason,
        "matched_rules": all_rules,
        "correction_text": correction_text,
        "evidence_required": evidence_required,
    }


def build_unit(path: str, section: str, parent_context: str, text: str, exposure_part: str) -> dict[str, Any]:
    redacted, credential_redacted = redact_forbidden(text)
    normalized = normalize_space(redacted)
    decision = decide_unit(normalized, exposure_part, credential_redacted)
    identifier_material = "\0".join((path, section, parent_context, exposure_part, normalized))
    unit_id = "W7TP-" + hashlib.sha256(identifier_material.encode("utf-8")).hexdigest()[:16].upper()
    public_level = "TRADE_SECRET" if decision["decision"] == "TRADE_SECRET_QUARANTINE" else "PUBLIC_SAFE"
    lower_path = path.lower()
    if public_level == "PUBLIC_SAFE" and "patent" in lower_path:
        public_level = "PATENT_CANDIDATE"
    elif public_level == "PUBLIC_SAFE" and any(word in lower_path for word in ("implementation", "roadmap")):
        public_level = "IMPLEMENTATION_ONLY"
    return {
        "unit_id": unit_id,
        "source_path": path,
        "source_section": section,
        "parent_context": parent_context,
        "raw_text": redacted,
        "normalized_text": normalized,
        "semantic_topic": infer_topic(path, section, normalized),
        "claimed_status": infer_claimed_status(normalized),
        "evidence_refs": evidence_references(normalized),
        "public_exposure_level": public_level,
        "exposure_part": exposure_part,
        "dependency_refs": dependency_references(normalized),
        **decision,
    }


def extract_units(data: Any, root_path: str = "$.candidate.raw_candidate_text") -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []

    def visit(value: Any, path: str, section: str, parents: list[str]) -> None:
        if isinstance(value, dict):
            for key in sorted(value, key=str):
                visit(value[key], json_path(path, key), section or str(key), parents + [str(key)])
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, json_path(path, index), section, parents + [f"item_{index}"])
            return
        if value is None:
            return
        text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        nested = parse_candidate_content(text) if isinstance(value, str) and text.strip().startswith(("{", "[", "```")) else None
        if nested and nested.parse_method in {"direct_json", "markdown_fenced_json", "balanced_json_substring", "truncated_json_top_level_recovery"}:
            visit(nested.data, path, section, parents)
            return
        parent_context = " > ".join(parents[-4:])
        for report_section, piece in split_report(text):
            effective_section = report_section or section or (parents[-1] if parents else "candidate")
            for exposure_part, clause in clause_secret_split(piece):
                if clause.strip():
                    units.append(build_unit(path, effective_section, parent_context, clause, exposure_part))

    visit(data, root_path, "", [])
    units.sort(key=lambda item: (item["source_path"], item["source_section"], item["unit_id"]))
    return units


def analyze_candidate(candidate: Any, root_path: str = "$.candidate") -> tuple[ParsedCandidate, list[dict[str, Any]]]:
    parsed = parse_candidate_content(candidate)
    return parsed, extract_units(parsed.data, root_path)


def structural_counts(value: Any) -> tuple[int, int, int]:
    list_items = 0
    dict_nodes = 0
    scalar_nodes = 0

    def visit(item: Any) -> None:
        nonlocal list_items, dict_nodes, scalar_nodes
        if isinstance(item, dict):
            dict_nodes += 1
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            list_items += len(item)
            for child in item:
                visit(child)
        else:
            scalar_nodes += 1

    visit(value)
    return list_items, dict_nodes, scalar_nodes


def section_count(value: Any) -> int:
    count = len(value) if isinstance(value, dict) else len(value) if isinstance(value, list) else 0
    strings: list[str] = []

    def collect(item: Any) -> None:
        if isinstance(item, dict):
            for child in item.values():
                collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)
        elif isinstance(item, str):
            strings.append(item)

    collect(value)
    count += sum(len(re.findall(r"(?m)^#{1,6}\s+", text)) for text in strings)
    return count


def select_candidate(normalized: Any) -> tuple[Any, str, str]:
    if isinstance(normalized, dict) and "candidate" in normalized:
        candidate = normalized["candidate"]
        candidate_type = type(candidate).__name__
        if isinstance(candidate, dict) and "raw_candidate_text" in candidate:
            return candidate["raw_candidate_text"], "$.candidate.raw_candidate_text", candidate_type
        return candidate, "$.candidate", candidate_type
    return normalized, "$", type(normalized).__name__


def raw_candidate_text(raw: Any) -> str:
    if isinstance(raw, dict) and isinstance(raw.get("candidate_text"), str):
        return raw["candidate_text"]
    return json.dumps(raw, ensure_ascii=False, sort_keys=True)


def canonical_unit(unit: dict[str, Any]) -> dict[str, str]:
    text = unit["correction_text"] if unit["decision"] == "ACCEPT_WITH_CORRECTION" else unit["normalized_text"]
    return {"unit_id": unit["unit_id"], "semantic_topic": unit["semantic_topic"], "text": text}


def select_canonical(units: list[dict[str, Any]], topics: set[str] | None = None) -> list[dict[str, str]]:
    selected = [unit for unit in units if unit["decision"] in {"ACCEPT", "ACCEPT_WITH_CORRECTION"}]
    if topics is not None:
        selected = [unit for unit in selected if unit["semantic_topic"] in topics]
    return [canonical_unit(unit) for unit in selected]


def markdown_units(title: str, units: list[dict[str, Any]], include_text: bool = True) -> str:
    lines = [f"# {title}", "", "本文件為本地細粒度候選審查輸出，仍需 OWNER SEAL。", ""]
    if not units:
        lines.extend(["無符合項目。", ""])
        return "\n".join(lines)
    for unit in units:
        lines.append(f"## {unit['unit_id']}")
        lines.append("")
        lines.append(f"- Source: `{unit['source_path']}`")
        lines.append(f"- Decision: `{unit['decision']}`")
        lines.append(f"- Topic: `{unit['semantic_topic']}`")
        if include_text:
            text = unit["correction_text"] if unit["decision"] == "ACCEPT_WITH_CORRECTION" else unit["normalized_text"]
            lines.extend(["", text])
        lines.append("")
    return "\n".join(lines)


def run_id_created_at(run_id: str) -> str:
    match = re.search(r"(\d{8})_(\d{6})$", run_id)
    if not match:
        return "UNSPECIFIED_DETERMINISTIC_RUN_TIME"
    date, clock = match.groups()
    return f"{date[:4]}-{date[4:6]}-{date[6:]}T{clock[:2]}:{clock[2:4]}:{clock[4:]}Z"


def validate_output_json(output_dir: Path) -> None:
    for path in output_dir.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def write_outputs(
    source_path: Path,
    raw_path: Path,
    normalized_path: Path,
    output_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    source = json.loads(source_path.read_text(encoding="utf-8"))
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    candidate, candidate_path, candidate_field_type = select_candidate(normalized)
    parsed, units = analyze_candidate(candidate, candidate_path)
    raw_text = raw_candidate_text(raw)
    list_items, dict_nodes, scalar_nodes = structural_counts(parsed.data)
    source_hash = sha256_file(source_path)
    raw_hash = sha256_file(raw_path)
    normalized_hash = sha256_file(normalized_path)
    created_at = run_id_created_at(run_id)

    counts = {decision: sum(unit["decision"] == decision for unit in units) for decision in DECISIONS}
    diagnosis = {
        "schema": "w7tp_candidate_structure_diagnosis_v1",
        "run_id": run_id,
        "top_level_type": type(normalized).__name__,
        "top_level_keys": list(normalized) if isinstance(normalized, dict) else [],
        "candidate_field_type": candidate_field_type,
        "adjudicated_candidate_path": candidate_path,
        "raw_candidate_text_length": len(raw_text),
        "json_nested_parse_possible": parsed.json_nested_parse_possible,
        "parse_method": parsed.parse_method,
        "structure_type": parsed.structure_type,
        "truncated_input_detected": parsed.truncated,
        "markdown_fence_detected": parsed.markdown_fence_detected,
        "section_count": section_count(parsed.data),
        "list_item_count": list_items,
        "dict_node_count": dict_nodes,
        "scalar_node_count": scalar_nodes,
        "old_review_granularity_failure_cause": "The old reviewer flattened the complete nested raw_candidate_text string into one adjudication item; one local trade-secret marker therefore set a whole-document quarantine decision.",
        "exact_path_causing_whole_document_quarantine": "$.candidate.raw_candidate_text",
        "old_review_recorded_path": "raw_candidate_text",
        "whether_trade_secret_match_was_local_or_global": "LOCAL_MATCH_WITH_GLOBAL_EFFECT_DUE_TO_WHOLE_DOCUMENT_FLATTENING",
    }

    normalized_artifact = {
        "schema": "w7tp_normalized_fine_grain_candidate_v1",
        "run_id": run_id,
        "source_candidate_path": candidate_path,
        "structure_type": parsed.structure_type,
        "parse_method": parsed.parse_method,
        "truncated_input_detected": parsed.truncated,
        "normalized_unit_count": len(units),
        "normalized_units": [
            {
                "unit_id": unit["unit_id"],
                "source_path": unit["source_path"],
                "source_section": unit["source_section"],
                "parent_context": unit["parent_context"],
                "normalized_text": unit["normalized_text"],
                "exposure_part": unit["exposure_part"],
            }
            for unit in units
        ],
    }
    review_artifact = {"schema": "w7tp_fine_grain_review_units_v1", "run_id": run_id, "review_unit_count": len(units), "units": units}
    comparison = {
        "schema": "w7tp_total_field_fine_grain_comparison_v1",
        "run_id": run_id,
        "created_at": created_at,
        "source_packet": str(source_path),
        "cloud_raw_candidate": str(raw_path),
        "cloud_normalized_candidate": str(normalized_path),
        "source_packet_sha256": source_hash,
        "cloud_raw_sha256": raw_hash,
        "cloud_normalized_sha256": normalized_hash,
        "review_unit_count": len(units),
        "counts": counts,
        "global_quarantine_bug_fixed": len(units) > 1 and counts["TRADE_SECRET_QUARANTINE"] < len(units),
        "decision_order": [
            "HARD_RISK",
            "TRADE_SECRET_QUARANTINE",
            "REJECT_TECHNICAL_DRIFT",
            "REJECT_OVERCLAIM",
            "HOLD_FOR_EVIDENCE",
            "ACCEPT_WITH_CORRECTION",
            "ACCEPT",
        ],
        "decisions": [{"unit_id": unit["unit_id"], "source_path": unit["source_path"], "decision": unit["decision"], "reason": unit["reason"]} for unit in units],
    }

    by_decision = {decision: [unit for unit in units if unit["decision"] == decision] for decision in DECISIONS}
    accepted_files = {
        "ACCEPTED_TECHNICAL_UNITS.json": ("w7tp_accepted_technical_units_v1", by_decision["ACCEPT"]),
        "CORRECTED_TECHNICAL_UNITS.json": ("w7tp_corrected_technical_units_v1", by_decision["ACCEPT_WITH_CORRECTION"]),
        "HELD_FOR_EVIDENCE_UNITS.json": ("w7tp_held_for_evidence_units_v1", by_decision["HOLD_FOR_EVIDENCE"]),
        "REJECTED_TECHNICAL_DRIFT_UNITS.json": ("w7tp_rejected_technical_drift_units_v1", by_decision["REJECT_TECHNICAL_DRIFT"]),
        "REJECTED_OVERCLAIM_UNITS.json": ("w7tp_rejected_overclaim_units_v1", by_decision["REJECT_OVERCLAIM"]),
        "TRADE_SECRET_QUARANTINE_UNITS.json": ("w7tp_trade_secret_quarantine_units_v1", by_decision["TRADE_SECRET_QUARANTINE"]),
    }

    canonical = {
        "schema": "w7tp_communication_canonical_v2_candidate_v1",
        "run_id": run_id,
        "technical_definition": "W7TP 生成式傳輸是 protocol-native 8D intent-field packet，透過狀態場封包、引用、查表鍵、重構條件、等價狀態生成與本地總場驗證產生封包所需結果。",
        "immutable_boundaries": [
            "不是完整檔案搬運、雲端同步、備份、下載解密或一般檔案壓縮。",
            "雲端僅具 Candidate Authority；正式執行、正典升格與放行只屬本地總場。",
            "真實硬風險不可由其他維度抵銷。",
            "只重構封包需要的部分，並達到封包要求的驗證層級。",
        ],
        "accepted_architecture": select_canonical(units, {"implementation_layer", "transport_envelope", "general_technical_candidate"}),
        "accepted_with_corrections": [canonical_unit(unit) for unit in by_decision["ACCEPT_WITH_CORRECTION"]],
        "implementation_layers": select_canonical(units, {"implementation_layer"}),
        "transport_envelope_schema_candidate": select_canonical(units, {"transport_envelope"}),
        "reconstruction_and_verification_flow": select_canonical(units, {"reconstruction_verification"}),
        "local_execution_gate": select_canonical(units, {"local_execution_gate"}),
        "hard_risk_gate": {"rule": "R_hard(packet)=1 => HOLD | BLOCK | MANUAL_CONFIRM", "local_authority_only": True},
        "evidence_chain": select_canonical(units, {"evidence_chain"}),
        "xdp_af_xdp_boundary": select_canonical(units, {"xdp_af_xdp"}),
        "quic_tcp_udp_mapping": select_canonical(units, {"quic_tcp_udp"}),
        "mec_5gc_mapping": select_canonical(units, {"mec_5gc"}),
        "constrained_iot_mapping": select_canonical(units, {"constrained_iot"}),
        "public_safe_boundary": select_canonical(units),
        "patent_candidate_boundary": [canonical_unit(unit) for unit in units if unit["decision"] in {"ACCEPT", "ACCEPT_WITH_CORRECTION"} and unit["public_exposure_level"] == "PATENT_CANDIDATE"],
        "trade_secret_boundary": {"content_included": False, "excluded_unit_ids": [unit["unit_id"] for unit in by_decision["TRADE_SECRET_QUARANTINE"]]},
        "held_evidence_items": [{"unit_id": unit["unit_id"], "reason": unit["reason"], "evidence_required": unit["evidence_required"]} for unit in by_decision["HOLD_FOR_EVIDENCE"]],
        "rejected_items": [{"unit_id": unit["unit_id"], "decision": unit["decision"], "reason": unit["reason"]} for unit in units if unit["decision"].startswith("REJECT_")],
        "source_hashes": {"source_packet_sha256": source_hash, "cloud_raw_sha256": raw_hash, "cloud_normalized_sha256": normalized_hash},
        "cloud_candidate_hash": raw_hash,
        "review_method": "Deterministic local tolerant parse, hierarchical fine-grain split, minimum-unit secret isolation, and ordered Total Field adjudication.",
        "status": "OWNER_SEAL_REQUIRED",
    }

    verdict = {
        "schema": "w7tp_fine_grain_final_local_verdict_v1",
        "state": "PASS_FINE_GRAIN_LOCAL_REVIEW_COMPLETED",
        "run_id": run_id,
        "review_unit_count": len(units),
        "counts": counts,
        "global_quarantine_bug_fixed": comparison["global_quarantine_bug_fixed"],
        "canonical_v2_candidate": "W7TP_COMMUNICATION_CANONICAL_V2_CANDIDATE.json",
        "owner_seal_required": True,
        "new_cloud_request": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "formal_submission": False,
        "next": "OWNER_REVIEW_AND_SEAL_OR_RETURN_CORRECTIONS",
    }

    json_dump(output_dir / "CANDIDATE_STRUCTURE_DIAGNOSIS.json", diagnosis)
    json_dump(output_dir / "NORMALIZED_FINE_GRAIN_CANDIDATE.json", normalized_artifact)
    json_dump(output_dir / "FINE_GRAIN_REVIEW_UNITS.json", review_artifact)
    json_dump(output_dir / "TOTAL_FIELD_FINE_GRAIN_COMPARISON.json", comparison)
    for filename, (schema, selected) in accepted_files.items():
        json_dump(output_dir / filename, {"schema": schema, "run_id": run_id, "count": len(selected), "units": selected})

    public_units = [unit for unit in units if unit["decision"] in {"ACCEPT", "ACCEPT_WITH_CORRECTION"} and unit["public_exposure_level"] == "PUBLIC_SAFE"]
    implementation_units = [unit for unit in units if unit["decision"] in {"ACCEPT", "ACCEPT_WITH_CORRECTION"} and unit["semantic_topic"] in {"implementation_layer", "xdp_af_xdp", "quic_tcp_udp", "mec_5gc", "constrained_iot"}]
    patent_units = [unit for unit in units if unit["decision"] in {"ACCEPT", "ACCEPT_WITH_CORRECTION"} and unit["public_exposure_level"] == "PATENT_CANDIDATE"]
    (output_dir / "PUBLIC_SAFE_ARCHITECTURE.md").write_text(markdown_units("W7TP Public-Safe Architecture Candidate", public_units), encoding="utf-8")
    (output_dir / "IMPLEMENTATION_ARCHITECTURE.md").write_text(markdown_units("W7TP Implementation Architecture Candidate", implementation_units), encoding="utf-8")
    (output_dir / "PATENT_CANDIDATE_BOUNDARY.md").write_text(markdown_units("W7TP Patent Candidate Boundary", patent_units), encoding="utf-8")
    (output_dir / "TRADE_SECRET_BOUNDARY.md").write_text(markdown_units("W7TP Trade Secret Boundary", by_decision["TRADE_SECRET_QUARANTINE"], include_text=False), encoding="utf-8")
    json_dump(output_dir / "W7TP_COMMUNICATION_CANONICAL_V2_CANDIDATE.json", canonical)

    canonical_md_units = [unit for unit in units if unit["decision"] in {"ACCEPT", "ACCEPT_WITH_CORRECTION"}]
    canonical_md = markdown_units("W7TP Communication Canonical V2 Candidate", canonical_md_units)
    canonical_md += "\n## Status\n\n`OWNER_SEAL_REQUIRED`\n"
    (output_dir / "W7TP_COMMUNICATION_CANONICAL_V2_CANDIDATE.md").write_text(canonical_md, encoding="utf-8")
    json_dump(output_dir / "FINAL_LOCAL_VERDICT.json", verdict)
    verdict_md = (
        "# Final Local Verdict\n\n"
        f"- State: `{verdict['state']}`\n"
        f"- Review units: `{len(units)}`\n"
        f"- Global quarantine bug fixed: `{str(comparison['global_quarantine_bug_fixed']).upper()}`\n"
        "- Status: `OWNER_SEAL_REQUIRED`\n"
        "- New cloud request: `NO`\n"
        "- DB write / deploy / restart / router write / formal submission: `NO`\n\n"
        "## Counts\n\n"
        + "\n".join(f"- {key}: `{value}`" for key, value in counts.items())
        + "\n"
    )
    (output_dir / "FINAL_LOCAL_VERDICT.md").write_text(verdict_md, encoding="utf-8")

    payload_files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    payload_hashes = {name: sha256_file(output_dir / name) for name in payload_files}
    manifest = {
        "schema": "w7tp_fine_grain_review_manifest_v1",
        "run_id": run_id,
        "files": payload_files + ["MANIFEST.json", "SHA256SUMS"],
        "hashes": payload_hashes,
        "source_hashes": canonical["source_hashes"],
    }
    json_dump(output_dir / "MANIFEST.json", manifest)
    checksum_names = sorted(payload_files + ["MANIFEST.json"])
    checksum_text = "".join(f"{sha256_file(output_dir / name)}  {name}\n" for name in checksum_names)
    (output_dir / "SHA256SUMS").write_text(checksum_text, encoding="utf-8")
    validate_output_json(output_dir)

    return {
        "source_packet_sha256": source_hash,
        "cloud_raw_sha256": raw_hash,
        "cloud_normalized_sha256": normalized_hash,
        "structure_type": parsed.structure_type,
        "review_unit_count": len(units),
        "counts": counts,
        "global_quarantine_bug_fixed": comparison["global_quarantine_bug_fixed"],
        "canonical": output_dir / "W7TP_COMMUNICATION_CANONICAL_V2_CANDIDATE.json",
        "verdict": output_dir / "FINAL_LOCAL_VERDICT.json",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-packet", required=True, type=Path)
    parser.add_argument("--cloud-raw", required=True, type=Path)
    parser.add_argument("--cloud-normalized", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = write_outputs(
            args.source_packet,
            args.cloud_raw,
            args.cloud_normalized,
            args.output_dir,
            args.run_id,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    counts = result["counts"]
    print(f"RUN_ID={args.run_id}")
    print(f"SOURCE_PACKET_SHA256={result['source_packet_sha256']}")
    print(f"CLOUD_RAW_SHA256={result['cloud_raw_sha256']}")
    print(f"CLOUD_NORMALIZED_SHA256={result['cloud_normalized_sha256']}")
    print(f"STRUCTURE_TYPE={result['structure_type']}")
    print(f"REVIEW_UNIT_COUNT={result['review_unit_count']}")
    for decision in DECISIONS:
        print(f"{decision}_COUNT={counts[decision]}")
    print(f"GLOBAL_QUARANTINE_BUG_FIXED={'YES' if result['global_quarantine_bug_fixed'] else 'NO'}")
    print(f"CANONICAL_V2_CANDIDATE={result['canonical']}")
    print(f"FINAL_LOCAL_VERDICT={result['verdict']}")
    print(f"OUT={args.output_dir}")
    print("OWNER_SEAL_REQUIRED=YES")
    print("NEW_CLOUD_REQUEST=NO")
    print("DB_WRITE=NO")
    print("DEPLOY=NO")
    print("RESTART=NO")
    print("ROUTER_WRITE=NO")
    print("FORMAL_SUBMISSION=NO")
    print("NEXT=OWNER_REVIEW_AND_SEAL_OR_RETURN_CORRECTIONS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
