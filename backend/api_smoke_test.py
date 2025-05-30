#!/usr/bin/env python3
"""
Complete smoke-test for Runner/Trainer MVP API.
Tests all available endpoints with basic functionality:
- User operations (getUser)
- Event operations (create, join, delete, get all open, get registered users)
- Track operations (create, get all)
- User's events (get user's events)
- SignalR negotiation
Outputs a JSON log you can share back for review.
"""

import json
import uuid
import time
import os
from datetime import datetime, timezone
from pathlib import Path
import argparse

import requests

# Default values - can be overridden via environment variables or command line args
DEFAULT_BASE_URL = "https://runfuncionapp.azurewebsites.net/api"
DEFAULT_RUNNER_ID = "user123"
DEFAULT_TRAINER_ID = "user456"

def parse_args():
    parser = argparse.ArgumentParser(description='Run API smoke tests')
    parser.add_argument('--base-url', default=os.getenv('API_BASE_URL', DEFAULT_BASE_URL),
                      help='Base URL for API endpoints')
    parser.add_argument('--runner-id', default=os.getenv('TEST_RUNNER_ID', DEFAULT_RUNNER_ID),
                      help='ID to use for runner in tests')
    parser.add_argument('--trainer-id', default=os.getenv('TEST_TRAINER_ID', DEFAULT_TRAINER_ID),
                      help='ID to use for trainer in tests')
    return parser.parse_args()

def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

log = []  # list of dicts with step / status / response

def add_log(step, method, url, payload, resp, duration_ms=None):
    entry = {
        "step": step,
        "method": method,
        "url": url,
        "payload": payload,
        "status_code": resp.status_code,
        "duration_ms": duration_ms,
        "response": resp.json() if resp.headers.get("content-type","").startswith("application/json") else resp.text
    }
    log.append(entry)
    return entry

def make_request(step, method, url, **kwargs):
    start_time = time.time()
    resp = requests.request(method, url, **kwargs)
    duration_ms = int((time.time() - start_time) * 1000)
    
    payload = kwargs.get('json') or kwargs.get('params')
    entry = add_log(step, method, resp.url, payload, resp, duration_ms)
    
    return resp, entry

def validate_response(entry, validation_fn=None):
    """Validate response status and optionally run custom validation"""
    if not (200 <= entry["status_code"] < 300):
        raise AssertionError(f"{entry['step']} failed with status {entry['status_code']}")
    
    if validation_fn and callable(validation_fn):
        validation_fn(entry["response"])

def main():
    args = parse_args()
    
    # 1. getUser runner
    resp, entry = make_request(
        "getUser runner", "GET",
        f"{args.base_url}/getUser",
        params={"userId": args.runner_id}
    )
    validate_response(entry, lambda r: r.get("userId") == args.runner_id)

    # 2. getUser trainer
    resp, entry = make_request(
        "getUser trainer", "GET",
        f"{args.base_url}/getUser",
        params={"userId": args.trainer_id}
    )
    validate_response(entry, lambda r: r.get("userId") == args.trainer_id)

    # 3. getAllTracks (before creating any)
    resp, entry = make_request(
        "getAllTracks (initial)", "GET",
        f"{args.base_url}/getAllTracks"
    )
    validate_response(entry)
    initial_track_count = len(entry["response"])

    # 4. createTrack
    track_payload = {
        "name": f"Test Track {uuid.uuid4().hex[:8]}",  # Unique name
        "description": "A test track for API smoke test",
        "difficulty": "intermediate",
        "type": "trail",
        "length": 5000,  # 5km
        "coordinates": [
            {"latitude": 32.0853, "longitude": 34.7818},  # Start point
            {"latitude": 32.0873, "longitude": 34.7838}   # End point
        ]
    }
    resp, entry = make_request(
        "createTrack", "POST",
        f"{args.base_url}/createTrack",
        json=track_payload
    )
    validate_response(entry)
    track_id = entry["response"].get("trackId")
    assert track_id, "Missing trackId in createTrack response"

    # 5. getAllTracks (after creating one)
    resp, entry = make_request(
        "getAllTracks (after creation)", "GET",
        f"{args.base_url}/getAllTracks"
    )
    validate_response(entry, lambda r: len(r) == initial_track_count + 1)

    # 6. createEvent
    event_payload = {
        "timestamp": iso_now(),
        "trainerId": args.trainer_id,
        "trackId": track_id,
        "name": f"Test Event {uuid.uuid4().hex[:8]}",  # Unique name
        "start_time": int(datetime.now().timestamp()) + 3600,  # 1 hour from now
        "difficulty": "intermediate",
        "type": "trail"
    }
    resp, entry = make_request(
        "createEvent", "POST",
        f"{args.base_url}/createEvent",
        json=event_payload
    )
    validate_response(entry)
    event_id = entry["response"].get("eventId")
    assert event_id, "Missing eventId in createEvent response"

    # 7. getAllOpenEvents
    resp, entry = make_request(
        "getAllOpenEvents", "GET",
        f"{args.base_url}/getAllOpenEvents"
    )
    validate_response(entry, lambda r: any(e.get("eventId") == event_id for e in r))

    # 8. joinEvent
    join_payload = {"eventId": event_id, "userId": args.runner_id}
    resp, entry = make_request(
        "joinEvent", "POST",
        f"{args.base_url}/joinEvent",
        json=join_payload
    )
    validate_response(entry)

    # 9. getEventRegisteredUsers
    resp, entry = make_request(
        "getEventRegisteredUsers", "GET",
        f"{args.base_url}/getEventRegisteredUsers",
        params={"eventId": event_id}
    )
    validate_response(entry, lambda r: any(u.get("userId") == args.runner_id for u in r))

    # 10. getUsersEvents
    resp, entry = make_request(
        "getUsersEvents", "GET",
        f"{args.base_url}/getUsersEvents",
        params={"userId": args.runner_id}
    )
    validate_response(entry, lambda r: any(e.get("eventId") == event_id for e in r))

    # 11. negotiate SignalR
    resp, entry = make_request(
        "negotiate", "POST",
        f"{args.base_url}/negotiate"
    )
    validate_response(entry)

    # 12. deleteEvent
    resp, entry = make_request(
        "deleteEvent", "POST",
        f"{args.base_url}/deleteEvent",
        json={"eventId": event_id}
    )
    validate_response(entry)

    # 13. verify event deletion with getAllOpenEvents
    resp, entry = make_request(
        "getAllOpenEvents (after deletion)", "GET",
        f"{args.base_url}/getAllOpenEvents"
    )
    validate_response(entry, lambda r: not any(e.get("eventId") == event_id for e in r))

    # 14. Test edge case: joining a deleted event
    resp, entry = make_request(
        "joinEvent (deleted event)", "POST",
        f"{args.base_url}/joinEvent",
        json={"eventId": event_id, "userId": args.runner_id}
    )
    # This should fail - expect 404 or similar
    assert 400 <= entry["status_code"] < 500, "Joining deleted event should fail"

    # save results
    outfile = Path(f"api_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
    outfile.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"✅ Test finished. Results saved to {outfile.resolve()}")
    
    # Print summary with timing information
    print("\nTest Summary:")
    slow_threshold_ms = 1000  # Consider requests over 1 second as slow
    for entry in log:
        status = "✅" if 200 <= entry["status_code"] < 300 else "❌"
        duration = f"{entry['duration_ms']}ms"
        if entry["duration_ms"] > slow_threshold_ms:
            duration += " ⚠️ SLOW"
        print(f"{status} {entry['step']}: HTTP {entry['status_code']} ({duration})")

if __name__ == "__main__":
    main()
