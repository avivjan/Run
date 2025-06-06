import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Connect to Azure Table Storage
        conn_str = os.getenv('AzureWebJobsStorage')
        tracks_table = TableClient.from_connection_string(conn_str, table_name="Tracks")
        events_table = TableClient.from_connection_string(conn_str, table_name="Events")

        # Get all tracks
        filter_str = "PartitionKey eq 'Track'"
        deleted_count = 0
        deleted_tracks = []
        tracks_in_use = []

        # Check each track if it's used by any event
        for track in tracks_table.query_entities(filter_str):
            track_id = track["RowKey"]
            
            # Check if track is used in any event
            event_filter = f"PartitionKey eq 'Event' and trackId eq '{track_id}'"
            events_using_track = list(events_table.query_entities(event_filter))
            
            if events_using_track:
                # Track is in use
                tracks_in_use.append({
                    "trackId": track_id,
                    "events": [e["RowKey"] for e in events_using_track]
                })
                continue

            # Delete the track if it's not in use
            tracks_table.delete_entity(
                partition_key="Track",
                row_key=track_id
            )
            deleted_tracks.append(track_id)
            deleted_count += 1

        response_data = {
            "message": f"Successfully deleted {deleted_count} tracks",
            "deletedTracks": deleted_tracks
        }

        if tracks_in_use:
            response_data["warning"] = "Some tracks could not be deleted because they are in use"
            response_data["tracksInUse"] = tracks_in_use

        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"deleteAllTracks error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 