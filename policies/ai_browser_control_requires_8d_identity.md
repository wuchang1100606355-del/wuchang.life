# AI Browser Control Requires 8D Identity

AI 控制瀏覽器前，必須先通過 8D 加密身分碼驗證。

## Hard Rule

No 8D encrypted identity code, no AI browser control.

## Required State

- 7D identity code exists
- 8D encrypted envelope exists
- sha256 verified
- local human review required
- no raw PII output
- no credential echo
- no secret logging
- browser control scope must be explicit

## Allowed After Verification

- open browser
- navigate pages
- fill non-secret form fields
- guide OAuth settings
- stop before password / 2FA / payment / irreversible actions
