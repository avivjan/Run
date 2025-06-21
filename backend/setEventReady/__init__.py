import logging
import json
import os
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableClient, UpdateMode
from azure.core.exceptions import ResourceNotFoundError
from shared.auth import require_auth

EVENTS_TABLE = "Events"

@require_auth
def main(
        req: func.HttpRequest,
        signalrMessages: func.Out[str]
    ) -> func.HttpResponse:
    try:
        body = req.get_json()
        event_id = body.get("eventId")

        if not event_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")
        if not conn:
            raise ValueError("AzureWebJobsStorage connection string not found")
            
        events_tbl = TableClient.from_connection_string(conn, EVENTS_TABLE)

        try:
            event = events_tbl.get_entity("Event", event_id)
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": f"event {event_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Verify the user is the host
        user = getattr(req, 'user', {})
        user_id = user.get('username')
        if event.get('trainerId') != user_id:
            return func.HttpResponse(
                json.dumps({"error": "only the host can set event to ready"}),
                status_code=403,
                mimetype="application/json"
            )

        # Update event status to ready
        event['status'] = 'ready'
        events_tbl.update_entity(entity=event, mode=UpdateMode.REPLACE)

        # Send signalR message
        event_for_client = {k: v for k, v in event.items() if k not in ("PartitionKey", "etag")}
        event_for_client["eventId"] = event["RowKey"]
        signalrMessages.set(json.dumps({
            'target': 'eventStatusChanged',
            'arguments': [event_for_client]
        }))

        return func.HttpResponse(
            json.dumps({
                "message": "event set to ready",
                "eventId": event_id,
                "status": "ready"
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"SetEventReady error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 