import logging
import json
import os
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from shared.auth import require_auth

EVENTS_TABLE = "Events"
RUNNERS_TABLE = "RunnersInEvent"
READY_USERS_TABLE = "ReadyUsers"

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        event_id = body.get("eventId")
        user_id = body.get("userId")

        if not event_id or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId or userId"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")
        if not conn:
            raise ValueError("AzureWebJobsStorage connection string not found")

        # Check if event exists and is in ready state
        events_tbl = TableClient.from_connection_string(conn, EVENTS_TABLE)
        try:
            event = events_tbl.get_entity("Event", event_id)
            if event['status'] != 'ready':
                return func.HttpResponse(
                    json.dumps({"error": "event is not in ready state"}),
                    status_code=409,
                    mimetype="application/json"
                )
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": f"event {event_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Check if user is registered for the event
        runners_tbl = TableClient.from_connection_string(conn, RUNNERS_TABLE)
        try:
            runners_tbl.get_entity(event_id, user_id)
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": "user is not registered for this event"}),
                status_code=403,
                mimetype="application/json"
            )

        # Mark user as ready
        ready_users_tbl = TableClient.from_connection_string(conn, READY_USERS_TABLE)
        entity = {
            "PartitionKey": event_id,
            "RowKey": user_id,
            "readyAt": datetime.utcnow().isoformat()
        }

        try:
            ready_users_tbl.create_entity(entity=entity)
        except ResourceExistsError:
            return func.HttpResponse(
                json.dumps({"message": "user already marked as ready", "eventId": event_id, "userId": user_id}),
                status_code=200,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({
                "message": "user marked as ready",
                "eventId": event_id,
                "userId": user_id
            }),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"MarkUserReady error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 