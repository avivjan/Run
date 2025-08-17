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

        connection_string = os.getenv('AzureWebJobsStorage')
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name='Friendships'
        )

        query_filter = f"addressee_id eq '{user_id}' and status eq 'pending'"
        entities = table_client.query_entities(query_filter)

        requests = []
        for entity in entities:
            requests.append({
                'request_id': entity['RowKey'],
                'requester_id': entity['requester_id']
            })

        return func.HttpResponse(
            json.dumps(requests),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in getFriendRequests: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 