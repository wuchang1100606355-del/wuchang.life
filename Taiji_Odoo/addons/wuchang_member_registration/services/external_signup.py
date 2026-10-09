from __future__ import annotations

import hashlib
import json
import re

from odoo import fields
from odoo.exceptions import AccessDenied, UserError
from odoo.addons.web.controllers.utils import _get_login_redirect_url


_ALLOWED_PROVIDERS = {"google", "line"}
_HASH_REF = re.compile(r"^[a-z][a-z0-9_.-]*:sha256:[0-9a-f]{64}$")


def _canonical_sha256(value: dict) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _hash_ref(namespace: str, value: str) -> str:
    return f"{namespace}:sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized_email(value: str | None) -> str:
    return str(value or "").strip().lower()


def _truthy_verified(value) -> bool:
    return value is True or str(value or "").strip().lower() == "true"


def build_provider_callback_evidence_ref(
    provider: str,
    *,
    subject: str,
    state: str,
    issued_at_epoch: int,
) -> str:
    provider = str(provider or "").strip().lower()
    if provider not in _ALLOWED_PROVIDERS or not subject or not state:
        raise ValueError("verified_provider_callback_material_invalid")
    material = {
        "schema": "WUCHANG_VERIFIED_PROVIDER_CALLBACK/1",
        "provider": provider,
        "provider_subject_ref": _hash_ref(f"provider:{provider}", subject),
        "state_ref": _hash_ref("oauth_state", state),
        "issued_at_epoch": int(issued_at_epoch),
    }
    return "provider_callback_ref:sha256:" + _canonical_sha256(material)


def _verified_binding_ref(
    *,
    provider: str,
    subject_hash: str,
    user_id: int,
    provisional_member_ref: str,
    callback_evidence_ref: str,
) -> str:
    if not _HASH_REF.fullmatch(callback_evidence_ref or ""):
        raise ValueError("callback_evidence_ref_invalid")
    material = {
        "schema": "WUCHANG_VERIFIED_CHANNEL_BINDING/1",
        "provider": provider,
        "provider_subject_hash": subject_hash,
        "member_user_ref": _hash_ref("member_user_ref", f"member-user:{user_id}"),
        "member_registration_ref": _hash_ref(
            "member_registration_ref", provisional_member_ref
        ),
        "callback_evidence_ref": callback_evidence_ref,
    }
    return "verified_channel_binding_ref:sha256:" + _canonical_sha256(material)


def _ensure_subject_group(env, user) -> None:
    subject_group = env.ref(
        "wuchang_member_registration.group_wuchang_member_subject",
        raise_if_not_found=False,
    )
    if subject_group and subject_group not in user.groups_id:
        user.sudo().write({"groups_id": [(4, subject_group.id)]})


def _find_google_user(env, email: str):
    if not email:
        return env["res.users"]
    users = env["res.users"].sudo().search(
        [
            "|",
            ("login", "=ilike", email),
            ("email", "=ilike", email),
        ],
        limit=3,
    )
    if len(users) > 1:
        raise UserError("HOLD_VERIFIED_EMAIL_MATCH_AMBIGUOUS")
    return users[:1]


def _create_minimum_user(
    env,
    *,
    provider: str,
    subject_hash: str,
    display_name: str,
    verified_email: str,
):
    portal_group = env.ref("base.group_portal", raise_if_not_found=False)
    subject_group = env.ref(
        "wuchang_member_registration.group_wuchang_member_subject",
        raise_if_not_found=False,
    )
    group_ids = [
        group.id for group in (portal_group, subject_group) if group
    ]
    login = verified_email or f"{provider}_{subject_hash[:24]}"
    values = {
        "name": (display_name or "小J會員").strip()[:160] or "小J會員",
        "login": login,
        "active": True,
        "tz": "Asia/Taipei",
    }
    if verified_email:
        values["email"] = verified_email
    if group_ids:
        values["groups_id"] = [(6, 0, group_ids)]
    return env["res.users"].sudo().with_context(no_reset_password=True).create(values)


def _find_or_create_registration(env, *, user, provider: str):
    registration_model = env["wuchang.member.registration"]
    registration = registration_model.sudo().search(
        [
            ("create_uid", "=", user.id),
            ("member_type", "=", "individual"),
            ("review_status", "=", "approved"),
        ],
        order="id desc",
        limit=1,
    )
    if not registration:
        registration = registration_model.sudo().search(
            [
                ("create_uid", "=", user.id),
                ("member_type", "=", "individual"),
                ("review_status", "in", ["draft", "pending_review"]),
            ],
            order="id desc",
            limit=1,
        )
    if registration:
        return registration
    return registration_model.with_user(user).sudo().create(
        {
            "registration_channel": provider,
            "review_status": "draft",
            "consent_version": f"{provider}_oauth_member_v1",
            "member_type": "individual",
            "role_scope": "member",
            "service_scope": "community_member_service",
        }
    )


