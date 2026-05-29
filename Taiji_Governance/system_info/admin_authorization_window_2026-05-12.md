# Admin Authorization Window

Version: 2026-05-12

## Account

```text
admin@wuchang.life
```

## Purpose

Open a human-controlled Google authorization window for organization readonly cloud dependency staging.

This record does not grant credential access to AI, scripts, or deployment runtime. It only defines the authorized human login account and the audit boundary for this authorization window.

## Governance Boundary

- Google API direct mutation: not performed
- Credential/token/service account JSON reading: forbidden
- Credential/token/service account JSON storage: forbidden
- Secret material output: forbidden
- Human login and approval: required
- Upload scope: non-sensitive readonly dependency package only
- Reverse sync from cloud to source: forbidden

## Target

```text
Google Drive folder: 1PwybNATp-pPZ8DJiTEJbga3mJO1p4NCn
```

## Risk

```text
L1_near = allow_with_audit
```
