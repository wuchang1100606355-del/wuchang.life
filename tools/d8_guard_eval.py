#!/usr/bin/env python3
import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RANK = {"PASS": 0, "INFO": 1, "WARN": 2, "HOLD": 3, "BLOCK": 4}
LEGACY_GTP_CANONICAL_V2 = "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
LEGACY_GTP_CANONICAL_V2_SHA256 = "a5281f229ced0943072cce373125be16f0d361b9352a71094ad5450a6022d5d0"
ACTIVE_GTP_CANONICAL = "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728.md"
ACTIVE_GTP_CANONICAL_SHA256 = "383aba5b7a9f5d0e948d9b43b83e7dd6b6ec9c27f025fb9069e83810f0ae870d"
GTP_TECHNICAL_DRIFT_ALERT_ID = "D8_WRITEBACK_ALERT_GTP_TECHNICAL_DEFINITION_DRIFT"
GTP_TECHNICAL_DRIFT_RULES = {
    "GTP-TD-001": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:24",
        "correction": "Restore the packet-native state, reference, lookup, reconstruction, verification, and equivalence definition.",
    },
    "GTP-TD-002": {
        "severity": "HOLD",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:24,105-134,323",
        "correction": "Supply every missing state-coordinate, reference, reconstruction-condition, packet-protocol, and verification operand before claiming completion.",
    },
    "GTP-TD-003": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:54-71,362",
        "correction": "Preserve D1-D8 as eight fixed governance dimensions of one packet instead of eight flat fields.",
    },
    "GTP-TD-004": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:35,120-134,327",
        "correction": "Restore the model-free deterministic lookup, integer transition, rule, reference, coordinate, and Total Field verification branch.",
    },
    "GTP-TD-005": {
        "severity": "HOLD",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:113,286,352",
        "correction": "Downclass the update claim until an exact receipt and its source evidence are present.",
    },
    "GTP-TD-006": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:149-180,273-287",
        "correction": "Use a deterministic discrete intent-state equivalence contract and retain Total Field PASS/HOLD/BLOCK authority.",
    },
    "GTP-TD-007": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:34-42",
        "correction": "Restore Intent Communication and State-Field Packet Communication; semantic models remain candidate parsers only.",
    },
    "GTP-TD-008": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:165-180",
        "correction": "Restore the distinct local irreversible ADI packet index and user-owned lineage-based spatiotemporal state index network.",
    },
    "GTP-TD-009": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}:182-192",
        "correction": "Replace protected H64-TD, codebook, mapping, or recovery material with a governed reference only.",
    },
    "GTP-TD-010": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}#lock-10",
        "correction": "Restore ten claims as the current filing package and classify the 2026-06-22 V04 twenty-one claims as superseded draft evidence.",
    },
    "GTP-TD-011": {
        "severity": "BLOCK",
        "canonical_reference": f"{ACTIVE_GTP_CANONICAL}#lock-12",
        "correction": "Create an append-only successor state or packet with explicit parent, hash, nonce, evidence, or signature lineage.",
    },
}

