# Pre-Activation Cutover Checklist

版本：2026-05-11

## Required Before Production Activation

- [ ] API keys revoked/rotated
- [ ] OAuth tokens revoked/rotated
- [ ] service account keys revoked/rotated
- [ ] private keys rotated
- [ ] passwords rotated
- [ ] webhook/tunnel tokens rotated
- [ ] test admin accounts disabled/downgraded/replaced
- [ ] test member-like data deleted or anonymized
- [ ] test POS data reset
- [ ] test Odoo data reset/rebuilt
- [ ] browser sessions invalidated
- [ ] production environment rebuilt from approved baseline
- [ ] SHA256 baseline generated
- [ ] rollback plan generated
- [ ] owner approval recorded

## Production Activation Rule

Do not activate production if any development credential, test account, or test personal-like data remains active.

