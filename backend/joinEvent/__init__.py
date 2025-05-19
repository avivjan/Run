import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Parse body
        req_body = req.get_json()
        event_id = req_body.get("eventId")
        userId = req_body.get("userId")

        if not event_id or not userId:
            return func.HttpResponse(
                "Missing required fields: eventId or userId",
                status_code=400
            )

        # Connect to RunnersInEvent table
        connection_string = os.getenv("AzureWebJobsStorage")
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name="RunnersInEvent"
        )

        # Prepare entity
        entity = {
            "PartitionKey": event_id,
            "RowKey": userId,
            "joinedAt": datetime.utcnow().isoformat()
        }

        # Insert entity
        table_client.create_entity(entity=entity)

        return func.HttpResponse(
            json.dumps({"message": "user joined event", "eventId": event_id, "userId": userId}),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"JoinEvent error: {e}")
        return func.HttpResponse(f"Something went wrong: {str(e)}", status_code=500)
