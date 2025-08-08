import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        search_query = req.params.get('search')
        if not search_query:
            return func.HttpResponse(
                json.dumps({"error": "missing search query"}),
                status_code=400,
                mimetype="application/json"
            )

        connection_string = os.getenv('AzureWebJobsStorage')
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name='Users'
        )

        query_filter = f"RowKey eq '{search_query}'"
        entities = table_client.query_entities(query_filter)

        users = []
        for entity in entities:
            users.append({
                'userId': entity['RowKey'],
            })

        return func.HttpResponse(
            json.dumps(users),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in searchUsers: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 