# Break-glass Recovery Policy

node: MSI
purpose: emergency recovery only
type: audited recovery channel
not_a_backdoor: true

## Allowed Recovery Paths

1. Local Windows console
2. Local WSL terminal
3. SSH via trusted private network only
4. Tailscale/VPN management path if already authenticated

## Forbidden

- No public unauthenticated admin port
- No permanent bypass of gateway
- No hidden credential
- No unrestricted remote shell
- No disabling audit logs

## Required Controls

- Every recovery action must write audit log
- Recovery mode must be temporary
- Recovery mode must have rollback command
- Gateway enforcement may be paused only for repair
