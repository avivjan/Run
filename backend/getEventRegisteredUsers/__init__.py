import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient
from azure.core.exceptions import ResourceNotFoundError


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get eventId from query string or request body
        event_id = req.params.get('eventId')
        if not event_id:
            try:
                req_body = req.get_json()
                event_id = req_body.get('eventId')
            except ValueError:
                pass

        if not event_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId"}),
                status_code=400,
                mimetype="application/json"
            )

        # Connect to Azure Table Storage
        conn_str = os.getenv('AzureWebJobsStorage')
        events_table = TableClient.from_connection_string(conn_str, table_name="Events")
        runners_table = TableClient.from_connection_string(conn_str, table_name="RunnersInEvent")
        users_table = TableClient.from_connection_string(conn_str, table_name="Users")

        # Check if event exists
        try:
            events_table.get_entity("Event", event_id)
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": f"Event with id {event_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Query all runners for this event
        # In RunnersInEvent table, PartitionKey is eventId and RowKey is userId
        filter_str = f"PartitionKey eq '{event_id}'"
        registered_users = []
        
        for runner in runners_table.query_entities(filter_str):
            try:
                # Get the user details from Users table
                user = users_table.get_entity("User", runner["RowKey"])
                # Clean up user data
                user_data = {k: v for k, v in user.items() 
                           if k not in ("PartitionKey", "etag")}
                user_data["userId"] = user["RowKey"]
                registered_users.append(user_data)
            except Exception as e:
                logging.warning(f"User {runner['RowKey']} registered but not found in Users table")

        return func.HttpResponse(
            json.dumps(registered_users),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"getEventRegisteredUsers error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 