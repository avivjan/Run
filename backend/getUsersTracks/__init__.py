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

    logging.info(f"Looking for tracks for user_id: {user_id}")

    # Azure Table Storage connection
    connection_string = os.getenv("AzureWebJobsStorage")
    table_name = "RunningTracks"

    try:
        service = TableServiceClient.from_connection_string(conn_str=connection_string)
        table_client = service.get_table_client(table_name=table_name)

        # Now try the query
        filter_query = "PartitionKey eq 'Track' and userId eq '{}'".format(user_id)
        logging.info(f"Using filter query: {filter_query}")
        entities = table_client.query_entities(query_filter=filter_query)

        query_count = 0
        tracks = []
        
        for entity in entities:
            query_count += 1
            logging.info(f"Query result {query_count}: {dict(entity)}")
            tracks.append({
                "trackId": entity.get("RowKey"),
                "name": entity.get("name", "Unnamed Track"),
                "path": json.loads(entity.get("path", "[]")),
                "timestamp": entity.get("timestamp"),
            })

        logging.info(f"Query returned {query_count} entities")

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