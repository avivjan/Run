import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        user = getattr(req, 'user', {})
        user_id = user.get('username')
        target_user_id = req.params.get('userId')
        if not target_user_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing userId parameter"}),
                status_code=400,
                mimetype="application/json"
            )

        connection_string = os.getenv('AzureWebJobsStorage')
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name='Friendships'
        )

        # Query for any friendship between the two users
        filter1 = f"requester_id eq '{user_id}' and addressee_id eq '{target_user_id}'"
        filter2 = f"requester_id eq '{target_user_id}' and addressee_id eq '{user_id}'"
        query_filter = f"({filter1}) or ({filter2})"
        entities = list(table_client.query_entities(query_filter))

        if entities:
            status = entities[0]['status']
        else:
            status = None

        return func.HttpResponse(
            json.dumps({"status": status}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in getFriendshipStatus: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 