_GTP_SUBJECT = re.compile(r"(?:\b(?:w7tp|gtp)\b|generative transmission|生成式傳輸)", re.IGNORECASE)
_TRANSFER_DRIFT = re.compile(
    r"(?:檔案搬運|搬檔|檔案傳輸|雲端同步|密文同步|同步|備份|壓縮|下載(?:後)?解密|"
    r"file (?:moving|movement|transfer)|moving files|cloud sync|ciphertext sync|backup|compression|download(?:-side)? decryption)",
    re.IGNORECASE,
)
_TRANSFER_ASSERTION = re.compile(
    r"(?:就是|等同(?:於)?|等於|視為|當作|定義為|\b(?:is|means|equals|same as|equivalent to|implemented as)\b)",
    re.IGNORECASE,
)
_TRANSFER_DENIAL = re.compile(
    r"(?:不是|並非|不等同|不屬於|不得.{0,32}(?:等同|視為|曲解|定義)|禁止.{0,32}(?:等同|視為|曲解|定義)|"
    r"\b(?:is not|not equivalent|not part of|must not|never|do not define|does not claim|cannot be)\b)",
    re.IGNORECASE,
)
_COMPLETION_CLAIM = re.compile(
    r"(?:\b(?:w7tp|gtp)\b|生成式傳輸).{0,96}"
    r"(?:已完成|完成(?:了)?|已落地|已啟用|\bPASS\b|\bready\b|\bcomplete(?:d)?\b|\blanded\b|\boperational\b)",
    re.IGNORECASE,
)
_COMPLETION_DENIAL = re.compile(
    r"(?:未完成|尚未完成|不代表.{0,20}(?:完成|PASS)|假\s*PASS|false\s+pass|"
    r"不得.{0,24}宣稱|禁止.{0,24}宣稱|\bnot complete\b|\bnot yet complete\b|\bmust not claim\b)",
    re.IGNORECASE,
)
_FLAT_8D = re.compile(
    r"(?:8D.{0,40}(?:就是|等同(?:於)?|等於|視為|扁平化為|\b(?:is|means|equals)\b).{0,32}"
    r"(?:八個(?:平面)?欄位|eight flat fields|eight fields|8 fields)|"
    r"(?:扁平化|flatten).{0,24}8D.{0,24}(?:欄位|fields))",
    re.IGNORECASE,
)
_FLAT_8D_DENIAL = re.compile(
    r"(?:不是.{0,32}(?:八個(?:平面)?欄位|eight fields)|不得.{0,32}(?:扁平|欄位)|"
    r"\b(?:is not|must not|do not)\b.{0,32}(?:eight fields|flatten))",
    re.IGNORECASE,
)
_MODEL_OPERATOR = re.compile(
    r"(?:\bLLM\b|\bdiffusion\b|embedding|cosine|語意相似|semantic similarity|"
    r"浮點(?:語意)?向量|floating[- ]point vector|float(?:ing)? vector|向量相似)",
    re.IGNORECASE,
)
_MODEL_REPLACEMENT = re.compile(
    r"(?:取代|替代|代替|作為.{0,16}核心|核心.{0,16}(?:使用|採用)|"
    r"\b(?:replace|instead of|uses?|depends on|core operator)\b)",
    re.IGNORECASE,
)
_MODEL_DENIAL = re.compile(
    r"(?:不得|禁止|不可|不能|不使用|無需使用|\b(?:must not|does not use|do not use|cannot replace|without using)\b)",
    re.IGNORECASE,
)
_UPDATE_TARGET = re.compile(r"(?:正典|\bcanonical\b|\bruntime\b|記憶|\bmemory\b|權威|\bauthority\b)", re.IGNORECASE)
_UPDATE_CLAIM = re.compile(
    r"(?:已更新|更新完成|已錨定|錨定完成|已升格|已啟用|已寫入|"
    r"\b(?:updated|anchored|landed|promoted|activated|written)\b)",
    re.IGNORECASE,
)
_UPDATE_DENIAL = re.compile(
    r"(?:未更新|尚未更新|不得.{0,24}宣稱|禁止.{0,24}宣稱|"
    r"\b(?:not updated|not anchored|not landed|must not claim|cannot claim)\b)",
    re.IGNORECASE,
)
_RECEIPT = re.compile(r"(?:回執|\breceipt\b)", re.IGNORECASE)
_SEMANTIC_AUTHORITY_CONTEXT = re.compile(
    r"(?:\b(?:w7tp|gtp)\b|generative transmission|生成式傳輸|"
    r"semantic-state equivalent|semantic-state-equivalent|語意狀態等價)",
    re.IGNORECASE,
)
_SEMANTIC_AUTHORITY_OPERATOR = re.compile(
    r"(?:\bLLM\b|embedding|向量資料庫|vector database|cosine similarity|模糊匹配|fuzzy matching|"
    r"機率(?:分數|閾值)?|probability score|probabilistic threshold|浮點語意評分|floating semantic score|"
    r"生成模型|generative model)",
    re.IGNORECASE,
)
_SEMANTIC_AUTHORITY_ELEVATION = re.compile(
    r"(?:必要|必須|唯一|最終).{0,32}(?:驗證器|決策者|執行權威|權威|PASS|ALLOW|等價證明|正典更新)|"
    r"(?:驗證器|決策者|執行權威|權威).{0,32}(?:必要|必須|唯一|最終)|"
    r"\b(?:required|mandatory|necessary|sole|final)\b.{0,40}"
    r"\b(?:verifier|validator|decision maker|execution authority|authority|PASS|ALLOW)\b|"
    r"\b(?:verifier|validator|decision maker|execution authority|authority)\b.{0,40}"
    r"\b(?:required|mandatory|necessary|sole|final)\b",
    re.IGNORECASE,
)
_SEMANTIC_AUTHORITY_DENIAL = re.compile(
    r"(?:不得|禁止|不可|不能|僅可|只能.{0,24}候選|不得單獨|"
    r"\b(?:must not|cannot|may not|forbidden|prohibited|candidate only|only (?:a )?candidate|not required)\b)",
    re.IGNORECASE,
)
_SEMANTIC_COMMUNICATION_DRIFT = re.compile(
    r"(?:\b(?:w7tp|gtp)\b|生成式傳輸).{0,48}"
    r"(?:是|等同(?:於)?|定義為|\bis\b|\bequals?\b).{0,24}"
    r"(?:語意通信|semantic communication)",
    re.IGNORECASE,
)
_ADI_SINGLE_LAYER_DRIFT = re.compile(
    r"(?:\bADI\b).{0,48}(?:只有一層|單層|可逆身分碼|一般資料庫主鍵|"
    r"浮點\s*embedding|one[- ]layer|single[- ]layer|reversible identity code|"
    r"database primary key|floating[- ]point embedding)",
    re.IGNORECASE,
)
_PROTECTED_MATERIAL_SUBJECT = re.compile(
    r"(?:H64[-_ ]TD|完整碼本|映射表|恢復材料|full codebook|mapping table|recovery material)",
    re.IGNORECASE,
)
_PROTECTED_MATERIAL_DISCLOSURE = re.compile(
    r"(?:輸出|公開|寫入|記錄|嵌入|包含|\b(?:output|publish|write|log|embed|include)\b)",
    re.IGNORECASE,
)
_CURRENT_TWENTY_ONE_CLAIMS = re.compile(
    r"(?:21\s*項|twenty[- ]one claims?).{0,40}(?:現行|實際送件|current|filed)|"
    r"(?:現行|實際送件|current|filed).{0,40}(?:21\s*項|twenty[- ]one claims?)",
    re.IGNORECASE,
)
_SUPERSEDED_CLAIMS = re.compile(
    r"(?:已取代|被取代|舊稿|草稿|superseded|obsolete|draft)",
    re.IGNORECASE,
)
_SILENT_HISTORY_OVERWRITE = re.compile(
    r"(?:歷史狀態|前態|封印狀態|historical state|prior state|sealed state).{0,48}"
    r"(?:原地覆寫|靜默覆寫|直接覆寫|in[- ]place overwrite|silently overwrite|overwrite in place)",
    re.IGNORECASE,
)
_APPEND_ONLY_REQUIREMENT = re.compile(
    r"(?:append[- ]only|新封包|新狀態紀錄|successor packet|successor state|不得.{0,24}覆寫|must not.{0,24}overwrite)",
    re.IGNORECASE,
)
_REQUIRED_COMPLETION_OPERANDS = {
    "state_coordinate": re.compile(
        r"(?:狀態.{0,24}座標|座標.{0,24}狀態|\bstate\b.{0,32}\bcoordinate\b|\bcoordinate\b.{0,32}\bstate\b)",
        re.IGNORECASE,
    ),
    "reference": re.compile(r"(?:引用|引用鍵|\breference(?:s)?\b|\bref(?:erence)?_key\b)", re.IGNORECASE),
    "reconstruction_condition": re.compile(
        r"(?:重構條件|重構契約|\breconstruction (?:condition|contract)s?\b)",
        re.IGNORECASE,
    ),
    "packet_protocol": re.compile(r"(?:封包協定|傳輸協定|\bpacket protocol\b|\bprotocol\b)", re.IGNORECASE),
    "verification": re.compile(r"(?:驗證|\bverification\b|\bverifier\b)", re.IGNORECASE),
}
_QUOTE_PREFIXES = (">", "引用：", "引用:", "quoted:", "quote:")
_PROTECTED_PATH_PARTS = {"credentials", "secrets", "private", "member_plaintext", "resident_plaintext"}
ACTIVE_PRODUCT_POINTER = "runtime/total_field/master_index/ACTIVE_PRODUCT_SYSTEM_ROOT_POINTER.json"
ACTIVE_PRODUCT_POINTER_SHA256 = "512adeb0c3700b2a3a7c8849ad94d66affe4aec3a0b27307e12d80f6a66fdc19"
ACTIVE_PRODUCT_ROOT = (
    "runtime/total_field/product_system_root/ROOT_IMPL_20260722T211410Z/"
    "package/local-implementation/W7TP_PRODUCT_SYSTEM_ROOT_PACKET.json"
)
ACTIVE_PRODUCT_ROOT_SHA256 = "a073f824d77e89b024f8f43415af857272e8a59d6f6de8b518ee1aba90971a3d"
ADI_CANONICAL_GLOB = "W7TP_ADI_絕對距離螺旋路徑索引資料庫_正典規格*V3.0*回復版.md"
FULL_SCAN_ROOTS = (
    "docs",
    "schemas",
    "tools",
    "scripts",
    "tests",
    "manifests",
    "runtime",
    "Taiji_Odoo/addons",
    "prompts",
    "web",
    "dashboard",
    "containers",
    "docker",
)
FULL_SCAN_SUFFIXES = {
    ".bash",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".scss",
    ".service",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsv",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
FULL_SCAN_PRUNED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "vendor",
    "quarantine_originals",
    "quarantine-originals",
    "raw_audio",
    "raw_media",
}
FULL_SCAN_MAX_BYTES = 2 * 1024 * 1024
_RUNTIME_METADATA_HINT = re.compile(
    r"(?:state|evidence|index|manifest|receipt|report|seal|registry|alert|status|pointer|canonical|redteam|audit|packet)",
    re.IGNORECASE,
)
_SENSITIVE_FILE_NAME = re.compile(
    r"(?:^|[._-])(?:key|keys|token|tokens|password|passwords|credential|credentials)(?:[._-]|$)",
    re.IGNORECASE,
)
_HISTORICAL_PATH_PARTS = {
    "archive",
    "archives",
    "deprecated",
    "examples",
    "fixtures",
    "historical",
    "history",
    "legacy",
}
_GENERAL_DENIAL = re.compile(
    r"(?:不得|禁止|不可|不能|未|尚未|不代表|不應|並非|不是|"
    r"\b(?:must not|may not|cannot|not |never|forbidden|prohibited|does not|do not|without)\b)",
    re.IGNORECASE,
)
_HISTORICAL_MARKER = re.compile(
    r"(?:historical|deprecated|test fixture|non-canonical|legacy reference|歷史|舊候選|棄用|非正典)",
    re.IGNORECASE,
)
_RECEIPT_OR_EVIDENCE_BINDING = re.compile(
    r"(?:(?:receipt|回執)(?:[_ -]?(?:id|ref|sha256))?\s*[:=@]\s*[A-Za-z0-9_.:/-]{8,}|"
    r"(?:evidence|source|target)[_ -]?sha256\s*[:=@]\s*[0-9a-f]{64}|"
    r"sha256:[0-9a-f]{64}|\b[0-9a-f]{64}\b)",
    re.IGNORECASE,
)
_AUTHORITY_STATUS_CLAIM = re.compile(
    r"(?:\b(?:state|status|decision|result|lifecycle|authority_status|canonical_status)\b"
    r"\s*[:=]\s*[\"']?\b(?:PASS|ALLOW|ACTIVE|CANONICAL|COMMITTED|VERIFIED)\b|"
    r"(?:總場|Total Field|權威|authority|權限|permission).{0,40}"
    r"(?:\bis\b|=|為|已).{0,12}"
    r"(?:\bPASS\b|\bALLOW\b|\bACTIVE\b|\bCANONICAL\b|\bCOMMITTED\b|\bVERIFIED\b|授予|核准|升格)|"
    r"(?:正典|canonical).{0,24}(?:\bis\b|=|為|已).{0,12}"
    r"(?:\bACTIVE\b|\bCOMMITTED\b|\bVERIFIED\b|核准|升格))",
    re.IGNORECASE,
)
_MEMBER_AUTHORITY_SUBJECT = re.compile(
    r"(?:\bLLM\b|Odoo|候選|candidate|持有封包|packet holder|Total Field verifier|總場驗證)",
    re.IGNORECASE,
)
_MEMBER_AUTHORITY_CLAIM = re.compile(
    r"(?:會員(?:同意|主權|根)|member (?:consent|sovereignty|root)|代簽|代表會員|"
    r"execution authority|執行授權).{0,48}(?:授予|形成|簽發|代表|權威|authority|authorize)|"
    r"(?:授予|形成|簽發|代表|權威|authority|authorize).{0,48}"
    r"(?:會員(?:同意|主權|根)|member (?:consent|sovereignty|root)|執行授權)",
    re.IGNORECASE,
)
_MEMORY_CLAIM = re.compile(
    r"(?:記憶|memory).{0,40}(?:已更新|更新完成|已錨定|錨定完成|已持久化|"
    r"\bupdated\b|\banchored\b|\bpersisted\b)",
    re.IGNORECASE,
)
_WRITE_EVIDENCE = re.compile(
    r"(?:write[_ -]?receipt|persistence[_ -]?receipt|memory[_ -]?receipt|"
    r"寫入回執|持久化回執|evidence[_ -]?sha256|\b[0-9a-f]{64}\b)",
    re.IGNORECASE,
)
_CANDIDATE_STATE = re.compile(
    r"(?:source[-_ ]ready|prototype|rehearsal|candidate|候選|原型|演練)",
    re.IGNORECASE,
)
_RUNTIME_COMPLETION = re.compile(
    r"(?:runtime.{0,24}(?:完成|已啟用|active|complete)|正式訂單|付款完成|"
    r"已部署|deployment complete|product complete|產品完成|正式上線)",
    re.IGNORECASE,
)
_IDENTITY_PROXY = re.compile(
    r"(?:\btoken\b|LINE(?:/Google)? subject|Google subject|封包持有|packet possession|"
    r"role projection|角色投影)",
    re.IGNORECASE,
)
_SOVEREIGN_AUTHORITY = re.compile(
    r"(?:自然人主權|會員主權|sovereign identity|execution authorization|執行授權|"
    r"授予權限|grant(?:ed)? authority)",
    re.IGNORECASE,
)
_CROSS_AUTHORITY = re.compile(
    r"(?:member|會員|total[_ -]?field[_ -]?verifier|總場驗證|odoo|candidate authority|候選權威)"
    r".{0,72}(?:代替|代表|越權|override|supersede|acts? as|authority of).{0,72}"
    r"(?:member|會員|total[_ -]?field[_ -]?verifier|總場驗證|odoo|candidate authority|候選權威)",
    re.IGNORECASE,
)
_PARALLEL_COMPONENT = re.compile(
    r"(?:新增|另建|建立).{0,40}(?:平行|第二(?:份|套)|獨立).{0,24}"
    r"(?:matcher|receiver|registry|schema|route|gateway|container|匹配器|接收器|登錄器|路由|容器)|"
    r"(?:new|parallel|second|separate).{0,32}"
    r"(?:matcher|receiver|registry|schema|route|gateway|container)",
    re.IGNORECASE,
)
_EXECUTED_VERIFIED_CLAIM = re.compile(
    r"(?:\bEXECUTED\b|\bVERIFIED\b|已執行|已驗證)",
    re.IGNORECASE,
)
_RECEIVER_CLAIM_SUBJECT = re.compile(
    r"(?:\b(?:w7tp|gtp)\b|生成式傳輸|generative transmission|receiver|接收端|封包|packet)",
    re.IGNORECASE,
)
_RECEIVER_EVIDENCE = re.compile(
    r"(?:receiver(?:[_ -]?(?:receipt|evidence|sha256))?\s*[:=@]\s*[A-Za-z0-9_.:/-]{8,}|"
    r"接收器(?:回執|證據|雜湊)\s*[:=@]\s*[A-Za-z0-9_.:/-]{8,}|"
    r"receiver.{0,24}(?:sha256:[0-9a-f]{64}|\b[0-9a-f]{64}\b))",
    re.IGNORECASE,
)
_RUN_ID_DECLARATION = re.compile(
    r"(?:^|\s)(?:RUN_ID\s*=|[\"']run_id[\"']\s*:\s*[\"'])([A-Za-z0-9_.:-]{8,})",
    re.IGNORECASE,
)
_GENERAL_RULES = {
    "AUTH-TD-001": {
        "severity": "BLOCK",
        "canonical_ref": f"{ACTIVE_PRODUCT_POINTER}@sha256:{ACTIVE_PRODUCT_POINTER_SHA256}",
        "reason": "An authority-bearing PASS/ALLOW/ACTIVE/CANONICAL/COMMITTED/VERIFIED claim lacks an exact receipt or SHA256 binding.",
        "correction": "Downclass the claim to candidate/HOLD until the exact Total Field receipt and source binding are present.",
    },
    "AUTH-TD-002": {
        "severity": "BLOCK",
        "canonical_ref": f"{ACTIVE_PRODUCT_ROOT}@sha256:{ACTIVE_PRODUCT_ROOT_SHA256}",
        "reason": "A model, workflow, candidate, packet holder, or verifier is asserted as member-consent or sovereign authority.",
        "correction": "Restore member-root consent authority and keep model/workflow/verifier output candidate or verification-only.",
    },
    "STATE-TD-001": {
        "severity": "HOLD",
        "canonical_ref": f"{ACTIVE_PRODUCT_ROOT}@sha256:{ACTIVE_PRODUCT_ROOT_SHA256}",
        "reason": "Memory is asserted updated, anchored, or persisted without write evidence.",
        "correction": "Downclass the memory claim until an exact persistence receipt and evidence SHA256 exist.",
    },
    "STATE-TD-002": {
        "severity": "BLOCK",
        "canonical_ref": f"{ACTIVE_PRODUCT_ROOT}@sha256:{ACTIVE_PRODUCT_ROOT_SHA256}",
        "reason": "A source-ready, prototype, rehearsal, or candidate state is asserted as Runtime, deployed, paid, ordered, or product-complete.",
        "correction": "Restore the candidate/source-only lifecycle and require separate Runtime activation evidence.",
    },
    "IDENTITY-TD-001": {
        "severity": "BLOCK",
        "canonical_ref": None,
        "reason": "A token, channel subject, packet possession, or role projection is asserted as natural-person sovereignty or execution authorization.",
        "correction": "Bind the proxy to a verified Root/Seat/Consent/Revocation/Receipt contract before any authority claim.",
    },
    "IDENTITY-TD-002": {
        "severity": "BLOCK",
        "canonical_ref": None,
        "reason": "Member, Total Field verifier, Odoo, or candidate authority is asserted across another authority boundary.",
        "correction": "Restore the distinct member, verification, business-projection, and candidate authority boundaries.",
    },
    "ARCH-TD-001": {
        "severity": "HOLD",
        "canonical_ref": f"{ACTIVE_PRODUCT_ROOT}@sha256:{ACTIVE_PRODUCT_ROOT_SHA256}",
        "reason": "A parallel matcher, receiver, registry, schema, route, gateway, or container is proposed instead of an evidenced native extension point.",
        "correction": "Reuse the existing authoritative extension point or bind evidence that no compatible native extension exists.",
    },
    "EVIDENCE-TD-001": {
        "severity": "HOLD",
        "canonical_ref": f"{ACTIVE_PRODUCT_POINTER}@sha256:{ACTIVE_PRODUCT_POINTER_SHA256}",
        "reason": "The same RUN_ID is declared by multiple active source artifacts with different SHA256 values.",
        "correction": "Issue a new RUN_ID and bind it to the prior run through BASE_RUN_ID.",
    },
    "EVIDENCE-TD-002": {
        "severity": "HOLD",
        "canonical_ref": f"{ACTIVE_PRODUCT_ROOT}@sha256:{ACTIVE_PRODUCT_ROOT_SHA256}",
        "reason": "EXECUTED or VERIFIED is asserted without receiver evidence.",
        "correction": "Downclass to source-ready/HOLD until an exact receiver receipt and SHA256 are present.",
    },
}


