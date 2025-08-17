import logging
import json
import os
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableClient
from shared.auth import require_auth

RUNNER_POSITIONS_TABLE = "RunnerPositions"

@require_auth
def main(req: func.HttpRequest, signalrMessages: func.Out[str]) -> func.HttpResponse:
    try:
        body = req.get_json()
        event_id = body.get("eventId")
        user_id = body.get("userId")
        latitude = body.get("latitude")
        longitude = body.get("longitude")
        altitude = body.get("altitude")
        speed = body.get("speed", 0)
        heading = body.get("heading", 0)
        distance = body.get("distance", 0)
        elapsed_time = body.get("elapsedTime", 0)

        if not all([event_id, user_id, latitude, longitude]):
            return func.HttpResponse(
                json.dumps({"error": "missing required fields: eventId, userId, latitude, longitude"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")
        if not conn:
            raise ValueError("AzureWebJobsStorage connection string not found")

        # Store position update
        positions_tbl = TableClient.from_connection_string(conn, RUNNER_POSITIONS_TABLE)
        
        position_entity = {
            "PartitionKey": event_id,
            "RowKey": f"{user_id}_{datetime.utcnow().isoformat()}",
            "userId": user_id,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "altitude": float(altitude) if altitude is not None else None,
            "speed": float(speed),
            "heading": float(heading),
            "distance": float(distance),
            "elapsedTime": int(elapsed_time),
            "timestamp": datetime.utcnow().isoformat()
        }

        positions_tbl.create_entity(entity=position_entity)

        # Send SignalR message to all participants
        signalrMessages.set(json.dumps({
            'target': 'runnerPositionUpdate',
            'arguments': [{
                'eventId': event_id,
                'userId': user_id,
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'speed': speed,
                'heading': heading,
                'distance': distance,
                'elapsedTime': elapsed_time,
                'timestamp': position_entity['timestamp']
            }]
        }))

        return func.HttpResponse(
            json.dumps({"message": "position updated"}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"UpdateRunnerPosition error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 