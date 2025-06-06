#!/usr/bin/env python3
"""
Complete smoke-test for Runner/Trainer MVP API.
Tests all available endpoints with basic functionality:
- Authentication (register, login)
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
    
    # Determine if this is an expected error test case
    is_expected_error = any(error_case in step.lower() for error_case in [
        "invalid", "wrong", "duplicate", "(deleted", "not found", "unauthorized",
        "verify auth required"  # Add this to treat auth verification as expected error
    ])
    
    # For expected error cases, success means getting an error status (4xx)
    is_success = (
        (200 <= resp.status_code < 300 and not is_expected_error) or
        (400 <= resp.status_code < 500 and is_expected_error)
    )
    
    # Print real-time test progress
    status_icon = "✅" if is_success else "❌"
    print(f"\n{status_icon} {step}")
    print(f"  Status: {resp.status_code}")
    print(f"  Duration: {duration_ms}ms")
    if resp.status_code >= 400:
        print(f"  Error: {entry['response']}")
    
    # Track test failures
    if not is_success:
        global test_failures
        test_failures.append(step)
    
    return entry

def make_request(step, method, url, **kwargs):
    start_time = time.time()
    resp = requests.request(method, url, **kwargs)
    duration_ms = int((time.time() - start_time) * 1000)
    
    payload = kwargs.get('json') or kwargs.get('params')
    entry = add_log(step, method, resp.url, payload, resp, duration_ms)
    
    return resp, entry

def validate_response(entry, validation_fn=None, expected_status_range=(200, 299)):
    """Validate response status and optionally run custom validation"""
    status_min, status_max = expected_status_range
    if not (status_min <= entry["status_code"] <= status_max):
        error_msg = (
            f"{entry['step']} failed with status {entry['status_code']}\n"
            f"Expected status range: {status_min}-{status_max}\n"
            f"Response: {json.dumps(entry['response'], indent=2)}"
        )
        raise AssertionError(error_msg)
    
    if validation_fn and callable(validation_fn):
        try:
            validation_fn(entry["response"])
        except AssertionError as e:
            raise AssertionError(f"{entry['step']} validation failed: {str(e)}")
        except Exception as e:
            raise AssertionError(f"{entry['step']} validation error: {str(e)}")

def verify_track_exists(base_url, track_id, track_payload, headers):
    """Verify a track exists and matches the creation payload"""
    resp, entry = make_request(
        "verify track exists", "GET",
        f"{base_url}/getAllTracks",
        headers=headers
    )
    validate_response(entry)
    
    # Find our track in the list
    track = next((t for t in entry["response"] if t.get("trackId") == track_id), None)
    if not track:
        raise AssertionError(f"Created track {track_id} not found in getAllTracks response")
    
    # Verify track data matches what we sent
    track_path = track["path"]  # path is already parsed as JSON by the API
    if track_path != track_payload["path"]:
        raise AssertionError(f"Track path mismatch. Expected {track_payload['path']}, got {track_path}")

def verify_event_exists(base_url, event_id, event_payload, headers):
    """Verify an event exists and matches the creation payload"""
    resp, entry = make_request(
        "verify event exists", "GET",
        f"{base_url}/getAllOpenEvents",
        headers=headers
    )
    validate_response(entry)
    
    # Find our event in the list
    event = next((e for e in entry["response"] if e.get("eventId") == event_id), None)
    if not event:
        raise AssertionError(f"Created event {event_id} not found in getAllOpenEvents response")
    
    # Verify event data matches what we sent
    for key, value in event_payload.items():
        if key in event and event[key] != value:
            raise AssertionError(f"Event {key} mismatch. Expected {value}, got {event[key]}")
    
    # Verify RowKey matches eventId
    if event.get("RowKey") != event.get("eventId"):
        raise AssertionError(f"Event RowKey ({event.get('RowKey')}) doesn't match eventId ({event.get('eventId')})")

def verify_auth_required(base_url, endpoint, method="GET", params=None, json_data=None):
    """Verify that an endpoint requires authentication"""
    resp, entry = make_request(
        f"verify auth required - {endpoint}", 
        method,
        f"{base_url}/{endpoint}",
        params=params,
        json=json_data
    )
    if resp.status_code not in (401, 403):
        raise AssertionError(
            f"Expected 401/403 for unauthenticated request to {endpoint}, "
            f"got {resp.status_code}"
        )

class TestState:
    """Track state changes during test run"""
    def __init__(self):
        self.created_tracks = []        # Tracks created during test
        self.deleted_tracks = []        # Tracks deleted during test
        self.created_events = []        # Events created during test
        self.deleted_events = []        # Events deleted during test
        self.test_username = None       # Test user created
        self.auth_headers = None        # Auth headers for cleanup
        self.runner_registrations = []  # Event registrations created

def cleanup_test_data(base_url, state):
    """Clean up test data and restore deleted resources. Returns True if all cleanup succeeded."""
    if not state.auth_headers:
        print("\n⚠️ No auth headers available for cleanup")
        return False

    print("\n🧹 Cleaning up test data...")
    cleanup_success = True
    
    # 1. Delete events created during test (this will also remove runner registrations)
    for event_id in state.created_events:
        if event_id not in state.deleted_events:  # Skip if already deleted during test
            resp, entry = make_request(
                f"cleanup - delete event {event_id}", "POST",
                f"{base_url}/deleteEvent",
                json={"eventId": event_id},
                headers=state.auth_headers
            )
            if 200 <= resp.status_code < 300:
                print(f"  ✓ Deleted test event: {event_id}")
            elif resp.status_code == 404:
                print(f"  ✓ Event already deleted: {event_id}")
            else:
                print(f"  ⚠️ Failed to delete event {event_id}: {resp.status_code}")
                cleanup_success = False

    # 2. Delete tracks created during test (skip if already deleted)
    for track_id in state.created_tracks:
        if track_id in state.deleted_tracks:  # Skip if already deleted during test
            continue  # Don't even print anything since it was handled during the test

        resp, entry = make_request(
            f"cleanup - delete track {track_id}", "POST",
            f"{base_url}/deleteTrack",
            json={"trackId": track_id},
            headers=state.auth_headers
        )
        if 200 <= resp.status_code < 300:
            print(f"  ✓ Deleted test track: {track_id}")
        elif resp.status_code == 404:
            print(f"  ✓ Track already deleted: {track_id}")
        else:
            print(f"  ⚠️ Failed to delete track {track_id}: {resp.status_code}")
            cleanup_success = False

    # 3. Recreate events that were deleted during test
    for event_id in state.deleted_events:
        if event_id not in state.created_events:  # Only recreate events that weren't created by us
            # Get event details from the test log
            event_details = None
            for entry in log:
                if entry["step"] == "createEvent" and entry["response"].get("RowKey") == event_id:
                    event_details = entry["payload"]
                    break
            
            if event_details:
                resp, entry = make_request(
                    f"cleanup - recreate event {event_id}", "POST",
                    f"{base_url}/createEvent",
                    json=event_details,
                    headers=state.auth_headers
                )
                if 200 <= resp.status_code < 300:
                    print(f"  ✓ Recreated deleted event: {event_id}")
                else:
                    print(f"  ⚠️ Failed to recreate event {event_id}: {resp.status_code}")
                    cleanup_success = False

    # 4. Restore runner registrations for recreated events
    for reg in state.runner_registrations:
        if reg["eventId"] in state.deleted_events and reg["eventId"] not in state.created_events:
            resp, entry = make_request(
                f"cleanup - restore registration", "POST",
                f"{base_url}/joinEvent",
                json={"eventId": reg["eventId"], "userId": reg["userId"]},
                headers=state.auth_headers
            )
            if 200 <= resp.status_code < 300:
                print(f"  ✓ Restored runner registration: {reg['userId']} in event {reg['eventId']}")
            elif resp.status_code == 404:
                print(f"  ⚠️ Could not restore registration - event {reg['eventId']} not found")
                cleanup_success = False
            else:
                print(f"  ⚠️ Failed to restore registration: {resp.status_code}")
                cleanup_success = False

    return cleanup_success

# Global variable to track test failures
test_failures = []

def main():
    try:
        args = parse_args()
        print("\n🔄 Starting API smoke tests...")
        print(f"Base URL: {args.base_url}")
        
        # Create state tracker
        state = TestState()
        
        # Reset test failures for this run
        global test_failures
        test_failures = []
        
        # Run tests
        main_with_auth(args, state)
        
        # Clean up test data
        cleanup_success = cleanup_test_data(args.base_url, state)
        
        if test_failures:
            failed_steps = "\n  - ".join(test_failures)
            print(f"\n❌ Tests failed. Failed steps:\n  - {failed_steps}")
            raise Exception("Test failures occurred")
        elif not cleanup_success:
            print("\n⚠️ Tests passed but cleanup failed - database state may be inconsistent")
            raise Exception("Cleanup failed")
        else:
            print("\n✨ All tests passed successfully!")
            
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        # Try to clean up even if tests fail, but don't overwrite the original error
        if 'args' in locals() and 'state' in locals():
            cleanup_test_data(args.base_url, state)
        raise
    finally:
        # Save test results
        output_file = "api_test_results.json"
        with open(output_file, "w") as f:
            json.dump(log, f, indent=2)
        print(f"\n📝 Test results saved to {output_file}")

def main_with_auth(args, state):
    """Run the main test sequence and track created resources"""
    # Generate unique test username
    state.test_username = f"testuser_{uuid.uuid4().hex[:8]}"
    test_password = "testpass123"

    # 0. Verify authentication is required for protected endpoints
    # Note: getAllTracks is a public endpoint
    verify_auth_required(args.base_url, "createTrack", method="POST", json_data={"path": []})
    verify_auth_required(args.base_url, "createEvent", method="POST", json_data={})
    verify_auth_required(args.base_url, "deleteEvent", method="POST", json_data={"eventId": "test"})
    verify_auth_required(args.base_url, "joinEvent", method="POST", json_data={"eventId": "test", "userId": "test"})

    # 1. Test registration with invalid password
    resp, entry = make_request(
        "register (invalid password)", "POST",
        f"{args.base_url}/register",
        json={"username": state.test_username, "password": "short"}
    )
    validate_response(entry, expected_status_range=(400, 400))

    # 2. Register new test user
    resp, entry = make_request(
        "register", "POST",
        f"{args.base_url}/register",
        json={"username": state.test_username, "password": test_password}
    )
    validate_response(entry, expected_status_range=(201, 201))

    # 3. Try registering same user again (should fail)
    resp, entry = make_request(
        "register (duplicate)", "POST",
        f"{args.base_url}/register",
        json={"username": state.test_username, "password": test_password}
    )
    validate_response(entry, expected_status_range=(409, 409))

    # 4. Login with wrong password
    resp, entry = make_request(
        "login (wrong password)", "POST",
        f"{args.base_url}/login",
        json={"username": state.test_username, "password": "wrongpass"}
    )
    validate_response(entry, expected_status_range=(401, 401))

    # 5. Login with correct password
    resp, entry = make_request(
        "login", "POST",
        f"{args.base_url}/login",
        json={"username": state.test_username, "password": test_password}
    )
    validate_response(entry, lambda r: all([
        "token" in r,
        r["username"] == state.test_username
    ]))
    auth_token = entry["response"]["token"]

    # Store the auth token for future requests
    state.auth_headers = {"Authorization": f"Bearer {auth_token}"}

    # 6. getUser runner
    resp, entry = make_request(
        "getUser runner", "GET",
        f"{args.base_url}/getUser",
        params={"userId": args.runner_id},
        headers=state.auth_headers
    )
    validate_response(entry, lambda r: r.get("userId") == args.runner_id)

    # 7. getUser trainer
    resp, entry = make_request(
        "getUser trainer", "GET",
        f"{args.base_url}/getUser",
        params={"userId": args.trainer_id},
        headers=state.auth_headers
    )
    validate_response(entry, lambda r: r.get("userId") == args.trainer_id)

    # 8. getAllTracks (before creating any)
    resp, entry = make_request(
        "getAllTracks (initial)", "GET",
        f"{args.base_url}/getAllTracks",
        headers=state.auth_headers
    )
    validate_response(entry)
    initial_track_count = len(entry["response"])

    # 9. createTrack
    track_payload = {
        "path": [
            {"latitude": 32.0853, "longitude": 34.7818},  # Start point
            {"latitude": 32.0853, "longitude": 34.7828},  # Middle point
            {"latitude": 32.0873, "longitude": 34.7838}   # End point
        ]
    }
    resp, entry = make_request(
        "createTrack", "POST",
        f"{args.base_url}/createTrack",
        json=track_payload,
        headers=state.auth_headers
    )
    validate_response(entry)
    track_id = entry["response"].get("trackId")
    assert track_id, "Missing trackId in createTrack response"
    state.created_tracks.append(track_id)

    # Verify track was created correctly
    verify_track_exists(args.base_url, track_id, track_payload, state.auth_headers)

    # 10. getAllTracks (after creating one)
    resp, entry = make_request(
        "getAllTracks (after creation)", "GET",
        f"{args.base_url}/getAllTracks",
        headers=state.auth_headers
    )
    validate_response(entry, lambda r: len(r) == initial_track_count + 1)

    # 11. createEvent
    event_payload = {
        "timestamp": iso_now(),
        "trainerId": args.trainer_id,
        "latitude": 32.0853,
        "longitude": 34.7818,
        "name": f"Test Event {uuid.uuid4().hex[:8]}",  # Unique name
        "status": "open",
        "start_time": int(datetime.now().timestamp()) + 3600,  # 1 hour from now
        "track_length": 5000,  # 5km
        "difficulty": "beginner",
        "type": "street",
        "trackId": track_id
    }
    resp, entry = make_request(
        "createEvent", "POST",
        f"{args.base_url}/createEvent",
        json=event_payload,
        headers=state.auth_headers
    )
    validate_response(entry)
    event_id = entry["response"].get("RowKey")
    assert event_id, "Missing eventId in createEvent response"
    state.created_events.append(event_id)

    # Verify event was created correctly
    verify_event_exists(args.base_url, event_id, event_payload, state.auth_headers)

    # 12. getAllOpenEvents
    resp, entry = make_request(
        "getAllOpenEvents", "GET",
        f"{args.base_url}/getAllOpenEvents",
        headers=state.auth_headers
    )
    validate_response(entry, lambda r: any(e.get("eventId") == event_id for e in r))

    # 13. joinEvent
    join_payload = {"eventId": event_id, "userId": args.runner_id}
    resp, entry = make_request(
        "joinEvent", "POST",
        f"{args.base_url}/joinEvent",
        json=join_payload,
        headers=state.auth_headers
    )
    validate_response(entry)
    state.runner_registrations.append({
        "eventId": event_id,
        "userId": args.runner_id
    })

    # 14. getEventRegisteredUsers
    resp, entry = make_request(
        "getEventRegisteredUsers", "GET",
        f"{args.base_url}/getEventRegisteredUsers",
        params={"eventId": event_id},
        headers=state.auth_headers
    )
    validate_response(entry, lambda r: any(u.get("userId") == args.runner_id for u in r))

    # 15. getUsersEvents
    resp, entry = make_request(
        "getUsersEvents", "GET",
        f"{args.base_url}/getUsersEvents",
        params={"userId": args.runner_id},
        headers=state.auth_headers
    )
    validate_response(entry, lambda r: any(e.get("eventId") == event_id for e in r))

    # 16. negotiate SignalR
    resp, entry = make_request(
        "negotiate", "POST",
        f"{args.base_url}/negotiate",
        headers=state.auth_headers
    )
    validate_response(entry)

    # 17. deleteEvent
    resp, entry = make_request(
        "deleteEvent", "POST",
        f"{args.base_url}/deleteEvent",
        json={"eventId": event_id},
        headers=state.auth_headers
    )
    validate_response(entry)
    state.deleted_events.append(event_id)

    # 18. verify event deletion with getAllOpenEvents
    resp, entry = make_request(
        "getAllOpenEvents (after deletion)", "GET",
        f"{args.base_url}/getAllOpenEvents",
        headers=state.auth_headers
    )
    validate_response(entry, lambda r: not any(e.get("eventId") == event_id for e in r))

    # 19. Test edge case: joining a deleted event
    resp, entry = make_request(
        "joinEvent (deleted event)", "POST",
        f"{args.base_url}/joinEvent",
        json={"eventId": event_id, "userId": args.runner_id},
        headers=state.auth_headers
    )
    # This should fail with 4xx - use custom validation range
    validate_response(entry, expected_status_range=(400, 499))

    # Track track deletion if it happens in the test
    resp, entry = make_request(
        "deleteTrack", "POST",
        f"{args.base_url}/deleteTrack",
        json={"trackId": track_id},
        headers=state.auth_headers
    )
    validate_response(entry)
    state.deleted_tracks.append(track_id)

    # Store auth headers for cleanup
    state.auth_headers = state.auth_headers

if __name__ == "__main__":
    main()
