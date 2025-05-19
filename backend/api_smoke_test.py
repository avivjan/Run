#!/usr/bin/env python3
"""
Simple smoke-test for Runner/Trainer MVP API.
Creates an event, joins it, and verifies user/event queries.
Outputs a JSON log you can share back for review.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://runfuncionapp.azurewebsites.net/api"
RUNNER_ID  = "user123"
TRAINER_ID = "user456"

def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

log = []  # list of dicts with step / status / response

def add_log(step, method, url, payload, resp):
    log.append({
        "step": step,
        "method": method,
        "url": url,
        "payload": payload,
        "status_code": resp.status_code,
        "response": resp.json() if resp.headers.get("content-type","").startswith("application/json") else resp.text
    })

def main():
    # 1. getUser runner
    url = f"{BASE_URL}/getUser"
    resp = requests.get(url, params={"userId": RUNNER_ID})
    add_log("getUser runner", "GET", resp.url, None, resp)

    # 2. getUser trainer
    resp = requests.get(url, params={"userId": TRAINER_ID})
    add_log("getUser trainer", "GET", resp.url, None, resp)

    # 3. createEvent
    url = f"{BASE_URL}/createEvent"
    payload = {"timestamp": iso_now(), "trainerId": TRAINER_ID}
    resp = requests.post(url, json=payload)
    add_log("createEvent", "POST", url, payload, resp)
    assert resp.ok, "createEvent failed"
    event_id = resp.json()["eventId"]

    # 4. getAllOpenEvents
    url = f"{BASE_URL}/getAllOpenEvents"
    resp = requests.get(url)
    add_log("getAllOpenEvents", "GET", url, None, resp)

    # 5. joinEvent
    url = f"{BASE_URL}/joinEvent"
    payload = {"eventId": event_id, "userId": RUNNER_ID}
    resp = requests.post(url, json=payload)
    add_log("joinEvent", "POST", url, payload, resp)

    # 6. getUsersEvents
    url = f"{BASE_URL}/getUsersEvents"
    resp = requests.get(url, params={"userId": RUNNER_ID})
    add_log("getUsersEvents", "GET", resp.url, None, resp)

    # save results
    outfile = Path(f"api_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
    outfile.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"✅ Test finished. Results saved to {outfile.resolve()}")
    # quick console summary
    for entry in log:
        print(f"{entry['step']}: HTTP {entry['status_code']}")

if __name__ == "__main__":
    main()
