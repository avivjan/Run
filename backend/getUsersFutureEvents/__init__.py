import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get user from JWT token
        user = getattr(req, 'user', {})
        user_id = user.get('username')
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "User not authenticated"}),
                status_code=401,
                mimetype="application/json"
            )

        logging.info(f"Getting future events for authenticated user: {user_id}")

        # ---- table clients --------------------------------------------------
        conn_str = os.getenv("AzureWebJobsStorage")
        if not conn_str:
            return func.HttpResponse(
                json.dumps({"error": "AzureWebJobsStorage connection string not found"}),
                status_code=500,
                mimetype="application/json"
            )
        events_tbl   = TableClient.from_connection_string(conn_str, table_name="Events")
        runners_tbl  = TableClient.from_connection_string(conn_str, table_name="RunnersInEvent")

        user_events = {}
        
        # 1) events where the user is trainer with status 'open' or 'ready'
        trainer_open_filter = f"PartitionKey eq 'Event' and trainerId eq '{user_id}' and status eq 'open'"
        trainer_ready_filter = f"PartitionKey eq 'Event' and trainerId eq '{user_id}' and status eq 'ready'"
        
        for e in events_tbl.query_entities(trainer_open_filter):
            user_events[e["RowKey"]] = e
        for e in events_tbl.query_entities(trainer_ready_filter):
            user_events[e["RowKey"]] = e

        # 2) events where the user is runner with status 'open' or 'ready'
        for rel in runners_tbl.query_entities(f"RowKey eq '{user_id}'"):
            evt_id = rel["PartitionKey"]
            try:
                e = events_tbl.get_entity("Event", evt_id)
                # Only include events with status 'open' or 'ready'
                if e.get("status") in ["open", "ready"]:
                    user_events[evt_id] = e
            except Exception:
                logging.warning(f"Event {evt_id} listed for runner {user_id} but not found in Events table.")

        # ---- build JSON list -----------------------------------------------
        result = []
        for e in user_events.values():
            event_out = {k: v for k, v in e.items()
                         if k not in ("PartitionKey", "etag")}
            event_out["eventId"] = e["RowKey"]
            result.append(event_out)

        logging.info(f"Returning {len(result)} future events for user {user_id}")
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as exc:
        logging.error(f"getUsersFutureEvents error: {exc}")
        return func.HttpResponse(
                json.dumps({"error": "something went wrong", "details": str(exc)}),
                status_code=500,
                mimetype="application/json"
        )
