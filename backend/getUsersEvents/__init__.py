import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # ---- get userId -----------------------------------------------------
        user_id = req.params.get("userId")
        if not user_id:
            try:
                user_id = req.get_json().get("userId")
            except ValueError:
                pass
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "missing userId"}),
                status_code=400,
                mimetype="application/json"
            )

        # ---- table clients --------------------------------------------------
        conn_str = os.getenv("AzureWebJobsStorage")
        events_tbl   = TableClient.from_connection_string(conn_str, table_name="Events")
        runners_tbl  = TableClient.from_connection_string(conn_str, table_name="RunnersInEvent")

        user_events = {}
        # 1) events where the user is trainer
        trainer_filter = f"PartitionKey eq 'Event' and trainerId eq '{user_id}'"
        for e in events_tbl.query_entities(trainer_filter):
            user_events[e["RowKey"]] = e

        # 2) events where the user is runner
        for rel in runners_tbl.query_entities(f"RowKey eq '{user_id}'"):
            evt_id = rel["PartitionKey"]
            try:
                e = events_tbl.get_entity("Event", evt_id)
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

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as exc:
        logging.error(f"getUsersEvents error: {exc}")
        return func.HttpResponse(
                json.dumps({"error": "something went wrong", "details": str(exc)}),
                status_code=500,
                mimetype="application/json"
        )
