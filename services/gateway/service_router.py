import os
import json
import requests

BASE = os.path.expanduser("~/Taiji_Hub/runtime")

SERVICES = f"{BASE}/registry/runtime_service_registry.json"

def load_services():

    with open(SERVICES, "r") as f:

        return json.load(f)

def resolve(service):

    services = load_services()

    if service not in services:

        return None

    return services[service]

def proxy_get(service, path="/"):

    target = resolve(service)

    if not target:

        return {
            "error": "service_not_found"
        }

    url = (
        f"http://{target['host']}:"
        f"{target['port']}{path}"
    )

    try:

        r = requests.get(
            url,
            timeout=10
        )

        return {
            "status": r.status_code,
            "data": r.text
        }

    except Exception as e:

        return {
            "error": str(e)
        }
