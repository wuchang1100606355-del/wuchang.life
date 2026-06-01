# Router Join Criteria

status: NOT_READY

Router may join Tailscale only after:

1. ACL / Grants reviewed and saved.
2. tag:router exists.
3. cloud-worker cannot access full LAN.
4. subnet routes are limited.
5. router is not exit node unless explicitly needed.
6. router does not hold Google / Odoo / AI secrets.
7. break-glass local access path exists.
8. rollback plan exists.

Router allowed:
- subnet routing
- LAN boundary
- emergency path

Router denied:
- AI executor
- Google Admin broker
- Odoo DB host
- secret vault
- host_root bridge
