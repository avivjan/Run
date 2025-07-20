import logging
import azure.functions as func
from azure.data.tables import TableClient
from azure.core.exceptions import ResourceNotFoundError
import os
import json
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get eventId from query string or request body
        event_id = req.params.get('eventId')
        if not event_id:
            try:
                req_body = req.get_json()
                event_id = req_body.get('eventId')
            except ValueError:
                pass

        if not event_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId"}),
                status_code=400,
                mimetype="application/json"
            )

        # Connect to Events table
        connection_string = os.getenv("AzureWebJobsStorage")
        if not connection_string:
            return func.HttpResponse(
                json.dumps({"error": "AzureWebJobsStorage environment variable not set"}),
                status_code=500,
                mimetype="application/json"
            )
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name="Events"
        )

        # Try to get the event entity
        try:
            entity = table_client.get_entity("Event", event_id)
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": f"Event with id {event_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Clean up entity for output
        event = {k: v for k, v in entity.items() if k not in ("PartitionKey", "RowKey", "etag")}
        event["eventId"] = entity["RowKey"]

        return func.HttpResponse(
            json.dumps(event),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"getEventById error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 