def run_psql(sql: str) -> str:
    cmd = [
        "docker",
        "compose",
        "--env-file",
        ".env.d8.local",
        "-f",
        "compose.d8.yml",
        "exec",
        "-T",
        "d8_db",
        "psql",
        "-U",
        "taiji",
        "-d",
        "taiji_d8",
        "-At",
        "-c",
        sql,
    ]
    return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_test_sample(source_file: str, context: dict) -> bool:
    if context.get("test_sample") is True:
        return True
    source = Path(source_file)
    lowered_parts = {part.lower() for part in source.parts}
    name = source.name.lower()
    return "tests" in lowered_parts or "fixtures" in lowered_parts or name.startswith("test_") or name.endswith("_test.py")


def _is_quarantined_redteam_evidence(text: str, context: dict) -> bool:
    if context.get("retrieval_scope") == "redteam_only" and context.get("quarantine") is True:
        return True
    lowered = text.lower()
    redteam_only = '"retrieval_scope": "redteam_only"' in lowered or "retrieval_scope=redteam_only" in lowered
    quarantined = '"quarantine": true' in lowered or "quarantine=true" in lowered
    return redteam_only and quarantined


def _is_protected_source_path(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if name.startswith(".env"):
        return True
    if lowered_parts & _PROTECTED_PATH_PARTS:
        return True
    return bool(re.search(r"(?:credential|password|token|member_plaintext|resident_plaintext)", name))


def _scannable_lines(text: str):
    in_fence = False
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        if stripped.lower().startswith(_QUOTE_PREFIXES):
            continue
        yield line_number, stripped


def _make_finding(
    rule_id: str,
    source_file: str,
    line_number: int,
    evidence_sha256: str,
    correction_suffix: str = "",
) -> dict:
    rule = GTP_TECHNICAL_DRIFT_RULES[rule_id]
    correction = rule["correction"]
    if correction_suffix:
        correction = f"{correction} {correction_suffix}"
    return {
        "rule_id": rule_id,
        "file": source_file,
        "line": line_number,
        "evidence_sha256": evidence_sha256,
        "canonical_reference": rule["canonical_reference"],
        "severity": rule["severity"],
        "correction": correction,
    }


def scan_technical_definition_drift(
    text: str,
    source_file: str,
    *,
    domain: str = "GTP",
    context: dict | None = None,
) -> dict:
    context = context or {}
    evidence_sha256 = _sha256_text(text)
    base = {
        "domain": domain,
        "ruleset": "GTP_TECHNICAL_DEFINITION_DRIFT_V1",
        "source_file": source_file,
        "evidence_sha256": evidence_sha256,
        "active_canonical": ACTIVE_GTP_CANONICAL,
        "active_canonical_sha256": ACTIVE_GTP_CANONICAL_SHA256,
        "non_executable": True,
        "writeback": False,
    }
    if domain.upper() != "GTP":
        return {**base, "state": "HOLD_UNSUPPORTED_RULE_DOMAIN", "findings": []}
    if context.get("quoted") is True or _is_test_sample(source_file, context):
        return {**base, "state": "PASS_EXCLUDED_TEST_OR_QUOTED_CONTEXT", "findings": []}
    if _is_quarantined_redteam_evidence(text, context):
        return {**base, "state": "PASS_EXCLUDED_REDTEAM_QUARANTINE_EVIDENCE", "findings": []}

    findings: list[dict] = []
    scannable = list(_scannable_lines(text))
    completion_operands = {
        operand: bool(pattern.search(text))
        for operand, pattern in _REQUIRED_COMPLETION_OPERANDS.items()
    }
    receipt_present = bool(_RECEIPT.search(text))

    for line_number, line in scannable:
        if (
            _GTP_SUBJECT.search(line)
            and _TRANSFER_DRIFT.search(line)
            and _TRANSFER_ASSERTION.search(line)
            and not _TRANSFER_DENIAL.search(line)
        ):
            findings.append(_make_finding("GTP-TD-001", source_file, line_number, evidence_sha256))

        if _COMPLETION_CLAIM.search(line) and not _COMPLETION_DENIAL.search(line):
            missing = [operand for operand, present in completion_operands.items() if not present]
            if missing:
                findings.append(
                    _make_finding(
                        "GTP-TD-002",
                        source_file,
                        line_number,
                        evidence_sha256,
                        "Missing operands: " + ", ".join(missing) + ".",
                    )
                )

        if _FLAT_8D.search(line) and not _FLAT_8D_DENIAL.search(line):
            findings.append(_make_finding("GTP-TD-003", source_file, line_number, evidence_sha256))

        if (
            _GTP_SUBJECT.search(line)
            and _MODEL_OPERATOR.search(line)
            and _MODEL_REPLACEMENT.search(line)
            and not _MODEL_DENIAL.search(line)
        ):
            findings.append(_make_finding("GTP-TD-004", source_file, line_number, evidence_sha256))

        if (
            _UPDATE_TARGET.search(line)
            and _UPDATE_CLAIM.search(line)
            and not _UPDATE_DENIAL.search(line)
            and not receipt_present
        ):
            findings.append(_make_finding("GTP-TD-005", source_file, line_number, evidence_sha256))

        if (
            _SEMANTIC_AUTHORITY_CONTEXT.search(line)
            and _SEMANTIC_AUTHORITY_OPERATOR.search(line)
            and _SEMANTIC_AUTHORITY_ELEVATION.search(line)
            and not _SEMANTIC_AUTHORITY_DENIAL.search(line)
        ):
            findings.append(_make_finding("GTP-TD-006", source_file, line_number, evidence_sha256))

        if _SEMANTIC_COMMUNICATION_DRIFT.search(line) and not _GENERAL_DENIAL.search(line):
            findings.append(_make_finding("GTP-TD-007", source_file, line_number, evidence_sha256))

        if _ADI_SINGLE_LAYER_DRIFT.search(line) and not _GENERAL_DENIAL.search(line):
            findings.append(_make_finding("GTP-TD-008", source_file, line_number, evidence_sha256))

        if (
            _PROTECTED_MATERIAL_SUBJECT.search(line)
            and _PROTECTED_MATERIAL_DISCLOSURE.search(line)
            and not _GENERAL_DENIAL.search(line)
            and "reference-only" not in line.casefold()
        ):
            findings.append(_make_finding("GTP-TD-009", source_file, line_number, evidence_sha256))

        if _CURRENT_TWENTY_ONE_CLAIMS.search(line) and not _SUPERSEDED_CLAIMS.search(line):
            findings.append(_make_finding("GTP-TD-010", source_file, line_number, evidence_sha256))

        if _SILENT_HISTORY_OVERWRITE.search(line) and not _APPEND_ONLY_REQUIREMENT.search(line):
            findings.append(_make_finding("GTP-TD-011", source_file, line_number, evidence_sha256))

    state = "BLOCK_TECHNICAL_DEFINITION_DRIFT" if findings else "PASS_NO_TECHNICAL_DEFINITION_DRIFT"
    return {**base, "state": state, "findings": findings}


def scan_technical_definition_drift_file(path: Path, *, domain: str = "GTP", context: dict | None = None) -> dict:
    resolved = path.resolve()
    if _is_protected_source_path(resolved):
        raise ValueError("protected source path is not allowed")
    text = resolved.read_text(encoding="utf-8")
    return scan_technical_definition_drift(text, resolved.as_posix(), domain=domain, context=context)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _is_protected_full_scan_path(path: Path) -> bool:
    relative = _relative_path(path)
    parts = tuple(part.lower() for part in Path(relative).parts)
    name = path.name.lower()
    if name.startswith(".env"):
        return True
    if relative.startswith("runtime/") and (
        name.startswith("chat_")
        or name.startswith("full_system_deterministic_drift_")
        or "packet_inference_cockpit" in parts
        or "conversation" in parts
        or "conversation_context_record" in parts
    ):
        return True
    if "h64-td" in relative.lower() or "h64_td" in relative.lower():
        return True
    if any(part in FULL_SCAN_PRUNED_DIRS or part.startswith(".venv") for part in parts):
        return True
    if set(parts) & _PROTECTED_PATH_PARTS:
        return True
    return bool(_SENSITIVE_FILE_NAME.search(name))


def _runtime_metadata_allowed(path: Path) -> bool:
    relative = _relative_path(path)
    if not relative.startswith("runtime/"):
        return True
    if relative in {
        ACTIVE_PRODUCT_POINTER,
        ACTIVE_PRODUCT_ROOT,
        (
            "runtime/total_field/product_system_root/ROOT_IMPL_20260722T211410Z/"
            "TOTAL_FIELD_GATEWAY_CANDIDATE_RECEIPT.D7_REFERENCE_ONLY_V3.json"
        ),
    }:
        return True
    return bool(_RUNTIME_METADATA_HINT.search(relative))


def _is_container_definition(path: Path) -> bool:
    name = path.name
    return name.startswith("Dockerfile") or bool(re.fullmatch(r"compose(?:\.[^.]+)*\.ya?ml", name))


def _discover_full_scan_files(root: Path) -> tuple[list[Path], int, int]:
    files: set[Path] = set()
    protected_skip_units = 0
    unsupported_files = 0
    for relative_root in FULL_SCAN_ROOTS:
        scan_root = root / relative_root
        if not scan_root.is_dir():
            continue
        for current, dirnames, filenames in os.walk(scan_root):
            current_path = Path(current)
            retained_dirs = []
            for dirname in dirnames:
                candidate = current_path / dirname
                lowered = dirname.lower()
                if (
                    lowered in FULL_SCAN_PRUNED_DIRS
                    or lowered.startswith(".venv")
                    or _is_protected_full_scan_path(candidate)
                ):
                    protected_skip_units += 1
                else:
                    retained_dirs.append(dirname)
            dirnames[:] = retained_dirs
            for filename in filenames:
                candidate = current_path / filename
                if _is_protected_full_scan_path(candidate):
                    protected_skip_units += 1
                    continue
                if candidate.is_symlink() or not candidate.is_file():
                    unsupported_files += 1
                    continue
                if candidate.stat().st_size > FULL_SCAN_MAX_BYTES:
                    unsupported_files += 1
                    continue
                if candidate.suffix.lower() not in FULL_SCAN_SUFFIXES and not _is_container_definition(candidate):
                    unsupported_files += 1
                    continue
                if not _runtime_metadata_allowed(candidate):
                    unsupported_files += 1
                    continue
                files.add(candidate.resolve())

    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        retained_dirs = []
        for dirname in dirnames:
            candidate = current_path / dirname
            lowered = dirname.lower()
            if (
                lowered in FULL_SCAN_PRUNED_DIRS
                or lowered.startswith(".venv")
                or _is_protected_full_scan_path(candidate)
            ):
                continue
            retained_dirs.append(dirname)
        dirnames[:] = retained_dirs
        for filename in filenames:
            candidate = current_path / filename
            if _is_container_definition(candidate) and not _is_protected_full_scan_path(candidate):
                if candidate.is_file() and candidate.stat().st_size <= FULL_SCAN_MAX_BYTES:
                    files.add(candidate.resolve())
    return sorted(files), protected_skip_units, unsupported_files


def _python_ast_string_lines(text: str) -> set[int]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()
    return {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and hasattr(node, "lineno")
    }


def _path_context_class(path: Path, text: str) -> str | None:
    relative = _relative_path(path)
    parts = {part.lower() for part in Path(relative).parts}
    name = path.name.lower()
    if relative == ACTIVE_GTP_CANONICAL:
        return "active_canonical_reference"
    if relative == LEGACY_GTP_CANONICAL_V2:
        return "legacy_canonical_parent"
    if "tests" in parts or "fixtures" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "test_fixture"
    if parts & _HISTORICAL_PATH_PARTS:
        return "historical_or_deprecated"
    if _is_quarantined_redteam_evidence(text, {}):
        return "redteam_quarantine"
    return None


def _general_finding(rule_id: str, path: Path, line: int, target_sha256: str, context_class: str) -> dict:
    rule = _GENERAL_RULES[rule_id]
    return {
        "rule_id": rule_id,
        "path": _relative_path(path),
        "line": line,
        "target_sha256": target_sha256,
        "canonical_ref": rule["canonical_ref"],
        "context_class": context_class,
        "severity": rule["severity"],
        "reason": rule["reason"],
        "correction_candidate": rule["correction"],
    }


def _scan_general_drift(path: Path, text: str, target_sha256: str) -> tuple[list[dict], int]:
    findings: list[dict] = []
    suppressed = 0
    receipt_bound = bool(_RECEIPT_OR_EVIDENCE_BINDING.search(text))
    write_evidence = bool(_WRITE_EVIDENCE.search(text))
    receiver_evidence = bool(_RECEIVER_EVIDENCE.search(text))
    ast_string_lines = _python_ast_string_lines(text) if path.suffix.lower() == ".py" else set()

    for line_number, line in _scannable_lines(text):
        matched_rules: list[str] = []
        if _AUTHORITY_STATUS_CLAIM.search(line) and not receipt_bound:
            matched_rules.append("AUTH-TD-001")
        if _MEMBER_AUTHORITY_SUBJECT.search(line) and _MEMBER_AUTHORITY_CLAIM.search(line):
            matched_rules.append("AUTH-TD-002")
        if _MEMORY_CLAIM.search(line) and not write_evidence:
            matched_rules.append("STATE-TD-001")
        if _CANDIDATE_STATE.search(line) and _RUNTIME_COMPLETION.search(line):
            matched_rules.append("STATE-TD-002")
        if _PARALLEL_COMPONENT.search(line):
            matched_rules.append("ARCH-TD-001")
        if (
            _RECEIVER_CLAIM_SUBJECT.search(line)
            and _EXECUTED_VERIFIED_CLAIM.search(line)
            and not receiver_evidence
        ):
            matched_rules.append("EVIDENCE-TD-002")
        if _GENERAL_DENIAL.search(line) or _HISTORICAL_MARKER.search(line):
            suppressed_rules = set(matched_rules)
            if (
                _UPDATE_TARGET.search(line)
                and re.search(
                    r"\b(?:PASS|ALLOW|ACTIVE|CANONICAL|COMMITTED|VERIFIED)\b|"
                    r"(?:核准|升格|授予)",
                    line,
                    re.IGNORECASE,
                )
                and not receipt_bound
            ):
                suppressed_rules.add("AUTH-TD-001")
            if _IDENTITY_PROXY.search(line) and _SOVEREIGN_AUTHORITY.search(line):
                suppressed_rules.add("IDENTITY-TD-001")
            if _CROSS_AUTHORITY.search(line):
                suppressed_rules.add("IDENTITY-TD-002")
            suppressed += len(suppressed_rules)
            continue
        if not matched_rules:
            continue
        context_class = "python_ast_string" if line_number in ast_string_lines else "active_source"
        findings.extend(
            _general_finding(rule_id, path, line_number, target_sha256, context_class)
            for rule_id in matched_rules
        )
    return findings, suppressed


def _gtp_findings_for_full_scan(path: Path, text: str, target_sha256: str) -> list[dict]:
    result = scan_technical_definition_drift(text, "active-source", context={})
    findings = []
    for finding in result["findings"]:
        findings.append(
            {
                "rule_id": finding["rule_id"],
                "path": _relative_path(path),
                "line": finding["line"],
                "target_sha256": target_sha256,
                "canonical_ref": (
                    f"{finding['canonical_reference']}@sha256:{ACTIVE_GTP_CANONICAL_SHA256}"
                ),
                "context_class": "active_source",
                "severity": finding["severity"],
                "reason": "Deterministic GTP technical-definition rule matched the active source context.",
                "correction_candidate": finding["correction"],
            }
        )
    return findings


def _run_id_declarations(path: Path, text: str, target_sha256: str) -> list[tuple[str, int, str, str]]:
    relative = _relative_path(path)
    if relative.startswith(("runtime/", "docs/", "tests/", "prompts/")):
        return []
    declarations = []
    for line_number, line in _scannable_lines(text):
        match = _RUN_ID_DECLARATION.search(line)
        if match and not _GENERAL_DENIAL.search(line):
            declarations.append((match.group(1), line_number, relative, target_sha256))
    return declarations


def _resolve_adi_canonical(root: Path) -> dict:
    canonical_candidates = []
    for base in ("docs", "manifests", "runtime"):
        search_root = root / base
        if search_root.is_dir():
            canonical_candidates.extend(search_root.rglob(ADI_CANONICAL_GLOB))
    canonical_candidates = sorted({path.resolve() for path in canonical_candidates if path.is_file()})

    active_index_candidates = []
    for base in ("manifests", "runtime"):
        search_root = root / base
        if not search_root.is_dir():
            continue
        for path in search_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".yaml", ".yml"}:
                continue
            name = path.name.lower()
            if "active" in name and "adi" in name and not _is_protected_full_scan_path(path):
                active_index_candidates.append(path.resolve())

    if len(canonical_candidates) != 1 or not active_index_candidates:
        return {
            "state": "HOLD_ADI_CANONICAL_UNBOUND",
            "canonical_ref": None,
            "canonical_sha256": None,
            "files_scanned": 0,
            "block_count": 0,
            "hold_count": 1,
            "legacy_references_suppressed": 0,
            "path_divergence_count": 0,
            "authority_radius_violations": 0,
        }

    canonical_path = canonical_candidates[0]
    canonical_sha256 = _sha256_file(canonical_path)
    relative = _relative_path(canonical_path)
    binding = f"{relative}@sha256:{canonical_sha256}"
    bound = False
    for index_path in active_index_candidates:
        try:
            index_text = index_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if relative in index_text and canonical_sha256 in index_text:
            bound = True
            break
    if not bound:
        return {
            "state": "HOLD_ADI_CANONICAL_UNBOUND",
            "canonical_ref": relative,
            "canonical_sha256": canonical_sha256,
            "files_scanned": 1,
            "block_count": 0,
            "hold_count": 1,
            "legacy_references_suppressed": 0,
            "path_divergence_count": 0,
            "authority_radius_violations": 0,
        }
    return {
        "state": "BOUND_RULES_NOT_ACTIVATED_IN_THIS_BASELINE",
        "canonical_ref": binding,
        "canonical_sha256": canonical_sha256,
        "files_scanned": 1,
        "block_count": 0,
        "hold_count": 1,
        "legacy_references_suppressed": 0,
        "path_divergence_count": 0,
        "authority_radius_violations": 0,
    }


