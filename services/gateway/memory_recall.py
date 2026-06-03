import os
import json

BASE = os.path.expanduser("~/Taiji_Hub/runtime/memory/conversations")

def list_events(limit=10):

    files = sorted(
        os.listdir(BASE),
        reverse=True
    )[:limit]

    events = []

    for file in files:

        path = f"{BASE}/{file}"

        with open(path, "r") as f:
            data = json.load(f)

        data["_file"] = file
        events.append(data)

    return events

def search_events(query):

    query = query.lower()

    results = []

    for file in sorted(os.listdir(BASE), reverse=True):

        path = f"{BASE}/{file}"

        with open(path, "r") as f:
            data = json.load(f)

        blob = json.dumps(data).lower()

        if query in blob:

            data["_file"] = file
            results.append(data)

    return results
