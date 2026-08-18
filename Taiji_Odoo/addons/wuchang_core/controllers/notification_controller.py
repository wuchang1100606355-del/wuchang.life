# -*- coding: utf-8 -*-
"""Existing store-internal notification carrier with packet-only handoff events."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import re

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)

HANDOFF_CHANNEL = "wuchang_delivery_dispatch"
HANDOFF_NOTIFICATION_TYPE = "wuchang_delivery_dispatch"
HANDOFF_REF_PATTERN = re.compile(r"^handoff-[a-z0-9-]{8,128}$")
TABLE_REF_PATTERN = re.compile(r"^T0?[1-9]\d?$")
TOKEN_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
SAFE_REF_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
RISK_CLASSES = {"LOW", "MEDIUM", "HIGH"}


def _logical_time():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _packet_sha256(packet):
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _as_mapping(value):
    return value if isinstance(value, dict) else {}


def _is_token(value, default):
    candidate = str(value or default).strip().upper()
    return candidate if TOKEN_PATTERN.fullmatch(candidate) else default


def _safe_ref(value):
    candidate = str(value or "").strip()
    return candidate if SAFE_REF_PATTERN.fullmatch(candidate) else None


def _customer_response(state, risk_class):
    if state == "HUMAN_REVIEW_DISPATCHED":
        return "我已經幫你喊人了，我再陪你等等喔～"
    if state == "HUMAN_REVIEW_ACKNOWLEDGED":
        return "收到啦～老闆等等過來。"
    if state == "HUMAN_REVIEW_RESOLVED":
        return "店員已經處理好了，我會繼續在這裡陪你。"
    if state == "HUMAN_REVIEW_DISPATCH_FAILED":
        return "糟糕，我剛剛沒叫到人，我再想別的辦法～"
    if risk_class == "HIGH":
        return "這件事需要店員確認，我先不亂處理，馬上幫你找人。"
    if risk_class == "MEDIUM":
        return "這題我想確認一下，我幫你叫店員過來喔。"
    return "老闆～這個我不會啦，快來救我一下～"


def _internal_staff_session():
    user = getattr(getattr(request, "env", None), "user", None)
    has_group = getattr(user, "has_group", None)
    if callable(has_group):
        try:
            return bool(has_group("base.group_user"))
        except Exception:
            return False
    return bool(getattr(user, "id", False))


def _publish(payload):
    bus = request.env["bus.bus"]
    sender = getattr(bus, "_sendone", None)
    if not callable(sender):
        raise RuntimeError("store_internal_bus_unavailable")
    sender(HANDOFF_CHANNEL, HANDOFF_NOTIFICATION_TYPE, payload)


def _receipt(kind, handoff_ref, status, **fields):
    packet = {
        "packet_kind": kind,
        "handoff_ref": handoff_ref,
        "channel_ref": HANDOFF_CHANNEL,
        "logical_time": _logical_time(),
        "status": status,
        **fields,
    }
    packet["evidence_ref"] = "sha256:" + _packet_sha256(packet)
    return packet


def _handoff_request(data):
    handoff_ref = str(data.get("handoff_ref") or "").strip().lower()
    if not HANDOFF_REF_PATTERN.fullmatch(handoff_ref):
        return None, "invalid_handoff_ref"
    table_ref = str(data.get("table_ref") or "").strip().upper()
    if table_ref and not TABLE_REF_PATTERN.fullmatch(table_ref):
        return None, "invalid_table_ref"
    risk_class = str(data.get("risk_class") or "LOW").strip().upper()
    if risk_class not in RISK_CLASSES:
        return None, "invalid_risk_class"
    evidence_ref = _safe_ref(data.get("non_pii_evidence_ref"))
    payload = {
        "action": "new_mission_alert",
        "data": {
            "handoff_ref": handoff_ref,
            "problem_class": _is_token(data.get("problem_class"), "GENERAL_SERVICE_ASSISTANCE"),
            "table_ref": table_ref or None,
            "general_assistance_request": "GENERAL_ASSISTANCE_REQUESTED",
            "risk_class": risk_class,
            "non_pii_evidence_ref": evidence_ref,
        },
    }
    return payload, None


class NotificationController(http.Controller):
    @http.route("/api/notification/broadcast", type="json", auth="public", methods=["POST"], csrf=False)
    def broadcast_notification(self, **kwargs):
        data = _as_mapping(getattr(request, "jsonrequest", None))
        action = str(data.get("action") or "").strip()

        if action == "handoff_request":
            payload, error = _handoff_request(data)
            if error:
                return {"success": False, "state": "DISPATCH_FAILED", "reason": error}
            handoff_ref = payload["data"]["handoff_ref"]
            try:
                receipt = _receipt("HANDOFF_DISPATCH_RECEIPT", handoff_ref, "DISPATCH_ACCEPTED")
                payload["receipt"] = receipt
                _publish(payload)
            except Exception:
                _logger.warning("store-internal handoff dispatch unavailable")
                return {
                    "success": False,
                    "state": "HUMAN_REVIEW_DISPATCH_FAILED",
                    "customer_response": _customer_response("HUMAN_REVIEW_DISPATCH_FAILED", payload["data"]["risk_class"]),
                }
            return {
                "success": True,
                "state": "HUMAN_REVIEW_DISPATCHED",
                "receipt": receipt,
                "customer_response": _customer_response("HUMAN_REVIEW_DISPATCHED", payload["data"]["risk_class"]),
            }

        if action == "human_acknowledge":
            if not _internal_staff_session():
                return {"success": False, "state": "HUMAN_ACK_DENIED"}
            handoff_ref = str(data.get("handoff_ref") or "").strip().lower()
            if not HANDOFF_REF_PATTERN.fullmatch(handoff_ref):
                return {"success": False, "state": "HUMAN_ACK_DENIED", "reason": "invalid_handoff_ref"}
            receipt = _receipt(
                "HUMAN_ACK_PACKET",
                handoff_ref,
                "ACCEPTED",
                human_role_ref="ODOO_INTERNAL_USER",
            )
            try:
                _publish({"action": "mission_taken", "data": {"handoff_ref": handoff_ref}, "receipt": receipt})
            except Exception:
                _logger.warning("store-internal handoff acknowledgement unavailable")
                return {"success": False, "state": "HUMAN_ACK_FAILED"}
            return {
                "success": True,
                "state": "HUMAN_REVIEW_ACKNOWLEDGED",
                "receipt": receipt,
                "customer_response": _customer_response("HUMAN_REVIEW_ACKNOWLEDGED", "LOW"),
            }

        if action == "human_resolution":
            if not _internal_staff_session():
                return {"success": False, "state": "HUMAN_RESOLUTION_DENIED"}
            handoff_ref = str(data.get("handoff_ref") or "").strip().lower()
            if not HANDOFF_REF_PATTERN.fullmatch(handoff_ref):
                return {"success": False, "state": "HUMAN_RESOLUTION_DENIED", "reason": "invalid_handoff_ref"}
            result_packet = _receipt(
                "HUMAN_REVIEW_RESULT_PACKET",
                handoff_ref,
                "RESOLVED",
                result_class=_is_token(data.get("result_class"), "GENERAL_ASSISTANCE_RESOLVED"),
                human_action_semantic=_is_token(data.get("human_action_semantic"), "STAFF_ASSISTANCE"),
                human_response_semantic=_is_token(data.get("human_response_semantic"), "GENERAL_ASSISTANCE_PROVIDED"),
                odoo_result_ref=_safe_ref(data.get("odoo_result_ref")),
                canonical_promotion=False,
            )
            try:
                _publish({"action": "mission_resolved", "data": {"handoff_ref": handoff_ref}, "receipt": result_packet})
            except Exception:
                _logger.warning("store-internal handoff resolution unavailable")
                return {"success": False, "state": "HUMAN_RESOLUTION_FAILED"}
            return {
                "success": True,
                "state": "HUMAN_REVIEW_RESOLVED",
                "result_packet": result_packet,
                "customer_response": _customer_response("HUMAN_REVIEW_RESOLVED", "LOW"),
            }

        _logger.info("generic notification received without handoff dispatch")
        return {"success": True, "state": "NOTIFICATION_RECEIVED_NO_DISPATCH"}

    @http.route("/api/notification/design_report", type="http", auth="public", methods=["GET"], csrf=False)
    def get_design_report_notification(self, **kwargs):
        notification = {
            "title": "小J 指揮通道設計方案報告",
            "message": "專用指揮通道 UI 設計方案已完成，請查看報告。",
            "report_url": "/design_report",
            "command_center_url": "/command_center",
            "access_code": "J2025",
            "status": "ready",
        }
        return request.make_response(
            json.dumps(notification, ensure_ascii=False),
            headers=[("Content-Type", "application/json")],
        )