def ensure_verified_external_applicant(
    env,
    *,
    provider: str,
    subject: str,
    display_name: str = "",
    email: str = "",
    email_verified=False,
    callback_evidence_ref: str,
) -> dict:
    provider = str(provider or "").strip().lower()
    subject = str(subject or "").strip()
    if provider not in _ALLOWED_PROVIDERS or not subject:
        raise UserError("HOLD_VERIFIED_PROVIDER_SUBJECT_REQUIRED")

    external = env["wuchang.member.external.auth"].sudo()
    subject_hash = external.hash_subject(provider, subject)
    binding = external.search(
        [
            ("provider", "=", provider),
            ("provider_subject_hash", "=", subject_hash),
        ],
        limit=1,
    )

    user = binding.member_user_id.sudo() if binding else env["res.users"]
    if binding and binding.binding_status == "revoked":
        raise AccessDenied("HOLD_PROVIDER_BINDING_REVOKED")
    if user and not user.active:
        raise AccessDenied("HOLD_LOCAL_ACCOUNT_INACTIVE")

    verified_email = ""
    if provider == "google" and _truthy_verified(email_verified):
        verified_email = _normalized_email(email)

    if not user:
        user = _find_google_user(env, verified_email) if provider == "google" else env["res.users"]
    if not user:
        user = _create_minimum_user(
            env,
            provider=provider,
            subject_hash=subject_hash,
            display_name=display_name,
            verified_email=verified_email,
        )

    _ensure_subject_group(env, user)
    registration = (
        env["wuchang.member.registration"].sudo().browse(binding.registration_ref_id).exists()
        if binding and binding.registration_ref_id
        else env["wuchang.member.registration"]
    )
    if not registration:
        registration = _find_or_create_registration(env, user=user, provider=provider)

    identity = registration.identity_code_id
    if not identity:
        identity = env["wuchang.member.identity.code"].sudo().search(
            [("registration_ref_id", "=", registration.id)],
            limit=1,
        )

    verified_ref = _verified_binding_ref(
        provider=provider,
        subject_hash=subject_hash,
        user_id=user.id,
        provisional_member_ref=registration.provisional_member_id,
        callback_evidence_ref=callback_evidence_ref,
    )
    binding_values = {
        "binding_status": "bound",
        "verified_channel_binding_ref": verified_ref,
        "last_login_at": fields.Datetime.now(),
    }
    if identity:
        binding_values["member_identity_id"] = identity.id

    if binding:
        if binding.member_user_id != user:
            raise AccessDenied("HOLD_CROSS_MEMBER_PROVIDER_BINDING")
        binding.with_user(user).sudo().write(binding_values)
    else:
        create_values = {
            "registration_ref_id": registration.id,
            "provisional_member_ref": registration.provisional_member_id,
            "member_user_id": user.id,
            "provider": provider,
            "provider_subject_hash": subject_hash,
            **binding_values,
        }
        binding = external.with_user(user).sudo().create(create_values)

    return {
        "user": user,
        "registration": registration,
        "binding": binding,
        "membership_active": bool(
            registration.review_status == "approved"
            and registration.identity_code_id
            and registration.identity_code_id.active_status == "active"
        ),
        "new_member_data_required": registration.review_status == "draft",
    }


def begin_verified_external_session(request, user, *, redirect_path: str) -> str:
    if not user or not user.active:
        raise AccessDenied("HOLD_LOCAL_ACCOUNT_INACTIVE")
    if request.session.uid and request.session.uid != user.id:
        raise AccessDenied("HOLD_CROSS_MEMBER_ACTIVE_SESSION")
    if request.session.uid == user.id:
        return redirect_path

    request.session.uid = None
    request.session.pre_login = user.login
    request.session.pre_uid = user.id
    mfa_url = request.env(user=user.id)["res.users"].browse(user.id)._mfa_url()
    if mfa_url:
        return _get_login_redirect_url(user.id, redirect=redirect_path)

    request.session.finalize(request.env(user=user.id))
    request.update_env(user=request.session.uid)
    request.update_context(**request.session.context)
    return redirect_path
