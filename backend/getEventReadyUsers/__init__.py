import logging
import json
import os

import azure.functions as func
from azure.data.tables import TableClient, TableServiceClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from shared.auth import require_auth

EVENTS_TABLE = "Events"
READY_USERS_TABLE = "ReadyUsers"
USERS_TABLE = "Users"

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        event_id = req.params.get("eventId")
        if not event_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")
        if not conn:
            raise ValueError("AzureWebJobsStorage connection string not found")

        # Check if event exists
        events_tbl = TableClient.from_connection_string(conn, EVENTS_TABLE)
        try:
            events_tbl.get_entity("Event", event_id)
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": f"event {event_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Ensure ReadyUsers table exists
        table_service = TableServiceClient.from_connection_string(conn)
        try:
            table_service.create_table(READY_USERS_TABLE)
            logging.info(f"Created {READY_USERS_TABLE} table")
        except ResourceExistsError:
            # Table already exists, which is fine
            pass

        # Get ready users
        ready_users_tbl = TableClient.from_connection_string(conn, READY_USERS_TABLE)
        users_tbl = TableClient.from_connection_string(conn, USERS_TABLE)
        
        ready_users = []
        try:
            # Query all ready users for this event
            ready_users_query = ready_users_tbl.query_entities(f"PartitionKey eq '{event_id}'")
            
            # For each ready user, get their details from Users table
            for ready_user in ready_users_query:
                try:
                    user = users_tbl.get_entity("User", ready_user["RowKey"])
                    ready_users.append({
                        "UserId": user["RowKey"],
                        "FirstName": user["FirstName"],
                        "LastName": user["LastName"],
                        "readyAt": ready_user["readyAt"]
                    })
                except ResourceNotFoundError:
                    # Skip users that don't exist anymore
                    continue

        except Exception as e:
            logging.error(f"Error querying ready users: {e}")
            # Return empty list instead of error if table is empty or query fails
            ready_users = []

        return func.HttpResponse(
            json.dumps(ready_users),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"GetEventReadyUsers error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 