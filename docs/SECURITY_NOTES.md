# Security Notes

## Current Risks
- `.env` and `keys/` must never be committed.
- Gateway authentication is not yet enforced.
- Replay protection is partial.
- DB migration is absent.

## Immediate Rules
- No secrets in Git.
- All external traffic should enter through `services/gateway`.
- Add `/health` before adding business logic.
