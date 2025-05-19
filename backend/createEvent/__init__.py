import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json
import uuid

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Parse request body
        req_body = req.get_json()
        timestamp = req_body.get("timestamp")
        trainer_id = req_body.get("trainerId", None)  # optional
        status = req_body.get("status", "open")

        if not timestamp:
            return func.HttpResponse("Missing required field: timestamp", status_code=400)

        # Generate unique event ID
        event_id = str(uuid.uuid4())

        # Connect to Events table
        connection_string = os.getenv("AzureWebJobsStorage")
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name="Events"
        )

        # Create event entity
        entity = {
            "PartitionKey": "Event",
            "RowKey": event_id,
            "timestamp": timestamp,
            "status": status,
        }

        # Only include trainerId if provided
        if trainer_id:
            entity["trainerId"] = trainer_id

        # Insert event
        table_client.create_entity(entity=entity)

        return func.HttpResponse(
            json.dumps({"eventId": event_id}),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"CreateEvent error: {e}")
        return func.HttpResponse(f"Something went wrong: {str(e)}", status_code=500)
