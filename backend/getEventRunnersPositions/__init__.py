import logging
import json
import os
from datetime import datetime, timedelta

import azure.functions as func
from azure.data.tables import TableClient
from shared.auth import require_auth

RUNNER_POSITIONS_TABLE = "RunnerPositions"

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        event_id = req.params.get('eventId')

        if not event_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId parameter"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")
        if not conn:
            raise ValueError("AzureWebJobsStorage connection string not found")

        # Get the most recent position for each runner in the event
        positions_tbl = TableClient.from_connection_string(conn, RUNNER_POSITIONS_TABLE)
        
        # Get positions from the last 5 minutes to ensure we have recent data
        five_minutes_ago = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        filter_query = f"PartitionKey eq '{event_id}' and timestamp gt '{five_minutes_ago}'"
        
        positions = list(positions_tbl.query_entities(filter_query))
        
        # Group by userId and get the most recent position for each
        runner_positions = {}
        for position in positions:
            user_id = position['userId']
            timestamp = position['timestamp']
            
            if user_id not in runner_positions or timestamp > runner_positions[user_id]['timestamp']:
                runner_positions[user_id] = {
                    'userId': user_id,
                    'latitude': float(position['latitude']),
                    'longitude': float(position['longitude']),
                    'speed': float(position['speed']),
                    'heading': float(position['heading']),
                    'distance': float(position['distance']),
                    'elapsedTime': int(position['elapsedTime']),
                    'timestamp': timestamp
                }

        return func.HttpResponse(
            json.dumps(list(runner_positions.values())),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"GetEventRunnersPositions error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 