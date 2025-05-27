import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # connect to Events table
        conn_str = os.getenv("AzureWebJobsStorage")
        table = TableClient.from_connection_string(conn_str, table_name="Events")

        # read all rows with status == "open"
        filter_str = "PartitionKey eq 'Event' and status eq 'open'"
        open_events = []
        for e in table.query_entities(filter_str):
            event = {k: v for k, v in e.items()
                    if k not in ("PartitionKey", "etag")}
            event["eventId"] = e["RowKey"]
            open_events.append(event)

        return func.HttpResponse(
            json.dumps(open_events),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as exc:
        logging.error(f"getAllOpenEvents error: {exc}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
