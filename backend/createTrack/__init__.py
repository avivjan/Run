import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json
import uuid
from shared.auth import require_auth

@require_auth
def main(
        req: func.HttpRequest
    ) -> func.HttpResponse:
    try:
        # Parse request body
        req_body = req.get_json()
        path = req_body.get("path")
        if not path:
            logging.error("Missing required field: path")
            return func.HttpResponse(
                json.dumps({"error": "Missing required field: path"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if len(path) == 0:
            logging.error("path can not be empty")
            return func.HttpResponse(
                json.dumps({"error": "'path' can not be empty"}),
                status_code=400,
                mimetype="application/json"
            )

        # Generate unique track ID
        trackId = str(uuid.uuid4())

        # Connect to Tracks table
        connection_string = os.getenv("AzureWebJobsStorage")
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name="RunningTracks"
        )

        # Create track entity
        entity = {
            "PartitionKey": "Track",
            "RowKey": trackId,
            "path": json.dumps(path),
        }

        # Insert track
        table_client.create_entity(entity=entity)
        logging.info(f"Track created with ID: {trackId}")
        return func.HttpResponse(
            json.dumps({"trackId": trackId}),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"CreateTrack error: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Something went wrong: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