def _load_baseline_report(path: Path | None) -> dict:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    index = payload.get("file_index")
    if not isinstance(index, dict):
        raise ValueError("baseline report does not contain file_index")
    payload["file_index"] = {str(key): str(value) for key, value in index.items()}
    return payload


def run_full_deterministic_drift_scan(
    *,
    run_id: str,
    report_path: Path,
    baseline_report: Path | None = None,
) -> dict:
    pointer_path = ROOT / ACTIVE_PRODUCT_POINTER
    product_root_path = ROOT / ACTIVE_PRODUCT_ROOT
    canonical_path = ROOT / ACTIVE_GTP_CANONICAL
    legacy_canonical_path = ROOT / LEGACY_GTP_CANONICAL_V2
    binding_checks = {
        ACTIVE_PRODUCT_POINTER: _sha256_file(pointer_path) == ACTIVE_PRODUCT_POINTER_SHA256,
        ACTIVE_PRODUCT_ROOT: _sha256_file(product_root_path) == ACTIVE_PRODUCT_ROOT_SHA256,
        ACTIVE_GTP_CANONICAL: _sha256_file(canonical_path) == ACTIVE_GTP_CANONICAL_SHA256,
        LEGACY_GTP_CANONICAL_V2: _sha256_file(legacy_canonical_path)
        == LEGACY_GTP_CANONICAL_V2_SHA256,
    }
    files, protected_skip_units, unsupported_files = _discover_full_scan_files(ROOT)
    prior_report = _load_baseline_report(baseline_report)
    prior_hashes = prior_report.get("file_index", {})
    file_index = {_relative_path(path): _sha256_file(path) for path in files}
    if prior_hashes:
        selected_paths = {
            relative
            for relative, sha256 in file_index.items()
            if prior_hashes.get(relative) != sha256
        }
        current_matcher_sha256 = _sha256_file(Path(__file__))
        if prior_report.get("matcher_sha256_before_report") != current_matcher_sha256:
            selected_paths.update(
                finding["path"]
                for finding in prior_report.get("findings", [])
                if isinstance(finding, dict) and finding.get("path") in file_index
            )
            scan_mode = "INCREMENTAL_CHANGED_FILES_AND_PRIOR_FINDING_REFERENCES"
        else:
            scan_mode = "INCREMENTAL_CHANGED_FILES"
        selected = [path for path in files if _relative_path(path) in selected_paths]
    else:
        selected_paths = {_relative_path(path) for path in files}
        selected = files
        scan_mode = "FULL_BASELINE"

    findings: list[dict] = [
        finding
        for finding in prior_report.get("findings", [])
        if (
            isinstance(finding, dict)
            and finding.get("path") in file_index
            and finding.get("path") not in selected_paths
            and finding.get("target_sha256") == file_index.get(finding.get("path"))
        )
    ]
    suppressed_count = int(prior_report.get("false_positive_suppressed", 0))
    run_id_declarations: dict[str, list[tuple[int, str, str]]] = {}
    read_errors: list[str] = []
    for path in selected:
        relative = _relative_path(path)
        target_sha256 = file_index[relative]
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            read_errors.append(relative)
            continue
        path_context = _path_context_class(path, text)
        gtp_findings = _gtp_findings_for_full_scan(path, text, target_sha256)
        general_findings, general_suppressed = _scan_general_drift(path, text, target_sha256)
        if path_context:
            if not prior_hashes:
                suppressed_count += len(gtp_findings) + len(general_findings) + general_suppressed
        else:
            findings.extend(gtp_findings)
            findings.extend(general_findings)
            if not prior_hashes:
                suppressed_count += general_suppressed
            for declared_run_id, line_number, declared_path, declared_sha256 in _run_id_declarations(
                path, text, target_sha256
            ):
                run_id_declarations.setdefault(declared_run_id, []).append(
                    (line_number, declared_path, declared_sha256)
                )

    for declared_run_id, declarations in sorted(run_id_declarations.items()):
        unique_files = {(path, sha256) for _, path, sha256 in declarations}
        if len(unique_files) < 2 or len({sha256 for _, sha256 in unique_files}) < 2:
            continue
        for line_number, declared_path, declared_sha256 in declarations:
            rule = _GENERAL_RULES["EVIDENCE-TD-001"]
            findings.append(
                {
                    "rule_id": "EVIDENCE-TD-001",
                    "path": declared_path,
                    "line": line_number,
                    "target_sha256": declared_sha256,
                    "canonical_ref": rule["canonical_ref"],
                    "context_class": "active_source",
                    "severity": rule["severity"],
                    "reason": f"{rule['reason']} RUN_ID={declared_run_id}",
                    "correction_candidate": rule["correction"],
                }
            )

    adi = _resolve_adi_canonical(ROOT)
    unbound_domains = ["IDENTITY_SOVEREIGNTY", "MANIFEST"]
    if adi["state"] == "HOLD_ADI_CANONICAL_UNBOUND":
        unbound_domains.append("ADI")
    block_count = sum(finding["severity"] == "BLOCK" for finding in findings)
    hold_count = sum(finding["severity"] == "HOLD" for finding in findings) + adi["hold_count"]
    duplicate_count = sum(finding["rule_id"] == "ARCH-TD-001" for finding in findings)
    state = (
        "HOLD_SOURCE_BINDING_DRIFT"
        if not all(binding_checks.values())
        else "HOLD_HUMAN_REVIEW_REQUIRED"
        if findings or unbound_domains
        else "PASS_READ_ONLY_FULL_BASELINE"
    )
    report = {
        "schema": "w7tp.total_field.deterministic_drift_scan_report.v1",
        "run_id": run_id,
        "created_at_utc": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "state": state,
        "mode": scan_mode,
        "baseline_run_id": prior_report.get("run_id"),
        "non_executable": True,
        "writeback": False,
        "active_canonical_refs": [
            f"{ACTIVE_PRODUCT_POINTER}@sha256:{ACTIVE_PRODUCT_POINTER_SHA256}",
            f"{ACTIVE_PRODUCT_ROOT}@sha256:{ACTIVE_PRODUCT_ROOT_SHA256}",
            f"{ACTIVE_GTP_CANONICAL}@sha256:{ACTIVE_GTP_CANONICAL_SHA256}",
            f"{LEGACY_GTP_CANONICAL_V2}@sha256:{LEGACY_GTP_CANONICAL_V2_SHA256}",
        ],
        "binding_checks": binding_checks,
        "manifest_binding": "UNBOUND_NO_DIRECT_FILE_REFERENCE",
        "matcher_sha256_before_report": _sha256_file(Path(__file__)),
        "files_discovered": len(files),
        "files_scanned": len(selected) - len(read_errors),
        "files_skipped_protected": protected_skip_units,
        "files_skipped_unsupported": unsupported_files,
        "read_error_paths": read_errors,
        "block_count": block_count,
        "hold_count": hold_count,
        "false_positive_suppressed": suppressed_count,
        "false_positive_suppressed_scope": (
            "FULL_BASELINE_CARRIED_FORWARD" if prior_hashes else "FULL_BASELINE"
        ),
        "duplicate_development_count": duplicate_count,
        "unbound_rule_domains": sorted(unbound_domains),
        "adi": adi,
        "findings": sorted(
            findings,
            key=lambda item: (
                -RANK.get(item["severity"], 0),
                item["rule_id"],
                item["path"],
                item["line"],
            ),
        ),
        "file_index": file_index,
        "db_write": False,
        "canonical_changed": False,
        "runtime_changed": False,
    }
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = _relative_path(report_path)
    report["report_sha256"] = _sha256_file(report_path)
    return report


