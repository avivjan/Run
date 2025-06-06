import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get trackId from request
        try:
            req_body = req.get_json()
            track_id = req_body.get('trackId')
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid request body"}),
                status_code=400,
                mimetype="application/json"
            )

        if not track_id:
            return func.HttpResponse(
                json.dumps({"error": "trackId is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Connect to Azure Table Storage
        conn_str = os.getenv('AzureWebJobsStorage')
        tracks_table = TableClient.from_connection_string(conn_str, table_name="RunningTracks")
        events_table = TableClient.from_connection_string(conn_str, table_name="Events")

        # Check if track exists
        try:
            track = tracks_table.get_entity(partition_key="Track", row_key=track_id)
        except Exception:
            return func.HttpResponse(
                json.dumps({"error": "Track not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Check if track is used in any events
        event_filter = f"PartitionKey eq 'Event' and trackId eq '{track_id}'"
        events_using_track = list(events_table.query_entities(event_filter))
        
        if events_using_track:
            return func.HttpResponse(
                json.dumps({
                    "error": "Track cannot be deleted because it is used in events",
                    "events": [e["RowKey"] for e in events_using_track]
                }),
                status_code=409,
                mimetype="application/json"
            )

        # Delete the track
        tracks_table.delete_entity(
            partition_key="Track",
            row_key=track_id
        )

        return func.HttpResponse(
            json.dumps({
                "message": "Track deleted successfully",
                "trackId": track_id
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"deleteTrack error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 