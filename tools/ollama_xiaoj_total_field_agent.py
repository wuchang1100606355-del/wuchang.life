"""Ollama XiaoJ Total Field candidate-only agent.

The agent can ask a local Ollama-compatible endpoint for a draft, but every
result is downgraded into a Candidate and delivered through receive_candidate.
It never commits, deploys, writes DB state, restarts services, writes routers,
or creates canonical pointers.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

try:
    from tools.ollama_total_field_skill_bridge import (  # type: ignore
        DEFAULT_MANIFEST,
        OllamaTotalFieldSkillBridge,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
    if str(ROOT_FOR_IMPORT) not in sys.path:
        sys.path.insert(0, str(ROOT_FOR_IMPORT))
    from tools.ollama_total_field_skill_bridge import DEFAULT_MANIFEST, OllamaTotalFieldSkillBridge

try:
    from tools.total_field_dynamic_context import build_dynamic_context
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    from total_field_dynamic_context import build_dynamic_context  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFIX = ROOT / "manifests" / "ollama_xiaoj_total_field_v0_1" / "system_prefix.txt"
DEFAULT_ROOT_MODEL = "w7tp-xiaoj-root-8b"

FORBIDDEN_OUTPUT_KEYS = {
    "ALLOW",
    "TFS",
    "TFID",
    "committed",
    "commit",
    "canonical",
    "canonical_pointer",
    "pointer",
    "total_field_hash",
    "Total Field Hash",
}

SECRET_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"\bAIza[0-9A-Za-z_\-]+",
        r"\bBearer\s+[0-9A-Za-z._\-]+",
        r"\b(access_token|refresh_token|id_token|private_key|password|passwd)\b",
        r"\bmember_plaintext\b",
        r"\bADC\b",
        r"application_default_credentials",
    ]
]

RED_TEAM_PATTERNS = {
    "RT_SECRET_EXPOSURE": re.compile(
        r"\b(secret|token|password|private[_ -]?key|credential|api[_ -]?key)\b|密鑰|憑證|密碼",
        re.IGNORECASE,
    ),
    "RT_AUTHORITY_BYPASS": re.compile(
        r"\b(bypass|privilege escalation|auth(?:ority|entication) bypass)\b|繞過權限|越權",
        re.IGNORECASE,
    ),
    "RT_DESTRUCTIVE_ACTION": re.compile(
        r"\b(rm\s+-rf|wipe|destroy|drop\s+database)\b|刪除全部|銷毀|破壞",
        re.IGNORECASE,
    ),
    "RT_PAYMENT_OR_FINANCIAL_EXECUTION": re.compile(
        r"\b(payment|refund|wire transfer|charge card)\b|付款|退款|匯款|扣款",
        re.IGNORECASE,
    ),
    "RT_MEMBER_PLAINTEXT": re.compile(r"\bmember plaintext\b|會員明文", re.IGNORECASE),
    "RT_EVIDENCE_DELETION": re.compile(r"\bdelete evidence\b|刪除證據|湮滅證據", re.IGNORECASE),
    "RT_PRODUCTION_MUTATION": re.compile(
        r"\b(production mutation|deploy|restart|db write|router write)\b|正式環境寫入|生產變更",
        re.IGNORECASE,
    ),
}


class AgentHold(RuntimeError):
    """Raised for governed HOLD paths."""


@dataclass(frozen=True)
class AgentConfig:
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = DEFAULT_ROOT_MODEL
    system_prefix_path: Path = DEFAULT_PREFIX
    skill_manifest_path: Path = DEFAULT_MANIFEST
    credential_available: bool = False
    cloud_completion_enabled: bool = False
    timeout_seconds: float = 10.0
    total_field_root: Path = ROOT
    dynamic_context_max_items: int = 20


def contains_secret_text(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def scrub_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if contains_secret_text(key) or key in FORBIDDEN_OUTPUT_KEYS:
                continue
            cleaned[key] = scrub_sensitive(item)
        return cleaned
    if isinstance(value, list):
        return [scrub_sensitive(item) for item in value if not contains_secret_text(item)]
    if isinstance(value, str):
        if contains_secret_text(value):
            return "[REDACTED_SECRET_OR_MEMBER_PLAINTEXT]"
        return value[:8000]
    return value


def remove_forbidden_outputs(value: Any) -> tuple[Any, list[str]]:
    found: list[str] = []
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key in FORBIDDEN_OUTPUT_KEYS:
                found.append(key)
                continue
            cleaned_item, nested = remove_forbidden_outputs(item)
            found.extend(nested)
            cleaned[key] = cleaned_item
        return cleaned, found
    if isinstance(value, list):
        items = []
        for item in value:
            cleaned_item, nested = remove_forbidden_outputs(item)
            found.extend(nested)
            items.append(cleaned_item)
        return items, found
    if isinstance(value, str):
        for marker in FORBIDDEN_OUTPUT_KEYS:
            if marker in value:
                found.append(marker)
        return value, found
    return value, found


def parse_ollama_response(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {"text": parsed}
    except json.JSONDecodeError:
        return {"text": text}


def detect_red_team_alerts(text: str) -> list[dict[str, str]]:
    alerts = []
    for code, pattern in RED_TEAM_PATTERNS.items():
        match = pattern.search(text)
        if match:
            alerts.append(
                {
                    "code": code,
                    "matched_reason": match.group(0)[:120],
                    "action_disposition": "HOLD_REQUESTED_ACTION",
                    "safe_analysis": "AVAILABLE_AS_CANDIDATE",
                }
            )
    return alerts


def default_receive_candidate_import() -> Callable[..., Any] | None:
    for module_name in [
        "tools.total_field_dynamic_context",
        "total_field_candidate_gateway",
        "tools.total_field_candidate_gateway",
        "xiaoj_candidate_adapter",
        "cloud_agent_candidate_provider",
        "tfct_true8d_runtime_candidate",
    ]:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        receiver = getattr(module, "receive_candidate", None)
        if callable(receiver):
            return receiver
    return None


class OllamaXiaoJTotalFieldAgent:
    def __init__(
        self,
        config: AgentConfig | None = None,
        *,
        receive_candidate: Callable[[Mapping[str, Any]], Any] | None = None,
        cloud_candidate_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        dynamic_context_provider: Callable[[str, int], Mapping[str, Any]] | None = None,
        skill_bridge: OllamaTotalFieldSkillBridge | None = None,
    ) -> None:
        self.config = config or AgentConfig()
        self.receive_candidate = receive_candidate if receive_candidate is not None else default_receive_candidate_import()
        self.cloud_candidate_provider = (
            cloud_candidate_provider
            if cloud_candidate_provider is not None
            else self._default_cloud_candidate_provider_import()
        )
        self.dynamic_context_provider = dynamic_context_provider or self._default_dynamic_context_provider
        self.skill_bridge = skill_bridge

    def run(
        self,
        *,
        source: str,
        prompt: str,
        skill_id: str | None = None,
        use_cloud_completion: bool = False,
        authority_ref: Any = None,
    ) -> dict[str, Any]:
        if source not in {"TOTAL_FIELD_PULL", "LLM_PUSH"}:
            return self._hold("HOLD_UNSUPPORTED_SOURCE", source=source)
        if self.receive_candidate is None:
            return self._hold("HOLD_NO_GATEWAY", source=source)
        if contains_secret_text(prompt):
            return self._hold("HOLD_SECRET_OR_MEMBER_PLAINTEXT_INPUT", source=source)

        bridge = self._skill_bridge_or_hold(source)
        if isinstance(bridge, dict):
            return bridge

        selected_skill = skill_id or "total_field_policy_check"
        skill_result = bridge.invoke(selected_skill, {"prompt": prompt, "source": source})
        if str(skill_result.get("state", "")).startswith("HOLD"):
            return self._hold(str(skill_result["state"]), source=source, evidence=skill_result)

        dynamic_context = self._load_dynamic_context(source=source, prompt=prompt)
        if str(dynamic_context.get("state", "")).startswith("HOLD"):
            return self._hold(str(dynamic_context["state"]), source=source, evidence=dynamic_context)

        if not self.config.credential_available:
            return self._hold("HOLD_NO_CREDENTIAL", source=source)

        ollama_result = self._call_ollama(
            source=source,
            prompt=prompt,
            skill_result=skill_result,
            dynamic_context=dynamic_context,
        )
        red_team_alerts = detect_red_team_alerts(prompt)
        cloud_result = None
        if use_cloud_completion or self.config.cloud_completion_enabled:
            cloud_result = self._call_cloud_candidate_provider(
                source=source,
                prompt=prompt,
                skill_result=skill_result,
                ollama_result=ollama_result,
                dynamic_context=dynamic_context,
                red_team_alerts=red_team_alerts,
            )
            if str(cloud_result.get("state", "")).startswith("HOLD"):
                return self._hold(str(cloud_result["state"]), source=source, evidence=cloud_result)

        candidate = self._build_candidate(
            source,
            prompt,
            selected_skill,
            skill_result,
            ollama_result,
            dynamic_context=dynamic_context,
            cloud_result=cloud_result,
            red_team_alerts=red_team_alerts,
        )
        total_field_decision = self._deliver_candidate(
            candidate,
            dynamic_context=dynamic_context,
            authority_ref=authority_ref,
        )
        if isinstance(total_field_decision, Mapping):
            decision_state = str(total_field_decision.get("decision", "HOLD_EVIDENCE_INCOMPLETE"))
            return {
                "state": decision_state,
                "source": source,
                "candidate": candidate,
                "total_field_decision": dict(total_field_decision),
            }
        return {
            "state": "CANDIDATE_RECEIVED",
            "source": source,
            "candidate": candidate,
        }

    def _deliver_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        dynamic_context: Mapping[str, Any],
        authority_ref: Any,
    ) -> Any:
        receiver = self.receive_candidate
        if receiver is None:
            return None
        try:
            parameters = tuple(inspect.signature(receiver).parameters.values())
        except (TypeError, ValueError):
            parameters = ()
        accepts_governed_contract = any(
            parameter.kind is inspect.Parameter.VAR_POSITIONAL for parameter in parameters
        ) or len(
            [
                parameter
                for parameter in parameters
                if parameter.kind
                in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
        ) >= 3
        if accepts_governed_contract:
            return receiver(candidate, dynamic_context, authority_ref)
        return receiver(candidate)

    def _default_cloud_candidate_provider_import(self) -> Callable[[Mapping[str, Any]], Mapping[str, Any]] | None:
        for module_name in [
            "cloud_agent_candidate_provider",
            "tools.cloud_agent_candidate_provider",
        ]:
            try:
                module = importlib.import_module(module_name)
            except Exception:
                continue
            for attr in ["complete_candidate", "generate_candidate", "cloud_complete_candidate"]:
                provider = getattr(module, attr, None)
                if callable(provider):
                    return provider
        return None

    def _default_dynamic_context_provider(self, query: str, max_items: int) -> Mapping[str, Any]:
        return build_dynamic_context(
            query,
            root=self.config.total_field_root,
            max_items=max_items,
        )

    def _load_dynamic_context(self, *, source: str, prompt: str) -> dict[str, Any]:
        try:
            packet = dict(self.dynamic_context_provider(prompt, self.config.dynamic_context_max_items))
        except Exception as exc:
            return {
                "state": "HOLD_TOTAL_FIELD_CONTEXT_PROVIDER_ERROR",
                "source": source,
                "reason": f"{type(exc).__name__}:{exc}",
            }
        if contains_secret_text(packet):
            return {
                "state": "HOLD_SECRET_OR_MEMBER_PLAINTEXT_INPUT",
                "source": source,
                "reason": "dynamic context failed sensitive-data guard",
            }
        if packet.get("state") != "TOTAL_FIELD_DYNAMIC_CONTEXT_READY":
            packet.setdefault("state", "HOLD_TOTAL_FIELD_CONTEXT_INVALID")
        return packet

    def _call_cloud_candidate_provider(
        self,
        *,
        source: str,
        prompt: str,
        skill_result: Mapping[str, Any],
        ollama_result: Mapping[str, Any],
        dynamic_context: Mapping[str, Any],
        red_team_alerts: list[dict[str, str]],
    ) -> dict[str, Any]:
        if not self.config.credential_available:
            return {"state": "HOLD_NO_CREDENTIAL", "candidate": None}
        if self.cloud_candidate_provider is None:
            return {"state": "HOLD_NO_CLOUD_PROVIDER", "candidate": None}
        request = {
            "mode": "cloud_precision_logic_candidate_only",
            "source": source,
            "user_intent": scrub_sensitive(prompt),
            "intent_projection": scrub_sensitive(
                dict((dynamic_context.get("capability_route") or {}).get("d1_intent_projection") or {})
            ),
            "total_field_dynamic_context": scrub_sensitive(dict(dynamic_context)),
            "skill_evidence": scrub_sensitive(dict(skill_result)),
            "local_root_logic_candidate": scrub_sensitive(dict(ollama_result)),
            "red_team_alerts": scrub_sensitive(red_team_alerts),
            "fusion_contract": {
                "method": "LOCAL_ROOT_PLUS_CLOUD_LOGIC_THEN_TOTAL_FIELD_VALIDATE",
                "prefer_verified_evidence": True,
                "preserve_user_intent": True,
                "cloud_may_replace_local_root": False,
            },
            "policy": {
                "candidate_only": True,
                "maximum_verified_detail_within_privacy_boundary": True,
                "raw_private_context_to_cloud": False,
                "db_write": False,
                "deploy": False,
                "restart": False,
                "router_write": False,
                "canonical_pointer_write": False,
                "credential_output": False,
                "member_plaintext_output": False,
            },
        }
        if contains_secret_text(request):
            return {"state": "HOLD_SECRET_OR_MEMBER_PLAINTEXT_INPUT", "candidate": None}
        try:
            response = dict(self.cloud_candidate_provider(request))
        except Exception as exc:
            return {"state": "HOLD_CLOUD_PROVIDER_ERROR", "candidate": None, "error": str(exc)}
        if contains_secret_text(response):
            return {"state": "HOLD_SECRET_OR_MEMBER_PLAINTEXT_OUTPUT", "candidate": None}
        cleaned, forbidden = remove_forbidden_outputs(response)
        return {
            "state": "CLOUD_CANDIDATE_FRAGMENT_READY",
            "candidate": scrub_sensitive(cleaned),
            "removed_forbidden_output_count": len(set(forbidden)),
        }

    def _skill_bridge_or_hold(self, source: str) -> OllamaTotalFieldSkillBridge | dict[str, Any]:
        if self.skill_bridge is not None:
            return self.skill_bridge
        if not self.config.skill_manifest_path.exists():
            return self._hold("HOLD_NO_SKILL", source=source)
        try:
            return OllamaTotalFieldSkillBridge(
                self.config.skill_manifest_path,
                credential_available=self.config.credential_available,
            )
        except Exception as exc:
            return self._hold("HOLD_NO_SKILL", source=source, evidence={"error": str(exc)})

    def _call_ollama(
        self,
        *,
        source: str,
        prompt: str,
        skill_result: Mapping[str, Any],
        dynamic_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        system_prefix = self.config.system_prefix_path.read_text(encoding="utf-8")
        request_body = {
            "model": self.config.model,
            "stream": False,
            "prompt": (
                system_prefix
                + "\n\nSOURCE="
                + source
                + "\nReturn candidate-only JSON. User intent:\n"
                + prompt
                + "\nTotal Field dynamic context evidence:\n"
                + json.dumps(dynamic_context, ensure_ascii=False, sort_keys=True)
                + "\nSkill evidence:\n"
                + json.dumps(skill_result, ensure_ascii=False, sort_keys=True)
            ),
        }
        url = self.config.ollama_url.rstrip("/") + "/api/generate"
        request = urllib.request.Request(
            url,
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AgentHold(f"HOLD_OLLAMA_UNAVAILABLE:{exc}") from exc
        return parse_ollama_response(str(payload.get("response", "")))

    def _build_candidate(
        self,
        source: str,
        prompt: str,
        skill_id: str,
        skill_result: Mapping[str, Any],
        ollama_result: Mapping[str, Any],
        *,
        dynamic_context: Mapping[str, Any],
        cloud_result: Mapping[str, Any] | None = None,
        red_team_alerts: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        cleaned_ollama, forbidden = remove_forbidden_outputs(ollama_result)
        cleaned_ollama = scrub_sensitive(cleaned_ollama)
        cleaned_cloud = None
        if cloud_result is not None:
            cleaned_cloud, cloud_forbidden = remove_forbidden_outputs(dict(cloud_result))
            forbidden.extend(cloud_forbidden)
            cleaned_cloud = scrub_sensitive(cleaned_cloud)
        candidate = {
            "state": "CANDIDATE_ONLY",
            "agent": "ollama_xiaoj_total_field_agent",
            "source": source,
            "mode": "candidate_only_no_commit",
            "prompt_preview": scrub_sensitive(prompt[:500]),
            "skill_id": skill_id,
            "skill_output": scrub_sensitive(dict(skill_result)),
            "dynamic_context_binding": {
                "state": dynamic_context.get("state"),
                "retrieval_state": dynamic_context.get("retrieval_state"),
                "generated_at": dynamic_context.get("generated_at"),
                "packet_sha256": dynamic_context.get("packet_sha256"),
                "source_binding_count": len(dynamic_context.get("source_bindings") or []),
                "context_item_count": len(dynamic_context.get("context_items") or []),
            },
            "ollama_candidate": cleaned_ollama,
            "cloud_completion_candidate": cleaned_cloud,
            "red_team_alerts": list(red_team_alerts or []),
            "policy": {
                "ollama_generates_candidate_only": True,
                "cloud_completion_candidate_only": cloud_result is not None,
                "receive_candidate_only": True,
                "dynamic_total_field_context_required": True,
                "cloud_receives_governed_intent_and_total_field_context": cloud_result is not None,
                "db_write": False,
                "deploy": False,
                "restart": False,
                "router_write": False,
                "canonical_pointer_write": False,
                "credential_output": False,
                "member_plaintext_output": False,
            },
            "removed_forbidden_output_count": len(set(forbidden)),
        }
        if forbidden:
            candidate["state"] = "CANDIDATE_ONLY_WITH_FORBIDDEN_FIELDS_REMOVED"
        return candidate

    def _hold(self, state: str, *, source: str, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return {
            "state": state,
            "source": source,
            "candidate": None,
            "evidence": dict(evidence or {}),
            "policy": {
                "db_write": False,
                "deploy": False,
                "restart": False,
                "router_write": False,
                "canonical_pointer_write": False,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["TOTAL_FIELD_PULL", "LLM_PUSH"], required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default=DEFAULT_ROOT_MODEL)
    parser.add_argument("--skill-id", default="total_field_policy_check")
    parser.add_argument("--credential-available", action="store_true")
    parser.add_argument("--use-cloud-completion", action="store_true")
    args = parser.parse_args()

    config = AgentConfig(
        ollama_url=args.ollama_url,
        model=args.model,
        credential_available=args.credential_available,
        cloud_completion_enabled=args.use_cloud_completion,
    )
    agent = OllamaXiaoJTotalFieldAgent(config)
    try:
        result = agent.run(
            source=args.source,
            prompt=args.prompt,
            skill_id=args.skill_id,
            use_cloud_completion=args.use_cloud_completion,
        )
    except AgentHold as exc:
        result = {
            "state": str(exc).split(":", 1)[0],
            "candidate": None,
            "evidence": {"reason": str(exc)},
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if str(result.get("state", "")).startswith(("CANDIDATE", "HOLD")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
