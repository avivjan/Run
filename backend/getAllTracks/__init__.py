import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # connect to Tracks table
        conn_str = os.getenv("AzureWebJobsStorage")
        table = TableClient.from_connection_string(conn_str, table_name="RunningTracks")

        # read all rows
        filter_str = "PartitionKey eq 'Track'"
        tracks = []
        for e in table.query_entities(filter_str):
            track = {k: v for k, v in e.items()
                     if k not in ("PartitionKey", "etag", "RowKey")}
            track["path"] = json.loads(track["path"])
            track["trackId"] = e["RowKey"]
            tracks.append(track)

        return func.HttpResponse(
            json.dumps(tracks),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as exc:
        logging.error(f"getAllTracks error: {exc}")
        return func.HttpResponse(
            json.dumps({"error": f"Something went wrong: {str(exc)}"}),
            status_code=500,
            mimetype="application/json"
        )
