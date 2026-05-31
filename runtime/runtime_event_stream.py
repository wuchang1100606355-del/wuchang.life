from fastapi import FastAPI
import os
import json

app = FastAPI()

BASE = "/home/taiji_admin/Taiji_Hub/runtime/outbox"

@app.get("/events")
async def events():

    results = []

    if not os.path.exists(BASE):

        return {
            "events": []
        }

    for file in sorted(os.listdir(BASE), reverse=True)[:50]:

        path = f"{BASE}/{file}"

        try:

            with open(path, "r") as f:

                data = json.load(f)

            data["_file"] = file

            results.append(data)

        except:
            pass

    return {
        "events": results
    }