def load_alerts() -> list[dict]:
    raw = run_psql(
        """
        SELECT COALESCE(jsonb_agg(to_jsonb(a)), '[]'::jsonb)
        FROM (
          SELECT id, run_id, event_type, alert_level, title, summary,
                 evidence_ref, reverse_refs, affected_paths
          FROM d8_active_possible_alerts
          ORDER BY created_at
        ) a;
        """
    )
    return json.loads(raw or "[]")


def matches(alert: dict, scope: dict) -> bool:
    evidence = alert.get("evidence_ref") or {}
    alert_id = str(alert.get("event_type") or "")
    text = " ".join(
        str(x).lower()
        for x in [
            alert.get("event_type"),
            alert.get("title"),
            alert.get("summary"),
            evidence.get("pattern"),
            evidence.get("possible_error"),
            evidence.get("correct_action"),
            json.dumps(alert.get("reverse_refs") or [], ensure_ascii=False),
            json.dumps(alert.get("affected_paths") or [], ensure_ascii=False),
        ]
    )
    if scope.get("human_review_required") and alert_id == "D8_ALERT_HUMAN_REVIEW_REQUIRED":
        return True
    if scope.get("pre_existing_non_d8_diff") and alert_id == "D8_ALERT_PRE_EXISTING_NON_D8_DIFF":
        return True
    if (
        "rerun_ingestion" in str(scope.get("request", "")).lower()
        and alert_id == "D8_ALERT_PHASE1_BASELINE_READY"
    ):
        return True
    if scope.get("d8_memory_count") and alert_id == "D8_ALERT_PHASE1_BASELINE_READY":
        return True
    if scope.get("file") and str(scope["file"]).lower() in text and "pre-existing" in text:
        return alert_id == "D8_ALERT_PRE_EXISTING_NON_D8_DIFF"
    scan_request = scope.get("technical_drift_scan")
    if alert_id == GTP_TECHNICAL_DRIFT_ALERT_ID and isinstance(scan_request, dict):
        content = scan_request.get("content")
        source_file = str(scan_request.get("source_file") or "scope-input")
        if isinstance(content, str):
            result = scan_technical_definition_drift(
                content,
                source_file,
                domain=str(scan_request.get("domain") or "GTP"),
                context=scan_request.get("context") if isinstance(scan_request.get("context"), dict) else {},
            )
            return bool(result["findings"])
    return False


