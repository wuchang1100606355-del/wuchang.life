# D8 Local Dashboard Usage

Start the local dashboard:

```bash
python tools/d8_local_dashboard.py --host 127.0.0.1 --port 8787
```

The dashboard binds only to the local machine by default. It refuses non-local hosts and does not read secrets or production configuration.

Routes:

- `/`: overview
- `/status`: D8 console status
- `/doctor`: D8 console doctor
- `/alerts`: non-executable possible alerts
- `/redteam`: quarantined redteam events
- `/evals`: guard evaluations
- `/preflight`: preflight form
- `/writeback`: disabled unless started with `--enable-writeback`
- `/seal`: console seal

Default behavior is read-only except preflight guard evaluation writes. No production DB writes, restarts, deploys, external API calls, or embeddings are performed.
