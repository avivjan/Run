import logging
import json
import os
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableClient
from azure.core.exceptions import ResourceNotFoundError
from shared.auth import require_auth

USERS_TABLE      = "Users"
EVENTS_TABLE     = "Events"
RUNNERS_TABLE    = "RunnersInEvent"

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        leaving_user_id = body.get("leavingUserId")
        requesting_user_id = body.get("requestingUserId")
        event_id = body.get("eventId")

        logging.info(f"LeaveEvent called with leavingUserId: {leaving_user_id}, requestingUserId: {requesting_user_id}, eventId: {event_id}")

        if not leaving_user_id or not requesting_user_id or not event_id:
            logging.error("Missing leavingUserId, requestingUserId, or eventId")
            return func.HttpResponse(
                json.dumps({"error": "missing leavingUserId, requestingUserId, or eventId"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")
        if not conn:
            logging.error("AzureWebJobsStorage connection string not found")
            return func.HttpResponse(
                json.dumps({"error": "AzureWebJobsStorage connection string not found"}),
                status_code=500,
                mimetype="application/json"
            )

        # Verify the requesting user exists
        users_tbl = TableClient.from_connection_string(conn, USERS_TABLE)
        try:
            users_tbl.get_entity("User", requesting_user_id)
            logging.info(f"Requesting user {requesting_user_id} found")
        except ResourceNotFoundError:
            logging.error(f"Requesting user {requesting_user_id} not found")
            return func.HttpResponse(
                json.dumps({"error": f"requesting user {requesting_user_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Verify the leaving user exists
        try:
            users_tbl.get_entity("User", leaving_user_id)
            logging.info(f"Leaving user {leaving_user_id} found")
        except ResourceNotFoundError:
            logging.error(f"Leaving user {leaving_user_id} not found")
            return func.HttpResponse(
                json.dumps({"error": f"leaving user {leaving_user_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Get event details to check if requesting user is the host
        events_tbl = TableClient.from_connection_string(conn, EVENTS_TABLE)
        try:
            event = events_tbl.get_entity("Event", event_id)
            logging.info(f"Event {event_id} found")
        except ResourceNotFoundError:
            logging.error(f"Event {event_id} not found")
            return func.HttpResponse(
                json.dumps({"error": f"event {event_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Check authorization: requesting user must be either the leaving user or the event host
        event_host = event.get("trainerId")
        if requesting_user_id != leaving_user_id and requesting_user_id != event_host:
            logging.error(f"Unauthorized: {requesting_user_id} cannot remove {leaving_user_id} from event {event_id}")
            return func.HttpResponse(
                json.dumps({"error": "unauthorized: only the leaving user or event host can remove a user"}),
                status_code=403,
                mimetype="application/json"
            )

        # Remove the user from the event
        runners_tbl = TableClient.from_connection_string(conn, RUNNERS_TABLE)
        try:
            runners_tbl.delete_entity(partition_key=event_id, row_key=leaving_user_id)
            logging.info(f"User {leaving_user_id} successfully left event {event_id}")
        except ResourceNotFoundError:
            logging.info(f"User {leaving_user_id} was not registered for event {event_id}")
            return func.HttpResponse(
                json.dumps({"message": "user was not registered for this event", "eventId": event_id, "userId": leaving_user_id}),
                status_code=200,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({"message": "user left event", "eventId": event_id, "userId": leaving_user_id}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"LeaveEvent error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 