import logging
import json
import os
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableClient
from shared.auth import require_auth

ACTIVITIES_TABLE = "Activities"
RUNNER_POSITIONS_TABLE = "RunnerPositions"

@require_auth
def main(req: func.HttpRequest, signalrMessages: func.Out[str]) -> func.HttpResponse:
    try:
        body = req.get_json()
        event_id = body.get("eventId")
        user_id = body.get("userId")
        # total_distance = body.get("totalDistance", 0)
        # total_duration = body.get("totalDuration", 0)
        # total_calories = body.get("totalCalories", 0)
        # average_pace = body.get("averagePace", 0)
        # average_speed = body.get("averageSpeed", 0)
        # path_data = body.get("path", [])

        if not all([event_id, user_id]):
            return func.HttpResponse(
                json.dumps({"error": "missing required fields: eventId, userId"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")
        if not conn:
            raise ValueError("AzureWebJobsStorage connection string not found")

        # Create activity record
        # activities_tbl = TableClient.from_connection_string(conn, ACTIVITIES_TABLE)
        
        # activity_id = f"event_{event_id}_{user_id}_{datetime.utcnow().isoformat()}"
        # start_time = datetime.utcnow().isoformat()
        # stop_time = datetime.utcnow().isoformat()

        # activity_entity = {
        #     "PartitionKey": user_id,
        #     "RowKey": activity_id,
        #     "start_time": start_time,
        #     "stop_time": stop_time,
        #     "distance": float(total_distance),
        #     "duration": int(total_duration),
        #     "calories": float(total_calories),
        #     "trackId": None,  # Will be set if event has a track
        #     "timestamp": datetime.utcnow().isoformat(),
        #     "averagePace": float(average_pace),
        #     "averageSpeed": float(average_speed),
        #     "type": "Event Run",
        #     "eventId": event_id,
        #     "path": json.dumps(path_data) if path_data else None
        # }

        # activities_tbl.create_entity(entity=activity_entity)

        # Send SignalR message to remove runner from other participants' maps
        signalrMessages.set(json.dumps({
            'target': 'runnerRemoved',
            'arguments': [{
                'eventId': event_id,
                'userId': user_id
            }]
        }))

        return func.HttpResponse(
            json.dumps({
                "message": "event run ended",
                # "activityId": activity_id,
                # "totalDistance": total_distance,
                # "totalDuration": total_duration,
                # "totalCalories": total_calories
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"EndEventRun error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 