def decide(matched: list[dict]) -> tuple[str, str]:
    if not matched:
        return "PASS", "no active possible_alert matched task scope"
    decision = max((a.get("alert_level", "INFO") for a in matched), key=lambda level: RANK.get(level, 0))
    return decision, "matched active possible_alerts: " + ", ".join(a.get("event_type", "") for a in matched)


def insert_evaluation(run_id: str, task_name: str, scope: dict, matched: list[dict], decision: str, reason: str) -> None:
    payload = {
        "scope": scope,
        "matched_alerts": [
            {
                "id": a.get("id"),
                "alert_id": a.get("event_type"),
                "alert_level": a.get("alert_level"),
            }
            for a in matched
        ],
    }
    sql = f"""
    INSERT INTO d8_guard_evaluations (
      run_id, task_name, task_scope, matched_alerts, decision, reason,
      executable, pollution_guard
    )
    VALUES (
      {sql_literal(run_id)},
      {sql_literal(task_name)},
      {sql_literal(json.dumps(scope, ensure_ascii=False))}::jsonb,
      {sql_literal(json.dumps(payload["matched_alerts"], ensure_ascii=False))}::jsonb,
      {sql_literal(decision)},
      {sql_literal(reason)},
      false,
      true
    );
    """
    run_psql(sql)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate task scope against D8 possible alerts")
    parser.add_argument("--run-id")
    parser.add_argument("--task-name")
    parser.add_argument("--scope-json")
    parser.add_argument("--scan-file")
    parser.add_argument("--scan-root", action="store_true")
    parser.add_argument("--report-path")
    parser.add_argument("--baseline-report")
    parser.add_argument("--domain", default="GTP")
    parser.add_argument("--context-json", default="{}")
    args = parser.parse_args()

    if args.scan_root:
        if not args.run_id or not args.report_path:
            parser.error("--scan-root requires --run-id and --report-path")
        summary = run_full_deterministic_drift_scan(
            run_id=args.run_id,
            report_path=Path(args.report_path),
            baseline_report=Path(args.baseline_report) if args.baseline_report else None,
        )
        print(
            json.dumps(
                {
                    key: summary[key]
                    for key in (
                        "state",
                        "run_id",
                        "active_canonical_refs",
                        "matcher_sha256_before_report",
                        "files_scanned",
                        "files_skipped_protected",
                        "block_count",
                        "hold_count",
                        "false_positive_suppressed",
                        "duplicate_development_count",
                        "unbound_rule_domains",
                        "adi",
                        "report_path",
                        "report_sha256",
                    )
                },
                ensure_ascii=False,
            )
        )
        return 30 if summary["state"].startswith("HOLD") else 0

    if args.scan_file:
        context = json.loads(args.context_json)
        if not isinstance(context, dict):
            parser.error("--context-json must decode to an object")
        summary = scan_technical_definition_drift_file(
            Path(args.scan_file),
            domain=args.domain,
            context=context,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 30 if summary["findings"] else 0

    if not args.run_id or not args.task_name or not args.scope_json:
        parser.error("--run-id, --task-name, and --scope-json are required unless --scan-file is used")
    scope = json.loads(args.scope_json)
    alerts = load_alerts()
    matched = [alert for alert in alerts if matches(alert, scope)]
    decision, reason = decide(matched)
    insert_evaluation(args.run_id, args.task_name, scope, matched, decision, reason)
    summary = {
        "run_id": args.run_id,
        "task_name": args.task_name,
        "decision": decision,
        "reason": reason,
        "matched_alerts": [
            {"alert_id": a.get("event_type"), "alert_level": a.get("alert_level")}
            for a in matched
        ],
        "executable": False,
        "pollution_guard": True,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
