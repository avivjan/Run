import logging
import json
import os

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableClient, TableServiceClient
from shared.auth import require_auth


EVENTS_TABLE   = "Events"
RUNNERS_TABLE  = "RunnersInEvent"      # שנה אם השתמשת בשם אחר


@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    """Delete event + all runner links. Does not delete associated tracks."""
    try:
        # ---------- get eventId ------------------------------------------------
        event_id = req.params.get("eventId")
        if not event_id:
            try:
                body = req.get_json()
                event_id = body.get("eventId")
            except ValueError:
                pass
        if not event_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId"}),
                status_code=400,
                mimetype="application/json"
            )
            
        conn = os.getenv("AzureWebJobsStorage")

        # ---------- delete from Events ----------------------------------------
        events_tbl = TableClient.from_connection_string(conn, EVENTS_TABLE)
        try:
            # Get event first to preserve its data
            event = events_tbl.get_entity(partition_key="Event", row_key=event_id)
            # Then delete it
            events_tbl.delete_entity(partition_key="Event", row_key=event_id)
            event_deleted = True
        except ResourceNotFoundError:
            event_deleted = False

        # ---------- delete runners rows ---------------------------------------
        # ensure runners table exists; if not, nothing to delete
        service = TableServiceClient.from_connection_string(conn)
        if RUNNERS_TABLE in [t.name for t in service.list_tables()]:
            runners_tbl = TableClient.from_connection_string(conn, RUNNERS_TABLE)
            # each runner row:  PartitionKey = eventId
            for rel in runners_tbl.query_entities(f"PartitionKey eq '{event_id}'"):
                runners_tbl.delete_entity(partition_key=rel["PartitionKey"],
                                          row_key=rel["RowKey"])

        # ---------- response ---------------------------------------------------
        if event_deleted:
            return func.HttpResponse(
                json.dumps({"message": "event deleted", "eventId": event_id}),
                status_code=200,
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
            json.dumps({"error": "event not found", "eventId": event_id}),
            status_code=404,
            mimetype="application/json"
            )

    except Exception as exc:
        logging.error(f"deleteEvent error: {exc}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong"}),
            status_code=500,
            mimetype="application/json"
        )
