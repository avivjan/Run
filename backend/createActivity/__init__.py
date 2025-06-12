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
        # Parse request body user_id, event_id, distance, duration, calories, start_time, stop_time, track_id and timestamp
        req_body = req.get_json()
        timestamp = req_body.get("timestamp")
        user_id = req_body.get("userId")
        distance = req_body.get("distance", 0) # optional
        track_id = req_body.get("trackId")
        event_id = req_body.get("eventId", None)  # optional
        duration = req_body.get("duration", 0) # optional
        start_time = req_body.get("start_time") # optional
        stop_time = req_body.get("stop_time") # optional
        calories = req_body.get("calories", 0) # optional

        if not timestamp:
            return func.HttpResponse(
                json.dumps({"error": "missing timestamp"}),
                status_code=400,
                mimetype="application/json"
            )

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "missing userId"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not track_id:
            return func.HttpResponse(
                json.dumps({"error": "missing trackId"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not start_time or not stop_time:
            return func.HttpResponse(
                json.dumps({"error": "missing start time or stop time"}),
                status_code=400,
                mimetype="application/json"
            )

        # Generate unique event ID
        activity_id = str(uuid.uuid4())

        # Connect to Events table
        connection_string = os.getenv("AzureWebJobsStorage")
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name="Activities"
        )

        # Create event entity
        entity = {
            "PartitionKey": "Activity",
            "RowKey": activity_id,
            "start_time": start_time,
            "stop_time": stop_time,
            "distance": distance,
            "duration": duration,
            "calories": calories,
            "userId": user_id,
            "trackId": track_id
        }

        # Only include eventId if provided
        if event_id:
            entity["eventId"] = event_id

        # Insert activity
        table_client.create_entity(entity=entity)
        
        
        signalrMessages.set(json.dumps({
            'target': 'addActivity',
            'arguments': [entity]
        }))

        return func.HttpResponse(
            json.dumps(entity),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"CreateActivity error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
