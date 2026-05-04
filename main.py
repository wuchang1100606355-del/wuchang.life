from datetime import datetime, timezone
from core.event_test import run_event_test

SYSTEM_NAME = "Wuchang Smart Cloud / Xiao J"
MODE = "development-prototype / non-operational"

BOUNDARIES = [
    "No personal-data backdoor",
    "No Cloudflare DNS API or automated DNS mutation",
    "Do not modify Google Nonprofits / Workspace DNS records",
    "Odoo is separated account-book public-interest cashflow prototype only",
    "Xiao J is controlled read-only / human-in-loop AI assistant",
]

def main():
    print(f"{SYSTEM_NAME}")
    print(f"Mode: {MODE}")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("Boundaries:")
    for item in BOUNDARIES:
        print(f"- {item}")
    run_event_test()

if __name__ == "__main__":
    main()
