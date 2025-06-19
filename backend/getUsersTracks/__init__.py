import logging
import azure.functions as func
import os
from azure.data.tables import TableServiceClient
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing request for getUsersTracks.')

    user_id = req.params.get('userId')
    if not user_id:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            user_id = req_body.get('userId')

    if not user_id:
        return func.HttpResponse(
            "Missing userId parameter.",
            status_code=400
        )

    # Azure Table Storage connection
    connection_string = os.getenv("AzureWebJobsStorage")
    table_name = "RunningTracks"

    try:
        service = TableServiceClient.from_connection_string(conn_str=connection_string)
        table_client = service.get_table_client(table_name=table_name)

        # Query: PartitionKey eq user_id (assuming PartitionKey is userId)
        filter_query = f"PartitionKey eq '{user_id}'"
        entities = table_client.query_entities(query_filter=filter_query)

        tracks = []
        for entity in entities:
            # Adjust these fields based on your schema
            tracks.append({
                "trackId": entity.get("RowKey"),
                "name": entity.get("name"),
                "path": entity.get("path"),  # Should be a list of [lng, lat] pairs
                "created": entity.get("created"),
                # Add more fields as needed
            })

        return func.HttpResponse(
            json.dumps(tracks),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error fetching tracks: {e}")
        return func.HttpResponse(
            f"Error fetching tracks: {str(e)}",
            status_code=500
        )