import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get user from JWT
        user = getattr(req, 'user', {})
        user_id = user.get('username')
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "User not authenticated"}),
                status_code=401,
                mimetype="application/json"
            )

        conn_str = os.getenv("AzureWebJobsStorage")
        if not conn_str:
            return func.HttpResponse(
                json.dumps({"error": "AzureWebJobsStorage connection string not found"}),
                status_code=500,
                mimetype="application/json"
            )
        events_table = TableClient.from_connection_string(conn_str, table_name="Events")
        runners_table = TableClient.from_connection_string(conn_str, table_name="RunnersInEvent")

        # Get all open events
        open_filter = "PartitionKey eq 'Event' and status eq 'open'"
        open_events = []
        for e in events_table.query_entities(open_filter):
            event = {k: v for k, v in e.items() if k not in ("PartitionKey", "etag")}
            event["eventId"] = e["RowKey"]
            open_events.append(event)

        # Get all ready events
        ready_filter = "PartitionKey eq 'Event' and status eq 'ready'"
        ready_events = []
        for e in events_table.query_entities(ready_filter):
            event = {k: v for k, v in e.items() if k not in ("PartitionKey", "etag")}
            event["eventId"] = e["RowKey"]
            # Host check
            is_host = (event.get("trainerId") == user_id)
            # Participant check
            is_participant = False
            try:
                # In RunnersInEvent, PartitionKey is eventId, RowKey is userId
                participant = runners_table.get_entity(event["eventId"], user_id)
                is_participant = True
            except Exception:
                pass
            if is_host or is_participant:
                ready_events.append(event)

        all_events = open_events + ready_events
        return func.HttpResponse(
            json.dumps(all_events),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as exc:
        logging.error(f"getAllOpenEvents error: {exc}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(exc)}),
            status_code=500,
            mimetype="application/json"
        )
