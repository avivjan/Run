import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json
import uuid

def main(
        req: func.HttpRequest,
        signalrMessages: func.Out[str]
    ) -> func.HttpResponse:
    try:
        # Parse request body
        req_body = req.get_json()
        timestamp = req_body.get("timestamp")
        trainer_id = req_body.get("trainerId", None)  # optional
        status = req_body.get("status", "open") # optional
        latitude = req_body.get("latitude")
        longitude = req_body.get("longitude")
        start_time = req_body.get("start_time", 0) # optional
        track_length = req_body.get("track_length", 0) # optional
        difficulty = req_body.get("difficulty", "beginner") # optional
        type = req_body.get("type", "street") # optional
        event_name = req_body.get("name", f"Event {event_id}") # optional, default to "Event {event_id}"
        track_id = req_body.get("trackId", None)  # optional, not used in this function
        
        if not timestamp:
            return func.HttpResponse(
                json.dumps({"error": "missing timestamp"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not latitude or not longitude:
            return func.HttpResponse(
                json.dumps({"error": "missing latitude or longitude"}),
                status_code=400,
                mimetype="application/json"
            )

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
            "name": event_name,
            "timestamp": timestamp,
            "status": status,
            "latitude": latitude,
            "longitude": longitude,
            "start_time": start_time,
            "track_length": track_length,
            "difficulty": difficulty,
            "type": type,
            "trackId": track_id
        }

        # Only include trainerId if provided
        if trainer_id:
            entity["trainerId"] = trainer_id

        # Insert event
        table_client.create_entity(entity=entity)
        
        
        signalrMessages.set(json.dumps({
            'target': 'addEvent',
            'arguments': [entity]
        }))

        return func.HttpResponse(
            json.dumps(entity),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"CreateEvent error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
