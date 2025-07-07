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
        user_id = req_body.get("userId")
        distance = req_body.get("distance", 0)
        track_id = req_body.get("trackId")
        event_id = req_body.get("eventId", None)
        duration = req_body.get("duration", 0)
        start_time = req_body.get("start_time")
        stop_time = req_body.get("stop_time")
        calories = req_body.get("calories", 0)
        avg_pace = req_body.get("averagePace", 0)
        avg_speed = req_body.get("averageSpeed", 0)
        type = req_body.get("type", "Free Run")

        # Validate required fields
        if not all([timestamp, user_id, track_id, start_time, stop_time]):
            missing_fields = []
            if not timestamp: missing_fields.append("timestamp")
            if not user_id: missing_fields.append("userId")
            if not track_id: missing_fields.append("trackId")
            if not start_time: missing_fields.append("start_time")
            if not stop_time: missing_fields.append("stop_time")
            
            logging.error(f"Missing fields: {', '.join(missing_fields)}")
            return func.HttpResponse(
                json.dumps({"error": f"Missing required fields: {', '.join(missing_fields)}"}),
                status_code=400,
                mimetype="application/json"
            )

        # Generate unique activity ID
        activity_id = str(uuid.uuid4())

        # Connect to Activities table
        connection_string = os.getenv("AzureWebJobsStorage")
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name="Activities"
        )

        # Create activity entity
        entity = {
            "PartitionKey": user_id,  # Changed from "Activity" to user_id
            "RowKey": activity_id,
            "start_time": start_time,
            "stop_time": stop_time,
            "distance": float(distance),  # Ensure numeric types
            "duration": int(duration),
            "calories": float(calories),
            "trackId": track_id,
            "timestamp": timestamp,
            "averagePace": float(avg_pace),
            "averageSpeed": float(avg_speed),
            "type": type
        }

        # Only include eventId if provided
        if event_id:
            entity["eventId"] = event_id

        # Insert activity
        table_client.create_entity(entity=entity)
        
        # Send SignalR message
        signalrMessages.set(json.dumps({
            'target': 'createActivity',
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