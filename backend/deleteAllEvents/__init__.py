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
        events_table = TableClient.from_connection_string(conn_str, table_name="Events")
        runners_table = TableClient.from_connection_string(conn_str, table_name="RunnersInEvent")

        # Get all events
        filter_str = "PartitionKey eq 'Event'"
        deleted_count = 0
        deleted_events = []

        # First, delete all runner registrations for each event
        for event in events_table.query_entities(filter_str):
            event_id = event["RowKey"]
            # Delete all runners for this event
            runner_filter = f"PartitionKey eq '{event_id}'"
            for runner in runners_table.query_entities(runner_filter):
                runners_table.delete_entity(
                    partition_key=runner["PartitionKey"],
                    row_key=runner["RowKey"]
                )
            
            # Delete the event itself
            events_table.delete_entity(
                partition_key="Event",
                row_key=event_id
            )
            deleted_events.append(event_id)
            deleted_count += 1

        return func.HttpResponse(
            json.dumps({
                "message": f"Successfully deleted {deleted_count} events",
                "deletedEvents": deleted_events
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"deleteAllEvents error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 