import logging
import json
import os
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from shared.auth import require_auth

USERS_TABLE      = "Users"
EVENTS_TABLE     = "Events"
RUNNERS_TABLE    = "RunnersInEvent"  

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        event_id = body.get("eventId")
        user_id  = body.get("userId")

        if not event_id or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId or userId"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")

        users_tbl = TableClient.from_connection_string(conn, USERS_TABLE)
        try:
            users_tbl.get_entity("User", user_id)
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": f"user {user_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        events_tbl = TableClient.from_connection_string(conn, EVENTS_TABLE)
        try:
            evt = events_tbl.get_entity("Event", event_id)
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": f"event {event_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        if evt.get("status") != "open":
            return func.HttpResponse(
                json.dumps({"error": "event is not open"}),
                status_code=409,
                mimetype="application/json"
            )

        runners_tbl = TableClient.from_connection_string(conn, RUNNERS_TABLE)

        entity = {
            "PartitionKey": event_id,
            "RowKey": user_id,
            "joinedAt": datetime.utcnow().isoformat()
        }

        try:
            runners_tbl.create_entity(entity=entity)
        except ResourceExistsError:
            return func.HttpResponse(
                json.dumps({"message": "user already joined", "eventId": event_id, "userId": user_id}),
                status_code=200,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({"message": "user joined event", "eventId": event_id, "userId": user_id}),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"JoinEvent error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
